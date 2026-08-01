"""Task 172c.q — wuxia 物品追踪语义补强（变体归一 / 非物品过滤 / 消耗流转）.

覆盖修复文档 tasks/172c.q-wuxia-inventory-identity.md §4：
- 基底名身份匹配：状态变体（「断刀（濒临碎裂）」/「断刀（裂纹上百道）」）归一为
  同一物理物品，命中刷新不新建；「断刀门刀谱」不被「断刀」吞并
- 非物品碎片过滤：基底名 >10 字拒绝登记
- 消耗状态流转：消耗标记条目 status='consumed'，不再计 forgotten
"""

from __future__ import annotations

import importlib.util
import sys
from pathlib import Path

from songyan.agents.continuity_auditor._scanners import _find_forgotten_items
from songyan.agents.settlement_extractor._apply import _update_continuity_tracking
from songyan.db.connection import get_db
from songyan.db.continuity_repo import (
    InventoryTrackerRepository,
    LocationTrackerRepository,
    SettingTrackingRepository,
)
from songyan.db.repository import (
    ChapterHeadRepository,
    ChapterVersionRepository,
    ProjectRepository,
)
from songyan.db.settlement_repo import ForeshadowingRepository
from songyan.models import (
    ChapterHead,
    ChapterVersion,
    CharacterUpdate,
    ProjectSetting,
    StateSettlement,
)

_PID = "p172cq"


async def _ensure_project(pid: str) -> None:
    if await ProjectRepository().get(pid) is None:
        await ProjectRepository().create(
            ProjectSetting(genre_id="wuxia", protagonist_name="沈孤鸿"), pid
        )


def _inv_settlement(new_value: str, character_id: str = "char-1") -> StateSettlement:
    return StateSettlement(
        character_updates=[
            CharacterUpdate(
                character_id=character_id,
                field="inventory",
                old_value="",
                new_value=new_value,
                source_quote="",
            )
        ]
    )


async def _apply(pid: str, chapter: int, settlement: StateSettlement) -> None:
    await _ensure_project(pid)
    async with get_db() as conn:
        await _update_continuity_tracking(
            settlement=settlement,
            project_id=pid,
            chapter_number=chapter,
            version_id=f"{pid}-v{chapter}",
            setting_tracking_repo=SettingTrackingRepository(),
            inventory_repo=InventoryTrackerRepository(),
            location_repo=LocationTrackerRepository(),
            foreshadowing_repo=ForeshadowingRepository(),
            conn=conn,
        )
        await conn.commit()


async def _make_accepted(pid: str, chapter: int, content: str) -> None:
    await _ensure_project(pid)
    version = ChapterVersion(
        version_id=f"{pid}-v{chapter}",
        project_id=pid,
        chapter_number=chapter,
        version_type="accepted",
        content=content,
        word_count=len(content),
    )
    await ChapterVersionRepository().create(version)
    await ChapterHeadRepository().update(
        ChapterHead(
            project_id=pid,
            chapter_number=chapter,
            current_version_id=version.version_id,
            accepted_version_id=version.version_id,
            status="accepted",
        )
    )


class TestBaseNameIdentity:
    """§4 基底名匹配（测试 1-4）."""

    async def test_state_variant_refreshes_same_item(self, test_db: Path) -> None:
        """状态变体归一：刷新不新建；item_name 保持首登名."""
        await _apply(_PID, 1, _inv_settlement("断刀（濒临碎裂）"))
        await _apply(_PID, 3, _inv_settlement("断刀（裂纹上百道，刀身濒临断裂）"))

        rows = await InventoryTrackerRepository().list_by_project(_PID)
        assert len(rows) == 1
        assert rows[0]["item_name"] == "断刀（濒临碎裂）"
        assert rows[0]["last_used_chapter"] == 3
        assert rows[0]["acquired_in_chapter"] == 1

    async def test_compound_item_not_swallowed_by_prefix(self, test_db: Path) -> None:
        """「断刀门刀谱」不被「断刀」吞并（双向）."""
        await _apply(_PID, 1, _inv_settlement("断刀"))
        await _apply(_PID, 2, _inv_settlement("断刀门刀谱"))

        rows = await InventoryTrackerRepository().list_by_project(_PID)
        assert {r["item_name"] for r in rows} == {"断刀", "断刀门刀谱"}

        pid2 = f"{_PID}-reverse"
        await _apply(pid2, 1, _inv_settlement("断刀门刀谱"))
        await _apply(pid2, 2, _inv_settlement("断刀"))
        rows2 = await InventoryTrackerRepository().list_by_project(pid2)
        assert {r["item_name"] for r in rows2} == {"断刀", "断刀门刀谱"}

    async def test_short_base_name_no_base_matching(self, test_db: Path) -> None:
        """短名保护：基底名 len<2 不参与基底名匹配."""
        pid = f"{_PID}-short"
        repo = InventoryTrackerRepository()
        await _ensure_project(pid)
        await repo.create(
            track_id="legacy-dao",
            project_id=pid,
            character_id="char-1",
            item_name="刀",
            item_description="",
            acquired_in_chapter=1,
        )
        await _apply(pid, 3, _inv_settlement("刀（刀身泛幽蓝色光，似淬毒）"))

        rows = await repo.list_by_project(pid)
        assert len(rows) == 2
        assert rows[0]["last_used_chapter"] == 1  # legacy「刀」未被误刷新

    async def test_single_item_value_unchanged(self, test_db: Path) -> None:
        """xuanhuan/scifi 单物品短值路径行为不变（回归保护）."""
        await _apply(_PID, 2, _inv_settlement("九转玄丹"))
        await _apply(_PID, 5, _inv_settlement("九转玄丹"))

        rows = await InventoryTrackerRepository().list_by_project(_PID)
        assert len(rows) == 1
        assert rows[0]["item_name"] == "九转玄丹"
        assert rows[0]["last_used_chapter"] == 5


