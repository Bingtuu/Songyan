"""Task 200 offline character voice anchor extraction.

The output is an observation report over accepted prose.  It is not
``DialogueStyleCard`` runtime data, is not written back to character profiles,
and is not injected into Writer / CreativeDirector prompts.
"""

from __future__ import annotations

import json
import re
import sqlite3
from collections import Counter, defaultdict
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path
from statistics import mean, pstdev
from typing import Any, Literal

from pydantic import BaseModel, Field

from songyan.evals.excellence_sampling import AnnotationRecord
from songyan.evals.excellence_signals import (
    ExcellenceSignalReport,
    LoadedChapter,
    load_task196_inputs,
)
from songyan.evals.style_card_extraction import StyleCardReport
from songyan.utils._helpers import locate_position, split_sentences

VoiceScopeMode = Literal["all", "by-genre", "both"]

QUOTE_RE = re.compile(r"[“「『\"]([^”」』\"]{2,180})[”」』\"]")
SPEECH_VERBS = (
    "说",
    "道",
    "问",
    "答",
    "喊",
    "喊道",
    "低声",
    "沉声",
    "冷声",
    "笑道",
    "吼道",
    "怒吼",
    "开口",
    "补充",
    "继续",
    "反问",
    "喃喃",
    "嘀咕",
)
VOICE_ATTRIBUTION_WORDS = ("声音", "嗓音", "录音", "语音", "话音", "声线")
EMOTION_WORDS = (
    "冷",
    "怒",
    "笑",
    "怕",
    "急",
    "慌",
    "疼",
    "痛",
    "静",
    "沉",
    "哑",
    "颤",
    "疯",
    "杀",
)
INTERACTION_WORDS = (
    "别",
    "快",
    "必须",
    "不行",
    "为什么",
    "怎么",
    "等等",
    "听着",
    "走",
    "停",
)
LOW_VALUE_TERMS = {
    "我们",
    "你们",
    "他们",
    "这个",
    "那个",
    "不是",
    "就是",
    "没有",
    "已经",
    "什么",
    "怎么",
    "为什么",
}
PRONOUNS = {"他", "她", "它", "我", "你", "我们", "你们", "他们", "她们", "它们"}


class VoiceAnchorError(RuntimeError):
    """Raised when Task 200 inputs are invalid."""


@dataclass(frozen=True)
class CharacterRegistryEntry:
    """Read-only character registry entry from a Task 196 source DB."""

    genre: str
    character_id: str
    name: str
    role_type: str


class VoiceEvidenceLine(BaseModel):
    """One attributed or unknown dialogue line."""

    genre: str
    chapter: int = Field(ge=1)
    speaker_name: str
    text: str
    attribution: str
    location: str


class SentenceLengthProfile(BaseModel):
    """Sentence length profile for one character."""

    quote_count: int
    sentence_count: int
    avg_sentence_chars: float
    stdev_sentence_chars: float
    short_sentence_ratio: float
    long_sentence_ratio: float


class VoiceAnchorObservation(BaseModel):
    """Report-only character voice anchor observation."""

    scope: str
    character_id: str
    character_name: str
    role_type: str = ""
    evidence_chapters: list[str] = Field(default_factory=list)
    sample_lines: list[VoiceEvidenceLine] = Field(default_factory=list)
    sentence_length_profile: SentenceLengthProfile
    lexical_markers: list[str] = Field(default_factory=list)
    emotional_register: list[str] = Field(default_factory=list)
    interaction_pattern: str
    distinctiveness_score: float | None = None
    drift_or_homogeneity_hits: list[str] = Field(default_factory=list)
    limitations: list[str] = Field(default_factory=list)


class UnknownAttributionSummary(BaseModel):
    """Dialogue lines that could not be safely attributed."""

    scope: str
    line_count: int
    ratio: float
    sample_lines: list[VoiceEvidenceLine] = Field(default_factory=list)
    limitations: list[str] = Field(default_factory=list)


class VoiceAnchorSanityCheck(BaseModel):
    """Directional sanity check against Task 196 deep-read labels."""

    scope: str
    weak_samples: int
    weak_with_voice_evidence: int
    weak_unexplained: list[str] = Field(default_factory=list)
    notes: list[str] = Field(default_factory=list)


