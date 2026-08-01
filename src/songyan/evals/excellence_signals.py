"""Task 197/198 offline excellence signals.

The module is deliberately report-only.  It reads accepted chapter text and
Task 196 annotations, produces structured evidence, and does not touch the
generation workflow, CED, five-gate, segment audit, or T9 hard gates.
"""

from __future__ import annotations

import json
import math
import re
import sqlite3
from collections import Counter, defaultdict
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path
from statistics import mean, pstdev
from typing import Any, Literal

from pydantic import BaseModel, Field

from songyan.evals.excellence_sampling import AnnotationRecord, load_chapter_content
from songyan.utils._helpers import locate_position, split_paragraphs, split_sentences
from songyan.utils.ai_tells import detect_ai_tells

SignalTask = Literal["197", "198"]
Severity = Literal["low", "medium", "high"]

MIN_REPEAT_SENTENCE_LEN = 12
MIN_CROSS_CHAPTER_SENTENCE_LEN = 14


class ExcellenceSignalError(RuntimeError):
    """Raised when Task 197/198 offline signal inputs are invalid."""


class EvidenceItem(BaseModel):
    """Concrete evidence for one report-only signal hit."""

    chapter: int = Field(ge=1)
    location: str
    quote: str
    detail: str = ""


class SignalHit(BaseModel):
    """One report-only excellence signal hit."""

    task: SignalTask
    signal_id: str
    label: str
    severity: Severity = "medium"
    evidence: list[EvidenceItem] = Field(default_factory=list)
    detail: str = ""


class AnnotationSummary(BaseModel):
    """Task 196 annotation projection used for calibration."""

    sample_layer: str
    annotator: str
    scores: dict[str, int]
    disagreement: str | None = None


class Task197Metrics(BaseModel):
    """Per-chapter structure/diversity/tension metrics."""

    scene_function: str
    scene_function_score: float
    beat_signature: str
    tension_average: float
    tension_peak: float
    tension_stdev: float
    dominant_terms: list[str] = Field(default_factory=list)
    segment_function_ratio: float | None = None


class Task198Metrics(BaseModel):
    """Per-chapter AI-tone/rule metrics."""

    repeated_sentence_count: int = 0
    cross_chapter_repetition_count: int = 0
    self_reference_count: int = 0
    engineering_residue_count: int = 0
    setting_patch_count: int = 0
    template_rhetoric_count: int = 0
    legacy_ai_tell_count: int = 0


class ChapterSignalReport(BaseModel):
    """All report-only signals for one sampled chapter."""

    genre: str
    chapter: int = Field(ge=1)
    version_id: str
    segment: int = Field(ge=1)
    annotation: AnnotationSummary | None = None
    task197: Task197Metrics
    task198: Task198Metrics
    hits: list[SignalHit] = Field(default_factory=list)


class CalibrationSummary(BaseModel):
    """Simple directional calibration against Task 196 agent-deep-read records."""

    task: SignalTask
    truth_rule: str
    evaluated: int
    truth_positive: int
    detected_positive: int
    true_positive: int
    false_positive: int
    false_negative: int
    precision: float | None
    recall: float | None
    examples: dict[str, list[str]] = Field(default_factory=dict)


class ExcellenceSignalReport(BaseModel):
    """Top-level Task 197/198 offline report."""

    generated_at: str
    sample_set: str
    annotations: str
    report_only: bool = True
    boundaries: list[str]
    summaries: dict[str, Any]
    calibration: list[CalibrationSummary]
    chapters: list[ChapterSignalReport]


@dataclass(frozen=True)
class LoadedChapter:
    genre: str
    chapter: int
    version_id: str
    segment: int
    content: str


@dataclass(frozen=True)
class SentenceOccurrence:
    genre: str
    chapter: int
    version_id: str
    sentence: str


SCENE_FUNCTION_KEYWORDS: dict[str, tuple[str, ...]] = {
    "combat": (
        "冲",
        "杀",
        "刀",
        "剑",
        "拳",
        "血",
        "爆",
        "撞",
        "敌",
        "战",
        "挡",
        "劈",
    ),
    "dialogue": ("道", "问", "说", "答", "喊", "笑", "沉默", "声音", "开口", "低声"),
    "investigation": ("查", "看", "发现", "线索", "痕迹", "记录", "扫描", "数据", "坐标"),
    "revelation": ("真相", "秘密", "记忆", "传承", "身份", "协议", "核心", "钥匙", "答案"),
    "planning": ("计划", "决定", "安排", "准备", "目标", "路线", "选择", "代价", "方案"),
    "training": ("修炼", "练", "呼吸", "功法", "灵气", "训练", "演算", "校准", "测试"),
    "transition": ("走", "来到", "穿过", "抵达", "离开", "返回", "路上", "夜色", "清晨"),
    "exposition": ("也就是说", "意味着", "换句话说", "原来", "事实上", "因此", "规则", "系统"),
}

