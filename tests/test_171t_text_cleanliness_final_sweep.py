"""Task 171t: D1 文本洁净量具补强与 final sweep 契约."""

from __future__ import annotations

from songyan.agents.rule_auditor import (
    collect_text_cleanliness_clean_issues,
    detect_text_cleanliness_artifacts,
    run_rule_audit,
)
from songyan.workflows.review_merger import _convert_rule_to_issues


def _artifact_types(text: str) -> set[str]:
    return {m.artifact_type or "" for m in detect_text_cleanliness_artifacts(text)}


class TestTextCleanlinessArtifacts:
    def test_detects_all_171t_artifact_types(self) -> None:
        text = "\n\n".join(
            [
                "# 第一章 方舟",
                "林渊推开舱门。",
                "【保护内容 — 请勿修改】",
                "他抬起左臂 / 然后把接口压进冷光里。",
                "……",
                "每句末尾加重语气，机械眼闪烁红色警告。",
            ]
        )

        types = _artifact_types(text)

        assert "markdown_heading_leak" in types
        assert "protected_directive_leak" in types
        assert "slash_splice_artifact" in types
        assert "ellipsis_placeholder_paragraph" in types
        assert "prompt_patch_instruction_leak" in types

    def test_slash_detector_allows_units_urls_paths_and_ratios(self) -> None:
        text = "\n".join(
            [
                "速度稳定在 12km/s，信号比为 7/8。",
                "日志路径 C:/tmp/songyan/report.txt 没有异常。",
                "远端地址 https://example.test/a/b 可访问。",
            ]
        )

        assert "slash_splice_artifact" not in _artifact_types(text)

    def test_sentence_ellipsis_is_allowed_but_placeholder_paragraph_is_not(self) -> None:
        text = "林渊沉默了……然后继续向前。\n\n……"

        matches = detect_text_cleanliness_artifacts(text)

        assert sum(m.artifact_type == "ellipsis_placeholder_paragraph" for m in matches) == 1
        assert all(m.matched_text.strip() != "林渊沉默了……然后继续向前。" for m in matches)


class TestFinalSweepCleanIssues:
    def test_final_sweep_emits_stable_clean_issue_shape(self) -> None:
        text = "# 第一章 方舟\n\n林渊推开舱门。\n\n【保护内容 — 请勿修改】"

        issues = collect_text_cleanliness_clean_issues(
            text, chapter_number=84, version_id="v-84-accepted"
        )

        assert {i.issue_type for i in issues} >= {
            "markdown_heading_leak",
            "protected_directive_leak",
        }
        for issue in issues:
            assert issue.chapter_number == 84
            assert issue.version_id == "v-84-accepted"
            assert issue.evidence_quote
            assert issue.evidence_location
            assert issue.suggested_action
            assert issue.deterministic_cleanable is True

    def test_final_sweep_includes_duplicate_paragraphs(self) -> None:
        para = (
            "林渊把那段不断回放的警报压进日志里，确认每一个闪烁频率都指向同一处裂隙，"
            "也指向舱壁后方那条正在扩大的黑色缝隙。"
        )
        text = f"{para}\n\n过渡段。\n\n{para}"

        issues = collect_text_cleanliness_clean_issues(text)

        assert any(i.issue_type == "duplicate_paragraph" for i in issues)

    def test_clean_text_has_no_171t_issues(self) -> None:
        text = (
            "林渊推开舱门，冷光从地面升起。\n\n"
            "速度维持在 12km/s，赵铭把路径写进 C:/tmp/songyan/report.txt。"
        )

        assert collect_text_cleanliness_clean_issues(text) == []


class TestRuleAuditAndReviewMergerIntegration:
    def test_run_rule_audit_records_text_artifact_count(self) -> None:
        result = run_rule_audit("# 第一章 方舟\n\n林渊推开舱门。", word_count_target=10)

        assert result.text_artifact_count == 1
        assert result.text_artifact_matches[0].artifact_type == "markdown_heading_leak"

    def test_artifacts_convert_to_patchable_major_issue(self) -> None:
        content = "林渊推开舱门。\n\n【保护内容 — 请勿修改】"
        rule_result = run_rule_audit(content, word_count_target=10)

        issues = _convert_rule_to_issues(content, rule_result, "v171t")
        artifact_issues = [
            issue for issue in issues if issue.issue_id.startswith("rule-artifact-")
        ]

        assert len(artifact_issues) == 1
        assert artifact_issues[0].severity == "major"
        assert artifact_issues[0].fix_type == "patch"
        assert artifact_issues[0].evidence_quote
