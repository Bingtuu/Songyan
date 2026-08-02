"""Environment diagnostics for the ``songyan doctor`` CLI command."""

from __future__ import annotations

import os
from dataclasses import dataclass
from importlib.resources import files
from pathlib import Path
from typing import Any, Literal

from songyan.config import Settings, get_settings_load_error, settings
from songyan.creative_modes.registry import list_creative_mode_profiles
from songyan.db.migrations import init_schema, verify_schema
from songyan.db.repository import ProjectRepository
from songyan.genres.loader import list_genre_profiles
from songyan.literary_optimization.plugin_loader import load_strategy_plugins
from songyan.llm.client import aclose_llm_clients, get_llm
from songyan.project_templates import ProjectTemplateLoader
from songyan.prompts import get_prompt_loader

DoctorStatus = Literal["pass", "warn", "fail"]

_REQUIRED_SCHEMA_COLUMNS: dict[str, set[str]] = {
    "projects": {"estimated_chapters", "words_per_chapter", "story_structure"},
    "chapter_versions": {"score_card"},
    "context_snapshots": {"context_emergency_level", "budget_used_before_emergency"},
    "creative_briefs": {
        "punch_points",
        "voice_anchors",
        "voice_samples",
        "protagonist_active_choice",
    },
    "human_marks": {"lifecycle_status", "version_id", "severity"},
    "setting_tracking": {"category"},
    "llm_call_usage": {"cost_cny", "token_source", "cost_source", "retry_attempt"},
}

_REQUIRED_SCHEMA_INDEXES: dict[str, set[str]] = {
    "llm_call_usage": {"idx_llm_call_usage_run", "idx_llm_call_usage_run_chapter"},
    "run_db_metrics": {"idx_run_db_metrics_run", "idx_run_db_metrics_project_chapter"},
}


@dataclass(frozen=True)
class DoctorCheck:
    """Single doctor check result."""

    id: str
    status: DoctorStatus
    message: str
    hint: str = ""

    def to_dict(self) -> dict[str, str]:
        """Return a JSON-serializable representation."""
        data = {"id": self.id, "status": self.status, "message": self.message}
        if self.hint:
            data["hint"] = self.hint
        return data


@dataclass(frozen=True)
class DoctorReport:
    """Aggregated doctor report."""

    status: DoctorStatus
    checks: tuple[DoctorCheck, ...]
    summary: dict[str, int]

    def to_dict(self) -> dict[str, object]:
        """Return a JSON-serializable representation."""
        return {
            "status": self.status,
            "checks": [check.to_dict() for check in self.checks],
            "summary": self.summary,
        }


def _summarize(checks: list[DoctorCheck]) -> DoctorReport:
    summary = {
        "pass": sum(1 for check in checks if check.status == "pass"),
        "warn": sum(1 for check in checks if check.status == "warn"),
        "fail": sum(1 for check in checks if check.status == "fail"),
    }
    status: DoctorStatus = "fail" if summary["fail"] else "warn" if summary["warn"] else "pass"
    return DoctorReport(status=status, checks=tuple(checks), summary=summary)


def _check_settings_load() -> DoctorCheck:
    error = get_settings_load_error()
    if error is None:
        return DoctorCheck("config.load", "pass", "settings loaded")

    details: list[str] = []
    for item in error.errors(include_url=False, include_input=False):
        loc = ".".join(str(part) for part in item.get("loc", ())) or "settings"
        details.append(f"{loc}: {item.get('msg', 'invalid value')}")
    message = "settings validation failed: " + "; ".join(details[:5])
    return DoctorCheck(
        "config.load",
        "fail",
        message,
        "请检查 .env 或环境变量中的配置值；修正后重新运行 songyan doctor --json。",
    )


def _sqlite_path_from_url(database_url: str) -> Path:
    prefix = "sqlite:///"
    if not database_url.startswith(prefix):
        raise ValueError(f"Unsupported database_url: {database_url}")
    return Path(database_url[len(prefix) :])


def _nearest_existing_parent(path: Path) -> Path | None:
    current = path.parent
    while not current.exists():
        parent = current.parent
        if parent == current:
            return None
        current = parent
    return current


