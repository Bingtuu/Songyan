"""Tests for RevisionHandler Agent."""

from __future__ import annotations

import json
from unittest.mock import AsyncMock, patch

import pytest

from songyan.agents.revision_handler import (
    MAX_CONTENT_TOKENS,
    _apply_patches,
    _build_revision_output,
    _determine_issues_fixed,
    _extract_protected_fissures,
    _filter_patchable_issues,
    _parse_patches,
    _render_previous_show_dont_tell_feedback,
    _render_prompt,
    _render_protected_fissures,
    run_revision,
    save_revision_output,
)
from songyan.exceptions import LLMResponseParseError
from songyan.models import (
    ChapterHead,
    ChapterVersion,
    LiteraryAuditResult,
    LiteraryObservation,
    MergedReviewReport,
    Patch,
    ReviewCategory,
    ReviewIssue,
    RevisionOutput,
)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------
def _make_review_issue(
    issue_id: str = "i1",
    severity: str = "major",
    fix_type: str = "patch",
    evidence_quote: str = "原文引用",
) -> ReviewIssue:
    return ReviewIssue(
        issue_id=issue_id,
        category=ReviewCategory.CHARACTER_BEHAVIOR,
        severity=severity,  # type: ignore[arg-type]
        evidence_quote=evidence_quote,
        evidence_location="第2段",
        issue_description="问题描述",
        fix_type=fix_type,  # type: ignore[arg-type]
    )


def _make_merged_report(*issues: ReviewIssue) -> MergedReviewReport:
    return MergedReviewReport(
        chapter_version_id="version_123",
        issues=list(issues),
    )


def _make_valid_llm_response(content: str = "修改后正文", patches: list[dict] | None = None) -> str:
    data: dict[str, object] = {"content": content}
    if patches is not None:
        data["patches"] = patches
    return json.dumps(data, ensure_ascii=False)


# ---------------------------------------------------------------------------
# Filter Patchable Issues
# ---------------------------------------------------------------------------
class TestFilterPatchableIssues:
    def test_filters_critical_major_patch(self) -> None:
        i1 = _make_review_issue("i1", "critical", "patch")
        i2 = _make_review_issue("i2", "major", "patch")
        report = _make_merged_report(i1, i2)
        result = _filter_patchable_issues(report)
        assert len(result) == 2

    def test_excludes_minor_info(self) -> None:
        i1 = _make_review_issue("i1", "minor", "patch")
        i2 = _make_review_issue("i2", "info", "patch")
        report = _make_merged_report(i1, i2)
        result = _filter_patchable_issues(report)
        assert result == []

    def test_excludes_non_patch_fix_type(self) -> None:
        i1 = _make_review_issue("i1", "critical", "rewrite_scene")
        i2 = _make_review_issue("i2", "major", "confirm")
        i3 = _make_review_issue("i3", "major", "register_setting")
        report = _make_merged_report(i1, i2, i3)
        result = _filter_patchable_issues(report)
        assert result == []


# ---------------------------------------------------------------------------
# Extract Protected Fissures
# ---------------------------------------------------------------------------
class TestExtractProtectedFissures:
    def test_valuable_fissure_preserve(self) -> None:
        result = LiteraryAuditResult(
            observations=[
                LiteraryObservation(
                    observation_id="o1",
                    observation_type="valuable_fissure",
                    description="裂隙",
                    evidence_quote="林凡放下了剑",
                    preserve=True,
                )
            ]
        )
        protected = _extract_protected_fissures(result)
        assert protected == ["林凡放下了剑"]

    def test_none_literary_result(self) -> None:
        assert _extract_protected_fissures(None) == []

    def test_non_valuable_fissure_ignored(self) -> None:
        result = LiteraryAuditResult(
            observations=[
                LiteraryObservation(
                    observation_id="o1",
                    observation_type="cliche_risk",
                    description="套路",
                    evidence_quote="反派大笑",
                    preserve=False,
                )
            ]
        )
        assert _extract_protected_fissures(result) == []

    def test_preserve_false_ignored(self) -> None:
        result = LiteraryAuditResult(
            observations=[
                LiteraryObservation(
                    observation_id="o1",
                    observation_type="valuable_fissure",
                    description="裂隙",
                    evidence_quote="放下剑",
                    preserve=False,
                )
            ]
        )
        assert _extract_protected_fissures(result) == []

    def test_empty_evidence_quote_skipped(self) -> None:
        result = LiteraryAuditResult(
            observations=[
                LiteraryObservation(
                    observation_id="o1",
                    observation_type="valuable_fissure",
                    description="裂隙",
                    evidence_quote="",
                    preserve=True,
                )
            ]
        )
        assert _extract_protected_fissures(result) == []


