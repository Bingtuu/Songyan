"""Tests for Writer Agent."""

from __future__ import annotations

from unittest.mock import AsyncMock, patch

from songyan.agents.writer import (
    _count_chinese_words,
    _extract_body,
    _parse_scenes,
    _render_prompt,
    write_chapter,
)
from songyan.models import (
    ChapterGoal,
    ChapterHead,
    ChapterSummary,
    ChapterVersion,
    CharacterStateSnapshot,
    ContextPackage,
    CreativeBrief,
    ForeshadowingItem,
    GenreRules,
    HardConstraint,
    ModeRules,
    RecentPlot,
    SoftReference,
    Tension,
)

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------
_MISSING = object()


def _make_context_package(
    creative_brief: CreativeBrief | None | object = _MISSING,
    **overrides: object,
) -> ContextPackage:
    goal = ChapterGoal(
        chapter_number=1,
        previous_summary="上一章结尾",
        target_events=["事件A", "事件B"],
        emotional_arc="紧张→爆发",
        hooks=["剑灵开口说话"],
        obligations=["兑现母亲遗愿"],
        word_count_target=3000,
        chapter_type="战斗",
    )
    if creative_brief is _MISSING:
        brief: CreativeBrief | None = CreativeBrief(
            mode_id="webnovel",
            chapter_goal=goal,
            creative_intent="让读者感受到爽感",
            required_tensions=[
                Tension(
                    tension_id="t1",
                    description="实力差距",
                    tension_type="power_imbalance",
                    intensity=0.8,
                )
            ],
            forbidden_patterns=["不要冷笑", "不要嘴角勾起"],
            allowed_fissures=["人物做出不合逻辑的选择"],
            style_constraints=["对话简短有力"],
            reader_contract="读者应该感到振奋",
        )
    else:
        brief = creative_brief  # type: ignore[assignment]
    return ContextPackage(
        chapter_goal=goal,
        creative_brief=brief,
        hard_constraints=[
            HardConstraint(type="obligation", description="兑现母亲遗愿", source="goal"),
            HardConstraint(type="taboo", description="绿帽", source="genre"),
        ],
        character_states=[
            CharacterStateSnapshot(
                character_id="c1",
                name="林凡",
                current_location="天剑峰",
                emotional_state="愤怒",
                importance_score=1.0,
            )
        ],
        recent_plot=RecentPlot(
            summaries=[ChapterSummary(chapter_number=1, summary="第一章", key_events=["事件1"])],
            last_chapter_ending="主角拔出剑",
            open_threads=["剑灵身份"],
        ),
        foreshadowing=[
            ForeshadowingItem(
                foreshadowing_id="fs1",
                description="神秘老人",
                planted_in_chapter=1,
                status="planted",
            )
        ],
        soft_references=[
            SoftReference(type="world_setting", content="玄天剑设定", relevance_score=0.7)
        ],
        genre_rules=GenreRules(
            genre_id="xuanhuan",
            writer_rules=["对话简短"],
            fatigue_words=["冷笑"],
            pacing_rule="每章一个小高潮",
        ),
        mode_rules=ModeRules(
            mode_id="webnovel",
            tolerance_max_ai_tells=2.0,
            tolerance_max_fatigue_words=3.0,
        ),
        **overrides,  # type: ignore[arg-type]
    )