class TestFragmentFilter:
    """§4 碎片过滤（测试 5-6）."""

    async def test_sentence_fragment_rejected(self, test_db: Path) -> None:
        """基底名 13 字的叙述句碎片 → 拒绝登记."""
        await _apply(_PID, 1, _inv_settlement("透出一丝不属于这个世界的微光"))
        await _apply(_PID, 2, _inv_settlement("刀柄上三寸铁片裂开一道细纹"))

        rows = await InventoryTrackerRepository().list_by_project(_PID)
        assert rows == []

    async def test_boundary_length_item_accepted(self, test_db: Path) -> None:
        """「密室三把钥匙之一」（8 字）正常登记（边界保护）."""
        await _apply(_PID, 1, _inv_settlement("密室三把钥匙之一（圆形锁孔钥匙）"))

        rows = await InventoryTrackerRepository().list_by_project(_PID)
        assert len(rows) == 1
        assert rows[0]["item_name"] == "密室三把钥匙之一（圆形锁孔钥匙）"


class TestConsumedStatus:
    """§4 消耗流转（测试 7-8）."""

    async def test_consumed_marker_creates_consumed_status(self, test_db: Path) -> None:
        """「续命丹（已服下）」→ create 时 status='consumed'."""
        await _apply(_PID, 1, _inv_settlement("续命丹（已服下）"))

        rows = await InventoryTrackerRepository().list_by_project(_PID)
        assert len(rows) == 1
        assert rows[0]["status"] == "consumed"

    async def test_held_item_transitions_to_consumed(self, test_db: Path) -> None:
        """已有 held「断刀令」，新值「断刀令（被夺走）」→ 刷新 + 流转；不再计 forgotten."""
        pid = f"{_PID}-transition"
        await _apply(pid, 1, _inv_settlement("断刀令"))
        await _apply(pid, 3, _inv_settlement("断刀令（被夺走）"))

        rows = await InventoryTrackerRepository().list_by_project(pid)
        assert len(rows) == 1
        assert rows[0]["status"] == "consumed"
        assert rows[0]["last_used_chapter"] == 3

        for ch in (8, 9, 10):
            await _make_accepted(pid, ch, "他一路北行，再没提起了。")
        forgotten = await _find_forgotten_items(pid, 10, InventoryTrackerRepository())
        assert forgotten == []


class TestInventoryRepair172cq:
    """§4 存量修复（测试 9）：变体归一 + 碎片删除 + 消耗改写 + 正文回刷."""

    async def test_repair_consolidates_variants(self, test_db: Path) -> None:
        pid = f"{_PID}-repair"
        repo = InventoryTrackerRepository()
        await _ensure_project(pid)
        fixtures = [
            ("t1", "断刀（濒临碎裂）", 3),
            ("t2", "断刀（裂纹上百道，刀身濒临断裂）", 5),
            ("t3", "续命丹（已服下）", 6),
            ("t4", "透出一丝不属于这个世界的微光", 7),
            ("t5", "血书", 2),
        ]
        for track_id, name, acq in fixtures:
            await repo.create(
                track_id=track_id,
                project_id=pid,
                character_id="c1",
                item_name=name,
                item_description="",
                acquired_in_chapter=acq,
            )
        contents = {ch: "风雪不止。" for ch in range(1, 11)}
        contents[4] = "他贴身藏着血书，不敢示人。"
        contents[9] = "他取出断刀，缓步上前。"
        for ch, text in contents.items():
            await _make_accepted(pid, ch, text)

        module = _load_repair_module()
        stats = await module.repair_inventory(pid, up_to_chapter=10)

        assert stats["before_rows"] == 5
        assert stats["deleted"] == 1  # 碎片「透出一丝…微光」
        rows = await repo.list_by_project(pid)
        by_name = {r["item_name"]: r for r in rows}
        assert set(by_name) == {"断刀（濒临碎裂）", "续命丹（已服下）", "血书"}
        # 变体归一：首登名 + 最早 acquired + 正文回刷
        assert by_name["断刀（濒临碎裂）"]["acquired_in_chapter"] == 3
        assert by_name["断刀（濒临碎裂）"]["last_used_chapter"] == 9
        # 消耗改写
        assert by_name["续命丹（已服下）"]["status"] == "consumed"
        # 正文回刷
        assert by_name["血书"]["last_used_chapter"] == 4

        forgotten = await _find_forgotten_items(pid, 10, repo)
        assert {f.item_name for f in forgotten} == {"血书"}


def _load_repair_module():
    script = (
        Path(__file__).resolve().parents[1]
        / "tests"
        / "fixtures"
        / "legacy_inventory_repairs"
        / "repair_172cq_inventory.py"
    )
    spec = importlib.util.spec_from_file_location("repair_172cq_inventory", script)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module
