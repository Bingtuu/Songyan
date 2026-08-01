"""Task 172c.p — wuxia forgotten_items 物品追踪粒度修复.

覆盖修复文档 tasks/172c.p-wuxia-forgotten-inventory-tracking.md §4：
- 写入层：inventory 聚合清单拆单物品（括号保护 + 前缀剥离）+ 同名 held 记录刷新不新建
- 检测兜底：_find_forgotten_items 对超阈值候选回查近 threshold 章 accepted 正文
- 存量修复：聚合串展开 + 同名合并 + 按正文回刷 last_used
"""

from __future__ import annotations

import importlib.util
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

_PID = "p172cp"


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


class TestInventoryWriteLayer:
    """§4 写入层：聚合清单拆分 + 前缀剥离 + 同名刷新 + 回归保护."""

    async def test_aggregate_list_split_into_single_items(self, test_db: Path) -> None:
        """聚合清单拆成单物品；括号内顿号不切（「断刀令（两块铁牌）」保持一条）."""
        await _apply(
            _PID,
            1,
            _inv_settlement("持有断刀、断刀门刀谱、血书、断刀令（两块铁牌）、刀谱最后一页密文"),
        )
        rows = await InventoryTrackerRepository().list_by_project(_PID)
        names = sorted(r["item_name"] for r in rows)
        assert names == sorted(
            ["断刀", "断刀门刀谱", "血书", "断刀令（两块铁牌）", "刀谱最后一页密文"]
        )

    async def test_prefix_stripped(self, test_db: Path) -> None:
        """「持有/携带/缴获/从…处缴获」前缀剥离."""
        await _apply(
            _PID,
            1,
            _inv_settlement("携带断刀、缴获铁牌、从暗卫首领处缴获的匕首"),
        )
        rows = await InventoryTrackerRepository().list_by_project(_PID)
        names = sorted(r["item_name"] for r in rows)
        assert names == sorted(["断刀", "铁牌", "匕首"])

    async def test_same_name_refreshes_instead_of_create(self, test_db: Path) -> None:
        """已有同名 held 记录 → 刷新 last_used，不新建."""
        await _apply(_PID, 1, _inv_settlement("断刀"))
        await _apply(_PID, 5, _inv_settlement("断刀、刀谱"))

        rows = await InventoryTrackerRepository().list_by_project(_PID)
        assert len(rows) == 2
        by_name = {r["item_name"]: r for r in rows}
        assert by_name["断刀"]["last_used_chapter"] == 5
        assert by_name["断刀"]["acquired_in_chapter"] == 1
        assert by_name["刀谱"]["acquired_in_chapter"] == 5
        assert by_name["刀谱"]["last_used_chapter"] == 5

    async def test_single_item_value_unchanged(self, test_db: Path) -> None:
        """单物品短值（xuanhuan/scifi 形态）→ 行为不变（回归保护）."""
        await _apply(_PID, 3, _inv_settlement("九转玄丹"))
        rows = await InventoryTrackerRepository().list_by_project(_PID)
        assert len(rows) == 1
        assert rows[0]["item_name"] == "九转玄丹"
        assert rows[0]["last_used_chapter"] == 3

    async def test_empty_or_meaningless_value_creates_nothing(self, test_db: Path) -> None:
        """空值 / 「无」/ 纯前缀值 → 不产生垃圾记录."""
        for i, value in enumerate(["", "无", "持有"], start=1):
            await _apply(_PID, i, _inv_settlement(value))
        rows = await InventoryTrackerRepository().list_by_project(_PID)
        assert rows == []


