"""Tests for V9 Task 185 T9 precision fixes.

Evidence base: urban base12000 end15 run1/run2 (2026-07-20). All T9 hits were
traced to four detector precision gaps plus one writer-side tic:
- slash_splice false positive on Chinese frequency units (47次/分钟);
- date_rewind false positives on archive/document dates not covered by the
  flashback marker list (时间戳/签署/发起时间/timestamp/三年前);
- countdown_increase false positives on routine/schedule timers (列车到站)
  and on pairing independent timers of very different magnitude
  (还有四分钟 vs 还有五天);
- writer tic: Echo system messages rendered as ``//`` code-comment splices
  (fixed genre-side in ``genres/data/urban.json`` writer_rules).
"""

from __future__ import annotations

from songyan.agents.rule_auditor import detect_text_cleanliness_artifacts
from songyan.evals.timeline_consistency import (
    detect_timeline_conflicts,
    extract_time_signals,
)


def _artifact_types(text: str) -> set[str]:
    return {m.artifact_type for m in detect_text_cleanliness_artifacts(text)}


def _signals_by_chapter(contents: dict[int, str]):
    return {ch: extract_time_signals(ch, content) for ch, content in contents.items()}


class TestSlashSpliceUnits:
    def test_frequency_per_minute_is_safe(self) -> None:
        # run2 Ch2: 探测频率 47次/分钟 被误判为斜杠拼接
        text = "外部探测频率：47次/分钟，持续时长：2小时13分钟。"

        assert "slash_splice_artifact" not in _artifact_types(text)

    def test_frequency_per_day_is_safe(self) -> None:
        text = "后台任务平均每 3 次/天同步一次，从未间断。"

        assert "slash_splice_artifact" not in _artifact_types(text)

    def test_frequency_per_24_hours_is_safe(self) -> None:
        """187.t: 6次/24小时 是频率单位，不是 CJK slash 拼接 artifact."""
        text = "通信频率: 6次/24小时，节点仍保持静默。"

        assert "slash_splice_artifact" not in _artifact_types(text)

    def test_decimal_seconds_per_item_is_safe(self) -> None:
        """187.w: 0.2秒/个 是速率单位，不是 CJK slash 拼接 artifact."""
        text = "预计生成时间：0.2秒/个。"

        assert "slash_splice_artifact" not in _artifact_types(text)

    def test_comment_splice_still_detected(self) -> None:
        # run1 Ch11: 系统消息被写成 // 注释体，必须继续命中
        text = "手机屏幕暗了半秒，然后亮起一行绿色的文字：“// 指令已接收。环境评估中。”"

        assert "slash_splice_artifact" in _artifact_types(text)


class TestTimelineArchiveMarkers:
    def test_years_ago_flashback_date_ignored(self) -> None:
        # run2 Ch15: “三年前4月2日的邮件” 是真闪回，但缺标记
        signals = _signals_by_chapter(
            {
                14: "2024-03-26，陈屿完成交接。",
                15: "他翻出三年前4月2日的邮件——那是他被开除后第七天。",
            }
        )

        assert detect_timeline_conflicts(signals) == []
        assert signals[15][0].ignored_for_conflict is True

    def test_signing_date_on_document_ignored(self) -> None:
        # run1 Ch10: 合同扫描件签署日期被当作叙事时间
        signals = _signals_by_chapter(
            {
                9: "2024-01-05，陈屿回到办公室。",
                10: "纸上是一份合同扫描件的打印版，签署日期为2023-09-10，纸张已经泛黄。",
            }
        )

        assert detect_timeline_conflicts(signals) == []

    def test_photo_timestamp_ignored(self) -> None:
        # run1 Ch8: 照片/注释时间戳是档案上下文
        signals = _signals_by_chapter(
            {
                5: "2023-11-02，陈屿搬进新公寓。",
                8: "他盯着照片右下角的时间戳：2023-10-27 15:42:08。",
            }
        )

        assert detect_timeline_conflicts(signals) == []

    def test_log_initiation_time_ignored(self) -> None:
        # run1 Ch5: “# 发起时间：...” 是日志头，不是叙事时间
        signals = _signals_by_chapter(
            {
                4: "# 发起时间：2024-03-26 22:11:05",
                5: "2024-03-20，陈屿第一次进入机房。",
            }
        )

        assert detect_timeline_conflicts(signals) == []

    def test_iso_timestamp_line_ignored(self) -> None:
        # run1 Ch11: “timestamp = 2023-08-29T...” 是文件时间戳行
        signals = _signals_by_chapter(
            {
                10: "2023-09-10，陈屿签下合同。",
                11: "文件最后一行写着 timestamp = 2023-08-29T14:23:17.892Z",
            }
        )

        assert detect_timeline_conflicts(signals) == []

    def test_pre_project_date_in_narrative_ignored(self) -> None:
        """187.w Ch29: 叙事中追溯项目启动前的日期是闪回，不是时间线回跳。"""
        signals = _signals_by_chapter(
            {
                24: "页脚上印着版本号 V3.2.1-2025-04-09。",
                29: "陈屿盯着屏幕。2021年3月15日。Echo项目还没有启动，但seed模块已经开始测试。",
            }
        )

        assert detect_timeline_conflicts(signals) == []

    def test_compile_timestamp_ignored(self) -> None:
        """187.w Ch43: 代码/文件编译时间戳是档案属性，不是叙事时间。"""
        signals = _signals_by_chapter(
            {
                39: "法院已受理，将于2024年3月15日上午9时开庭审理。",
                43: "最后编译时间：2022-03-17 14:32:47。",
            }
        )

        assert detect_timeline_conflicts(signals) == []

    def test_code_comment_timestamp_ignored(self) -> None:
        """187.w Ch30: // Timestamp: ... (UTC) 是代码注释时间戳，不是叙事时间。"""
        signals = _signals_by_chapter(
            {
                24: "页脚上印着版本号 V3.2.1-2025-04-09。",
                30: "`// Timestamp: 1708094827 (2024-02-17 03:47:00 UTC)`",
            }
        )

        assert detect_timeline_conflicts(signals) == []


