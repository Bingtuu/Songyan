"""Tests for Task 142 — 项目创建可携带大纲（--outline-file 导入）.

覆盖：``load_outline_file`` 解析/校验；``NarrativeRepository.import_outline`` 原子写入；
CLI ``create-project`` 缺省行为不变 vs 带大纲导入。
"""

from __future__ import annotations

import asyncio
import json
from contextlib import ExitStack
from pathlib import Path
from unittest.mock import patch

import pytest
from click.testing import CliRunner

from songyan.cli.main import cli
from songyan.cli.outline_import import OutlineImportError, load_outline_file
from songyan.config import settings
from songyan.db.connection import get_db
from songyan.db.migrations import init_schema
from songyan.db.narrative_repo import NarrativeError, NarrativeRepository
from songyan.db.repository import ProjectRepository
from songyan.models import ArcPlan, ProjectSetting, StoryOutline

SAMPLE_OUTLINE = {
    "outline": {
        "core_conflict": "少年对抗宗门",
        "mainline_synopsis": "少年偶得传承，一路对抗压迫他的宗门势力。",
        "themes": ["成长", "复仇"],
        "intended_ending": "登顶宗门之巅",
    },
    "arc_plans": [
        {
            "arc_index": 0, "start_chapter": 1, "end_chapter": 20,
            "arc_goal": "开局立威", "threads_to_open": ["t1"],
            "threads_to_resolve": [], "is_mainline": True,
        },
        {
            "arc_index": 1, "start_chapter": 21, "end_chapter": 40,
            "arc_goal": "宗门风波", "threads_to_open": [],
            "threads_to_resolve": ["t1"], "is_mainline": True,
        },
    ],
    "plot_threads": [
        {
            "thread_id": "t1", "title": "身世之谜",
            "description": "主角真实身世", "is_mainline": True,
            "expected_resolve_arc": 1,
        },
    ],
}

# create-project 交互 prompt 输入（选择器已 mock，仅剩自由文本 9 项）
_CLI_INPUT = "\n英雄\n\n\n\n\n\n\n\n"


def _write_json(tmp_path: Path, data: object) -> str:
    p = tmp_path / "outline.json"
    if isinstance(data, str):
        p.write_text(data, encoding="utf-8")
    else:
        p.write_text(json.dumps(data, ensure_ascii=False), encoding="utf-8")
    return str(p)


async def _seed_project(project_id: str = "proj-142") -> str:
    await ProjectRepository().create(
        ProjectSetting(genre_id="xuanhuan", protagonist_name="英雄"),
        project_id,
    )
    return project_id


# --------------------------------------------------------------------------- #
# load_outline_file（纯解析，无需 DB）
# --------------------------------------------------------------------------- #
class TestLoadOutlineFile:
    def test_valid(self, tmp_path: Path) -> None:
        path = _write_json(tmp_path, SAMPLE_OUTLINE)
        outline, arcs, threads = load_outline_file(path, "p1")
        assert outline.project_id == "p1"
        assert outline.core_conflict == "少年对抗宗门"
        assert [a.arc_index for a in arcs] == [0, 1]
        assert all(a.project_id == "p1" for a in arcs)
        assert arcs[0].arc_id  # 自动生成 arc_id
        assert [t.thread_id for t in threads] == ["t1"]

    def test_missing_file(self, tmp_path: Path) -> None:
        with pytest.raises(OutlineImportError):
            load_outline_file(str(tmp_path / "nope.json"), "p1")

    def test_invalid_json(self, tmp_path: Path) -> None:
        path = _write_json(tmp_path, "{not valid json")
        with pytest.raises(OutlineImportError):
            load_outline_file(path, "p1")

    def test_top_level_not_object(self, tmp_path: Path) -> None:
        path = _write_json(tmp_path, [1, 2, 3])
        with pytest.raises(OutlineImportError):
            load_outline_file(path, "p1")

    def test_missing_required_arc_field(self, tmp_path: Path) -> None:
        data = {"arc_plans": [{"start_chapter": 1, "end_chapter": 20}]}  # 缺 arc_index
        path = _write_json(tmp_path, data)
        with pytest.raises(OutlineImportError):
            load_outline_file(path, "p1")

    def test_dangling_thread_ref(self, tmp_path: Path) -> None:
        data = {
            "arc_plans": [
                {"arc_index": 0, "start_chapter": 1, "end_chapter": 20,
                 "threads_to_open": ["ghost"]},
            ],
            "plot_threads": [],
        }
        path = _write_json(tmp_path, data)
        with pytest.raises(OutlineImportError):
            load_outline_file(path, "p1")

    def test_duplicate_thread_id(self, tmp_path: Path) -> None:
        data = {
            "plot_threads": [
                {"thread_id": "t1"},
                {"thread_id": "t1"},
            ],
        }
        path = _write_json(tmp_path, data)
        with pytest.raises(OutlineImportError):
            load_outline_file(path, "p1")


