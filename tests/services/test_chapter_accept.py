"""M4 步 2: chapter accept 写径（tech-m4 §5 步 2 / B2/B3/B5，task 239）.

TDD 切片（tasks/239-m4-step2-chapter-accept.md）：
1. 副作用路径：accept 后结算库零新行（九表）+ plan_* 五表快照不变；故障注入回滚。
2. 副本链：draft → accepted / picked → accepted / --from-file 三段链。
3. 拒绝路径：head 缺失 / current 为空 / 重复 accept（exit 2 且零写入）。
"""

from __future__ import annotations

from pathlib import Path
from unittest import mock

import pytest

from songyan.config import settings
from songyan.db.connection import get_db
from songyan.db.migrations import init_schema
from songyan.db.plan_fact_repo import PlanFactRepository
from songyan.db.repository import (
    ChapterHeadRepository,
    ChapterVersionRepository,
    ProjectRepository,
)
from songyan.models.chapter import ChapterHead, ChapterVersion
from songyan.models.plan_facts import (
    PlanAttribute,
    PlanEntity,
    PlanEvent,
    PlanTimeAnchor,
)
from songyan.models.project import ProjectSetting
from songyan.services.chapter_accept import (
    AlreadyAcceptedError,
    ChapterFileError,
    NothingToAcceptError,
    accept_chapter,
)
from songyan.utils.word_count import count_chinese_words

_PROJECT = "p-m4-accept"

# SettlementExtractor apply 写集（tech-m4 / task 239 TDD 切片 1）
_SETTLEMENT_TABLES = (
    "characters",
    "character_states",
    "numerical_ledgers",
    "setting_snapshots",
    "setting_tracking",
    "inventory_tracker",
    "location_tracker",
    "foreshadowings",
    "permanent_scenes",
)
# plan_* 五表（B3 精神：accept 零触碰）
_PLAN_TABLES = (
    "plan_entities",
    "plan_time_anchors",
    "plan_attributes",
    "plan_events",
    "plan_clues",
)

_EDITED_CONTENT = "编辑后的正文：陈照走出南站，雨停了。"
_DRAFT_CONTENT = "原始草稿：陈照走进南站。"


