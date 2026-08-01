"""Task 202 offline readability and perplexity feasibility spike.

This module is report-only.  It consumes Task 196 accepted samples and Task
197-201 report artifacts, computes deterministic readability proxies, and
records why true perplexity is deferred without a stable local language model.
"""

from __future__ import annotations

import json
import re
from collections import Counter
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
from songyan.evals.judge_bias_analysis import JudgeBiasReport
from songyan.evals.style_card_extraction import StyleCardReport
from songyan.evals.voice_anchor_extraction import VoiceAnchorReport
from songyan.utils._helpers import split_paragraphs, split_sentences

AdoptionDecision = Literal["adopt", "report-only", "reject", "defer"]
SignalId = Literal[
    "sentence_readability",
    "paragraph_readability",
    "dialogue_ratio",
    "punctuation_rhythm",
    "lexical_repetition_proxy",
    "perplexity_feasibility",
]

QUOTE_RE = re.compile(r"[“「『\"]([^”」』\"]{1,240})[”」』\"]")
CJK_RE = re.compile(r"[\u4e00-\u9fff]")
LOW_INFO_TERMS = (
    "不是",
    "而是",
    "已经",
    "只是",
    "依旧",
    "仿佛",
    "像是",
    "某种",
    "这个",
    "那个",
    "什么",
    "怎么",
    "为什么",
    "意味着",
    "换句话说",
    "也就是说",
)
LOW_VALUE_NGRAMS = {
    "一个",
    "这个",
    "那个",
    "他们",
    "我们",
    "你们",
    "自己",
    "没有",
    "已经",
    "只是",
}


class ReadabilitySpikeError(RuntimeError):
    """Raised when Task 202 inputs cannot be loaded."""


class SentenceReadabilityMetrics(BaseModel):
    """Sentence-level readability proxies."""

    sentence_count: int
    avg_sentence_chars: float
    stdev_sentence_chars: float
    short_sentence_ratio: float
    long_sentence_ratio: float
    risk_flags: list[str] = Field(default_factory=list)


class ParagraphReadabilityMetrics(BaseModel):
    """Paragraph-level readability proxies."""

    paragraph_count: int
    avg_paragraph_chars: float
    stdev_paragraph_chars: float
    overlong_paragraph_ratio: float
    max_short_paragraph_run: int
    risk_flags: list[str] = Field(default_factory=list)


class DialogueRatioMetrics(BaseModel):
    """Dialogue ratio and sparsity proxies."""

    quote_count: int
    dialogue_char_ratio: float
    avg_quote_chars: float
    risk_flags: list[str] = Field(default_factory=list)


class PunctuationRhythmMetrics(BaseModel):
    """Punctuation rhythm density per 1k Chinese characters."""

    question_per_1k: float
    exclamation_per_1k: float
    ellipsis_per_1k: float
    dash_per_1k: float
    risk_flags: list[str] = Field(default_factory=list)


class LexicalRepetitionMetrics(BaseModel):
    """Lightweight lexical repetition proxies."""

    unique_bigram_ratio: float
    top_bigram: str
    top_bigram_density: float
    low_info_term_density_per_1k: float
    risk_flags: list[str] = Field(default_factory=list)


class ChapterReadabilityReport(BaseModel):
    """All Task 202 report-only metrics for one sampled chapter."""

    genre: str
    chapter: int = Field(ge=1)
    version_id: str
    segment: int = Field(ge=1)
    truth_scores: dict[str, int] | None = None
    risk_flags: list[str] = Field(default_factory=list)
    sentence_readability: SentenceReadabilityMetrics
    paragraph_readability: ParagraphReadabilityMetrics
    dialogue_ratio: DialogueRatioMetrics
    punctuation_rhythm: PunctuationRhythmMetrics
    lexical_repetition_proxy: LexicalRepetitionMetrics


class SignalDecision(BaseModel):
    """Decision for one candidate signal."""

    signal_id: SignalId
    definition: str
    decision: AdoptionDecision
    sample_summary: dict[str, Any]
    evidence: list[str] = Field(default_factory=list)
    limitations: list[str] = Field(default_factory=list)
    task203_recommendation: str


