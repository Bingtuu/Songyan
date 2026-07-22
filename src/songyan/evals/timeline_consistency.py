"""Cross-chapter timeline consistency diagnostics (Task 162).

This module is intentionally diagnostic-only. It extracts deterministic time
signals from accepted chapter text and reports likely conflicts without feeding
the result into review or gate decisions.
"""

from __future__ import annotations

import re
from datetime import date
from typing import Literal

from pydantic import BaseModel

from songyan.db.repository import ChapterHeadRepository, ChapterVersionRepository
from songyan.utils._helpers import locate_position

TimeSignalType = Literal["countdown", "absolute_date", "relative_sequence"]
TimelineConflictType = Literal["countdown_increase", "date_rewind"]

_CHINESE_NUMERAL_MAP = {
    "零": 0,
    "〇": 0,
    "一": 1,
    "二": 2,
    "两": 2,
    "三": 3,
    "四": 4,
    "五": 5,
    "六": 6,
    "七": 7,
    "八": 8,
    "九": 9,
}

_FLASHBACK_MARKERS = (
    "闪回",
    "回忆",
    "梦境",
    "旧日",
    "旧时",
    "曾经",
    "档案",
    "日志",
    "记录显示",
    "录音",
    "录像",
    "历史记录",
    # 185 补充：档案/文档日期语境（urban end15 run1/run2 实证假阳性）
    "年前",  # “三年前4月2日” 等相对过去引用
    "时间戳",
    "签署",
    "发起时间",
    "timestamp",
    # 185 第二轮（run3 实证）
    "去年",
    "前年",
    "距今",
    "修改时间",
    # 187.w 补充：urban Ch50 闪回/档案日期语境
    "还没有启动",
    "项目启动",
    "启动日期",
    "视频文件",
    "原型",
    "测试",
    "编译时间",
    "创建时间",
    "时间戳是",
    "最后编译",
    "Timestamp",
    "UTC",
    # 187.x 补充：urban Ch75 出生/身份/注册档案日期语境
    "出生",
    "出生日期",
    "胚胎",
    "移植",
    "实验体",
    "实验体编号",
    "注册时间",
    "注册日期",
    "签订",
    "签字",
    "签名",
    "同意书",
    "知情同意",
    "身份证",
    "小时候",
    "父亲",
    "我父亲",
    "你父亲",
    "我爸",
    "第一次",
    # 187.y Ch100：相对过去引用与日志/暗网语境
    "天前",
    "隐蔽通道",
    # 187.z Ch100：归档版本/封存项目/身份验证语境
    "物理隔离",
    "项目被封存",
    "身份验证",
)

# 同一倒计时计时器的量级容差：相邻倒计时信号的规范化小时数比值超过该值，
# 视为两个独立计时器（185：run1 “还有四分钟” vs “还有五天” 实证假阳性）。
_COUNTDOWN_SAME_TIMER_MAX_RATIO = 4.0

# 作息/日程类计时语境：交通时刻表与日常作息不是剧情倒计时弧，
# 不参与跨章 countdown 回跳判定（185：run2 “列车还有两分钟到站” 实证）。
_SCHEDULE_MARKERS = (
    "到站",
    "发车",
    "班次",
    "末班",
    "检票",
    "午休",
    "下班",
    "打卡",
)

# 结构化元数据块：方括号/全角括号/行内代码内的键值对日期
# （如 `[注册日期: ...]`、`【覆盖时间戳: ...】`、`Echo_Core_2022-03-15_log.enc`）
# 是档案/文件属性，不参与叙事时间线判定（187.x Ch66 / 187.z Ch91/Ch96）。
_METADATA_BLOCK_RE = re.compile(r"\[[^\]]*\]|【[^】]*】|`[^`]*`")


class TimeSignal(BaseModel):
    """A deterministic time signal extracted from chapter text."""

    chapter_no: int
    signal_type: TimeSignalType
    source_quote: str
    location: str
    value: float | int | str
    unit: str = ""
    normalized_value: float | int | None = None
    ignored_for_conflict: bool = False
    ignore_reason: str = ""
    # 倒计时语义锚点（仅 countdown）：匹配点邻近窗口的 CJK bigram 集合，
    # 用于判断两个倒计时信号是否指向同一截止期限（185 第二轮）。
    anchors: frozenset[str] = frozenset()


