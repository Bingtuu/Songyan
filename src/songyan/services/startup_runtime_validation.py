"""V12 startup runtime validation.

The validator enforces startup-stage policy after Writer/Revision and after
SettlementExtractor has produced structured facts, but before accepted head is
written.  It is deterministic and does not call LLMs.
"""

from __future__ import annotations

import os
import re
from pathlib import Path

from pydantic import BaseModel, ConfigDict, Field

from songyan.models import StateSettlement, SupervisionSpec
from songyan.models.supervision import StagePolicy
from songyan.services.supervision_spec import SupervisionSpecError, load_supervision_spec_file


class StartupRuntimeFinding(BaseModel):
    """One deterministic startup runtime violation."""

    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)

    chapter_number: int = Field(ge=1)
    code: str = Field(min_length=1)
    message: str = Field(min_length=1)
    evidence: str = ""
    severity: str = "blocker"


_COORDINATE_RE = re.compile(
    r"\d{1,3}\.\d+\s*,\s*\d{1,3}\.\d+"
    r"|(?<![参])坐标(?![系轴空统转网])"
    r"|经纬度"
)
_RELATIVE_TIME_RE = re.compile(
    r"[一二三四五六七八九十两\d]+\s*(?:年|个月|天)\s*(?:前|后)"
    r"|入职时间\s*[一二三四五六七八九十两\d]+"
    r"|旧(?:案|事故|记录)|历史(?:事故|背景)"
)
_CROSS_LOCATION_RE = re.compile(r"跨区|追踪到|前往|D区|储物柜")
_IDENTITY_SECRET_RE = re.compile(r"身份秘密|权限秘密|账号权限|沈弥账号|自然人身份|系统底层配置")
_NEW_CHARACTER_PATTERNS = (
    re.compile(r"签名是[“\"']?([\u4e00-\u9fff]{2,4})[”\"']?"),
    re.compile(r"显示为[“\"']?([\u4e00-\u9fff]{2,4})[”\"']?"),
    re.compile(r"名(?:叫|为)[“\"']?([\u4e00-\u9fff]{2,4})[”\"']?"),
    re.compile(r"([\u4e00-\u9fff]{2,4})的工牌"),
)
_COMMON_FALSE_NAME_HITS = {
    "系统",
    "货舱",
    "责任",
    "质量",
    "当前",
    "记录",
    "状态",
    "对象",
    "协议",
    "终端",
    # Task 225: UI 状态/颜色词与系统行为描述——"显示为灰色""签名是系统自动验证"
    # 这类界面状态陈述不是人名。
    "灰色",
    "红色",
    "绿色",
    "蓝色",
    "黄色",
    "黑色",
    "白色",
    "空白",
    "为空",
    "一条灰带",
    "已归档",
    "已确认",
    "待确认",
    "正常",
    "异常",
    "离线",
    "在线",
    "锁定",
    "完成",
    "失败",
    "系统自动",
}

# Task 225: "坐标"后接缺失/差异陈述时不揭示任何坐标值，不构成违规。
_COORDINATE_ABSENCE_SUFFIXES = ("不同", "缺失", "为空", "不符", "未知")

# Task 225: "跨区"后接日志/记录类目名时是数据类别而非跨区追逐情节。
_CROSS_LOCATION_CATEGORY_SUFFIXES = ("审计日志", "日志", "记录", "同步", "数据")


def validate_startup_runtime(
    *,
    content: str,
    settlement: StateSettlement,
    spec: SupervisionSpec,
    chapter_number: int,
    allowed_names: set[str] | None = None,
) -> list[StartupRuntimeFinding]:
    """Validate one startup chapter against stage policy."""
    try:
        chapter_spec = spec.chapter(chapter_number)
    except KeyError:
        return [
            StartupRuntimeFinding(
                chapter_number=chapter_number,
                code="missing_chapter_spec",
                message="supervision spec does not define this chapter",
                evidence=str(chapter_number),
            )
        ]

    policy = chapter_spec.stage_policy
    allowed = set(allowed_names or set())
    findings: list[StartupRuntimeFinding] = []
    findings.extend(
        _scan_content(
            content=content,
            policy=policy,
            chapter_number=chapter_number,
            allowed_names=allowed,
        )
    )
    findings.extend(
        _scan_settlement(
            settlement=settlement,
            policy=policy,
            chapter_number=chapter_number,
            allowed_names=allowed,
        )
    )
    return findings