TENSION_KEYWORDS: tuple[str, ...] = (
    "死",
    "杀",
    "血",
    "危险",
    "崩",
    "爆",
    "断",
    "痛",
    "敌",
    "冲",
    "警报",
    "倒计时",
    "无法",
    "必须",
    "代价",
    "真相",
    "秘密",
    "背叛",
    "封锁",
    "坠",
)

ENGINEERING_PATTERNS: tuple[tuple[str, str], ...] = (
    (r"(?m)^\s{0,3}#{1,6}\s+\S+", "Markdown heading"),
    (r"```|{{|}}|<[^>\n]{1,40}>", "template/code marker"),
    (r"保护内容|请勿修改|系统提示|占位|TODO|FIXME", "instruction or placeholder"),
    (r"（[^）]{0,20}(?:停顿|镜头|半秒|括号内)[^）]{0,20}）", "stage direction"),
    (r"\b[A-Za-z_]{6,}(?:/[A-Za-z_]{2,})*\b", "ASCII residue"),
)

SELF_REFERENCE_PATTERN = re.compile(
    r"第(?:\d+|[一二三四五六七八九十百零〇两]+)章"
)

PATCH_TERMS: tuple[str, ...] = (
    "也就是说",
    "换句话说",
    "这意味着",
    "事实上",
    "因此",
    "分别",
    "同时",
    "此前",
    "之前",
    "已经",
    "完整",
    "身份",
    "关系",
    "规则",
    "设定",
    "协议",
    "令牌",
    "血脉",
    "系统",
    "节点",
)

TEMPLATE_TERMS: tuple[str, ...] = (
    "不是",
    "而是",
    "仿佛",
    "像是",
    "如同",
    "某种",
    "难以名状",
    "本质上",
    "换句话说",
    "这意味着",
)


def load_task196_inputs(
    sample_set_path: Path,
    annotations_path: Path,
) -> tuple[list[LoadedChapter], dict[str, AnnotationRecord]]:
    """Load Task 196 sampled accepted text and annotations."""
    sample_set = _load_json_object(sample_set_path)
    annotations_raw = _load_json_object(annotations_path)
    sources = sample_set.get("sources")
    samples = sample_set.get("samples")
    if not isinstance(sources, list) or not isinstance(samples, list):
        raise ExcellenceSignalError("Task 196 sample set must contain sources and samples")
    db_by_genre = {
        str(source["genre"]): str(source["db"])
        for source in sources
        if isinstance(source, dict) and "genre" in source and "db" in source
    }
    chapters: list[LoadedChapter] = []
    conns: dict[str, sqlite3.Connection] = {}
    try:
        for sample in samples:
            if not isinstance(sample, dict):
                continue
            genre = str(sample["genre"])
            db_path = db_by_genre.get(genre)
            if not db_path:
                raise ExcellenceSignalError(f"missing DB source for genre={genre}")
            conn = conns.get(genre)
            if conn is None:
                conn = sqlite3.connect(f"file:{Path(db_path).as_posix()}?mode=ro", uri=True)
                conns[genre] = conn
            content = load_chapter_content(conn, str(sample["version_id"]))
            chapters.append(
                LoadedChapter(
                    genre=genre,
                    chapter=int(sample["chapter"]),
                    version_id=str(sample["version_id"]),
                    segment=int(sample["segment"]),
                    content=content,
                )
            )
    finally:
        for conn in conns.values():
            conn.close()

    annotations = {
        str(raw["version_id"]): AnnotationRecord.model_validate(raw)
        for raw in annotations_raw.get("annotations", [])
        if isinstance(raw, dict) and raw.get("version_id")
    }
    return chapters, annotations


