"""Task 170p 验证：小窗口重生成，验证配角入库 + voice 量具落点.

用法:
    # 1. 初始化干净隔离 DB + 建带大纲项目（复用 170i 科幻大纲种子）
    python scripts/run_170p_validation.py --init

    # 2. 真实 LLM 跑小窗口（默认 Ch1-Ch5，observe 门禁，isolate）
    python scripts/run_170p_validation.py

    # 中途 kill / AutoHalt 后续跑
    python scripts/run_170p_validation.py --resume

    # 3. 只做检查（不跑生成）：查 characters 表 + 逐章 voice 量具
    python scripts/run_170p_validation.py --check

说明:
    - 目的：验证 Task 170p（SettlementExtractor 新配角入库）是否让 `characters`
      表在真实生成中出现配角，从而让 170o 的 `detect_human_voice_homogeneity`
      有归因落点。**不是**文学放行复评，只验证数据层闭环。
    - 用 observe 门禁 + 小窗口，尽量降低成本与 AutoHalt 概率。
    - 结算工艺卡走当前 default（1.0.3，含 new_characters 提取）。
"""

from __future__ import annotations

import argparse
import asyncio
import json
import os
import sys
import uuid
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from songyan.config import settings
from songyan.db.connection import get_db_path
from songyan.db.migrations import init_schema
from songyan.db.narrative_repo import NarrativeRepository
from songyan.db.repository import (
    ChapterHeadRepository,
    ChapterVersionRepository,
    CharacterRepository,
    ProjectRepository,
)
from songyan.exceptions import AutoHaltException
from songyan.models import (
    ArcPlan,
    GateConfig,
    PlotThread,
    ProjectSetting,
    StoryOutline,
)
from songyan.workflows.phase2_graph import run_project_pipeline

DB_PATH = Path(".tmp/task170p_validation.db")
DATABASE_URL = os.getenv("DATABASE_URL", f"sqlite:///{DB_PATH}")
settings.database_url = DATABASE_URL
GATE_MODE = os.getenv("GATE_MODE", "observe")
ON_FAILURE = os.getenv("ON_FAILURE", "isolate")
PROJECT_FILE = Path(".tmp/task170p_project.json")

START_CHAPTER = int(os.getenv("START_CHAPTER", "1"))
END_CHAPTER = int(os.getenv("END_CHAPTER", "5"))


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
            "的隐情。"
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
            arc_goal="发现方舟、确立林渊的共鸣者身份，引入关键配角",
            threads_to_open=["t_ark", "t_partner"],
            threads_to_resolve=[],
            is_mainline=True,
        ),
    ]
    return outline, arcs, threads


async def _init_db() -> str:
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
    print(f"[init] PROJECT_ID={project_id}")
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


async def _check(project_id: str) -> None:
    """查 characters 表 + 逐章 voice 量具落点."""
    from songyan.agents.rule_auditor import detect_human_voice_homogeneity

    chars = await CharacterRepository().list_by_project(project_id)
    print("\n=== characters 表 ===")
    for c in chars:
        print(f"  [{c.role_type}] {c.name} ({c.character_id})")
    registry = {c.name for c in chars if c.name}
    supporting = [c for c in chars if c.role_type in ("supporting", "antagonist")]
    print(f"\n配角/反派入库数: {len(supporting)}  （170p 目标：>0）")

    head_repo = ChapterHeadRepository()
    version_repo = ChapterVersionRepository()
    heads = await head_repo.list_by_project(project_id)
    print("\n=== 逐章 voice 量具（注册表 gating 后）===")
    for head in sorted(heads, key=lambda h: h.chapter_number):
        if head.status != "accepted" or not head.accepted_version_id:
            continue
        version = await version_repo.get(head.accepted_version_id)
        if version is None:
            continue
        hits = detect_human_voice_homogeneity(
            version.content, character_names=registry
        )
        print(
            f"  Ch{head.chapter_number}: homogeneity_hits={len(hits)} "
            f"(registry={len(registry)} names)"
        )


async def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--init", action="store_true")
    parser.add_argument("--resume", action="store_true")
    parser.add_argument("--check", action="store_true", help="只查 characters + voice 量具")
    parser.add_argument("--project-id", default=None)
    args = parser.parse_args()

    if args.init:
        await _init_db()
        return

    project_id = args.project_id or _resolve_project_id()
    if not project_id:
        parser.error("请先用 --init 创建项目，或提供 --project-id / PROJECT_ID")

    if args.check:
        await _check(project_id)
        return

    db_path = get_db_path()
    print(f"[preflight] db={db_path}")
    print(f"[preflight] project={project_id}, range=({START_CHAPTER}, {END_CHAPTER})")
    print(f"[preflight] gate_mode={GATE_MODE}, on_failure={ON_FAILURE}, resume={args.resume}")

    project = await ProjectRepository().get(project_id)
    if project is None:
        raise ValueError(f"Project not found: {project_id}")

    gate_config = GateConfig.for_mode(GATE_MODE)  # type: ignore[arg-type]
    try:
        result = await run_project_pipeline(
            project_id=project_id,
            chapter_range=(START_CHAPTER, END_CHAPTER),
            mode_id=project.mode_id,
            auto_confirm=True,
            on_failure=ON_FAILURE,
            gate_config=gate_config,
            resume=args.resume,
        )
        print("\n=== Pipeline completed ===")
        print(f"Completed: {result.chapters_completed}")
        print(f"Failed: {result.chapters_failed}")
        print(f"Status: {result.final_status}")
    except AutoHaltException as exc:
        print("\n=== AutoHalt / Gate triggered ===")
        print(f"{exc.reason} (last chapter: {exc.last_chapter})")

    await _check(project_id)


if __name__ == "__main__":
    raise SystemExit(asyncio.run(main()))