class VoiceAnchorReport(BaseModel):
    """Top-level Task 200 report."""

    generated_at: str
    sample_set: str
    annotations: str
    excellence_report: str
    style_card_report: str
    report_only: bool = True
    boundaries: list[str]
    anchors: list[VoiceAnchorObservation]
    unknown_attribution: list[UnknownAttributionSummary]
    sanity_checks: list[VoiceAnchorSanityCheck]


@dataclass(frozen=True)
class AttributedLine:
    genre: str
    chapter: int
    version_id: str
    text: str
    speaker_name: str
    character_id: str
    role_type: str
    attribution: str
    location: str


def load_voice_anchor_inputs(
    sample_set_path: Path,
    annotations_path: Path,
    excellence_report_path: Path,
    style_card_report_path: Path,
) -> tuple[
    list[LoadedChapter],
    dict[str, AnnotationRecord],
    ExcellenceSignalReport,
    StyleCardReport,
    dict[str, list[CharacterRegistryEntry]],
]:
    """Load Task 196/197/198/199 report-only inputs."""
    try:
        chapters, annotations = load_task196_inputs(sample_set_path, annotations_path)
    except Exception as exc:
        raise VoiceAnchorError(f"failed to load Task 196 inputs: {exc}") from exc
    excellence_report = _load_model(excellence_report_path, ExcellenceSignalReport)
    style_report = _load_model(style_card_report_path, StyleCardReport)
    registry = _load_character_registry(sample_set_path)
    return chapters, annotations, excellence_report, style_report, registry


def build_voice_anchor_report(
    chapters: list[LoadedChapter],
    annotations: dict[str, AnnotationRecord],
    excellence_report: ExcellenceSignalReport,
    style_card_report: StyleCardReport,
    registry: dict[str, list[CharacterRegistryEntry]],
    *,
    sample_set_path: Path,
    annotations_path: Path,
    excellence_report_path: Path,
    style_card_report_path: Path,
    scope_mode: VoiceScopeMode = "both",
    min_lines: int = 2,
) -> VoiceAnchorReport:
    """Build Task 200 report-only voice anchor report."""
    groups = _group_chapters(chapters, scope_mode)
    report_by_version = {chapter.version_id: chapter for chapter in excellence_report.chapters}
    anchors: list[VoiceAnchorObservation] = []
    unknown_summaries: list[UnknownAttributionSummary] = []
    checks: list[VoiceAnchorSanityCheck] = []
    for scope, scoped_chapters in groups:
        scoped_lines = _extract_lines_for_scope(scoped_chapters, registry)
        known_lines = [line for line in scoped_lines if line.speaker_name != "unknown"]
        unknown_lines = [line for line in scoped_lines if line.speaker_name == "unknown"]
        scoped_anchors = _build_anchors(scope, known_lines, min_lines=min_lines)
        anchors.extend(scoped_anchors)
        unknown_summaries.append(_unknown_summary(scope, scoped_lines, unknown_lines))
        checks.append(
            _sanity_check(
                scope,
                scoped_chapters,
                scoped_lines,
                annotations,
                report_by_version,
            )
        )
    return VoiceAnchorReport(
        generated_at=datetime.now(UTC).isoformat(),
        sample_set=sample_set_path.as_posix(),
        annotations=annotations_path.as_posix(),
        excellence_report=excellence_report_path.as_posix(),
        style_card_report=style_card_report_path.as_posix(),
        boundaries=[
            "report-only / observe-only",
            "voice anchors are observations, not DialogueStyleCard runtime data",
            "does not write back to characters or character_states",
            "does not modify Writer or CreativeDirector prompts",
            "does not enter accept/reject gates",
            "does not change CED, five-gate, segment audit, or T9",
        ],
        anchors=anchors,
        unknown_attribution=unknown_summaries,
        sanity_checks=checks,
    )