def build_excellence_signal_report(
    chapters: list[LoadedChapter],
    annotations: dict[str, AnnotationRecord],
    *,
    sample_set_path: Path,
    annotations_path: Path,
) -> ExcellenceSignalReport:
    """Build Task 197/198 offline report from loaded chapters."""
    cross_sentence_index = _build_cross_sentence_index(chapters)
    segment_ratios = _segment_function_ratios(chapters)
    chapter_reports: list[ChapterSignalReport] = []
    for chapter in sorted(chapters, key=lambda item: (item.genre, item.chapter)):
        annotation = annotations.get(chapter.version_id)
        reports_for_chapter = _analyze_chapter(
            chapter,
            annotation,
            cross_sentence_index,
            segment_ratios,
        )
        chapter_reports.append(reports_for_chapter)

    summaries = _summarize_reports(chapter_reports)
    calibration = [
        _calibrate(chapter_reports, task="197"),
        _calibrate(chapter_reports, task="198"),
    ]
    return ExcellenceSignalReport(
        generated_at=datetime.now(UTC).isoformat(),
        sample_set=sample_set_path.as_posix(),
        annotations=annotations_path.as_posix(),
        boundaries=[
            "report-only / observe-only",
            "does not modify Writer or CreativeDirector prompts",
            "does not enter accept/reject gates",
            "does not change CED, five-gate, segment audit, or T9",
            "Task 196 prelabel is comparison-only; anchor + spotcheck are calibration truth",
        ],
        summaries=summaries,
        calibration=calibration,
        chapters=chapter_reports,
    )


def render_excellence_signal_report(report: ExcellenceSignalReport) -> str:
    """Render Task 197/198 report as Markdown."""
    lines = [
        "# Task 197/198 优秀度信号包第一批离线报告",
        "",
        f"> generated_at: `{report.generated_at}`",
        f"> sample_set: `{report.sample_set}`",
        f"> annotations: `{report.annotations}`",
        "",
        "## 边界",
        "",
    ]
    lines.extend(f"- {item}" for item in report.boundaries)
    lines.extend(["", "## 总览", ""])
    summary_rows = report.summaries.get("by_task", {})
    lines.append("| Task | 章节命中 | hit 总数 | top signals |")
    lines.append("|------|----------|----------|-------------|")
    for task in ("197", "198"):
        summary = summary_rows.get(task, {})
        top = ", ".join(
            f"{item['signal_id']}={item['count']}"
            for item in summary.get("top_signals", [])[:5]
        )
        lines.append(
            f"| {task} | {summary.get('chapters_with_hits', 0)} | "
            f"{summary.get('hit_count', 0)} | {top or '-'} |"
        )

    lines.extend(["", "## 校准摘要（agent-deep-read 24 章）", ""])
    lines.append(
        "| Task | truth rule | evaluated | truth+ | detected+ | TP | FP | FN | "
        "precision | recall |"
    )
    lines.append(
        "|------|------------|-----------|--------|-----------|----|----|----|"
        "-----------|--------|"
    )
    for cal in report.calibration:
        precision = "-" if cal.precision is None else f"{cal.precision:.2f}"
        recall = "-" if cal.recall is None else f"{cal.recall:.2f}"
        lines.append(
            f"| {cal.task} | {cal.truth_rule} | {cal.evaluated} | {cal.truth_positive} | "
            f"{cal.detected_positive} | {cal.true_positive} | {cal.false_positive} | "
            f"{cal.false_negative} | {precision} | {recall} |"
        )

    lines.extend(["", "## 高风险命中样例", ""])
    for task in ("197", "198"):
        hits = [
            (chapter, hit)
            for chapter in report.chapters
            for hit in chapter.hits
            if hit.task == task
        ]
        lines.append(f"### Task {task}")
        if not hits:
            lines.append("")
            lines.append("无命中。")
            lines.append("")
            continue
        for chapter, hit in hits[:12]:
            evidence = hit.evidence[0] if hit.evidence else None
            quote = f"`{_shorten(evidence.quote, 80)}`" if evidence else "-"
            location = evidence.location if evidence else "-"
            lines.append(
                f"- **{chapter.genre} Ch{chapter.chapter}** `{hit.signal_id}` "
                f"({hit.severity})：{hit.detail}；{location} {quote}"
            )
        lines.append("")

    lines.extend(["## 逐章明细", ""])
    lines.append(
        "| genre | chapter | annotation | T197 hits | T198 hits | scene | beat | "
        "tension avg/peak |"
    )
    lines.append("|-------|---------|------------|-----------|-----------|-------|------|------------------|")
    for chapter in report.chapters:
        ann = "-"
        if chapter.annotation:
            scores = chapter.annotation.scores
            ann = (
                f"{chapter.annotation.sample_layer}: "
                f"H{scores.get('homogeneity')}/T{scores.get('tension')}/"
                f"A{scores.get('ai_tone')}/O{scores.get('overall')}"
            )
        t197 = sum(1 for hit in chapter.hits if hit.task == "197")
        t198 = sum(1 for hit in chapter.hits if hit.task == "198")
        lines.append(
            f"| {chapter.genre} | {chapter.chapter} | {ann} | {t197} | {t198} | "
            f"{chapter.task197.scene_function} | `{chapter.task197.beat_signature}` | "
            f"{chapter.task197.tension_average:.2f}/{chapter.task197.tension_peak:.2f} |"
        )

    lines.extend(
        [
            "",
            "## 局限",
            "",
            "- 本报告只覆盖 Task 196 的 xuanhuan + sci-fi 60 章样本，不能外推到全部体裁。",
            "- anchor + spotcheck 共 24 章，只支撑方向性校准，不支撑 hard gate 阈值。",
            "- prelabel 仅用于对照，未作为真值参与 precision / recall 计算。",
            "- 所有信号均为 report-only；任何进入 prompt 或 gate 的尝试必须另立任务并回归。",
        ]
    )
    return "\n".join(lines) + "\n"