class TimelineConflict(BaseModel):
    """Likely cross-chapter timeline conflict."""

    conflict_type: TimelineConflictType
    previous_chapter: int
    current_chapter: int
    previous_value: float | int | str
    current_value: float | int | str
    previous_quote: str
    current_quote: str
    previous_location: str
    current_location: str
    severity: str = "diagnostic"
    message: str


_ANCHOR_TRIGGER_RE = re.compile(r"倒计时|还剩|剩余|还有|大约|距离")
# 187.w: “窗口”是通用容器词，出现在不同战术/调度语境中时不提供可配对的截止期限证据。
_ANCHOR_STRIP_CHARS = frozenset("零〇一二两三四五六七八九十百千万亿天日小时分钟秒钟秒窗口")


def _countdown_anchor(text: str, start: int, end: int, radius: int = 12) -> frozenset[str]:
    """提取倒计时匹配点邻近窗口的 CJK bigram 集合，作为“同一截止期限”证据。

    剔除触发词（还剩/还有/倒计时等）、中文数字与时间单位后，对剩余 CJK 字符
    取 bigram。两个倒计时信号锚点均非空且不相交时，视为不同的截止期限
    （185 第二轮：run3 “房租还有五天到期” vs “项目总结会还有7天” 实证）。
    """
    window = text[max(0, start - radius): min(len(text), end + radius)]
    window = _ANCHOR_TRIGGER_RE.sub("", window)
    chars = [c for c in window if "\u4e00" <= c <= "\u9fff" and c not in _ANCHOR_STRIP_CHARS]
    return frozenset("".join(chars[i:i + 2]) for i in range(len(chars) - 1))


def _chinese_to_int(text: str) -> int | None:
    """Convert simple Chinese numerals up to 999 to int."""
    stripped = text.strip()
    if not stripped:
        return None
    if stripped.isdigit():
        return int(stripped)
    total = 0
    section = 0
    current = 0
    unit_map = {"十": 10, "百": 100}
    for char in stripped:
        if char in _CHINESE_NUMERAL_MAP:
            current = _CHINESE_NUMERAL_MAP[char]
            continue
        if char in unit_map:
            unit = unit_map[char]
            section += (current or 1) * unit
            current = 0
            continue
        return None
    total += section + current
    return total


def _countdown_to_hours(value: int, unit: str) -> float:
    if unit in {"天", "日"}:
        return float(value * 24)
    if unit in {"小时", "时"}:
        return float(value)
    if unit in {"分钟", "分"}:
        return round(value / 60, 4)
    return float(value)


def _context_window(text: str, start: int, end: int, radius: int = 80) -> str:
    return text[max(0, start - radius): min(len(text), end + radius)]


_LOG_LINE_RE = re.compile(r"\d{4}-\d{2}-\d{2}[ T]\d{2}:\d{2}(?::\d{2})?\s*[|｜]")


def _ignored_by_flashback_context(text: str, start: int, end: int) -> tuple[bool, str]:
    context = _context_window(text, start, end)
    marker = next((m for m in _FLASHBACK_MARKERS if m in context), "")
    if marker:
        return True, f"flashback_context:{marker}"
    marker = next((m for m in _SCHEDULE_MARKERS if m in context), "")
    if marker:
        return True, f"schedule_context:{marker}"
    # 结构化元数据块（方括号/全角括号/行内代码）不是叙事时间
    for block_match in _METADATA_BLOCK_RE.finditer(text):
        if block_match.start() <= start and block_match.end() >= end:
            return True, "metadata_block"
    # 日期后紧跟 HH:MM(:SS) 是机器/日志/口令时间戳（如 2022年3月15日14:37:22）
    if text[end:end + 1].isdigit():
        tail = text[end:end + 10].lstrip()
        if re.match(r"\d{1,2}:\d{2}(?::\d{2})?", tail):
            return True, "compact_timestamp"
    # 管道分隔的机器日志行（如 "2024-10-15 03:47:14 | INFO | ..."）不是叙事时间
    line_start = text.rfind("\n", 0, start) + 1
    line_end = text.find("\n", end)
    if line_end < 0:
        line_end = len(text)
    if _LOG_LINE_RE.search(text[line_start:line_end]):
        return True, "log_line_context"
    return False, ""