class TestCountdownPairing:
    def test_schedule_arrival_countdown_ignored(self) -> None:
        # run2 Ch13: 列车到站是交通时刻表，不与剧情倒计时配对
        signals = _signals_by_chapter(
            {
                11: "他盯着隧道口：反向列车还有两分钟到站。",
                13: "三分钟。他还有三分钟。",
            }
        )

        assert detect_timeline_conflicts(signals) == []

    def test_independent_timer_magnitude_not_paired(self) -> None:
        # run1 Ch5: 4 分钟监听窗口与 5 天截止期限是两个独立计时器
        signals = _signals_by_chapter(
            {
                2: "他在心里默数着剩下的时间：大约还有四分钟。",
                5: "距离下周三，还有五天。",
            }
        )

        assert detect_timeline_conflicts(signals) == []

    def test_same_timer_small_increase_still_flagged(self) -> None:
        # 同一倒计时的小幅回跳（3 天 → 5 天）必须继续命中
        signals = _signals_by_chapter(
            {
                74: "屏幕提示：还剩三天，潮汐墙抵达。",
                75: "控制台刷新后写着：还剩五天，潮汐墙抵达。",
            }
        )

        conflicts = detect_timeline_conflicts(signals)

        assert len(conflicts) == 1
        assert conflicts[0].conflict_type == "countdown_increase"

    def test_distinct_deadlines_same_magnitude_not_paired(self) -> None:
        # run3 Ch2: 房租到期与项目总结会是两个独立截止期限（量级相近、语义无关）
        signals = _signals_by_chapter(
            {
                1: "房租还有五天到期，房东上周已经发了第三次催缴通知。",
                2: "距离下周项目总结会还有7天。",
            }
        )

        assert detect_timeline_conflicts(signals) == []

    def test_same_deadline_reworded_still_flagged(self) -> None:
        # 同一截止期限换措辞（还剩 → 倒计时）仍须命中：锚点重叠提供配对证据
        signals = _signals_by_chapter(
            {
                74: "警报显示：潮汐墙还剩三天抵达。",
                75: "控制台刷新：潮汐墙抵达倒计时五天。",
            }
        )

        conflicts = detect_timeline_conflicts(signals)

        assert len(conflicts) == 1
        assert conflicts[0].conflict_type == "countdown_increase"

    def test_distinct_tactical_windows_not_paired(self) -> None:
        """187.w Ch29→Ch30: 两个不同战术“时间窗口”的倒计时不应被配对为同一计时器。"""
        signals = _signals_by_chapter(
            {
                29: (
                    "你的位置暴露时间窗口还剩四分钟——"
                    "下一个监控轮巡周期在三分四十七秒后完成数据回传。"
                ),
                30: "距离Echo_Core警告的十五分钟窗口还有八分钟。",
            }
        )

        assert detect_timeline_conflicts(signals) == []