# ---------------------------------------------------------------------------
# Prompt Rendering Tests
# ---------------------------------------------------------------------------
class TestRenderPrompt:
    def test_renders_chapter_number(self) -> None:
        ctx = _make_context_package()
        prompt = _render_prompt(ctx)
        assert "第 1 章" in prompt or "1" in prompt

    def test_renders_target_events(self) -> None:
        ctx = _make_context_package()
        prompt = _render_prompt(ctx)
        assert "事件A" in prompt
        assert "事件B" in prompt

    def test_renders_creative_intent(self) -> None:
        ctx = _make_context_package()
        prompt = _render_prompt(ctx)
        assert "让读者感受到爽感" in prompt

    def test_renders_tensions(self) -> None:
        ctx = _make_context_package()
        prompt = _render_prompt(ctx)
        assert "实力差距" in prompt
        assert "power_imbalance" in prompt

    def test_renders_forbidden_patterns(self) -> None:
        ctx = _make_context_package()
        prompt = _render_prompt(ctx)
        assert "不要冷笑" in prompt

    def test_renders_hard_constraints(self) -> None:
        ctx = _make_context_package()
        prompt = _render_prompt(ctx)
        assert "兑现母亲遗愿" in prompt
        assert "[obligation]" in prompt

    def test_renders_character_states(self) -> None:
        ctx = _make_context_package()
        prompt = _render_prompt(ctx)
        assert "林凡" in prompt
        assert "天剑峰" in prompt
        assert "愤怒" in prompt

    def test_renders_recent_plot(self) -> None:
        ctx = _make_context_package()
        prompt = _render_prompt(ctx)
        assert "主角拔出剑" in prompt
        assert "剑灵身份" in prompt

    def test_renders_foreshadowing(self) -> None:
        ctx = _make_context_package()
        prompt = _render_prompt(ctx)
        assert "神秘老人" in prompt

    def test_renders_genre_rules(self) -> None:
        ctx = _make_context_package()
        prompt = _render_prompt(ctx)
        assert "每章一个小高潮" in prompt

    def test_renders_mode_rules(self) -> None:
        ctx = _make_context_package()
        prompt = _render_prompt(ctx)
        assert "AI腔容忍" in prompt or "2.0" in prompt

    def test_no_creative_brief(self) -> None:
        ctx = _make_context_package(creative_brief=None)
        prompt = _render_prompt(ctx)
        assert "（无）" in prompt
        assert "让读者感受到爽感" not in prompt

    def test_loads_template_from_file(self) -> None:
        ctx = _make_context_package()
        prompt = _render_prompt(ctx)
        # 文件模板包含 "小说写作专家"
        assert "小说写作专家" in prompt

    def test_human_instruction_type_field_renders_action_label(self) -> None:
        ctx = _make_context_package(
            human_instructions=[
                {
                    "instruction_id": "inst-old",
                    "gate_type": "audit_report",
                    "type": "rewrite",
                    "content": "按人工意见重写冲突场景",
                }
            ]
        )
        prompt = _render_prompt(ctx)
        assert "- [rewrite] 按人工意见重写冲突场景" in prompt
        assert "- []" not in prompt

    def test_human_instruction_action_field_renders_action_label(self) -> None:
        ctx = _make_context_package(
            human_instructions=[
                {
                    "instruction_id": "inst-new",
                    "gate_type": "audit_report",
                    "action": "inject",
                    "content": "强化主角对黑匣子的执念",
                }
            ]
        )
        prompt = _render_prompt(ctx)
        assert "- [inject] 强化主角对黑匣子的执念" in prompt


# ---------------------------------------------------------------------------
# Scene Parsing Tests
# ---------------------------------------------------------------------------
class TestParseScenes:
    def test_no_scene_markers(self) -> None:
        text = "这是第一章的内容。\n\n第二段内容。"
        scenes = _parse_scenes(text)
        assert len(scenes) == 1
        assert scenes[0]["scene_number"] == 1
        assert "这是第一章的内容" in scenes[0]["content"]

    def _test_single_scene_marker(self) -> None:
        text = "### Scene 1\n场景一内容。"
        scenes = _parse_scenes(text)
        assert len(scenes) == 1
        assert scenes[0]["scene_number"] == 1
        assert "场景一内容" in scenes[0]["content"]

    def test_multiple_scene_markers(self) -> None:
        text = "### Scene 1\n场景一。\n\n### Scene 2\n场景二。"
        scenes = _parse_scenes(text)
        assert len(scenes) == 2
        assert scenes[0]["scene_number"] == 1
        assert scenes[1]["scene_number"] == 2
        assert "场景一" in scenes[0]["content"]
        assert "场景二" in scenes[1]["content"]

    def test_scene_marker_case_insensitive(self) -> None:
        text = "### scene 1\n内容。\n### SCENE 2\n内容2。"
        scenes = _parse_scenes(text)
        assert len(scenes) == 2

    def test_empty_content(self) -> None:
        scenes = _parse_scenes("")
        assert scenes == []

    def test_whitespace_only(self) -> None:
        scenes = _parse_scenes("   \n   ")
        assert scenes == []


