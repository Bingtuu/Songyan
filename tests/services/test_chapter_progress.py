"""M4 步 1: 章进度视图推导 + 服务组装（tech-m4 §5 步 1 / B1 / task 238）."""

from __future__ import annotations

from datetime import datetime
from pathlib import Path

import pytest

from songyan.config import settings
from songyan.db.chapter_variant_repo import ChapterVariantRepository
from songyan.db.connection import get_db
from songyan.db.migrations import init_schema
from songyan.db.repository import (
    ChapterHeadRepository,
    ChapterVersionRepository,
    ContextSnapshotRepository,
    ProjectRepository,
)
from songyan.models.chapter import ChapterHead, ChapterVersion
from songyan.models.chapter_progress import (
    ChapterProgressState,
    derive_chapter_progress,
)
from songyan.models.context import ContextSnapshot
from songyan.models.project import ProjectSetting
from songyan.models.variant import ChapterVariant, VariantStatus
from songyan.services.chapter_progress import (
    load_chapter_progress,
    load_context_emergency,
)

_PROJECT = "p-m4-progress"
_TS = "2026-11-08T00:00:00Z"

_READ_TABLES = (
    "chapter_heads",
    "chapter_variants",
    "chapter_versions",
    "context_snapshots",
)


def _head(
    chapter: int,
    *,
    current: str | None = None,
    accepted: str | None = None,
    stale: int = 0,
) -> ChapterHead:
    return ChapterHead(
        project_id=_PROJECT,
        chapter_number=chapter,
        current_version_id=current,
        accepted_version_id=accepted,
        content_stale=stale,
    )


def _variant(
    chapter: int,
    slot: int,
    status: VariantStatus = "generated",
    *,
    project_id: str = _PROJECT,
) -> ChapterVariant:
    return ChapterVariant(
        variant_id=f"var-{project_id}-{chapter}-{slot}",
        project_id=project_id,
        chapter_number=chapter,
        slot_index=slot,
        status=status,
        parent_canon_fingerprint="fp-test",
        content_ref=f"v-{chapter}-{slot}",
        created_at=_TS,
        updated_at=_TS,
    )


def _version(chapter: int, version_number: int = 1) -> ChapterVersion:
    return ChapterVersion(
        version_id=f"v-{_PROJECT}-{chapter}-{version_number}",
        project_id=_PROJECT,
        chapter_number=chapter,
        version_number=version_number,
        version_type="draft",
        content=f"第{chapter}章草稿",
    )