def _is_directory_writable(path: Path) -> bool:
    return path.is_dir() and os.access(path, os.W_OK)


def _check_env_file(env_path: Path = Path(".env")) -> DoctorCheck:
    if env_path.exists():
        return DoctorCheck("config.env", "pass", f"{env_path} exists")
    return DoctorCheck(
        "config.env",
        "warn",
        f"{env_path} not found",
        "可使用环境变量提供配置；如需本地文件，请复制 .env.example 为 .env。",
    )


def _check_llm_config(config: Settings) -> list[DoctorCheck]:
    checks: list[DoctorCheck] = []
    api_key = config.llm_api_key or os.getenv("LLM_API_KEY", "")
    if api_key:
        checks.append(DoctorCheck("llm.key", "pass", "LLM API key configured"))
    else:
        checks.append(
            DoctorCheck(
                "llm.key",
                "fail",
                "LLM API key is not configured",
                "请设置 LLM_API_KEY 环境变量或在 .env 中配置 llm_api_key。",
            )
        )

    if not config.llm_base_url:
        checks.append(DoctorCheck("llm.config", "fail", "LLM base URL is empty"))
    elif not config.llm_model:
        checks.append(DoctorCheck("llm.config", "fail", "LLM model is empty"))
    elif not 0 <= config.llm_temperature <= 2:
        checks.append(
            DoctorCheck(
                "llm.config",
                "warn",
                f"LLM temperature looks unusual: {config.llm_temperature}",
            )
        )
    else:
        checks.append(
            DoctorCheck(
                "llm.config",
                "pass",
                f"model={config.llm_model}, base_url={config.llm_base_url}",
            )
        )
    return checks


async def _check_database(
    config: Settings,
    *,
    init_db: bool,
    strict_schema: bool = False,
) -> list[DoctorCheck]:
    checks: list[DoctorCheck] = []
    try:
        db_path = _sqlite_path_from_url(config.database_url)
    except ValueError as exc:
        return [
            DoctorCheck(
                "db.url",
                "fail",
                str(exc),
                "当前仅支持 sqlite:///... 形式的 DATABASE_URL。",
            )
        ]

    checks.append(DoctorCheck("db.url", "pass", config.database_url))

    existing_parent = _nearest_existing_parent(db_path)
    if existing_parent is None or not _is_directory_writable(existing_parent):
        checks.append(
            DoctorCheck(
                "db.path",
                "fail",
                f"database parent is not writable: {db_path.parent}",
            )
        )
        return checks
    checks.append(DoctorCheck("db.path", "pass", f"writable parent: {existing_parent}"))

    if init_db:
        try:
            await init_schema(db_path)
        except Exception as exc:  # noqa: BLE001 - convert diagnostic failures to report rows
            checks.append(
                DoctorCheck(
                    "db.schema",
                    "fail",
                    f"schema initialization failed: {exc}",
                )
            )
            return checks

    if not db_path.exists():
        checks.append(
            DoctorCheck(
                "db.schema",
                "fail" if strict_schema else "warn",
                "database does not exist",
                "运行 songyan doctor --init-db 可初始化当前 DATABASE_URL 指向的库。",
            )
        )
        return checks

    try:
        import aiosqlite

        async with aiosqlite.connect(db_path) as conn:
            missing = await verify_schema(conn)
            drift = [] if missing else await _schema_drift(conn)
    except Exception as exc:  # noqa: BLE001 - diagnostic command should report, not crash
        checks.append(DoctorCheck("db.schema", "fail", f"schema check failed: {exc}"))
        return checks

    if missing:
        checks.append(
            DoctorCheck(
                "db.schema",
                "fail" if strict_schema else "warn",
                f"schema missing {len(missing)} tables",
                "运行 songyan doctor --init-db 可初始化或迁移当前数据库。",
            )
        )
    else:
        if drift:
            checks.append(
                DoctorCheck(
                    "db.schema",
                    "fail" if strict_schema else "warn",
                    f"schema drift detected: {', '.join(drift[:5])}",
                    "运行 songyan doctor --init-db 可补齐缺失迁移。",
                )
            )
        else:
            checks.append(DoctorCheck("db.schema", "pass", "schema complete"))
    return checks


