"""RuleAuditor Agent — 纯代码规则检测，复用 Quality Utils."""

from __future__ import annotations

import re
import time
import uuid
from difflib import SequenceMatcher
from typing import Any

import structlog

from songyan.db.review_repo import ReviewReportRepository
from songyan.models import (
    DuplicateParagraphMatch,
    ExpositionCarrierMatch,
    GenreRules,
    MergedReviewReport,
    MetaTagLeakMatch,
    MotifFatigueMatch,
    PunchCheck,
    PunchPoint,
    RuleAuditResult,
    TextCleanlinessCleanIssue,
)
from songyan.utils import (
    analyze_paragraph_rhythm,
    check_ending_hook,
    check_opening_hook,
    detect_ai_tells,
    detect_fatigue_words,
)
from songyan.utils._helpers import locate_position, split_paragraphs
from songyan.utils.generic_names import detect_generic_names
from songyan.utils.numerical_validator import (
    NumericalContext,
)
from songyan.utils.truncation import word_count_bounds
from songyan.utils.word_count import count_chinese_words as _count_chinese_words

logger = structlog.get_logger(__name__)

# 简易情感词表（用于情绪转折检测）
_POSITIVE_WORDS = {
    "笑", "喜", "乐", "安", "静", "暖", "光", "希望", "胜利", "成功",
    "轻松", "愉快", "幸福", "满足", "信任", "勇敢", "坚定", "温柔",
}
_NEGATIVE_WORDS = {
    "恐", "惧", "怕", "悲", "痛", "死", "血", "暗", "冷", "绝望",
    "愤怒", "仇恨", "悲伤", "痛苦", "惊恐", "焦虑", "压抑", "窒息",
    "崩溃", "疯狂", "扭曲", "腐烂", "冰冷", "阴冷", "刺骨",
}


def _analyze_scene_emotion(text: str) -> str:
    """基于情感词频判断场景的 dominant emotion."""
    pos = sum(1 for w in _POSITIVE_WORDS if w in text)
    neg = sum(1 for w in _NEGATIVE_WORDS if w in text)
    if neg > pos:
        return "negative"
    if pos > neg:
        return "positive"
    return "neutral"


_META_TAG_PATTERNS: list[tuple[str, str]] = [
    (r"(?s)<!--.*?-->", "HTML注释"),
    (r"(?s)<mark>.*?</mark>", "Mark标签"),
    (r"(?im)^\s*meta:.*", "Meta前缀"),
    (r"(?s)\[\[.*?\]\]", "旧式可见标记"),
]

_MARKDOWN_SCENE_PATTERNS: list[tuple[str, str]] = [
    (r"(?im)^\s*#{1,6}\s*Scene\s+(?:\d+|[A-Z]).*$", "Markdown场景标题"),
    (r"(?im)^\s*Scene\s+(?:\d+|[A-Z])(?:\s*[:：].*)?\s*$", "裸场景标题"),
    (r"(?im)^\s*\*\*Scene\s+(?:\d+|[A-Z])\*\*.*$", "加粗场景标题"),
    (r"(?im)^\s*#{1,6}\s*场景\s*(?:\d+|[A-Z]|[一二三四五六七八九十]+).*$", "Markdown中文场景标题"),
    (r"(?im)^\s*场景\s*(?:\d+|[A-Z]|[一二三四五六七八九十]+)(?:\s*[:：].*)?\s*$", "裸中文场景标题"),
    (r"(?im)^\s*\*\*场景\s*(?:\d+|[A-Z]|[一二三四五六七八九十]+)\*\*.*$", "加粗中文场景标题"),
]

_MARKDOWN_HEADING_PATTERNS: list[tuple[str, str]] = [
    (
        r"(?im)^\s*#{1,6}\s*(?:第\s*)?[一二三四五六七八九十百千万零〇两\d]+\s*(?:章|章节|回)\b.*$",
        "Markdown章节标题",
    ),
    (r"(?im)^\s*#{1,6}\s*Chapter\s+\d+\b.*$", "Markdown英文章节标题"),
]

_PROTECTED_DIRECTIVE_RE = re.compile(
    r"(?im)(?:【[^】]*(?:保护内容|请勿修改|不要修改|不可修改)[^】]*】|"
    r"\b(?:保护内容|请勿修改|不要修改|不可修改)\b)"
)

_PROMPT_PATCH_INSTRUCTION_PATTERNS: list[tuple[str, str]] = [
    (r"(?im)每句末尾.{0,12}(?:加重|加强|强化).{0,8}语气", "句尾语气指令"),
    (
        r"(?im)(?:请|务必|必须).{0,20}(?:改写|修改|替换|保留|删除)"
        r".{0,20}(?:本段|这一段|正文|内容)",
        "写作修改指令",
    ),
    (r"(?im)(?:patch|rewrite|diff)\s*(?:note|instruction|指令|说明)\s*[:：]", "Patch指令"),
]

_CJK_RE = re.compile(r"[\u4e00-\u9fff]")
_ELLIPSIS_PLACEHOLDER_RE = re.compile(r"^(?:[.．。…·\s]+)$")

MotifDefinition = tuple[str, tuple[str, ...], tuple[str, ...]]

DEFAULT_MOTIF_FATIGUE_THRESHOLD = 3

_FATIGUE_MOTIF_DEFINITIONS: tuple[MotifDefinition, ...] = (
    (
        "指尖悬停",
        (r"指尖.{0,6}悬停", r"手指.{0,6}悬停"),
        ("身体重心变化", "环境反应", "配角动作打断", "战术动作"),
    ),
    (
        "左臂发烫",
        (r"左臂.{0,8}(?:发烫|灼|痛|金属化)", r"金属化左臂"),
        ("肩背受力", "呼吸节奏", "设备回震", "伤口牵扯"),
    ),
    (
        "神经接口刺痛",
        (r"神经接口.{0,8}(?:刺痛|发烫|灼痛)", r"颅骨内侧"),
        ("听觉失真", "视野延迟", "平衡感偏移", "记忆闪断"),
    ),
    (
        "倒计时",
        (r"倒计时", r"\d+\s*秒"),
        ("环境临界变化", "对手抢先动作", "配角催促", "系统资源下降"),
    ),
    (
        "控制台数据流",
        (r"控制台.{0,10}(?:数据流|刷新|跳动)", r"全息屏.{0,10}刷新"),
        ("机械噪声变化", "灯光失序", "地面震动", "手动操作反馈"),
    ),
    (
        "共鸣频率",
        (r"共鸣频率.{0,8}(?:跳动|震荡|偏移)", r"频率.{0,8}(?:跳动|震荡)"),
        ("温差变化", "材料裂纹", "角色误判", "局部失控后果"),
    ),
)


def detect_meta_tag_leaks(text: str) -> list[MetaTagLeakMatch]:
    """检测元标记泄漏."""
    matches: list[MetaTagLeakMatch] = []
    seen: set[tuple[int, int]] = set()
    for pattern, tag_type in _META_TAG_PATTERNS:
        for m in re.finditer(pattern, text):
            key = (m.start(), m.end())
            if key in seen:
                continue
            seen.add(key)
            location = locate_position(text, m.start())
            matches.append(
                MetaTagLeakMatch(
                    pattern=f"{tag_type}: {pattern}",
                    matched_text=m.group(),
                    location=location,
                    severity="major",
                    message="检测到元标记泄漏",
                    artifact_type="meta_tag_leak",
                )
            )
    matches.sort(key=lambda x: text.find(x.matched_text))
    return matches


def detect_markdown_scene_titles(text: str) -> list[MetaTagLeakMatch]:
    """检测正文中的 Markdown / 裸场景标题."""
    matches: list[MetaTagLeakMatch] = []
    seen: set[tuple[int, int]] = set()
    for pattern, tag_type in _MARKDOWN_SCENE_PATTERNS:
        for m in re.finditer(pattern, text):
            key = (m.start(), m.end())
            if key in seen:
                continue
            seen.add(key)
            location = locate_position(text, m.start())
            matches.append(
                MetaTagLeakMatch(
                    pattern=f"{tag_type}: {pattern}",
                    matched_text=m.group(),
                    location=location,
                    severity="major",
                    message="检测到 Markdown 场景标题（应使用空行分隔场景）",
                    artifact_type="markdown_scene_title",
                )
            )
    matches.sort(key=lambda x: text.find(x.matched_text))
    return matches


def _line_span_at(text: str, pos: int) -> tuple[int, int]:
    """返回 pos 所在行的 [start, end) span。"""
    start = text.rfind("\n", 0, pos) + 1
    end = text.find("\n", pos)
    if end < 0:
        end = len(text)
    return start, end


def _append_artifact_match(
    matches: list[MetaTagLeakMatch],
    *,
    text: str,
    start: int,
    end: int,
    artifact_type: str,
    pattern: str,
    message: str,
    matched_text: str | None = None,
) -> None:
    """创建带 artifact_type 的 MetaTagLeakMatch。"""
    evidence = (matched_text if matched_text is not None else text[start:end]).strip()
    matches.append(
        MetaTagLeakMatch(
            pattern=pattern,
            matched_text=evidence,
            location=locate_position(text, start),
            severity="major",
            message=message,
            artifact_type=artifact_type,
        )
    )


