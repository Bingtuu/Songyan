"""Task 079: RevisionHandler 分段修订 — 单元测试."""

from __future__ import annotations

from unittest.mock import AsyncMock, patch

import pytest

from songyan.agents.revision_handler._segmented_revision import (
    _compute_preservation_ratio,
    _map_issues_to_scenes,
    _reassemble_content,
    _render_scene_prompt,
    _split_content_by_scenes,
    run_segmented_revision,
)
from songyan.models import ReviewCategory, ReviewIssue

# =============================================================================
# Scene 分割
# =============================================================================

class TestSplitContentByScenes:
    def test_splits_multiple_scenes(self) -> None:
        content = (
            "### Scene 1\n第一段正文。\n\n"
            "### Scene 2\n第二段正文。\n\n"
            "### Scene 3\n第三段正文。"
        )
        scenes = _split_content_by_scenes(content)
        assert len(scenes) == 3
        assert scenes[0]["scene_number"] == 1
        assert "第一段" in scenes[0]["content"]
        assert scenes[1]["scene_number"] == 2
        assert "第二段" in scenes[1]["content"]
        assert scenes[2]["scene_number"] == 3
        assert "第三段" in scenes[2]["content"]

    def test_single_scene_fallback(self) -> None:
        content = "没有 scene 标题的纯文本。"
        scenes = _split_content_by_scenes(content)
        assert len(scenes) == 1
        assert scenes[0]["scene_number"] == 1

    def test_header_preserved(self) -> None:
        content = "### Scene 1\n正文。"
        scenes = _split_content_by_scenes(content)
        assert scenes[0]["header"].strip() == "### Scene 1"


# =============================================================================
# Issue-Scene 映射
# =============================================================================

class TestMapIssuesToScenes:
    def test_evidence_quote_maps_to_scene(self) -> None:
        content = "### Scene 1\n这是第一段。\n\n### Scene 2\n这是第二段。"
        scenes = _split_content_by_scenes(content)
        issues = [
            ReviewIssue(
                issue_id="i1",
                category=ReviewCategory.SHOW_DONT_TELL,
                severity="major",
                evidence_quote="这是第二段",
                evidence_location="Scene 2",
                issue_description="test",
                fix_type="patch",
            )
        ]
        mapped, global_issues = _map_issues_to_scenes(issues, scenes, content)
        assert len(mapped[2]) == 1
        assert mapped[1] == []
        assert global_issues == []

    def test_no_evidence_quote_fallback_to_location(self) -> None:
        content = "### Scene 1\n森林里的故事。\n\n### Scene 2\n飞船上的故事。"
        scenes = _split_content_by_scenes(content)
        issues = [
            ReviewIssue(
                issue_id="i1",
                category=ReviewCategory.SHOW_DONT_TELL,
                severity="major",
                evidence_quote="",
                evidence_location="飞船",
                issue_description="test",
                fix_type="patch",
            )
        ]
        mapped, global_issues = _map_issues_to_scenes(issues, scenes, content)
        assert len(mapped[2]) == 1
        assert global_issues == []

    def test_unlocatable_issue_goes_global(self) -> None:
        content = "### Scene 1\n正文。"
        scenes = _split_content_by_scenes(content)
        issues = [
            ReviewIssue(
                issue_id="i1",
                category=ReviewCategory.SHOW_DONT_TELL,
                severity="major",
                evidence_quote="不存在的文本",
                evidence_location="",
                issue_description="test",
                fix_type="patch",
            )
        ]
        mapped, global_issues = _map_issues_to_scenes(issues, scenes, content)
        assert len(global_issues) == 1


# =============================================================================
# 保留率计算
# =============================================================================

class TestPreservationRatio:
    def test_full_preserve(self) -> None:
        assert _compute_preservation_ratio("abc", "abc") == 1.0

    def test_half_preserve(self) -> None:
        assert _compute_preservation_ratio("abcd", "ab") == 0.5

    def test_below_threshold(self) -> None:
        assert _compute_preservation_ratio("abcd", "a") == 0.25


# =============================================================================
# 拼接
# =============================================================================

class TestReassembleContent:
    def test_reassembles_without_scene_headers(self) -> None:
        scenes = [
            {"scene_number": 1, "content": "第一段", "header": "### Scene 1"},
            {"scene_number": 2, "content": "第二段", "header": "### Scene 2"},
        ]
        revised = ["修订一", "修订二"]
        result = _reassemble_content(scenes, revised)
        assert "### Scene 1" not in result
        assert "修订一" in result
        assert "### Scene 2" not in result
        assert "修订二" in result


# =============================================================================
# Prompt 渲染
# =============================================================================

