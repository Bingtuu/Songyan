"""task 252：故事线切片指纹（纯函数稳定性 + loader 切片选择）。

切片组成：全书 story_outlines 行 + 覆盖本章的 arcs + 相关 threads（三条件并集）。
字段白名单见 docs/tech-m4-followup-s5.md §3.2。
"""

from __future__ import annotations

from datetime import datetime
from pathlib import Path

import pytest

from songyan.models.narrative import ArcPlan, PlotThread, StoryOutline
from songyan.services.storyline_fingerprint import (
    load_storyline_slice,
    storyline_fingerprint_from_parts,
)


def _outline(**kw) -> StoryOutline:
    return StoryOutline(project_id="p1", **kw)


def _arc(start: int, end: int, **kw) -> ArcPlan:
    return ArcPlan(
        arc_id=kw.pop("arc_id", f"arc-{start}-{end}"),
        project_id="p1",
        arc_index=kw.pop("arc_index", 0),
        start_chapter=start,
        end_chapter=end,
        **kw,
    )


def _thread(**kw) -> PlotThread:
    return PlotThread(thread_id=kw.pop("thread_id", "t-1"), project_id="p1", **kw)


class TestStableDigest:
    def test_order_independent(self) -> None:
        arcs = [_arc(1, 10, arc_id="a"), _arc(11, 20, arc_id="b", arc_index=1)]
        threads = [_thread(thread_id="t1"), _thread(thread_id="t2")]
        fp1 = storyline_fingerprint_from_parts(
            outline=_outline(), arcs=arcs, threads=threads
        )
        fp2 = storyline_fingerprint_from_parts(
            outline=_outline(),
            arcs=list(reversed(arcs)),
            threads=list(reversed(threads)),
        )
        assert fp1 == fp2

    def test_none_outline_stable(self) -> None:
        fp1 = storyline_fingerprint_from_parts(outline=None, arcs=[], threads=[])
        fp2 = storyline_fingerprint_from_parts(outline=None, arcs=[], threads=[])
        assert fp1 == fp2


class TestFieldWhitelist:
    def test_outline_timestamp_ignored(self) -> None:
        a = _outline(core_conflict="A")
        b = a.model_copy(update={"updated_at": datetime(2030, 1, 1)})
        assert storyline_fingerprint_from_parts(outline=a, arcs=[], threads=[]) == (
            storyline_fingerprint_from_parts(outline=b, arcs=[], threads=[])
        )

    def test_thread_audit_fields_ignored(self) -> None:
        """last_status_version_id / created_at 不进指纹。"""
        a = _thread(thread_id="t", status="opened", opened_chapter=1)
        b = a.model_copy(update={"last_status_version_id": "v-x"})
        fp_a = storyline_fingerprint_from_parts(outline=None, arcs=[], threads=[a])
        fp_b = storyline_fingerprint_from_parts(outline=None, arcs=[], threads=[b])
        assert fp_a == fp_b

    def test_whitelisted_field_changes_digest(self) -> None:
        assert storyline_fingerprint_from_parts(
            outline=_outline(core_conflict="A"), arcs=[], threads=[]
        ) != storyline_fingerprint_from_parts(
            outline=_outline(core_conflict="B"), arcs=[], threads=[]
        )
        assert storyline_fingerprint_from_parts(
            outline=None, arcs=[_arc(1, 10, arc_goal="X")], threads=[]
        ) != storyline_fingerprint_from_parts(
            outline=None, arcs=[_arc(1, 10, arc_goal="Y")], threads=[]
        )
        assert storyline_fingerprint_from_parts(
            outline=None, arcs=[], threads=[_thread(thread_id="t", status="planned")]
        ) != storyline_fingerprint_from_parts(
            outline=None,
            arcs=[],
            threads=[_thread(thread_id="t", status="opened", opened_chapter=1)],
        )
        # 弧边界字段进指纹
        assert storyline_fingerprint_from_parts(
            outline=None, arcs=[_arc(1, 5)], threads=[]
        ) != storyline_fingerprint_from_parts(
            outline=None, arcs=[_arc(1, 6)], threads=[]
        )


@pytest.fixture
async def slice_db(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> str:
    import songyan.db.connection as conn_mod
    from songyan.db.migrations import init_schema
    from songyan.db.repository import ProjectRepository
    from songyan.models import ProjectSetting

    db_path = tmp_path / "storyline.db"
    monkeypatch.setattr(
        conn_mod,
        "settings",
        type("S", (), {"database_url": f"sqlite:///{db_path}"})(),
    )
    await init_schema(db_path)
    await ProjectRepository().create(
        ProjectSetting(
            genre_id="mystery",
            mode_id="webnovel",
            protagonist_name="陈照",
        ),
        "p1",
    )
    return "p1"


class TestLoaderSlice:
    async def test_covering_arc_selection(self, slice_db: str) -> None:
        from songyan.db.narrative_repo import NarrativeRepository

        repo = NarrativeRepository()
        await repo.add_arc_plan(
            ArcPlan(
                arc_id="near",
                project_id="p1",
                arc_index=0,
                start_chapter=1,
                end_chapter=10,
                arc_goal="近弧",
            )
        )
        await repo.add_arc_plan(
            ArcPlan(
                arc_id="far",
                project_id="p1",
                arc_index=1,
                start_chapter=11,
                end_chapter=20,
                arc_goal="远弧",
            )
        )
        _, arcs5, _ = await load_storyline_slice("p1", 5)
        assert [a.arc_id for a in arcs5] == ["near"]
        _, arcs15, _ = await load_storyline_slice("p1", 15)
        assert [a.arc_id for a in arcs15] == ["far"]

    async def test_thread_relevance_union(self, slice_db: str) -> None:
        from songyan.db.narrative_repo import NarrativeRepository

        repo = NarrativeRepository()
        await repo.add_arc_plan(
            ArcPlan(
                arc_id="a0",
                project_id="p1",
                arc_index=0,
                start_chapter=1,
                end_chapter=10,
                arc_goal="弧",
                threads_to_open=["t-arc"],
                threads_to_resolve=[],
            )
        )
        await repo.add_thread(
            PlotThread(thread_id="t-arc", project_id="p1", title="弧引用")
        )
        await repo.add_thread(
            PlotThread(
                thread_id="t-opened",
                project_id="p1",
                title="已开启",
                opened_chapter=3,
            )
        )
        await repo.add_thread(
            PlotThread(
                thread_id="t-resolve-here",
                project_id="p1",
                title="本章弧收束",
                expected_resolve_arc=0,
            )
        )
        await repo.add_thread(
            PlotThread(thread_id="t-far", project_id="p1", title="远弧收束")
        )
        await repo.add_thread(
            PlotThread(
                thread_id="t-irrelevant",
                project_id="p1",
                title="无关联",
                expected_resolve_arc=7,  # 不存在的弧
            )
        )
        _, _, threads = await load_storyline_slice("p1", 5)
        ids = {t.thread_id for t in threads}
        assert {"t-arc", "t-opened", "t-resolve-here"} <= ids
        assert "t-irrelevant" not in ids