def _has_cjk_on_both_sides(left: str, right: str) -> bool:
    return bool(_CJK_RE.search(left) and _CJK_RE.search(right))


def _is_safe_slash_context(text: str, slash_pos: int) -> bool:
    """判断 `/` 是否属于单位、URL、路径或数字比值等合法上下文。"""
    left = text[max(0, slash_pos - 16):slash_pos]
    right = text[slash_pos + 1: slash_pos + 17]
    window = left + "/" + right
    if re.search(r"https?://|[A-Za-z]:[/\\]|[/\\][\w.-]+[/\\]", window):
        return True
    if re.search(r"[A-Za-z0-9]\s*/\s*[A-Za-z0-9]", window):
        return True
    if re.search(r"\d+(?:\.\d+)?\s*/\s*\d+(?:\.\d+)?", window):
        return True
    # 常见速度/频率/比例单位，如 km/s、m/s、次/秒、次/分钟。
    # 185: 右侧单位补齐中文时间单位，避免 "47次/分钟" 这类频率被误判为拼接痕。
    if re.search(
        r"(?:km|m|cm|mm|次|米|公里)\s*/\s*(?:s|秒|min|h|小时|分钟|分|天|日|周|月|年)",
        window,
        re.I,
    ):
        return True
    if re.search(
        r"(?:次|米|公里)\s*/\s*\d+(?:\.\d+)?\s*"
        r"(?:s|秒|min|h|小时|分钟|分|天|日|周|月|年)",
        window,
        re.I,
    ):
        return True
    # 187.w: numeric rate units such as "0.2秒/个" are telemetry units,
    # not narrative slash splices.
    if re.search(
        r"\d+(?:\.\d+)?\s*"
        r"(?:毫秒|秒|分钟|分|小时|天|日|周|月|年|次|个|条|份)\s*/\s*"
        r"(?:毫秒|秒|分钟|分|小时|天|日|周|月|年|次|个|条|份)",
        window,
        re.I,
    ):
        return True
    # 187.x: structured system/form messages like `[目标：... / 源数据：...]`
    # use slashes as field separators, not narrative splice artifacts.
    wide_window = text[max(0, slash_pos - 40):slash_pos + 40]
    if re.search(r"\[[^\]]*?[：:][^\]]*?/\s*[^\]]*?[：:]", wide_window):
        return True
    return False


def _detect_slash_splice_artifacts(text: str) -> list[MetaTagLeakMatch]:
    matches: list[MetaTagLeakMatch] = []
    seen_lines: set[tuple[int, int]] = set()
    for m in re.finditer("/", text):
        slash_pos = m.start()
        if _is_safe_slash_context(text, slash_pos):
            continue
        line_start, line_end = _line_span_at(text, slash_pos)
        key = (line_start, line_end)
        if key in seen_lines:
            continue
        line = text[line_start:line_end]
        left = line[: slash_pos - line_start]
        right = line[slash_pos - line_start + 1:]
        if not _has_cjk_on_both_sides(left[-12:], right[:12]):
            continue
        seen_lines.add(key)
        _append_artifact_match(
            matches,
            text=text,
            start=line_start,
            end=line_end,
            artifact_type="slash_splice_artifact",
            pattern="slash_splice_artifact: CJK / CJK",
            message="检测到斜杠拼接痕迹",
        )
    return matches


def _detect_ellipsis_placeholder_paragraphs(text: str) -> list[MetaTagLeakMatch]:
    matches: list[MetaTagLeakMatch] = []
    for paragraph_index, paragraph, start in _paragraphs_with_offsets(text):
        normalized = re.sub(r"\s+", "", paragraph)
        if not _ELLIPSIS_PLACEHOLDER_RE.match(normalized):
            continue
        if normalized.count(".") + normalized.count("．") < 3 and normalized.count("…") < 2:
            continue
        _append_artifact_match(
            matches,
            text=text,
            start=start,
            end=start + len(paragraph),
            artifact_type="ellipsis_placeholder_paragraph",
            pattern="ellipsis_placeholder_paragraph",
            message=f"检测到纯省略号占位段（第{paragraph_index}段）",
        )
    return matches


def detect_text_cleanliness_artifacts(text: str) -> list[MetaTagLeakMatch]:
    """Task 171t: 检测 T9 hard-clean 的新增文本 artifact。"""
    matches: list[MetaTagLeakMatch] = []
    seen: set[tuple[int, int, str]] = set()

    def add_regex_matches(
        pattern: str,
        tag_type: str,
        artifact_type: str,
        message: str,
    ) -> None:
        for m in re.finditer(pattern, text):
            key = (m.start(), m.end(), artifact_type)
            if key in seen:
                continue
            seen.add(key)
            _append_artifact_match(
                matches,
                text=text,
                start=m.start(),
                end=m.end(),
                artifact_type=artifact_type,
                pattern=f"{tag_type}: {pattern}",
                message=message,
            )

    for pattern, tag_type in _MARKDOWN_HEADING_PATTERNS:
        add_regex_matches(
            pattern,
            tag_type,
            "markdown_heading_leak",
            "检测到 Markdown 章节标题泄漏",
        )

    add_regex_matches(
        _PROTECTED_DIRECTIVE_RE.pattern,
        "保护指令",
        "protected_directive_leak",
        "检测到保护/请勿修改指令泄漏",
    )

    for pattern, tag_type in _PROMPT_PATCH_INSTRUCTION_PATTERNS:
        add_regex_matches(
            pattern,
            tag_type,
            "prompt_patch_instruction_leak",
            "检测到 prompt/patch 写作指令泄漏",
        )

    matches.extend(_detect_slash_splice_artifacts(text))
    matches.extend(_detect_ellipsis_placeholder_paragraphs(text))
    matches.sort(key=lambda x: text.find(x.matched_text))
    return matches


def _unique_limited(values: list[str], *, limit: int = 5) -> list[str]:
    """保留少量去重示例，避免 observe 报告膨胀."""
    seen: set[str] = set()
    result: list[str] = []
    for value in values:
        cleaned = value.strip()
        if not cleaned or cleaned in seen:
            continue
        seen.add(cleaned)
        result.append(cleaned)
        if len(result) >= limit:
            break
    return result


def detect_fatigue_motifs(
    text: str,
    *,
    threshold: int = DEFAULT_MOTIF_FATIGUE_THRESHOLD,
) -> list[MotifFatigueMatch]:
    """Task 171v: 检测 Ch200+ 高频母题疲劳（observe-only）."""
    if not text.strip() or threshold <= 0:
        return []

    matches: list[MotifFatigueMatch] = []
    for motif, patterns, alternatives in _FATIGUE_MOTIF_DEFINITIONS:
        matched_texts: list[str] = []
        for pattern in patterns:
            for match in re.finditer(pattern, text):
                matched_texts.append(match.group(0))
        count = len(matched_texts)
        if count < threshold:
            continue
        matches.append(
            MotifFatigueMatch(
                motif=motif,
                count=count,
                threshold=threshold,
                matched_texts=_unique_limited(matched_texts),
                alternatives=list(alternatives),
            )
        )
    return matches


def _normalize_paragraph_for_similarity(paragraph: str) -> str:
    """归一化段落空白，供重复检测计算相似度."""
    return re.sub(r"\s+", "", paragraph.strip())


def _paragraphs_with_offsets(text: str) -> list[tuple[int, str, int]]:
    """返回 1-based 段落序号、段落文本和起始偏移."""
    paragraphs = split_paragraphs(text)
    result: list[tuple[int, str, int]] = []
    cursor = 0
    for idx, paragraph in enumerate(paragraphs, 1):
        start = text.find(paragraph, cursor)
        if start < 0:
            start = text.find(paragraph)
        if start < 0:
            start = cursor
        result.append((idx, paragraph, start))
        cursor = start + len(paragraph)
    return result


def detect_duplicate_paragraphs(
    text: str,
    *,
    min_chars: int = 40,
    similarity_threshold: float = 0.9,
    long_paragraph_chars: int = 100,
    short_similarity_threshold: float = 0.95,
) -> list[DuplicateParagraphMatch]:
    """检出同章内重复长段落并定位（诊断项，不直接阻断）.

    分级阈值：归一化长度 >= long_paragraph_chars 的长段用 similarity_threshold；
    落在 [min_chars, long_paragraph_chars) 的中段改用更严的 short_similarity_threshold，
    只抓近乎逐字的重复。这样既能捕获 70-95 字的近似重复（170c Ch31 漏报），
    又不会误伤刻意的短句 refrain（< min_chars 直接跳过）。
    """
    matches: list[DuplicateParagraphMatch] = []
    seen: list[tuple[int, str, str, int]] = []

    for paragraph_index, paragraph, start in _paragraphs_with_offsets(text):
        normalized = _normalize_paragraph_for_similarity(paragraph)
        if len(normalized) < min_chars:
            continue

        for original_index, original, original_normalized, original_start in seen:
            similarity = (
                1.0
                if normalized == original_normalized
                else SequenceMatcher(None, original_normalized, normalized).ratio()
            )
            effective_threshold = (
                similarity_threshold
                if min(len(normalized), len(original_normalized)) >= long_paragraph_chars
                else short_similarity_threshold
            )
            if similarity < effective_threshold:
                continue
            matches.append(
                DuplicateParagraphMatch(
                    paragraph_index=paragraph_index,
                    duplicate_of_index=original_index,
                    matched_text=paragraph,
                    original_text=original,
                    location=locate_position(text, start),
                    original_location=locate_position(text, original_start),
                    similarity=round(similarity, 4),
                )
            )
            break

        seen.append((paragraph_index, paragraph, normalized, start))

    return matches