class PerplexityFeasibility(BaseModel):
    """True perplexity feasibility assessment."""

    decision: AdoptionDecision
    reproducible_without_external_model: bool
    requires_model_weights: bool
    requires_tokenizer_policy: bool
    risks: list[str] = Field(default_factory=list)
    recommendation: str


class ReadabilitySanityCheck(BaseModel):
    """Directional sanity check against Task 196 deep-read labels."""

    truth_records: int
    weak_samples: int
    weak_with_proxy_hit: int
    weak_unexplained: list[str] = Field(default_factory=list)
    strong_samples: int
    strong_with_proxy_hit: int
    notes: list[str] = Field(default_factory=list)


class ReadabilityFeasibilityReport(BaseModel):
    """Top-level Task 202 report."""

    generated_at: str
    sample_set: str
    annotations: str
    excellence_report: str
    style_card_report: str
    voice_anchor_report: str
    judge_bias_report: str
    report_only: bool = True
    boundaries: list[str]
    summaries: dict[str, Any]
    decisions: list[SignalDecision]
    perplexity_feasibility: PerplexityFeasibility
    sanity_check: ReadabilitySanityCheck
    chapters: list[ChapterReadabilityReport]


def load_readability_inputs(
    sample_set_path: Path,
    annotations_path: Path,
    excellence_report_path: Path,
    style_card_report_path: Path,
    voice_anchor_report_path: Path,
    judge_bias_report_path: Path,
) -> tuple[
    list[LoadedChapter],
    list[AnnotationRecord],
    ExcellenceSignalReport,
    StyleCardReport,
    VoiceAnchorReport,
    JudgeBiasReport,
]:
    """Load Task 196-201 artifacts for Task 202."""
    try:
        chapters, _annotations_by_version = load_task196_inputs(
            sample_set_path, annotations_path
        )
    except Exception as exc:
        raise ReadabilitySpikeError(f"failed to load Task 196 inputs: {exc}") from exc
    return (
        chapters,
        _load_annotations(annotations_path),
        _load_model(excellence_report_path, ExcellenceSignalReport),
        _load_model(style_card_report_path, StyleCardReport),
        _load_model(voice_anchor_report_path, VoiceAnchorReport),
        _load_model(judge_bias_report_path, JudgeBiasReport),
    )


def build_readability_feasibility_report(
    chapters: list[LoadedChapter],
    annotations: list[AnnotationRecord],
    excellence_report: ExcellenceSignalReport,
    style_card_report: StyleCardReport,
    voice_anchor_report: VoiceAnchorReport,
    judge_bias_report: JudgeBiasReport,
    *,
    sample_set_path: Path,
    annotations_path: Path,
    excellence_report_path: Path,
    style_card_report_path: Path,
    voice_anchor_report_path: Path,
    judge_bias_report_path: Path,
) -> ReadabilityFeasibilityReport:
    """Build Task 202 readability / perplexity feasibility report."""
    truth = _truth_records(annotations)
    chapter_reports = [
        analyze_chapter_readability(chapter, truth.get(chapter.version_id))
        for chapter in sorted(chapters, key=lambda item: (item.genre, item.chapter))
    ]
    sanity = _sanity_check(chapter_reports, truth)
    perplexity = _perplexity_feasibility()
    decisions = _signal_decisions(
        chapter_reports,
        sanity,
        excellence_report,
        style_card_report,
        voice_anchor_report,
        judge_bias_report,
        perplexity,
    )
    return ReadabilityFeasibilityReport(
        generated_at=datetime.now(UTC).isoformat(),
        sample_set=sample_set_path.as_posix(),
        annotations=annotations_path.as_posix(),
        excellence_report=excellence_report_path.as_posix(),
        style_card_report=style_card_report_path.as_posix(),
        voice_anchor_report=voice_anchor_report_path.as_posix(),
        judge_bias_report=judge_bias_report_path.as_posix(),
        boundaries=[
            "report-only / observe-only",
            "does not call LLMs",
            "does not download or require external language-model weights",
            "does not modify Writer or CreativeDirector prompts",
            "does not enter accept/reject gates",
            "does not change CED, five-gate, segment audit, or T9",
        ],
        summaries=_summaries(chapter_reports, decisions, sanity),
        decisions=decisions,
        perplexity_feasibility=perplexity,
        sanity_check=sanity,
        chapters=chapter_reports,
    )


