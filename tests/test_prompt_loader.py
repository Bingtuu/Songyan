"""Tests for Craft Card PromptLoader."""

from __future__ import annotations

from typing import Any

import pytest

from songyan.prompts import get_prompt_loader, reset_prompt_loader
from songyan.prompts._models import CraftCard, CraftCardMetadata, CraftCardSection


class TestPromptLoaderBasics:
    """Basic loading and rendering tests."""

    def test_load_writer_card(self) -> None:
        reset_prompt_loader()
        loader = get_prompt_loader()
        card = loader.load_card("writer")
        assert card.metadata.agent == "writer"
        # # Writer 当前默认版本为 1.1.0（Task 121r），但 1.2.0 已注册。
        assert card.metadata.version in ("1.0.7", "1.0.8", "1.0.9", "1.1.0", "1.2.0")
        assert len(card.sections) == 10  # 1.1.0: 9 original + scene_interaction (170f)

    def test_load_goal_planner_card(self) -> None:
        reset_prompt_loader()
        loader = get_prompt_loader()
        card = loader.load_card("goal_planner")
        assert card.metadata.agent == "goal_planner"
        assert card.metadata.name == "章节目标制定"
        assert "目标规划师" in card.system_prompt

    def test_load_nonexistent_agent_raises(self) -> None:
        reset_prompt_loader()
        loader = get_prompt_loader()
        with pytest.raises(KeyError):
            loader.load_card("nonexistent_agent")

    def test_list_versions(self) -> None:
        reset_prompt_loader()
        loader = get_prompt_loader()
        versions = loader.list_versions("writer")
        # # Writer 当前保留 7 个版本（1.0.5 ~ 1.2.0）
        assert len(versions) == 7
        assert versions[0].version == "1.0.5"
        assert versions[1].version == "1.0.6"
        assert versions[2].version == "1.0.7"
        assert versions[3].version == "1.0.8"
        assert versions[4].version == "1.0.9"
        assert versions[5].version == "1.1.0"
        assert versions[6].version == "1.2.0"

    def test_list_versions_nonexistent_agent_raises(self) -> None:
        reset_prompt_loader()
        loader = get_prompt_loader()
        with pytest.raises(KeyError):
            loader.list_versions("nonexistent_agent")


def _writer_vars(**overrides: Any) -> dict[str, Any]:
    """生成 writer card 渲染所需的全部必需变量（空字符串兜底）."""
    defaults = {
        "chapter_number": 1,
        "chapter_type": "开篇",
        "word_count_target": 3000,
        "target_events": "",
        "emotional_arc": "",
        "hooks": "",
        "obligations": "",
        "creative_intent": "",
        "required_tensions": "",
        "forbidden_patterns": "",
        "allowed_fissures": "",
        "style_constraints": "",
        "reader_contract": "",
        "hard_constraints": "",
        "character_states": "",
        "recent_plot": "",
        "foreshadowing": "",
        "genre_rules": "",
        "mode_rules": "",
    }
    defaults.update(overrides)
    return defaults


