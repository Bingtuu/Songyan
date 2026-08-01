"""Task 199 style card extraction tests."""

from __future__ import annotations

from pathlib import Path

from songyan.evals.excellence_sampling import AnnotationRecord
from songyan.evals.excellence_signals import (
    AnnotationSummary,
    ChapterSignalReport,
    EvidenceItem,
    ExcellenceSignalReport,
    LoadedChapter,
    SignalHit,
    Task197Metrics,
    Task198Metrics,
)
from songyan.evals.style_card_extraction import (
    build_style_card_report,
    render_style_card_report,
)


def _annotation(
    *,
    genre: str,
    chapter: int,
    version_id: str,
    overall: int,
    ai_tone: int = 4,
    homogeneity: int = 4,
    tension: int = 4,
) -> AnnotationRecord:
    return AnnotationRecord(
        genre=genre,
        chapter=chapter,
        version_id=version_id,
        sample_layer="anchor",
        annotator="agent-deep-read",
        scores={
            "homogeneity": homogeneity,
            "tension": tension,
            "ai_tone": ai_tone,
            "overall": overall,
        },
    )


def _chapter_report(
    chapter: LoadedChapter,
    *,
    annotation: AnnotationRecord | None = None,
    hits: list[SignalHit] | None = None,
    scene: str = "dialogue",
    tension_average: float = 0.2,
    tension_peak: float = 1.8,
    tension_stdev: float = 0.3,
) -> ChapterSignalReport:
    ann_summary = None
    if annotation is not None:
        ann_summary = AnnotationSummary(
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
        annotation=ann_summary,
        task197=Task197Metrics(
            scene_function=scene,
            scene_function_score=0.6,
            beat_signature="D-D-D-D",
            tension_average=tension_average,
            tension_peak=tension_peak,
            tension_stdev=tension_stdev,
            dominant_terms=["方舟", "协议"],
            segment_function_ratio=0.5,
        ),
        task198=Task198Metrics(engineering_residue_count=len(hits or [])),
        hits=hits or [],
    )


def _signal(signal_id: str, label: str = "工程残留") -> SignalHit:
    return SignalHit(
        task="198",
        signal_id=signal_id,
        label=label,
        severity="high",
        evidence=[
            EvidenceItem(chapter=2, location="第1段", quote="TODO", detail="test")
        ],
        detail="test hit",
    )


def _excellence_report(reports: list[ChapterSignalReport]) -> ExcellenceSignalReport:
    return ExcellenceSignalReport(
        generated_at="2026-08-01T00:00:00+00:00",
        sample_set="sample.json",
        annotations="annotations.json",
        boundaries=["report-only"],
        summaries={},
        calibration=[],
        chapters=reports,
    )


def test_builds_report_only_cards_with_expected_schema() -> None:
    good = LoadedChapter(
        genre="scifi",
        chapter=1,
        version_id="v-good",
        segment=1,
        content="林渊看着方舟核心。“说具体。”他低声说。警报在远处响起。",
    )
    bad = LoadedChapter(
        genre="scifi",
        chapter=2,
        version_id="v-bad",
        segment=1,
        content="# 场景一\n林渊在第21章看见过协议。协议不是答案，而是锁。",
    )
    good_ann = _annotation(genre="scifi", chapter=1, version_id="v-good", overall=5)
    bad_ann = _annotation(
        genre="scifi",
        chapter=2,
        version_id="v-bad",
        overall=2,
        ai_tone=1,
    )
    report = build_style_card_report(
        [good, bad],
        {"v-good": good_ann, "v-bad": bad_ann},
        _excellence_report(
            [
                _chapter_report(good, annotation=good_ann),
                _chapter_report(
                    bad,
                    annotation=bad_ann,
                    hits=[_signal("engineering_residue")],
                ),
            ]
        ),
        sample_set_path=Path("sample.json"),
        annotations_path=Path("annotations.json"),
        excellence_report_path=Path("excellence.json"),
    )

    card = report.cards[0]
    assert report.report_only is True
    assert card.report_only is True
    assert "not a prompt constraint" in report.boundaries[1]
    assert card.narrative_voice.dominant_person == "third"
    assert card.dialogue_style.dialogue_line_count >= 1
    assert card.anti_patterns[0].signal_id == "engineering_residue"


def test_scope_by_genre_creates_independent_cards() -> None:
    chapters = [
        LoadedChapter("scifi", 1, "v-s", 1, "方舟核心亮起。“走。”"),
        LoadedChapter("xuanhuan", 1, "v-x", 1, "灵渊符文亮起。“走。”"),
    ]
    annotations = {
        chapter.version_id: _annotation(
            genre=chapter.genre,
            chapter=chapter.chapter,
            version_id=chapter.version_id,
            overall=4,
        )
        for chapter in chapters
    }
    report = build_style_card_report(
        chapters,
        annotations,
        _excellence_report(
            [
                _chapter_report(chapter, annotation=annotations[chapter.version_id])
                for chapter in chapters
            ]
        ),
        sample_set_path=Path("sample.json"),
        annotations_path=Path("annotations.json"),
        excellence_report_path=Path("excellence.json"),
        scope_mode="by-genre",
    )

    assert [card.scope for card in report.cards] == ["genre:scifi", "genre:xuanhuan"]


def test_sanity_check_explains_weak_samples_with_anti_patterns() -> None:
    weak = LoadedChapter(
        genre="scifi",
        chapter=84,
        version_id="v-weak",
        segment=4,
        content="林渊在第21章看见过协议。协议不是答案，而是锁。",
    )
    ann = _annotation(
        genre="scifi",
        chapter=84,
        version_id="v-weak",
        overall=2,
        ai_tone=1,
    )
    report = build_style_card_report(
        [weak],
        {"v-weak": ann},
        _excellence_report(
            [_chapter_report(weak, annotation=ann, hits=[_signal("chapter_self_reference")])]
        ),
        sample_set_path=Path("sample.json"),
        annotations_path=Path("annotations.json"),
        excellence_report_path=Path("excellence.json"),
    )

    sanity = report.sanity_checks[0]
    assert sanity.weak_count == 1
    assert sanity.weak_with_anti_patterns == 1
    assert sanity.weak_unexplained == []


def test_markdown_declares_observation_not_constraint() -> None:
    chapter = LoadedChapter(
        genre="scifi",
        chapter=1,
        version_id="v-1",
        segment=1,
        content="方舟核心亮起。“走。”",
    )
    ann = _annotation(genre="scifi", chapter=1, version_id="v-1", overall=4)
    report = build_style_card_report(
        [chapter],
        {"v-1": ann},
        _excellence_report([_chapter_report(chapter, annotation=ann)]),
        sample_set_path=Path("sample.json"),
        annotations_path=Path("annotations.json"),
        excellence_report_path=Path("excellence.json"),
    )
    markdown = render_style_card_report(report)

    assert "style card is an observed profile, not a prompt constraint" in markdown
    assert "不得默认注入 Writer / CreativeDirector prompt" in markdown