def analyze_chapter_readability(
    chapter: LoadedChapter,
    truth: AnnotationRecord | None = None,
) -> ChapterReadabilityReport:
    """Analyze one accepted chapter with deterministic readability proxies."""
    sentence = _sentence_metrics(chapter.content)
    paragraph = _paragraph_metrics(chapter.content)
    dialogue = _dialogue_metrics(chapter.content)
    punctuation = _punctuation_metrics(chapter.content)
    lexical = _lexical_metrics(chapter.content)
    flags = sorted(
        set(
            sentence.risk_flags
            + paragraph.risk_flags
            + dialogue.risk_flags
            + punctuation.risk_flags
            + lexical.risk_flags
        )
    )
    return ChapterReadabilityReport(
        genre=chapter.genre,
        chapter=chapter.chapter,
        version_id=chapter.version_id,
        segment=chapter.segment,
        truth_scores=truth.scores.model_dump(mode="json") if truth else None,
        risk_flags=flags,
        sentence_readability=sentence,
        paragraph_readability=paragraph,
        dialogue_ratio=dialogue,
        punctuation_rhythm=punctuation,
        lexical_repetition_proxy=lexical,
    )


def render_readability_feasibility_report(
    report: ReadabilityFeasibilityReport,
) -> str:
    """Render Task 202 report as Markdown."""
    lines = [
        "# Task 202 Perplexity / 可读性可行性 Spike 报告",
        "",
        f"> generated_at: `{report.generated_at}`",
        f"> sample_set: `{report.sample_set}`",
        f"> annotations: `{report.annotations}`",
        f"> excellence_report: `{report.excellence_report}`",
        f"> style_card_report: `{report.style_card_report}`",
        f"> voice_anchor_report: `{report.voice_anchor_report}`",
        f"> judge_bias_report: `{report.judge_bias_report}`",
        "",
        "## 边界",
        "",
    ]
    lines.extend(f"- {item}" for item in report.boundaries)
    lines.extend(["", "## 总览", ""])
    for key, value in report.summaries.items():
        if key == "by_signal":
            continue
        lines.append(f"- {key}: `{value}`")

    lines.extend(["", "## 候选信号结论", ""])
    lines.append("| signal | decision | hit chapters | weak coverage | recommendation |")
    lines.append("|--------|----------|-------------:|---------------|----------------|")
    by_signal = report.summaries.get("by_signal", {})
    for decision in report.decisions:
        stats = by_signal.get(decision.signal_id, {})
        weak = stats.get("weak_with_signal")
        weak_total = stats.get("weak_samples")
        weak_text = "-" if weak is None else f"{weak}/{weak_total}"
        lines.append(
            f"| {decision.signal_id} | `{decision.decision}` | "
            f"{stats.get('chapters_with_signal', '-')} | {weak_text} | "
            f"{decision.task203_recommendation} |"
        )

    lines.extend(["", "## Perplexity Feasibility", ""])
    lines.extend(
        [
            f"- decision: `{report.perplexity_feasibility.decision}`",
            "- reproducible_without_external_model: "
            f"`{report.perplexity_feasibility.reproducible_without_external_model}`",
            f"- requires_model_weights: `{report.perplexity_feasibility.requires_model_weights}`",
            "- requires_tokenizer_policy: "
            f"`{report.perplexity_feasibility.requires_tokenizer_policy}`",
            f"- recommendation: {report.perplexity_feasibility.recommendation}",
            "- risks:",
        ]
    )
    lines.extend(f"  - {item}" for item in report.perplexity_feasibility.risks)

    lines.extend(["", "## Sanity Check", ""])
    sanity = report.sanity_check
    lines.extend(
        [
            f"- truth_records: `{sanity.truth_records}`",
            f"- weak_samples: `{sanity.weak_samples}`",
            f"- weak_with_proxy_hit: `{sanity.weak_with_proxy_hit}`",
            f"- strong_samples: `{sanity.strong_samples}`",
            f"- strong_with_proxy_hit: `{sanity.strong_with_proxy_hit}`",
            f"- weak_unexplained: {', '.join(sanity.weak_unexplained) or '-'}",
        ]
    )

    lines.extend(["", "## 决策明细", ""])
    for decision in report.decisions:
        lines.extend(
            [
                f"### {decision.signal_id}",
                "",
                f"- decision: `{decision.decision}`",
                f"- definition: {decision.definition}",
                "- sample_summary:",
            ]
        )
        for key, value in decision.sample_summary.items():
            lines.append(f"  - {key}: `{value}`")
        if decision.evidence:
            lines.append("- evidence:")
            lines.extend(f"  - {item}" for item in decision.evidence[:8])
        if decision.limitations:
            lines.append("- limitations:")
            lines.extend(f"  - {item}" for item in decision.limitations)
        lines.append(f"- Task 203: {decision.task203_recommendation}")
        lines.append("")

    lines.extend(["## 逐章明细", ""])
    lines.append(
        "| genre | chapter | flags | sent avg/long | para avg/overlong | "
        "dialogue | punct q/!/…/-- | lexical top/density |"
    )
    lines.append(
        "|-------|---------|-------|---------------|-------------------|----------|"
        "-----------------|---------------------|"
    )
    for chapter in report.chapters:
        punct = chapter.punctuation_rhythm
        lexical = chapter.lexical_repetition_proxy
        lines.append(
            f"| {chapter.genre} | {chapter.chapter} | "
            f"{', '.join(chapter.risk_flags) or '-'} | "
            f"{chapter.sentence_readability.avg_sentence_chars:.1f}/"
            f"{chapter.sentence_readability.long_sentence_ratio:.2f} | "
            f"{chapter.paragraph_readability.avg_paragraph_chars:.1f}/"
            f"{chapter.paragraph_readability.overlong_paragraph_ratio:.2f} | "
            f"{chapter.dialogue_ratio.dialogue_char_ratio:.2f} | "
            f"{punct.question_per_1k:.1f}/{punct.exclamation_per_1k:.1f}/"
            f"{punct.ellipsis_per_1k:.1f}/{punct.dash_per_1k:.1f} | "
            f"{lexical.top_bigram}/{lexical.top_bigram_density:.3f} |"
        )

    lines.extend(
        [
            "",
            "## 局限",
            "",
            "- 只覆盖 Task 196 的 xuanhuan + sci-fi 60 章样本。",
            "- 可读性 proxy 只能解释局部读感风险，不能替代人工质量判断。",
            "- 真实 perplexity 未执行；没有稳定本地中文长篇 LM 与 tokenizer 政策。",
            "- 所有结论均为 Task 203 report-only 输入，不进入 hard gate。",
        ]
    )
    return "\n".join(lines) + "\n"