def render_voice_anchor_report(report: VoiceAnchorReport) -> str:
    """Render Task 200 voice anchor report as Markdown."""
    lines = [
        "# Task 200 角色声纹锚点离线报告",
        "",
        f"> generated_at: `{report.generated_at}`",
        f"> sample_set: `{report.sample_set}`",
        f"> annotations: `{report.annotations}`",
        f"> excellence_report: `{report.excellence_report}`",
        f"> style_card_report: `{report.style_card_report}`",
        "",
        "## 边界",
        "",
    ]
    lines.extend(f"- {item}" for item in report.boundaries)
    lines.extend(["", "## 总览", ""])
    lines.append("| scope | anchors | unknown lines | weak explained |")
    lines.append("|-------|--------:|--------------:|----------------|")
    checks_by_scope = {check.scope: check for check in report.sanity_checks}
    unknown_by_scope = {item.scope: item for item in report.unknown_attribution}
    scopes = sorted({anchor.scope for anchor in report.anchors} | set(unknown_by_scope))
    for scope in scopes:
        count = sum(1 for anchor in report.anchors if anchor.scope == scope)
        unknown = unknown_by_scope.get(scope)
        check = checks_by_scope.get(scope)
        explained = "-"
        if check is not None:
            explained = f"{check.weak_with_voice_evidence}/{check.weak_samples}"
        lines.append(
            f"| {scope} | {count} | {unknown.line_count if unknown else 0} | {explained} |"
        )

    lines.extend(["", "## 声纹锚点", ""])
    if not report.anchors:
        lines.append("无足够归因样本生成角色声纹锚点。")
    for anchor in report.anchors:
        lines.extend(
            [
                f"### {anchor.scope} / {anchor.character_name}",
                "",
                f"- character_id: `{anchor.character_id}`",
                f"- role_type: `{anchor.role_type or '-'}`",
                f"- evidence_chapters: {', '.join(anchor.evidence_chapters) or '-'}",
                f"- distinctiveness_score: `{anchor.distinctiveness_score}`",
                f"- interaction_pattern: `{anchor.interaction_pattern}`",
                f"- lexical_markers: {', '.join(anchor.lexical_markers) or '-'}",
                f"- emotional_register: {', '.join(anchor.emotional_register) or '-'}",
                "- drift_or_homogeneity_hits: "
                f"{', '.join(anchor.drift_or_homogeneity_hits) or '-'}",
                f"- limitations: {', '.join(anchor.limitations) or '-'}",
                "",
                "sample_lines:",
            ]
        )
        for sample in anchor.sample_lines[:5]:
            lines.append(
                f"- Ch{sample.chapter} `{sample.text}` "
                f"({sample.attribution}, {sample.location})"
            )
        lines.append("")

    lines.extend(["## Unknown Attribution", ""])
    for item in report.unknown_attribution:
        lines.extend(
            [
                f"### {item.scope}",
                "",
                f"- line_count: `{item.line_count}`",
                f"- ratio: `{item.ratio}`",
                f"- limitations: {', '.join(item.limitations) or '-'}",
            ]
        )
        for sample in item.sample_lines[:5]:
            lines.append(f"- Ch{sample.chapter} `{sample.text}` ({sample.location})")
        lines.append("")

    lines.extend(["## Sanity Check", ""])
    lines.append("| scope | weak samples | weak with voice evidence | weak unexplained |")
    lines.append("|-------|-------------:|-------------------------:|------------------|")
    for check in report.sanity_checks:
        lines.append(
            f"| {check.scope} | {check.weak_samples} | "
            f"{check.weak_with_voice_evidence} | "
            f"{', '.join(check.weak_unexplained) or '-'} |"
        )
    lines.extend(
        [
            "",
            "## 局限",
            "",
            "- 本报告只覆盖 Task 196 的 xuanhuan + sci-fi 60 章样本。",
            "- 说话人归因为启发式，unknown 必须保留，不得强行分配。",
            "- 本报告不是 DialogueStyleCard，不写回角色档案，不作为生成约束。",
            "- 弱样本解释是方向性 sanity check，不支持 hard gate 阈值。",
        ]
    )
    return "\n".join(lines) + "\n"