def _line_quote(text: str, start: int, end: int, max_len: int = 80) -> str:
    line_start = text.rfind("\n", 0, start) + 1
    line_end = text.find("\n", end)
    if line_end < 0:
        line_end = len(text)
    quote = text[line_start:line_end].strip()
    if len(quote) > max_len:
        return quote[:max_len] + "..."
    return quote


def _date_ordinal(year: int | None, month: int, day: int) -> int | None:
    if month < 1 or month > 12 or day < 1 or day > 31:
        return None
    if year is not None:
        try:
            return date(year, month, day).toordinal()
        except ValueError:
            return None
    return month * 31 + day


def _append_signal(
    signals: list[TimeSignal],
    *,
    chapter_no: int,
    signal_type: TimeSignalType,
    text: str,
    start: int,
    end: int,
    value: float | int | str,
    unit: str = "",
    normalized_value: float | int | None = None,
    anchors: frozenset[str] = frozenset(),
) -> None:
    ignored, reason = _ignored_by_flashback_context(text, start, end)
    signals.append(
        TimeSignal(
            chapter_no=chapter_no,
            signal_type=signal_type,
            source_quote=_line_quote(text, start, end),
            location=locate_position(text, start),
            value=value,
            unit=unit,
            normalized_value=normalized_value,
            ignored_for_conflict=ignored,
            ignore_reason=reason,
            anchors=anchors,
        )
    )


_COUNTDOWN_PATTERNS: tuple[re.Pattern[str], ...] = (
    re.compile(
        r"(?:倒计时|还剩|剩余|还有|距[^\n，。；;]{0,12}?还有)\s*"
        r"(?P<num>\d+|[零〇一二两三四五六七八九十百]+)\s*"
        r"(?P<unit>天|日|小时|时|分钟|分)"
    ),
)

_ISO_DATE_PATTERN = re.compile(
    r"(?P<year>\d{4})[-/.](?P<month>\d{1,2})[-/.](?P<day>\d{1,2})"
    r"(?:[ T](?P<hour>\d{1,2}):(?P<minute>\d{2}))?"
)
_CN_DATE_PATTERN = re.compile(
    r"(?:(?P<year>\d{4})年)?(?P<month>\d{1,2})月(?P<day>\d{1,2})[日号]"
)
_RELATIVE_PATTERN = re.compile(
    r"(次日|翌日|第二天|"
    r"(?P<num>\d+|[零〇一二两三四五六七八九十百]+)\s*天\s*(?:后|之后|以后))"
)


def extract_time_signals(chapter_no: int, content: str) -> list[TimeSignal]:
    """Extract deterministic countdown/date/relative time signals from a chapter."""
    signals: list[TimeSignal] = []
    seen_spans: set[tuple[int, int, str]] = set()

    for pattern in _COUNTDOWN_PATTERNS:
        for match in pattern.finditer(content):
            span_key = (match.start(), match.end(), "countdown")
            if span_key in seen_spans:
                continue
            seen_spans.add(span_key)
            raw_num = match.group("num")
            value = _chinese_to_int(raw_num)
            if value is None:
                continue
            unit = match.group("unit")
            _append_signal(
                signals,
                chapter_no=chapter_no,
                signal_type="countdown",
                text=content,
                start=match.start(),
                end=match.end(),
                value=value,
                unit=unit,
                normalized_value=_countdown_to_hours(value, unit),
                anchors=_countdown_anchor(content, match.start(), match.end()),
            )

    for pattern in (_ISO_DATE_PATTERN, _CN_DATE_PATTERN):
        for match in pattern.finditer(content):
            span_key = (match.start(), match.end(), "absolute_date")
            if span_key in seen_spans:
                continue
            seen_spans.add(span_key)
            year = int(match.group("year")) if match.groupdict().get("year") else None
            month = int(match.group("month"))
            day = int(match.group("day"))
            ordinal = _date_ordinal(year, month, day)
            if ordinal is None:
                continue
            date_value = (
                f"{year:04d}-{month:02d}-{day:02d}"
                if year is not None
                else f"{month:02d}-{day:02d}"
            )
            _append_signal(
                signals,
                chapter_no=chapter_no,
                signal_type="absolute_date",
                text=content,
                start=match.start(),
                end=match.end(),
                value=date_value,
                unit="date",
                normalized_value=ordinal,
            )

    for match in _RELATIVE_PATTERN.finditer(content):
        span_key = (match.start(), match.end(), "relative_sequence")
        if span_key in seen_spans:
            continue
        seen_spans.add(span_key)
        if match.group("num"):
            days = _chinese_to_int(match.group("num"))
        else:
            days = 1
        if days is None:
            continue
        _append_signal(
            signals,
            chapter_no=chapter_no,
            signal_type="relative_sequence",
            text=content,
            start=match.start(),
            end=match.end(),
            value=match.group(0),
            unit="day_offset",
            normalized_value=days,
        )

    signals.sort(key=lambda item: (item.chapter_no, item.location, item.signal_type))
    return signals


