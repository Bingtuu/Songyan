"""Settlement 验证 — source_quote、old_value、公式校验."""

from __future__ import annotations

import difflib
import math
import re
from typing import Any

import structlog

from songyan.models import (
    CharacterState,
    NewSetting,
    NumericalUpdate,
    StateSettlement,
)
from songyan.utils.numerical_validator import NUMERICAL_TOLERANCE

from ._setting_quality import _is_valid_setting_key

logger = structlog.get_logger(__name__)

# Task 170p: 新角色登记的噪声过滤——代词/泛称不得当作具名角色。
_NEW_CHARACTER_NAME_STOPWORDS = frozenset(
    {
        "他", "她", "它", "我", "你", "他们", "她们", "它们", "我们", "你们",
        "对方", "众人", "大家", "所有人", "有人", "某人", "那人", "此人",
        "声音", "身影", "人影", "投影", "残影",
    }
)

_TELEMETRY_ATTRIBUTE_KEYWORDS = (
    "temperature",
    "温度",
    "countdown",
    "timer",
    "_time",
    "duration",
    "time_reading",
    "倒计时",
    "激活时间",
    "耗时",
    "时间读数",
    "heart_rate",
    "心率",
    "脉搏",
    "oxygen",
    "氧气",
    "氧浓度",
    "氧含量",
    "pressure",
    "压力",
    "舱压",
    "frequency",
    "频率",
    "赫兹",
    "ratio",
    "比例",
    "比率",
    "rate",
    "match_rate",
    "匹配度",
    "phase_offset",
    "phase offset",
    "相位偏移",
    "相位差",
    "速度",
    "speed",
    "完成度",
    "进度",
    "百分比",
    "percent",
    "progress",
    "completion",
    "gap",
    "door_gap",
    "间隙",
    "门缝",
    "period",
    "周期",
    "decay",
    "衰减",
    "depth",
    "深度",
    "distance",
    "距离",
    # Task 138l: 科幻文本中常见的遥测快照属性
    "pulse",
    "signal",
    "transmission",
    "latency",
    "delay",
    "coordinate",
    "arcsecond",
    "error",
    "deviation",
    # Task 172: 玄幻/武侠寿命读数
    "lifespan",
    "life_span",
    "remaining_lifespan",
    "寿元",
    "余寿",
    "剩余寿命",
    "寿命",
)
_TELEMETRY_QUANTITY_ATTRIBUTE_PATTERNS = ("文字数量", "文字数", "脉冲数")
_TELEMETRY_ALIAS_GROUPS: tuple[tuple[tuple[str, ...], tuple[str, ...]], ...] = (
    (("heart_rate", "心率", "脉搏"), ("heart_rate", "心率", "脉搏")),
    (
        ("oxygen", "氧气", "氧浓度", "氧含量"),
        ("oxygen", "oxygen_concentration", "氧气浓度", "氧浓度", "氧含量"),
    ),
    (
        ("pressure", "压力", "舱压"),
        ("pressure", "chamber_pressure", "压力", "舱压", "舱室压力", "腔室压力"),
    ),
    (
        ("frequency", "频率", "赫兹"),
        ("frequency", "频率", "赫兹", "Hz", "hz", "kHz", "khz"),
    ),
    (("ratio", "比例", "比率"), ("ratio", "比例", "比率", "配比")),
    (
        ("phase_offset", "phase offset", "相位偏移", "相位差"),
        ("phase_offset", "phase offset", "相位偏移", "相位差"),
    ),
    (
        ("_time", "duration", "time_reading", "激活时间", "耗时", "时间读数"),
        (
            "activation_time",
            "duration",
            "time_reading",
            "激活时间",
            "耗时",
            "用时",
            "持续时间",
            "时间读数",
        ),
    ),
    (("速度", "speed"), ("速度", "speed", "生长速度", "组织生长速度")),
    (
        ("gap", "door_gap", "间隙", "门缝"),
        ("gap", "door_gap", "door gap", "间隙", "门缝", "门缝读数"),
    ),
    (
        ("period", "周期"),
        ("period", "周期", "收缩周期", "舒张周期"),
    ),
    (
        ("decay", "衰减"),
        ("decay", "衰减", "张力衰减", "弹簧张力衰减"),
    ),
    (
        ("depth", "深度"),
        ("depth", "深度", "距离"),
    ),
    (
        ("distance", "距离"),
        ("distance", "距离"),
    ),
    # Task 138l: 信号 / 脉冲 / 传输
    (
        ("signal", "pulse", "transmission", "信号", "脉冲", "传输"),
        ("signal", "pulse", "transmission", "信号", "脉冲", "传输"),
    ),
    # Task 138l: 延迟 / 响应时间
    (
        ("latency", "delay", "response_time", "延迟", "响应时间"),
        ("latency", "delay", "response_time", "延迟", "响应时间"),
    ),
    # Task 138l: 坐标 / 误差 / 偏差
    (
        ("coordinate", "arcsecond", "error", "deviation", "坐标", "误差", "偏差"),
        ("coordinate", "arcsecond", "error", "deviation", "坐标", "误差", "偏差"),
    ),
    (("脉冲数",), ("脉冲数", "指令脉冲数", "自毁指令脉冲数")),
    (("文字数量", "文字数"), ("文字数量", "文字数")),
    # Task 172: 玄幻/武侠寿命读数（余寿、寿元等）按遥测快照处理
    (
        ("lifespan", "life_span", "remaining_lifespan", "寿元", "余寿", "剩余寿命", "寿命"),
        (
            "lifespan",
            "life_span",
            "remaining_lifespan",
            "remaining_lifespan_days",
            "寿元",
            "余寿",
            "剩余寿命",
            "寿命",
        ),
    ),
)
_CHINESE_DIGITS = {
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


def _normalize_text(text: str) -> str:
    """统一空白字符：去头尾空格、压缩连续空白、统一换行符."""
    text = text.strip().replace("\r\n", "\n").replace("\r", "\n")
    text = re.sub(r"\n+", "\n", text)
    text = re.sub(r"[ \t]+", " ", text)
    return text


def _quote_in_content(quote: str, content: str, threshold: float = 0.8) -> bool:
    """模糊检查 quote 是否存在于 content 中.

    先尝试精确匹配（归一化后），再尝试 difflib 块匹配。
    """
    if not quote or not content:
        return True  # 空 quote 视为通过

    norm_quote = _normalize_text(quote)
    norm_content = _normalize_text(content)

    # 1. 精确子串匹配（归一化后）
    if norm_quote in norm_content:
        return True

    # 2. 模糊匹配：滑动窗口找最佳相似度
    quote_len = len(norm_quote)
    if quote_len == 0:
        return True

    best_ratio = 0.0
    step = max(1, quote_len // 4)
    for i in range(0, len(norm_content) - quote_len + 1, step):
        window = norm_content[i : i + quote_len]
        ratio = difflib.SequenceMatcher(None, norm_quote, window).ratio()
        if ratio > best_ratio:
            best_ratio = ratio
        if best_ratio >= threshold:
            return True

    return False


def _is_telemetry_attribute(attribute_name: str) -> bool:
    """读数型属性只记录状态快照，不强制要求台账式增减过程."""
    normalized = attribute_name.lower()
    return any(keyword in normalized for keyword in _TELEMETRY_ATTRIBUTE_KEYWORDS) or any(
        pattern in attribute_name for pattern in _TELEMETRY_QUANTITY_ATTRIBUTE_PATTERNS
    )


def _is_telemetry_formula(formula: str) -> bool:
    """LLM 显式声明为 telemetry snapshot 的公式也按遥测快照处理."""
    return bool(formula) and "telemetry" in formula.lower()


def _parse_chinese_integer(text: str) -> int | None:
    """解析 0-999 范围内的中文整数，用于温度读数。"""
    if not text:
        return None
    if text.isdigit():
        return int(text)
    if all(ch in _CHINESE_DIGITS for ch in text):
        value = 0
        for ch in text:
            value = value * 10 + _CHINESE_DIGITS[ch]
        return value

    total = 0
    section = 0
    number = 0
    for ch in text:
        if ch in _CHINESE_DIGITS:
            number = _CHINESE_DIGITS[ch]
        elif ch == "十":
            section += (number or 1) * 10
            number = 0
        elif ch == "百":
            section += (number or 1) * 100
            number = 0
        else:
            return None
    total += section + number
    return total


def _parse_chinese_number(text: str) -> float | None:
    """解析中文小数，如“四十七点三”."""
    if "点" not in text:
        integer = _parse_chinese_integer(text)
        return float(integer) if integer is not None else None

    integer_text, decimal_text = text.split("点", 1)
    integer = _parse_chinese_integer(integer_text)
    if integer is None or not decimal_text:
        return None
    digits: list[str] = []
    for ch in decimal_text:
        if ch not in _CHINESE_DIGITS:
            return None
        digits.append(str(_CHINESE_DIGITS[ch]))
    return float(f"{integer}.{''.join(digits)}")


def _extract_temperature_readings(text: str) -> list[float]:
    """提取带“度”的温度读数，避免把普通数字误判为温度."""
    readings: list[float] = []
    for match in re.finditer(r"(-?\d+(?:\.\d+)?)\s*度", text):
        readings.append(float(match.group(1)))
    chinese_pattern = r"([零〇一二两三四五六七八九十百点]+)\s*度"
    for match in re.finditer(chinese_pattern, text):
        value = _parse_chinese_number(match.group(1))
        if value is not None:
            readings.append(value)

    # 温度遥测有时写作“温度继续下降。52.0，51.3，50.6。”，
    # 数字本身不带“度”，但前文已有明确温度关键词。
    number = _numeric_reading_pattern()
    keyword_pattern = r"(?:temperature|温度|温度曲线|义肢温度|温度传感器)"
    for match in re.finditer(
        rf"{keyword_pattern}[^\d\-零〇一二两三四五六七八九十百点\n]{{0,16}}"
        rf"((?:{number}(?:\s*[，,、。；;]\s*|\s+|$)){{1,8}})",
        text,
        flags=re.IGNORECASE,
    ):
        for raw_value in re.findall(number, match.group(1)):
            value = _parse_numeric_reading(raw_value)
            if value is not None:
                readings.append(value)
    return readings


def _extract_countdown_readings(text: str) -> list[float]:
    """提取 HH:MM:SS 或 MM:SS 倒计时读数，统一为秒."""
    readings: list[float] = []
    pattern = r"(?<!\d)(?:(\d{1,2}):)?(\d{2}):(\d{2})(?!\d)"
    for match in re.finditer(pattern, text):
        hours = int(match.group(1) or 0)
        minutes = int(match.group(2))
        seconds = int(match.group(3))
        readings.append(float(hours * 3600 + minutes * 60 + seconds))

    chinese_time_pattern = r"(\d{1,3})\s*小时\s*(\d{1,2})\s*分\s*(\d{1,2})\s*秒"
    for match in re.finditer(chinese_time_pattern, text):
        hours = int(match.group(1))
        minutes = int(match.group(2))
        seconds = int(match.group(3))
        readings.append(float(hours * 3600 + minutes * 60 + seconds))

    number = _numeric_reading_pattern()
    keyword_pattern = r"(?:倒计时|countdown|timer|emp_countdown|EMP倒计时|电磁脉冲倒计时)"
    for match in re.finditer(
        rf"{keyword_pattern}[^\d零〇一二两三四五六七八九十百点\n]{{0,16}}{number}\s*秒",
        text,
        flags=re.IGNORECASE,
    ):
        value = _parse_numeric_reading(match.group(1))
        if value is not None:
            readings.append(value)

    for match in re.finditer(
        rf"{keyword_pattern}[^\d零〇一二两三四五六七八九十百点\n]{{0,16}}{number}\s*分钟",
        text,
        flags=re.IGNORECASE,
    ):
        value = _parse_numeric_reading(match.group(1))
        if value is not None:
            readings.append(value * 60)

    zero_pattern = rf"{keyword_pattern}[^\n]{{0,16}}(?:归零|清零|归于零|回到零)"
    if re.search(zero_pattern, text, flags=re.IGNORECASE):
        readings.append(0.0)
    return readings


def _extract_progress_readings(text: str) -> list[float]:
    """提取完成度、进度、百分比读数，统一为 0-100 的百分数."""
    readings: list[float] = []
    chinese_number = r"([零〇一二两三四五六七八九十百点]+)"

    for match in re.finditer(r"(-?\d+(?:\.\d+)?)\s*(?:%|％|个百分点)", text):
        readings.append(float(match.group(1)))

    for match in re.finditer(rf"百分之\s*{chinese_number}", text):
        value = _parse_chinese_number(match.group(1))
        if value is not None:
            readings.append(value)

    for match in re.finditer(rf"{chinese_number}\s*个百分点", text):
        value = _parse_chinese_number(match.group(1))
        if value is not None:
            readings.append(value)

    # 进度类属性常写作“完成度达到九十四”或“进度为 94”，没有显式百分号。
    keyword_pattern = r"(?:完成度|进度|百分比|匹配度|percent|progress|completion|match_rate|rate)"
    numeric_pattern = r"(-?\d+(?:\.\d+)?)"
    for match in re.finditer(
        rf"{keyword_pattern}[^\d零〇一二两三四五六七八九十百点]{{0,12}}{numeric_pattern}",
        text,
        flags=re.IGNORECASE,
    ):
        readings.append(float(match.group(1)))

    for match in re.finditer(
        rf"{keyword_pattern}[^\d零〇一二两三四五六七八九十百点]{{0,12}}{chinese_number}",
        text,
        flags=re.IGNORECASE,
    ):
        value = _parse_chinese_number(match.group(1))
        if value is not None:
            readings.append(value)

    return readings


def _convert_lifespan_unit(value: float, unit: str) -> float:
    """统一寿命单位为天数；年/岁按 365 天换算。"""
    if unit in ("年", "岁"):
        return value * 365.0
    return value


def _extract_lifespan_readings(text: str) -> list[float]:
    """提取寿命/余寿/寿元类读数，统一为天数。

    覆盖常见表达：
    - “活不过三日”“余寿三日”“寿命只剩三天”
    - “寿元将尽”“生机耗尽”等归零表述
    """
    readings: list[float] = []
    number = _numeric_reading_pattern()
    unit = r"(天|日|年|岁)"
    keyword_pattern = (
        r"(?:余寿|剩余寿命|寿命|活不过|只剩|仅余|仅剩下|"
        r"只剩下|余下|还有|可活|命|寿元)"
    )

    # keyword + number + unit，如“寿命只剩三天”
    for match in re.finditer(
        rf"{keyword_pattern}[^\d零〇一二两三四五六七八九十百点\n]{{0,16}}"
        rf"{number}\s*{unit}",
        text,
    ):
        value = _parse_numeric_reading(match.group(1))
        if value is not None:
            readings.append(_convert_lifespan_unit(value, match.group(2)))

    # number + unit + keyword，如“三日可活”
    for match in re.finditer(
        rf"{number}\s*{unit}[^\d零〇一二两三四五六七八九十百点\n]{{0,16}}"
        rf"{keyword_pattern}",
        text,
    ):
        value = _parse_numeric_reading(match.group(1))
        if value is not None:
            readings.append(_convert_lifespan_unit(value, match.group(2)))

    # 无数字的归零表述
    zero_phrases = r"(?:生机耗尽|寿元耗尽|将死|濒死|命不久矣|必死无疑|死期将至)"
    if re.search(zero_phrases, text):
        readings.append(0.0)

    return readings


def _numeric_reading_pattern() -> str:
    chinese_number = r"[零〇一二两三四五六七八九十百点]+"
    return rf"(-?\d+(?:\.\d+)?|{chinese_number})"


def _parse_numeric_reading(text: str) -> float | None:
    if re.fullmatch(r"-?\d+(?:\.\d+)?", text):
        return float(text)
    return _parse_chinese_number(text)


def _telemetry_aliases(attribute_name: str) -> tuple[str, ...]:
    normalized = attribute_name.lower()
    aliases = {attribute_name}
    for triggers, group_aliases in _TELEMETRY_ALIAS_GROUPS:
        if any(trigger.lower() in normalized for trigger in triggers):
            aliases.update(group_aliases)
    if "emp" in normalized and ("countdown" in normalized or "倒计时" in attribute_name):
        aliases.update(("EMP倒计时", "电磁脉冲倒计时", "倒计时"))
    return tuple(sorted(aliases, key=len, reverse=True))


def _extract_alias_telemetry_readings(text: str, aliases: tuple[str, ...]) -> list[float]:
    """提取读数类属性附近的数值，不放开普通数量台账."""
    readings: list[float] = []
    number = _numeric_reading_pattern()
    for alias in aliases:
        escaped_alias = re.escape(alias)
        pattern = rf"{escaped_alias}[^\d\-零〇一二两三四五六七八九十百点\n]{{0,24}}{number}"
        for match in re.finditer(pattern, text):
            value = _parse_numeric_reading(match.group(1))
            if value is not None:
                readings.append(value)
    return readings


def _telemetry_evidence_text(num: NumericalUpdate, content: str) -> str:
    """汇总读数证据来源。"""
    parts = [content]
    for inc in num.increments:
        parts.append(inc.source_quote)
    for dec in num.decrements:
        parts.append(dec.source_quote)
    return "\n".join(part for part in parts if part)


def _find_telemetry_reading(num: NumericalUpdate, content: str) -> float | None:
    if not _is_telemetry_attribute(num.attribute_name) and not _is_telemetry_formula(num.formula):
        return None

    evidence = _telemetry_evidence_text(num, content)
    attr = num.attribute_name.lower()
    readings: list[float] = []
    if "倒计时" in attr or "countdown" in attr or "timer" in attr:
        readings = _extract_countdown_readings(evidence)
    elif "温度" in attr or "temperature" in attr:
        readings = _extract_temperature_readings(evidence)
    elif (
        "完成度" in attr
        or "进度" in attr
        or "百分比" in attr
        or "匹配度" in attr
        or "percent" in attr
        or "progress" in attr
        or "completion" in attr
        or "match_rate" in attr
    ):
        readings = _extract_progress_readings(evidence)
    elif (
        "寿命" in attr
        or "lifespan" in attr
        or "life_span" in attr
        or "寿元" in attr
        or "余寿" in attr
    ):
        readings = _extract_lifespan_readings(evidence)
    else:
        readings = _extract_alias_telemetry_readings(
            evidence, _telemetry_aliases(num.attribute_name)
        )

    if not readings:
        return None

    # 选取与 LLM closing_value 最接近的明示读数；温度可容忍“四十七点三”被取整为 47。
    closest = min(readings, key=lambda value: abs(value - num.closing_value))
    if abs(closest - num.closing_value) <= 0.5:
        return closest
    return None


def _normalize_telemetry_snapshot(num: NumericalUpdate, content: str) -> bool:
    """把明确读数型 numerical_update 规整为快照，避免过度台账化."""
    if not _is_telemetry_attribute(num.attribute_name) and not _is_telemetry_formula(num.formula):
        return False
    reading = _find_telemetry_reading(num, content)
    if reading is None:
        return False

    expected = (
        num.opening_value
        + sum(i.amount for i in num.increments)
        - sum(d.amount for d in num.decrements)
    )
    if abs(num.closing_value - expected) <= NUMERICAL_TOLERANCE:
        return False

    original_opening = num.opening_value
    original_closing = num.closing_value
    original_formula = num.formula
    num.opening_value = reading
    num.increments = []
    num.decrements = []
    num.closing_value = reading
    num.formula = f"telemetry_snapshot: {reading}"
    logger.info(
        "settlement.numerical_telemetry_normalized",
        character_id=num.character_id,
        attribute_name=num.attribute_name,
        original_opening=original_opening,
        original_closing=original_closing,
        original_formula=original_formula,
        normalized_value=reading,
    )
    return True


def _numerical_formula_expected(num: NumericalUpdate) -> float:
    return (
        num.opening_value
        + sum(i.amount for i in num.increments)
        - sum(d.amount for d in num.decrements)
    )


def _is_formula_mismatch(num: NumericalUpdate) -> bool:
    expected = _numerical_formula_expected(num)
    return abs(num.closing_value - expected) > NUMERICAL_TOLERANCE


def _should_filter_unevidenced_numerical_update(
    num: NumericalUpdate,
    content: str,
) -> bool:
    """Task 138f: 读数型字段无明确证据时不进入有效数值结算.

    真实 ledger 字段仍由公式硬校验阻断；这里只处理 telemetry snapshot
    候选，避免 LLM 从概念性正文推断不存在的数值。
    """
    if not _is_telemetry_attribute(num.attribute_name) and not _is_telemetry_formula(num.formula):
        return False
    if not _is_formula_mismatch(num):
        return False
    # Task 138l: 公式声明 telemetry snapshot 但属性名不在关键词列表时，
    # 只有在没有真实台账增减记录的情况下才按无证据快照过滤，避免绕过 ledger 硬校验。
    if _is_telemetry_formula(num.formula) and not _is_telemetry_attribute(num.attribute_name):
        if num.increments or num.decrements:
            return False
    return _find_telemetry_reading(num, content) is None


def _filter_new_characters(
    settlement: StateSettlement,
    content: str,
    existing_character_names: set[str],
    chapter_number: int,
    project_id: str,
) -> None:
    """Task 170p: 对 new_characters 做证据门禁与去重，就地剔除不合格条目.

    门禁规则（任一不满足即剔除，仅记 diagnostic，不阻断整章结算）：
    1. name 非空、去空白后长度 2-6、非代词/泛称停用词。
    2. name 实际出现在正文中（LLM 不得凭空捏造角色）。
    3. source_quote 能在正文中模糊匹配（与 NewSetting 同纪律）。
    4. 不与已存在角色重名（幂等，避免重复入库）。
    5. 同一结算内 name 去重（保留首个）。
    """
    if not settlement.new_characters:
        return

    kept: list[Any] = []
    seen_names: set[str] = set()
    existing_lower = {n.strip() for n in existing_character_names if n}

    for nc in settlement.new_characters:
        name = (nc.name or "").strip()
        reason: str | None = None
        if not (2 <= len(name) <= 6):
            reason = "name_length_invalid"
        elif name in _NEW_CHARACTER_NAME_STOPWORDS:
            reason = "name_is_pronoun_or_generic"
        elif name in seen_names:
            reason = "duplicate_in_settlement"
        elif name in existing_lower:
            reason = "already_exists"
        elif name not in content:
            reason = "name_not_in_content"
        elif nc.source_quote and not _quote_in_content(nc.source_quote, content):
            reason = "source_quote_not_in_content"

        if reason is not None:
            logger.info(
                "settlement.new_character_filtered",
                name=name,
                role_type=nc.role_type,
                reason=reason,
                project_id=project_id,
                chapter_number=chapter_number,
            )
            continue

        seen_names.add(name)
        kept.append(nc)

    settlement.new_characters = kept


async def _validate_settlement(
    settlement: StateSettlement,
    content: str,
    current_states: list[CharacterState],
    current_settings: list[NewSetting],
    chapter_number: int = 0,
    project_id: str = "",
    existing_character_names: set[str] | None = None,
    resolvable_foreshadowing_ids: set[str] | None = None,
) -> list[str]:
    """验证结算结果，返回错误列表.

    Task 114a 修复：
    - old_value 由 DB 事实源回填，不再依赖 LLM 精确复现
    - 对未知角色/字段或异常变更触发校验警告，不静默掩盖

    Task 170p:
    - new_characters 证据门禁：source_quote / name 必须在正文中出现，
      过滤代词/泛称，去重已存在角色；不合格条目就地剔除，不阻断整章结算。

    Task 172c.r:
    - resolve 防幻觉校验：resolve 缺 ``foreshadowing_id`` 或目标 id 不在
      当前可 resolve 集合（``resolvable_foreshadowing_ids``，含 overdue）时，
      丢弃该条并记 warning，不阻断整章结算；``None`` 表示调用方未提供
      可 resolve 集合，只做缺 id 检查（旧行为兼容）。
    """
    errors: list[str] = []

    # Task 170p: 新角色证据门禁与去重（就地过滤，不阻断整章结算）
    _filter_new_characters(
        settlement=settlement,
        content=content,
        existing_character_names=existing_character_names or set(),
        chapter_number=chapter_number,
        project_id=project_id,
    )

    # 1. 验证并回填 character_update.old_value
    # Task 114a: old_value 由代码从 DB 事实源回填，不再依赖 LLM 精确复现
    state_map: dict[tuple[str, str], str] = {
        (s.character_id, s.field): s.value for s in current_states
    }
    for update in settlement.character_updates:
        key = (update.character_id, update.field)
        if key in state_map:
            db_value = state_map[key]
            if db_value != update.old_value:
                # Task 114a: 用 DB 事实源回填 old_value
                logger.info(
                    "settlement.old_value_backfilled",
                    character_id=update.character_id,
                    field=update.field,
                    llm_old_value_length=len(update.old_value),
                    db_value_length=len(db_value),
                    project_id=project_id,
                    chapter_number=chapter_number,
                )
                update.old_value = db_value
        else:
            # 未知角色/字段：记录警告但不阻断
            logger.warning(
                "settlement.unknown_character_field",
                character_id=update.character_id,
                field=update.field,
                project_id=project_id,
                chapter_number=chapter_number,
            )

    # 2. 验证 source_quote 在正文中存在（模糊匹配）
    # 注：空 source_quote 表示已被 _quote_filter 过滤，跳过验证
    for update in settlement.character_updates:
        if update.source_quote and not _quote_in_content(update.source_quote, content):
            errors.append(
                f"角色 {update.character_id} 的 source_quote "
                f"未在正文中找到: '{update.source_quote[:50]}...'"
            )
    for setting in settlement.new_settings:
        if setting.source_quote and not _quote_in_content(setting.source_quote, content):
            errors.append(
                f"设定 '{setting.setting_name}' 的 source_quote "
                f"未在正文中找到: '{setting.source_quote[:50]}...'"
            )

    # 3. 验证 setting_key 唯一性和格式
    existing_keys = {s.setting_key for s in current_settings if s.setting_key}
    for setting in settlement.new_settings:
        if setting.setting_key:
            if setting.setting_key in existing_keys:
                # Task 094: 去重已在代码层处理，此处仅记录 warning 不报错
                logger.info(
                    "settlement.duplicate_key_skipped",
                    key=setting.setting_key,
                    project_id=project_id,
                )
            if not _is_valid_setting_key(setting.setting_key):
                errors.append(
                    f"设定 '{setting.setting_name}' 的 setting_key "
                    f"'{setting.setting_key}' 格式无效，"
                    f"必须为 category.subcategory.name 三段式小写 key"
                )

    # 4. 验证 numerical_update.closing_value 公式
    validated_numerical_updates: list[NumericalUpdate] = []
    for num in settlement.numerical_updates:
        _normalize_telemetry_snapshot(num, content)
        expected = _numerical_formula_expected(num)
        if _should_filter_unevidenced_numerical_update(num, content):
            logger.warning(
                "settlement.numerical_unevidenced_filtered",
                character_id=num.character_id,
                attribute_name=num.attribute_name,
                opening_value=num.opening_value,
                closing_value=num.closing_value,
                expected_value=expected,
                formula=num.formula,
                project_id=project_id,
                chapter_number=chapter_number,
            )
            continue
        validated_numerical_updates.append(num)
        if abs(num.closing_value - expected) > NUMERICAL_TOLERANCE:
            # 171w-d: closing_value 为 0.0/缺省但公式可计算时，从公式推导
            closing_is_default = (
                num.closing_value == 0.0
                or math.isinf(num.closing_value)
            )
            has_ledger_evidence = bool(
                num.increments or num.decrements or num.opening_value != 0.0
            )
            if closing_is_default and has_ledger_evidence:
                logger.info(
                    "settlement.numerical_closing_autocorrected",
                    character_id=num.character_id,
                    attribute_name=num.attribute_name,
                    llm_closing_value=num.closing_value,
                    computed_closing=expected,
                    project_id=project_id,
                    chapter_number=chapter_number,
                )
                num.closing_value = expected
            else:
                errors.append(
                    f"角色 {num.character_id} 的 {num.attribute_name} "
                    f"closing_value ({num.closing_value}) 不等于 "
                    f"公式值 ({expected:.3f})"
                )
    settlement.numerical_updates = validated_numerical_updates

    # 5. 验证 foreshadowing_update.source_version_id
    validated_foreshadowing_updates = []
    for fs in settlement.foreshadowing_updates:
        if not fs.source_version_id:
            errors.append(
                f"伏笔 '{fs.description[:30]}...' 的 source_version_id 为空"
            )
        # 172c.r: resolve 防幻觉校验——缺 id 或目标不在可 resolve 集合时
        # 丢弃该条并记 warning，不阻断整章结算（与 170p new_characters 同级容错）。
        if fs.operation == "resolve":
            if not fs.foreshadowing_id:
                logger.warning(
                    "settlement.foreshadowing_resolve_missing_id",
                    description=fs.description[:50],
                    project_id=project_id,
                    chapter_number=chapter_number,
                )
                continue
            if (
                resolvable_foreshadowing_ids is not None
                and fs.foreshadowing_id not in resolvable_foreshadowing_ids
            ):
                logger.warning(
                    "settlement.foreshadowing_resolve_unknown_id",
                    foreshadowing_id=fs.foreshadowing_id,
                    description=fs.description[:50],
                    project_id=project_id,
                    chapter_number=chapter_number,
                )
                continue
        validated_foreshadowing_updates.append(fs)
        # Task 094: 验证 expected_resolve_chapter 必须在当前章节之后。
        # Task 121e: LLM 常把“近期回收”写成当前章节号；plant 操作在
        # 当前章只能表示新埋设，等于当前章节时安全回填为下一章，
        # 小于当前章节仍保留为硬错误。
        if fs.operation == "plant" and fs.expected_resolve_chapter is not None:
            if fs.expected_resolve_chapter == chapter_number:
                fs.expected_resolve_chapter = chapter_number + 1
                logger.info(
                    "settlement.foreshadowing_expected_chapter_backfilled",
                    description=fs.description[:50],
                    original_expected_chapter=chapter_number,
                    backfilled_expected_chapter=fs.expected_resolve_chapter,
                    project_id=project_id,
                    chapter_number=chapter_number,
                )
            elif fs.expected_resolve_chapter < chapter_number:
                errors.append(
                    f"伏笔 '{fs.description[:30]}...' 的预计回收章节 "
                    f"({fs.expected_resolve_chapter}) 必须大于当前章节 ({chapter_number})"
                )
    settlement.foreshadowing_updates = validated_foreshadowing_updates

    return errors