# ---------------------------------------------------------------------------
# Prompt Rendering
# ---------------------------------------------------------------------------
class TestRenderPrompt:
    def test_loads_template(self) -> None:
        prompt = _render_prompt("正文", [], [])
        assert "修订" in prompt or "修改" in prompt

    def test_includes_content(self) -> None:
        prompt = _render_prompt("这是测试正文", [], [])
        assert "这是测试正文" in prompt

    def test_truncates_long_content(self) -> None:
        long_content = "测" * (MAX_CONTENT_TOKENS + 1000)
        prompt = _render_prompt(long_content, [], [])
        assert "...（正文已截断）" in prompt

    def test_includes_issues(self) -> None:
        issue = _make_review_issue("i1", "critical", "patch", "原文引用")
        prompt = _render_prompt("正文", [issue], [])
        assert "i1" in prompt
        assert "原文引用" in prompt

    def test_includes_protected_fissures(self) -> None:
        prompt = _render_prompt("正文", [], ["保护内容1", "保护内容2"])
        assert "保护内容1" in prompt
        assert "保护内容2" in prompt


class TestRenderProtectedFissures:
    def test_empty(self) -> None:
        assert _render_protected_fissures([]) == "（无）"

    def test_with_items(self) -> None:
        result = _render_protected_fissures(["a", "b"])
        assert "1. a" in result
        assert "2. b" in result


# ---------------------------------------------------------------------------
# Previous Issues Feedback Injection (Task 068)
# ---------------------------------------------------------------------------
class TestRenderPreviousShowDontTellFeedback:
    def test_none_returns_empty(self) -> None:
        assert _render_previous_show_dont_tell_feedback(None) == ""

    def test_empty_list_returns_empty(self) -> None:
        assert _render_previous_show_dont_tell_feedback([]) == ""

    def test_no_show_dont_tell_issues_returns_empty(self) -> None:
        issues = [
            ReviewIssue(
                issue_id="i1",
                category=ReviewCategory.CHARACTER_BEHAVIOR,
                severity="major",
                evidence_quote="引用",
                evidence_location="第2段",
                issue_description="问题",
            )
        ]
        assert _render_previous_show_dont_tell_feedback(issues) == ""

    def test_includes_evidence_quotes_and_descriptions(self) -> None:
        issues = [
            ReviewIssue(
                issue_id="i1",
                category=ReviewCategory.SHOW_DONT_TELL,
                severity="major",
                evidence_quote="他感到非常愤怒。",
                evidence_location="第2段",
                issue_description="直接陈述情绪，未通过动作/环境展示",
            ),
            ReviewIssue(
                issue_id="i2",
                category=ReviewCategory.SHOW_DONT_TELL,
                severity="major",
                evidence_quote="林凡不禁意识到一股暖流涌上心头。",
                evidence_location="第3段",
                issue_description="过于抽象，缺乏感官细节",
            ),
        ]
        result = _render_previous_show_dont_tell_feedback(issues)
        assert "上一轮审查的具体证据" in result
        assert "他感到非常愤怒。" in result
        assert "林凡不禁意识到一股暖流涌上心头。" in result
        assert "直接陈述情绪，未通过动作/环境展示" in result
        assert "过于抽象，缺乏感官细节" in result

    def test_skips_empty_evidence_quote(self) -> None:
        issues = [
            ReviewIssue(
                issue_id="i1",
                category=ReviewCategory.SHOW_DONT_TELL,
                severity="major",
                evidence_quote="",
                evidence_location="第2段",
                issue_description="空引用",
            ),
            ReviewIssue(
                issue_id="i2",
                category=ReviewCategory.SHOW_DONT_TELL,
                severity="major",
                evidence_quote="有效引用",
                evidence_location="第3段",
                issue_description="有引用",
            ),
        ]
        result = _render_previous_show_dont_tell_feedback(issues)
        assert "有效引用" in result
        assert "空引用" not in result
        assert result.count(".") == 1  # 只有一个序号

    def test_truncates_long_feedback(self) -> None:
        long_quote = "长" * 1000
        issues = [
            ReviewIssue(
                issue_id="i1",
                category=ReviewCategory.SHOW_DONT_TELL,
                severity="major",
                evidence_quote=long_quote,
                evidence_location="第2段",
                issue_description="描述",
            ),
        ]
        result = _render_previous_show_dont_tell_feedback(issues)
        assert len(result) <= 1020  # 1000 + 截断提示符
        assert "...（证据列表已截断）" in result


class TestRenderPromptFeedbackInjection:
    def test_includes_previous_issues_feedback(self) -> None:
        issue = _make_review_issue("i1", "critical", "patch", "大笑起来")
        previous = [
            ReviewIssue(
                issue_id="prev1",
                category=ReviewCategory.SHOW_DONT_TELL,
                severity="major",
                evidence_quote="他感到非常愤怒。",
                evidence_location="第2段",
                issue_description="直接陈述情绪",
            )
        ]
        prompt = _render_prompt("正文", [issue], [], previous_issues=previous)
        assert "上一轮审查的具体证据" in prompt
        assert "他感到非常愤怒。" in prompt
        assert "直接陈述情绪" in prompt

    def test_no_previous_issues_no_feedback_section(self) -> None:
        issue = _make_review_issue("i1", "critical", "patch", "大笑起来")
        prompt = _render_prompt("正文", [issue], [], previous_issues=None)
        assert "上一轮审查的具体证据" not in prompt


