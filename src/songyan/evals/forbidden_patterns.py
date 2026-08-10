"""Pattern-level forbidden detectors for calibration reports and rule audit."""

from __future__ import annotations

import re
from dataclasses import dataclass


@dataclass(frozen=True)
class ForbiddenPatternMatch:
    """One regex-level forbidden match."""

    label: str
    matched_text: str
    start: int
    end: int


_PATTERN_RULES: tuple[tuple[str, tuple[str, ...], tuple[re.Pattern[str], ...]], ...] = (
    (
        "经纬度坐标",
        ("具体经纬度", "坐标值", "深空坐标", "解码出坐标", "科伊博带边缘坐标"),
        (
            re.compile(r"东经\s*\d+(?:\.\d+)?"),
            re.compile(r"北纬\s*\d+(?:\.\d+)?"),
            re.compile(r"经纬度"),
        ),
    ),
    (
        "沈弥身份化线索",
        ("沈弥的声音", "沈弥的脸", "自然人身份", "沈弥本人回归", "沈弥回归"),
        (
            re.compile(r"沈弥.{0,12}(?:ID|工号|模板|签名|签名栏|生物特征|静态存档)"),
            re.compile(r"(?:ID|工号|模板|签名|签名栏|生物特征|静态存档).{0,12}沈弥"),
        ),
    ),
    (
        "提前节点机制",
        ("节点九", "静海站", "继任者协议", "继承程序", "节点重生"),
        (
            re.compile(r"[A-Z]-\d+\s*节点"),
            re.compile(r"节点\s*[A-Z]-\d+"),
        ),
    ),
    (
        "前三章禁用回溯时间",
        ("三天前", "三天后", "明天", "未来时间戳", "未来第43分钟", "三天前回归"),
        (
            re.compile(r"三天前"),
            re.compile(r"三天后"),
            re.compile(r"昨天"),
            re.compile(r"前天"),
            re.compile(r"明天"),
            re.compile(r"[一二三四五六七八九十两\d]+\s*年前"),
            re.compile(r"过去\s*[一二三四五六七八九十两\d]+\s*年"),
            re.compile(r"未来\s*第?\s*\d+\s*分钟"),
            re.compile(r"未来\s*[一二三四五六七八九十\d]+\s*天"),
        ),
    ),
    (
        "章内时间格式冲突",
        ("三天前", "三天后", "明天", "未来时间戳", "未来第43分钟", "三天前回归"),
        (
            re.compile(r"(?:0[0-5]:\d{2}[\s\S]{0,800}1[2-9]:\d{2})|(?:1[2-9]:\d{2}[\s\S]{0,800}0[0-5]:\d{2})"),
        ),
    ),
)


def detect_forbidden_patterns(
    text: str,
    forbidden_terms: list[str],
) -> list[ForbiddenPatternMatch]:
    """Detect regex-level forbidden patterns implied by explicit terms."""
    active_terms = {str(term).strip() for term in forbidden_terms if str(term).strip()}
    matches: list[ForbiddenPatternMatch] = []
    seen: set[tuple[str, int, int]] = set()
    for label, trigger_terms, patterns in _PATTERN_RULES:
        if not any(term in active_terms for term in trigger_terms):
            continue
        for pattern in patterns:
            for match in pattern.finditer(text):
                if match.group(0) in active_terms:
                    continue
                key = (label, match.start(), match.end())
                if key in seen:
                    continue
                seen.add(key)
                matches.append(
                    ForbiddenPatternMatch(
                        label=label,
                        matched_text=match.group(0),
                        start=match.start(),
                        end=match.end(),
                    )
                )
    matches.sort(key=lambda item: item.start)
    return matches
