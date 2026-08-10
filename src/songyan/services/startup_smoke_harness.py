"""V12 startup smoke harness.

This service standardizes Ch1-only / Ch1-Ch3 startup smoke artifacts.  Dry-run
mode performs deterministic preflight and artifact rendering only; it does not
call the generation pipeline or any LLM-backed node.
"""

from __future__ import annotations

from collections.abc import Awaitable, Callable
from datetime import datetime
from pathlib import Path
from typing import Any, Literal

from pydantic import BaseModel, Field

from songyan.db.repository import ProjectRepository
from songyan.evals.streaming_report import generate_report, read_run_logs, write_report
from songyan.models.gate_config import GateConfig
from songyan.models.project import ProjectSetting
from songyan.models.project_run import ProjectRunResult
from songyan.services.export_service import ExportServiceError, export_project
from songyan.services.run_bundle_service import RunBundleServiceError, bundle_run
from songyan.services.supervision_spec import (
    SupervisionSpecError,
    load_project_supervision_spec,
)

StartupSmokeMode = Literal["ch1_only", "ch1_3"]
ArtifactStatus = Literal[
    "written",
    "skipped",
    "failed",
    "safe_no_accepted",
]

PipelineRunner = Callable[..., Awaitable[ProjectRunResult]]


class StartupSmokeArtifact(BaseModel):
    """One artifact or post-run action produced by the startup harness."""

    kind: str
    status: ArtifactStatus
    path: str | None = None
    message: str = ""


class StartupSmokeResult(BaseModel):
    """Structured result for one startup smoke harness invocation."""

    smoke_id: str
    project_id: str
    mode: StartupSmokeMode
    chapters: tuple[int, int]
    dry_run: bool
    status: Literal["dry_run", "completed", "partial", "failed", "preflight_failed"]
    run_id: str | None = None
    preflight_findings: list[str] = Field(default_factory=list)
    artifacts: list[StartupSmokeArtifact] = Field(default_factory=list)

    def artifact(self, kind: str) -> StartupSmokeArtifact | None:
        """Return the first artifact matching ``kind``."""
        for artifact in self.artifacts:
            if artifact.kind == kind:
                return artifact
        return None


def chapter_range_for_startup_smoke(mode: StartupSmokeMode) -> tuple[int, int]:
    """Return the chapter range for a startup smoke mode."""
    if mode == "ch1_only":
        return (1, 1)
    return (1, 3)


async def run_startup_smoke_harness(
    *,
    project_id: str,
    mode: StartupSmokeMode = "ch1_only",
    dry_run: bool = True,
    project_root: str | Path = ".",
    output_dir: str | Path = Path("logs") / "startup_smoke",
    run_id: str | None = None,
    pipeline_runner: PipelineRunner | None = None,
) -> StartupSmokeResult:
    """Run a standardized startup smoke harness.

    Dry-run validates the project and supervision spec, then writes harness
    report/review artifacts without invoking the generation pipeline.
    """
    chapters = chapter_range_for_startup_smoke(mode)
    smoke_id = _new_smoke_id()
    output = Path(output_dir)
    output.mkdir(parents=True, exist_ok=True)

    project = await ProjectRepository().get(project_id)
    findings = _preflight_project(project, project_id)
    findings.extend(_preflight_supervision_spec(Path(project_root), chapters))

    effective_run_id = run_id
    status: Literal["dry_run", "completed", "partial", "failed", "preflight_failed"] = "dry_run"
    if findings:
        status = "preflight_failed"
    elif not dry_run:
        runner = pipeline_runner or _default_pipeline_runner
        pipeline_result = await runner(
            project_id=project_id,
            chapter_range=chapters,
            mode_id=(project.mode_id if project is not None and project.mode_id else "webnovel"),
            auto_confirm=True,
            gate_config=GateConfig.for_mode("enforce"),
            on_failure="isolate",
        )
        effective_run_id = pipeline_result.run_id
        status = _status_from_pipeline_result(pipeline_result)

    result = StartupSmokeResult(
        smoke_id=smoke_id,
        project_id=project_id,
        mode=mode,
        chapters=chapters,
        dry_run=dry_run,
        status=status,
        run_id=effective_run_id,
        preflight_findings=findings,
    )
    result.artifacts.extend(
        [
            _write_reading_review_template(result, output),
            await _write_run_report_if_available(result),
            await _build_bundle_if_available(result, output),
            await _record_export_status(result, output, project),
        ]
    )
    result.artifacts.append(_write_harness_report(result, output))
    return result