# ---------------------------------------------------------------------------
# Parse Patches
# ---------------------------------------------------------------------------
class TestParsePatches:
    def test_valid(self) -> None:
        data = {
            "patches": [
                {
                    "issue_id": "i1",
                    "original_text": "原文",
                    "revised_text": "修改后",
                    "location": "第3段",
                }
            ]
        }
        patches = _parse_patches(data)
        assert len(patches) == 1
        assert patches[0].issue_id == "i1"

    def test_missing_issue_id_filtered(self) -> None:
        data = {"patches": [{"original_text": "原文", "revised_text": "修改后"}]}
        patches = _parse_patches(data)
        assert patches == []

    def test_missing_original_text_filtered(self) -> None:
        data = {"patches": [{"issue_id": "i1", "revised_text": "修改后"}]}
        patches = _parse_patches(data)
        assert patches == []

    def test_empty_patches(self) -> None:
        assert _parse_patches({"patches": []}) == []

    def test_no_patches_key(self) -> None:
        assert _parse_patches({}) == []


# ---------------------------------------------------------------------------
# Apply Patches
# ---------------------------------------------------------------------------
class TestApplyPatches:
    def test_single_patch(self) -> None:
        content = "林凡大笑起来，然后离开了。"
        patches = [
            Patch(issue_id="i1", original_text="大笑起来", revised_text="微微一笑", location="")
        ]
        result, applied = _apply_patches(content, patches)
        assert result == "林凡微微一笑，然后离开了。"
        assert len(applied) == 1

    def test_multiple_patches_backwards(self) -> None:
        content = "A 和 B 和 C"
        patches = [
            Patch(issue_id="i1", original_text="A", revised_text="X", location=""),
            Patch(issue_id="i2", original_text="B", revised_text="Y", location=""),
        ]
        result, applied = _apply_patches(content, patches)
        assert result == "X 和 Y 和 C"
        assert len(applied) == 2

    def test_no_match_keeps_original(self) -> None:
        content = "原文内容"
        patches = [Patch(issue_id="i1", original_text="不存在", revised_text="替换", location="")]
        result, applied = _apply_patches(content, patches)
        assert result == "原文内容"
        assert len(applied) == 0

    def test_empty_patches(self) -> None:
        content = "原文"
        result, applied = _apply_patches(content, [])
        assert result == "原文"
        assert applied == []

    def test_overlapping_patches(self) -> None:
        """从后往前应用时，后面的 patch 先替换，前面的 patch 在已修改的字符串上继续."""
        content = "abc def ghi"
        patches = [
            Patch(issue_id="i1", original_text="abc", revised_text="XXX", location=""),
            Patch(issue_id="i2", original_text="def", revised_text="YYY", location=""),
        ]
        result, applied = _apply_patches(content, patches)
        assert result == "XXX YYY ghi"
        assert len(applied) == 2

    def test_collision_skipped(self) -> None:
        """重叠 patch 碰撞时应跳过，避免错误替换."""
        content = "abc def ghi"
        patches = [
            Patch(issue_id="i1", original_text="abc def", revised_text="XXX", location=""),
            Patch(issue_id="i2", original_text="def ghi", revised_text="YYY", location=""),
        ]
        result, applied = _apply_patches(content, patches)
        # i2 位置更靠后，先应用；i1 与 i2 重叠，应被跳过
        assert "YYY" in result
        assert "XXX" not in result
        assert len(applied) == 1
        assert applied[0].issue_id == "i2"

    def test_same_text_collision(self) -> None:
        """相同 original_text 多次出现时，第二个应被跳过（或找不到）."""
        content = "hello world hello"
        patches = [
            Patch(issue_id="i1", original_text="hello", revised_text="XXX", location=""),
            Patch(issue_id="i2", original_text="hello", revised_text="YYY", location=""),
        ]
        result, applied = _apply_patches(content, patches)
        # 两个 patch 在原始文本中都指向最后一个 "hello"
        # 先应用一个后，另一个找不到或被碰撞检测跳过
        assert len(applied) == 1


# ---------------------------------------------------------------------------
# Determine Issues Fixed
# ---------------------------------------------------------------------------
class TestDetermineIssuesFixed:
    def test_all_fixed(self) -> None:
        issues = [_make_review_issue("i1"), _make_review_issue("i2")]
        patches = [
            Patch(issue_id="i1", original_text="a", revised_text="b", location=""),
            Patch(issue_id="i2", original_text="c", revised_text="d", location=""),
        ]
        fixed, remaining = _determine_issues_fixed(patches, issues)
        assert fixed == ["i1", "i2"]
        assert remaining == []

    def test_partial_fixed(self) -> None:
        issues = [_make_review_issue("i1"), _make_review_issue("i2")]
        patches = [Patch(issue_id="i1", original_text="a", revised_text="b", location="")]
        fixed, remaining = _determine_issues_fixed(patches, issues)
        assert fixed == ["i1"]
        assert remaining == ["i2"]

    def test_none_fixed(self) -> None:
        issues = [_make_review_issue("i1")]
        patches: list[Patch] = []
        fixed, remaining = _determine_issues_fixed(patches, issues)
        assert fixed == []
        assert remaining == ["i1"]


