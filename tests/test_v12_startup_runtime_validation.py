"""Task 223: V12 startup runtime validation tests."""

from __future__ import annotations

from pathlib import Path

from songyan.models import StateSettlement
from songyan.models.settlement import NewCharacter, NewSetting
from songyan.models.supervision import (
    BeatSpec,
    ChapterSupervisionSpec,
    StagePolicy,
    SupervisionSpec,
    WordCountPolicy,
)
from songyan.services.startup_runtime_validation import (
    validate_startup_runtime,
    validate_startup_runtime_from_env,
)


def _spec() -> SupervisionSpec:
    return SupervisionSpec(
        stage="startup_ch1_3",
        word_count=WordCountPolicy(target=3000, hard_min=2700, hard_max=3300),
        chapters={
            1: ChapterSupervisionSpec(
                allowed_beats=[
                    BeatSpec(
                        visible_action="沈砚复核当前数值链。",
                        current_friction="责任质量归属与实测质量不一致。",
                        feedback="终端只返回当前数值链。",
                        micro_decision="沈砚决定保存离线记录。",
                        landing="当前缺口被保存。",
                    )
                ],
                stage_policy=StagePolicy(
                    allow_new_characters=False,
                    allow_past_backstory=False,
                    allow_cross_location_chase=False,
                    allow_identity_secret_reveal=False,
                    allow_relative_time=False,
                    allow_coordinates=False,
                ),
            )
        },
    )


def test_blocks_new_character_from_settlement() -> None:
    settlement = StateSettlement(
        new_characters=[
            NewCharacter(
                name="李维",
                role_type="supporting",
                source_quote="确认人签名是李维",
                background="地面仓储区三号班组的质检员，入职时间两年零四个月。",
            )
        ]
    )

    findings = validate_startup_runtime(
        content="沈砚复核当前数值链。",
        settlement=settlement,
        spec=_spec(),
        chapter_number=1,
        allowed_names={"沈砚"},
    )
    codes = [finding.code for finding in findings]

    assert "new_character" in codes
    assert "character_background" in codes
    assert any("李维" in finding.evidence for finding in findings)


def test_blocks_new_character_from_draft_content() -> None:
    content = "系统记录显示确认人签名是李维。沈砚决定先保存当前数值链。"

    findings = validate_startup_runtime(
        content=content,
        settlement=StateSettlement(),
        spec=_spec(),
        chapter_number=1,
        allowed_names={"沈砚"},
    )

    assert [finding.code for finding in findings] == ["new_character"]


def test_ignores_negated_policy_mentions() -> None:
    content = (
        "沈砚在本地审计会话中写下：不新增角色，不展开旧事故，不使用坐标，"
        "不提前揭示身份秘密。沈砚决定保存当前数值链。"
    )

    findings = validate_startup_runtime(
        content=content,
        settlement=StateSettlement(),
        spec=_spec(),
        chapter_number=1,
        allowed_names={"沈砚"},
    )

    assert findings == []


def test_blocks_relative_time_coordinate_and_cross_location() -> None:
    content = (
        "沈砚追踪到D区储物柜，看到坐标31.23, 121.47。"
        "记录显示李维入职时间两年零四个月。"
    )

    findings = validate_startup_runtime(
        content=content,
        settlement=StateSettlement(),
        spec=_spec(),
        chapter_number=1,
        allowed_names={"沈砚"},
    )
    codes = {finding.code for finding in findings}

    assert {"past_backstory", "coordinates", "cross_location_chase"} <= codes


def test_blocks_new_setting_historical_explanation() -> None:
    settlement = StateSettlement(
        new_settings=[
            NewSetting(
                setting_name="旧记录",
                description="两年前的历史记录解释了当前异常。",
                source_quote="两年前",
                setting_key="old.record",
            )
        ]
    )

    findings = validate_startup_runtime(
        content="沈砚决定保存当前数值链。",
        settlement=settlement,
        spec=_spec(),
        chapter_number=1,
        allowed_names={"沈砚"},
    )

    assert [finding.code for finding in findings] == ["setting_past_backstory"]


def test_validate_from_env_returns_empty_without_config(monkeypatch) -> None:
    monkeypatch.delenv("SONGYAN_STARTUP_SUPERVISION_SPEC", raising=False)

    findings = validate_startup_runtime_from_env(
        content="确认人签名是李维。",
        settlement=StateSettlement(),
        chapter_number=1,
    )

    assert findings == []