def _clean_issue_for_meta_match(
    match: MetaTagLeakMatch,
    *,
    chapter_number: int | None,
    version_id: str | None,
) -> TextCleanlinessCleanIssue:
    issue_type = match.artifact_type or "meta_tag_leak"
    suggested_actions = {
        "meta_tag_leak": "删除工程元标记，仅保留自然正文。",
        "markdown_scene_title": "删除场景标题或编号，使用空行保留场景切换。",
        "markdown_heading_leak": "删除 Markdown 章节标题行，保留正文内容。",
        "protected_directive_leak": "删除保护/请勿修改指令，不改动叙事正文。",
        "slash_splice_artifact": "移除拼接斜杠，按上下文改成自然标点或直接连接句段。",
        "ellipsis_placeholder_paragraph": "删除纯省略号占位段。",
        "prompt_patch_instruction_leak": "删除写作/patch 指令文本，保留叙事内容。",
    }
    return TextCleanlinessCleanIssue(
        chapter_number=chapter_number,
        version_id=version_id,
        issue_type=issue_type,
        evidence_quote=match.matched_text,
        evidence_location=match.location,
        suggested_action=suggested_actions.get(issue_type, "删除非叙事 artifact。"),
        deterministic_cleanable=True,
    )


def _clean_issue_for_duplicate(
    match: DuplicateParagraphMatch,
    *,
    chapter_number: int | None,
    version_id: str | None,
) -> TextCleanlinessCleanIssue:
    return TextCleanlinessCleanIssue(
        chapter_number=chapter_number,
        version_id=version_id,
        issue_type="duplicate_paragraph",
        evidence_quote=match.matched_text,
        evidence_location=match.location,
        suggested_action="保留首次出现段落，删除后续重复长段落；必要时补一处新的自然过渡。",
        deterministic_cleanable=True,
    )


def collect_text_cleanliness_clean_issues(
    content: str,
    *,
    chapter_number: int | None = None,
    version_id: str | None = None,
) -> list[TextCleanlinessCleanIssue]:
    """Task 171t: 汇总 accept-time final sweep 的 hard-clean 问题清单."""
    meta_matches = detect_meta_tag_leaks(content)
    scene_matches = detect_markdown_scene_titles(content)
    artifact_matches = detect_text_cleanliness_artifacts(content)
    duplicate_matches = detect_duplicate_paragraphs(content)

    issues: list[TextCleanlinessCleanIssue] = []
    for match in [*meta_matches, *scene_matches, *artifact_matches]:
        issues.append(
            _clean_issue_for_meta_match(
                match, chapter_number=chapter_number, version_id=version_id
            )
        )
    for dup_match in duplicate_matches:
        issues.append(
            _clean_issue_for_duplicate(
                dup_match, chapter_number=chapter_number, version_id=version_id
            )
        )
    return issues


def _split_scenes(text: str) -> list[str]:
    """按空行（\n\n+）分割场景."""
    normalized = text.replace("\r\n", "\n")
    scenes = [block.strip() for block in re.split(r"\n\s*\n", normalized) if block.strip()]
    return scenes if scenes else [text.strip()] if text.strip() else []


def _merge_short_scenes_for_voice(
    scenes: list[str],
    max_short_len: int = 300,
    max_group_len: int = 1200,
) -> list[str]:
    """为声纹同质化检测合并相邻短场景.

    Writer 1.1.0+ 使用空行分隔场景，但段落之间也常出现空行，导致 `_split_scenes`
    把同一段对话里的每个对白/动作节拍都切成独立场景。该 helper 把连续短场景
    （<= max_short_len）合并成语义上更接近"对话块"的单元，避免 detector 因为
    格式原因漏检。合并长度超过 max_group_len 时强制切分，防止过度聚合。
    """
    if not scenes:
        return []
    merged: list[str] = []
    current = scenes[0]
    for scene in scenes[1:]:
        current_len = len(current)
        next_len = len(scene)
        if (
            current_len <= max_short_len
            and next_len <= max_short_len
            and current_len + next_len + 2 <= max_group_len
        ):
            current = current + "\n\n" + scene
        else:
            merged.append(current)
            current = scene
    merged.append(current)
    return merged


# --------------------------------------------------------------------------- #
# Task 170g: exposition 载体硬灌模式检测
# --------------------------------------------------------------------------- #
_EXPOSITION_CARRIER_PATTERNS: list[tuple[str, str, str]] = [
    (
        "info_stream",
        r"信息流[^。，]{0,15}(?:涌入|冲入|灌入|冲刷|涌进|冲进|灌进|撕裂|撕裂.{0,5}颅腔|高压电流)",
        "信息流硬灌",
    ),
    (
        "consciousness_tentacle",
        r"意识触须[^。，]{0,20}(?:延伸|探入|触及|触碰|深入|伸入|铺开|铺开去|铺开向)",
        "意识触须硬灌",
    ),
    (
        "vision_dump",
        r"(?:他|她|林渊|宋晚|苏晚)看见了[^。，]{0,10}(?:建造者|他们|完整的画面|完整画面|一幕|一切|真相|过去|未来|自己)",
        "幻象/画面直接播放",
    ),
]

_FAQ_DIALOGUE_PATTERN = re.compile(
    (
        r"[\"“”]([^\"“”]{1,20}[?？][\"“”][\s\n]{0,30}"
        r"[\"“”][^\"“”]{1,60}[\"“”][\s\n]{0,30}){2,}"
    ),
    re.MULTILINE,
)

_REVELATION_BEAT_PATTERNS: list[tuple[str, str]] = [
    ("info_stream", r"信息流[^。，]{0,15}(?:涌入|冲入|灌入|冲刷|涌进|冲进|灌进)"),
    ("vision_dump", r"看见了[^。，]{0,15}(?:建造者|他们|完整的画面|完整画面|一切|真相)"),
    (
        "faq_dialogue",
        (
            r"[。？！\"“”][\s\n]{0,30}[\"“”][^\"“”]{1,30}[？！。]"
            r"[\"“”][\s\n]{0,30}[\"“”][^\"“”]{1,60}[。？！][\"“”]"
        ),
    ),
]

# Task 170h: 结构性 exposition 检测阈值
_NON_CHARACTER_SPEAKER_KEYWORDS = [
    "建造者",
    "残影",
    "前代",
    "碎片",
    "守门人",
    "意识",
    "舰队之手",
    "建造者文明",
]

# Task 171a: 体裁解耦——不再写死本项目主角名作默认值。
# 未注入 character_names 时，vision_dump（依赖具名角色）不计分，而非误报到硬编码人名。
# 保留常量仅供单测/回归引用其历史值，不再作为生产 fallback。
_DEFAULT_CHARACTER_NAMES: set[str] = set()
_LEGACY_SCIFI_CHARACTER_NAMES = {"林渊", "宋晚", "苏晚"}  # 仅历史记录，不参与检测

# 非人实体单章台词上限（字）
_NON_CHARACTER_DIALOGUE_WORD_LIMIT = 100
# 非人实体连续独白上限（句）
_NON_CHARACTER_CONSECUTIVE_MONOLOGUE_LIMIT = 2


_EARNED_REVELATION_CUES = [
    "失败",
    "错误",
    "损坏",
    "碎裂",
    "尸体",
    "血",
    "崩溃",
    "锁死",
    "失效",
    "无法",
    "拒绝",
    "警报",
    "火花",
    "焦黑",
    "扭曲",
    "断裂",
]

# Task 170i: 对立判断 / 主角误判 / 代价线索
_OPPOSING_JUDGMENT_CUES = [
    "不",
    "错",
    "反",
    "别",
    "否",
    "怀疑",
    "质疑",
    "不对",
    "相反",
    "未必",
    "冷笑",
    "嘲讽",
    "讥讽",
]
_MISJUDGMENT_CUES = [
    "以为",
    "认为",
    "误判",
    "猜错",
    "错把",
    "误把",
    "想当然",
    "坚持",
    "不听",
]
_COST_CUES = _EARNED_REVELATION_CUES + [
    "代价",
    "伤口",
    "损失",
    "受伤",
    "疼痛",
    "撕裂",
    "破裂",
    "背叛",
    "信任",
]