class TestRenderScenePrompt:
    def test_includes_scene_content(self) -> None:
        issues = [
            ReviewIssue(
                issue_id="i1",
                category=ReviewCategory.SHOW_DONT_TELL,
                severity="major",
                evidence_quote="引用",
                evidence_location="Scene 1",
                issue_description="描述",
                suggested_fix="建议",
                fix_type="patch",
            )
        ]
        prompt = _render_scene_prompt("场景正文", issues, [])
        assert "场景正文" in prompt
        assert "引用" in prompt
        assert "建议" in prompt
        assert "不要输出 `### Scene N`" in prompt

    def test_includes_protected_fissures(self) -> None:
        prompt = _render_scene_prompt("正文", [], ["保护内容"])
        assert "保护内容" in prompt


# =============================================================================
# 分段修订主入口（mock LLM）
# =============================================================================

class TestRunSegmentedRevision:
    @pytest.mark.asyncio
    async def test_not_enough_scenes_fallback(self) -> None:
        """没有 issue 时返回 segmented=False."""
        output, content = await run_segmented_revision(
            content="单一段落，没有 scene 标题。",
            issues=[],
        )
        assert output.segmented is False
        assert content == "单一段落，没有 scene 标题。"

    @pytest.mark.asyncio
    async def test_single_scene_with_issue_uses_segmented_revision(self) -> None:
        """Task 114c: 单 scene 章节仍可作为局部修订单元处理."""
        content = "单一场景开头。这里有一处直接说明情绪。单一场景结尾。"
        issues = [
            ReviewIssue(
                issue_id="i1",
                category=ReviewCategory.SHOW_DONT_TELL,
                severity="major",
                evidence_quote="直接说明情绪",
                evidence_location="单一场景",
                issue_description="需要改成动作呈现",
                fix_type="patch",
            )
        ]

        with patch(
            "songyan.agents.revision_handler._segmented_revision.call_llm",
            new_callable=AsyncMock,
        ) as mock_llm:
            mock_llm.return_value = "单一场景开头。这里有一处攥紧袖口的动作。单一场景结尾。"
            output, revised = await run_segmented_revision(
                content=content,
                issues=issues,
            )

        assert output.segmented is True
        assert output.scenes_modified == 1
        assert output.scenes_fallback_count == 0
        assert "攥紧袖口" in revised

    @pytest.mark.asyncio
    async def test_no_mapped_issues_fallback(self) -> None:
        """issue 无法映射到 scene 时返回 segmented=False."""
        output, content = await run_segmented_revision(
            content="### Scene 1\n正文一。\n\n### Scene 2\n正文二。",
            issues=[
                ReviewIssue(
                    issue_id="i1",
                    category=ReviewCategory.SHOW_DONT_TELL,
                    severity="major",
                    evidence_quote="完全不存在的文本",
                    evidence_location=" nowhere ",
                    issue_description="test",
                    fix_type="patch",
                )
            ],
        )
        assert output.segmented is False

    @pytest.mark.asyncio
    async def test_revises_scene_and_assembles(self) -> None:
        """正常分段修订流程：mock LLM 返回修订后的 scene."""
        content = "### Scene 1\n这是第一段正文。\n\n### Scene 2\n这是第二段正文。"
        issues = [
            ReviewIssue(
                issue_id="i1",
                category=ReviewCategory.SHOW_DONT_TELL,
                severity="major",
                evidence_quote="第二段正文",
                evidence_location="Scene 2",
                issue_description="需要修改",
                fix_type="patch",
            )
        ]

        with patch(
            "songyan.agents.revision_handler._segmented_revision.call_llm",
            new_callable=AsyncMock,
        ) as mock_llm:
            # Scene 1 无 issue，不调 LLM
            # Scene 2 有 issue，调 LLM 返回修订版
            mock_llm.return_value = "这是修改后的第二段正文。"
            output, revised = await run_segmented_revision(
                content=content,
                issues=issues,
            )

        assert output.segmented is True
        assert output.scenes_modified == 1
        assert output.scenes_fallback_count == 0
        assert "修改后的第二段" in revised
        assert "这是第一段正文" in revised  # Scene 1 未修改

    @pytest.mark.asyncio
    async def test_fallback_when_poor_preservation(self) -> None:
        """保留率 < 50% 时回退到原始 scene."""
        content = "### Scene 1\n正文一。\n\n### Scene 2\n正文二正文二正文二。"
        issues = [
            ReviewIssue(
                issue_id="i1",
                category=ReviewCategory.SHOW_DONT_TELL,
                severity="major",
                evidence_quote="正文二正文二正文二",
                evidence_location="Scene 2",
                issue_description="需要修改",
                fix_type="patch",
            )
        ]

        with patch(
            "songyan.agents.revision_handler._segmented_revision.call_llm",
            new_callable=AsyncMock,
        ) as mock_llm:
            # LLM 返回极短内容（< 50% 保留率）
            mock_llm.return_value = "短。"
            output, revised = await run_segmented_revision(
                content=content,
                issues=issues,
            )

        assert output.segmented is True
        assert output.scenes_fallback_count == 1
        assert "正文二正文二正文二" in revised  # Scene 2 回退到原始内容