def _sentence_metrics(text: str) -> SentenceReadabilityMetrics:
    sentences = [sentence.strip() for sentence in split_sentences(text) if sentence.strip()]
    lengths = [_cjk_len(sentence) for sentence in sentences if _cjk_len(sentence) > 0]
    if not lengths:
        lengths = [0]
    short_ratio = _ratio(sum(1 for length in lengths if length <= 12), len(lengths))
    long_ratio = _ratio(sum(1 for length in lengths if length >= 42), len(lengths))
    avg = round(mean(lengths), 3)
    stdev = round(pstdev(lengths), 3) if len(lengths) > 1 else 0.0
    flags: list[str] = []
    if avg >= 34 or long_ratio >= 0.22:
        flags.append("long_sentence_load")
    if short_ratio >= 0.62 and len(lengths) >= 8:
        flags.append("fragmented_sentence_load")
    return SentenceReadabilityMetrics(
        sentence_count=len(sentences),
        avg_sentence_chars=avg,
        stdev_sentence_chars=stdev,
        short_sentence_ratio=short_ratio,
        long_sentence_ratio=long_ratio,
        risk_flags=flags,
    )


def _paragraph_metrics(text: str) -> ParagraphReadabilityMetrics:
    paragraphs = split_paragraphs(text)
    lengths = [_cjk_len(paragraph) for paragraph in paragraphs if _cjk_len(paragraph) > 0]
    if not lengths:
        lengths = [0]
    overlong_ratio = _ratio(sum(1 for length in lengths if length >= 220), len(lengths))
    avg = round(mean(lengths), 3)
    stdev = round(pstdev(lengths), 3) if len(lengths) > 1 else 0.0
    short_run = _max_short_paragraph_run(lengths)
    flags: list[str] = []
    if avg >= 170 or overlong_ratio >= 0.18:
        flags.append("dense_paragraph_load")
    if short_run >= 5:
        flags.append("short_paragraph_staccato")
    return ParagraphReadabilityMetrics(
        paragraph_count=len(paragraphs),
        avg_paragraph_chars=avg,
        stdev_paragraph_chars=stdev,
        overlong_paragraph_ratio=overlong_ratio,
        max_short_paragraph_run=short_run,
        risk_flags=flags,
    )