# Task 170i: 情绪词与副词表（用于人类声纹同质化检测）
_EMOTION_WORDS = _POSITIVE_WORDS | _NEGATIVE_WORDS
_ADVERBS = {
    "很", "非常", "突然", "猛地", "悄悄", "冷冷地", "缓缓", "狠狠", "死死",
    "紧紧", "微微", "明显", "似乎", "大概", "根本", "完全", "绝对", "几乎",
    "终于", "猛地", "忽然", "猛然", "骤然", "渐渐", "慢慢", "迅速", "飞快",
}
# Task 171a: 代词提示语——纯代词提示的对白轮替，继承上一位具名说话人。
_DIALOGUE_PRONOUN_CUES = {
    "他说", "她说", "他问", "她问", "他道", "她道", "他答", "她答",
    "他喊", "她喊", "他低声", "她低声", "他继续", "她继续", "他反问", "她反问",
}
# Task 171a: 章级对话密度门——判定"是否对话承载章"（宽松，任意成对引号即计一处对白）。
_VOICE_QUOTE_RE = re.compile(r'[\"“”][^\"“”]{1,400}[\"“”]')
_PROTAGONIST_TELL_VERBS = [
    "明白了",
    "意识到",
    "知道了",
    "理解了",
    "懂了",
    "终于懂了",
    "这一切都意味着",
    "他理解了",
    "醒悟",
    "顿悟",
    "总结",
    "断定",
    "确信",
    "觉察",
    "发现",
]
_INFO_DELIVERY_KEYWORDS = [
    "是",
    "叫做",
    "称为",
    "机制",
    "文明",
    "协议",
    "方舟",
    "基因",
    "意识",
    "钥匙",
    "舰队",
    "转化度",
    "共鸣",
    "隐藏节点",
]

def _locate_match(text: str, matched_text: str, start: int) -> str:
    """将偏移转换为段落/句子位置描述."""
    return locate_position(text, start)