def _analyze_chapter(
    chapter: LoadedChapter,
    annotation: AnnotationRecord | None,
    cross_sentence_index: dict[str, list[SentenceOccurrence]],
    segment_ratios: dict[tuple[str, int], tuple[str, float]],
) -> ChapterSignalReport:
    task197, task197_hits = _analyze_task197(chapter, segment_ratios)
    task198, task198_hits = _analyze_task198(chapter, cross_sentence_index)
    annotation_summary = None
    if annotation is not None:
        annotation_summary = AnnotationSummary(
            sample_layer=annotation.sample_layer,
            annotator=annotation.annotator,
            scores=annotation.scores.model_dump(mode="json"),
            disagreement=annotation.disagreement,
        )
    return ChapterSignalReport(
        genre=chapter.genre,
        chapter=chapter.chapter,
        version_id=chapter.version_id,
        segment=chapter.segment,
        annotation=annotation_summary,
        task197=task197,
        task198=task198,
        hits=task197_hits + task198_hits,
    )


def _analyze_task197(
    chapter: LoadedChapter,
    segment_ratios: dict[tuple[str, int], tuple[str, float]],
) -> tuple[Task197Metrics, list[SignalHit]]:
    scene_function, scene_score = _classify_scene_function(chapter.content)
    beat_signature = _beat_signature(chapter.content)
    tension_scores = _paragraph_tension_scores(chapter.content)
    avg = round(mean(tension_scores), 3) if tension_scores else 0.0
    peak = round(max(tension_scores), 3) if tension_scores else 0.0
    stdev = round(pstdev(tension_scores), 3) if len(tension_scores) > 1 else 0.0
    dominant_terms = _dominant_terms(chapter.content)
    segment_function, segment_ratio = segment_ratios.get(
        (chapter.genre, chapter.segment),
        (scene_function, 0.0),
    )
    metrics = Task197Metrics(
        scene_function=scene_function,
        scene_function_score=scene_score,
        beat_signature=beat_signature,
        tension_average=avg,
        tension_peak=peak,
        tension_stdev=stdev,
        dominant_terms=dominant_terms,
        segment_function_ratio=round(segment_ratio, 3),
    )
    hits: list[SignalHit] = []
    if segment_ratio >= 0.75 and segment_function == scene_function:
        hits.append(
            SignalHit(
                task="197",
                signal_id="scene_function_homogeneity",
                label="场景功能同质化",
                severity="medium" if segment_ratio < 0.8 else "high",
                evidence=[
                    EvidenceItem(
                        chapter=chapter.chapter,
                        location="弧段统计",
                        quote=f"{chapter.genre} segment {chapter.segment}",
                        detail=f"{scene_function} ratio={segment_ratio:.2f}",
                    )
                ],
                detail=(
                    f"弧段 {chapter.segment} 内 `{scene_function}` 场景占比 "
                    f"{segment_ratio:.0%}"
                ),
            )
        )
    if _is_repetitive_beat(beat_signature):
        hits.append(
            SignalHit(
                task="197",
                signal_id="beat_rhythm_repetition",
                label="桥段节奏重复",
                severity="medium",
                evidence=[
                    EvidenceItem(
                        chapter=chapter.chapter,
                        location="chapter beat signature",
                        quote=beat_signature,
                        detail="四段 beat 中重复功能过多",
                    )
                ],
                detail=f"beat signature `{beat_signature}` 重复度偏高",
            )
        )
    if avg <= 0.18 and peak <= 1.35 and stdev <= 0.25:
        hits.append(
            SignalHit(
                task="197",
                signal_id="tension_flatline",
                label="张力曲线平直",
                severity="high",
                evidence=[
                    EvidenceItem(
                        chapter=chapter.chapter,
                        location="paragraph tension",
                        quote=f"avg={avg:.2f}, peak={peak:.2f}, stdev={stdev:.2f}",
                        detail="low average + low peak + low variance",
                    )
                ],
                detail="段落张力均值、峰值与波动均偏低",
            )
        )
    if len(dominant_terms) >= 3 and _repeated_term_density(chapter.content, dominant_terms) >= 0.04:
        hits.append(
            SignalHit(
                task="197",
                signal_id="motif_reuse_density",
                label="意象/冲突词复用密度高",
                severity="low",
                evidence=[
                    EvidenceItem(
                        chapter=chapter.chapter,
                        location="chapter lexical motifs",
                        quote=", ".join(dominant_terms[:5]),
                        detail="dominant terms repeated unusually often",
                    )
                ],
                detail=f"高频核心词：{', '.join(dominant_terms[:5])}",
            )
        )
    return metrics, hits


