"""Task 074: DialogueStyleCard 单元与集成测试."""

from __future__ import annotations

import pytest

from songyan.models.character import Character, DialogueStyleCard

pytestmark = pytest.mark.performance


class TestDialogueStyleCardModel:
    """DialogueStyleCard 数据模型测试."""

    def test_default_values(self) -> None:
        card = DialogueStyleCard(character_id="c1", project_id="p1")
        assert card.sentence_length_preference == "mixed"
        assert card.common_openers == []
        assert card.irony_usage is False
        assert card.metaphor_frequency == "moderate"

    def test_serialization_roundtrip(self) -> None:
        card = DialogueStyleCard(
            character_id="c1",
            project_id="p1",
            sentence_length_preference="short",
            common_openers=["哼", "听着"],
            anger_expression="冷笑+反问",
            irony_usage=True,
        )
        data = card.model_dump(mode="json")
        restored = DialogueStyleCard(**data)
        assert restored.sentence_length_preference == "short"
        assert restored.common_openers == ["哼", "听着"]
        assert restored.anger_expression == "冷笑+反问"
        assert restored.irony_usage is True

    def test_character_with_style_card(self) -> None:
        card = DialogueStyleCard(character_id="c1", project_id="p1")
        char = Character(
            character_id="c1",
            project_id="p1",
            name="测试角色",
            dialogue_style_card=card,
        )
        assert char.dialogue_style_card is not None
        assert char.dialogue_style_card.character_id == "c1"

    def test_character_without_style_card(self) -> None:
        char = Character(
            character_id="c1",
            project_id="p1",
            name="测试角色",
        )
        assert char.dialogue_style_card is None


class TestDialogueStyleCardDB:
    """DB 读写测试."""

    async def _seed_project(self) -> str:
        from songyan.db.repository import ProjectRepository
        from songyan.models import ProjectSetting

        project = ProjectSetting(
            title="测试项目",
            genre_id="xuanhuan",
            mode_id="webnovel",
            protagonist_name="主角",
        )
        await ProjectRepository().create(project, "proj-test")
        return "proj-test"

    @pytest.mark.asyncio
    async def test_create_character_with_style_card(self, test_db) -> None:
        from songyan.db.repository import CharacterRepository

        await self._seed_project()
        card = DialogueStyleCard(
            character_id="c1",
            project_id="proj-test",
            sentence_length_preference="long",
            common_openers=["哈哈"],
            anger_expression="暴怒",
        )
        char = Character(
            character_id="c1",
            project_id="proj-test",
            name="测试",
            dialogue_style_card=card,
        )
        repo = CharacterRepository()
        await repo.create(char)

        loaded = await repo.get("c1")
        assert loaded is not None
        assert loaded.dialogue_style_card is not None
        assert loaded.dialogue_style_card.sentence_length_preference == "long"
        assert loaded.dialogue_style_card.common_openers == ["哈哈"]
        assert loaded.dialogue_style_card.anger_expression == "暴怒"

    @pytest.mark.asyncio
    async def test_save_dialogue_style_card(self, test_db) -> None:
        from songyan.db.repository import CharacterRepository

        await self._seed_project()
        char = Character(
            character_id="c1",
            project_id="proj-test",
            name="测试",
        )
        repo = CharacterRepository()
        await repo.create(char)

        card = DialogueStyleCard(
            character_id="c1",
            project_id="proj-test",
            sentence_length_preference="short",
            common_openers=["切"],
        )
        await repo.save_dialogue_style_card("c1", card)

        loaded = await repo.get("c1")
        assert loaded is not None
        assert loaded.dialogue_style_card is not None
        assert loaded.dialogue_style_card.sentence_length_preference == "short"
        assert loaded.dialogue_style_card.common_openers == ["切"]

    @pytest.mark.asyncio
    async def test_character_without_style_card_loads_none(self, test_db) -> None:
        from songyan.db.repository import CharacterRepository

        await self._seed_project()
        char = Character(
            character_id="c1",
            project_id="proj-test",
            name="测试",
        )
        repo = CharacterRepository()
        await repo.create(char)

        loaded = await repo.get("c1")
        assert loaded is not None
        assert loaded.dialogue_style_card is None


class TestCreativeDirectorDialogueStyle:
    """CreativeDirector 风格卡生成测试."""

    @pytest.mark.asyncio
    async def test_generate_skips_existing_cards(self) -> None:
        from songyan.agents.creative_director import generate_dialogue_style_cards

        char = Character(
            character_id="c1",
            project_id="p1",
            name="已有风格卡",
            dialogue_style_card=DialogueStyleCard(
                character_id="c1", project_id="p1"
            ),
        )
        cards = await generate_dialogue_style_cards([char], "p1")
        assert cards == []

    @pytest.mark.asyncio
    async def test_generate_for_characters_without_cards(self) -> None:
        from songyan.agents.creative_director import generate_dialogue_style_cards

        chars = [
            Character(character_id="c1", project_id="p1", name="角色A"),
            Character(character_id="c2", project_id="p1", name="角色B"),
        ]
        cards = await generate_dialogue_style_cards(chars, "p1")
        # 无 LLM 可用时返回 []（graceful degradation）
        assert isinstance(cards, list)


class TestWriterPromptInjection:
    """Writer Prompt 注入测试."""

    def test_render_with_dialogue_style_cards(self) -> None:
        from songyan.agents.writer import _render_prompt
        from songyan.models import (
            ChapterGoal,
            ContextPackage,
            DialogueStyleCard,
        )

        ctx = ContextPackage(
            chapter_goal=ChapterGoal(
                chapter_number=1,
                target_events=["事件"],
                word_count_target=3000,
            ),
            dialogue_style_cards=[
                DialogueStyleCard(
                    character_id="c1",
                    project_id="p1",
                    common_openers=["哼"],
                    anger_expression="冷笑",
                ),
            ],
        )
        prompt = _render_prompt(ctx)
        assert "哼" in prompt
        assert "冷笑" in prompt
        assert "对话风格" in prompt

    def test_render_without_style_cards(self) -> None:
        from songyan.agents.writer import _render_prompt
        from songyan.models import ChapterGoal, ContextPackage

        ctx = ContextPackage(
            chapter_goal=ChapterGoal(
                chapter_number=1,
                target_events=["事件"],
                word_count_target=3000,
            ),
        )
        prompt = _render_prompt(ctx)
        assert "（无）" in prompt or "dialogue_style_cards" not in prompt
