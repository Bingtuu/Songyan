"""Task 200 character voice anchor extraction tests."""

from __future__ import annotations

from pathlib import Path

from songyan.evals.excellence_sampling import AnnotationRecord
from songyan.evals.excellence_signals import (
    ChapterSignalReport,
    ExcellenceSignalReport,
    SignalHit,
    Task197Metrics,
    Task198Metrics,
)
from songyan.evals.style_card_extraction import StyleCardReport
from songyan.evals.voice_anchor_extraction import (
    CharacterRegistryEntry,
    LoadedChapter,
    build_voice_anchor_report,
    extract_dialogue_lines,
    render_voice_anchor_report,
)


def _registry() -> list[CharacterRegistryEntry]:
    return [
        CharacterRegistryEntry(
            genre="scifi",
            character_id="char-linyuan",
            name="林渊",
            role_type="protagonist",
        ),
        CharacterRegistryEntry(
            genre="scifi",
            character_id="char-chenwei",
            name="陈薇",
            role_type="supporting",
        ),
    ]


def _annotation(
    *,
    chapter: int,
    version_id: str,
    overall: int,
    ai_tone: int = 4,
    homogeneity: int = 4,
) -> AnnotationRecord:
    return AnnotationRecord(
        genre="scifi",
        chapter=chapter,
        version_id=version_id,
        sample_layer="anchor",
        annotator="agent-deep-read",
        scores={
            "homogeneity": homogeneity,
            "tension": 4,
            "ai_tone": ai_tone,
            "overall": overall,
        },
    )


def _chapter_report(
    chapter: LoadedChapter,
    hits: list[SignalHit] | None = None,
) -> ChapterSignalReport:
    return ChapterSignalReport(
        genre=chapter.genre,
        chapter=chapter.chapter,
        version_id=chapter.version_id,
        segment=chapter.segment,
        task197=Task197Metrics(
            scene_function="dialogue",
            scene_function_score=0.5,
            beat_signature="D-D-D-D",
            tension_average=0.2,
            tension_peak=1.2,
            tension_stdev=0.2,
            dominant_terms=[],
            segment_function_ratio=0.5,
        ),
        task198=Task198Metrics(),
        hits=hits or [],
    )


def _excellence_report(chapters: list[LoadedChapter]) -> ExcellenceSignalReport:
    return ExcellenceSignalReport(
        generated_at="2026-08-01T00:00:00+00:00",
        sample_set="sample.json",
        annotations="annotations.json",
        boundaries=["report-only"],
        summaries={},
        calibration=[],
        chapters=[_chapter_report(chapter) for chapter in chapters],
    )


def _style_report() -> StyleCardReport:
    return StyleCardReport(
        generated_at="2026-08-01T00:00:00+00:00",
        sample_set="sample.json",
        annotations="annotations.json",
        excellence_report="excellence.json",
        boundaries=["report-only"],
        cards=[],
        sanity_checks=[],
    )


def test_extract_dialogue_lines_keeps_unknown_when_unattributed() -> None:
    chapter = LoadedChapter(
        genre="scifi",
        chapter=1,
        version_id="v-1",
        segment=1,
        content='林渊说：“走。”\n“别急。”陈薇说。\n“没有名字。”',
    )

    lines = extract_dialogue_lines(chapter, _registry())

    assert [line.speaker_name for line in lines] == ["林渊", "陈薇", "unknown"]
    assert lines[0].attribution == "pre_speech"
    assert lines[1].attribution == "post_speech"
    assert lines[2].attribution == "unknown"


def test_build_report_creates_voice_anchor_schema() -> None:
    chapter = LoadedChapter(
        genre="scifi",
        chapter=2,
        version_id="v-2",
        segment=1,
        content=(
            '林渊说：“走，别停。”\n'
            '林渊说：“快走，门要关了！”\n'
            '陈薇说：“等一下，坐标还没锁定。”\n'
            '陈薇说：“你先别动，我来处理。”'
        ),
    )
    report = build_voice_anchor_report(
        [chapter],
        {"v-2": _annotation(chapter=2, version_id="v-2", overall=4)},
        _excellence_report([chapter]),
        _style_report(),
        {"scifi": _registry()},
        sample_set_path=Path("sample.json"),
        annotations_path=Path("annotations.json"),
        excellence_report_path=Path("excellence.json"),
        style_card_report_path=Path("style.json"),
    )

    anchors = {anchor.character_name: anchor for anchor in report.anchors}
    assert set(anchors) == {"林渊", "陈薇"}
    assert anchors["林渊"].sentence_length_profile.quote_count == 2
    assert anchors["陈薇"].distinctiveness_score is not None
    assert report.report_only is True


def test_weak_sample_sanity_uses_voice_evidence() -> None:
    chapter = LoadedChapter(
        genre="scifi",
        chapter=84,
        version_id="v-weak",
        segment=4,
        content='林渊说：“协议不是答案。”\n陈薇说：“协议不是答案。”',
    )
    report = build_voice_anchor_report(
        [chapter],
        {
            "v-weak": _annotation(
                chapter=84,
                version_id="v-weak",
                overall=2,
                ai_tone=1,
                homogeneity=1,
            )
        },
        _excellence_report([chapter]),
        _style_report(),
        {"scifi": _registry()},
        sample_set_path=Path("sample.json"),
        annotations_path=Path("annotations.json"),
        excellence_report_path=Path("excellence.json"),
        style_card_report_path=Path("style.json"),
    )

    sanity = report.sanity_checks[0]
    assert sanity.weak_samples == 1
    assert sanity.weak_with_voice_evidence == 1
    assert sanity.weak_unexplained == []


def test_markdown_declares_not_dialogue_style_card() -> None:
    chapter = LoadedChapter(
        genre="scifi",
        chapter=1,
        version_id="v-1",
        segment=1,
        content='林渊说：“走。”',
    )
    report = build_voice_anchor_report(
        [chapter],
        {"v-1": _annotation(chapter=1, version_id="v-1", overall=4)},
        _excellence_report([chapter]),
        _style_report(),
        {"scifi": _registry()},
        sample_set_path=Path("sample.json"),
        annotations_path=Path("annotations.json"),
        excellence_report_path=Path("excellence.json"),
        style_card_report_path=Path("style.json"),
        min_lines=1,
    )

    markdown = render_voice_anchor_report(report)

    assert "not DialogueStyleCard runtime data" in markdown
    assert "不写回角色档案" in markdown
