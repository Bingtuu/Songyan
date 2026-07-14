"""Task 160: 元标记泄漏根治测试."""

from __future__ import annotations

from unittest.mock import AsyncMock

import pytest

from songyan.agents.rule_auditor import detect_markdown_scene_titles, run_rule_audit
from songyan.agents.writer import _extract_body
from songyan.models import (
    AiTellMatch,
    FatigueWordMatch,
    LLMAuditResult,
    MetaTagLeakMatch,
    RuleAuditResult,
)
from songyan.workflows.review_merger import _convert_rule_to_issues, merge_reviews


class TestSceneMarkerDetection:
    def test_detects_v7_representative_scene_marker_shapes(self) -> None:
        text = "\n".join(
            [
                "### Scene N",
                "## Scene 1 控制室",
                "# Scene 2: 外围",
                "**Scene 3** 外层甲板",
                "Scene 4: 指挥中心",
                "### 场景一：坠落",
                "场景二：地面站",
                "这是正常正文。",
            ]
        )

        matches = detect_markdown_scene_titles(text)

        assert len(matches) == 7
        assert all(match.severity == "major" for match in matches)
        assert any("Markdown场景标题" in match.pattern for match in matches)
        assert any("中文场景标题" in match.pattern for match in matches)

    def test_does_not_match_normal_sentences(self) -> None:
        text = (
            "场景一片混乱，但林渊没有停下。\n"
            "他在 Scene 1 旧日志里找到一个坐标，不是章节标题。"
        )

        assert detect_markdown_scene_titles(text) == []


class TestSceneMarkerCleaning:
    def test_extract_body_strips_scene_markers_by_default(self) -> None:
        response = (
            "正文：\n"
            "### Scene N\n"
            "第一段正文。\n\n"
            "## Scene 1 控制室\n"
            "第二段正文。\n\n"
            "**Scene 2** 外层甲板\n"
            "第三段正文。\n\n"
            "Scene 3: 指挥中心\n"
            "第四段正文。\n\n"
            "### 场景一：坠落\n"
            "第五段正文。"
        )

        body = _extract_body(response)

        assert "Scene" not in body
        assert "场景一" not in body
        assert "第一段正文" in body
        assert "第五段正文" in body

    def test_extract_body_can_preserve_numeric_scene_markers_for_parser(self) -> None:
        response = "### Scene 1\n第一段正文。\n\n### Scene 2\n第二段正文。"

        body = _extract_body(response, strip_scene_markers=False)

        assert "### Scene 1" in body
        assert "### Scene 2" in body
        assert "第一段正文" in body

    def test_extract_body_strips_chinese_numeral_chapter_heading(self) -> None:
        response = "# 第一章\n\n正文第一段。\n\n正文第二段。"

        body = _extract_body(response)

        assert "# 第一章" not in body
        assert "第一章" not in body
        assert "正文第一段" in body
        assert "正文第二段" in body

    def test_extract_body_strips_mixed_numeral_chapter_heading(self) -> None:
        response = "## 第1章 灵渊纪\n正文开始。"

        body = _extract_body(response)

        assert "## 第1章" not in body
        assert "正文开始" in body


class TestReviewMergerBlocking:
    def test_rule_audit_scene_markers_convert_to_patchable_major_issue(self) -> None:
        content = "### Scene N\n第一段正文。\n\nScene 2: 控制室\n第二段正文。"
        rule_result = run_rule_audit(content, word_count_target=10)

        issues = _convert_rule_to_issues(content, rule_result, "v160")
        scene_issues = [i for i in issues if i.issue_id.startswith("rule-scene-")]

        assert len(scene_issues) == 1
        assert scene_issues[0].severity == "major"
        assert scene_issues[0].fix_type == "patch"
        assert scene_issues[0].evidence_quote

    def test_meta_tag_and_scene_marker_issues_are_not_capped(self) -> None:
        rule_result = RuleAuditResult(
            meta_tag_count=1,
            meta_tag_matches=[
                MetaTagLeakMatch(
                    pattern="HTML注释",
                    matched_text="<!-- debug -->",
                    location="第1段",
                )
            ],
            markdown_scene_title_count=1,
            markdown_scene_title_matches=[
                MetaTagLeakMatch(
                    pattern="Markdown场景标题",
                    matched_text="### Scene N",
                    location="第2段",
                )
            ],
            has_opening_hook=False,
            has_ending_hook=False,
            ai_tell_count=2,
            ai_tell_matches=[
                AiTellMatch(pattern="p1", matched_text="不禁意识到", location="第3段"),
                AiTellMatch(pattern="p2", matched_text="一股暖流", location="第4段"),
            ],
            fatigue_word_count=3,
            fatigue_word_matches=[
                FatigueWordMatch(word="冷笑", count=1, locations=["第5段"]),
                FatigueWordMatch(word="嘴角勾起", count=1, locations=["第6段"]),
                FatigueWordMatch(word="眼神复杂", count=1, locations=["第7段"]),
            ],
            paragraph_rhythm_score=3.0,
            rhythm_issues=["段落过长"],
            word_count=4000,
            word_count_target=3000,
            scene_count=1,
        )

        issues = _convert_rule_to_issues("正文", rule_result, "v160")
        issue_ids = {issue.issue_id for issue in issues}
        regular = [
            issue for issue in issues
            if not issue.issue_id.startswith(("rule-meta-", "rule-scene-"))
        ]

        assert "rule-meta-v160" in issue_ids
        assert "rule-scene-v160" in issue_ids
        assert len(regular) == 5

    @pytest.mark.asyncio
    async def test_merged_report_has_major_for_scene_marker(self) -> None:
        content = "### Scene N\n第一段正文。"
        rule_result = run_rule_audit(content, word_count_target=10)
        db = AsyncMock()

        report = await merge_reviews(
            version_id="v160",
            content=content,
            rule_result=rule_result,
            llm_result=LLMAuditResult(),
            db=db,
            report_id="mr-v160",
        )

        assert report.has_major is True
        assert any(
            issue.issue_id.startswith("rule-scene-")
            for issue in report.patchable_issues
        )