def render_reading_review_template(result: StartupSmokeResult) -> str:
    """Render the human reading review template for startup calibration."""
    start, end = result.chapters
    return "\n".join(
        [
            f"# Startup Reading Review - {result.smoke_id}",
            "",
            f"- project_id: `{result.project_id}`",
            f"- run_id: `{result.run_id or '-'}`",
            f"- chapters: `Ch{start}-Ch{end}`",
            f"- mode: `{result.mode}`",
            "",
            "## Decision",
            "",
            "- [ ] GO",
            "- [ ] STOP",
            "- [ ] REVISE-METHOD",
            "",
            "## Machine Gates",
            "",
            "- accepted chapters:",
            "- word count window 2700-3300:",
            "- forbidden scan:",
            "- summary missing facts:",
            "- ContextEmergency:",
            "",
            "## Reading Notes",
            "",
            "- opening hook:",
            "- current-scene density:",
            "- protagonist agency:",
            "- leakage / old accident / new character / coordinate risk:",
            "",
        ]
    )


def render_startup_smoke_report(result: StartupSmokeResult) -> str:
    """Render a compact startup smoke harness report."""
    start, end = result.chapters
    lines = [
        f"# Startup Smoke Harness - {result.smoke_id}",
        "",
        f"- project_id: `{result.project_id}`",
        f"- run_id: `{result.run_id or '-'}`",
        f"- chapters: `Ch{start}-Ch{end}`",
        f"- mode: `{result.mode}`",
        f"- dry_run: `{result.dry_run}`",
        f"- status: `{result.status}`",
        "",
        "## Preflight",
        "",
    ]
    if result.preflight_findings:
        lines.extend(f"- {finding}" for finding in result.preflight_findings)
    else:
        lines.append("- PASS")

    lines.extend(["", "## Artifacts", ""])
    for artifact in result.artifacts:
        path = artifact.path or "-"
        message = artifact.message or "-"
        lines.append(
            f"- `{artifact.kind}`: `{artifact.status}` / path=`{path}` / {message}"
        )
    lines.extend(
        [
            "",
            "## Human Review",
            "",
            "Use the reading review template before allowing Task 222 closure.",
            "",
        ]
    )
    return "\n".join(lines)


def _preflight_project(project: ProjectSetting | None, project_id: str) -> list[str]:
    if project is None:
        return [f"project not found: {project_id}"]
    findings: list[str] = []
    if not project.genre_id:
        findings.append("project genre_id is empty")
    if not project.protagonist_name:
        findings.append("project protagonist_name is empty")
    return findings


def _preflight_supervision_spec(project_root: Path, chapters: tuple[int, int]) -> list[str]:
    try:
        spec = load_project_supervision_spec(project_root)
    except SupervisionSpecError as exc:
        return [f"supervision spec invalid: {exc}"]

    findings: list[str] = []
    for chapter in range(chapters[0], chapters[1] + 1):
        try:
            if not spec.beat_sheet_for_chapter(chapter):
                findings.append(f"Ch{chapter} supervision spec has no beat sheet")
        except (KeyError, ValueError) as exc:
            findings.append(f"Ch{chapter} supervision spec missing: {exc}")
    return findings


async def _default_pipeline_runner(**kwargs: Any) -> ProjectRunResult:
    from songyan.workflows.phase2_graph import run_project_pipeline

    return await run_project_pipeline(**kwargs)