def extract_dialogue_lines(
    chapter: LoadedChapter,
    registry_entries: list[CharacterRegistryEntry],
) -> list[AttributedLine]:
    """Extract dialogue lines from one accepted chapter."""
    registry = {entry.name: entry for entry in registry_entries if entry.name}
    known_names = sorted(registry, key=len, reverse=True)
    lines: list[AttributedLine] = []
    last_speaker: CharacterRegistryEntry | None = None
    for match in QUOTE_RE.finditer(chapter.content):
        quote = match.group(1).strip()
        if not quote:
            continue
        before = chapter.content[max(0, match.start() - 80):match.start()]
        after = chapter.content[match.end():min(len(chapter.content), match.end() + 80)]
        entry, attribution = _attribute_speaker(before, after, known_names, registry, last_speaker)
        if entry is None:
            speaker_name = "unknown"
            character_id = f"unknown:{chapter.genre}"
            role_type = ""
            attribution = "unknown"
        elif _quote_addresses_candidate(quote, entry.name):
            speaker_name = "unknown"
            character_id = f"unknown:{chapter.genre}"
            role_type = ""
            attribution = "unknown_addressed_candidate"
        else:
            speaker_name = entry.name
            character_id = entry.character_id
            role_type = entry.role_type
            last_speaker = entry
        lines.append(
            AttributedLine(
                genre=chapter.genre,
                chapter=chapter.chapter,
                version_id=chapter.version_id,
                text=quote,
                speaker_name=speaker_name,
                character_id=character_id,
                role_type=role_type,
                attribution=attribution,
                location=locate_position(chapter.content, match.start()),
            )
        )
    return lines


def _attribute_speaker(
    before: str,
    after: str,
    known_names: list[str],
    registry: dict[str, CharacterRegistryEntry],
    last_speaker: CharacterRegistryEntry | None,
) -> tuple[CharacterRegistryEntry | None, str]:
    for name in known_names:
        if _name_has_pre_speech_cue(before, name):
            return registry[name], "pre_speech"
    for name in known_names:
        if _name_has_post_speech_cue(after, name):
            return registry[name], "post_speech"
    for name in known_names:
        if _name_has_voice_cue(before, after, name):
            return registry[name], "voice_cue"
    for name in known_names:
        if _name_is_near_quote(before, after, name):
            return registry[name], "nearby_action"
    if last_speaker is not None and _pronoun_cue_near_quote(before, after):
        return last_speaker, "pronoun_carry"
    return None, "unknown"


def _name_has_pre_speech_cue(text: str, name: str) -> bool:
    idx = text.rfind(name)
    if idx == -1:
        return False
    tail = text[idx + len(name):]
    if any(mark in tail for mark in ("。", "！", "？", "\n", "“", "”", "\"", "」", "』")):
        return False
    return len(tail) <= 18 and any(verb in tail for verb in SPEECH_VERBS)


def _name_has_post_speech_cue(text: str, name: str) -> bool:
    idx = text.find(name)
    if idx == -1 or idx > 12:
        return False
    tail = text[idx + len(name):idx + len(name) + 18]
    return any(verb in tail for verb in SPEECH_VERBS)


def _name_has_voice_cue(before: str, after: str, name: str) -> bool:
    windows = (before[-40:], after[:40])
    for window in windows:
        idx = window.find(name)
        if idx == -1:
            continue
        near = window[max(0, idx - 8):idx + len(name) + 12]
        if any(word in near for word in VOICE_ATTRIBUTION_WORDS):
            return True
    return False


def _name_is_near_quote(before: str, after: str, name: str) -> bool:
    b_idx = before.rfind(name)
    if b_idx != -1:
        tail = before[b_idx + len(name):]
        if (
            len(tail) <= 14
            and not any(mark in tail for mark in ("。", "！", "？", "\n", "“", "”", "\""))
            and _looks_like_action_beat(tail)
        ):
            return True
    a_idx = after.find(name)
    if a_idx != -1 and a_idx <= 8:
        head = after[:a_idx]
        tail = after[a_idx + len(name):a_idx + len(name) + 14]
        if len(head.strip(" \t，。！？、…")) == 0 and _looks_like_action_beat(tail):
            return True
    return False