def _analyze_task198(
    chapter: LoadedChapter,
    cross_sentence_index: dict[str, list[SentenceOccurrence]],
) -> tuple[Task198Metrics, list[SignalHit]]:
    hits: list[SignalHit] = []
    repeated_hits = _detect_repeated_paragraphs(chapter) + _detect_repeated_sentences(chapter)
    hits.extend(repeated_hits)
    cross_hits = _detect_cross_chapter_repetition(chapter, cross_sentence_index)
    hits.extend(cross_hits)
    self_ref_hits = _detect_self_reference(chapter)
    hits.extend(self_ref_hits)
    residue_hits = _detect_engineering_residue(chapter)
    hits.extend(residue_hits)
    patch_hits = _detect_setting_patch_segments(chapter)
    hits.extend(patch_hits)
    template_hits = _detect_template_rhetoric(chapter)
    hits.extend(template_hits)
    legacy_tells = detect_ai_tells(chapter.content)
    if len(legacy_tells) < 2:
        legacy_tells = []
    for item in legacy_tells[:2]:
        hits.append(
            SignalHit(
                task="198",
                signal_id="legacy_ai_tell",
                label="既有 AI 腔词面命中",
                severity="low",
                evidence=[
                    EvidenceItem(
                        chapter=chapter.chapter,
                        location=item.location,
                        quote=item.matched_text,
                        detail=item.pattern,
                    )
                ],
                detail=item.pattern,
            )
        )

    metrics = Task198Metrics(
        repeated_sentence_count=len(repeated_hits),
        cross_chapter_repetition_count=len(cross_hits),
        self_reference_count=len(self_ref_hits),
        engineering_residue_count=len(residue_hits),
        setting_patch_count=len(patch_hits),
        template_rhetoric_count=len(template_hits),
        legacy_ai_tell_count=len(legacy_tells),
    )
    return metrics, hits


def _detect_repeated_sentences(chapter: LoadedChapter) -> list[SignalHit]:
    grouped: dict[str, list[str]] = defaultdict(list)
    for sentence in split_sentences(chapter.content):
        normalized = _normalize_text(sentence)
        if len(normalized) >= MIN_REPEAT_SENTENCE_LEN:
            grouped[normalized].append(sentence.strip())
    hits: list[SignalHit] = []
    for sentences in grouped.values():
        if len(sentences) < 3:
            continue
        quote = sentences[0]
        hits.append(
            SignalHit(
                task="198",
                signal_id="verbatim_sentence_repeat",
                label="逐字句子复读",
                severity="high" if len(sentences) >= 3 else "medium",
                evidence=[
                    EvidenceItem(
                        chapter=chapter.chapter,
                        location=locate_position(chapter.content, chapter.content.find(quote)),
                        quote=quote,
                        detail=f"same sentence repeated {len(sentences)} times",
                    )
                ],
                detail=f"同一句式逐字重复 {len(sentences)} 次",
            )
        )
    return hits[:5]


def _detect_repeated_paragraphs(chapter: LoadedChapter) -> list[SignalHit]:
    grouped: dict[str, list[str]] = defaultdict(list)
    for paragraph in split_paragraphs(chapter.content):
        normalized = _normalize_text(paragraph)
        if len(normalized) >= 40:
            grouped[normalized].append(paragraph.strip())
    hits: list[SignalHit] = []
    for paragraphs in grouped.values():
        if len(paragraphs) < 2:
            continue
        quote = paragraphs[0]
        hits.append(
            SignalHit(
                task="198",
                signal_id="verbatim_paragraph_repeat",
                label="逐字段落复读",
                severity="high",
                evidence=[
                    EvidenceItem(
                        chapter=chapter.chapter,
                        location=locate_position(chapter.content, chapter.content.find(quote)),
                        quote=_shorten(quote, 120),
                        detail=f"same paragraph repeated {len(paragraphs)} times",
                    )
                ],
                detail=f"同一长段落逐字重复 {len(paragraphs)} 次",
            )
        )
    return hits[:5]


