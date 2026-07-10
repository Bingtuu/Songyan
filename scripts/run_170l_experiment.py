"""Task 170l: Ch29-Ch32 few_shot_voice_anchor experiment harness.

用法:
    # 1. 初始化干净隔离 DB + 创建带大纲项目
    python scripts/run_170l_experiment.py --init

    # 2. 真实 LLM 跑 Ch29-Ch32（默认 observe 门禁，on_failure=isolate）
    python scripts/run_170l_experiment.py --start 29 --end 32

说明:
    - 复用 Task 170i 的种子大纲与项目设定，保证窗口可比。
    - 叠加启用 Task 170j 的 minimal_voice_anchor、Task 170k 的 opposing_goal_anchor、
      Task 170l 的 few_shot_voice_anchor 与 ai_tone_blocklist。
    - 默认 GATE_MODE=observe，便于小样本快速验证。
    - 生成后由 scripts/run_170l_reeval.py 做 Ch29-Ch32 抽读复评。
    - 逐章 metrics 追加到 .tmp/task170l_few_shot_voice_anchor_metrics.jsonl。
"""

from __future__ import annotations

import argparse
import asyncio
import json
import os
import sys
import uuid
from datetime import datetime
from pathlib import Path
from typing import Any

# 优先使用当前 worktree 的 src/songyan，避免 editable install 指向主仓库
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from songyan.config import settings
from songyan.db import get_db
from songyan.db.connection import get_db_path
from songyan.db.migrations import init_schema
from songyan.db.narrative_repo import NarrativeRepository
from songyan.db.repository import ProjectRepository
from songyan.exceptions import AutoHaltException
from songyan.models import (
    ArcPlan,
    GateConfig,
    PlotThread,
    ProjectSetting,
    StoryOutline,
)
from songyan.workflows.phase2_graph import run_project_pipeline

_MODES_DIR = Path(__file__).parent.parent / "creative_modes"

# 170l 同时启用 170j/170k 的前置策略 + 本任务新增的 few_shot_voice_anchor + ai_tone_blocklist
DEFAULT_STRATEGY_SLUG = "few_shot_voice_anchor"
DEFAULT_STRATEGY_IDS = [
    "minimal_voice_anchor",
    "opposing_goal_anchor",
    "few_shot_voice_anchor",
    "ai_tone_blocklist",
]
DEFAULT_START_CHAPTER = 29
DEFAULT_END_CHAPTER = 32


def _resolve_db_path(strategy_slug: str) -> Path:
    return Path(f".tmp/task170l_{strategy_slug}.db")


def _resolve_project_file(strategy_slug: str) -> Path:
    return Path(f".tmp/task170l_{strategy_slug}_project.json")


def _resolve_metrics_path(strategy_slug: str) -> Path:
    return Path(f".tmp/task170l_{strategy_slug}_metrics.jsonl")


def _temp_mode_profile_path(strategy_slug: str) -> Path:
    return _MODES_DIR / f"webnovel_intense_{strategy_slug}.json"


DB_PATH = _resolve_db_path(DEFAULT_STRATEGY_SLUG)


def _ensure_temp_mode_profile(strategy_slug: str, strategy_ids: list[str]) -> str:
    """基于 webnovel_intense 创建临时 mode profile，启用指定 literary optimization strategies.

    返回新的 mode_id（文件名，不含 .json）。
    """
    source_path = _MODES_DIR / "webnovel_intense.json"
    target_path = _temp_mode_profile_path(strategy_slug)
    data = json.loads(source_path.read_text(encoding="utf-8"))
    data["id"] = f"webnovel_intense_{strategy_slug}"
    plugins = data.get("literary_optimization_plugins", [])
    for sid in strategy_ids:
        if sid not in plugins:
            plugins.append(sid)
    data["literary_optimization_plugins"] = plugins
    target_path.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
    return f"webnovel_intense_{strategy_slug}"


DATABASE_URL = os.getenv("DATABASE_URL", f"sqlite:///{DB_PATH}")
# 安全默认：强制指向隔离 DB，避免误删/误写主库 songyan.db。
settings.database_url = DATABASE_URL
GATE_MODE = os.getenv("GATE_MODE", "observe")
ON_FAILURE = os.getenv("ON_FAILURE", "isolate")
PROJECT_FILE = _resolve_project_file(DEFAULT_STRATEGY_SLUG)
METRICS_PATH = _resolve_metrics_path(DEFAULT_STRATEGY_SLUG)


def _project_setting() -> ProjectSetting:
    return ProjectSetting(
        title="轨道蜃景",
        genre_id="scifi",
        mode_id="webnovel_intense",
        protagonist_name="林渊",
        protagonist_background="前星际考古学家，因一次事故失去搭档，独自追查真相",
        core_hook="人类在太阳系边缘发现一座无法解析的黑色结构『方舟』，"
        "林渊是唯一能与之产生共鸣的个体",
        target_reader_expectation="硬科幻+太空悬疑，要求科学细节与剧情张力兼顾",
        target_word_count=450000,
        tone="热血",
        estimated_chapters=150,
        words_per_chapter=3000,
        story_structure="serial",
        sub_genre_id="space_opera",
        arc_boundaries=[25, 50, 75, 100, 125],
        arc_boundaries_auto=True,
    )