def validate_startup_runtime_from_env(
    *,
    content: str,
    settlement: StateSettlement,
    chapter_number: int,
    allowed_names: set[str] | None = None,
) -> list[StartupRuntimeFinding]:
    """Validate using ``SONGYAN_STARTUP_SUPERVISION_SPEC`` if configured."""
    spec_path = os.environ.get("SONGYAN_STARTUP_SUPERVISION_SPEC")
    if not spec_path:
        return []
    try:
        spec = load_supervision_spec_file(Path(spec_path))
    except SupervisionSpecError as exc:
        return [
            StartupRuntimeFinding(
                chapter_number=chapter_number,
                code="supervision_spec_invalid",
                message="startup supervision spec is invalid",
                evidence=str(exc),
            )
        ]
    return validate_startup_runtime(
        content=content,
        settlement=settlement,
        spec=spec,
        chapter_number=chapter_number,
        allowed_names=allowed_names,
    )


def _scan_content(
    *,
    content: str,
    policy: StagePolicy,
    chapter_number: int,
    allowed_names: set[str],
) -> list[StartupRuntimeFinding]:
    findings: list[StartupRuntimeFinding] = []
    if not policy.allow_new_characters:
        findings.extend(_scan_new_named_characters(content, chapter_number, allowed_names))
    if not policy.allow_past_backstory:
        finding = _scan_pattern(
            content,
            _RELATIVE_TIME_RE,
            chapter_number=chapter_number,
            code="past_backstory",
            message="startup draft contains past backstory or relative time",
        )
        if finding:
            findings.append(finding)
    if not policy.allow_coordinates:
        finding = _scan_coordinates(content, chapter_number)
        if finding:
            findings.append(finding)
    if not policy.allow_cross_location_chase:
        finding = _scan_cross_location(content, chapter_number)
        if finding:
            findings.append(finding)
    if not policy.allow_identity_secret_reveal:
        finding = _scan_pattern(
            content,
            _IDENTITY_SECRET_RE,
            chapter_number=chapter_number,
            code="identity_secret_reveal",
            message="startup draft contains identity-secret evidence",
        )
        if finding:
            findings.append(finding)
    return findings


def _scan_settlement(
    *,
    settlement: StateSettlement,
    policy: StagePolicy,
    chapter_number: int,
    allowed_names: set[str],
) -> list[StartupRuntimeFinding]:
    findings: list[StartupRuntimeFinding] = []
    if not policy.allow_new_characters:
        for character in settlement.new_characters:
            name = character.name.strip()
            if name and name not in allowed_names:
                findings.append(
                    StartupRuntimeFinding(
                        chapter_number=chapter_number,
                        code="new_character",
                        message="settlement introduces a new named character",
                        evidence=_compact_evidence(
                            f"{character.name}: {character.background or character.source_quote}"
                        ),
                    )
                )
            background_finding = _scan_pattern(
                character.background,
                _RELATIVE_TIME_RE,
                chapter_number=chapter_number,
                code="character_background",
                message="new character contains startup-forbidden background",
            )
            if background_finding:
                findings.append(background_finding)

    for setting in settlement.new_settings:
        text = f"{setting.setting_name}\n{setting.description}\n{setting.source_quote}"
        if not policy.allow_past_backstory:
            finding = _scan_pattern(
                text,
                _RELATIVE_TIME_RE,
                chapter_number=chapter_number,
                code="setting_past_backstory",
                message="new setting contains startup-forbidden historical explanation",
            )
            if finding:
                findings.append(finding)
    return findings


def _scan_new_named_characters(
    content: str,
    chapter_number: int,
    allowed_names: set[str],
) -> list[StartupRuntimeFinding]:
    findings: list[StartupRuntimeFinding] = []
    seen: set[str] = set()
    for pattern in _NEW_CHARACTER_PATTERNS:
        for match in pattern.finditer(content):
            if _is_negated_match(content, match.start(), match.end()):
                continue
            name = match.group(1).strip()
            if (
                name in seen
                or name in allowed_names
                or name in _COMMON_FALSE_NAME_HITS
                or not _looks_like_person_name(name)
                or _overlaps_allowed_name(content, match.start(1), match.end(1), allowed_names)
            ):
                continue
            seen.add(name)
            findings.append(
                StartupRuntimeFinding(
                    chapter_number=chapter_number,
                    code="new_character",
                    message="startup draft appears to introduce a new named character",
                    evidence=_evidence(content, match.start(), match.end()),
                )
            )
    return findings