def _detect_cross_chapter_repetition(
    chapter: LoadedChapter,
    cross_sentence_index: dict[str, list[SentenceOccurrence]],
) -> list[SignalHit]:
    hits: list[SignalHit] = []
    seen: set[str] = set()
    for sentence in split_sentences(chapter.content):
        normalized = _normalize_text(sentence)
        if normalized in seen or len(normalized) < MIN_CROSS_CHAPTER_SENTENCE_LEN:
            continue
        seen.add(normalized)
        occurrences = [
            occurrence
            for occurrence in cross_sentence_index.get(normalized, [])
            if occurrence.version_id != chapter.version_id and occurrence.genre == chapter.genre
        ]
        if not occurrences:
            continue
        hit = SignalHit(
            task="198",
            signal_id="cross_chapter_verbatim_repeat",
            label="跨章逐字复读",
            severity="medium",
            evidence=[
                EvidenceItem(
                    chapter=chapter.chapter,
                    location=locate_position(chapter.content, chapter.content.find(sentence)),
                    quote=sentence.strip(),
                    detail=(
                        "also appears in "
                        + ", ".join(f"Ch{o.chapter}" for o in occurrences[:3])
                    ),
                )
            ],
            detail=f"同体裁样本中跨章复用句子，另见 {len(occurrences)} 处",
        )
        hits.append(hit)
    return hits[:4]


def _detect_self_reference(chapter: LoadedChapter) -> list[SignalHit]:
    hits: list[SignalHit] = []
    for match in SELF_REFERENCE_PATTERN.finditer(chapter.content):
        start = max(0, match.start() - 20)
        end = min(len(chapter.content), match.end() + 24)
        quote = chapter.content[start:end].strip()
        hits.append(
            SignalHit(
                task="198",
                signal_id="chapter_self_reference",
                label="章节号自指泄漏",
                severity="high",
                evidence=[
                    EvidenceItem(
                        chapter=chapter.chapter,
                        location=locate_position(chapter.content, match.start()),
                        quote=quote,
                        detail="chapter number appears inside accepted prose",
                    )
                ],
                detail=f"正文出现 `{match.group()}`，疑似用章节号作记忆索引",
            )
        )
    return hits[:5]


def _detect_engineering_residue(chapter: LoadedChapter) -> list[SignalHit]:
    hits: list[SignalHit] = []
    for pattern, label in ENGINEERING_PATTERNS:
        for match in re.finditer(pattern, chapter.content):
            hits.append(
                SignalHit(
                    task="198",
                    signal_id="engineering_residue",
                    label="工程残留 / 未渲染标记",
                    severity="high",
                    evidence=[
                        EvidenceItem(
                            chapter=chapter.chapter,
                            location=locate_position(chapter.content, match.start()),
                            quote=match.group().strip(),
                            detail=label,
                        )
                    ],
                    detail=label,
                )
            )
    return hits[:8]


def _detect_setting_patch_segments(chapter: LoadedChapter) -> list[SignalHit]:
    hits: list[SignalHit] = []
    for paragraph in split_paragraphs(chapter.content):
        if len(paragraph) < 90:
            continue
        count = sum(paragraph.count(term) for term in PATCH_TERMS)
        punctuation_load = paragraph.count("；") + paragraph.count("、") + paragraph.count("：")
        if count >= 5 and punctuation_load >= 2:
            hits.append(
                SignalHit(
                    task="198",
                    signal_id="setting_patch_segment",
                    label="设定补丁段 / 说明文重述",
                    severity="medium",
                    evidence=[
                        EvidenceItem(
                            chapter=chapter.chapter,
                            location=locate_position(
                                chapter.content, chapter.content.find(paragraph)
                            ),
                            quote=_shorten(paragraph, 120),
                            detail=f"patch_terms={count}, separators={punctuation_load}",
                        )
                    ],
                    detail="段落解释性连接词与设定词密度较高",
                )
            )
    return hits[:4]