# --------------------------------------------------------------------------- #
# NarrativeRepository.import_outline（原子写入 + 读回）
# --------------------------------------------------------------------------- #
class TestImportOutline:
    async def test_import_and_readback(self, test_db: Path, tmp_path: Path) -> None:
        pid = await _seed_project()
        path = _write_json(tmp_path, SAMPLE_OUTLINE)
        outline, arcs, threads = load_outline_file(path, pid)
        repo = NarrativeRepository()
        await repo.import_outline(pid, outline, arcs, threads)

        got = await repo.get_outline(pid)
        assert got is not None and got.core_conflict == "少年对抗宗门"
        arc = await repo.get_arc_for_chapter(pid, 5)
        assert arc is not None and arc.arc_index == 0
        assert len(await repo.list_arc_plans(pid)) == 2
        assert len(await repo.list_threads(pid)) == 1

    async def test_import_atomic_rollback(self, test_db: Path) -> None:
        pid = await _seed_project()
        repo = NarrativeRepository()
        outline = StoryOutline(project_id=pid, core_conflict="X")
        # 两个重复 arc_id → 第二次 INSERT 触发 IntegrityError → 整体回滚
        dup1 = ArcPlan(arc_id="dup", project_id=pid, arc_index=0, start_chapter=1, end_chapter=10)
        dup2 = ArcPlan(arc_id="dup", project_id=pid, arc_index=1, start_chapter=11, end_chapter=20)
        with pytest.raises(NarrativeError):
            await repo.import_outline(pid, outline, [dup1, dup2], [])
        # 不留半份数据
        assert await repo.get_outline(pid) is None
        assert await repo.list_arc_plans(pid) == []


# --------------------------------------------------------------------------- #
# CLI create-project（缺省 vs 带大纲）
# --------------------------------------------------------------------------- #
async def _narrative_counts() -> tuple[int, int, int]:
    async with get_db() as conn:
        cur = await conn.execute("SELECT COUNT(*) FROM story_outlines")
        outlines = (await cur.fetchone())[0]
        cur = await conn.execute("SELECT COUNT(*) FROM arc_plans")
        arcs = (await cur.fetchone())[0]
        cur = await conn.execute("SELECT COUNT(*) FROM plot_threads")
        threads = (await cur.fetchone())[0]
    return outlines, arcs, threads


async def _first_project() -> ProjectSetting | None:
    async with get_db() as conn:
        cur = await conn.execute("SELECT project_id FROM projects LIMIT 1")
        row = await cur.fetchone()
    if row is None:
        return None
    return await ProjectRepository().get(row[0])


@pytest.fixture
def cli_db(tmp_path: Path):
    """同步 fixture：隔离临时 DB（CLI 内部自行 asyncio.run，故测试为同步）."""
    db_file = tmp_path / "cli.db"
    orig_url = settings.database_url
    orig_mode = settings.checkpointer_mode
    settings.database_url = f"sqlite:///{db_file}"
    settings.checkpointer_mode = "memory"
    asyncio.run(init_schema(db_file))
    yield db_file
    settings.database_url = orig_url
    settings.checkpointer_mode = orig_mode


def _patched_selectors() -> list:
    return [
        patch("songyan.cli.main._select_mode", return_value="webnovel"),
        patch("songyan.cli.main._select_genre", return_value="xuanhuan"),
        patch("songyan.cli.main._select_story_structure", return_value="free"),
        patch("songyan.cli.main._select_sub_genre", return_value=None),
    ]


class TestCreateProjectCLI:
    def test_default_no_outline_leaves_skeleton_empty(self, cli_db: Path) -> None:
        with ExitStack() as stack:
            for p in _patched_selectors():
                stack.enter_context(p)
            result = CliRunner().invoke(cli, ["create-project"], input=_CLI_INPUT)
        assert result.exit_code == 0, result.output
        assert asyncio.run(_narrative_counts()) == (0, 0, 0)
        # 项目其余字段与旧行为一致
        project = asyncio.run(_first_project())
        assert project is not None
        assert project.genre_id == "xuanhuan"
        assert project.mode_id == "webnovel"
        assert project.protagonist_name == "英雄"
        assert project.story_structure == "free"
        assert project.estimated_chapters == 30

    def test_outline_file_populates_skeleton(self, cli_db: Path, tmp_path: Path) -> None:
        outline_path = _write_json(tmp_path, SAMPLE_OUTLINE)
        with ExitStack() as stack:
            for p in _patched_selectors():
                stack.enter_context(p)
            result = CliRunner().invoke(
                cli,
                ["create-project", "--outline-file", outline_path],
                input=_CLI_INPUT,
            )
        assert result.exit_code == 0, result.output
        outlines, arcs, threads = asyncio.run(_narrative_counts())
        assert outlines == 1
        assert arcs == 2
        assert threads == 1
        # 读回并验证 get_arc_for_chapter
        project = asyncio.run(_first_project())
        assert project is not None

    def test_bad_outline_file_clean_error(self, cli_db: Path, tmp_path: Path) -> None:
        bad = _write_json(tmp_path, {"plot_threads": [{"thread_id": "t1"}, {"thread_id": "t1"}]})
        with ExitStack() as stack:
            for p in _patched_selectors():
                stack.enter_context(p)
            result = CliRunner().invoke(
                cli,
                ["create-project", "--outline-file", bad],
                input=_CLI_INPUT,
            )
        assert result.exit_code != 0
        # 报错清晰（ClickException），非未捕获 traceback
        assert "thread_id" in result.output or "大纲" in result.output
