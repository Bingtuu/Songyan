"""task 265 S1: 服务层组装——story_brief / character_roster 从库构建。"""

from __future__ import annotations

from pathlib import Path

import pytest

import songyan.db.connection as conn_mod
from songyan.db import ProjectRepository
from songyan.db.migrations import init_schema
from songyan.db.narrative_repo import NarrativeRepository
from songyan.db.repository import CharacterRepository
from songyan.models import Character, ProjectSetting
from songyan.models.chapter import ChapterGoal
from songyan.models.narrative import ArcPlan, PlotThread, StoryOutline

_PID = "p-orient"
_CH_BG = "27岁，庆安大厦夜班保安，退伍后长期失眠所以上长夜班"
_CORE = "夜班保安与零点十三分鬼电梯的对峙"


@pytest.fixture
async def oriented_db(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> str:
    db_path = tmp_path / "orient.db"
    monkeypatch.setattr(
        conn_mod,
        "settings",
        type("S", (), {"database_url": f"sqlite:///{db_path}"})(),
    )
    await init_schema(db_path)
    await ProjectRepository().create(
        ProjectSetting(
            title="末班电梯",
            genre_id="urban",
            mode_id="webnovel_intense",
            protagonist_name="陈屿",
            protagonist_background=_CH_BG,
            core_hook="零点十三分，电梯门会开向不存在的楼层",
        ),
        _PID,
    )
    repo = NarrativeRepository()
    await repo.upsert_outline(
        StoryOutline(
            project_id=_PID,
            core_conflict=_CORE,
            mainline_synopsis="老式电梯每天零点十三分停靠13A层",
            themes=["都市恐怖", "灵异悬疑"],
        ),
    )
    await repo.add_arc_plan(
        ArcPlan(
            arc_id=f"{_PID}-arc0",
            project_id=_PID,
            arc_index=0,
            start_chapter=1,
            end_chapter=30,
            arc_goal="确立零点电梯异象",
            is_mainline=True,
        )
    )
    await repo.upsert_thread(
        PlotThread(
            thread_id=f"{_PID}-t-elevator",
            project_id=_PID,
            title="13A层之谜",
            status="opened",
        )
    )
    await CharacterRepository().create(
        Character(
            character_id="char-chen",
            project_id=_PID,
            name="陈屿",
            role_type="protagonist",
            background=_CH_BG,
        )
    )
    await CharacterRepository().create(
        Character(
            character_id="char-zhang",
            project_id=_PID,
            name="老张",
            role_type="supporting",
            background="58岁，老电梯维修工" + "，在这栋楼干了三十年" * 30,
        )
    )
    return _PID


async def test_story_brief_built_from_storyline_and_project(
    oriented_db: str,
) -> None:
    from songyan.workflows._helpers import assemble_context_package

    pkg = await assemble_context_package(
        oriented_db, 1, ChapterGoal(chapter_number=1, word_count_target=3000), None
    )
    assert _CORE in pkg.story_brief
    assert "13A层" in pkg.story_brief  # 主线梗概
    assert "确立零点电梯异象" in pkg.story_brief  # 当前弧目标
    assert "13A层之谜" in pkg.story_brief  # 开放线索
    assert "零点十三分，电梯门会开向不存在的楼层" in pkg.story_brief  # 核心钩子
    assert "末班电梯" in pkg.story_brief  # 书名


async def test_character_roster_built_from_characters(oriented_db: str) -> None:
    from songyan.workflows._helpers import assemble_context_package

    pkg = await assemble_context_package(
        oriented_db, 1, ChapterGoal(chapter_number=1, word_count_target=3000), None
    )
    assert "陈屿（主角）" in pkg.character_roster
    assert _CH_BG in pkg.character_roster  # 主角背景全量
    assert "老张（配角）" in pkg.character_roster
    # 非主角裁剪：长背景不得全文出现
    assert "，在这栋楼干了三十年" * 30 not in pkg.character_roster


async def test_empty_storyline_yields_empty_brief(oriented_db: str) -> None:
    """无大纲项目的 story_brief 允许为空（S2 提醒负责兜底提示）。"""
    from songyan.db.connection import get_db

    async with get_db() as conn:
        await conn.execute("DELETE FROM story_outlines WHERE project_id=?", (_PID,))
        await conn.execute("DELETE FROM arc_plans WHERE project_id=?", (_PID,))
        await conn.execute("DELETE FROM plot_threads WHERE project_id=?", (_PID,))
        await conn.execute(
            "UPDATE projects SET title='', protagonist_name='', core_hook='', "
            "protagonist_background='' WHERE project_id=?",
            (_PID,),
        )
        await conn.commit()
    from songyan.workflows._helpers import assemble_context_package

    pkg = await assemble_context_package(
        oriented_db, 1, ChapterGoal(chapter_number=1, word_count_target=3000), None
    )
    assert pkg.story_brief == ""
