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

    def test_single_scene_marker(self) -> None:
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

        llm_response = "### Scene 1\n这是第一章的内容。\n\n第二段。"

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
        assert len(version.scenes) >= 1
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
        mock_head_repo = AsyncMock()
        mock_head_repo.get.return_value = ChapterHead(
            project_id="proj_123",
            chapter_number=1,
            current_version_id="v-old",
            status="draft",
        )

        llm_response = "新内容"

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

        llm_response = "正文内容"

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

        llm_response = "正文"

        with patch("songyan.agents.writer.call_llm", return_value=llm_response):
            version = await write_chapter(
                db_version=mock_version_repo,
                db_head=mock_head_repo,
                project_id="proj_123",
                context_package=ctx,
            )

        assert "context_snapshot" in version.generation_metadata
        assert version.generation_metadata["context_snapshot"]["estimated_tokens"] == 5000
        assert version.generation_metadata["context_snapshot"]["budget_used"] == 0.75
        assert "prompt_length" in version.generation_metadata
        assert "scenes_count" in version.generation_metadata

    async def test_word_count_accuracy(self) -> None:
        ctx = _make_context_package()
        mock_version_repo = AsyncMock()
        mock_version_repo.list_by_chapter.return_value = []
        mock_head_repo = AsyncMock()
        mock_head_repo.get.return_value = None

        llm_response = "这是一段测试正文，包含中文和 English。"

        with patch("songyan.agents.writer.call_llm", return_value=llm_response):
            version = await write_chapter(
                db_version=mock_version_repo,
                db_head=mock_head_repo,
                project_id="proj_123",
                context_package=ctx,
            )

        # 中文字符 13 + 英文词 1 = 14
        assert version.word_count == 14

    async def test_empty_llm_response(self) -> None:
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

        assert version.content == ""
        assert version.word_count == 0
        assert version.scenes == []