async def _schema_drift(conn: Any) -> list[str]:
    """Return missing migration columns/indexes from an otherwise table-complete DB."""
    drift: list[str] = []
    for table, required_columns in _REQUIRED_SCHEMA_COLUMNS.items():
        cursor = await conn.execute(f"PRAGMA table_info({table})")
        columns = {row[1] for row in await cursor.fetchall()}
        for column in sorted(required_columns - columns):
            drift.append(f"{table}.{column}")

    for table, required_indexes in _REQUIRED_SCHEMA_INDEXES.items():
        cursor = await conn.execute(f"PRAGMA index_list({table})")
        indexes = {row[1] for row in await cursor.fetchall()}
        for index in sorted(required_indexes - indexes):
            drift.append(f"{table}.{index}")
    return drift


def _check_runtime_mode(config: Settings) -> DoctorCheck:
    raw_mode = os.getenv("CHECKPOINTER_MODE")
    mode = raw_mode if raw_mode is not None else config.checkpointer_mode
    if mode in {"memory", "sqlite"}:
        return DoctorCheck(
            "runtime.checkpointer",
            "pass",
            f"checkpointer_mode={mode}",
        )
    return DoctorCheck(
        "runtime.checkpointer",
        "fail",
        f"unsupported checkpointer_mode: {mode}",
        "请设置 CHECKPOINTER_MODE=sqlite 或 CHECKPOINTER_MODE=memory。",
    )


def _check_log_path(log_root: Path = Path("logs")) -> DoctorCheck:
    if log_root.exists():
        if not log_root.is_dir():
            return DoctorCheck(
                "logs.path",
                "fail",
                f"log path exists but is not a directory: {log_root}",
            )
        if _is_directory_writable(log_root):
            return DoctorCheck("logs.path", "pass", f"writable log directory: {log_root}")
        return DoctorCheck(
            "logs.path",
            "fail",
            f"log directory is not writable: {log_root}",
        )

    existing_parent = _nearest_existing_parent(log_root)
    if existing_parent is not None and _is_directory_writable(existing_parent):
        return DoctorCheck(
            "logs.path",
            "pass",
            f"log directory can be created under: {existing_parent}",
        )
    return DoctorCheck(
        "logs.path",
        "fail",
        f"log directory parent is not writable: {log_root.parent}",
        "请切换到可写目录，或修正当前工作目录权限。",
    )


def _read_raw_run_cost_budget() -> tuple[str | None, str | None]:
    for env_name in ("SONGYAN_RUN_COST_BUDGET", "RUN_COST_BUDGET"):
        if env_name in os.environ:
            return os.environ[env_name], env_name
    return None, None


def _check_run_cost_budget(config: Settings) -> DoctorCheck:
    raw_value, source = _read_raw_run_cost_budget()
    if raw_value is not None:
        try:
            budget = float(raw_value)
        except ValueError:
            return DoctorCheck(
                "runtime.budget",
                "fail",
                f"{source} must be a non-negative number: {raw_value}",
                "请设置为 0 或正数，例如 SONGYAN_RUN_COST_BUDGET=10。",
            )
    else:
        budget = config.run_cost_budget
        source = "settings.run_cost_budget"

    if budget < 0:
        return DoctorCheck(
            "runtime.budget",
            "fail",
            f"{source} must be non-negative: {budget}",
            "0 表示不启用单次运行成本预算；正数表示预算上限。",
        )
    if budget == 0:
        return DoctorCheck("runtime.budget", "pass", "run cost budget disabled")
    return DoctorCheck("runtime.budget", "pass", f"run cost budget=¥{budget:g}")