class TestTimelineArchiveMarkersRound2:
    def test_last_year_meeting_minutes_ignored(self) -> None:
        # run3 Ch13: 加密会议纪要的会议日期是档案上下文
        signals = _signals_by_chapter(
            {
                6: "2024-10-20，陈屿收到第二封邮件。",
                13: "灵犀解析出文本：会议日期：去年10月15日。地点：蓝港资本上海办公室。",
            }
        )

        assert detect_timeline_conflicts(signals) == []

    def test_modified_time_and_elapsed_phrase_ignored(self) -> None:
        # run3 Ch6: “最后修改时间 + 距今” 是档案属性，不是叙事时间
        signals = _signals_by_chapter(
            {
                4: "2024-06-15，数据转移完成。",
                6: "防火墙规则最后修改时间：2023年11月7日。距今十一个月。",
            }
        )

        assert detect_timeline_conflicts(signals) == []

    def test_pipe_log_line_date_ignored(self) -> None:
        # run3 Ch13: 管道分隔的服务器日志行不是叙事时间
        signals = _signals_by_chapter(
            {
                6: "2024-11-02，陈屿合上笔记本。",
                13: "恢复出的记录如下：2024-10-15 03:47:14 | INFO | External command received",
            }
        )

        assert detect_timeline_conflicts(signals) == []

    def test_yearless_date_not_compared_with_full_date(self) -> None:
        # run3 Ch15: 无年份的“10月16日”归一化为 month*31+day，与完整日期
        # ordinal 不可比，配对必然误判回跳——跳过混合配对
        signals = _signals_by_chapter(
            {
                4: "2024-06-15，数据转移完成。",
                15: "“星图”项目启动日期被标注出来——10月16日。",
            }
        )

        assert detect_timeline_conflicts(signals) == []

    def test_yearless_pair_still_compared(self) -> None:
        # 两个无年份日期仍可比较（同一年度语境内的回跳）
        signals = _signals_by_chapter(
            {
                4: "他在10月17日提交了报告。",
                5: "回溯到10月16日，系统已经开始告警。",
            }
        )

        conflicts = detect_timeline_conflicts(signals)

        assert len(conflicts) == 1
        assert conflicts[0].conflict_type == "date_rewind"


class TestTimelineArchiveMarkersCh75:
    def test_birth_date_ignored(self) -> None:
        """187.x Ch64/Ch70/Ch75: 出生/童年日期是档案闪回，不是叙事时间回跳。"""
        signals = _signals_by_chapter(
            {
                63: "当前时间：2025年3月20日。",
                64: "那个婴儿的出生日期是1992年12月24日。",
            }
        )

        assert detect_timeline_conflicts(signals) == []

    def test_id_card_date_ignored(self) -> None:
        """187.x Ch75: 身份证/证件日期是档案属性。"""
        signals = _signals_by_chapter(
            {
                73: "他打开手机，屏幕显示2024年4月7日。",
                75: "身份证上的出生日期是1989年3月12日。",
            }
        )

        assert detect_timeline_conflicts(signals) == []

    def test_registration_time_ignored(self) -> None:
        """187.x Ch66: 账号注册时间是档案属性。"""
        signals = _signals_by_chapter(
            {
                65: "2024年1月5日，陈屿到达数据中心。",
                66: "`[注册时间: 2017年9月12日]` `[签订日期: 2024年1月7日]`",
            }
        )

        assert detect_timeline_conflicts(signals) == []

    def test_bracket_registration_date_ignored(self) -> None:
        """187.x Ch66: `[注册日期: ...]` 元数据块内的日期不参与时间线判定。"""
        signals = _signals_by_chapter(
            {
                63: "当前时间：2025年3月20日。",
                66: "`[注册日期: 2017年9月12日]`",
            }
        )

        assert detect_timeline_conflicts(signals) == []

    def test_bracket_last_update_ignored(self) -> None:
        """187.x Ch66: `[最后更新: ...]` 元数据块内的日期不参与时间线判定。"""
        signals = _signals_by_chapter(
            {
                63: "当前时间：2025年3月20日。",
                66: "`[最后更新: 2024年1月7日]`",
            }
        )

        assert detect_timeline_conflicts(signals) == []

    def test_father_relationship_date_ignored(self) -> None:
        """187.x Ch70: 父子回忆语境中的日期是档案闪回，不是叙事时间回跳。"""
        signals = _signals_by_chapter(
            {
                63: "当前时间：2025年3月20日。",
                70: (
                    "他知道那个密码。那是他和父亲之间从未对第三人提及的暗号——"
                    "不是1998年7月19日，不是任何可以被第三方推断出来的信息。"
                ),
            }
        )

        assert detect_timeline_conflicts(signals) == []