def _looks_like_action_beat(text: str) -> bool:
    if any(verb in text for verb in SPEECH_VERBS):
        return True
    action_cues = (
        "皱眉",
        "抬头",
        "低头",
        "转身",
        "摇头",
        "点头",
        "沉默",
        "盯",
        "看",
        "笑",
        "冷笑",
        "伸手",
        "按住",
        "握紧",
        "停下",
    )
    if any(cue in text for cue in action_cues):
        return True
    return text.strip() in {"：", ":", "，", ",", "。", ""}


def _pronoun_cue_near_quote(before: str, after: str) -> bool:
    window = before[-8:] + after[:8]
    return any(pronoun in window for pronoun in ("他说", "她说", "他问", "她问", "他道", "她道"))


def _quote_addresses_candidate(quote: str, name: str) -> bool:
    stripped = quote.lstrip()
    aliases = {name}
    if len(name) >= 2:
        aliases.update({f"{name[0]}工", f"{name[0]}师兄", f"{name[0]}师弟"})
    for alias in aliases:
        if stripped.startswith(alias) and (
            len(stripped) == len(alias)
            or stripped[len(alias)] in "，,。！？：:、 "
        ):
            return True
    return False


def _build_anchors(
    scope: str,
    lines: list[AttributedLine],
    *,
    min_lines: int,
) -> list[VoiceAnchorObservation]:
    by_character: dict[str, list[AttributedLine]] = defaultdict(list)
    for line in lines:
        by_character[line.character_id].append(line)
    candidates = {
        character_id: values
        for character_id, values in by_character.items()
        if len(values) >= min_lines
    }
    scores = _distinctiveness_scores(candidates)
    anchors: list[VoiceAnchorObservation] = []
    for character_id, values in sorted(
        candidates.items(),
        key=lambda item: (-len(item[1]), item[1][0].speaker_name),
    ):
        profile = _sentence_profile(values)
        markers = _lexical_markers(values)
        emotions = _emotional_register(values)
        limitations = [
            "report-only observation",
            "not DialogueStyleCard",
            "speaker attribution is heuristic",
        ]
        if len(values) < 4:
            limitations.append("small attributed sample")
        score = scores.get(character_id)
        hits = []
        if score is not None and score < 0.25 and len(candidates) >= 2:
            hits.append("voice_homogeneity_risk")
        anchors.append(
            VoiceAnchorObservation(
                scope=scope,
                character_id=character_id,
                character_name=values[0].speaker_name,
                role_type=values[0].role_type,
                evidence_chapters=sorted(
                    {f"{line.genre} Ch{line.chapter}" for line in values}
                ),
                sample_lines=[
                    VoiceEvidenceLine(
                        genre=line.genre,
                        chapter=line.chapter,
                        speaker_name=line.speaker_name,
                        text=_shorten(line.text, 100),
                        attribution=line.attribution,
                        location=line.location,
                    )
                    for line in values[:8]
                ],
                sentence_length_profile=profile,
                lexical_markers=markers,
                emotional_register=emotions,
                interaction_pattern=_interaction_pattern(values, profile),
                distinctiveness_score=score,
                drift_or_homogeneity_hits=hits,
                limitations=limitations,
            )
        )
    return anchors


def _unknown_summary(
    scope: str,
    all_lines: list[AttributedLine],
    unknown_lines: list[AttributedLine],
) -> UnknownAttributionSummary:
    ratio = round(len(unknown_lines) / max(len(all_lines), 1), 3)
    limitations = ["unattributed dialogue preserved instead of fabricated"]
    if ratio > 0.5:
        limitations.append("unknown attribution dominates this scope")
    return UnknownAttributionSummary(
        scope=scope,
        line_count=len(unknown_lines),
        ratio=ratio,
        sample_lines=[
            VoiceEvidenceLine(
                genre=line.genre,
                chapter=line.chapter,
                speaker_name="unknown",
                text=_shorten(line.text, 100),
                attribution=line.attribution,
                location=line.location,
            )
            for line in unknown_lines[:10]
        ],
        limitations=limitations,
    )


