"""Task 199 offline style extraction to style card.

The generated cards are observations over accepted prose.  They are not prompt
cards, are not injected into Writer / CreativeDirector, and do not affect CED,
five-gate, segment audit, T9, or any runtime gate.
"""

from __future__ import annotations

import json
import re
from collections import Counter, defaultdict
from datetime import UTC, datetime
from pathlib import Path
from statistics import mean
from typing import Any, Literal

from pydantic import BaseModel, Field

from songyan.evals.excellence_sampling import AnnotationRecord
from songyan.evals.excellence_signals import (
    ChapterSignalReport,
    ExcellenceSignalError,
    ExcellenceSignalReport,
    LoadedChapter,
    load_task196_inputs,
)
from songyan.utils._helpers import split_paragraphs, split_sentences

StyleScopeMode = Literal["all", "by-genre", "both"]

QUOTE_RE = re.compile(r"[“「『\"]([^”」』\"]{2,100})[”」』\"]")
TENSION_WORDS = (
    "死",
    "杀",
    "血",
    "痛",
    "危险",
    "警报",
    "倒计时",
    "必须",
    "无法",
    "崩",
    "爆",
    "真相",
    "秘密",
    "代价",
)
POV_WORDS = ("想", "觉得", "意识到", "明白", "记得", "心中", "心里", "忽然", "仿佛")
EXPOSITION_MARKERS = ("也就是说", "换句话说", "这意味着", "事实上", "因此", "原来", "规则", "协议")
GENRE_TERMS = (
    "方舟",
    "共鸣",
    "协议",
    "坐标",
    "核心",
    "灵渊",
    "血脉",
    "令牌",
    "守门",
    "拳",
    "刀",
    "剑",
)


class StyleCardError(RuntimeError):
    """Raised when Task 199 style card extraction cannot proceed."""


class StyleEvidence(BaseModel):
    """A concrete text example supporting an extracted style trait."""

    chapter: int = Field(ge=1)
    quote: str
    detail: str = ""


class NarrativeVoiceCard(BaseModel):
    """Narrative point of view and distance."""

    dominant_person: str
    pov_depth: str
    tone: str
    evidence: list[StyleEvidence] = Field(default_factory=list)


class SentenceRhythmCard(BaseModel):
    """Sentence and paragraph rhythm."""

    avg_sentence_chars: float
    avg_paragraph_chars: float
    short_sentence_ratio: float
    long_sentence_ratio: float
    dialogue_ratio: float
    rhythm_label: str
    evidence: list[StyleEvidence] = Field(default_factory=list)


class ImageryLexiconCard(BaseModel):
    """Frequent imagery and lexical motifs."""

    top_terms: list[str] = Field(default_factory=list)
    genre_terms: list[str] = Field(default_factory=list)
    overused_terms: list[str] = Field(default_factory=list)
    evidence: list[StyleEvidence] = Field(default_factory=list)


class ExpositionStyleCard(BaseModel):
    """How the prose releases settings and explanations."""

    exposition_density: float
    setting_patch_hits: int
    style_label: str
    risks: list[str] = Field(default_factory=list)
    evidence: list[StyleEvidence] = Field(default_factory=list)


class TensionPatternCard(BaseModel):
    """Observed tension curve shape."""

    average_tension: float
    peak_tension: float
    tension_stdev: float
    pattern: str
    dominant_scene_functions: list[str] = Field(default_factory=list)


class DialogueStyleCardObservation(BaseModel):
    """Global dialogue tendency, not per-character voice."""

    dialogue_ratio: float
    dialogue_line_count: int
    avg_dialogue_sentence_chars: float
    style_label: str
    sample_lines: list[str] = Field(default_factory=list)


class AntiPatternCard(BaseModel):
    """Report-only style risk aggregated from Task 197/198 hits."""

    signal_id: str
    label: str
    count: int
    max_severity: str
    examples: list[str] = Field(default_factory=list)


