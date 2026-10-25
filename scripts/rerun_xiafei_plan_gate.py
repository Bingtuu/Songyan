"""Re-run 霞飞路《旧案》 ch1–3 with the read-only plan gate.

Without ``LLM_API_KEY`` (environment or ``.env``), this writes a blocked
scoreboard and does not invent a recall number. With a key, it creates a
project from the experiment template, loads the approved ``xiafei-jiuan``
cards onto that project id, and runs ``songyan run --chapters N
--auto-confirm`` one chapter at a time.

The live review path still does not set ``_plan_attribute_extracts`` or
``_plan_claim_anchors``. After a real run the exported chapters can be
scored with ``scripts/score_xiafei_roadmap_recall.py``. Fill
``occurred.json`` from the prose. Do not treat a missing v4 phrase as
non-occurrence.
"""

from __future__ import annotations

import argparse
import asyncio
import json
import os
import subprocess
import sys
from datetime import date
from pathlib import Path

_ROOT = Path(__file__).resolve().parents[1]
_EXPERIMENT = _ROOT / "docs" / "experiments" / "xiafei-plan-gate-rerun-2026-10-25"
_TEMPLATE_PARENT = _EXPERIMENT / "tpl"
_PLACEHOLDER_KEY = "your-api-key-here"


def main(argv: list[str] | None = None) -> int:
    """Probe the LLM config, then either block or generate chapters 1–3."""
    parser = argparse.ArgumentParser(description="Re-run 霞飞路 ch1–3 against the plan gate")
    parser.add_argument("--output-dir", type=Path, default=_EXPERIMENT)
    parser.add_argument("--template-dir", type=Path, default=_TEMPLATE_PARENT)
    parser.add_argument("--database", type=Path, default=None)
    args = parser.parse_args(argv)
    args.output_dir.mkdir(parents=True, exist_ok=True)

    probe = _llm_probe()
    if not probe["api_key_present"]:
        _write_blocked(args.output_dir, probe)
        print(probe["reason"])
        print(f"scoreboard: {args.output_dir / 'scoreboard.json'}")
        return 2

    database = args.database or (args.output_dir / "run" / "songyan.db")
    database.parent.mkdir(parents=True, exist_ok=True)
    os.environ["DATABASE_URL"] = f"sqlite:///{database}"
    os.environ["CHECKPOINTER_MODE"] = "sqlite"
    project_id = asyncio.run(_prepare_project(args.template_dir))
    (args.output_dir / "project_id.txt").write_text(project_id + "\n", encoding="utf-8")
    log_dir = args.output_dir / "logs"
    log_dir.mkdir(parents=True, exist_ok=True)
    failed = _drive_chapters(project_id, log_dir)
    chapters = asyncio.run(_export_chapters(project_id, args.output_dir / "chapters"))
    note = {
        "project_id": project_id,
        "database": str(database),
        "chapters_exported": sorted(chapters),
        "failed_chapters": failed,
        "llm_probe": probe,
    }
    (args.output_dir / "run_note.json").write_text(
        json.dumps(note, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    if failed or len(chapters) < 3:
        _write_blocked(
            args.output_dir,
            probe,
            reason=(
                "写章没有收齐 ch1–3，召回不算。"
                f" 已导出 {sorted(chapters)}，失败章 {failed}。"
            ),
        )
        return 1
    print(
        "章节已导出。召回还要 occurred.json。"
        " 用 scripts/score_xiafei_roadmap_recall.py 计分，不要在这里填数字。"
    )
    return 0


def _llm_probe() -> dict[str, object]:
    key = os.environ.get("LLM_API_KEY", "").strip()
    dotenv = _ROOT / ".env"
    dotenv_has_key = _dotenv_has_key(dotenv)
    present = bool(key) or dotenv_has_key
    if key == _PLACEHOLDER_KEY:
        present = dotenv_has_key
    reason = (
        "这台环境不能调用 Songyan 的生产 LLM。"
        " LLM_API_KEY 未设置，工作区也没有可用的 .env。"
        " songyan run 的 preflight 会在 llm.key 失败。"
        " 没有新的 ch1–3，五类召回未测量。"
    )
    return {
        "checked_on": date.today().isoformat(),
        "api_key_present": present,
        "dotenv_present": dotenv.is_file(),
        "llm_base_url": os.environ.get("LLM_BASE_URL", "https://api.deepseek.com"),
        "llm_model": os.environ.get("LLM_MODEL", "deepseek-chat"),
        "reason": reason,
    }


def _dotenv_has_key(path: Path) -> bool:
    if not path.is_file():
        return False
    for raw in path.read_text(encoding="utf-8").splitlines():
        line = raw.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        name, value = line.split("=", 1)
        if name.strip() not in {"LLM_API_KEY", "llm_api_key"}:
            continue
        secret = value.strip().strip('"').strip("'")
        if secret and secret != _PLACEHOLDER_KEY:
            return True
    return False


def _write_blocked(
    output_dir: Path,
    probe: dict[str, object],
    *,
    reason: str | None = None,
) -> None:
    from songyan.plan_checks.roadmap_recall import blocked_rerun_scoreboard

    board = blocked_rerun_scoreboard(reason=reason or str(probe["reason"]))
    payload = {
        "experiment": "xiafei-plan-gate-rerun-2026-10-25",
        "chapters_written": False,
        "recall_measured": False,
        "llm_probe": probe,
        "live_review_path": {
            "extracts_state_key": "_plan_attribute_extracts",
            "anchors_state_key": "_plan_claim_anchors",
            "populated_by_run_chapter_pipeline": False,
            "note": (
                "rule_auditor_node 只把 state 里已有的摘录和锚交给 "
                "run_plan_fact_gate。初始 state 不写这两项，所以活路径的"
                "类型化比较为空，主张核验只认主张原文。"
            ),
        },
        "scoreboard": board.model_dump(),
    }
    path = output_dir / "scoreboard.json"
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


async def _prepare_project(template_parent: Path) -> str:
    from songyan.db.migrations import init_schema
    from songyan.db.plan_fact_loader import bundled_xiafei_fixture, load_plan_fact_fixture
    from songyan.project_templates.initializer import ProjectInitializer
    from songyan.project_templates.loader import ProjectTemplateLoader

    await init_schema()
    template = ProjectTemplateLoader(templates_dir=template_parent).load("xiafei")
    project_id, _project = await ProjectInitializer.from_template(template)
    await load_plan_fact_fixture(bundled_xiafei_fixture(), project_id=project_id)
    return project_id


def _drive_chapters(project_id: str, log_dir: Path) -> list[int]:
    """One chapter per process, at most three extra attempts. Returns failures."""
    songyan = Path(sys.executable).with_name("songyan")
    executable = str(songyan if songyan.is_file() else "songyan")
    failed: list[int] = []
    for chapter in (1, 2, 3):
        accepted = False
        for attempt in range(1, 5):
            command = [
                executable,
                "run",
                "--project-id",
                project_id,
                "--chapters",
                str(chapter),
                "--auto-confirm",
                "--on-failure",
                "abort",
            ]
            if attempt > 1:
                command.append("--resume")
            log_path = log_dir / f"run_ch{chapter}_{attempt}.log"
            with log_path.open("w", encoding="utf-8") as log:
                try:
                    completed = subprocess.run(
                        command,
                        cwd=_ROOT,
                        env=os.environ.copy(),
                        stdout=log,
                        stderr=subprocess.STDOUT,
                        timeout=1800,
                        check=False,
                    )
                except subprocess.TimeoutExpired:
                    log.write("\nTIMEOUT after 1800s\n")
                    continue
            if completed.returncode == 0 and _chapter_accepted(project_id, chapter):
                accepted = True
                break
        if not accepted:
            failed.append(chapter)
            break
    return failed


def _chapter_accepted(project_id: str, chapter: int) -> bool:
    import sqlite3

    database = os.environ["DATABASE_URL"].removeprefix("sqlite:///")
    with sqlite3.connect(database) as conn:
        row = conn.execute(
            """SELECT accepted_version_id FROM chapter_heads
               WHERE project_id = ? AND chapter_number = ?""",
            (project_id, chapter),
        ).fetchone()
    return row is not None and row[0] is not None


async def _export_chapters(project_id: str, dest: Path) -> list[int]:
    from songyan.db.repository import ChapterHeadRepository, ChapterVersionRepository

    dest.mkdir(parents=True, exist_ok=True)
    heads = ChapterHeadRepository()
    versions = ChapterVersionRepository()
    exported: list[int] = []
    for chapter in (1, 2, 3):
        head = await heads.get(project_id, chapter)
        if head is None or not head.accepted_version_id:
            continue
        version = await versions.get(head.accepted_version_id)
        if version is None or not version.content:
            continue
        (dest / f"ch0{chapter}.md").write_text(version.content, encoding="utf-8")
        exported.append(chapter)
    return exported


if __name__ == "__main__":
    raise SystemExit(main())