def _sanity_check(
    scope: str,
    chapters: list[LoadedChapter],
    lines: list[AttributedLine],
    annotations: dict[str, AnnotationRecord],
    report_by_version: dict[str, Any],
) -> VoiceAnchorSanityCheck:
    lines_by_version: dict[str, list[AttributedLine]] = defaultdict(list)
    for line in lines:
        lines_by_version[line.version_id].append(line)
    weak = []
    unexplained = []
    for chapter in chapters:
        annotation = annotations.get(chapter.version_id)
        if annotation is None or annotation.annotator != "agent-deep-read":
            continue
        if (
            annotation.scores.overall <= 2
            or annotation.scores.ai_tone <= 2
            or annotation.scores.homogeneity <= 2
        ):
            label = f"{chapter.genre} Ch{chapter.chapter}"
            weak.append(label)
            chapter_lines = lines_by_version.get(chapter.version_id, [])
            report = report_by_version.get(chapter.version_id)
            signal_hits = getattr(report, "hits", []) if report is not None else []
            voice_related = (
                len(chapter_lines) >= 2
                or any(hit.signal_id in {"template_rhetoric_density", "verbatim_sentence_repeat"}
                       for hit in signal_hits)
            )
            if not voice_related:
                unexplained.append(label)
    return VoiceAnchorSanityCheck(
        scope=scope,
        weak_samples=len(weak),
        weak_with_voice_evidence=len(weak) - len(unexplained),
        weak_unexplained=unexplained,
        notes=[
            "weak samples use overall<=2 or ai_tone<=2 or homogeneity<=2",
            "voice evidence means >=2 dialogue lines or adjacent 197/198 dialogue-style risk",
        ],
    )


def _sentence_profile(lines: list[AttributedLine]) -> SentenceLengthProfile:
    sentences = []
    for line in lines:
        sentences.extend(sentence for sentence in split_sentences(line.text) if sentence.strip())
    lengths = [len(sentence) for sentence in sentences] or [0]
    return SentenceLengthProfile(
        quote_count=len(lines),
        sentence_count=len(sentences),
        avg_sentence_chars=round(mean(lengths), 2),
        stdev_sentence_chars=round(pstdev(lengths), 2) if len(lengths) > 1 else 0.0,
        short_sentence_ratio=round(sum(1 for length in lengths if length <= 12) / len(lengths), 3),
        long_sentence_ratio=round(sum(1 for length in lengths if length >= 36) / len(lengths), 3),
    )


def _lexical_markers(lines: list[AttributedLine]) -> list[str]:
    text = "".join(line.text for line in lines)
    counter: Counter[str] = Counter()
    normalized = re.sub(r"[^\u4e00-\u9fff]", "", text)
    for size in (2, 3):
        for idx in range(0, max(0, len(normalized) - size + 1)):
            term = normalized[idx:idx + size]
            if _low_value_term(term):
                continue
            counter[term] += 1
    return [term for term, count in counter.most_common(8) if count >= 2]


def _emotional_register(lines: list[AttributedLine]) -> list[str]:
    text = "".join(line.text for line in lines)
    return [word for word in EMOTION_WORDS if word in text][:8]


def _interaction_pattern(
    lines: list[AttributedLine],
    profile: SentenceLengthProfile,
) -> str:
    text = "".join(line.text for line in lines)
    question_ratio = text.count("？") / max(len(lines), 1)
    exclaim_ratio = text.count("！") / max(len(lines), 1)
    imperative_count = sum(text.count(word) for word in INTERACTION_WORDS)
    if question_ratio >= 0.4:
        return "question-heavy"
    if exclaim_ratio >= 0.3 or imperative_count >= len(lines):
        return "urgent-imperative"
    if profile.avg_sentence_chars <= 14:
        return "terse"
    if profile.avg_sentence_chars >= 32:
        return "expository"
    return "measured"


def _distinctiveness_scores(
    by_character: dict[str, list[AttributedLine]],
) -> dict[str, float | None]:
    if len(by_character) < 2:
        return {character_id: None for character_id in by_character}
    features = {
        character_id: _voice_features(lines)
        for character_id, lines in by_character.items()
    }
    scores: dict[str, float] = {}
    for character_id, own in features.items():
        distances = [
            _feature_distance(own, other)
            for other_id, other in features.items()
            if other_id != character_id
        ]
        scores[character_id] = round(sum(distances) / len(distances), 3)
    return scores