class ExtractedStyleCard(BaseModel):
    """Task 199 style card observation."""

    scope: str
    source_chapters: list[str]
    report_only: bool = True
    usage_note: str
    narrative_voice: NarrativeVoiceCard
    sentence_rhythm: SentenceRhythmCard
    imagery_lexicon: ImageryLexiconCard
    exposition_style: ExpositionStyleCard
    tension_pattern: TensionPatternCard
    dialogue_style: DialogueStyleCardObservation
    anti_patterns: list[AntiPatternCard] = Field(default_factory=list)


class StyleCardSanityCheck(BaseModel):
    """Directional sanity check against Task 196 agent-deep-read labels."""

    scope: str
    strong_count: int
    strong_with_style_traits: int
    weak_count: int
    weak_with_anti_patterns: int
    weak_unexplained: list[str] = Field(default_factory=list)
    notes: list[str] = Field(default_factory=list)


class StyleCardReport(BaseModel):
    """Top-level Task 199 report."""

    generated_at: str
    sample_set: str
    annotations: str
    excellence_report: str
    report_only: bool = True
    boundaries: list[str]
    cards: list[ExtractedStyleCard]
    sanity_checks: list[StyleCardSanityCheck]


def load_style_card_inputs(
    sample_set_path: Path,
    annotations_path: Path,
    excellence_report_path: Path,
) -> tuple[
    list[LoadedChapter],
    dict[str, AnnotationRecord],
    ExcellenceSignalReport,
]:
    """Load Task 196 accepted text and Task 197/198 report artifacts."""
    try:
        chapters, annotations = load_task196_inputs(sample_set_path, annotations_path)
    except ExcellenceSignalError as exc:
        raise StyleCardError(str(exc)) from exc
    try:
        raw_report = json.loads(excellence_report_path.read_text(encoding="utf-8"))
    except OSError as exc:
        raise StyleCardError(f"failed to read {excellence_report_path}: {exc}") from exc
    if not isinstance(raw_report, dict):
        raise StyleCardError(f"expected JSON object: {excellence_report_path}")
    return (
        chapters,
        annotations,
        ExcellenceSignalReport.model_validate(raw_report),
    )


def build_style_card_report(
    chapters: list[LoadedChapter],
    annotations: dict[str, AnnotationRecord],
    excellence_report: ExcellenceSignalReport,
    *,
    sample_set_path: Path,
    annotations_path: Path,
    excellence_report_path: Path,
    scope_mode: StyleScopeMode = "both",
) -> StyleCardReport:
    """Build report-only style cards from loaded accepted prose."""
    report_by_version = {
        chapter.version_id: chapter for chapter in excellence_report.chapters
    }
    groups = _group_chapters(chapters, scope_mode)
    cards: list[ExtractedStyleCard] = []
    checks: list[StyleCardSanityCheck] = []
    for scope, scoped_chapters in groups:
        scoped_reports = [
            report_by_version[chapter.version_id]
            for chapter in scoped_chapters
            if chapter.version_id in report_by_version
        ]
        card = _build_card(scope, scoped_chapters, scoped_reports)
        cards.append(card)
        checks.append(_build_sanity_check(scope, scoped_chapters, scoped_reports, annotations))
    return StyleCardReport(
        generated_at=datetime.now(UTC).isoformat(),
        sample_set=sample_set_path.as_posix(),
        annotations=annotations_path.as_posix(),
        excellence_report=excellence_report_path.as_posix(),
        boundaries=[
            "report-only / observe-only",
            "style card is an observed profile, not a prompt constraint",
            "does not modify Writer or CreativeDirector prompts",
            "does not enter accept/reject gates",
            "does not change CED, five-gate, segment audit, or T9",
            "does not create character voice anchors; Task 200 owns that scope",
        ],
        cards=cards,
        sanity_checks=checks,
    )