# ---------------------------------------------------------------------------
# Word Count Tests
# ---------------------------------------------------------------------------
class TestCountChineseWords:
    def test_empty(self) -> None:
        assert _count_chinese_words("") == 0

    def test_chinese_only(self) -> None:
        assert _count_chinese_words("这是一个测试") == 6

    def test_mixed_text(self) -> None:
        # 中文 4 字 + 英文 1 词
        count = _count_chinese_words("这是test文本")
        assert count == 5

    def test_english_only(self) -> None:
        assert _count_chinese_words("Hello world") == 2

    def test_numbers(self) -> None:
        assert _count_chinese_words("123 456") == 2

    def test_punctuation_not_counted(self) -> None:
        assert _count_chinese_words("你好，世界！") == 4


# ---------------------------------------------------------------------------
# Body Extraction Tests
# ---------------------------------------------------------------------------
class TestExtractBody:
    def test_plain_text(self) -> None:
        assert _extract_body("正文内容") == "正文内容"

    def test_strips_code_block(self) -> None:
        text = "```markdown\n正文内容\n```"
        assert _extract_body(text) == "正文内容"

    def test_strips_code_block_no_lang(self) -> None:
        text = "```\n正文内容\n```"
        assert _extract_body(text) == "正文内容"

    def test_strips_prefix(self) -> None:
        text = "以下是第1章正文：\n\n正文内容"
        result = _extract_body(text)
        assert "正文内容" in result
        assert "以下是" not in result

    def test_strips_suffix(self) -> None:
        text = "正文内容\n\n完"
        result = _extract_body(text)
        assert "正文内容" in result

    def test_mixed_markdown(self) -> None:
        text = "```\n正文\n### Scene 1\n场景\n```"
        result = _extract_body(text)
        assert "正文" in result
        assert "### Scene 1" in result
        assert "```" not in result