def _voice_features(lines: list[AttributedLine]) -> dict[str, Any]:
    profile = _sentence_profile(lines)
    text = "".join(line.text for line in lines)
    markers = set(_lexical_markers(lines))
    emotions = set(_emotional_register(lines))
    return {
        "avg_len": profile.avg_sentence_chars,
        "question_ratio": text.count("？") / max(len(lines), 1),
        "exclaim_ratio": text.count("！") / max(len(lines), 1),
        "markers": markers,
        "emotions": emotions,
    }


def _feature_distance(a: dict[str, Any], b: dict[str, Any]) -> float:
    len_diff = abs(a["avg_len"] - b["avg_len"]) / max(a["avg_len"], b["avg_len"], 1.0)
    question_diff = abs(a["question_ratio"] - b["question_ratio"])
    exclaim_diff = abs(a["exclaim_ratio"] - b["exclaim_ratio"])
    marker_distance = 1.0 - _jaccard(a["markers"], b["markers"])
    emotion_distance = 1.0 - _jaccard(a["emotions"], b["emotions"])
    return max(0.0, min(1.0, (
        len_diff * 0.35
        + question_diff * 0.15
        + exclaim_diff * 0.15
        + marker_distance * 0.2
        + emotion_distance * 0.15
    )))


def _jaccard(a: set[str], b: set[str]) -> float:
    if not a and not b:
        return 1.0
    return len(a & b) / max(len(a | b), 1)


def _extract_lines_for_scope(
    chapters: list[LoadedChapter],
    registry: dict[str, list[CharacterRegistryEntry]],
) -> list[AttributedLine]:
    lines: list[AttributedLine] = []
    for chapter in chapters:
        lines.extend(extract_dialogue_lines(chapter, registry.get(chapter.genre, [])))
    return lines


def _group_chapters(
    chapters: list[LoadedChapter],
    scope_mode: VoiceScopeMode,
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


def _load_character_registry(
    sample_set_path: Path,
) -> dict[str, list[CharacterRegistryEntry]]:
    try:
        sample_set = json.loads(sample_set_path.read_text(encoding="utf-8"))
    except OSError as exc:
        raise VoiceAnchorError(f"failed to read {sample_set_path}: {exc}") from exc
    registry: dict[str, list[CharacterRegistryEntry]] = {}
    for source in sample_set.get("sources", []):
        if not isinstance(source, dict):
            continue
        genre = str(source.get("genre") or "")
        db_path = Path(str(source.get("db") or ""))
        project_id = str(source.get("project_id") or "")
        if not genre or not db_path.exists() or not project_id:
            registry[genre] = []
            continue
        conn = sqlite3.connect(f"file:{db_path.as_posix()}?mode=ro", uri=True)
        try:
            rows = conn.execute(
                """SELECT character_id, name, role_type
                   FROM characters
                   WHERE project_id = ?
                   ORDER BY LENGTH(name) DESC, name""",
                (project_id,),
            ).fetchall()
        except sqlite3.Error:
            rows = []
        finally:
            conn.close()
        registry[genre] = [
            CharacterRegistryEntry(
                genre=genre,
                character_id=str(row[0]),
                name=str(row[1]),
                role_type=str(row[2] or ""),
            )
            for row in rows
            if row[1] and str(row[1]) not in PRONOUNS
        ]
    return registry


def _load_model(path: Path, model_type: Any) -> Any:
    try:
        raw = json.loads(path.read_text(encoding="utf-8"))
    except OSError as exc:
        raise VoiceAnchorError(f"failed to read {path}: {exc}") from exc
    if not isinstance(raw, dict):
        raise VoiceAnchorError(f"expected JSON object: {path}")
    return model_type.model_validate(raw)


def _low_value_term(term: str) -> bool:
    if len(set(term)) <= 1:
        return True
    if term in LOW_VALUE_TERMS:
        return True
    return term.startswith("的") or term.endswith("的")


def _shorten(text: str, limit: int) -> str:
    collapsed = re.sub(r"\s+", " ", text.strip())
    if len(collapsed) <= limit:
        return collapsed
    return collapsed[:limit - 1] + "…"