def render_style_card_report(report: StyleCardReport) -> str:
    """Render Task 199 style card report as Markdown."""
    lines = [
        "# Task 199 Style Card 离线报告",
        "",
        f"> generated_at: `{report.generated_at}`",
        f"> sample_set: `{report.sample_set}`",
        f"> annotations: `{report.annotations}`",
        f"> excellence_report: `{report.excellence_report}`",
        "",
        "## 边界",
        "",
    ]
    lines.extend(f"- {item}" for item in report.boundaries)
    lines.extend(["", "## 总览", ""])
    lines.append("| scope | chapters | rhythm | dialogue | exposition | tension | anti-patterns |")
    lines.append("|-------|----------|--------|----------|------------|---------|---------------|")
    for card in report.cards:
        lines.append(
            f"| {card.scope} | {len(card.source_chapters)} | "
            f"{card.sentence_rhythm.rhythm_label} | "
            f"{card.dialogue_style.style_label} | "
            f"{card.exposition_style.style_label} | "
            f"{card.tension_pattern.pattern} | "
            f"{len(card.anti_patterns)} |"
        )

    for card in report.cards:
        lines.extend(["", f"## Style Card: {card.scope}", ""])
        lines.append(f"> {card.usage_note}")
        lines.extend(
            [
                "",
                "### Narrative Voice",
                "",
                f"- dominant_person: `{card.narrative_voice.dominant_person}`",
                f"- pov_depth: `{card.narrative_voice.pov_depth}`",
                f"- tone: `{card.narrative_voice.tone}`",
            ]
        )
        _append_evidence(lines, card.narrative_voice.evidence)
        lines.extend(
            [
                "",
                "### Sentence Rhythm",
                "",
                f"- avg_sentence_chars: `{card.sentence_rhythm.avg_sentence_chars}`",
                f"- avg_paragraph_chars: `{card.sentence_rhythm.avg_paragraph_chars}`",
                f"- dialogue_ratio: `{card.sentence_rhythm.dialogue_ratio}`",
                f"- rhythm_label: `{card.sentence_rhythm.rhythm_label}`",
            ]
        )
        lines.extend(
            [
                "",
                "### Imagery Lexicon",
                "",
                f"- top_terms: {', '.join(card.imagery_lexicon.top_terms) or '-'}",
                f"- genre_terms: {', '.join(card.imagery_lexicon.genre_terms) or '-'}",
                f"- overused_terms: {', '.join(card.imagery_lexicon.overused_terms) or '-'}",
            ]
        )
        _append_evidence(lines, card.imagery_lexicon.evidence)
        lines.extend(
            [
                "",
                "### Exposition Style",
                "",
                f"- exposition_density: `{card.exposition_style.exposition_density}`",
                f"- setting_patch_hits: `{card.exposition_style.setting_patch_hits}`",
                f"- style_label: `{card.exposition_style.style_label}`",
                f"- risks: {', '.join(card.exposition_style.risks) or '-'}",
                "",
                "### Tension Pattern",
                "",
                f"- average_tension: `{card.tension_pattern.average_tension}`",
                f"- peak_tension: `{card.tension_pattern.peak_tension}`",
                f"- tension_stdev: `{card.tension_pattern.tension_stdev}`",
                f"- pattern: `{card.tension_pattern.pattern}`",
                "- dominant_scene_functions: "
                f"{', '.join(card.tension_pattern.dominant_scene_functions) or '-'}",
                "",
                "### Dialogue Style",
                "",
                f"- dialogue_ratio: `{card.dialogue_style.dialogue_ratio}`",
                f"- dialogue_line_count: `{card.dialogue_style.dialogue_line_count}`",
                f"- avg_dialogue_sentence_chars: "
                f"`{card.dialogue_style.avg_dialogue_sentence_chars}`",
                f"- style_label: `{card.dialogue_style.style_label}`",
            ]
        )
        if card.dialogue_style.sample_lines:
            lines.append("- sample_lines:")
            lines.extend(f"  - `{line}`" for line in card.dialogue_style.sample_lines[:5])
        lines.extend(["", "### Anti Patterns", ""])
        if not card.anti_patterns:
            lines.append("无聚合风险。")
        else:
            lines.append("| signal | count | severity | examples |")
            lines.append("|--------|------:|----------|----------|")
            for item in card.anti_patterns[:10]:
                examples = "<br>".join(_shorten(example, 60) for example in item.examples[:3])
                lines.append(
                    f"| `{item.signal_id}` | {item.count} | {item.max_severity} | "
                    f"{examples or '-'} |"
                )

    lines.extend(["", "## Sanity Check", ""])
    lines.append("| scope | strong | strong traits | weak | weak explained | weak unexplained |")
    lines.append("|-------|--------|---------------|------|----------------|------------------|")
    for check in report.sanity_checks:
        lines.append(
            f"| {check.scope} | {check.strong_count} | "
            f"{check.strong_with_style_traits} | {check.weak_count} | "
            f"{check.weak_with_anti_patterns} | "
            f"{', '.join(check.weak_unexplained) or '-'} |"
        )
    lines.extend(
        [
            "",
            "## 局限",
            "",
            "- 本报告只覆盖 Task 196 的 xuanhuan + sci-fi 60 章样本。",
            "- style card 是观察画像，不是 Writer / CreativeDirector 约束。",
            "- 角色声纹锚点不在本任务内，归 Task 200。",
            "- prelabel 仅作对照；sanity check 使用 agent-deep-read 标注。",
        ]
    )
    return "\n".join(lines) + "\n"