# ---------------------------------------------------------------------------
# Build Revision Output
# ---------------------------------------------------------------------------
class TestBuildRevisionOutput:
    def test_full_output(self) -> None:
        data = {
            "patches": [
                {"issue_id": "i1", "original_text": "a", "revised_text": "b", "location": "第1段"}
            ]
        }
        issues = [_make_review_issue("i1")]
        output = _build_revision_output(data, issues, "xa", "version_new")
        assert output.new_version_id == "version_new"
        assert len(output.patches_applied) == 1
        assert output.issues_fixed == ["i1"]
        assert output.issues_remaining == []

    def test_empty_patches(self) -> None:
        data = {"patches": []}
        issues = [_make_review_issue("i1")]
        output = _build_revision_output(data, issues, "xa", "v_new")
        assert output.patches_applied == []
        assert output.issues_fixed == []
        assert output.issues_remaining == ["i1"]

    def test_patch_not_found_not_marked_fixed(self) -> None:
        """LLM 返回了 patch 但 original_text 不在正文中，issue 不应标记为 fixed."""
        data = {
            "patches": [
                {
                    "issue_id": "i1",
                    "original_text": "这段文字不存在",
                    "revised_text": "替换",
                    "location": "第1段",
                }
            ]
        }
        issues = [_make_review_issue("i1")]
        output = _build_revision_output(data, issues, "实际正文内容", "v_new")
        assert output.patches_applied == []
        assert output.issues_fixed == []
        assert output.issues_remaining == ["i1"]


