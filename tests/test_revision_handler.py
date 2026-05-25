"""Tests for RevisionHandler Agent."""

from __future__ import annotations

import json
from unittest.mock import AsyncMock, patch

import pytest

from songyan.agents.revision_handler import (
    MAX_CONTENT_LENGTH,
    _apply_patches,
    _build_revision_output,
    _determine_issues_fixed,
    _extract_protected_fissures,
    _filter_patchable_issues,
    _parse_patches,
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
        long_content = "a" * (MAX_CONTENT_LENGTH + 1000)
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
        result = _apply_patches(content, patches)
        assert result == "林凡微微一笑，然后离开了。"

    def test_multiple_patches_backwards(self) -> None:
        content = "A 和 B 和 C"
        patches = [
            Patch(issue_id="i1", original_text="A", revised_text="X", location=""),
            Patch(issue_id="i2", original_text="B", revised_text="Y", location=""),
        ]
        result = _apply_patches(content, patches)
        assert result == "X 和 Y 和 C"

    def test_no_match_keeps_original(self) -> None:
        content = "原文内容"
        patches = [Patch(issue_id="i1", original_text="不存在", revised_text="替换", location="")]
        result = _apply_patches(content, patches)
        assert result == "原文内容"

    def test_empty_patches(self) -> None:
        content = "原文"
        assert _apply_patches(content, []) == "原文"

    def test_overlapping_patches(self) -> None:
        """从后往前应用时，后面的 patch 先替换，前面的 patch 在已修改的字符串上继续."""
        content = "abc def ghi"
        patches = [
            Patch(issue_id="i1", original_text="abc", revised_text="XXX", location=""),
            Patch(issue_id="i2", original_text="def", revised_text="YYY", location=""),
        ]
        result = _apply_patches(content, patches)
        assert result == "XXX YYY ghi"


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
        output = _build_revision_output(data, issues, "version_new")
        assert output.new_version_id == "version_new"
        assert len(output.patches_applied) == 1
        assert output.issues_fixed == ["i1"]
        assert output.issues_remaining == []

    def test_empty_patches(self) -> None:
        data = {"patches": []}
        issues = [_make_review_issue("i1")]
        output = _build_revision_output(data, issues, "v_new")
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