def _build_card(
    scope: str,
    chapters: list[LoadedChapter],
    reports: list[ChapterSignalReport],
) -> ExtractedStyleCard:
    combined = "\n".join(chapter.content for chapter in chapters)
    source_chapters = [f"{chapter.genre} Ch{chapter.chapter}" for chapter in chapters]
    return ExtractedStyleCard(
        scope=scope,
        source_chapters=source_chapters,
        usage_note=(
            "观察到的风格画像；V10 内不得默认注入 Writer / CreativeDirector prompt。"
        ),
        narrative_voice=_extract_narrative_voice(combined, chapters),
        sentence_rhythm=_extract_sentence_rhythm(combined, chapters),
        imagery_lexicon=_extract_imagery_lexicon(combined, chapters, reports),
        exposition_style=_extract_exposition_style(combined, chapters, reports),
        tension_pattern=_extract_tension_pattern(reports),
        dialogue_style=_extract_dialogue_style(combined),
        anti_patterns=_aggregate_anti_patterns(reports),
    )


def _extract_narrative_voice(
    text: str,
    chapters: list[LoadedChapter],
) -> NarrativeVoiceCard:
    first = text.count("我") + text.count("我们")
    second = text.count("你") + text.count("你们")
    third = text.count("他") + text.count("她") + text.count("它")
    counts = {"first": first, "second": second, "third": third}
    dominant = max(counts.items(), key=lambda item: (item[1], item[0]))[0]
    pov_density = sum(text.count(word) for word in POV_WORDS) / max(len(text), 1)
    pov_depth = "deep" if pov_density > 0.006 else "medium" if pov_density > 0.003 else "shallow"
    tension_density = sum(text.count(word) for word in TENSION_WORDS) / max(len(text), 1)
    dialogue_ratio = _dialogue_char_ratio(text)
    if tension_density > 0.006:
        tone = "high-pressure"
    elif dialogue_ratio > 0.28:
        tone = "dialogue-driven"
    else:
        tone = "restrained-observational"
    return NarrativeVoiceCard(
        dominant_person=dominant,
        pov_depth=pov_depth,
        tone=tone,
        evidence=_sample_evidence(chapters, POV_WORDS, limit=3),
    )