def _build_outline(project_id: str) -> tuple[StoryOutline, list[ArcPlan], list[PlotThread]]:
    outline = StoryOutline(
        project_id=project_id,
        core_conflict="人类文明存续与深空黑色结构『方舟』的意志之间的对抗",
        mainline_synopsis=(
            "太阳系边缘出现一座无法解析的黑色结构『方舟』。前星际考古学家林渊"
            "是唯一能与之产生『共鸣』的个体。随着军方、财团与神秘教团先后介入，"
            "林渊在追查方舟真相的过程中，逐渐揭开当年那场夺走搭档性命的事故背后"
            "的隐情——『旧日搭档』之死并非意外，而与方舟的苏醒直接相关。林渊必须"
            "在人类被方舟同化之前，破解共鸣的本质，并决定是唤醒还是封存这座方舟。"
        ),
        themes=["存续与牺牲", "认知的边界", "信任与背叛"],
        intended_ending="林渊以自身共鸣为代价封存方舟，人类文明得以延续但代价沉重",
    )

    threads = [
        PlotThread(
            thread_id="t_ark",
            project_id=project_id,
            title="方舟",
            description="太阳系边缘的黑色结构，无法解析，疑似具有意志",
            is_mainline=True,
            expected_resolve_arc=5,
        ),
        PlotThread(
            thread_id="t_resonance",
            project_id=project_id,
            title="共鸣",
            description="林渊与方舟之间独有的感应能力，本质未知",
            is_mainline=True,
            expected_resolve_arc=4,
        ),
        PlotThread(
            thread_id="t_partner",
            project_id=project_id,
            title="旧日搭档",
            description="林渊失去的搭档之死背后的隐情",
            is_mainline=True,
            expected_resolve_arc=3,
        ),
    ]

    arcs = [
        ArcPlan(
            arc_id=f"{project_id}-arc0",
            project_id=project_id,
            arc_index=0,
            start_chapter=1,
            end_chapter=25,
            arc_goal="发现方舟、确立林渊的共鸣者身份，开启三条主线",
            threads_to_open=["t_ark", "t_resonance", "t_partner"],
            threads_to_resolve=[],
            is_mainline=True,
        ),
        ArcPlan(
            arc_id=f"{project_id}-arc1",
            project_id=project_id,
            arc_index=1,
            start_chapter=26,
            end_chapter=50,
            arc_goal="多方势力介入，共鸣加深，旧日搭档之谜浮现关键线索",
            threads_to_open=[],
            threads_to_resolve=[],
            is_mainline=True,
        ),
    ]
    return outline, arcs, threads


async def _query_dicts(sql: str, params: tuple[Any, ...] = ()) -> list[dict[str, Any]]:
    async with get_db() as conn:
        conn.row_factory = lambda cursor, row: {
            col[0]: row[i] for i, col in enumerate(cursor.description)
        }
        cursor = await conn.execute(sql, params)
        return await cursor.fetchall()


async def _init_experiment(strategy_slug: str, strategy_ids: list[str]) -> str:
    db_path = get_db_path()
    for suffix in ("", "-wal", "-shm"):
        p = db_path.with_name(db_path.name + suffix) if suffix else db_path
        if p.exists():
            p.unlink()
            print(f"[init] removed {p}")
    await init_schema()
    print(f"[init] schema initialized at {db_path}")

    project_id = uuid.uuid4().hex
    await ProjectRepository().create(_project_setting(), project_id)
    outline, arcs, threads = _build_outline(project_id)
    await NarrativeRepository().import_outline(project_id, outline, arcs, threads)
    print(f"[init] project created {project_id}")
    print(f"[init] outline imported: {len(arcs)} arcs, {len(threads)} threads")

    # 启用本次实验的文学优化策略（供 Agent 集成读取）
    os.environ["LITERARY_OPTIMIZATION_PLUGINS"] = ",".join(strategy_ids)

    project_file = _resolve_project_file(strategy_slug)
    project_file.parent.mkdir(parents=True, exist_ok=True)
    project_file.write_text(
        json.dumps({"project_id": project_id, "db": str(db_path)}, ensure_ascii=False),
        encoding="utf-8",
    )
    print(f"[init] PROJECT_ID={project_id} (also saved to {project_file})")
    return project_id


def _resolve_project_id(strategy_slug: str) -> str | None:
    pid = os.getenv("PROJECT_ID")
    if pid:
        return pid
    project_file = _resolve_project_file(strategy_slug)
    if project_file.exists():
        try:
            return json.loads(project_file.read_text(encoding="utf-8")).get("project_id")
        except (json.JSONDecodeError, OSError):
            return None
    return None


async def _find_run_id(project_id: str) -> str | None:
    rows = await _query_dicts(
        """SELECT run_id FROM project_runs
           WHERE project_id = ?
           ORDER BY created_at DESC
           LIMIT 1""",
        (project_id,),
    )
    return rows[0]["run_id"] if rows else None