# ---------------------------------------------------------------------------
# Integration Tests
# ---------------------------------------------------------------------------
class TestWriteChapter:
    async def test_first_version(self) -> None:
        ctx = _make_context_package()
        mock_version_repo = AsyncMock()
        mock_version_repo.list_by_chapter.return_value = []
        mock_head_repo = AsyncMock()
        mock_head_repo.get.return_value = None

        llm_response = "### Scene 1\n这是第一章的内容。\n\n### Scene 2\n第二段内容。"

        with patch("songyan.agents.writer.call_llm", return_value=llm_response):
            version = await write_chapter(
                db_version=mock_version_repo,
                db_head=mock_head_repo,
                project_id="proj_123",
                context_package=ctx,
                creative_brief_id="brief_001",
            )

        assert version.project_id == "proj_123"
        assert version.chapter_number == 1
        assert version.version_number == 1
        assert version.version_type == "draft"
        assert version.creative_brief_id == "brief_001"
        assert version.word_count > 0
        assert len(version.scenes) >= 2
        assert "这是第一章的内容" in version.content

        mock_version_repo.create.assert_called_once()
        mock_head_repo.update.assert_called_once()
        head_call = mock_head_repo.update.call_args[0][0]
        assert isinstance(head_call, ChapterHead)
        assert head_call.project_id == "proj_123"
        assert head_call.chapter_number == 1
        assert head_call.current_version_id == version.version_id
        assert head_call.status == "draft"

    async def test_second_version(self) -> None:
        ctx = _make_context_package()
        existing_version = ChapterVersion(
            version_id="v-old",
            project_id="proj_123",
            chapter_number=1,
            version_number=1,
        )
        mock_version_repo = AsyncMock()
        mock_version_repo.list_by_chapter.return_value = [existing_version]
        mock_version_repo.get_next_version_number.return_value = 2
        mock_head_repo = AsyncMock()
        mock_head_repo.get.return_value = ChapterHead(
            project_id="proj_123",
            chapter_number=1,
            current_version_id="v-old",
            status="draft",
        )

        llm_response = "### Scene 1\n新内容第一段。\n\n### Scene 2\n新内容第二段。"

        with patch("songyan.agents.writer.call_llm", return_value=llm_response):
            version = await write_chapter(
                db_version=mock_version_repo,
                db_head=mock_head_repo,
                project_id="proj_123",
                context_package=ctx,
            )

        assert version.version_number == 2
        mock_version_repo.create.assert_called_once()
        mock_head_repo.update.assert_called_once()

    async def test_no_creative_brief(self) -> None:
        ctx = _make_context_package(creative_brief=None)
        mock_version_repo = AsyncMock()
        mock_version_repo.list_by_chapter.return_value = []
        mock_head_repo = AsyncMock()
        mock_head_repo.get.return_value = None

        llm_response = "### Scene 1\n正文内容第一段。\n\n### Scene 2\n正文内容第二段。"

        with patch("songyan.agents.writer.call_llm", return_value=llm_response):
            version = await write_chapter(
                db_version=mock_version_repo,
                db_head=mock_head_repo,
                project_id="proj_123",
                context_package=ctx,
            )

        assert version.creative_brief_id is None

    async def test_generation_metadata(self) -> None:
        ctx = _make_context_package()
        ctx.estimated_tokens = 5000
        ctx.budget_used = 0.75

        mock_version_repo = AsyncMock()
        mock_version_repo.list_by_chapter.return_value = []
        mock_head_repo = AsyncMock()
        mock_head_repo.get.return_value = None

        llm_response = "### Scene 1\n正文第一段。\n\n### Scene 2\n正文第二段。"

        with patch("songyan.agents.writer.call_llm", return_value=llm_response):
            version = await write_chapter(
                db_version=mock_version_repo,
                db_head=mock_head_repo,
                project_id="proj_123",
                context_package=ctx,
                context_snapshot_id="ctx-123",
            )

        assert "context_snapshot" in version.generation_metadata
        assert version.generation_metadata["context_snapshot_id"] == "ctx-123"
        assert version.generation_metadata["context_snapshot"]["estimated_tokens"] == 5000
        assert version.generation_metadata["context_snapshot"]["budget_used"] == 0.75
        brief_snapshot = version.generation_metadata["creative_brief_snapshot"]
        assert brief_snapshot["creative_intent"] == "让读者感受到爽感"
        assert brief_snapshot["narrative_fullness"] == 0.0
        assert brief_snapshot["focal_distance"] == "mid"
        assert "prompt_length" in version.generation_metadata
        assert "scenes_count" in version.generation_metadata

    async def test_word_count_accuracy(self) -> None:
        ctx = _make_context_package()
        mock_version_repo = AsyncMock()
        mock_version_repo.list_by_chapter.return_value = []
        mock_head_repo = AsyncMock()
        mock_head_repo.get.return_value = None

        llm_response = (
            "### Scene 1\n这是一段测试正文，包含中文和 English。"
            "\n\n### Scene 2\n第二段测试内容。"
        )

        with patch("songyan.agents.writer.call_llm", return_value=llm_response):
            version = await write_chapter(
                db_version=mock_version_repo,
                db_head=mock_head_repo,
                project_id="proj_123",
                context_package=ctx,
            )

        # Scene 1: 中文字符 13 + 英文词 3 (Scene, 1, English) = 16
        # Scene 2: 中文字符 7 + 英文词 2 (Scene, 2) = 9
        assert version.word_count == 25

    async def test_empty_llm_response_warns(self) -> None:
        """空 LLM 响应不再 raise，而是记录 warning 并继续（scene 不足由后续审查捕获）."""
        ctx = _make_context_package()
        mock_version_repo = AsyncMock()
        mock_version_repo.list_by_chapter.return_value = []
        mock_head_repo = AsyncMock()
        mock_head_repo.get.return_value = None

        with patch("songyan.agents.writer.call_llm", return_value=""):
            version = await write_chapter(
                db_version=mock_version_repo,
                db_head=mock_head_repo,
                project_id="proj_123",
                context_package=ctx,
            )
            # 空响应 → scene 数为 0，但不应抛异常
            assert version.scenes == []
            assert version.word_count == 0

    async def test_word_count_underrun_warns(self) -> None:
        """字数严重不足（超过 ±10% 容差）时应记录 warning."""
        ctx = _make_context_package()
        ctx.chapter_goal.word_count_target = 3000
        mock_version_repo = AsyncMock()
        mock_version_repo.list_by_chapter.return_value = []
        mock_head_repo = AsyncMock()
        mock_head_repo.get.return_value = None

        # 只返回 10 个字，远低于 3000 ±10%，但必须满足至少 2 个场景
        llm_response = "### Scene 1\n很短的内容。\n\n### Scene 2\n第二段。"

        with patch("songyan.agents.writer.call_llm", return_value=llm_response):
            with patch("songyan.agents.writer.logger") as mock_logger:
                version = await write_chapter(
                    db_version=mock_version_repo,
                    db_head=mock_head_repo,
                    project_id="proj_123",
                    context_package=ctx,
                )

        assert version.word_count < 300
        # 验证 word_count_mismatch 被调用过
        mismatch_calls = [
            c for c in mock_logger.warning.call_args_list
            if c.args and c.args[0] == "writer.word_count_mismatch"
        ]
        assert len(mismatch_calls) == 1
        call_kwargs = mismatch_calls[0].kwargs
        assert call_kwargs.get("deviation", 0) > 0.10


