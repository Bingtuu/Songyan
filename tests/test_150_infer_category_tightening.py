"""Tests for Task 150 — tighten `_infer_setting_category` and remove hardcoded protagonist name."""

from __future__ import annotations

from pathlib import Path

from songyan.agents.settlement_extractor._apply import (
    _build_protagonist_names,
    _infer_setting_category,
    _update_continuity_tracking,
)
from songyan.db.connection import get_db
from songyan.db.continuity_repo import (
    InventoryTrackerRepository,
    LocationTrackerRepository,
    SettingTrackingRepository,
)
from songyan.db.repository import ProjectRepository
from songyan.db.settlement_repo import ForeshadowingRepository
from songyan.models import NewSetting, ProjectSetting, StateSettlement


def _setting(setting_name: str, description: str, setting_key: str = "") -> NewSetting:
    return NewSetting(
        setting_name=setting_name,
        description=description,
        source_quote="",
        setting_key=setting_key,
    )


def _category(
    setting: NewSetting,
    protagonist_names: set[str] | None = None,
) -> str:
    return _infer_setting_category(setting, protagonist_names=protagonist_names)


class TestInferCategoryTightening:
    """收紧 critical 判定 + 去硬编码主角名."""

    def test_worldview_detail_no_longer_critical_with_protagonist_name(self) -> None:
        """提供具体主角名时，仅含通用指涉的世界观细节不应被判为 critical."""
        names = {"萧炎", "萧"}
        settings = [
            _setting("他的命运", "命格轨迹在远方"),
            _setting("她的能力", "传承自上古的特殊能力"),
            _setting("遗迹中的血脉", "他的状态与此相关"),
            _setting("古老的天赋", "她的命格并不出众"),
            _setting("mainline 的传承", "他的目标早已失落"),
        ]
        for s in settings:
            assert _category(s, names) != "critical"

    def test_true_critical_still_detected(self) -> None:
        """主角名 + 命格/血脉/传承 等真 critical 关键词仍应判为 critical."""
        names = {"萧炎", "萧"}
        assert _category(_setting("萧炎的命格", "天赋觉醒"), names) == "critical"
        assert _category(_setting("萧族血脉", "传承之力"), names) == "critical"
        assert _category(_setting("萧炎的传承", "主角专属"), names) == "critical"

    def test_no_hardcoded_linyuan(self) -> None:
        """林渊 不再是写死特权；当项目主角为萧炎时，仅含 林渊 不触发 critical."""
        names = {"萧炎", "萧"}
        s = _setting("林渊的旧友", "传承自林渊一脉的功法")
        assert _category(s, names) != "critical"

    def test_fallback_without_protagonist_names(self) -> None:
        """无主角名时回退到保守集合，通用代词不再触发 critical."""
        # 仅命中通用代词 + critical 关键词 → 不再 critical
        assert _category(_setting("他的血脉", "一种古老传承"), None) != "critical"
        # 显式 "主角" + critical 关键词 → 仍 critical（回退集合保留明确主角指涉）
        assert _category(_setting("主角的命格", "决定命运"), None) == "critical"

    def test_138m_sample_hit_rate(self) -> None:
        """138m 误判样本：提供主角名时绝大多数不再 critical；无主角名时仍优于现状."""
        samples = [
            _setting("他的命运", "命格轨迹在远方"),
            _setting("她的能力", "传承自上古的特殊能力"),
            _setting("他的状态", "血脉处于 dormant 状态"),
            _setting("主角的能力", "只是背景中提到的他的能力"),
            _setting("她的命格", "天赋并不出众"),
            _setting("他的传承", "一门古老的目标技艺"),
            _setting("主角的状态", "在遗迹中他的状态"),
            _setting("她的血脉", "源自某个族群的能力"),
            _setting("他的天赋", "注定不凡的他"),
            _setting("她的传承", "mainline 中的过去"),
            _setting("他的命格", "protagonist-related 描述"),
            _setting("主角的命运", "他的目标在远方"),
            _setting("她的状态", "血脉中的古老传承"),
            _setting("他的能力", "命格并非人人所有"),
            _setting("主角的目标", "他的传承尚未觉醒"),
            _setting("她的命格", "mainline 中的天赋设定"),
            _setting("他的血脉", "命运多舛的他"),
            _setting("主角的天赋", "状态逐渐稳定的他"),
            _setting("她的传承", "能力在遗迹中消散"),
            _setting("他的状态", "命格与主线无关"),
            _setting("主角的传承", "他的命运被改写"),
            _setting("她的能力", "血脉之力只是背景"),
        ]

        with_names = [_category(s, {"林渊"}) for s in samples]
        not_critical_with_names = sum(1 for c in with_names if c != "critical")
        assert not_critical_with_names >= 20

        without_names = [_category(s, None) for s in samples]
        not_critical_without_names = sum(1 for c in without_names if c != "critical")
        assert not_critical_without_names >= 15

    def test_technical_and_historical_unchanged(self) -> None:
        """technical / historical 判定不受本次收紧影响."""
        assert _category(_setting("主角能力 Ω", "型号 Ω 的引擎参数")) == "technical"
        assert _category(_setting("上古纪元", "曾经存在的血脉")) == "historical"


class TestBuildProtagonistNames:
    """`_build_protagonist_names` 名称集合构造."""

    def test_build_from_project(self) -> None:
        project = ProjectSetting(genre_id="xuanhuan", protagonist_name="张小凡")
        assert _build_protagonist_names(project) == {"张小凡", "张小"}

    def test_build_short_name(self) -> None:
        project = ProjectSetting(genre_id="xuanhuan", protagonist_name="萧炎")
        assert _build_protagonist_names(project) == {"萧炎"}

    def test_fallback_when_no_project(self) -> None:
        assert _build_protagonist_names(None) == {
            "主角",
            "主人公",
            "protagonist",
            "命定之人",
            "全书核心",
        }

    def test_fallback_when_empty_name(self) -> None:
        project = ProjectSetting(genre_id="xuanhuan", protagonist_name="")
        assert _build_protagonist_names(project) == {
            "主角",
            "主人公",
            "protagonist",
            "命定之人",
            "全书核心",
        }


class TestUpdateContinuityTrackingIntegration:
    """`_update_continuity_tracking` 从项目读取主角名并传入分类器."""

    async def test_loads_project_protagonist_name(self, test_db: Path) -> None:
        pid = "proj-150"
        await ProjectRepository().create(
            ProjectSetting(genre_id="xuanhuan", protagonist_name="萧炎"),
            pid,
        )

        settlement = StateSettlement(
            new_settings=[
                NewSetting(
                    setting_key="xiaoyan.bloodline",
                    setting_name="萧炎血脉",
                    description="传承自萧族的血脉力量",
                    source_quote="",
                )
            ]
        )

        async with get_db() as conn:
            await _update_continuity_tracking(
                settlement=settlement,
                project_id=pid,
                chapter_number=1,
                version_id="v1",
                setting_tracking_repo=SettingTrackingRepository(),
                inventory_repo=InventoryTrackerRepository(),
                location_repo=LocationTrackerRepository(),
                foreshadowing_repo=ForeshadowingRepository(),
                conn=conn,
            )
            await conn.commit()

        rows = await SettingTrackingRepository().list_by_project(pid)
        assert len(rows) == 1
        assert rows[0]["category"] == "critical"