def _status_from_pipeline_result(
    result: ProjectRunResult,
) -> Literal["completed", "partial", "failed"]:
    if result.final_status == "completed" and not result.chapters_failed:
        return "completed"
    if result.chapters_completed:
        return "partial"
    return "failed"


async def _write_run_report_if_available(
    result: StartupSmokeResult,
) -> StartupSmokeArtifact:
    if not result.run_id:
        return StartupSmokeArtifact(
            kind="run_report",
            status="skipped",
            message="no run_id available",
        )
    logs = read_run_logs(result.run_id)
    if not logs:
        return StartupSmokeArtifact(
            kind="run_report",
            status="skipped",
            message="run log not found",
        )

    report_md = generate_report(logs, chapter_range=result.chapters)
    path = write_report(report_md, result.run_id, Path("logs") / "reports")
    return StartupSmokeArtifact(
        kind="run_report",
        status="written",
        path=path.as_posix(),
    )


async def _build_bundle_if_available(
    result: StartupSmokeResult,
    output: Path,
) -> StartupSmokeArtifact:
    if not result.run_id:
        return StartupSmokeArtifact(
            kind="bundle",
            status="skipped",
            message="no run_id available",
        )
    try:
        bundle = await bundle_run(
            result.run_id,
            project_id=result.project_id,
            output=output / "bundles",
        )
    except RunBundleServiceError as exc:
        return StartupSmokeArtifact(
            kind="bundle",
            status="failed",
            message=str(exc),
        )
    return StartupSmokeArtifact(
        kind="bundle",
        status="written",
        path=bundle.bundle_path.as_posix(),
    )


async def _record_export_status(
    result: StartupSmokeResult,
    output: Path,
    project: ProjectSetting | None,
) -> StartupSmokeArtifact:
    if project is None:
        return StartupSmokeArtifact(
            kind="export",
            status="skipped",
            message="project not found",
        )
    try:
        exported = await export_project(
            result.project_id,
            output_dir=output / "exports",
            fmt="md",
            chapters=result.chapters,
        )
    except ExportServiceError as exc:
        if _is_no_accepted_export_error(str(exc)):
            return StartupSmokeArtifact(
                kind="export",
                status="safe_no_accepted",
                message=str(exc),
            )
        return StartupSmokeArtifact(
            kind="export",
            status="failed",
            message=str(exc),
        )
    chapter_count = sum(item.chapter_count for item in exported.files)
    if chapter_count == 0:
        return StartupSmokeArtifact(
            kind="export",
            status="safe_no_accepted",
            message="no accepted chapters exported",
        )
    return StartupSmokeArtifact(
        kind="export",
        status="written",
        path=";".join(item.path.as_posix() for item in exported.files),
        message=f"exported {chapter_count} accepted chapter(s)",
    )


def _write_reading_review_template(
    result: StartupSmokeResult,
    output: Path,
) -> StartupSmokeArtifact:
    path = output / f"reading-review-{result.smoke_id}.md"
    path.write_text(render_reading_review_template(result), encoding="utf-8")
    return StartupSmokeArtifact(
        kind="reading_review",
        status="written",
        path=path.as_posix(),
    )


def _write_harness_report(
    result: StartupSmokeResult,
    output: Path,
) -> StartupSmokeArtifact:
    path = output / f"startup-smoke-{result.smoke_id}.md"
    path.write_text(render_startup_smoke_report(result), encoding="utf-8")
    return StartupSmokeArtifact(
        kind="harness_report",
        status="written",
        path=path.as_posix(),
    )


def _new_smoke_id() -> str:
    return "startup-" + datetime.now().strftime("%Y%m%d-%H%M%S-%f")


def _is_no_accepted_export_error(message: str) -> bool:
    return "没有可导出的 accepted 章节" in message or "没有可渲染的章节" in message