# ---------------------------------------------------------------------------
# Integration Tests
# ---------------------------------------------------------------------------
class TestRunRevision:
    async def test_full_flow(self) -> None:
        content = "林凡大笑起来，然后离开了。"
        issue = _make_review_issue("i1", "critical", "patch", "大笑起来")
        report = _make_merged_report(issue)
        llm_response = _make_valid_llm_response(
            content="林凡微微一笑，然后离开了。",
            patches=[
                {
                    "issue_id": "i1",
                    "original_text": "大笑起来",
                    "revised_text": "微微一笑",
                    "location": "第1段",
                }
            ],
        )
        with patch("songyan.agents.revision_handler.call_llm", return_value=llm_response):
            result, revised_content = await run_revision(content, report)
        assert len(result.patches_applied) == 1
        assert result.issues_fixed == ["i1"]
        assert result.issues_remaining == []
        assert "微微一笑" in revised_content

    async def test_no_patchable_issues(self) -> None:
        report = _make_merged_report()
        result, revised = await run_revision("正文", report)
        assert result.patches_applied == []
        assert result.issues_fixed == []
        assert revised == "正文"

    async def test_invalid_json_raises(self) -> None:
        content = "正文"
        issue = _make_review_issue("i1", "critical", "patch")
        report = _make_merged_report(issue)
        with patch(
            "songyan.agents.revision_handler.call_llm", return_value="不是 JSON"
        ), pytest.raises(LLMResponseParseError):
            await run_revision(content, report)

    async def test_with_protected_fissures(self) -> None:
        content = "林凡放下了剑。"
        issue = _make_review_issue("i1", "critical", "patch", "放下了剑")
        report = _make_merged_report(issue)
        literary = LiteraryAuditResult(
            observations=[
                LiteraryObservation(
                    observation_id="o1",
                    observation_type="valuable_fissure",
                    description="裂隙",
                    evidence_quote="放下了剑",
                    preserve=True,
                )
            ]
        )
        llm_response = _make_valid_llm_response(
            content="林凡放下了剑。",
            patches=[
                {
                    "issue_id": "i1",
                    "original_text": "放下了剑",
                    "revised_text": "收回了手",
                    "location": "第1段",
                }
            ],
        )
        with patch("songyan.agents.revision_handler.call_llm", return_value=llm_response):
            result, _ = await run_revision(content, report, literary_result=literary)
        assert len(result.patches_applied) == 1
        # Prompt 中应包含保护内容，但 patch 仍可能被应用（取决于 LLM）

    async def test_temperature_param(self) -> None:
        content = "正文"
        issue = _make_review_issue("i1", "critical", "patch")
        report = _make_merged_report(issue)
        llm_response = _make_valid_llm_response()
        with patch("songyan.agents.revision_handler.call_llm", return_value=llm_response) as mock:
            await run_revision(content, report, temperature=0.4)
        mock.assert_called_once()
        assert mock.call_args[1]["temperature"] == 0.4

    async def test_truncated_content_fallback_to_patches(self) -> None:
        """LLM 返回截断的 content（<50% 原文），但有有效 patches，应 fallback 到 patches."""
        content = "这是一段很长的测试正文，包含很多文字内容。" * 20  # ~520 chars
        issue = _make_review_issue("i1", "critical", "patch", "测试正文")
        report = _make_merged_report(issue)
        # LLM 只返回了截断的 content（<50%），但 patch 是有效的
        llm_response = _make_valid_llm_response(
            content="截断内容",  # 远小于 50%
            patches=[
                {
                    "issue_id": "i1",
                    "original_text": "测试正文",
                    "revised_text": "修改后的正文",
                    "location": "第1段",
                }
            ],
        )
        with patch("songyan.agents.revision_handler.call_llm", return_value=llm_response):
            result, revised_content = await run_revision(content, report)
        # 应使用 patch 应用后的结果（与原文长度相近）
        assert len(revised_content) >= len(content) * 0.5
        assert "修改后的正文" in revised_content
        assert result.issues_fixed == ["i1"]

    async def test_truncated_content_revert_to_original(self) -> None:
        """LLM 返回截断的 content，patches 也无效，应回退到原始内容."""
        content = "这是一段很长的测试正文，包含很多文字内容。" * 20
        issue = _make_review_issue("i1", "critical", "patch", "测试正文")
        report = _make_merged_report(issue)
        # LLM 返回截断 content + 无效的 patch
        llm_response = _make_valid_llm_response(
            content="截断内容",
            patches=[
                {
                    "issue_id": "i1",
                    "original_text": "不存在的文字",
                    "revised_text": "替换",
                    "location": "第1段",
                }
            ],
        )
        with patch("songyan.agents.revision_handler.call_llm", return_value=llm_response):
            result, revised_content = await run_revision(content, report)
        # 应回退到原始内容
        assert revised_content == content
        assert result.issues_fixed == []
        assert result.issues_remaining == ["i1"]

    async def test_llm_content_kept_when_patches_too_short(self) -> None:
        """LLM 返回正常长度的 content，但 patches 应用后太短，应保留 LLM content."""
        content = "这是一段很长的测试正文，包含很多文字内容。" * 20
        issue = _make_review_issue("i1", "critical", "patch", "测试正文")
        report = _make_merged_report(issue)
        # LLM 返回正常 content，patch 会删除大量内容
        llm_response = _make_valid_llm_response(
            content=content.replace("测试正文", "修改后的正文"),  # 正常长度
            patches=[
                {
                    "issue_id": "i1",
                    "original_text": content[:400],  # 匹配大量文字
                    "revised_text": "短",
                    "location": "第1段",
                }
            ],
        )
        with patch("songyan.agents.revision_handler.call_llm", return_value=llm_response):
            result, revised_content = await run_revision(content, report)
        # 应保留 LLM 返回的 content（正常长度），而不是 patch 后的超短结果
        assert len(revised_content) >= len(content) * 0.5
        assert "修改后的正文" in revised_content

    async def test_content_preservation_ratio_normal(self) -> None:
        """正常修订场景，content_preservation_ratio 应为 1.0（内容完整保留）."""
        content = "这是一段很长的测试正文，包含很多文字内容。" * 20
        issue = _make_review_issue("i1", "critical", "patch", "测试正文")
        report = _make_merged_report(issue)
        llm_response = _make_valid_llm_response(
            content=content.replace("测试正文", "修改后的正文"),
            patches=[
                {
                    "issue_id": "i1",
                    "original_text": "测试正文",
                    "revised_text": "修改后的正文",
                    "location": "第1段",
                }
            ],
        )
        with patch("songyan.agents.revision_handler.call_llm", return_value=llm_response):
            result, revised_content = await run_revision(content, report)
        assert result.content_preservation_ratio == 1.0
        assert "修改后的正文" in revised_content

    async def test_content_preservation_ratio_logged(self) -> None:
        """截断场景下 content_preservation_ratio 被正确计算并回退到原始内容."""
        content = "这是一段很长的测试正文，包含很多文字内容。" * 20
        issue = _make_review_issue("i1", "critical", "patch", "测试正文")
        report = _make_merged_report(issue)
        # LLM 返回截断 content，patches 无效 → 触发回退
        llm_response = _make_valid_llm_response(
            content="截断内容",
            patches=[
                {
                    "issue_id": "i1",
                    "original_text": "不存在的文字",
                    "revised_text": "替换",
                    "location": "第1段",
                }
            ],
        )
        with patch("songyan.agents.revision_handler.call_llm", return_value=llm_response):
            result, revised_content = await run_revision(content, report)
        # 回退到原始内容，ratio 应为 1.0
        assert result.content_preservation_ratio == 1.0
        assert revised_content == content
        assert result.issues_fixed == []
        assert result.issues_remaining == ["i1"]

    async def test_previous_issues_injected_into_prompt(self) -> None:
        """068: previous_issues 中的 show-dont-tell evidence 应被注入 prompt."""
        content = "林凡大笑起来，然后离开了。"
        issue = _make_review_issue("i1", "critical", "patch", "大笑起来")
        report = _make_merged_report(issue)

        previous = [
            ReviewIssue(
                issue_id="prev1",
                category=ReviewCategory.SHOW_DONT_TELL,
                severity="major",
                evidence_quote="他感到非常愤怒。",
                evidence_location="第2段",
                issue_description="直接陈述情绪",
            )
        ]

        captured_prompt: str | None = None

        def capture_prompt(prompt: str, **kwargs: Any) -> str:
            nonlocal captured_prompt
            captured_prompt = prompt
            return _make_valid_llm_response(content=content)

        with patch("songyan.agents.revision_handler.call_llm", side_effect=capture_prompt):
            await run_revision(content, report, previous_issues=previous)

        assert captured_prompt is not None
        assert "上一轮审查的具体证据" in captured_prompt
        assert "他感到非常愤怒。" in captured_prompt
        assert "直接陈述情绪" in captured_prompt

    async def test_no_previous_issues_no_injection(self) -> None:
        """068: 不传 previous_issues 时 prompt 不应包含 feedback 段落."""
        content = "林凡大笑起来，然后离开了。"
        issue = _make_review_issue("i1", "critical", "patch", "大笑起来")
        report = _make_merged_report(issue)

        captured_prompt: str | None = None

        def capture_prompt(prompt: str, **kwargs: Any) -> str:
            nonlocal captured_prompt
            captured_prompt = prompt
            return _make_valid_llm_response(content=content)

        with patch("songyan.agents.revision_handler.call_llm", side_effect=capture_prompt):
            await run_revision(content, report)

        assert captured_prompt is not None
        assert "上一轮审查的具体证据" not in captured_prompt