def _dialogue_metrics(text: str) -> DialogueRatioMetrics:
    quotes = [match.group(1).strip() for match in QUOTE_RE.finditer(text)]
    total = max(_cjk_len(text), 1)
    quote_chars = sum(_cjk_len(quote) for quote in quotes)
    ratio = round(quote_chars / total, 3)
    avg_quote = round(mean([_cjk_len(quote) for quote in quotes]), 3) if quotes else 0.0
    flags: list[str] = []
    if ratio <= 0.035:
        flags.append("dialogue_sparse")
    if ratio >= 0.42:
        flags.append("dialogue_heavy")
    return DialogueRatioMetrics(
        quote_count=len(quotes),
        dialogue_char_ratio=ratio,
        avg_quote_chars=avg_quote,
        risk_flags=flags,
    )


def _punctuation_metrics(text: str) -> PunctuationRhythmMetrics:
    total = max(_cjk_len(text), 1)
    question = _per_1k(text.count("？") + text.count("?"), total)
    exclamation = _per_1k(text.count("！") + text.count("!"), total)
    ellipsis = _per_1k(text.count("……") + text.count("...") + text.count("…"), total)
    dash = _per_1k(text.count("——") + text.count("--"), total)
    flags: list[str] = []
    if exclamation >= 9:
        flags.append("exclamation_pressure")
    if question >= 8:
        flags.append("question_pressure")
    if ellipsis >= 8:
        flags.append("ellipsis_pressure")
    if dash >= 7:
        flags.append("dash_pressure")
    return PunctuationRhythmMetrics(
        question_per_1k=question,
        exclamation_per_1k=exclamation,
        ellipsis_per_1k=ellipsis,
        dash_per_1k=dash,
        risk_flags=flags,
    )


def _lexical_metrics(text: str) -> LexicalRepetitionMetrics:
    normalized = "".join(CJK_RE.findall(text))
    bigrams = [
        normalized[idx : idx + 2]
        for idx in range(max(0, len(normalized) - 1))
        if not _is_low_value_ngram(normalized[idx : idx + 2])
    ]
    counter = Counter(bigrams)
    if counter:
        top_bigram, top_count = counter.most_common(1)[0]
        unique_ratio = round(len(counter) / len(bigrams), 3)
        top_density = round(top_count / max(len(bigrams), 1), 4)
    else:
        top_bigram = ""
        unique_ratio = 0.0
        top_density = 0.0
    low_info_count = sum(text.count(term) for term in LOW_INFO_TERMS)
    low_info_density = _per_1k(low_info_count, max(_cjk_len(text), 1))
    flags: list[str] = []
    if unique_ratio <= 0.56 and len(bigrams) >= 200:
        flags.append("low_lexical_variety")
    if top_density >= 0.015 and len(bigrams) >= 200:
        flags.append("top_bigram_repetition")
    if low_info_density >= 18:
        flags.append("low_info_term_density")
    return LexicalRepetitionMetrics(
        unique_bigram_ratio=unique_ratio,
        top_bigram=top_bigram,
        top_bigram_density=top_density,
        low_info_term_density_per_1k=low_info_density,
        risk_flags=flags,
    )


