"""Tests for per-chapter forbidden-term scan helpers."""

from __future__ import annotations

from songyan.agents.goal_planner import _extract_forbidden_terms_for_chapter
from songyan.evals.forbidden_scan import (
    ForbiddenScanResult,
    render_forbidden_scan_section,
    scan_text_for_forbidden_terms,
)


def test_scan_text_for_forbidden_terms_reports_line_number() -> None:
    text = "第一行\n沈砚看见木星大红斑。\n第三行"

    hits = scan_text_for_forbidden_terms(
        chapter_number=3,
        text=text,
        forbidden_terms=["木星", "阮星河"],
    )

    assert len(hits) == 1
    assert hits[0].chapter_number == 3
    assert hits[0].term == "木星"
    assert hits[0].line_number == 2
    assert "木星大红斑" in hits[0].evidence


def test_chapter_scoped_terms_prevent_global_false_positive() -> None:
    arc_goal = (
        "硬禁用：Ch1-Ch3 不得出现阮星河；"
        "Ch3 不得出现三天前、自然人身份。"
    )
    ch2_terms = _extract_forbidden_terms_for_chapter(arc_goal, 2)
    ch3_terms = _extract_forbidden_terms_for_chapter(arc_goal, 3)

    ch2_hits = scan_text_for_forbidden_terms(
        chapter_number=2,
        text="三天前，一次常规确认留下记录。",
        forbidden_terms=ch2_terms,
    )
    ch3_hits = scan_text_for_forbidden_terms(
        chapter_number=3,
        text="V-0003 的创建时间戳是三天前。",
        forbidden_terms=ch3_terms,
    )

    assert ch2_hits == []
    assert [hit.term for hit in ch3_hits] == ["三天前"]


def test_time_prefix_forbidden_term_does_not_match_mass_value() -> None:
    arc_goal = "Ch2 不得出现 14:、下午两点。"
    ch2_terms = _extract_forbidden_terms_for_chapter(arc_goal, 2)

    hits = scan_text_for_forbidden_terms(
        chapter_number=2,
        text="账面质量：14,286.71 kg。终端时间显示04:32。",
        forbidden_terms=ch2_terms,
    )

    assert ch2_terms == ["14:", "下午两点"]
    assert hits == []


def test_scan_text_for_forbidden_patterns_from_terms() -> None:
    text = "他解码后得到东经121.47，北纬31.23。沈弥的ID在屏幕上闪了一次。"

    hits = scan_text_for_forbidden_terms(
        chapter_number=2,
        text=text,
        forbidden_terms=["具体经纬度", "沈弥的声音"],
    )

    terms = [hit.term for hit in hits]
    assert "pattern:经纬度坐标" in terms
    assert "pattern:沈弥身份化线索" in terms


def test_scan_text_for_future_time_forbidden_patterns() -> None:
    text = "记录显示为未来第43分钟，随后又写成三天后。"

    hits = scan_text_for_forbidden_terms(
        chapter_number=3,
        text=text,
        forbidden_terms=["三天前"],
    )

    assert [hit.term for hit in hits] == [
        "pattern:前三章禁用回溯时间",
        "pattern:前三章禁用回溯时间",
    ]
    assert "未来第43分钟" in hits[0].evidence


def test_scan_text_for_relative_past_forbidden_patterns() -> None:
    text = "舱壁参数和昨天、前天一样。三年前的旧记录仍在缓存。"

    hits = scan_text_for_forbidden_terms(
        chapter_number=1,
        text=text,
        forbidden_terms=["三天前"],
    )

    assert [hit.term for hit in hits] == [
        "pattern:前三章禁用回溯时间",
        "pattern:前三章禁用回溯时间",
        "pattern:前三章禁用回溯时间",
    ]
    assert any("三年前" in hit.evidence for hit in hits)


def test_scan_text_for_mixed_clock_forbidden_pattern() -> None:
    text = (
        "终端显示当前时间是04:32。沈砚继续复核当前责任栏。"
        "他再次打开操作日志，开始查看14:32之后的系统访问记录。"
    )

    hits = scan_text_for_forbidden_terms(
        chapter_number=2,
        text=text,
        forbidden_terms=["三天前"],
    )

    assert [hit.term for hit in hits] == ["pattern:章内时间格式冲突"]
    assert "04:32" in hits[0].evidence
    assert "14:32" in hits[0].evidence


def test_render_forbidden_scan_section() -> None:
    result = ForbiddenScanResult(
        scanned_chapters=[1, 2, 3],
        hits=scan_text_for_forbidden_terms(
            chapter_number=3,
            text="V-0003 的创建时间戳是三天前。",
            forbidden_terms=["三天前"],
        ),
        warnings=[],
    )

    report = render_forbidden_scan_section(result)

    assert "## 章节禁用词扫描" in report
    assert "**扫描章节**: Ch1, Ch2, Ch3" in report
    assert "**命中数**: 1" in report
    assert "| Ch3 | `三天前` | 1 |" in report