@pytest.fixture
async def progress_db(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    db_path = tmp_path / "m4-progress.db"
    monkeypatch.chdir(tmp_path)
    monkeypatch.setattr(settings, "database_url", f"sqlite:///{db_path}")
    await init_schema(db_path)
    await ProjectRepository().create(
        ProjectSetting(
            genre_id="mystery",
            mode_id="webnovel",
            protagonist_name="陈照",
            title="m4 progress",
        ),
        _PROJECT,
    )
    return db_path


async def _write_head(head: ChapterHead) -> None:
    await ChapterHeadRepository().update(head)


async def _write_variant(variant: ChapterVariant) -> None:
    await ChapterVariantRepository().insert(variant)


async def _write_version(version: ChapterVersion) -> None:
    await ChapterVersionRepository().create(version)


async def _write_snapshot(
    chapter: int,
    snapshot_id: str,
    *,
    emergency: bool,
    budget_before: float | None = None,
    created_at: datetime | None = None,
) -> None:
    await ContextSnapshotRepository().create(
        ContextSnapshot(
            snapshot_id=snapshot_id,
            project_id=_PROJECT,
            chapter_number=chapter,
            budget_used=1.0,
            context_emergency=emergency,
            context_emergency_level=2 if emergency else 0,
            budget_used_before_emergency=budget_before,
            created_at=created_at or datetime(2026, 11, 8),
        )
    )


async def _table_counts() -> dict[str, int]:
    async with get_db() as conn:
        out: dict[str, int] = {}
        for table in _READ_TABLES:
            cursor = await conn.execute(f"SELECT COUNT(*) FROM {table}")
            row = await cursor.fetchone()
            assert row is not None
            out[table] = int(row[0])
    return out


# --- 切片 1: 纯函数真值表（六态 + 优先级 + 边角） -------------------------


@pytest.mark.parametrize(
    ("head", "variants", "has_version", "expected"),
    [
        # accepted 系两态吸收所有 accepted 章（无论槽 / 工作稿）
        (
            _head(1, accepted="v-a", stale=1),
            [],
            True,
            ChapterProgressState.STALE,
        ),
        (
            _head(1, accepted="v-a"),
            [_variant(1, 1), _variant(1, 2, "picked")],
            True,
            ChapterProgressState.SETTLED,
        ),
        # accepted 章再有 generated 槽 → 仍 settled（优先级：accepted 系最高）
        (
            _head(1, accepted="v-a"),
            [_variant(1, 1)],
            False,
            ChapterProgressState.SETTLED,
        ),
        # 未 accepted：picked 槽优先于 generated 槽
        (
            _head(2, current="v-w"),
            [_variant(2, 1), _variant(2, 2, "picked")],
            True,
            ChapterProgressState.PICKED,
        ),
        # 未 accepted、无 picked、存在活动 generated 槽
        (
            _head(2, current="v-w"),
            [_variant(2, 1), _variant(2, 2)],
            True,
            ChapterProgressState.VARIANTS_READY,
        ),
        # 无 head 有 variant（variant generate 不写 head）→ 章仍可达
        (
            None,
            [_variant(2, 1)],
            True,
            ChapterProgressState.VARIANTS_READY,
        ),
        # abandoned / archived 槽不算活动槽
        (
            _head(2, current="v-w"),
            [_variant(2, 1, "abandoned"), _variant(2, 2, "archived")],
            True,
            ChapterProgressState.DRAFTING,
        ),
        # 未 accepted、无活动 variant：head 工作指针非空 → drafting
        (
            _head(3, current="v-w"),
            [],
            False,
            ChapterProgressState.DRAFTING,
        ),
        # 无 head：版本表有该章行 → drafting
        (None, [], True, ChapterProgressState.DRAFTING),
        # 双指针 NULL 罕见行：head 存在、无版本、无 variant → empty
        (
            _head(4),
            [],
            False,
            ChapterProgressState.EMPTY,
        ),
        # 无 head 无版本无 variant → empty
        (None, [], False, ChapterProgressState.EMPTY),
    ],
)
def test_derive_chapter_progress_truth_table(
    head: ChapterHead | None,
    variants: list[ChapterVariant],
    has_version: bool,
    expected: ChapterProgressState,
) -> None:
    assert derive_chapter_progress(head, variants, has_version=has_version) == expected


def test_progress_states_cover_six() -> None:
    states = {state.value for state in ChapterProgressState}
    assert states == {
        "stale",
        "settled",
        "picked",
        "variants_ready",
        "drafting",
        "empty",
    }


# --- 切片 2: 服务组装（章宇宙三源并集 + 分布计数） ------------------------


async def test_load_chapter_progress_universe_and_distribution(
    progress_db: Path,
) -> None:
    # ch1: accepted + content_stale → stale
    await _write_version(_version(1, 1))
    await _write_head(_head(1, accepted="v-p-m4-progress-1-1", current="v-p-m4-progress-1-1"))
    await ChapterHeadRepository().mark_content_stale(_PROJECT, [1])
    # ch2: 无 head，两个 generated 槽（+版本行）→ variants_ready
    await _write_variant(_variant(2, 1))
    await _write_variant(_variant(2, 2))
    await _write_version(_version(2, 1))
    await _write_version(_version(2, 2))
    # ch3: head 工作指针 → drafting
    await _write_version(_version(3, 1))
    await _write_head(_head(3, current="v-p-m4-progress-3-1"))
    # ch4: 双指针 NULL 罕见行 → empty
    await _write_head(_head(4))
    # ch5: picked 槽（未 accepted）→ picked
    await _write_version(_version(5, 1))
    await _write_head(_head(5, current="v-p-m4-progress-5-1"))
    await _write_variant(_variant(5, 1, "picked"))
    # ch7: 仅版本表有行（无 head、无 variant）→ drafting；章号不连续
    await _write_version(_version(7, 1))

    before = await _table_counts()
    summary = await load_chapter_progress(_PROJECT)
    after = await _table_counts()

    # 章宇宙 = heads ∪ variants ∪ versions 的章号并集；不虚构 1..max
    assert [entry.chapter_number for entry in summary.chapters] == [1, 2, 3, 4, 5, 7]
    by_chapter = {entry.chapter_number: entry.state for entry in summary.chapters}
    assert by_chapter[1] == ChapterProgressState.STALE
    assert by_chapter[2] == ChapterProgressState.VARIANTS_READY
    assert by_chapter[3] == ChapterProgressState.DRAFTING
    assert by_chapter[4] == ChapterProgressState.EMPTY
    assert by_chapter[5] == ChapterProgressState.PICKED
    assert by_chapter[7] == ChapterProgressState.DRAFTING

    assert summary.distribution == {
        ChapterProgressState.STALE: 1,
        ChapterProgressState.SETTLED: 0,
        ChapterProgressState.PICKED: 1,
        ChapterProgressState.VARIANTS_READY: 1,
        ChapterProgressState.DRAFTING: 2,
        ChapterProgressState.EMPTY: 1,
    }
    assert summary.pending_confirm == 1
    # B1 口径：第一个非 accepted 章
    assert summary.next_chapter == 2
    assert summary.next_state == ChapterProgressState.VARIANTS_READY
    assert after == before


async def test_load_chapter_progress_all_accepted_has_no_next(
    progress_db: Path,
) -> None:
    await _write_version(_version(1, 1))
    await _write_version(_version(2, 1))
    await _write_head(_head(1, accepted="v-p-m4-progress-1-1", current="v-p-m4-progress-1-1"))
    await _write_head(_head(2, accepted="v-p-m4-progress-2-1", current="v-p-m4-progress-2-1"))

    summary = await load_chapter_progress(_PROJECT)

    assert summary.next_chapter is None
    assert summary.next_state is None
    assert summary.pending_confirm == 0
    assert summary.distribution[ChapterProgressState.SETTLED] == 2


async def test_load_chapter_progress_empty_project(progress_db: Path) -> None:
    summary = await load_chapter_progress(_PROJECT)

    assert summary.chapters == []
    assert summary.pending_confirm == 0
    assert summary.next_chapter is None
    assert summary.next_state is None
    assert all(count == 0 for count in summary.distribution.values())


# --- 切片 3: repo 只读查询 ----------------------------------------------


async def test_context_snapshot_list_by_project_maps_emergency_fields(
    progress_db: Path,
) -> None:
    await _write_snapshot(3, "snap-3", emergency=True, budget_before=0.35)
    await _write_snapshot(4, "snap-4", emergency=False)
    await _write_snapshot(
        5,
        "snap-5",
        emergency=True,
        budget_before=0.8,
        created_at=datetime(2026, 11, 9),
    )

    rows = await ContextSnapshotRepository().list_by_project(_PROJECT)

    assert [row.snapshot_id for row in rows] == ["snap-3", "snap-4", "snap-5"]
    assert rows[0].context_emergency is True
    assert rows[0].context_emergency_level == 2
    assert rows[0].budget_used_before_emergency == 0.35
    assert rows[1].context_emergency is False
    assert rows[2].budget_used_before_emergency == 0.8


async def test_context_snapshot_list_by_project_filters_other_project(
    progress_db: Path,
) -> None:
    other = "p-m4-progress-other"
    await ProjectRepository().create(
        ProjectSetting(
            genre_id="mystery",
            mode_id="webnovel",
            protagonist_name="陈照",
            title="other",
        ),
        other,
    )
    await _write_snapshot(1, "snap-own", emergency=True, budget_before=0.1)
    await ContextSnapshotRepository().create(
        ContextSnapshot(
            snapshot_id="snap-other",
            project_id=other,
            chapter_number=9,
            context_emergency=True,
            budget_used_before_emergency=9.9,
            created_at=datetime(2026, 11, 9),
        )
    )

    rows = await ContextSnapshotRepository().list_by_project(_PROJECT)

    assert [row.snapshot_id for row in rows] == ["snap-own"]
    assert rows[0].chapter_number == 1


async def test_context_snapshot_list_by_project_no_rows(progress_db: Path) -> None:
    assert await ContextSnapshotRepository().list_by_project(_PROJECT) == []


async def test_context_emergency_summary_aggregates_latest(
    progress_db: Path,
) -> None:
    await _write_snapshot(3, "snap-3", emergency=True, budget_before=0.35)
    await _write_snapshot(4, "snap-4", emergency=False)
    await _write_snapshot(
        5,
        "snap-5",
        emergency=True,
        budget_before=0.8,
        created_at=datetime(2026, 11, 9),
    )

    summary = await load_context_emergency(_PROJECT)

    assert summary.count == 2
    assert summary.last_chapter == 5
    assert summary.budget_used_before == 0.8


async def test_context_emergency_summary_no_records(progress_db: Path) -> None:
    summary = await load_context_emergency(_PROJECT)

    assert summary.count == 0
    assert summary.last_chapter is None
    assert summary.budget_used_before is None


async def test_variant_list_by_project_orders_and_filters(
    progress_db: Path,
) -> None:
    await _write_variant(_variant(5, 2, "generated"))
    await _write_variant(_variant(2, 1, "generated"))
    await _write_variant(_variant(2, 2, "picked"))
    await _write_variant(_variant(2, 3, "abandoned"))
    await _write_variant(_variant(9, 1, "generated", project_id="p-other"))

    rows = await ChapterVariantRepository().list_by_project(_PROJECT)

    assert [(row.chapter_number, row.slot_index, row.status) for row in rows] == [
        (2, 1, "generated"),
        (2, 2, "picked"),
        (2, 3, "abandoned"),
        (5, 2, "generated"),
    ]


async def test_variant_list_by_project_no_rows(progress_db: Path) -> None:
    assert await ChapterVariantRepository().list_by_project(_PROJECT) == []