def _signal_decisions(
    chapters: list[ChapterReadabilityReport],
    sanity: ReadabilitySanityCheck,
    excellence_report: ExcellenceSignalReport,
    style_card_report: StyleCardReport,
    voice_anchor_report: VoiceAnchorReport,
    judge_bias_report: JudgeBiasReport,
    perplexity: PerplexityFeasibility,
) -> list[SignalDecision]:
    by_signal = _signal_stats(chapters, sanity)
    return [
        SignalDecision(
            signal_id="sentence_readability",
            definition="句长均值、长句比例与碎片短句比例。",
            decision="report-only",
            sample_summary=by_signal["sentence_readability"],
            evidence=_examples(chapters, {"long_sentence_load", "fragmented_sentence_load"}),
            limitations=[
                "长句或短句密集是风格风险，不等于质量缺陷。",
                "中文网文动作段常天然短句密集。",
            ],
            task203_recommendation="展示为章节读感 proxy，不参与排序或 hard gate。",
        ),
        SignalDecision(
            signal_id="paragraph_readability",
            definition="段长均值、超长段比例与连续短段节奏。",
            decision="report-only",
            sample_summary=by_signal["paragraph_readability"],
            evidence=_examples(chapters, {"dense_paragraph_load", "short_paragraph_staccato"}),
            limitations=[
                "段落长度受体裁、战斗密度和对话排版影响大。",
                "需要结合 Task 197 tension / scene function 解释。",
            ],
            task203_recommendation="展示为辅助读感维度，并链接 Task 197 张力/场景证据。",
        ),
        SignalDecision(
            signal_id="dialogue_ratio",
            definition="对白字符占比、对白行数和对白稀疏 / 过密风险。",
            decision="report-only",
            sample_summary=by_signal["dialogue_ratio"],
            evidence=_examples(chapters, {"dialogue_sparse", "dialogue_heavy"}),
            limitations=[
                "对白稀疏不等于坏章；揭示章和动作章可能需要少对白。",
                "角色声纹质量仍以 Task 200 为主。",
            ],
            task203_recommendation="展示为 dialogue context，和 Task 200 voice anchors 并列。",
        ),
        SignalDecision(
            signal_id="punctuation_rhythm",
            definition="问号、叹号、省略号、破折号每千字密度。",
            decision="report-only",
            sample_summary=by_signal["punctuation_rhythm"],
            evidence=_examples(
                chapters,
                {"question_pressure", "exclamation_pressure", "ellipsis_pressure", "dash_pressure"},
            ),
            limitations=[
                "标点密度对中文网文节奏有解释力，但误报率高。",
                "省略号和破折号在悬念章中是正常修辞。",
            ],
            task203_recommendation="仅作为节奏解释项，默认低权重展示。",
        ),
        SignalDecision(
            signal_id="lexical_repetition_proxy",
            definition="唯一 bigram 比例、高频 bigram 密度与低信息词密度。",
            decision="report-only",
            sample_summary=by_signal["lexical_repetition_proxy"],
            evidence=_examples(
                chapters,
                {"low_lexical_variety", "top_bigram_repetition", "low_info_term_density"},
            ),
            limitations=[
                "轻量 ngram 不能理解设定专有名词的必要重复。",
                "与 Task 197/198 重复类信号有重叠，不能重复计分。",
            ],
            task203_recommendation="作为 Task 197/198 的补充证据，不单独评分。",
        ),
        SignalDecision(
            signal_id="perplexity_feasibility",
            definition="真实 LM perplexity 的可复现性、依赖、成本和中文适配风险。",
            decision=perplexity.decision,
            sample_summary={
                "requires_model_weights": perplexity.requires_model_weights,
                "requires_tokenizer_policy": perplexity.requires_tokenizer_policy,
                "reproducible_without_external_model": (
                    perplexity.reproducible_without_external_model
                ),
                "upstream_reports_consumed": _upstream_summary(
                    excellence_report,
                    style_card_report,
                    voice_anchor_report,
                    judge_bias_report,
                ),
            },
            evidence=perplexity.risks,
            limitations=[
                "本轮不下载模型、不联网、不调用 LLM。",
                "PPL 对中文长篇网文和专名密度存在强 tokenizer 偏差。",
            ],
            task203_recommendation=perplexity.recommendation,
        ),
    ]