def _load_run_log_metrics(run_id: str | None) -> dict[int, dict[str, Any]]:
    metrics: dict[int, dict[str, Any]] = {}
    if run_id is None:
        return metrics
    path = Path(f"logs/chapter_runs/{run_id}.jsonl")
    if not path.exists():
        return metrics
    for line in path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line:
            continue
        try:
            entry = json.loads(line)
        except json.JSONDecodeError:
            continue
        ch = entry.get("chapter_number")
        if not isinstance(ch, int):
            continue
        metrics[ch] = {
            "success": entry.get("success"),
            "settlement_success": entry.get("settlement_success"),
            "summary_success": entry.get("summary_success"),
            "quality_gate_passed": entry.get("quality_gate_passed"),
            "revision_rounds": entry.get("revision_rounds"),
            "gate_triggered": entry.get("gate_triggered"),
            "gate_reasons": entry.get("gate_reasons") or [],
            "budget_used": entry.get("budget_used"),
            "context_emergency": entry.get("context_emergency"),
            "duration_sec": entry.get("duration_sec"),
            "word_count": entry.get("word_count"),
            "continuity_health_score": entry.get("continuity_health_score"),
        }
    return metrics


def _append_metric(record: dict[str, Any], strategy_slug: str) -> None:
    metrics_path = _resolve_metrics_path(strategy_slug)
    metrics_path.parent.mkdir(parents=True, exist_ok=True)
    with metrics_path.open("a", encoding="utf-8") as f:
        f.write(json.dumps(record, ensure_ascii=False) + "\n")


async def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--init", action="store_true", help="初始化干净 DB + 建项目 + 导入大纲")
    parser.add_argument("--start", type=int, default=DEFAULT_START_CHAPTER, help="起始章节")
    parser.add_argument("--end", type=int, default=DEFAULT_END_CHAPTER, help="结束章节")
    parser.add_argument("--project-id", default=None, help="覆盖 PROJECT_ID")
    args = parser.parse_args()

    # 根据策略 slug 重新定向 DB / project / metrics 路径
    db_path = _resolve_db_path(DEFAULT_STRATEGY_SLUG)
    settings.database_url = f"sqlite:///{db_path}"
    os.environ["LITERARY_OPTIMIZATION_PLUGINS"] = ",".join(DEFAULT_STRATEGY_IDS)

    if args.init:
        await _init_experiment(DEFAULT_STRATEGY_SLUG, DEFAULT_STRATEGY_IDS)
        return 0

    project_id = args.project_id or _resolve_project_id(DEFAULT_STRATEGY_SLUG)
    if not project_id:
        parser.error("请先用 --init 创建项目，或提供 --project-id / PROJECT_ID")

    mode_id = _ensure_temp_mode_profile(DEFAULT_STRATEGY_SLUG, DEFAULT_STRATEGY_IDS)
    db_path = get_db_path()
    print(f"[preflight] db={db_path}")
    print(f"[preflight] project={project_id}, range=({args.start}, {args.end})")
    print(f"[preflight] strategies={DEFAULT_STRATEGY_IDS}")
    print(f"[preflight] gate_mode={GATE_MODE}, on_failure={ON_FAILURE}")

    project = await ProjectRepository().get(project_id)
    if project is None:
        raise ValueError(f"Project not found: {project_id}")

    gate_config = GateConfig.for_mode(GATE_MODE)  # type: ignore[arg-type]

    halt_reason: str | None = None
    try:
        result = await run_project_pipeline(
            project_id=project_id,
            chapter_range=(args.start, args.end),
            mode_id=mode_id,
            auto_confirm=True,
            on_failure=ON_FAILURE,
            gate_config=gate_config,
        )
        print("\n=== Pipeline completed ===")
        print(f"Completed: {result.chapters_completed}")
        print(f"Failed: {result.chapters_failed}")
        print(f"Status: {result.final_status}")
        print(f"Duration: {result.total_duration_sec:.1f}s")
    except AutoHaltException as exc:
        halt_reason = f"{exc.reason} (last chapter: {exc.last_chapter})"
        print("\n=== AutoHalt / Gate triggered ===")
        print(halt_reason)

    run_id = await _find_run_id(project_id)
    run_log = _load_run_log_metrics(run_id)
    completed = sorted(ch for ch, m in run_log.items() if m.get("success"))

    for ch in sorted(run_log.keys()):
        if args.start <= ch <= args.end:
            _append_metric({"chapter": ch, **run_log[ch]}, DEFAULT_STRATEGY_SLUG)

    print("\n=== Summary ===")
    print(f"Timestamp: {datetime.now().isoformat()}")
    print(f"Project: {project_id}")
    print(f"Run ID: {run_id}")
    print(f"Completed chapters: {len(completed)} / {args.end - args.start + 1}")
    print(f"Halt: {halt_reason or 'None'}")
    print(f"Metrics: {_resolve_metrics_path(DEFAULT_STRATEGY_SLUG)}")
    print("下一步: python scripts/run_170l_reeval.py")
    return 0


if __name__ == "__main__":
    asyncio.run(main())