class TestForgottenTextRecheck:
    """§4 检测兜底：超阈值候选回查近 threshold 章 accepted 正文."""

    async def test_item_in_recent_text_not_forgotten_and_refreshed(
        self, test_db: Path
    ) -> None:
        """物品近 3 章正文出现 → 不计 forgotten 且 last_used 被刷新."""
        pid = f"{_PID}-scan-hit"
        await InventoryTrackerRepository().create(
            track_id="t1",
            project_id=pid,
            character_id="c1",
            item_name="断刀",
            item_description="",
            acquired_in_chapter=1,
        )
        await _make_accepted(pid, 8, "山门前的石阶上落满了叶。")
        await _make_accepted(pid, 9, "他取出断刀，刀锋映着月光。")
        await _make_accepted(pid, 10, "夜色沉沉，四下无声。")

        result = await _find_forgotten_items(pid, 10, InventoryTrackerRepository())

        assert result == []
        rows = await InventoryTrackerRepository().list_by_project(pid)
        assert rows[0]["last_used_chapter"] == 9

    async def test_item_absent_from_recent_text_still_forgotten(
        self, test_db: Path
    ) -> None:
        """物品近 3 章正文未出现 → 仍判 forgotten（真遗忘捕获）."""
        pid = f"{_PID}-scan-miss"
        await InventoryTrackerRepository().create(
            track_id="t1",
            project_id=pid,
            character_id="c1",
            item_name="断刀",
            item_description="",
            acquired_in_chapter=1,
        )
        for ch in (8, 9, 10):
            await _make_accepted(pid, ch, "他一路北行，再没有提起过任何兵器。")

        result = await _find_forgotten_items(pid, 10, InventoryTrackerRepository())

        assert len(result) == 1
        assert result[0].track_id == "t1"
        rows = await InventoryTrackerRepository().list_by_project(pid)
        assert rows[0]["last_used_chapter"] == 1

    async def test_low_info_or_short_core_name_no_false_refresh(
        self, test_db: Path
    ) -> None:
        """核心名 <2 字或 low-info → 不因单字/泛词误刷新."""
        pid = f"{_PID}-scan-lowinfo"
        repo = InventoryTrackerRepository()
        await repo.create(
            track_id="t-low",
            project_id=pid,
            character_id="c1",
            item_name="系统",
            item_description="",
            acquired_in_chapter=1,
        )
        await repo.create(
            track_id="t-short",
            project_id=pid,
            character_id="c1",
            item_name="刀",
            item_description="",
            acquired_in_chapter=1,
        )
        for ch in (8, 9, 10):
            await _make_accepted(pid, ch, "系统的提示音响起，他放下手中的刀。")

        result = await _find_forgotten_items(pid, 10, repo)

        assert {r.track_id for r in result} == {"t-low", "t-short"}
        rows = await repo.list_by_project(pid)
        assert all(r["last_used_chapter"] == 1 for r in rows)

    async def test_compound_item_multi_token_coref_rescues(self, test_db: Path) -> None:
        """复合物品名：全名未出现但 ≥3 个 n-gram token（含长 token）同章共现 → 视为使用.

        例：「断刀门刀谱」全名未被正文书写，但 断刀+刀谱+断刀门 同章共现足以证明
        该 McGuffin 仍在推进（172b 多 token 语义在物品域的复用）。
        """
        pid = f"{_PID}-scan-multi"
        repo = InventoryTrackerRepository()
        await repo.create(
            track_id="t1",
            project_id=pid,
            character_id="c1",
            item_name="断刀门刀谱",
            item_description="",
            acquired_in_chapter=1,
        )
        await _make_accepted(pid, 8, "他擦拭断刀，默诵刀谱口诀，断刀门的传承系于一线。")
        await _make_accepted(pid, 9, "夜色沉沉，四下无声。")
        await _make_accepted(pid, 10, "山门前的石阶上落满了叶。")

        result = await _find_forgotten_items(pid, 10, repo)

        assert result == []
        rows = await repo.list_by_project(pid)
        assert rows[0]["last_used_chapter"] == 8

    async def test_compound_item_single_token_not_enough(self, test_db: Path) -> None:
        """复合物品名：仅 1 个 token 命中（只提 断刀）不构成使用 → 仍判 forgotten."""
        pid = f"{_PID}-scan-single"
        repo = InventoryTrackerRepository()
        await repo.create(
            track_id="t1",
            project_id=pid,
            character_id="c1",
            item_name="断刀门刀谱",
            item_description="",
            acquired_in_chapter=1,
        )
        for ch in (8, 9, 10):
            await _make_accepted(pid, ch, "他挥动断刀杀敌，而后收刀入鞘。")

        result = await _find_forgotten_items(pid, 10, repo)

        assert len(result) == 1
        rows = await repo.list_by_project(pid)
        assert rows[0]["last_used_chapter"] == 1