class TestSaveRevisionOutput:
    async def test_creates_revision_version(self) -> None:
        mock_version_db = AsyncMock()
        mock_head_db = AsyncMock()

        output = RevisionOutput(
            new_version_id="vid_old",
            patches_applied=[
                Patch(issue_id="i1", original_text="a", revised_text="b", location="")
            ],
        )
        parent = ChapterVersion(
            version_id="v_old",
            project_id="p1",
            chapter_number=3,
            version_number=1,
            version_type="draft",
        )

        mock_version_db.list_by_chapter.return_value = [parent]
        mock_version_db.get_next_version_number.return_value = 2

        vid = await save_revision_output(
            version_db=mock_version_db,
            head_db=mock_head_db,
            project_id="p1",
            chapter_number=3,
            output=output,
            revised_content="修改后正文",
            parent_version=parent,
        )

        mock_version_db.create.assert_called_once()
        created = mock_version_db.create.call_args[0][0]
        assert created.version_type == "revision"
        assert created.version_number == 2
        assert created.parent_version_id == "v_old"
        assert created.content == "修改后正文"
        assert vid.startswith("rev-")

    async def test_updates_chapter_head(self) -> None:
        mock_version_db = AsyncMock()
        mock_head_db = AsyncMock()

        existing_head = ChapterHead(
            project_id="p1",
            chapter_number=3,
            current_version_id="v_old",
            status="draft",
        )
        mock_head_db.get.return_value = existing_head
        mock_version_db.list_by_chapter.return_value = []

        parent = ChapterVersion(
            version_id="v_old",
            project_id="p1",
            chapter_number=3,
            version_number=1,
            version_type="draft",
        )

        await save_revision_output(
            version_db=mock_version_db,
            head_db=mock_head_db,
            project_id="p1",
            chapter_number=3,
            output=RevisionOutput(new_version_id="vid_old"),
            revised_content="正文",
            parent_version=parent,
        )

        mock_head_db.update.assert_called_once()
        updated = mock_head_db.update.call_args[0][0]
        assert updated.status == "under_review"

    async def test_creates_head_if_none(self) -> None:
        mock_version_db = AsyncMock()
        mock_head_db = AsyncMock()
        mock_head_db.get.return_value = None
        mock_version_db.list_by_chapter.return_value = []

        parent = ChapterVersion(
            version_id="v_old",
            project_id="p1",
            chapter_number=3,
            version_number=1,
            version_type="draft",
        )

        await save_revision_output(
            version_db=mock_version_db,
            head_db=mock_head_db,
            project_id="p1",
            chapter_number=3,
            output=RevisionOutput(new_version_id="vid_old"),
            revised_content="正文",
            parent_version=parent,
        )

        mock_head_db.update.assert_called_once()
        created = mock_head_db.update.call_args[0][0]
        assert created.status == "under_review"


# ---------------------------------------------------------------------------
# 058d: New Issues Detection
# ---------------------------------------------------------------------------
from songyan.agents.revision_handler import _detect_new_issues
from songyan.models import RuleAuditResult