class TestRenderCard:
    """Tests for render_card."""

    def test_render_with_variables(self) -> None:
        reset_prompt_loader()
        loader = get_prompt_loader()
        card = loader.load_card("writer")
        rendered = loader.render_card(
            card,
            _writer_vars(chapter_number=5, chapter_type="高潮"),
        )
        assert "第 5 章" in rendered.full_prompt or "5" in rendered.full_prompt
        assert rendered.active_sections
        assert "paragraph_rhythm" in rendered.active_sections

    def test_render_tags_filter_conditional_sections(self) -> None:
        reset_prompt_loader()
        loader = get_prompt_loader()
        card = loader.load_card("writer")

        # Without tags: golden_opening should NOT be active
        rendered_no_tags = loader.render_card(
            card, _writer_vars(chapter_number=1, chapter_type="开篇")
        )
        assert "golden_opening" not in rendered_no_tags.active_sections

        # With chapter_early tag: golden_opening SHOULD be active
        rendered_with_tags = loader.render_card(
            card,
            _writer_vars(chapter_number=1, chapter_type="开篇"),
            tags=["chapter_early"],
        )
        assert "golden_opening" in rendered_with_tags.active_sections

    def test_render_sections_sorted_by_weight(self) -> None:
        reset_prompt_loader()
        loader = get_prompt_loader()
        card = loader.load_card("writer")
        rendered = loader.render_card(card, _writer_vars())
        # All unconditional sections should be present
        unconditional = [s.id for s in card.sections if not s.tags]
        for sid in unconditional:
            assert sid in rendered.active_sections

    def test_render_content_follows_weight_order(self) -> None:
        card = CraftCard(
            metadata=CraftCardMetadata(agent="test", version="1.0.0"),
            sections=[
                CraftCardSection(
                    id="low",
                    name="Low",
                    content="low content",
                    weight=0.5,
                ),
                CraftCardSection(
                    id="high",
                    name="High",
                    content="high content",
                    weight=2.0,
                ),
                CraftCardSection(
                    id="mid",
                    name="Mid",
                    content="mid content",
                    weight=1.0,
                ),
            ],
        )
        reset_prompt_loader()
        loader = get_prompt_loader()
        rendered = loader.render_card(card, {})
        assert rendered.active_sections == ["high", "mid", "low"]
        assert rendered.sections_content.index("high content") < rendered.sections_content.index(
            "mid content"
        )
        assert rendered.sections_content.index("mid content") < rendered.sections_content.index(
            "low content"
        )

    def test_render_caches_result(self) -> None:
        reset_prompt_loader()
        loader = get_prompt_loader()
        card = loader.load_card("writer")

        rendered1 = loader.render_card(card, _writer_vars())
        rendered2 = loader.render_card(card, _writer_vars())
        assert rendered1.full_prompt == rendered2.full_prompt

    def test_render_different_tags_bypass_cache(self) -> None:
        reset_prompt_loader()
        loader = get_prompt_loader()
        card = loader.load_card("writer")

        rendered1 = loader.render_card(card, _writer_vars())
        rendered2 = loader.render_card(
            card, _writer_vars(), tags=["chapter_early"]
        )
        assert rendered1.full_prompt != rendered2.full_prompt


class TestGetActiveSections:
    """Tests for get_active_sections."""

    def test_unconditional_sections_always_active(self) -> None:
        reset_prompt_loader()
        loader = get_prompt_loader()
        card = loader.load_card("writer")
        active = loader.get_active_sections(card)
        assert "paragraph_rhythm" in active  # no tags

    def test_conditional_section_with_matching_tag(self) -> None:
        reset_prompt_loader()
        loader = get_prompt_loader()
        card = loader.load_card("writer")
        active = loader.get_active_sections(card, tags=["chapter_early"])
        assert "golden_opening" in active

    def test_conditional_section_without_tag_inactive(self) -> None:
        reset_prompt_loader()
        loader = get_prompt_loader()
        card = loader.load_card("writer")
        active = loader.get_active_sections(card)
        assert "golden_opening" not in active

    def test_sorted_by_descending_weight(self) -> None:
        card = CraftCard(
            metadata=CraftCardMetadata(agent="test", version="1.0.0"),
            sections=[
                CraftCardSection(id="low", weight=0.5),
                CraftCardSection(id="high", weight=2.0),
                CraftCardSection(id="mid", weight=1.0),
            ],
        )
        reset_prompt_loader()
        loader = get_prompt_loader()
        active = loader.get_active_sections(card)
        assert active == ["high", "mid", "low"]


class TestSingleton:
    """Tests for module-level singleton."""

    def test_get_prompt_loader_returns_same_instance(self) -> None:
        reset_prompt_loader()
        loader1 = get_prompt_loader()
        loader2 = get_prompt_loader()
        assert loader1 is loader2

    def test_reset_creates_new_instance(self) -> None:
        reset_prompt_loader()
        loader1 = get_prompt_loader()
        reset_prompt_loader()
        loader2 = get_prompt_loader()
        assert loader1 is not loader2


class TestAgentIntegration:
    """Verify that Agent prompts contain craft card content."""

    def test_writer_prompt_contains_section_content(self) -> None:
        reset_prompt_loader()
        loader = get_prompt_loader()
        card = loader.load_card("writer")
        rendered = loader.render_card(
            card,
            _writer_vars(chapter_number=1, chapter_type="开篇"),
            tags=["chapter_early"],
        )
        assert "黄金开篇" in rendered.full_prompt
        assert "段落节奏" in rendered.full_prompt
        assert "Show Don't Tell" in rendered.full_prompt

    def test_llm_auditor_prompt_loaded_from_card(self) -> None:
        reset_prompt_loader()
        loader = get_prompt_loader()
        card = loader.load_card("llm_auditor")
        assert "语义审查" in card.system_prompt
        assert "12 个维度" in card.system_prompt