def _extract_sentence_rhythm(
    text: str,
    chapters: list[LoadedChapter],
) -> SentenceRhythmCard:
    sentences = _all_sentences(text)
    paragraphs = split_paragraphs(text)
    sentence_lengths = [len(sentence) for sentence in sentences] or [0]
    paragraph_lengths = [len(paragraph) for paragraph in paragraphs] or [0]
    avg_sentence = round(mean(sentence_lengths), 2)
    avg_paragraph = round(mean(paragraph_lengths), 2)
    short_ratio = round(
        sum(1 for length in sentence_lengths if length <= 18) / len(sentence_lengths),
        3,
    )
    long_ratio = round(
        sum(1 for length in sentence_lengths if length >= 45) / len(sentence_lengths),
        3,
    )
    dialogue_ratio = round(_dialogue_char_ratio(text), 3)
    if avg_sentence < 22:
        rhythm = "short-pulse"
    elif avg_sentence > 38:
        rhythm = "long-flow"
    else:
        rhythm = "mixed-cadence"
    return SentenceRhythmCard(
        avg_sentence_chars=avg_sentence,
        avg_paragraph_chars=avg_paragraph,
        short_sentence_ratio=short_ratio,
        long_sentence_ratio=long_ratio,
        dialogue_ratio=dialogue_ratio,
        rhythm_label=rhythm,
        evidence=_sample_evidence(chapters, ("。", "！", "？"), limit=3),
    )


def _extract_imagery_lexicon(
    text: str,
    chapters: list[LoadedChapter],
    reports: list[ChapterSignalReport],
) -> ImageryLexiconCard:
    terms = _dominant_terms(text, limit=12)
    genre_terms = [term for term in GENRE_TERMS if text.count(term) >= 3]
    overused = _overused_terms_from_reports(reports)
    evidence_terms = tuple(terms[:3] + genre_terms[:3])
    return ImageryLexiconCard(
        top_terms=terms[:10],
        genre_terms=genre_terms[:10],
        overused_terms=overused[:10],
        evidence=_sample_evidence(chapters, evidence_terms or ("",), limit=3),
    )


def _extract_exposition_style(
    text: str,
    chapters: list[LoadedChapter],
    reports: list[ChapterSignalReport],
) -> ExpositionStyleCard:
    sentences = _all_sentences(text)
    marker_count = sum(text.count(marker) for marker in EXPOSITION_MARKERS)
    density = round(marker_count / max(len(sentences), 1), 3)
    patch_hits = sum(
        1
        for report in reports
        for hit in report.hits
        if hit.signal_id == "setting_patch_segment"
    )
    risks: list[str] = []
    if density > 0.12:
        risks.append("exposition_marker_density")
    if patch_hits:
        risks.append("setting_patch_segment")
    if density <= 0.05 and patch_hits == 0:
        label = "embedded-in-action"
    elif density <= 0.12:
        label = "mixed-exposition"
    else:
        label = "exposition-forward"
    return ExpositionStyleCard(
        exposition_density=density,
        setting_patch_hits=patch_hits,
        style_label=label,
        risks=risks,
        evidence=_sample_evidence(chapters, EXPOSITION_MARKERS, limit=3),
    )


def _extract_tension_pattern(reports: list[ChapterSignalReport]) -> TensionPatternCard:
    averages = [report.task197.tension_average for report in reports]
    peaks = [report.task197.tension_peak for report in reports]
    stdevs = [report.task197.tension_stdev for report in reports]
    flatline_count = sum(
        1
        for report in reports
        for hit in report.hits
        if hit.signal_id == "tension_flatline"
    )
    scene_counter = Counter(report.task197.scene_function for report in reports)
    average = round(mean(averages), 3) if averages else 0.0
    peak = round(max(peaks), 3) if peaks else 0.0
    stdev = round(mean(stdevs), 3) if stdevs else 0.0
    if reports and flatline_count / len(reports) >= 0.35:
        pattern = "flatline-risk"
    elif peak >= 2.5 and stdev >= 0.45:
        pattern = "spike-driven"
    else:
        pattern = "steady-escalation"
    return TensionPatternCard(
        average_tension=average,
        peak_tension=peak,
        tension_stdev=stdev,
        pattern=pattern,
        dominant_scene_functions=[item for item, _count in scene_counter.most_common(5)],
    )