def _conflict_from_signals(
    conflict_type: TimelineConflictType,
    previous: TimeSignal,
    current: TimeSignal,
    message: str,
) -> TimelineConflict:
    return TimelineConflict(
        conflict_type=conflict_type,
        previous_chapter=previous.chapter_no,
        current_chapter=current.chapter_no,
        previous_value=previous.value,
        current_value=current.value,
        previous_quote=previous.source_quote,
        current_quote=current.source_quote,
        previous_location=previous.location,
        current_location=current.location,
        message=message,
    )


def detect_timeline_conflicts(
    signals_by_chapter: dict[int, list[TimeSignal]],
) -> list[TimelineConflict]:
    """Detect likely cross-chapter timeline conflicts (diagnostic only)."""
    conflicts: list[TimelineConflict] = []
    ordered_signals = [
        signal
        for chapter in sorted(signals_by_chapter)
        for signal in signals_by_chapter[chapter]
        if not signal.ignored_for_conflict
    ]

    countdowns = [
        signal
        for signal in ordered_signals
        if signal.signal_type == "countdown" and signal.normalized_value is not None
    ]
    for previous, current in zip(countdowns, countdowns[1:]):
        if current.chapter_no <= previous.chapter_no:
            continue
        previous_hours = float(previous.normalized_value or 0)
        current_hours = float(current.normalized_value or 0)
        if previous_hours > 0 and current_hours / previous_hours > _COUNTDOWN_SAME_TIMER_MAX_RATIO:
            # 量级差异过大视为两个独立计时器（如 "还有四分钟" vs "还有五天"），
            # 不参与同一倒计时回跳判定（185：run1/Ch5、run1/Ch10 实证假阳性）。
            continue
        if previous.anchors and current.anchors and previous.anchors.isdisjoint(current.anchors):
            # 锚点无语义重叠视为两个独立截止期限（如 "房租还有五天到期" vs
            # "项目总结会还有7天"），不参与同一倒计时回跳判定（185 第二轮：
            # run3/Ch2 实证）。任一侧锚点为空时保守回退到仅量级约束。
            continue
        if current_hours > previous_hours:
            conflicts.append(
                _conflict_from_signals(
                    "countdown_increase",
                    previous,
                    current,
                    "倒计时在后续章节反增，疑似时间线回跳或版本拼接矛盾。",
                )
            )

    dates = [
        signal
        for signal in ordered_signals
        if signal.signal_type == "absolute_date" and signal.normalized_value is not None
    ]
    for previous, current in zip(dates, dates[1:]):
        if current.chapter_no <= previous.chapter_no:
            continue
        # 无年份日期（"MM-DD"）与完整日期（"YYYY-MM-DD"）的归一化值不可比：
        # 前者为 month*31+day，后者为 date ordinal，混合配对必然误判回跳
        # （185 第二轮：run3/Ch15 "10月16日" vs "2024-06-15" 实证）。
        if str(previous.value).count("-") != str(current.value).count("-"):
            continue
        if int(current.normalized_value or 0) < int(previous.normalized_value or 0):
            conflicts.append(
                _conflict_from_signals(
                    "date_rewind",
                    previous,
                    current,
                    "绝对日期在后续章节回跳，疑似跨章时间线矛盾。",
                )
            )

    conflicts.sort(key=lambda item: (item.current_chapter, item.conflict_type))
    return conflicts