def test_validate_from_env_reports_invalid_spec(tmp_path: Path, monkeypatch) -> None:
    spec_path = tmp_path / "bad.json"
    spec_path.write_text("{}", encoding="utf-8")
    monkeypatch.setenv("SONGYAN_STARTUP_SUPERVISION_SPEC", str(spec_path))

    findings = validate_startup_runtime_from_env(
        content="沈砚决定保存当前数值链。",
        settlement=StateSettlement(),
        chapter_number=1,
    )

    assert [finding.code for finding in findings] == ["supervision_spec_invalid"]


def test_allows_coordinate_reference_systems() -> None:
    """Task 224d 修复："轨道坐标系"是参考系概念，不应被坐标红线拦截。"""
    content = (
        "交接记录在第三屏刷新时出现了偏差。沈砚把视线从轨道坐标系移开，"
        "重新看了那行状态码。货舱编号LH-7712的交接栏显示：已完成。"
    )

    findings = validate_startup_runtime(
        content=content,
        settlement=StateSettlement(),
        spec=_spec(),
        chapter_number=1,
        allowed_names={"沈砚"},
    )
    codes = {finding.code for finding in findings}

    assert "coordinates" not in codes


def test_allows_reference_coordinate_and_axes() -> None:
    """参考坐标系、坐标轴、坐标转换都是合法概念术语。"""
    content = (
        "屏幕以参考坐标系为基准绘制了货舱位置图，X坐标轴指向低轨升降港。"
        "经过坐标转换，差值窗口仍静止在27公斤。"
    )

    findings = validate_startup_runtime(
        content=content,
        settlement=StateSettlement(),
        spec=_spec(),
        chapter_number=1,
        allowed_names={"沈砚"},
    )
    codes = {finding.code for finding in findings}

    assert "coordinates" not in codes


def test_allows_coordinate_grid_visual() -> None:
    """Task 224d 修复："坐标网格"是屏幕上的视觉元素，不是真实坐标，不应被拦截。"""
    content = (
        "逆向视图在屏幕上缓慢旋转，每转一圈，那些细密的坐标网格就跟着微微颤动一下，"
        "像是某种正在呼吸的活物。沈砚没有急着去碰键盘。"
    )

    findings = validate_startup_runtime(
        content=content,
        settlement=StateSettlement(),
        spec=_spec(),
        chapter_number=1,
        allowed_names={"沈砚"},
    )
    codes = {finding.code for finding in findings}

    assert "coordinates" not in codes


def test_blocks_relative_time_days() -> None:
    """Task 224d 修复："十一天前"是相对时间表述，属于 startup 禁止的过去背景。"""
    content = (
        "系统返回了一条访问记录：十一天前，封存操作完成后三小时，"
        "有一个匿名会话读取过这条链。沈砚决定保存当前数值链。"
    )

    findings = validate_startup_runtime(
        content=content,
        settlement=StateSettlement(),
        spec=_spec(),
        chapter_number=1,
        allowed_names={"沈砚"},
    )
    codes = {finding.code for finding in findings}

    assert "past_backstory" in codes


def test_blocks_actual_coordinate_mentions() -> None:
    """真正的坐标指示仍应被正确拦截（裸词+数对）。"""
    content = (
        "空白栏下方显示出一组坐标，数值精确到小数点后三位，"
        "旁边是标注为经纬度的对：31.23, 121.47。"
    )

    findings = validate_startup_runtime(
        content=content,
        settlement=StateSettlement(),
        spec=_spec(),
        chapter_number=1,
        allowed_names={"沈砚"},
    )
    codes = {finding.code for finding in findings}

    assert "coordinates" in codes


def test_allows_technical_history_records() -> None:
    """Task 224d 修复："不调用外部历史记录"是技术操作指令（拒绝访问历史），
    不应被 _RELATIVE_TIME_RE 的"历史记录"分支误判为 past_backstory。

    "历史记录"作为数据系统术语（historical records）与叙事性过去背景
    （narrative past backstory）不同；真正的相对时间引用（如"X年前"）
    仍由 _RELATIVE_TIME_RE 的第一分支捕获。
    """
    content = (
        "沈砚在回放选项里选了当前责任质量链，明确指定不调用外部历史记录。"
        "回放从第一段开始：空舱门读数，载荷从零跳到 21.0 kg。"
        "他决定只确认测试结果，不确认对象身份。"
    )

    findings = validate_startup_runtime(
        content=content,
        settlement=StateSettlement(),
        spec=_spec(),
        chapter_number=3,
        allowed_names={"沈砚"},
    )
    codes = {finding.code for finding in findings}

    assert "past_backstory" not in codes