def _signal_stats(
    chapters: list[ChapterReadabilityReport],
    sanity: ReadabilitySanityCheck,
) -> dict[str, dict[str, Any]]:
    weak_versions = {
        chapter.version_id
        for chapter in chapters
        if chapter.truth_scores and _is_weak_truth(chapter.truth_scores)
    }
    stats: dict[str, dict[str, Any]] = {}
    mapping = {
        "sentence_readability": {"long_sentence_load", "fragmented_sentence_load"},
        "paragraph_readability": {"dense_paragraph_load", "short_paragraph_staccato"},
        "dialogue_ratio": {"dialogue_sparse", "dialogue_heavy"},
        "punctuation_rhythm": {
            "question_pressure",
            "exclamation_pressure",
            "ellipsis_pressure",
            "dash_pressure",
        },
        "lexical_repetition_proxy": {
            "low_lexical_variety",
            "top_bigram_repetition",
            "low_info_term_density",
        },
    }
    for signal_id, flags in mapping.items():
        hit_versions = {
            chapter.version_id
            for chapter in chapters
            if flags & set(chapter.risk_flags)
        }
        stats[signal_id] = {
            "chapters_with_signal": len(hit_versions),
            "sample_chapters": len(chapters),
            "weak_samples": sanity.weak_samples,
            "weak_with_signal": len(hit_versions & weak_versions),
            "decision_basis": "directional proxy over Task 196 sample",
        }
    return stats


def _perplexity_feasibility() -> PerplexityFeasibility:
    return PerplexityFeasibility(
        decision="defer",
        reproducible_without_external_model=False,
        requires_model_weights=True,
        requires_tokenizer_policy=True,
        risks=[
            "No project-local Chinese language model weights are versioned in the repo.",
            "Downloading a model would make the spike non-reproducible in offline CI.",
            "Tokenizer choice changes PPL materially for Chinese webnovel names "
            "and invented terms.",
            "PPL can reward generic fluent prose and punish genre-specific proper nouns.",
            "Compute cost is not bounded without a fixed local model and batch policy.",
        ],
        recommendation=(
            "Defer true perplexity to a later offline experiment with pinned local "
            "model weights, tokenizer policy, and cost budget; use readability proxies "
            "as report-only Task 203 context for V10."
        ),
    )


def _sanity_check(
    chapters: list[ChapterReadabilityReport],
    truth: dict[str, AnnotationRecord],
) -> ReadabilitySanityCheck:
    weak_unexplained: list[str] = []
    weak = 0
    weak_hit = 0
    strong = 0
    strong_hit = 0
    for chapter in chapters:
        record = truth.get(chapter.version_id)
        if record is None:
            continue
        label = f"{chapter.genre} Ch{chapter.chapter}"
        has_hit = bool(chapter.risk_flags)
        if _is_weak_truth(record.scores.model_dump(mode="json")):
            weak += 1
            if has_hit:
                weak_hit += 1
            else:
                weak_unexplained.append(label)
        if record.scores.overall >= 4:
            strong += 1
            if has_hit:
                strong_hit += 1
    return ReadabilitySanityCheck(
        truth_records=len(truth),
        weak_samples=weak,
        weak_with_proxy_hit=weak_hit,
        weak_unexplained=weak_unexplained,
        strong_samples=strong,
        strong_with_proxy_hit=strong_hit,
        notes=[
            "weak truth: overall<=2 or ai_tone<=2 or homogeneity<=2 or tension<=2",
            "proxy hit means any Task 202 readability risk flag",
            "strong hits are expected false positives and keep signals report-only",
        ],
    )