def _detect_template_rhetoric(chapter: LoadedChapter) -> list[SignalHit]:
    counts = {term: chapter.content.count(term) for term in TEMPLATE_TERMS}
    heavy = {term: count for term, count in counts.items() if count >= 10}
    hits: list[SignalHit] = []
    if heavy:
        term, count = sorted(heavy.items(), key=lambda item: (-item[1], item[0]))[0]
        idx = chapter.content.find(term)
        hits.append(
            SignalHit(
                task="198",
                signal_id="template_rhetoric_density",
                label="模板修辞 / 说明文腔密度高",
                severity="low" if count < 14 else "medium",
                evidence=[
                    EvidenceItem(
                        chapter=chapter.chapter,
                        location=locate_position(chapter.content, idx),
                        quote=term,
                        detail=f"{term} count={count}",
                    )
                ],
                detail=f"`{term}` 等模板连接词密度偏高",
            )
        )
    negation_pairs = len(re.findall(r"不是[^。！？]{0,30}而是", chapter.content))
    if negation_pairs >= 3:
        match = re.search(r"不是[^。！？]{0,30}而是", chapter.content)
        assert match is not None
        hits.append(
            SignalHit(
                task="198",
                signal_id="not_but_template",
                label="否定转折模板复用",
                severity="medium",
                evidence=[
                    EvidenceItem(
                        chapter=chapter.chapter,
                        location=locate_position(chapter.content, match.start()),
                        quote=match.group(),
                        detail=f"not-but count={negation_pairs}",
                    )
                ],
                detail="`不是...而是...` 模板复用过多",
            )
        )
    return hits


def _segment_function_ratios(
    chapters: list[LoadedChapter],
) -> dict[tuple[str, int], tuple[str, float]]:
    bucket: dict[tuple[str, int], list[str]] = defaultdict(list)
    for chapter in chapters:
        function, _score = _classify_scene_function(chapter.content)
        bucket[(chapter.genre, chapter.segment)].append(function)
    out: dict[tuple[str, int], tuple[str, float]] = {}
    for key, functions in bucket.items():
        counter = Counter(functions)
        top, count = counter.most_common(1)[0]
        out[key] = (top, count / len(functions))
    return out


def _classify_scene_function(text: str) -> tuple[str, float]:
    scores: dict[str, int] = {}
    for function, keywords in SCENE_FUNCTION_KEYWORDS.items():
        scores[function] = sum(text.count(keyword) for keyword in keywords)
    top, score = max(scores.items(), key=lambda item: (item[1], item[0]))
    total = sum(scores.values()) or 1
    return top, round(score / total, 3)


def _beat_signature(text: str) -> str:
    paragraphs = split_paragraphs(text)
    if not paragraphs:
        return "empty"
    groups = _chunk(paragraphs, 4)
    letters = []
    for group in groups:
        function, _score = _classify_scene_function("\n".join(group))
        letters.append(function[:1].upper())
    return "-".join(letters)


def _is_repetitive_beat(signature: str) -> bool:
    letters = [part for part in signature.split("-") if part]
    if len(letters) < 3:
        return False
    counter = Counter(letters)
    return counter.most_common(1)[0][1] >= max(3, math.ceil(len(letters) * 0.75))


def _paragraph_tension_scores(text: str) -> list[float]:
    scores: list[float] = []
    for paragraph in split_paragraphs(text):
        if not paragraph:
            continue
        score = 0.0
        score += sum(paragraph.count(keyword) for keyword in TENSION_KEYWORDS) * 0.35
        score += paragraph.count("！") * 0.25
        score += paragraph.count("？") * 0.15
        score += min(len(paragraph) / 220, 1.0) * 0.3
        scores.append(round(score, 3))
    return scores


def _dominant_terms(text: str) -> list[str]:
    normalized = re.sub(r"[^\u4e00-\u9fff]", "", text)
    counter: Counter[str] = Counter()
    for size in (2, 3, 4):
        for idx in range(0, max(0, len(normalized) - size + 1)):
            term = normalized[idx : idx + size]
            if _is_low_value_term(term):
                continue
            counter[term] += 1
    return [term for term, count in counter.most_common(8) if count >= 5]


def _repeated_term_density(text: str, terms: list[str]) -> float:
    if not text:
        return 0.0
    total = sum(text.count(term) for term in terms)
    return total / max(len(text), 1)


def _build_cross_sentence_index(
    chapters: list[LoadedChapter],
) -> dict[str, list[SentenceOccurrence]]:
    index: dict[str, list[SentenceOccurrence]] = defaultdict(list)
    for chapter in chapters:
        seen: set[str] = set()
        for sentence in split_sentences(chapter.content):
            normalized = _normalize_text(sentence)
            if len(normalized) < MIN_CROSS_CHAPTER_SENTENCE_LEN or normalized in seen:
                continue
            seen.add(normalized)
            index[normalized].append(
                SentenceOccurrence(
                    genre=chapter.genre,
                    chapter=chapter.chapter,
                    version_id=chapter.version_id,
                    sentence=sentence.strip(),
                )
            )
    return {key: value for key, value in index.items() if len(value) > 1}