# ---------------------------------------------------------------------------
# Hard Truncate Tests (090b-2)
# ---------------------------------------------------------------------------


class TestHardTruncate:
    def test_no_op_when_within_limit(self) -> None:
        from songyan.agents.writer import _hard_truncate_at_boundary
        content = "这是一段内容。"
        result = _hard_truncate_at_boundary(content, 100)
        assert result == content

    def test_truncate_by_paragraph(self) -> None:
        from songyan.agents.writer import _hard_truncate_at_boundary
        content = "第一段。\n\n第二段也有很多字。\n\n第三段同样很多字。"
        result = _hard_truncate_at_boundary(content, 5)
        # 应截断到第一段
        assert "第二段" not in result
        assert _count_chinese_words(result) <= 5

    def test_truncate_by_sentence(self) -> None:
        from songyan.agents.writer import _hard_truncate_at_boundary
        content = "第一句。第二句。第三句。"
        result = _hard_truncate_at_boundary(content, 4)
        # 应截断到第一句或第二句
        assert "第三句" not in result
        assert _count_chinese_words(result) <= 4

    def test_appends_ellipsis_when_truncated(self) -> None:
        from songyan.agents.writer import _hard_truncate_at_boundary
        content = "第一句\n\n第二句很长很长"
        result = _hard_truncate_at_boundary(content, 3)
        assert result.endswith("……")


# ---------------------------------------------------------------------------
# Task 095: Min Scenes Truncation Tests
# ---------------------------------------------------------------------------
class TestEnforceWordCountMinScenes:
    """Tests for Task 095: truncation preserves min_scenes=2."""

    def test_truncate_3_scenes_keeps_min_2(self) -> None:
        from songyan.agents.writer import _enforce_word_count

        # 3 个 scene，每个约 1500 字，总计约 4500 字
        content = (
            "### Scene 1\n" + "正文" * 750 + "\n\n"
            "### Scene 2\n" + "正文" * 750 + "\n\n"
            "### Scene 3\n" + "正文" * 750
        )
        scenes = _parse_scenes(content)
        target = 3000
        current_wc = _count_chinese_words(content)

        result, result_scenes, wc, was_truncated, reason = _enforce_word_count(
            content, scenes, target, current_wc
        )

        assert was_truncated is True
        assert len(result_scenes) >= 2
        assert wc <= int(target * 1.20)
        assert "truncated_before_scene" in reason

    def _test_single_scene_not_protected(self) -> None:
        from songyan.agents.writer import _enforce_word_count

        # 2 个 scene，每个约 2500 字，总计约 5000 字
        # 截断到 Scene 2 开头只剩 1 个 scene，不满足 min_scenes=2
        content = (
            "### Scene 1\n" + "正文" * 1250 + "\n\n"
            "### Scene 2\n" + "正文" * 1250
        )
        scenes = _parse_scenes(content)
        target = 3000
        current_wc = _count_chinese_words(content)

        result, result_scenes, wc, was_truncated, reason = _enforce_word_count(
            content, scenes, target, current_wc
        )

        assert was_truncated is False
        assert result == content
        assert reason == "truncation_would_destroy_structure"

    def _test_single_scene_can_be_truncated(self) -> None:
        from songyan.agents.writer import _enforce_word_count

        content = "正文" * 3000  # 6000 字，1 个 scene
        scenes = _parse_scenes(content)
        target = 3000

        result, result_scenes, wc, was_truncated, reason = _enforce_word_count(
            content, scenes, target, _count_chinese_words(content)
        )

        assert was_truncated is False
        assert reason == "_disallowed_by_scene_structure"

