"""Task 171a-1: second-genre (wuxia) small-sample generation for metric P/R/F1.

Generates a fresh wuxia project Ch1-Ch4 into an isolated DB so 171a's genre-decoupled
voice/exposition metrics can be validated on non-scifi prose (framework §8 B2).

Usage:
    python scripts/run_171a1_generate.py --init          # clean DB + create project + outline
    python scripts/run_171a1_generate.py --start 1 --end 4
"""

from __future__ import annotations

import argparse
import asyncio
import json
import os
import sys
import uuid
from pathlib import Path
from typing import Any

sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from songyan.config import settings
from songyan.db import get_db
from songyan.db.connection import get_db_path
from songyan.db.migrations import init_schema
from songyan.db.narrative_repo import NarrativeRepository
from songyan.db.repository import ProjectRepository
from songyan.exceptions import AutoHaltException
from songyan.models import ArcPlan, GateConfig, PlotThread, ProjectSetting, StoryOutline
from songyan.workflows.phase2_graph import run_project_pipeline

DB_PATH = Path(".tmp/task171a1_wuxia.db")
PROJECT_FILE = Path(".tmp/task171a1_wuxia_project.json")
settings.database_url = os.getenv("DATABASE_URL", f"sqlite:///{DB_PATH}")
GATE_MODE = os.getenv("GATE_MODE", "observe")
ON_FAILURE = os.getenv("ON_FAILURE", "isolate")


def _project_setting() -> ProjectSetting:
    return ProjectSetting(
        title="断剑江湖",
        genre_id="wuxia",
        mode_id="webnovel",
        protagonist_name="沈砚",
        protagonist_background="没落剑派弟子，师门被灭后独自查凶，剑法未成而心志已冷",
        core_hook="一柄断剑牵出二十年前灭门旧案，江湖各派都想抢先夺回断剑中的秘密",
        target_reader_expectation="传统武侠+悬疑复仇，重人物对峙与江湖恩怨",
        target_word_count=300000,
        tone="沉郁",
        estimated_chapters=100,
        words_per_chapter=3000,
        story_structure="serial",
        arc_boundaries=[25, 50, 75],
        arc_boundaries_auto=True,
    )


def _build_outline(project_id: str) -> tuple[StoryOutline, list[ArcPlan], list[PlotThread]]:
    outline = StoryOutline(
        project_id=project_id,
        core_conflict="沈砚为师门复仇，与隐藏在江湖各派背后的灭门主谋对抗",
        mainline_synopsis=(
            "没落剑派弟子沈砚在师门被灭后，凭一柄断剑追查真凶。断剑中似藏着"
            "二十年前那桩灭门旧案的秘密，引来各大门派觊觎。沈砚在追凶途中结识"
            "亦敌亦友的女捕快苏九娘与老酒鬼剑客柳孤鸣，逐步揭开当年恩怨——灭门"
            "并非江湖仇杀，而与朝堂密谋牵连。沈砚必须在剑法大成与人心不失之间，"
            "做出抉择。"
        ),
        themes=["复仇与放下", "江湖道义", "人心叵测"],
        intended_ending="沈砚查明真相却选择不以血还血，断剑归鞘，江湖重归平静",
    )
    threads = [
        PlotThread(
            thread_id="t_broken_sword",
            project_id=project_id,
            title="断剑之秘",
            description="断剑中藏着灭门旧案的关键线索",
            is_mainline=True,
            expected_resolve_arc=3,
        ),
        PlotThread(
            thread_id="t_massacre",
            project_id=project_id,
            title="灭门旧案",
            description="二十年前沈砚师门被灭的真相",
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
            arc_goal="沈砚持断剑入江湖、结识苏九娘与柳孤鸣，追凶开局",
            threads_to_open=["t_broken_sword", "t_massacre"],
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


async def _init() -> str:
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
    PROJECT_FILE.parent.mkdir(parents=True, exist_ok=True)
    PROJECT_FILE.write_text(
        json.dumps({"project_id": project_id, "db": str(db_path)}, ensure_ascii=False),
        encoding="utf-8",
    )
    print(f"[init] PROJECT_ID={project_id} (saved to {PROJECT_FILE})")
    return project_id


def _resolve_project_id() -> str | None:
    pid = os.getenv("PROJECT_ID")
    if pid:
        return pid
    if PROJECT_FILE.exists():
        try:
            return json.loads(PROJECT_FILE.read_text(encoding="utf-8")).get("project_id")
        except (json.JSONDecodeError, OSError):
            return None
    return None


async def _find_run_id(project_id: str) -> str | None:
    rows = await _query_dicts(
        "SELECT run_id FROM project_runs WHERE project_id = ? "
        "ORDER BY created_at DESC LIMIT 1",
        (project_id,),
    )
    return rows[0]["run_id"] if rows else None


async def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--init", action="store_true")
    parser.add_argument("--start", type=int, default=1)
    parser.add_argument("--end", type=int, default=4)
    parser.add_argument("--project-id", default=None)
    args = parser.parse_args()

    if args.init:
        await _init()
        return 0

    project_id = args.project_id or _resolve_project_id()
    if not project_id:
        parser.error("请先 --init 或提供 --project-id / PROJECT_ID")

    print(f"[preflight] db={get_db_path()}")
    print(f"[preflight] project={project_id}, range=({args.start},{args.end})")
    print(f"[preflight] gate_mode={GATE_MODE}, on_failure={ON_FAILURE}")

    gate_config = GateConfig.for_mode(GATE_MODE)  # type: ignore[arg-type]
    halt_reason: str | None = None
    try:
        result = await run_project_pipeline(
            project_id=project_id,
            chapter_range=(args.start, args.end),
            auto_confirm=True,
            on_failure=ON_FAILURE,
            gate_config=gate_config,
        )
        print("\n=== Pipeline completed ===")
        print(f"Completed: {result.chapters_completed}")
        print(f"Failed: {result.chapters_failed}")
        print(f"Status: {result.final_status}")
    except AutoHaltException as exc:
        halt_reason = f"{exc.reason} (last chapter: {exc.last_chapter})"
        print(f"\n=== AutoHalt: {halt_reason} ===")

    run_id = await _find_run_id(project_id)
    print(f"\nRun ID: {run_id}")
    print(f"Halt: {halt_reason or 'None'}")
    return 0


if __name__ == "__main__":
    asyncio.run(main())