def _summarize_reports(reports: list[ChapterSignalReport]) -> dict[str, Any]:
    by_task: dict[str, dict[str, Any]] = {}
    for task in ("197", "198"):
        hits = [hit for report in reports for hit in report.hits if hit.task == task]
        chapters = {
            (report.genre, report.chapter)
            for report in reports
            if any(hit.task == task for hit in report.hits)
        }
        counter = Counter(hit.signal_id for hit in hits)
        by_task[task] = {
            "chapters_with_hits": len(chapters),
            "hit_count": len(hits),
            "top_signals": [
                {"signal_id": signal_id, "count": count}
                for signal_id, count in counter.most_common()
            ],
        }
    return {
        "sample_count": len(reports),
        "by_task": by_task,
        "by_genre": {
            genre: {
                "chapters": sum(1 for report in reports if report.genre == genre),
                "task197_hits": sum(
                    1 for report in reports for hit in report.hits
                    if report.genre == genre and hit.task == "197"
                ),
                "task198_hits": sum(
                    1 for report in reports for hit in report.hits
                    if report.genre == genre and hit.task == "198"
                ),
            }
            for genre in sorted({report.genre for report in reports})
        },
    }


def _calibrate(reports: list[ChapterSignalReport], *, task: SignalTask) -> CalibrationSummary:
    evaluated: list[ChapterSignalReport] = [
        report
        for report in reports
        if report.annotation is not None and report.annotation.annotator == "agent-deep-read"
    ]
    truth_rule = (
        "homogeneity<=2 or tension<=2 or overall<=2"
        if task == "197"
        else "ai_tone<=2 or overall<=2"
    )
    truth_positive = detected_positive = true_positive = false_positive = false_negative = 0
    examples: dict[str, list[str]] = {
        "true_positive": [],
        "false_positive": [],
        "false_negative": [],
    }
    for report in evaluated:
        scores = report.annotation.scores if report.annotation else {}
        truth = (
            scores.get("homogeneity", 5) <= 2
            or scores.get("tension", 5) <= 2
            or scores.get("overall", 5) <= 2
            if task == "197"
            else scores.get("ai_tone", 5) <= 2 or scores.get("overall", 5) <= 2
        )
        detected = any(hit.task == task for hit in report.hits)
        if truth:
            truth_positive += 1
        if detected:
            detected_positive += 1
        label = f"{report.genre} Ch{report.chapter}"
        if truth and detected:
            true_positive += 1
            examples["true_positive"].append(label)
        elif not truth and detected:
            false_positive += 1
            examples["false_positive"].append(label)
        elif truth and not detected:
            false_negative += 1
            examples["false_negative"].append(label)
    precision = (
        round(true_positive / detected_positive, 3) if detected_positive else None
    )
    recall = round(true_positive / truth_positive, 3) if truth_positive else None
    return CalibrationSummary(
        task=task,
        truth_rule=truth_rule,
        evaluated=len(evaluated),
        truth_positive=truth_positive,
        detected_positive=detected_positive,
        true_positive=true_positive,
        false_positive=false_positive,
        false_negative=false_negative,
        precision=precision,
        recall=recall,
        examples={key: value[:8] for key, value in examples.items()},
    )


def _load_json_object(path: Path) -> dict[str, Any]:
    try:
        raw = path.read_text(encoding="utf-8")
    except OSError as exc:
        raise ExcellenceSignalError(f"failed to read {path}: {exc}") from exc
    data = json.loads(raw)
    if not isinstance(data, dict):
        raise ExcellenceSignalError(f"expected JSON object: {path}")
    return data


def _chunk(items: list[str], n: int) -> list[list[str]]:
    if n <= 0:
        return [items]
    size = max(1, math.ceil(len(items) / n))
    return [items[idx : idx + size] for idx in range(0, len(items), size)]


def _normalize_text(text: str) -> str:
    return re.sub(r"[^\u4e00-\u9fffA-Za-z0-9]", "", text).lower()


def _is_low_value_term(term: str) -> bool:
    if len(set(term)) <= 1:
        return True
    low_value = {
        "他们",
        "自己",
        "这个",
        "那个",
        "一种",
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
        "他们",
        "林渊",
        "方舟",
        "陆沉",
        "灵渊",
        "指挥",
        "挥官",
        "指挥官",
    }
    return term in low_value


def _shorten(text: str, limit: int) -> str:
    collapsed = re.sub(r"\s+", " ", text.strip())
    if len(collapsed) <= limit:
        return collapsed
    return collapsed[: limit - 1] + "…"
