"""Failure recovery guidance used by V11 CLI commands."""

from __future__ import annotations

from collections.abc import Iterable, Sequence
from dataclasses import dataclass

from songyan.services.doctor_service import DoctorCheck


@dataclass(frozen=True)
class RecoveryAdvice:
    """Human-readable recovery advice for a failure category."""

    category: str
    summary: str
    commands: tuple[str, ...]
    detail: str = ""


def render_recovery_advice(advices: Sequence[RecoveryAdvice]) -> str:
    """Render recovery advice as a compact CLI section."""
    unique: list[RecoveryAdvice] = []
    seen: set[str] = set()
    for advice in advices:
        key = f"{advice.category}:{advice.summary}:{advice.commands}"
        if key in seen:
            continue
        seen.add(key)
        unique.append(advice)

    if not unique:
        return ""

    lines = ["", "恢复建议:"]
    for advice in unique:
        lines.append(f"- [{advice.category}] {advice.summary}")
        if advice.detail:
            lines.append(f"  - 说明: {advice.detail}")
        for command in advice.commands:
            lines.append(f"  - 命令: {command}")
    lines.append("  - 文档: docs/troubleshooting.md")
    return "\n".join(lines)


def config_error_advice() -> RecoveryAdvice:
    return RecoveryAdvice(
        category="config_error",
        summary="修正 LLM/API/config 环境变量后重新运行 doctor。",
        commands=(
            'Copy-Item .env.example .env',
            'songyan doctor --json --init-db',
        ),
    )


def database_error_advice() -> RecoveryAdvice:
    return RecoveryAdvice(
        category="database_error",
        summary="初始化或修复 SQLite DB/schema。",
        commands=(
            '$env:DATABASE_URL = "sqlite:///songyan.db"',
            'songyan doctor --json --init-db',
        ),
    )


def preflight_failed_advice() -> RecoveryAdvice:
    return RecoveryAdvice(
        category="preflight_failed",
        summary="run 尚未进入 pipeline；先修复 preflight 中的 FAIL 项。",
        commands=(
            'songyan doctor --json --init-db',
            'songyan list-projects',
        ),
    )


def run_failed_advice(run_id: str) -> RecoveryAdvice:
    return RecoveryAdvice(
        category="run_failed",
        summary="pipeline 已启动但有章节失败；先生成报告定位失败阶段。",
        commands=(
            f'songyan report --run-id {run_id}',
            'songyan run --project-id <project_id> --chapters <range> --auto-confirm --resume',
        ),
    )


def missing_artifact_advice(run_id: str) -> RecoveryAdvice:
    return RecoveryAdvice(
        category="missing_artifact",
        summary="未找到 run 日志或 run_id 不正确。",
        commands=(
            'Get-ChildItem logs/chapter_runs',
            f'songyan report --run-id {run_id}',
        ),
        detail="如果 logs/chapter_runs/<run_id>.jsonl 不存在，请确认 run 输出中的 run_id。",
    )


def no_accepted_content_advice(project_id: str) -> RecoveryAdvice:
    return RecoveryAdvice(
        category="no_accepted_content",
        summary="项目还没有 accepted 正文，无法导出书稿。",
        commands=(
            f'songyan run --project-id {project_id} --chapters 1-3 --auto-confirm',
            (
                f'songyan export --project-id {project_id} --chapters 1-3 '
                '--format md --output exports/'
            ),
        ),
    )


def backup_project_missing_advice() -> RecoveryAdvice:
    return RecoveryAdvice(
        category="asset_restore_error",
        summary="备份项目不存在；先确认 project_id。",
        commands=('songyan list-projects',),
    )


def restore_existing_db_advice() -> RecoveryAdvice:
    return RecoveryAdvice(
        category="asset_restore_error",
        summary="restore 目标 DB 已存在；换新路径或显式确认覆盖。",
        commands=(
            'songyan restore --backup <zip> --database-url sqlite:///restored.db',
            'songyan restore --backup <zip> --database-url sqlite:///restored.db --force',
        ),
        detail="--force 会覆盖目标 DB，执行前请确认已有文件不再需要。",
    )


def restore_bad_package_advice() -> RecoveryAdvice:
    return RecoveryAdvice(
        category="asset_restore_error",
        summary="备份资产包不可读取或格式不兼容；请重新生成 backup。",
        commands=('songyan backup --project-id <project_id> --output backups/',),
    )


def advice_for_doctor_checks(checks: Iterable[DoctorCheck]) -> list[RecoveryAdvice]:
    """Map failed doctor/preflight checks to recovery advice."""
    advices: list[RecoveryAdvice] = []
    for check in checks:
        if check.status != "fail":
            continue
        if check.id in {
            "config.load",
            "llm.key",
            "llm.config",
            "runtime.checkpointer",
            "runtime.budget",
        }:
            advices.append(config_error_advice())
        elif check.id.startswith("db."):
            advices.append(database_error_advice())
        elif check.id == "project.exists":
            advices.append(
                RecoveryAdvice(
                    category="preflight_failed",
                    summary="项目不存在或 DATABASE_URL 指向错误。",
                    commands=('songyan list-projects', 'songyan doctor --json --init-db'),
                )
            )
        elif check.id in {"logs.path", "resources.package"}:
            advices.append(preflight_failed_advice())
    return advices


def advice_for_export_error(message: str, project_id: str) -> list[RecoveryAdvice]:
    if "没有可导出的 accepted 章节" in message:
        return [no_accepted_content_advice(project_id)]
    return [
        RecoveryAdvice(
            category="missing_artifact",
            summary="导出失败；请确认 project_id、章节范围和 accepted 状态。",
            commands=('songyan list-projects',),
        )
    ]


def advice_for_backup_error(message: str) -> list[RecoveryAdvice]:
    if "project not found" in message:
        return [backup_project_missing_advice()]
    return [
        RecoveryAdvice(
            category="asset_restore_error",
            summary="备份失败；请先确认 DB、project_id 和输出路径。",
            commands=('songyan doctor --json --init-db', 'songyan list-projects'),
        )
    ]


def advice_for_restore_error(message: str) -> list[RecoveryAdvice]:
    if "already exists" in message or "已存在" in message:
        return [restore_existing_db_advice()]
    if "not a valid zip" in message or "missing" in message or "unsupported" in message:
        return [restore_bad_package_advice()]
    return [
        RecoveryAdvice(
            category="asset_restore_error",
            summary="恢复失败；请确认 backup 路径和目标 database-url。",
            commands=('songyan restore --backup <zip> --database-url sqlite:///restored.db',),
        )
    ]