class TestInventoryRepairScript:
    """§4 存量修复：聚合串展开 + 同名合并 + 正文回刷 last_used."""

    async def test_repair_expands_merges_and_refreshes(self, test_db: Path) -> None:
        pid = f"{_PID}-repair"
        repo = InventoryTrackerRepository()
        await repo.create(
            track_id="agg-1",
            project_id=pid,
            character_id="c1",
            item_name="持有断刀、断刀门刀谱、血书、断刀令（两块铁牌）、刀谱最后一页密文",
            item_description="",
            acquired_in_chapter=2,
        )
        await repo.create(
            track_id="agg-2",
            project_id=pid,
            character_id="c1",
            item_name="持有断刀、断刀门刀谱、血书、从暗卫首领处缴获的匕首",
            item_description="",
            acquired_in_chapter=5,
        )
        contents = {ch: "他一路北行，风雪不止。" for ch in range(1, 11)}
        contents[3] = "他贴身藏着血书，不敢示人。"
        contents[5] = "他翻阅断刀门刀谱，又摸了摸怀中的断刀令。"
        contents[8] = "匕首的寒光一闪而过。"
        contents[9] = "他取出断刀，缓步上前。"
        for ch, text in contents.items():
            await _make_accepted(pid, ch, text)

        module = _load_repair_module()
        stats = await module.repair_inventory(pid, up_to_chapter=10)

        assert stats["before_rows"] == 2
        assert stats["deleted"] == 1  # 「刀谱最后一页密文」全文零命中且已陈旧 → 删除
        rows = await repo.list_by_project(pid)
        by_name = {r["item_name"]: r for r in rows}
        assert set(by_name) == {
            "断刀",
            "断刀门刀谱",
            "血书",
            "断刀令（两块铁牌）",
            "匕首",
        }
        # 同名合并：保留最早 acquired；正文回刷 last_used
        assert by_name["断刀"]["acquired_in_chapter"] == 2
        assert by_name["断刀"]["last_used_chapter"] == 9
        assert by_name["匕首"]["acquired_in_chapter"] == 5
        assert by_name["匕首"]["last_used_chapter"] == 8
        # 正文后续章节出现 → 回刷到最近提及章
        assert by_name["血书"]["last_used_chapter"] == 3
        assert by_name["断刀门刀谱"]["last_used_chapter"] == 5
        assert by_name["断刀令（两块铁牌）"]["last_used_chapter"] == 5

        forgotten = await _find_forgotten_items(pid, 10, repo)
        # 正文回刷过的 断刀/匕首 不再 forgotten；超阈值静默的单物品仍被捕获
        assert {f.item_name for f in forgotten} == {
            "断刀门刀谱",
            "血书",
            "断刀令（两块铁牌）",
        }


    async def test_repair_deletes_stale_ungroundable_items(self, test_db: Path) -> None:
        """存量修复删除：核心名全文零命中且已陈旧的记录（截断碎片/伪名）.

        新鲜登记（未超阈值）即使暂无正文命中也保留——写入层重列与正文回查
        还有机会将其刷新。
        """
        pid = f"{_PID}-repair-del"
        repo = InventoryTrackerRepository()
        await repo.create(
            track_id="garbage",
            project_id=pid,
            character_id="c1",
            item_name="从暗卫首领处缴",
            item_description="",
            acquired_in_chapter=2,
        )
        await repo.create(
            track_id="fresh",
            project_id=pid,
            character_id="c1",
            item_name="新得的物件",
            item_description="",
            acquired_in_chapter=9,
        )
        await repo.create(
            track_id="grounded",
            project_id=pid,
            character_id="c1",
            item_name="断刀",
            item_description="",
            acquired_in_chapter=2,
        )
        for ch in range(1, 11):
            await _make_accepted(pid, ch, "他取出断刀，缓步上前。" if ch == 9 else "风雪不止。")

        module = _load_repair_module()
        stats = await module.repair_inventory(pid, up_to_chapter=10)

        assert stats["deleted"] == 1
        rows = await repo.list_by_project(pid)
        by_name = {r["item_name"]: r for r in rows}
        assert set(by_name) == {"新得的物件", "断刀"}
        assert by_name["断刀"]["last_used_chapter"] == 9


def _load_repair_module():
    import sys

    script = (
        Path(__file__).resolve().parents[1]
        / "tests"
        / "fixtures"
        / "legacy_inventory_repairs"
        / "repair_172cp_inventory.py"
    )
    spec = importlib.util.spec_from_file_location("repair_172cp_inventory", script)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module  # dataclass 处理字符串注解时需要
    spec.loader.exec_module(module)
    return module