def detect_exposition_carriers(
    text: str,
    *,
    character_names: set[str] | None = None,
    non_character_keywords: set[str] | None = None,
    setting_keywords: set[str] | None = None,
    info_delivery_keywords: set[str] | None = None,
    non_character_dialogue_word_limit: int = _NON_CHARACTER_DIALOGUE_WORD_LIMIT,
    non_character_consecutive_monologue_limit: int = _NON_CHARACTER_CONSECUTIVE_MONOLOGUE_LIMIT,
    direct_revelation_quote_min_chars: int = 50,
    info_delivery_dialogue_min_chars: int = 50,
) -> list[ExpositionCarrierMatch]:
    """检测说明文载体硬灌模式（Task 170g 诊断辅助，Phase 2 扩展版）.

    当前实现为代码级启发式检测，用于量化观察和报告，不直接阻断 accept。
    命中模式包括：信息流/意识触须硬灌、幻象直接播放、FAQ 式连续问答、
    非角色实体直接揭示独白、主角总结式 tell、角色一次性大段说明、
    同一章内反复使用同一揭示节拍。

    Args:
        text: 待检测正文.
        character_names: 项目主角/人类角色名集合；未提供时使用默认集合.
        non_character_keywords: 非人实体/声源关键词集合；未提供时使用模块常量.
        setting_keywords: 项目设定关键词（保留参数，当前未参与计算）.
        info_delivery_keywords: 说明性信息投递关键词集合；未提供时使用模块常量.
        non_character_dialogue_word_limit: 非人实体单章台词字数上限.
        non_character_consecutive_monologue_limit: 非人实体连续独白句数上限.
        direct_revelation_quote_min_chars: 直接揭示独白引语最小长度.
        info_delivery_dialogue_min_chars: 信息投递式对话引语最小长度.
    """
    matches: list[ExpositionCarrierMatch] = []
    seen: set[tuple[str | int, int]] = set()

    effective_character_names = (
        character_names if character_names is not None else _DEFAULT_CHARACTER_NAMES
    )
    effective_non_char_keywords = (
        non_character_keywords
        if non_character_keywords is not None
        else set(_NON_CHARACTER_SPEAKER_KEYWORDS)
    )
    effective_direct_revelation_keywords = effective_non_char_keywords
    effective_info_delivery_keywords = (
        info_delivery_keywords
        if info_delivery_keywords is not None
        else set(_INFO_DELIVERY_KEYWORDS)
    )
    # setting_keywords 保留给未来项目级设定注入，当前未参与量具计算

    # Dynamic vision_dump pattern: effective character names + pronouns
    char_alternatives = "|".join(map(re.escape, sorted(effective_character_names | {"他", "她"})))
    vision_dump_re = re.compile(
        f"(?:{char_alternatives})看见了[^。，]{{0,10}}"
        f"(?:建造者|他们|完整的画面|完整画面|一幕|一切|真相|过去|未来|自己)"
    )

    # Compile local regexes using effective keywords and thresholds
    quoted_segment_re = re.compile(r'["“”]([^"“”]{20,800})["“”]')  # noqa: F841
    # Task 171a-1: 方向性引号——开引号 ["“]、闭引号 ["”]，内部禁含任何引号。
    # 防止"上一句闭引号 ” + 叙事 + 下一句开引号"被当成一段引语（跨对话轮 artifact，
    # 该 artifact 内容常无换行，故 "\n\n" 过滤无法拦截）。ASCII " 两端通用仍可匹配。
    direct_revelation_quote_re = re.compile(
        rf'["“]([^"“”]{{{direct_revelation_quote_min_chars},800}})["”]'
    )
    info_delivery_dialogue_re = re.compile(
        rf'["“]([^"“”]{{{info_delivery_dialogue_min_chars},800}})["”]'
    )
    non_character_quote_re = re.compile(r'["“”]([^"“”]{1,800})["“”]')
    protagonist_summary_tell_re = re.compile(
        r"[。！？\n]\s*(?:他|她)?[^。，]{0,10}?(?:"
        + "|".join(map(re.escape, _PROTAGONIST_TELL_VERBS))
        + r")[^。，]{0,15}?(?:，|：|——)([^。！？]{15,400})[。！？]"
    )

    # 1. 正则模式匹配（原始 170g 形式层模式；vision_dump 使用动态角色名）
    for carrier_type, pattern, message in _EXPOSITION_CARRIER_PATTERNS:
        pattern_re = vision_dump_re if carrier_type == "vision_dump" else re.compile(pattern)
        for m in pattern_re.finditer(text):
            key = (m.start(), m.end())
            if key in seen:
                continue
            seen.add(key)
            matches.append(
                ExpositionCarrierMatch(
                    carrier_type=carrier_type,  # type: ignore[arg-type]
                    matched_text=m.group(),
                    location=_locate_match(text, m.group(), m.start()),
                    severity="minor",
                    message=message,
                    start=m.start(),
                    end=m.end(),
                )
            )

    # 2. FAQ 式连续问答（简化：连续 2 轮以上短问答）
    for m in _FAQ_DIALOGUE_PATTERN.finditer(text):
        key = (m.start(), m.end())
        if key in seen:
            continue
        seen.add(key)
        matches.append(
            ExpositionCarrierMatch(
                carrier_type="faq_dialogue",
                matched_text=m.group()[:120],
                location=_locate_match(text, m.group(), m.start()),
                severity="info",
                message="FAQ 式连续问答（可能为低摩擦 exposition）",
                start=m.start(),
                end=m.end(),
            )
        )

    # 3. 非角色实体直接揭示独白
    for m in direct_revelation_quote_re.finditer(text):
        key = (m.start(), m.end())
        if key in seen:
            continue
        content = m.group(1)
        # 过滤跨段落（closing quote 与下一段 opening quote 夹住叙事）的伪引语
        if "\n\n" in content:
            continue
        if any(kw in content for kw in effective_direct_revelation_keywords):
            seen.add(key)
            matches.append(
                ExpositionCarrierMatch(
                    carrier_type="direct_revelation_monologue",
                    matched_text=m.group()[:120],
                    location=_locate_match(text, m.group(), m.start()),
                    severity="minor",
                    message="非角色实体直接揭示世界观/设定（独白硬灌）",
                    start=m.start(),
                    end=m.end(),
                )
            )

    # 4. 主角总结式 tell
    for m in protagonist_summary_tell_re.finditer(text):
        key = (m.start(), m.end())
        if key in seen:
            continue
        seen.add(key)
        matches.append(
            ExpositionCarrierMatch(
                carrier_type="protagonist_summary_tell",
                matched_text=m.group()[:120],
                location=_locate_match(text, m.group(), m.start()),
                severity="minor",
                message="主角总结式 tell 直接投递世界观/真相",
                start=m.start(),
                end=m.end(),
            )
        )

    # 5. 信息投递式对话（长引语含说明性关键词）
    for m in info_delivery_dialogue_re.finditer(text):
        key = (m.start(), m.end())
        if key in seen:
            continue
        content = m.group(1)
        if "\n\n" in content:
            continue
        if any(kw in content for kw in effective_info_delivery_keywords):
            seen.add(key)
            matches.append(
                ExpositionCarrierMatch(
                    carrier_type="info_delivery_dialogue",
                    matched_text=m.group()[:120],
                    location=_locate_match(text, m.group(), m.start()),
                    severity="info",
                    message="角色一次性大段说明设定/世界观（低摩擦 exposition）",
                    start=m.start(),
                    end=m.end(),
                )
            )

    # 6. 重复揭示节拍
    beat_counts: dict[str, int] = {
        "info_stream": len(re.findall(_REVELATION_BEAT_PATTERNS[0][1], text)),
        "vision_dump": len(re.findall(_REVELATION_BEAT_PATTERNS[1][1], text)),
        "faq_dialogue": len(re.findall(_REVELATION_BEAT_PATTERNS[2][1], text)),
        "direct_revelation_monologue": len(
            [
                m
                for m in direct_revelation_quote_re.finditer(text)
                if "\n\n" not in m.group(1)
                and any(kw in m.group(1) for kw in effective_direct_revelation_keywords)
            ]
        ),
        "protagonist_summary_tell": len(protagonist_summary_tell_re.findall(text)),
        "info_delivery_dialogue": len(
            [
                m
                for m in info_delivery_dialogue_re.finditer(text)
                if "\n\n" not in m.group(1)
                and any(kw in m.group(1) for kw in effective_info_delivery_keywords)
            ]
        ),
    }

    for carrier_type, count in beat_counts.items():
        if count >= 2:
            matches.append(
                ExpositionCarrierMatch(
                    carrier_type="repeated_revelation_beat",
                    matched_text=f"{carrier_type} 出现 {count} 次",
                    location="全章",
                    severity="minor",
                    message=f"同一章内 '{carrier_type}' 揭示节拍重复 {count} 次，可能产生审美疲劳",
                )
            )

    # 7. Task 170h: 非人实体台词总量/连续独白超标检测
    non_char_total_words = 0
    non_char_consecutive = 0
    last_was_non_character = False
    for m in non_character_quote_re.finditer(text):
        quote = m.group(1)
        is_non_character = any(kw in quote for kw in effective_non_char_keywords)
        if is_non_character:
            non_char_total_words += len(quote)
            non_char_consecutive += 1
            last_was_non_character = True
        else:
            if last_was_non_character:
                if non_char_consecutive > non_character_consecutive_monologue_limit:
                    event_key = ("non_char_consecutive", m.start())
                    if event_key not in seen:
                        seen.add(event_key)
                        matches.append(
                            ExpositionCarrierMatch(
                                carrier_type="non_character_monologue_overflow",
                                matched_text=f"非人实体连续独白 {non_char_consecutive} 句",
                                location=_locate_match(text, quote, m.start()),
                                severity="minor",
                                message="非人实体连续独白超过 2 句，可能承担世界观讲解员角色",
                            )
                        )
            non_char_consecutive = 0
            last_was_non_character = False

    # 句尾再检查一次连续独白
    if last_was_non_character and non_char_consecutive > non_character_consecutive_monologue_limit:
        event_key = ("non_char_consecutive", len(text))
        if event_key not in seen:
            seen.add(event_key)
            matches.append(
                ExpositionCarrierMatch(
                    carrier_type="non_character_monologue_overflow",
                    matched_text=f"非人实体连续独白 {non_char_consecutive} 句",
                    location="章末",
                    severity="minor",
                    message="非人实体连续独白超过 2 句，可能承担世界观讲解员角色",
                )
            )

    if non_char_total_words > non_character_dialogue_word_limit:
        event_key = ("non_char_total_words", 0)
        if event_key not in seen:
            seen.add(event_key)
            matches.append(
                ExpositionCarrierMatch(
                    carrier_type="non_character_monologue_overflow",
                    matched_text=f"非人实体台词总量 {non_char_total_words} 字",
                    location="全章",
                    severity="major",
                    message=(
                        f"非人实体单章台词超过 {non_character_dialogue_word_limit} 字，"
                        "戏份分配失衡"
                    ),
                )
            )

    # 8. Task 170h: 连续说明性对话链检测
    consecutive_expository = 0
    last_end = 0
    chain_start = 0
    for m in info_delivery_dialogue_re.finditer(text):
        quote = m.group(1)
        if "\n\n" in quote:
            continue
        has_info_keyword = any(kw in quote for kw in effective_info_delivery_keywords)
        has_conflict_interruption = any(
            kw in quote for kw in ["？", "？", "！", "别动", "住手", "该死", "滚开", "闭嘴"]
        )
        if has_info_keyword and not has_conflict_interruption:
            if consecutive_expository == 0:
                chain_start = m.start()
            consecutive_expository += 1
            last_end = m.end()
        else:
            if consecutive_expository >= 3:
                event_key = ("expository_chain", chain_start)
                if event_key not in seen:
                    seen.add(event_key)
                    matches.append(
                        ExpositionCarrierMatch(
                            carrier_type="expository_dialogue_chain",
                            matched_text=text[chain_start:last_end][:120],
                            location=_locate_match(text, text[chain_start:last_end], chain_start),
                            severity="minor",
                            message="连续 3 句以上说明性对话传递设定，缺乏冲突/动作打断",
                        )
                    )
            consecutive_expository = 0

    if consecutive_expository >= 3:
        event_key = ("expository_chain", chain_start)
        if event_key not in seen:
            seen.add(event_key)
            matches.append(
                ExpositionCarrierMatch(
                    carrier_type="expository_dialogue_chain",
                    matched_text=text[chain_start:last_end][:120],
                    location=_locate_match(text, text[chain_start:last_end], chain_start),
                    severity="minor",
                    message="连续 3 句以上说明性对话传递设定，缺乏冲突/动作打断",
                )
            )

    # 9. Task 170h: 无动作/失败/代价支撑的揭示
    for m in direct_revelation_quote_re.finditer(text):
        quote = m.group(1)
        if "\n\n" in quote:
            continue
        has_non_char = any(kw in quote for kw in effective_non_char_keywords)
        if not has_non_char:
            continue
        window_start = max(0, m.start() - 200)
        preceding = text[window_start:m.start()]
        if not any(cue in preceding for cue in _EARNED_REVELATION_CUES):
            matches.append(
                ExpositionCarrierMatch(
                    carrier_type="unearned_revelation",
                    matched_text=m.group()[:120],
                    location=_locate_match(text, m.group(), m.start()),
                    severity="info",
                    message=(
                        "非人实体揭示前 200 字内未出现失败/损坏/代价/锁死等动作线索，"
                        "揭示可能缺乏支撑"
                    ),
                    start=m.start(),
                    end=m.end(),
                )
            )

    # 10. Task 170i: 无认知冲突支撑的揭示
    for m in info_delivery_dialogue_re.finditer(text):
        quote = m.group(1)
        if "\n\n" in quote:
            continue
        if not any(kw in quote for kw in effective_info_delivery_keywords):
            continue
        event_key = ("unconflicted", m.start())
        if event_key in seen:
            continue
        window_start = max(0, m.start() - 300)
        preceding = text[window_start:m.start()]
        has_conflict = any(cue in preceding for cue in _OPPOSING_JUDGMENT_CUES)
        has_misjudgment = any(cue in preceding for cue in _MISJUDGMENT_CUES)
        has_cost = any(cue in preceding for cue in _COST_CUES)
        if not (has_conflict or has_misjudgment or has_cost):
            seen.add(event_key)
            matches.append(
                ExpositionCarrierMatch(
                    carrier_type="unconflicted_revelation",
                    matched_text=m.group()[:120],
                    location=_locate_match(text, m.group(), m.start()),
                    severity="info",
                    message=(
                        "高概念信息前 300 字内未出现对立判断、主角误判或代价事件，"
                        "揭示可能缺乏认知冲突支撑"
                    ),
                    start=m.start(),
                    end=m.end(),
                )
            )

    matches.sort(key=lambda x: text.find(x.matched_text) if x.matched_text in text else 0)
    return matches

def _nearest_registry_name(
    before: str,
    after: str,
    registry: set[str],
) -> str | None:
    """Task 171a: 动作节拍归因——在引语紧邻窗口内就近匹配注册表角色名.

    覆盖"名字+动作节拍+引语"（``林渊皱眉。"..."``）与"引语+名字动作"
    （``"..."林渊转身``）等无 speech-verb 句式。**优先 before 窗口**（引语前的动作
    主体通常是说话人），仅当 before 无注册表名时才回退 after，避免把"下一位说话人"
    （紧跟在引语后开始其动作节拍的角色）误当当前说话人。仅在有注册表时调用。
    """
    best: str | None = None
    best_dist: int | None = None
    # 1) 优先 before：取最靠近引语（末次出现）的注册表名。
    for known in registry:
        b_idx = before.rfind(known)
        if b_idx != -1:
            dist = len(before) - (b_idx + len(known))
            if best_dist is None or dist < best_dist:
                best, best_dist = known, dist
    if best is not None:
        return best
    # 2) before 无名时回退 after：取最先出现（首次）的注册表名。
    for known in registry:
        a_idx = after.find(known)
        if a_idx != -1 and (best_dist is None or a_idx < best_dist):
            best, best_dist = known, a_idx
    return best


