"""Task 202 readability / perplexity feasibility tests."""

from __future__ import annotations

from pathlib import Path

from songyan.evals.excellence_sampling import AnnotationRecord
from songyan.evals.excellence_signals import ExcellenceSignalReport, LoadedChapter
from songyan.evals.judge_bias_analysis import JudgeBiasReport
from songyan.evals.readability_feasibility import (
    analyze_chapter_readability,
    build_readability_feasibility_report,
    render_readability_feasibility_report,
)
from songyan.evals.style_card_extraction import StyleCardReport
from songyan.evals.voice_anchor_extraction import VoiceAnchorReport


def _annotation(
    *,
    version_id: str,
    overall: int,
    ai_tone: int = 4,
    homogeneity: int = 4,
    tension: int = 4,
) -> AnnotationRecord:
    return AnnotationRecord(
        genre="scifi",
        chapter=1,
        version_id=version_id,
        sample_layer="spotcheck",
        annotator="agent-deep-read",
        scores={
            "homogeneity": homogeneity,
            "tension": tension,
            "ai_tone": ai_tone,
            "overall": overall,
        },
    )


def _excellence_report() -> ExcellenceSignalReport:
    return ExcellenceSignalReport(
        generated_at="2026-08-01T00:00:00+00:00",
        sample_set="sample.json",
        annotations="annotations.json",
        boundaries=["report-only"],
        summaries={},
        calibration=[],
        chapters=[],
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


def _voice_report() -> VoiceAnchorReport:
    return VoiceAnchorReport(
        generated_at="2026-08-01T00:00:00+00:00",
        sample_set="sample.json",
        annotations="annotations.json",
        excellence_report="excellence.json",
        style_card_report="style.json",
        boundaries=["report-only"],
        anchors=[],
        unknown_attribution=[],
        sanity_checks=[],
    )


def _judge_report() -> JudgeBiasReport:
    return JudgeBiasReport(
        generated_at="2026-08-01T00:00:00+00:00",
        sample_set="sample.json",
        annotations="annotations.json",
        excellence_report="excellence.json",
        style_card_report="style.json",
        voice_anchor_report="voice.json",
        boundaries=["report-only"],
        summary={"supported_biases": 1},
        score_deltas=[],
        evidence_fidelity=[],
        findings=[],
        protocols=[],
    )


def test_analyze_chapter_readability_flags_long_sentence_and_sparse_dialogue() -> None:
    long_sentence = (
        "林渊沿着裂开的主控台继续向前走，他看见所有协议像潮水一样"
        "从屏幕深处倒卷出来，几乎要把整座方舟的呼吸都压进胸腔，"
        "而远处那些没有熄灭的信标仍在用同一个频率回应他的心跳。"
    )
    chapter = LoadedChapter(
        genre="scifi",
        chapter=1,
        version_id="v-1",
        segment=1,
        content=f"{long_sentence}\n{long_sentence}\n短。\n短。\n短。\n短。\n短。",
    )

    report = analyze_chapter_readability(chapter)

    assert "long_sentence_load" in report.risk_flags
    assert "short_paragraph_staccato" in report.risk_flags
    assert "dialogue_sparse" in report.risk_flags
    assert report.sentence_readability.sentence_count >= 2


def test_build_report_defers_true_perplexity_without_external_model() -> None:
    chapters = [
        LoadedChapter(
            "scifi",
            1,
            "v-weak",
            1,
            "短。\n短。\n短。\n短。\n短。\n“走。”",
        ),
        LoadedChapter(
            "scifi",
            2,
            "v-strong",
            1,
            "林渊把手放在控制台上，屏幕亮起。陈薇说：“坐标锁定。”",
        ),
    ]
    annotations = [
        _annotation(version_id="v-weak", overall=2, ai_tone=2),
        _annotation(version_id="v-strong", overall=4),
    ]

    report = build_readability_feasibility_report(
        chapters,
        annotations,
        _excellence_report(),
        _style_report(),
        _voice_report(),
        _judge_report(),
        sample_set_path=Path("sample.json"),
        annotations_path=Path("annotations.json"),
        excellence_report_path=Path("excellence.json"),
        style_card_report_path=Path("style.json"),
        voice_anchor_report_path=Path("voice.json"),
        judge_bias_report_path=Path("judge.json"),
    )

    assert report.perplexity_feasibility.decision == "defer"
    assert report.perplexity_feasibility.requires_model_weights is True
    assert report.perplexity_feasibility.reproducible_without_external_model is False
    assert report.sanity_check.weak_samples == 1


def test_decisions_include_all_candidate_signals() -> None:
    chapter = LoadedChapter(
        "scifi",
        1,
        "v-1",
        1,
        "林渊说：“坐标锁定。”陈薇点头，控制台亮起。",
    )
    report = build_readability_feasibility_report(
        [chapter],
        [_annotation(version_id="v-1", overall=4)],
        _excellence_report(),
        _style_report(),
        _voice_report(),
        _judge_report(),
        sample_set_path=Path("sample.json"),
        annotations_path=Path("annotations.json"),
        excellence_report_path=Path("excellence.json"),
        style_card_report_path=Path("style.json"),
        voice_anchor_report_path=Path("voice.json"),
        judge_bias_report_path=Path("judge.json"),
    )

    assert {item.signal_id for item in report.decisions} == {
        "sentence_readability",
        "paragraph_readability",
        "dialogue_ratio",
        "punctuation_rhythm",
        "lexical_repetition_proxy",
        "perplexity_feasibility",
    }
    assert all(item.decision in {"report-only", "defer"} for item in report.decisions)


def test_markdown_declares_no_llm_and_no_gate() -> None:
    chapter = LoadedChapter("scifi", 1, "v-1", 1, "林渊说：“坐标锁定。”")
    report = build_readability_feasibility_report(
        [chapter],
        [_annotation(version_id="v-1", overall=4)],
        _excellence_report(),
        _style_report(),
        _voice_report(),
        _judge_report(),
        sample_set_path=Path("sample.json"),
        annotations_path=Path("annotations.json"),
        excellence_report_path=Path("excellence.json"),
        style_card_report_path=Path("style.json"),
        voice_anchor_report_path=Path("voice.json"),
        judge_bias_report_path=Path("judge.json"),
    )

    markdown = render_readability_feasibility_report(report)

    assert "does not call LLMs" in markdown
    assert "does not enter accept/reject gates" in markdown
    assert "Perplexity Feasibility" in markdown