_ABSENCE_MARKERS = ("没有", "无", "不含")


def _scan_coordinates(content: str, chapter_number: int) -> StartupRuntimeFinding | None:
    """Scan for coordinate evidence; bare "坐标" preceded by absence markers is exempt.

    Task 225 修复：裸词"坐标"在"没有值班席坐标"这类缺席陈述中不揭示任何坐标，
    不应触发红线；数对（31.23, 121.47）与"经纬度"无论是否定语境一律拦截。
    """
    for match in _COORDINATE_RE.finditer(content):
        if _is_negated_match(content, match.start(), match.end()):
            continue
        if match.group(0) == "坐标":
            prefix = content[max(0, match.start() - 8): match.start()]
            if any(marker in prefix for marker in _ABSENCE_MARKERS):
                continue
            if content[match.end(): match.end() + 2] in _COORDINATE_ABSENCE_SUFFIXES:
                continue
        return StartupRuntimeFinding(
            chapter_number=chapter_number,
            code="coordinates",
            message="startup draft contains coordinate evidence",
            evidence=_evidence(content, match.start(), match.end()),
        )
    return None


def _scan_cross_location(content: str, chapter_number: int) -> StartupRuntimeFinding | None:
    """Scan for cross-location chase evidence; log-category names are exempt.

    Task 225 修复："跨区审计日志/跨区同步记录"这类数据类别名不是跨区追逐情节，
    "跨区"后接日志/记录类目词时豁免；其余跨区表述与"追踪到/前往/D区/储物柜"
    维持原红线。
    """
    for match in _CROSS_LOCATION_RE.finditer(content):
        if _is_negated_match(content, match.start(), match.end()):
            continue
        if match.group(0) == "跨区":
            suffix = content[match.end(): match.end() + 4]
            if any(suffix.startswith(cat) for cat in _CROSS_LOCATION_CATEGORY_SUFFIXES):
                continue
        return StartupRuntimeFinding(
            chapter_number=chapter_number,
            code="cross_location_chase",
            message="startup draft contains cross-location chase evidence",
            evidence=_evidence(content, match.start(), match.end()),
        )
    return None


def _scan_pattern(
    text: str,
    pattern: re.Pattern[str],
    *,
    chapter_number: int,
    code: str,
    message: str,
) -> StartupRuntimeFinding | None:
    match = pattern.search(text)
    if not match or _is_negated_match(text, match.start(), match.end()):
        return None
    return StartupRuntimeFinding(
        chapter_number=chapter_number,
        code=code,
        message=message,
        evidence=_evidence(text, match.start(), match.end()),
    )


def _looks_like_person_name(name: str) -> bool:
    return 2 <= len(name) <= 4 and all("\u4e00" <= char <= "\u9fff" for char in name)


def _overlaps_allowed_name(
    content: str,
    start: int,
    end: int,
    allowed_names: set[str],
) -> bool:
    """Task 225 修复：匹配片段与既有角色名重叠时视为同一人物，不判新角色。

    例如"沈砚把左腕的工牌"中，"XX的工牌"模式会贪婪命中"砚把左腕"，
    但该片段与 allowed_names 中的"沈砚"重叠，属于主角自己的工牌。
    """
    for name in allowed_names:
        if not name:
            continue
        idx = content.find(name)
        while idx != -1:
            if idx < end and start < idx + len(name):
                return True
            idx = content.find(name, idx + 1)
    return False


def _is_negated_match(text: str, start: int, end: int) -> bool:
    window = text[max(0, start - 18): min(len(text), end + 18)]
    negation_markers = (
        "不提前揭示",
        "不揭示",
        "不展开",
        "不使用",
        "不引入",
        "不新增",
        "避免",
        "禁止",
        "不得",
        "无需",
    )
    return any(marker in window for marker in negation_markers)


def _evidence(text: str, start: int, end: int) -> str:
    return _compact_evidence(text[max(0, start - 40): min(len(text), end + 40)])


def _compact_evidence(text: str) -> str:
    return " ".join(text.replace("\n", " ").split())