def detect_human_voice_homogeneity(
    text: str,
    non_character_keywords: set[str] | None = None,
    character_names: set[str] | None = None,
    min_chapter_quotes: int = 2,
) -> list[ExpositionCarrierMatch]:
    """Task 170i: 检测同场景多人类角色对白声纹同质化.

    启发式规则：同一场景（或合并后的短场景对话块）中两个以上人类角色有对白，且
    - 平均句长差异 <20%
    - 情绪词重叠 >50%
    - 副词密度差异 <30%
    则认为声纹同质化，返回 report-only 命中。

    说话人归因（Task 170o 校准）：
    - 前置说话人：``林渊说："..."``；
    - 后置说话人：``"..."林渊说。``；
    - 叙事归因：``X的声音/嗓音/录音``、``声音是X的``（真实正文大量使用，非 ``X说`` 标签）。
    当提供 ``character_names``（项目角色注册表）时，仅接受注册表内的人名作为说话人，
    过滤 ``寻找更多`` / ``录音中`` 等把叙事片段误当人名的噪声；未提供时回退到
    "长度 2-4 汉字 + 非代词 + 非非人实体" 的宽松启发式，保持向后兼容。
    """
    matches: list[ExpositionCarrierMatch] = []
    raw_scenes = _split_scenes(text)
    scenes = _merge_short_scenes_for_voice(raw_scenes)

    # Task 171a 构念重定义：voice 仅在"对话承载章"计分。
    # 全章对白引语过稀（单人解谜/意识流/纯叙事）时视为"voice 不适用"，直接返回空——
    # 不把"没有对白可比"误判为"声纹同质"。真正的多角色声纹区分度由下游
    # "≥2 具名说话人 + 各 ≥2 句" 判定。
    if len(_VOICE_QUOTE_RE.findall(text)) < min_chapter_quotes:
        return matches

    # 基础说话人识别：支持前置、后置与叙事归因，覆盖常见 speech-verb 变体。
    # 注意：捕获组为说话人名字（1-6 个汉字），可能误捕"他/她"等代词或叙事片段；
    # 后续用代词过滤 + 非人关键词过滤 + 角色注册表 gating + 多角色成对比较收敛噪声。
    speech_verb = (
        r"(?:说|道|喊道|问道|冷笑道|回答道|低声道|吼道|骂道|"
        r"开口|打断|补充|继续|反问|沉声|厉声|轻声|喃喃|嘀咕)"
    )
    pre_speaker_re = re.compile(
        rf'([一-龥]{{1,6}}){speech_verb}(?:道|着|了|：|\s*)$'
    )
    post_speaker_re = re.compile(
        rf'^[\s，。！？、…]*([一-龥]{{1,6}}){speech_verb}(?:道|着|了|，|。|：|\s*)'
    )
    # 叙事归因：真实正文多用"X的声音/录音"而非"X说"，用注册表 gating 收敛噪声。
    voice_of_re = re.compile(r'([一-龥]{2,4})的(?:声音|嗓音|录音|语音|话音|声线)')
    is_voice_of_re = re.compile(r'(?:声音|嗓音|话音|语音)是([一-龥]{2,4})的')
    quote_re = re.compile(r'[\"“”]([^\"“”]{10,400})[\"“”]')

    pronouns = {"他", "她", "它", "我", "你", "他们", "她们", "它们", "我们", "你们"}

    effective_non_char_keywords = (
        non_character_keywords
        if non_character_keywords is not None
        else set(_NON_CHARACTER_SPEAKER_KEYWORDS)
    )
    # 角色注册表 gating：提供时只认注册表内人名，杜绝叙事片段误当说话人。
    registry = {n for n in (character_names or set()) if n}

    def _accept_speaker(name: str | None) -> str | None:
        if not name or name in pronouns or name in effective_non_char_keywords:
            return None
        if registry:
            # 注册表模式：名字必须命中注册表（支持子串，兼容"老陈/陈薇"式指代）。
            for known in registry:
                if known in name or name in known:
                    return known
            return None
        # 无注册表：回退宽松启发式，仅接受 2-4 汉字候选，滤掉过长叙事片段。
        return name if 2 <= len(name) <= 4 else None

    for scene_idx, scene in enumerate(scenes, 1):
        speaker_stats: dict[str, dict[str, Any]] = {}
        last_named_speaker: str | None = None  # 用于代词就近继承（对话轮替常见）
        for m in quote_re.finditer(scene):
            quote = m.group(1)
            raw_speaker: str | None = None
            # Task 171a: 加宽归因窗口 30/40 -> 60/60，覆盖"名字+动作节拍+引语"的较长句式。
            before = scene[max(0, m.start() - 60):m.start()]
            after = scene[m.end():min(len(scene), m.end() + 60)]
            # 1) 前置说话人
            pre_match = pre_speaker_re.search(before)
            if pre_match:
                raw_speaker = pre_match.group(1)
            # 2) 后置说话人
            if raw_speaker is None:
                post_match = post_speaker_re.search(after)
                if post_match:
                    raw_speaker = post_match.group(1)
            # 3) 叙事归因（X的声音 / 声音是X的）：优先看引语前窗口（归因通常前置），
            #    取窗口内最靠近引语的一次匹配，避免误取下一句的说话人。
            if raw_speaker is None:
                for rgx in (is_voice_of_re, voice_of_re):
                    before_hits = list(rgx.finditer(before))
                    if before_hits:
                        raw_speaker = before_hits[-1].group(1)
                        break
                    after_hit = rgx.search(after)
                    if after_hit:
                        raw_speaker = after_hit.group(1)
                        break
            speaker = _accept_speaker(raw_speaker)
            # 4) Task 171a 动作节拍归因（``林渊皱眉。"..."`` / ``"..."林渊转身``）：
            #    speech-verb 归因失败时，若引语紧邻窗口出现注册表内角色名（无 speech verb，
            #    多为动作节拍夹引语），就近绑定。仅在提供 character_names 注册表时启用，
            #    避免无注册表时把任意人名误当说话人。
            if speaker is None and registry:
                speaker = _nearest_registry_name(before, after, registry)
            # 5) 代词就近继承：纯代词提示（"他说"/"她问）或无提示轮替，继承上一位具名说话人。
            if speaker is None and last_named_speaker is not None:
                tail = before[-6:]
                head = after[:6]
                if any(p in tail or p in head for p in _DIALOGUE_PRONOUN_CUES):
                    speaker = last_named_speaker
            if speaker is None:
                continue
            last_named_speaker = speaker
            if speaker not in speaker_stats:
                speaker_stats[speaker] = {
                    "quotes": [],
                    "lengths": [],
                    "emotion_words": set(),
                    "adverb_count": 0,
                    "word_count": 0,
                }
            # 按句拆分
            sentences = re.split(r'[。！？…]', quote)
            for s in sentences:
                s = s.strip()
                if not s:
                    continue
                speaker_stats[speaker]["lengths"].append(len(s))
            speaker_stats[speaker]["quotes"].append(quote)
            speaker_stats[speaker]["word_count"] += len(quote)
            for w in _EMOTION_WORDS:
                if w in quote:
                    speaker_stats[speaker]["emotion_words"].add(w)
            for adv in _ADVERBS:
                speaker_stats[speaker]["adverb_count"] += quote.count(adv)

        # 只保留有 >=2 句对白的角色
        qualified = {
            name: stats
            for name, stats in speaker_stats.items()
            if len(stats["lengths"]) >= 2
        }
        if len(qualified) < 2:
            continue

        names = list(qualified.keys())
        for i in range(len(names)):
            for j in range(i + 1, len(names)):
                a, b = qualified[names[i]], qualified[names[j]]
                avg_a = sum(a["lengths"]) / len(a["lengths"])
                avg_b = sum(b["lengths"]) / len(b["lengths"])
                if avg_a == 0 or avg_b == 0:
                    continue
                length_diff = abs(avg_a - avg_b) / max(avg_a, avg_b)
                emotion_union = a["emotion_words"] | b["emotion_words"]
                if not emotion_union:
                    # 双方都没有情绪词：在"无情绪标记"这一维度上视为趋同，
                    # 避免漏检干净但模板化的对白。
                    emotion_overlap = 1.0
                else:
                    emotion_overlap = len(
                        a["emotion_words"] & b["emotion_words"]
                    ) / len(emotion_union)
                adv_density_a = a["adverb_count"] / max(a["word_count"], 1)
                adv_density_b = b["adverb_count"] / max(b["word_count"], 1)
                if adv_density_a == 0 and adv_density_b == 0:
                    adv_diff = 0.0
                else:
                    adv_diff = abs(adv_density_a - adv_density_b) / max(
                        adv_density_a, adv_density_b, 1e-6
                    )

                if (
                    length_diff < 0.20
                    and emotion_overlap > 0.50
                    and adv_diff < 0.30
                ):
                    matches.append(
                        ExpositionCarrierMatch(
                            carrier_type="human_voice_homogeneity",
                            matched_text=f"场景{scene_idx}: {names[i]} 与 {names[j]} 对白趋同",
                            location=f"场景{scene_idx}",
                            severity="info",
                            message=(
                                f"人类角色声纹同质化：{names[i]} 与 {names[j]} "
                                f"句长差异 {length_diff:.0%}、情绪重叠 {emotion_overlap:.0%}、"
                                f"副词密度差异 {adv_diff:.0%}"
                            ),
                        )
                    )
    return matches