class TestTimelineArchiveMarkersCh100:
    def test_relative_day_before_date_ignored(self) -> None:
        """187.y Ch82: 日期后紧跟“三天前”是相对过去引用，不是叙事时间回跳。"""
        signals = _signals_by_chapter(
            {
                81: "当前时间：2025年3月20日。",
                82: "2024年3月12日。三天前。他激活Echo_Core的同一天。",
            }
        )

        assert detect_timeline_conflicts(signals) == []

    def test_covert_channel_log_date_ignored(self) -> None:
        """187.y Ch83: 日志/暗网隐蔽通道语境中的日期是档案闪回。"""
        signals = _signals_by_chapter(
            {
                81: "当前时间：2025年3月20日。",
                83: (
                    "“2022年3月15日。”林知遥的声音很轻，"
                    "“凌晨3点47分——Echo_Core自主创建了一个隐蔽通道，"
                    "连接到暗面组织的内部网络。”"
                ),
            }
        )

        assert detect_timeline_conflicts(signals) == []


class TestTimelineArchiveMarkersCh100Round2:
    def test_fullwidth_bracket_timestamp_ignored(self) -> None:
        """187.z Ch91: `【覆盖时间戳: ...】` 全角括号元数据块不参与判定。"""
        signals = _signals_by_chapter(
            {
                90: "当前时间：2025年3月20日。",
                91: "【覆盖时间戳：2022年3月17日 14:23:47】",
            }
        )

        assert detect_timeline_conflicts(signals) == []

    def test_physical_isolation_archive_date_ignored(self) -> None:
        """187.z Ch91: 物理隔离的归档版本日期是档案属性。"""
        signals = _signals_by_chapter(
            {
                90: "当前时间：2025年3月20日。",
                91: "那个版本在2022年3月17日已经被物理隔离了。",
            }
        )

        assert detect_timeline_conflicts(signals) == []

    def test_inline_code_filename_date_ignored(self) -> None:
        """187.z Ch96: 行内代码文件名中的日期不参与时间线判定。"""
        signals = _signals_by_chapter(
            {
                90: "当前时间：2025年3月20日。",
                96: "`Echo_Core_2022-03-15_log.enc`",
            }
        )

        assert detect_timeline_conflicts(signals) == []

    def test_project_sealed_date_ignored(self) -> None:
        """187.z Ch96: “项目被封存后”语境中的日期是档案闪回。"""
        signals = _signals_by_chapter(
            {
                90: "当前时间：2025年3月20日。",
                96: (
                    "“2022年3月15日。”林知遥说，"
                    "“那是项目被封存后的第四个月。”"
                ),
            }
        )

        assert detect_timeline_conflicts(signals) == []

    def test_compact_timestamp_date_ignored(self) -> None:
        """187.z Ch96: 日期后紧跟 HH:MM:SS 是机器/口令时间戳，不是叙事时间。"""
        signals = _signals_by_chapter(
            {
                90: "当前时间：2025年3月20日。",
                96: "“2022年3月15日14:37:22。”陈屿说。",
            }
        )

        assert detect_timeline_conflicts(signals) == []


class TestSlashSpliceStructuredMessage:
    def test_structured_form_field_separator_is_safe(self) -> None:
        """187.x Ch66: 结构化消息中的 `/` 是字段分隔符，不是拼接 artifact。"""
        text = (
            "`[目标：建立通信链路 / 源数据：内部节点 / 目标数据：外部组织核心节点]`"
        )

        assert "slash_splice_artifact" not in _artifact_types(text)

    def test_id_form_field_separator_is_safe(self) -> None:
        """187.x Ch66: 身份信息表单中的 `/` 是字段分隔符。"""
        text = (
            "`[类别：注册账号 / 真实姓名：张三 / 身份证号：310***********0012 / "
            "联系电话：138********]`"
        )

        assert "slash_splice_artifact" not in _artifact_types(text)
