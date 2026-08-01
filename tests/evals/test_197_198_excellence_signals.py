"""Task 197/198 offline excellence signal tests."""

from __future__ import annotations

from pathlib import Path

from songyan.evals.excellence_sampling import AnnotationRecord
from songyan.evals.excellence_signals import (
    LoadedChapter,
    build_excellence_signal_report,
    render_excellence_signal_report,
)


def _annotation(
    *,
    genre: str = "scifi",
    chapter: int = 1,
    version_id: str = "v-1",
    homogeneity: int = 3,
    tension: int = 3,
    ai_tone: int = 3,
    overall: int = 3,
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


def _report(chapters: list[LoadedChapter], annotations: list[AnnotationRecord]):
    return build_excellence_signal_report(
        chapters,
        {item.version_id: item for item in annotations},
        sample_set_path=Path("tasks/196-excellence-sample-set.json"),
        annotations_path=Path("tasks/196-excellence-annotations.json"),
    )


def test_task198_detects_generation_accident_patterns() -> None:
    repeated = "这个协议会在下一章再次开启。"
    content = "\n".join(
        [
            "# 场景一",
            "TODO：修复这段。",
            "林渊在第21章看到过这个协议的设计蓝图。",
            repeated + repeated + repeated,
        ]
    )
    chapter = LoadedChapter(
        genre="scifi",
        chapter=84,
        version_id="v-bad",
        segment=4,
        content=content,
    )
    report = _report(
        [chapter],
        [_annotation(chapter=84, version_id="v-bad", ai_tone=1, overall=2)],
    )

    hit_ids = {hit.signal_id for hit in report.chapters[0].hits if hit.task == "198"}
    assert "engineering_residue" in hit_ids
    assert "chapter_self_reference" in hit_ids
    assert "verbatim_sentence_repeat" in hit_ids


def test_task197_detects_repetitive_low_tension_structure() -> None:
    content = "\n".join(
        [
            "他说这件事还要再等等。",
            "她低声回答这件事还要再等等。",
            "他说这件事还要再等等。",
            "她低声回答这件事还要再等等。",
        ]
    )
    chapter = LoadedChapter(
        genre="scifi",
        chapter=32,
        version_id="v-flat",
        segment=2,
        content=content,
    )
    report = _report(
        [chapter],
        [_annotation(chapter=32, version_id="v-flat", homogeneity=1, tension=2, overall=2)],
    )

    hit_ids = {hit.signal_id for hit in report.chapters[0].hits if hit.task == "197"}
    assert "beat_rhythm_repetition" in hit_ids
    assert "tension_flatline" in hit_ids


def test_calibration_uses_agent_deep_read_truth_only() -> None:
    bad = LoadedChapter(
        genre="scifi",
        chapter=84,
        version_id="v-bad",
        segment=4,
        content="林渊在第84章提到旧协议。林渊在第84章提到旧协议。林渊在第84章提到旧协议。",
    )
    good = LoadedChapter(
        genre="xuanhuan",
        chapter=1,
        version_id="v-good",
        segment=1,
        content="铁匠铺里火光明亮，少年把铁胚放入水槽，白汽升起。",
    )
    report = _report(
        [bad, good],
        [
            _annotation(chapter=84, version_id="v-bad", ai_tone=1, overall=2),
            _annotation(
                genre="xuanhuan",
                chapter=1,
                version_id="v-good",
                homogeneity=4,
                tension=5,
                ai_tone=4,
                overall=5,
            ),
        ],
    )

    task198 = next(item for item in report.calibration if item.task == "198")
    assert task198.evaluated == 2
    assert task198.truth_positive == 1
    assert task198.true_positive == 1


def test_markdown_report_declares_report_only_boundary() -> None:
    chapter = LoadedChapter(
        genre="scifi",
        chapter=1,
        version_id="v-1",
        segment=1,
        content="正常章节正文，没有明显事故。",
    )
    report = _report([chapter], [_annotation(version_id="v-1")])
    markdown = render_excellence_signal_report(report)

    assert "report-only / observe-only" in markdown
    assert "does not change CED, five-gate, segment audit, or T9" in markdown