async def collect_timeline_signals(
    project_id: str,
    start: int,
    end: int,
    *,
    head_repo: ChapterHeadRepository | None = None,
    version_repo: ChapterVersionRepository | None = None,
) -> dict[int, list[TimeSignal]]:
    """Read accepted chapter text and extract time signals by chapter."""
    head_repo = head_repo or ChapterHeadRepository()
    version_repo = version_repo or ChapterVersionRepository()
    heads = await head_repo.list_by_project(project_id)
    signals_by_chapter: dict[int, list[TimeSignal]] = {}

    for head in heads:
        if not (start <= head.chapter_number <= end):
            continue
        if head.status != "accepted" or not head.accepted_version_id:
            continue
        version = await version_repo.get(head.accepted_version_id)
        if version is None:
            continue
        signals_by_chapter[head.chapter_number] = extract_time_signals(
            head.chapter_number, version.content
        )

    return signals_by_chapter


async def collect_timeline_conflicts(
    project_id: str,
    start: int,
    end: int,
) -> tuple[dict[int, list[TimeSignal]], list[TimelineConflict]]:
    """Collect accepted-text time signals and detect conflicts."""
    signals = await collect_timeline_signals(project_id, start, end)
    return signals, detect_timeline_conflicts(signals)


def render_timeline_consistency_section(
    signals_by_chapter: dict[int, list[TimeSignal]],
    conflicts: list[TimelineConflict],
) -> str:
    """Render timeline diagnostics for metrics/report output."""
    lines = ["## 跨章时间线一致性诊断（Task 162，诊断项；不阻塞 accept）", ""]
    signal_count = sum(len(signals) for signals in signals_by_chapter.values())
    if signal_count == 0:
        lines.append("（未抽取到确定性时间信号）")
        return "\n".join(lines)

    lines.append(
        f"- 抽取确定性时间信号 **{signal_count}** 条；"
        f"疑似冲突 **{len(conflicts)}** 条。"
    )
    ignored = [
        signal
        for signals in signals_by_chapter.values()
        for signal in signals
        if signal.ignored_for_conflict
    ]
    if ignored:
        lines.append(f"- 闪回/档案上下文信号 **{len(ignored)}** 条，仅展示，不参与冲突判定。")
    lines.append("")

    if conflicts:
        lines.append("| 类型 | 前章 | 后章 | 前值 | 后值 | 定位 |")
        lines.append("|------|------|------|------|------|------|")
        for conflict in conflicts:
            lines.append(
                f"| {conflict.conflict_type} | Ch{conflict.previous_chapter} "
                f"| Ch{conflict.current_chapter} | {conflict.previous_value} "
                f"| {conflict.current_value} | "
                f"{conflict.previous_location} → {conflict.current_location} |"
            )
        lines.append("")
    else:
        lines.append("- ✓ 未发现确定性时间信号的跨章矛盾。")
        lines.append("")

    lines.append("<details><summary>时间信号明细</summary>")
    lines.append("")
    lines.append("| 章 | 类型 | 值 | 单位 | 定位 | 片段 | 备注 |")
    lines.append("|----|------|----|------|------|------|------|")
    for chapter in sorted(signals_by_chapter):
        for signal in signals_by_chapter[chapter]:
            note = signal.ignore_reason if signal.ignored_for_conflict else ""
            quote = signal.source_quote.replace("|", "\\|")
            lines.append(
                f"| {chapter} | {signal.signal_type} | {signal.value} | {signal.unit} "
                f"| {signal.location} | {quote} | {note} |"
            )
    lines.append("")
    lines.append("</details>")
    return "\n".join(lines)