def _summaries(
    chapters: list[ChapterReadabilityReport],
    decisions: list[SignalDecision],
    sanity: ReadabilitySanityCheck,
) -> dict[str, Any]:
    flag_counter: Counter[str] = Counter()
    for chapter in chapters:
        flag_counter.update(chapter.risk_flags)
    by_signal = {decision.signal_id: decision.sample_summary for decision in decisions}
    return {
        "sample_chapters": len(chapters),
        "chapters_with_any_proxy_hit": sum(1 for chapter in chapters if chapter.risk_flags),
        "weak_proxy_coverage": f"{sanity.weak_with_proxy_hit}/{sanity.weak_samples}",
        "strong_proxy_false_positive_pressure": (
            f"{sanity.strong_with_proxy_hit}/{sanity.strong_samples}"
        ),
        "top_flags": [
            {"flag": flag, "count": count}
            for flag, count in flag_counter.most_common(8)
        ],
        "by_signal": by_signal,
    }


def _upstream_summary(
    excellence_report: ExcellenceSignalReport,
    style_card_report: StyleCardReport,
    voice_anchor_report: VoiceAnchorReport,
    judge_bias_report: JudgeBiasReport,
) -> dict[str, Any]:
    return {
        "task197198_chapters": len(excellence_report.chapters),
        "style_cards": len(style_card_report.cards),
        "voice_anchors": len(voice_anchor_report.anchors),
        "judge_supported_biases": judge_bias_report.summary.get("supported_biases"),
    }


def _examples(
    chapters: list[ChapterReadabilityReport],
    flags: set[str],
    limit: int = 8,
) -> list[str]:
    examples: list[str] = []
    for chapter in chapters:
        matched = sorted(flags & set(chapter.risk_flags))
        if not matched:
            continue
        examples.append(f"{chapter.genre} Ch{chapter.chapter}: {', '.join(matched)}")
        if len(examples) >= limit:
            break
    return examples


def _truth_records(annotations: list[AnnotationRecord]) -> dict[str, AnnotationRecord]:
    return {
        record.version_id: record
        for record in annotations
        if record.annotator == "agent-deep-read"
        and record.sample_layer in {"anchor", "spotcheck"}
    }


def _is_weak_truth(scores: dict[str, int]) -> bool:
    return (
        int(scores.get("overall", 5)) <= 2
        or int(scores.get("ai_tone", 5)) <= 2
        or int(scores.get("homogeneity", 5)) <= 2
        or int(scores.get("tension", 5)) <= 2
    )


def _cjk_len(text: str) -> int:
    return len(CJK_RE.findall(text))


def _ratio(numerator: int, denominator: int) -> float:
    return round(numerator / denominator, 3) if denominator else 0.0


def _per_1k(count: int, denominator_chars: int) -> float:
    return round(count * 1000 / max(denominator_chars, 1), 3)


def _max_short_paragraph_run(lengths: list[int]) -> int:
    best = 0
    current = 0
    for length in lengths:
        if length <= 35:
            current += 1
            best = max(best, current)
        else:
            current = 0
    return best


def _is_low_value_ngram(value: str) -> bool:
    if len(value) != 2:
        return True
    if value in LOW_VALUE_NGRAMS:
        return True
    return value[0] == value[1] or value.endswith("的")


def _load_annotations(path: Path) -> list[AnnotationRecord]:
    try:
        raw = json.loads(path.read_text(encoding="utf-8"))
    except OSError as exc:
        raise ReadabilitySpikeError(f"failed to read {path}: {exc}") from exc
    if not isinstance(raw, dict) or not isinstance(raw.get("annotations"), list):
        raise ReadabilitySpikeError(f"expected annotations list: {path}")
    return [
        AnnotationRecord.model_validate(item)
        for item in raw["annotations"]
        if isinstance(item, dict)
    ]


def _load_model(path: Path, model_type: Any) -> Any:
    try:
        raw = json.loads(path.read_text(encoding="utf-8"))
    except OSError as exc:
        raise ReadabilitySpikeError(f"failed to read {path}: {exc}") from exc
    if not isinstance(raw, dict):
        raise ReadabilitySpikeError(f"expected JSON object: {path}")
    return model_type.model_validate(raw)