class TestDetectNewIssues:
    """Tests for _detect_new_issues — 058d revision convergence fix."""

    def _make_rule_result(
        self,
        ai_tell_count: int = 0,
        fatigue_word_count: int = 0,
        has_opening_hook: bool = True,
        has_ending_hook: bool = True,
    ) -> RuleAuditResult:
        return RuleAuditResult(
            ai_tell_count=ai_tell_count,
            fatigue_word_count=fatigue_word_count,
            has_opening_hook=has_opening_hook,
            has_ending_hook=has_ending_hook,
        )

    def test_no_issues_when_both_none(self) -> None:
        result = _detect_new_issues(None, None)
        assert result == []

    def test_no_issues_when_original_none(self) -> None:
        revised = self._make_rule_result(ai_tell_count=5)
        result = _detect_new_issues(None, revised)
        assert result == []

    def test_no_issues_when_revised_none(self) -> None:
        original = self._make_rule_result(ai_tell_count=5)
        result = _detect_new_issues(original, None)
        assert result == []

    def test_no_issues_when_no_regression(self) -> None:
        original = self._make_rule_result(
            ai_tell_count=2, fatigue_word_count=3, has_opening_hook=True, has_ending_hook=True
        )
        revised = self._make_rule_result(
            ai_tell_count=2, fatigue_word_count=3, has_opening_hook=True, has_ending_hook=True
        )
        result = _detect_new_issues(original, revised)
        assert result == []

    def test_detects_ai_tell_increase(self) -> None:
        original = self._make_rule_result(ai_tell_count=2)
        revised = self._make_rule_result(ai_tell_count=5)
        result = _detect_new_issues(original, revised)
        assert len(result) == 1
        assert result[0].category == ReviewCategory.SHOW_DONT_TELL
        assert result[0].severity == "major"
        assert "AI" in result[0].issue_description

    def test_detects_fatigue_word_increase(self) -> None:
        original = self._make_rule_result(fatigue_word_count=1)
        revised = self._make_rule_result(fatigue_word_count=4)
        result = _detect_new_issues(original, revised)
        assert len(result) == 1
        assert result[0].category == ReviewCategory.DESCRIPTION_SENSORY
        assert result[0].severity == "major"
        assert "fatigue" in result[0].issue_description.lower() or "疲劳" in result[0].issue_description

    def test_detects_opening_hook_loss(self) -> None:
        original = self._make_rule_result(has_opening_hook=True)
        revised = self._make_rule_result(has_opening_hook=False)
        result = _detect_new_issues(original, revised)
        assert len(result) == 1
        assert result[0].category == ReviewCategory.NARRATIVE_HOOK
        assert result[0].severity == "critical"
        assert "opening" in result[0].issue_description.lower() or "首屏" in result[0].issue_description

    def test_detects_ending_hook_loss(self) -> None:
        original = self._make_rule_result(has_ending_hook=True)
        revised = self._make_rule_result(has_ending_hook=False)
        result = _detect_new_issues(original, revised)
        assert len(result) == 1
        assert result[0].category == ReviewCategory.NARRATIVE_HOOK
        assert result[0].severity == "critical"
        assert "ending" in result[0].issue_description.lower() or "章末" in result[0].issue_description

    def test_detects_multiple_regressions(self) -> None:
        original = self._make_rule_result(
            ai_tell_count=1, fatigue_word_count=1, has_opening_hook=True, has_ending_hook=True
        )
        revised = self._make_rule_result(
            ai_tell_count=3, fatigue_word_count=5, has_opening_hook=False, has_ending_hook=False
        )
        result = _detect_new_issues(original, revised)
        assert len(result) == 4
        categories = {r.category for r in result}
        assert ReviewCategory.SHOW_DONT_TELL in categories
        assert ReviewCategory.DESCRIPTION_SENSORY in categories
        assert ReviewCategory.NARRATIVE_HOOK in categories

    def test_no_false_positive_when_hooks_already_missing(self) -> None:
        original = self._make_rule_result(has_opening_hook=False, has_ending_hook=False)
        revised = self._make_rule_result(has_opening_hook=False, has_ending_hook=False)
        result = _detect_new_issues(original, revised)
        assert result == []


class TestBuildRevisionOutputWithNewIssues:
    """Tests for _build_revision_output with rule results — 058d."""

    def _make_rule_result(
        self,
        ai_tell_count: int = 0,
        fatigue_word_count: int = 0,
        has_opening_hook: bool = True,
        has_ending_hook: bool = True,
    ) -> RuleAuditResult:
        return RuleAuditResult(
            ai_tell_count=ai_tell_count,
            fatigue_word_count=fatigue_word_count,
            has_opening_hook=has_opening_hook,
            has_ending_hook=has_ending_hook,
        )

    def test_with_rule_results_detects_new_issues(self) -> None:
        data = {"patches": []}
        original = self._make_rule_result(ai_tell_count=1)
        revised = self._make_rule_result(ai_tell_count=3)
        output = _build_revision_output(
            data,
            original_issues=[],
            content="正文",
            new_version_id="v2",
            original_rule_result=original,
            revised_rule_result=revised,
        )
        assert len(output.new_issues_introduced) == 1
        assert output.new_issues_introduced[0].category == ReviewCategory.SHOW_DONT_TELL

    def test_without_rule_results_empty_new_issues(self) -> None:
        """向后兼容：不传 rule results 时 new_issues_introduced 为空."""
        data = {"patches": []}
        output = _build_revision_output(
            data,
            original_issues=[],
            content="正文",
            new_version_id="v2",
        )
        assert output.new_issues_introduced == []

    def test_preserves_other_fields_with_rule_results(self) -> None:
        data = {"patches": []}
        issue = _make_review_issue("i1", "major", "patch", "old text")
        original = self._make_rule_result()
        revised = self._make_rule_result()
        output = _build_revision_output(
            data,
            original_issues=[issue],
            content="old text here",
            new_version_id="v2",
            original_rule_result=original,
            revised_rule_result=revised,
        )
        assert output.new_version_id == "v2"
        assert output.issues_remaining == ["i1"]
        assert output.new_issues_introduced == []