def _short_paragraph_ratio(text: str, threshold: int = 50) -> float:
    """计算短段落（< threshold 字）占比."""
    paragraphs = split_paragraphs(text)
    if not paragraphs:
        return 0.0
    short_count = sum(1 for p in paragraphs if len(p) < threshold)
    return round(short_count / len(paragraphs), 3)


def _check_punch_points(
    content: str,
    punch_points: list[PunchPoint],
    word_count: int,
) -> PunchCheck:
    """检查刺激点执行情况和情绪转折密度."""
    # 按空行分割场景（与 Writer Prompt 1.1.0+ 一致）
    scenes = _split_scenes(content)
    if not scenes:
        scenes = [content] if content else []

    # 刺激点密度
    expected = len(punch_points)
    # 简化检查：只要 planned 了至少 1 个且 target_scene 在有效范围内就算通过
    # （严格的内容级检查留给 LLMAuditor 做语义判断）
    valid_targets = 0
    for p in punch_points:
        if 1 <= p.target_scene <= len(scenes):
            valid_targets += 1

    punch_density_ok = expected == 0 or valid_targets >= 1

    # 情绪转折检测
    scene_emotions = [_analyze_scene_emotion(s) for s in scenes]
    switch_count = 0
    for i in range(1, len(scene_emotions)):
        if scene_emotions[i] != scene_emotions[i - 1]:
            switch_count += 1

    # 每 1500 字至少 1 次情绪转折
    required_switches = max(1, word_count // 1500)
    emotion_switch_ok = switch_count >= required_switches or expected == 0

    issues: list[str] = []
    if expected > 0 and valid_targets < expected:
        issues.append(f"刺激点场景匹配不足：规划 {expected} 个，有效匹配 {valid_targets} 个")
    if expected > 0 and not emotion_switch_ok:
        issues.append(
            f"情绪转折不足：检测到 {switch_count} 次，要求至少 {required_switches} 次"
        )

    return PunchCheck(
        punch_count=valid_targets,
        expected_punch_count=expected,
        punch_density_ok=punch_density_ok,
        emotion_switch_count=switch_count,
        emotion_switch_ok=emotion_switch_ok,
        dominant_senses=[p.dominant_sense for p in punch_points if p.dominant_sense],
        issues=issues,
    )


def _check_mandatory_references(
    content: str,
    mandatory_references: list[dict[str, Any]] | None,
) -> tuple[bool, list[dict[str, Any]]]:
    """Task 138h: 检测正文中是否缺失 mandatory_reference 的提及.

    匹配策略：检查 setting_key 的最后一个 segment 或 setting_name
    是否在正文中出现（不区分中英文标点）。

    Returns:
        (passed, issues)
    """
    if not mandatory_references:
        return True, []

    issues: list[dict[str, Any]] = []
    text = content.lower()
    for ref in mandatory_references:
        key = str(ref.get("setting_key") or "").lower()
        name = str(ref.get("setting_name") or "").lower()
        # 取 key 的最后一个 segment 作为别名（如 surface_material）
        key_alias = key.split(".")[-1] if key else ""

        # Bug（V8 172b.p）：xuanhuan 惯用引号包裹的口语化设定名（祭坛上的'那个东西'），
        # 全名含引号在正文不逐字出现、key_alias 又是英文（entity），旧三元候选全落空，
        # 与 settlement 的引用检测口径不一致 → 反复要求回收、误判 orphan。此处按同一套
        # 分隔符（含中英文引号）拆出 name-part 候选（len>=2），使两条路径口径一致。
        candidates = [name, key_alias, key]
        if name:
            for part in re.split(
                r"[·—\-_/（）()\[\]【】,，、;；:\s'\u2018\u2019\u201c\u201d\"“”]+", name
            ):
                cleaned = part.strip()
                if len(cleaned) >= 2:
                    candidates.append(cleaned)

        found = False
        for candidate in candidates:
            if candidate and candidate in text:
                found = True
                break

        if not found:
            silent = ref.get("silent_chapters", 0)
            setting_name = ref.get("setting_name") or key or "未命名设定"
            issues.append(
                {
                    "setting_key": key or setting_name,
                    "setting_name": setting_name,
                    "silent_chapters": silent,
                    "message": f"强制连续性约束未回收：{setting_name}（已沉寂 {silent} 章）",
                }
            )

    return len(issues) == 0, issues


def run_rule_audit(
    content: str,
    genre_rules: GenreRules | None = None,
    word_count_target: int = 3000,
    chapter_type: str | None = None,
    scene_count_target: int = 2,
    numerical_contexts: list[NumericalContext] | None = None,
    punch_points: list[PunchPoint] | None = None,
    mandatory_references: list[dict[str, Any]] | None = None,
    *,
    character_names: set[str] | None = None,
    non_character_keywords: set[str] | None = None,
    setting_keywords: set[str] | None = None,
    info_delivery_keywords: set[str] | None = None,
    non_character_dialogue_word_limit: int = _NON_CHARACTER_DIALOGUE_WORD_LIMIT,
    non_character_consecutive_monologue_limit: int = _NON_CHARACTER_CONSECUTIVE_MONOLOGUE_LIMIT,
    direct_revelation_quote_min_chars: int = 50,
    info_delivery_dialogue_min_chars: int = 50,
) -> RuleAuditResult:
    """运行规则检测（纯代码，无 LLM）.

    Args:
        content: 章节正文
        genre_rules: 题材规则（含 fatigue_words）
        word_count_target: 目标字数
        numerical_contexts: 数值上下文（玄幻题材用）
        punch_points: CreativeBrief 规划的刺激点（Punch Engine 用）

    Returns:
        RuleAuditResult
    """
    start_time = time.perf_counter()

    # 1. AI 腔检测
    ai_tell_matches = detect_ai_tells(content)
    ai_tell_count = len(ai_tell_matches)

    # 2. 疲劳词检测
    fatigue_words = genre_rules.fatigue_words if genre_rules else []
    fatigue_word_matches = detect_fatigue_words(content, fatigue_words)
    fatigue_word_count = sum(m.count for m in fatigue_word_matches)

    # 3. 钩子检测
    has_opening_hook = check_opening_hook(content)
    has_ending_hook = check_ending_hook(content)

    # 4. 段落节奏
    rhythm = analyze_paragraph_rhythm(content)
    paragraph_rhythm_score = rhythm.score
    rhythm_issues = rhythm.issues

    # 5. 字数统计
    word_count = _count_chinese_words(content)
    lower_bound, upper_bound = word_count_bounds(word_count_target, chapter_type)
    word_count_ok = lower_bound <= word_count <= upper_bound
    word_count_ratio = round(word_count / word_count_target, 2) if word_count_target > 0 else 0.0

    # 6. 场景数量检测（按空行分割，与 Prompt 1.1.0+ 一致）
    scene_count = len(_split_scenes(content))
    scene_count_ok = scene_count >= scene_count_target

    # 7. 数值公式验证（占位）
    numerical_issues: list[str] = []

    # 8. 通用角色名检测
    generic_name_matches = detect_generic_names(content)
    generic_name_count = len(generic_name_matches)

    # 9. 元标记泄漏检测
    meta_tag_matches = detect_meta_tag_leaks(content)
    meta_tag_count = len(meta_tag_matches)

    # 10. Markdown 场景标题检测
    markdown_scene_title_matches = detect_markdown_scene_titles(content)
    markdown_scene_title_count = len(markdown_scene_title_matches)

    # 11. Task 171t: 文本洁净 artifact 检测（T9 hard issue）
    text_artifact_matches = detect_text_cleanliness_artifacts(content)
    text_artifact_count = len(text_artifact_matches)

    # 12. Task 171v: 母题疲劳扫描（观测指标，不直接阻断）
    motif_fatigue_matches = detect_fatigue_motifs(content)
    motif_fatigue_count = len(motif_fatigue_matches)

    # 13. 重复长段落检测（观测指标，不直接阻断）
    duplicate_paragraph_matches = detect_duplicate_paragraphs(content)
    duplicate_paragraph_count = len(duplicate_paragraph_matches)

    # 14. 短段落比例（观测指标，不直接阻断）
    short_paragraph_ratio = _short_paragraph_ratio(content, threshold=50)

    # 15. Task 170g/170i: 说明文载体硬灌检测 + 人类声纹同质化检测（观测指标，不直接阻断）
    exposition_carrier_matches = detect_exposition_carriers(
        content,
        character_names=character_names,
        non_character_keywords=non_character_keywords,
        setting_keywords=setting_keywords,
        info_delivery_keywords=info_delivery_keywords,
        non_character_dialogue_word_limit=non_character_dialogue_word_limit,
        non_character_consecutive_monologue_limit=non_character_consecutive_monologue_limit,
        direct_revelation_quote_min_chars=direct_revelation_quote_min_chars,
        info_delivery_dialogue_min_chars=info_delivery_dialogue_min_chars,
    )
    exposition_carrier_matches.extend(
        detect_human_voice_homogeneity(
            content,
            non_character_keywords=non_character_keywords,
            character_names=character_names,
        )
    )
    exposition_carrier_count = len(exposition_carrier_matches)

    # 16. 刺激度检查（Punch Engine）
    punch_check = _check_punch_points(content, punch_points or [], word_count)

    # 17. Task 138h: 强制连续性约束检查
    mr_passed, mr_issues = _check_mandatory_references(content, mandatory_references)

    duration_ms = int((time.perf_counter() - start_time) * 1000)

    result = RuleAuditResult(
        auditor_id="rule_auditor",
        ai_tell_matches=ai_tell_matches,
        ai_tell_count=ai_tell_count,
        fatigue_word_matches=fatigue_word_matches,
        fatigue_word_count=fatigue_word_count,
        has_opening_hook=has_opening_hook,
        has_ending_hook=has_ending_hook,
        paragraph_rhythm_score=paragraph_rhythm_score,
        rhythm_issues=rhythm_issues,
        word_count=word_count,
        word_count_target=word_count_target,
        word_count_ratio=word_count_ratio,
        word_count_ok=word_count_ok,
        scene_count=scene_count,
        scene_count_target=scene_count_target,
        scene_count_ok=scene_count_ok,
        generic_name_matches=generic_name_matches,
        generic_name_count=generic_name_count,
        meta_tag_matches=meta_tag_matches,
        meta_tag_count=meta_tag_count,
        markdown_scene_title_matches=markdown_scene_title_matches,
        markdown_scene_title_count=markdown_scene_title_count,
        text_artifact_matches=text_artifact_matches,
        text_artifact_count=text_artifact_count,
        motif_fatigue_matches=motif_fatigue_matches,
        motif_fatigue_count=motif_fatigue_count,
        duplicate_paragraph_matches=duplicate_paragraph_matches,
        duplicate_paragraph_count=duplicate_paragraph_count,
        short_paragraph_ratio=short_paragraph_ratio,
        exposition_carrier_matches=exposition_carrier_matches,
        exposition_carrier_count=exposition_carrier_count,
        numerical_issues=numerical_issues,
        punch_check=punch_check,
        mandatory_reference_issues=mr_issues,
        mandatory_reference_check_passed=mr_passed,
        duration_ms=duration_ms,
    )

    logger.info(
        "rule_auditor.done",
        ai_tell_count=ai_tell_count,
        fatigue_word_count=fatigue_word_count,
        has_opening_hook=has_opening_hook,
        has_ending_hook=has_ending_hook,
        rhythm_score=paragraph_rhythm_score,
        word_count=word_count,
        word_count_ok=word_count_ok,
        punch_density_ok=punch_check.punch_density_ok,
        emotion_switch_ok=punch_check.emotion_switch_ok,
        mandatory_reference_check_passed=mr_passed,
        mandatory_reference_issue_count=len(mr_issues),
        exposition_carrier_count=exposition_carrier_count,
        text_artifact_count=text_artifact_count,
        motif_fatigue_count=motif_fatigue_count,
        duration_ms=duration_ms,
    )
    return result


async def save_rule_audit(
    db: ReviewReportRepository,
    version_id: str,
    result: RuleAuditResult,
    report_id: str | None = None,
) -> None:
    """保存 RuleAuditResult 到 review_reports 表.

    Args:
        db: ReviewReportRepository
        version_id: 章节版本 ID
        result: RuleAuditResult
        report_id: 可选的报告 ID，自动生成
    """
    if report_id is None:
        report_id = f"ra-{version_id}-{uuid.uuid4().hex[:8]}"

    report = MergedReviewReport(
        chapter_version_id=version_id,
        rule_audit=result,
        ai_tell_count=result.ai_tell_count,
        fatigue_word_count=result.fatigue_word_count,
        has_opening_hook=result.has_opening_hook,
        has_ending_hook=result.has_ending_hook,
        scene_count=result.scene_count,
        scene_count_ok=result.scene_count_ok,
        overall_score=_compute_overall_score(result),
        summary=_generate_summary(result),
    )

    await db.create(report, report_id, audit_type="rule")
    logger.info(
        "rule_auditor.saved",
        report_id=report_id,
        version_id=version_id,
    )


def _compute_overall_score(result: RuleAuditResult) -> float:
    """计算综合评分（0-10）."""
    score = 10.0

    # AI 腔扣分：每个 -0.5，最多 -3
    score -= min(result.ai_tell_count * 0.5, 3.0)

    # 疲劳词扣分：每个 -0.3，最多 -2
    score -= min(result.fatigue_word_count * 0.3, 2.0)

    # 无首屏钩子 -1
    if not result.has_opening_hook:
        score -= 1.0

    # 无章末钩子 -1.5
    if not result.has_ending_hook:
        score -= 1.5

    # 段落节奏扣分：低于 5 分每差 1 分扣 0.3
    if result.paragraph_rhythm_score < 5.0:
        score -= (5.0 - result.paragraph_rhythm_score) * 0.3

    # 字数偏差扣分
    if not result.word_count_ok and result.word_count_target > 0:
        deviation = abs(result.word_count - result.word_count_target) / result.word_count_target
        score -= min(deviation * 5, 2.0)

    # 场景数不足扣分（硬约束）
    if not result.scene_count_ok:
        score -= 3.0

    # 通用角色名扣分：每个 -0.3，最多 -1.5
    score -= min(result.generic_name_count * 0.3, 1.5)

    # 元标记泄漏扣分：每个 -0.5，最多 -2
    score -= min(result.meta_tag_count * 0.5, 2.0)

    # Task 171t: 文本 artifact 泄漏扣分：每个 -0.5，最多 -2
    score -= min(result.text_artifact_count * 0.5, 2.0)

    # Task 170g: 说明文载体硬灌扣分（观测指标，轻量扣分，最多 -1.5）
    score -= min(result.exposition_carrier_count * 0.3, 1.5)

    # Punch Engine 扣分
    if result.punch_check.expected_punch_count > 0:
        if not result.punch_check.punch_density_ok:
            score -= 1.0
        if not result.punch_check.emotion_switch_ok:
            score -= 0.5

    # Task 138h: 强制连续性约束扣分 — 每个缺失 -1.5，最多 -3
    if not result.mandatory_reference_check_passed:
        score -= min(len(result.mandatory_reference_issues) * 1.5, 3.0)

    return max(0.0, round(score, 1))


def _generate_summary(result: RuleAuditResult) -> str:
    """生成检测摘要."""
    parts: list[str] = []
    if result.ai_tell_count > 0:
        parts.append(f"发现 {result.ai_tell_count} 处 AI 腔")
    if result.fatigue_word_count > 0:
        parts.append(f"发现 {result.fatigue_word_count} 个疲劳词")
    if not result.has_opening_hook:
        parts.append("缺少首屏钩子")
    if not result.has_ending_hook:
        parts.append("缺少章末钩子")
    if result.paragraph_rhythm_score < 5.0:
        parts.append(f"段落节奏欠佳（{result.paragraph_rhythm_score:.1f}/10）")
    if not result.word_count_ok:
        parts.append(
            f"字数偏差：{result.word_count}/{result.word_count_target}"
        )
    if not result.scene_count_ok:
        parts.append(
            f"场景数不足：{result.scene_count} 个（要求至少 {result.scene_count_target} 个）"
        )
    if result.generic_name_count > 0:
        names = "、".join(m.name for m in result.generic_name_matches)
        parts.append(f"发现 {result.generic_name_count} 个通用角色名（{names}）")
    if result.meta_tag_count > 0:
        parts.append(f"发现 {result.meta_tag_count} 处元标记泄漏")
    if result.markdown_scene_title_count > 0:
        parts.append(
            f"发现 {result.markdown_scene_title_count} 处 Markdown 场景标题（建议改为空行分隔）"
        )
    if result.text_artifact_count > 0:
        parts.append(f"发现 {result.text_artifact_count} 处文本洁净 artifact")
    if result.motif_fatigue_count > 0:
        motifs = "、".join(m.motif for m in result.motif_fatigue_matches)
        parts.append(f"发现 {result.motif_fatigue_count} 类母题疲劳（{motifs}）")
    if result.duplicate_paragraph_count > 0:
        parts.append(f"发现 {result.duplicate_paragraph_count} 处重复长段落")
    if result.short_paragraph_ratio > 0.50:
        parts.append(
            f"短段落占比偏高（{result.short_paragraph_ratio:.0%}，建议控制 <50%）"
        )
    if result.exposition_carrier_count > 0:
        parts.append(
            f"发现 {result.exposition_carrier_count} 处说明文载体硬灌（exposition 风险）"
        )

    if result.punch_check.expected_punch_count > 0:
        if not result.punch_check.punch_density_ok:
            parts.append("刺激点密度不足")
        if not result.punch_check.emotion_switch_ok:
            parts.append("情绪转折不足")

    if not result.mandatory_reference_check_passed:
        parts.append(
            f"强制连续性约束未回收：{len(result.mandatory_reference_issues)} 项"
        )

    if not parts:
        return "规则检测通过，未发现明显问题。"
    return "；".join(parts) + "。"