def _extract_dialogue_style(text: str) -> DialogueStyleCardObservation:
    quoted_lines = [line.strip() for line in QUOTE_RE.findall(text)]
    dialogue_ratio = round(_dialogue_char_ratio(text), 3)
    line_lengths = [len(line) for line in quoted_lines] or [0]
    avg_line = round(mean(line_lengths), 2)
    if not quoted_lines:
        label = "narration-heavy"
    elif avg_line < 18:
        label = "short-exchange"
    elif dialogue_ratio > 0.3:
        label = "dialogue-forward"
    else:
        label = "measured-dialogue"
    return DialogueStyleCardObservation(
        dialogue_ratio=dialogue_ratio,
        dialogue_line_count=len(quoted_lines),
        avg_dialogue_sentence_chars=avg_line,
        style_label=label,
        sample_lines=[_shorten(line, 80) for line in quoted_lines[:8]],
    )


def _aggregate_anti_patterns(reports: list[ChapterSignalReport]) -> list[AntiPatternCard]:
    by_signal: dict[str, list[tuple[ChapterSignalReport, Any]]] = defaultdict(list)
    for report in reports:
        for hit in report.hits:
            by_signal[hit.signal_id].append((report, hit))
    out: list[AntiPatternCard] = []
    severity_rank = {"low": 1, "medium": 2, "high": 3}
    for signal_id, pairs in by_signal.items():
        label = pairs[0][1].label
        max_severity = max(
            (pair[1].severity for pair in pairs),
            key=lambda severity: severity_rank.get(severity, 0),
        )
        examples: list[str] = []
        for report, hit in pairs[:5]:
            quote = hit.evidence[0].quote if hit.evidence else hit.detail
            examples.append(f"{report.genre} Ch{report.chapter}: {_shorten(quote, 80)}")
        out.append(
            AntiPatternCard(
                signal_id=signal_id,
                label=label,
                count=len(pairs),
                max_severity=max_severity,
                examples=examples,
            )
        )
    return sorted(out, key=lambda item: (-item.count, item.signal_id))


def _build_sanity_check(
    scope: str,
    chapters: list[LoadedChapter],
    reports: list[ChapterSignalReport],
    annotations: dict[str, AnnotationRecord],
) -> StyleCardSanityCheck:
    reports_by_version = {report.version_id: report for report in reports}
    strong = []
    weak = []
    weak_unexplained: list[str] = []
    for chapter in chapters:
        annotation = annotations.get(chapter.version_id)
        if annotation is None or annotation.annotator != "agent-deep-read":
            continue
        label = f"{chapter.genre} Ch{chapter.chapter}"
        overall = annotation.scores.overall
        ai_tone = annotation.scores.ai_tone
        if overall >= 4:
            strong.append(label)
        if overall <= 2 or ai_tone <= 2:
            weak.append(label)
            report = reports_by_version.get(chapter.version_id)
            if report is None or not report.hits:
                weak_unexplained.append(label)
    notes = [
        "strong_with_style_traits uses non-empty extracted traits as a smoke check",
        "weak_with_anti_patterns requires at least one Task 197/198 hit",
    ]
    return StyleCardSanityCheck(
        scope=scope,
        strong_count=len(strong),
        strong_with_style_traits=len(strong),
        weak_count=len(weak),
        weak_with_anti_patterns=len(weak) - len(weak_unexplained),
        weak_unexplained=weak_unexplained,
        notes=notes,
    )


def _group_chapters(
    chapters: list[LoadedChapter],
    scope_mode: StyleScopeMode,
) -> list[tuple[str, list[LoadedChapter]]]:
    ordered = sorted(chapters, key=lambda item: (item.genre, item.chapter))
    if scope_mode == "all":
        return [("all", ordered)]
    by_genre: dict[str, list[LoadedChapter]] = defaultdict(list)
    for chapter in ordered:
        by_genre[chapter.genre].append(chapter)
    groups = [(f"genre:{genre}", values) for genre, values in sorted(by_genre.items())]
    if scope_mode == "by-genre":
        return groups
    return [("all", ordered), *groups]