# ---------------------------------------------------------------------------
# Task 095: Scene Split / Merge Strategies
# ---------------------------------------------------------------------------
class TestSceneSplitStrategy:
    async def test_scene_split_triggered(self) -> None:
        content = "### Scene 1\n这是一个很长的场景内容。" * 50
        issue = ReviewIssue(
            issue_id="rule-v1-001",
            category=ReviewCategory.NARRATIVE_PACING,
            severity="major",
            evidence_quote="当前仅 1 个场景",
            evidence_location="全章结构",
            issue_description="章节仅有 1 个场景，叙事节奏可能过于集中",
            fix_type="rewrite_scene",
        )
        report = MergedReviewReport(
            chapter_version_id="v1",
            issues=[issue],
        )

        with patch(
            "songyan.agents.revision_handler._handle_scene_shortage",
            return_value="### Scene 1\na\n\n### Scene 2\nb",
        ) as mock_split:
            result, revised = await run_revision(content, report)

        mock_split.assert_called_once()
        assert "### Scene 2" in revised

    async def test_scene_split_not_triggered_without_issue(self) -> None:
        """没有场景结构 issue 时，即使单 scene 也不触发 scene_split."""
        content = "林凡大笑起来，然后离开了。"
        issue = ReviewIssue(
            issue_id="i1",
            category=ReviewCategory.CHARACTER_BEHAVIOR,
            severity="major",
            evidence_quote="大笑起来",
            evidence_location="第2段",
            issue_description="问题描述",
            fix_type="patch",
        )
        report = MergedReviewReport(
            chapter_version_id="v1",
            issues=[issue],
        )

        llm_response = json.dumps(
            {
                "content": "林凡微微一笑，然后离开了。",
                "patches": [
                    {
                        "issue_id": "i1",
                        "original_text": "大笑起来",
                        "revised_text": "微微一笑",
                        "location": "第1段",
                    }
                ],
            },
            ensure_ascii=False,
        )

        with patch(
            "songyan.agents.revision_handler.call_llm", return_value=llm_response
        ) as mock_llm:
            result, revised = await run_revision(content, report)

        # 不应调用 scene_split，而是正常 patch_engine
        mock_llm.assert_called_once()
        assert len(result.patches_applied) == 1


class TestSceneMergeStrategy:
    async def test_scene_merge_triggered(self) -> None:
        # 5 个 scene，每个约 1000 字，总计约 5000 字
        content = (
            "### Scene 1\n" + "正文" * 500 + "\n\n"
            "### Scene 2\n" + "正文" * 500 + "\n\n"
            "### Scene 3\n" + "正文" * 500 + "\n\n"
            "### Scene 4\n" + "正文" * 500 + "\n\n"
            "### Scene 5\n" + "正文" * 500
        )
        issue = ReviewIssue(
            issue_id="rule-v1-001",
            category=ReviewCategory.NARRATIVE_PACING,
            severity="major",
            evidence_quote="当前共 5 个场景",
            evidence_location="全章结构",
            issue_description="章节场景数过多（5 个），可能导致叙事碎片化",
            fix_type="patch",
        )
        report = MergedReviewReport(
            chapter_version_id="v1",
            issues=[issue],
        )

        with patch(
            "songyan.agents.revision_handler._handle_scene_overflow",
            return_value="### Scene 1\na\n\n### Scene 2\nb",
        ) as mock_merge:
            result, revised = await run_revision(
                content, report, word_count_target=3000
            )

        mock_merge.assert_called_once()
        assert "### Scene 2" in revised

    async def test_scene_merge_not_triggered_when_word_count_ok(self) -> None:
        """字数未超标时不触发 scene_merge."""
        # 5 个 scene，但字数只有约 2000 字（< 1.4x target=3000 → 4200）
        content = (
            "### Scene 1\n" + "正文" * 200 + "\n\n"
            "### Scene 2\n" + "正文" * 200 + "\n\n"
            "### Scene 3\n" + "正文" * 200 + "\n\n"
            "### Scene 4\n" + "正文" * 200 + "\n\n"
            "### Scene 5\n" + "正文" * 200
        )
        issue = ReviewIssue(
            issue_id="rule-v1-001",
            category=ReviewCategory.NARRATIVE_PACING,
            severity="major",
            evidence_quote="当前共 5 个场景",
            evidence_location="全章结构",
            issue_description="章节场景数过多（5 个），可能导致叙事碎片化",
            fix_type="patch",
        )
        report = MergedReviewReport(
            chapter_version_id="v1",
            issues=[issue],
        )

        llm_response = json.dumps(
            {"content": content, "patches": []}, ensure_ascii=False
        )

        with patch(
            "songyan.agents.revision_handler.call_llm", return_value=llm_response
        ) as mock_llm:
            result, revised = await run_revision(
                content, report, word_count_target=3000
            )

        # 不应调用 scene_merge，字数未超标
        mock_llm.assert_called_once()
        assert result.patches_applied == []