def _check_package_resources() -> DoctorCheck:
    try:
        genres = list_genre_profiles()
        modes = list_creative_mode_profiles()
        template_root = files("songyan.project_templates") / "data"
        templates = sorted(
            path.name
            for path in template_root.iterdir()
            if path.is_dir() and (path / "template.yaml").is_file()
        )
        ProjectTemplateLoader().load("scifi")
        get_prompt_loader().load_card("writer")
        plugin_fragments = load_strategy_plugins(["minimal_voice_anchor"], "writer")
        seeds_dir = files("evals") / "seeds"
        schema_file = files("songyan.db") / "schema.sql"

        missing: list[str] = []
        if len(genres) < 7:
            missing.append(f"genres({len(genres)})")
        if len(modes) < 4:
            missing.append(f"modes({len(modes)})")
        for template_id in ("scifi", "xuanhuan", "wuxia", "urban"):
            if template_id not in templates:
                missing.append(f"template:{template_id}")
        if not plugin_fragments:
            missing.append("literary plugin:minimal_voice_anchor/writer")
        if not (seeds_dir / "xuanhuan_webnovel.json").is_file():
            missing.append("evals/seeds/xuanhuan_webnovel.json")
        if not (seeds_dir / "chapters" / "xuanhuan_ch1.md").is_file():
            missing.append("evals/seeds/chapters/xuanhuan_ch1.md")
        if not schema_file.is_file():
            missing.append("songyan.db/schema.sql")

        if missing:
            return DoctorCheck(
                "resources.package",
                "fail",
                "runtime resources missing: " + ", ".join(missing),
            )
        return DoctorCheck(
            "resources.package",
            "pass",
            f"{len(genres)} genres, {len(modes)} modes, {len(templates)} templates",
        )
    except Exception as exc:  # noqa: BLE001 - diagnostic command should report, not crash
        return DoctorCheck("resources.package", "fail", f"resource check failed: {exc}")


async def _probe_llm_connectivity() -> DoctorCheck:
    """Opt-in LLM client probe.

    This only initializes the configured client; it does not issue a generation
    request, avoiding hidden API cost and telemetry writes from doctor.
    """
    try:
        get_llm(temperature=0.0, max_tokens=1, timeout=10)
    except Exception as exc:  # noqa: BLE001 - report any initialization failure
        return DoctorCheck("llm.connectivity", "fail", f"LLM client init failed: {exc}")
    finally:
        await aclose_llm_clients()
    return DoctorCheck("llm.connectivity", "pass", "LLM client initialized")


async def run_doctor(
    *,
    config: Settings = settings,
    check_llm: bool = False,
    init_db: bool = False,
) -> DoctorReport:
    """Run Songyan environment diagnostics."""
    checks: list[DoctorCheck] = []
    checks.append(_check_settings_load())
    checks.append(_check_env_file())
    checks.extend(_check_llm_config(config))
    checks.extend(await _check_database(config, init_db=init_db))
    checks.append(_check_runtime_mode(config))
    checks.append(_check_log_path())
    checks.append(_check_run_cost_budget(config))
    checks.append(_check_package_resources())
    if check_llm:
        checks.append(await _probe_llm_connectivity())
    return _summarize(checks)


async def _check_project_exists(project_id: str) -> DoctorCheck:
    try:
        project = await ProjectRepository().get(project_id)
    except Exception as exc:  # noqa: BLE001 - preflight should report, not crash
        return DoctorCheck(
            "project.exists",
            "fail",
            f"project lookup failed: {exc}",
            "请先运行 songyan doctor --init-db，并确认 DATABASE_URL 指向正确数据库。",
        )
    if project is None:
        return DoctorCheck(
            "project.exists",
            "fail",
            f"project not found: {project_id}",
            "请检查 project_id，或使用 songyan list-projects 找回项目 ID。",
        )
    return DoctorCheck(
        "project.exists",
        "pass",
        f"project found: {project_id}",
    )


async def run_run_preflight(
    project_id: str,
    *,
    config: Settings = settings,
) -> DoctorReport:
    """Run strict preflight checks before starting ``songyan run``."""
    checks: list[DoctorCheck] = []
    checks.append(_check_settings_load())
    checks.extend(_check_llm_config(config))
    checks.extend(await _check_database(config, init_db=False, strict_schema=True))
    checks.append(_check_runtime_mode(config))
    checks.append(_check_log_path())
    checks.append(_check_run_cost_budget(config))
    checks.append(_check_package_resources())

    db_failed = any(check.status == "fail" and check.id.startswith("db.") for check in checks)
    if not db_failed:
        checks.append(await _check_project_exists(project_id))
    return _summarize(checks)