@pytest.fixture
async def accept_db(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    db_path = tmp_path / "m4-accept.db"
    monkeypatch.chdir(tmp_path)
    monkeypatch.setattr(settings, "database_url", f"sqlite:///{db_path}")
    await init_schema(db_path)
    await ProjectRepository().create(
        ProjectSetting(
            genre_id="mystery",
            mode_id="webnovel",
            protagonist_name="陈照",
            title="m4 accept",
        ),
        _PROJECT,
    )
    return db_path


async def _seed_plan_facts() -> None:
    """落一条 approved plan_* 数据，让快照断言非平凡。"""
    repo = PlanFactRepository()
    await repo.write_entity(
        PlanEntity(
            entity_id="ent-chen",
            project_id=_PROJECT,
            entity_type="person",
            aliases=["陈照"],
            approval_status="approved",
        )
    )
    await repo.write_attribute(
        PlanAttribute(
            attribute_id="attr-loc",
            project_id=_PROJECT,
            entity_id="ent-chen",
            key="location",
            value="南站",
            source="plan",
            approval_status="approved",
            valid_from_ch=1,
            valid_to_ch=5,
        )
    )
    await repo.write_time_anchor(
        PlanTimeAnchor(
            anchor_id="ta-1",
            project_id=_PROJECT,
            date="第一天黄昏",
            kind="story",
            approval_status="approved",
        )
    )
    await repo.write_event(
        PlanEvent(
            event_id="evt-1",
            project_id=_PROJECT,
            ch=1,
            time_anchor_id="ta-1",
            participants=["ent-chen"],
            causes=[],
            reveals_evidence=[],
            claims=[],
            approval_status="approved",
        )
    )


async def _seed_draft(chapter: int = 1, version_id: str = "v-draft-1") -> ChapterVersion:
    version = ChapterVersion(
        version_id=version_id,
        project_id=_PROJECT,
        chapter_number=chapter,
        version_number=1,
        version_type="draft",
        content=_DRAFT_CONTENT,
        word_count=count_chinese_words(_DRAFT_CONTENT),
    )
    await ChapterVersionRepository().create(version)
    return version


async def _seed_head(
    chapter: int = 1,
    *,
    current: str | None = "v-draft-1",
    status: str = "draft",
) -> None:
    await ChapterHeadRepository().update(
        ChapterHead(
            project_id=_PROJECT,
            chapter_number=chapter,
            current_version_id=current,
            accepted_version_id=None,
            status=status,
        )
    )


async def _table_counts(tables: tuple[str, ...]) -> dict[str, int]:
    async with get_db() as conn:
        out: dict[str, int] = {}
        for table in tables:
            cursor = await conn.execute(f"SELECT COUNT(*) FROM {table}")
            row = await cursor.fetchone()
            assert row is not None
            out[table] = int(row[0])
    return out


async def _plan_status_snapshot() -> dict[str, dict[str, int]]:
    """plan_* 五表按 approval_status 分组计数（pending 行数 + approved 集锁死）。"""
    async with get_db() as conn:
        out: dict[str, dict[str, int]] = {}
        for table in _PLAN_TABLES:
            cursor = await conn.execute(
                f"SELECT approval_status, COUNT(*) FROM {table} GROUP BY approval_status"
            )
            rows = await cursor.fetchall()
            out[table] = {str(r[0]): int(r[1]) for r in rows}
    return out


# --- 切片 1：副作用路径（零新行 + 故障注入回滚） -------------------------


async def test_accept_writes_no_settlement_rows_and_plan_snapshot_unchanged(
    accept_db: Path,
) -> None:
    """B5 锁死：accept 事务只动 chapter_versions + chapter_heads；结算九表零新行。"""
    await _seed_plan_facts()
    draft = await _seed_draft()
    await _seed_head(current=draft.version_id)

    settlement_before = await _table_counts(_SETTLEMENT_TABLES)
    plan_before = await _plan_status_snapshot()

    outcome = await accept_chapter(_PROJECT, 1)

    assert outcome.accepted_version_id != draft.version_id
    settlement_after = await _table_counts(_SETTLEMENT_TABLES)
    plan_after = await _plan_status_snapshot()
    assert settlement_after == settlement_before
    for table in _SETTLEMENT_TABLES:
        assert settlement_after[table] == settlement_before[table]
    assert plan_after == plan_before
    # approved 集不被触碰（非空快照，锁死的是「不变」而非「全空」）
    assert plan_after["plan_entities"].get("approved") == 1


async def test_head_update_failure_rolls_back_all_writes(accept_db: Path) -> None:
    """故障注入：head.update 抛错 → chapter_versions 无新行、chapter_heads 原状。"""
    draft = await _seed_draft()
    await _seed_head(current=draft.version_id)

    async def _boom(self: ChapterHeadRepository, *args: object, **kwargs: object) -> None:
        raise RuntimeError("injected head update failure")

    with mock.patch.object(ChapterHeadRepository, "update", _boom):
        with pytest.raises(RuntimeError, match="injected head update failure"):
            await accept_chapter(_PROJECT, 1)

    versions = await ChapterVersionRepository().list_by_chapter(_PROJECT, 1)
    assert [v.version_id for v in versions] == [draft.version_id]
    head = await ChapterHeadRepository().get(_PROJECT, 1)
    assert head is not None
    assert head.current_version_id == draft.version_id
    assert head.accepted_version_id is None
    assert head.status == "draft"


# --- 切片 2：副本链 ------------------------------------------------------


async def test_draft_accept_appends_copy_and_moves_head(accept_db: Path) -> None:
    """draft → accepted：parent 链、version_number 递增、原稿 version_type 不变。"""
    draft = await _seed_draft()
    await _seed_head(current=draft.version_id)

    outcome = await accept_chapter(_PROJECT, 1)

    assert outcome.source_version_id == draft.version_id
    assert outcome.edited_version_id is None
    original = await ChapterVersionRepository().get(draft.version_id)
    assert original is not None
    assert original.version_type == "draft"
    accepted = await ChapterVersionRepository().get(outcome.accepted_version_id)
    assert accepted is not None
    assert accepted.version_type == "accepted"
    assert accepted.parent_version_id == draft.version_id
    assert accepted.version_number == draft.version_number + 1
    assert accepted.content == draft.content
    head = await ChapterHeadRepository().get(_PROJECT, 1)
    assert head is not None
    assert head.current_version_id == outcome.accepted_version_id
    assert head.accepted_version_id == outcome.accepted_version_id
    assert head.status == "accepted"


async def test_picked_working_draft_accepted(accept_db: Path) -> None:
    """picked 语义 = head.current 指向工作稿；accept 对其走同一副本链（B2）。"""
    draft = await _seed_draft()
    await _seed_head(current=draft.version_id, status="draft")

    outcome = await accept_chapter(_PROJECT, 1)

    accepted = await ChapterVersionRepository().get(outcome.accepted_version_id)
    assert accepted is not None
    assert accepted.parent_version_id == draft.version_id
    assert accepted.version_type == "accepted"


async def test_from_file_materializes_edited_then_accepts(accept_db: Path) -> None:
    """--from-file 三段链 draft → edited → accepted；edited 行 word_count 按文件实算。"""
    draft = await _seed_draft()
    await _seed_head(current=draft.version_id)
    edit_file = accept_db.parent / "edit.txt"
    edit_file.write_text(_EDITED_CONTENT, encoding="utf-8")

    outcome = await accept_chapter(_PROJECT, 1, from_file=edit_file)

    assert outcome.edited_version_id is not None
    assert outcome.source_version_id == outcome.edited_version_id
    expected_wc = count_chinese_words(_EDITED_CONTENT)
    assert outcome.word_count == expected_wc

    edited = await ChapterVersionRepository().get(outcome.edited_version_id)
    assert edited is not None
    assert edited.version_type == "edited"
    assert edited.parent_version_id == draft.version_id
    assert edited.content == _EDITED_CONTENT
    assert edited.word_count == expected_wc
    assert edited.version_number == draft.version_number + 1

    accepted = await ChapterVersionRepository().get(outcome.accepted_version_id)
    assert accepted is not None
    assert accepted.version_type == "accepted"
    assert accepted.parent_version_id == edited.version_id
    assert accepted.version_number == edited.version_number + 1
    assert accepted.content == _EDITED_CONTENT
    assert accepted.word_count == expected_wc

    head = await ChapterHeadRepository().get(_PROJECT, 1)
    assert head is not None
    assert head.current_version_id == outcome.accepted_version_id
    assert head.status == "accepted"


async def test_from_file_version_numbers_use_same_connection_max(accept_db: Path) -> None:
    """edited 物化与 accepted 副本共用同一 conn 的 MAX+1 口径（连续编号 1/2/3）。"""
    draft = await _seed_draft()
    await _seed_head(current=draft.version_id)
    edit_file = accept_db.parent / "edit.txt"
    edit_file.write_text(_EDITED_CONTENT, encoding="utf-8")

    outcome = await accept_chapter(_PROJECT, 1, from_file=edit_file)

    versions = await ChapterVersionRepository().list_by_chapter(_PROJECT, 1)
    assert [(v.version_number, v.version_type) for v in versions] == [
        (1, "draft"),
        (2, "edited"),
        (3, "accepted"),
    ]
    assert outcome.edited_version_id is not None


async def test_from_file_empty_rejects_with_no_writes(accept_db: Path) -> None:
    """文件为空 → ChapterFileError（exit 1 语义），零写入。"""
    draft = await _seed_draft()
    await _seed_head(current=draft.version_id)
    edit_file = accept_db.parent / "edit.txt"
    edit_file.write_text("   \n", encoding="utf-8")

    with pytest.raises(ChapterFileError):
        await accept_chapter(_PROJECT, 1, from_file=edit_file)

    versions = await ChapterVersionRepository().list_by_chapter(_PROJECT, 1)
    assert [v.version_id for v in versions] == [draft.version_id]
    head = await ChapterHeadRepository().get(_PROJECT, 1)
    assert head is not None
    assert head.status == "draft"


async def test_from_file_missing_rejects(accept_db: Path) -> None:
    """文件读失败 → ChapterFileError（exit 1 语义），零写入。"""
    draft = await _seed_draft()
    await _seed_head(current=draft.version_id)

    with pytest.raises(ChapterFileError):
        await accept_chapter(_PROJECT, 1, from_file=accept_db.parent / "nope.txt")

    versions = await ChapterVersionRepository().list_by_chapter(_PROJECT, 1)
    assert [v.version_id for v in versions] == [draft.version_id]


# --- 切片 3：拒绝路径（exit 2 且零写入） ---------------------------------


async def test_missing_head_rejects_with_no_writes(accept_db: Path) -> None:
    """head 行不存在 → NothingToAcceptError（exit 2）；upsert 不得静默建新 head。"""
    with pytest.raises(NothingToAcceptError) as exc_info:
        await accept_chapter(_PROJECT, 1)
    assert exc_info.value.exit_code == 2

    head = await ChapterHeadRepository().get(_PROJECT, 1)
    assert head is None
    versions = await ChapterVersionRepository().list_by_chapter(_PROJECT, 1)
    assert versions == []


async def test_head_without_current_version_rejects(accept_db: Path) -> None:
    """head 存在但 current_version_id 为空 → 另一种 exit 2（无可确认稿）。"""
    await _seed_head(current=None)

    with pytest.raises(NothingToAcceptError) as exc_info:
        await accept_chapter(_PROJECT, 1)
    assert exc_info.value.exit_code == 2

    head = await ChapterHeadRepository().get(_PROJECT, 1)
    assert head is not None
    assert head.current_version_id is None
    assert head.accepted_version_id is None


async def test_repeat_accept_is_idempotent_reject(accept_db: Path) -> None:
    """重复 accept → AlreadyAcceptedError（exit 2 幂等提示），不产生新版本。"""
    draft = await _seed_draft()
    await _seed_head(current=draft.version_id)
    first = await accept_chapter(_PROJECT, 1)

    with pytest.raises(AlreadyAcceptedError) as exc_info:
        await accept_chapter(_PROJECT, 1)
    assert exc_info.value.exit_code == 2

    versions = await ChapterVersionRepository().list_by_chapter(_PROJECT, 1)
    assert [v.version_id for v in versions] == [draft.version_id, first.accepted_version_id]
    head = await ChapterHeadRepository().get(_PROJECT, 1)
    assert head is not None
    assert head.accepted_version_id == first.accepted_version_id