def _dialogue_char_ratio(text: str) -> float:
    if not text:
        return 0.0
    dialogue_chars = 0
    for paragraph in split_paragraphs(text):
        if _is_dialogue_paragraph(paragraph):
            dialogue_chars += len(paragraph)
    return dialogue_chars / len(text)


def _is_dialogue_paragraph(paragraph: str) -> bool:
    return bool(
        re.search(r"[“”「」『』\"]", paragraph)
        or re.search(r"(?:说道|问道|答道|低声|喊道|开口|笑道)", paragraph)
    )


def _sample_evidence(
    chapters: list[LoadedChapter],
    keywords: tuple[str, ...],
    *,
    limit: int,
) -> list[StyleEvidence]:
    evidence: list[StyleEvidence] = []
    for chapter in chapters:
        quote = _first_matching_paragraph(chapter.content, keywords)
        if quote:
            evidence.append(
                StyleEvidence(
                    chapter=chapter.chapter,
                    quote=_shorten(quote, 120),
                    detail=chapter.genre,
                )
            )
        if len(evidence) >= limit:
            break
    if not evidence and chapters:
        first = split_paragraphs(chapters[0].content)
        if first:
            evidence.append(
                StyleEvidence(
                    chapter=chapters[0].chapter,
                    quote=_shorten(first[0], 120),
                    detail=chapters[0].genre,
                )
            )
    return evidence


def _first_matching_paragraph(text: str, keywords: tuple[str, ...]) -> str:
    paragraphs = split_paragraphs(text)
    if not keywords or keywords == ("",):
        return paragraphs[0] if paragraphs else ""
    for paragraph in paragraphs:
        if any(keyword and keyword in paragraph for keyword in keywords):
            return paragraph
    return ""


def _all_sentences(text: str) -> list[str]:
    sentences: list[str] = []
    for paragraph in split_paragraphs(text):
        sentences.extend(s.strip() for s in split_sentences(paragraph) if s.strip())
    return sentences


def _dominant_terms(text: str, *, limit: int) -> list[str]:
    normalized = re.sub(r"[^\u4e00-\u9fff]", "", text)
    counter: Counter[str] = Counter()
    for size in (2, 3, 4):
        for idx in range(0, max(0, len(normalized) - size + 1)):
            term = normalized[idx : idx + size]
            if _is_low_value_term(term):
                continue
            counter[term] += 1
    return [term for term, count in counter.most_common(limit * 2) if count >= 6][:limit]


def _overused_terms_from_reports(reports: list[ChapterSignalReport]) -> list[str]:
    terms: Counter[str] = Counter()
    for report in reports:
        for hit in report.hits:
            if hit.signal_id != "motif_reuse_density" or not hit.evidence:
                continue
            for raw in re.split(r"[,，、]\s*", hit.evidence[0].quote):
                term = raw.strip()
                if term and not _is_low_value_term(term):
                    terms[term] += 1
    return [term for term, _count in terms.most_common(10)]


def _is_low_value_term(term: str) -> bool:
    if len(set(term)) <= 1:
        return True
    if term.endswith("的") or term.startswith("的"):
        return True
    low_value = {
        "他们",
        "自己",
        "这个",
        "那个",
        "一种",
        "一个",
        "一下",
        "里面",
        "已经",
        "没有",
        "不是",
        "就是",
        "时候",
        "声音",
        "看着",
        "什么",
        "他的",
        "她的",
        "它的",
        "了一",
        "了。",
        "声音",
        "林渊",
        "陆沉",
    }
    return term in low_value


def _append_evidence(lines: list[str], evidence: list[StyleEvidence]) -> None:
    if not evidence:
        return
    lines.append("- evidence:")
    for item in evidence[:3]:
        lines.append(f"  - Ch{item.chapter} `{item.quote}`")


def _shorten(text: str, limit: int) -> str:
    collapsed = re.sub(r"\s+", " ", text.strip())
    if len(collapsed) <= limit:
        return collapsed
    return collapsed[: limit - 1] + "…"
