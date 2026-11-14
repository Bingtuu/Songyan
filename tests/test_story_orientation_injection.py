"""task 265 S1: writer 故事定向注入——story_brief / character_roster / world_settings 渲染。"""

from __future__ import annotations

from songyan.agents.writer import _render_prompt
from songyan.prompts import get_prompt_loader
from tests.test_writer import _make_context_package


class TestRenderStoryOrientation:
    def test_story_brief_rendered(self) -> None:
        ctx = _make_context_package(
            story_brief="核心冲突：夜班保安与零点十三分的鬼电梯",
        )
        prompt = _render_prompt(ctx)
        assert "故事定向" in prompt
        assert "夜班保安与零点十三分的鬼电梯" in prompt

    def test_story_brief_absent_shows_placeholder(self) -> None:
        ctx = _make_context_package()
        prompt = _render_prompt(ctx)
        assert "故事定向" not in prompt

    def test_character_roster_rendered(self) -> None:
        ctx = _make_context_package(
            character_roster="- 陈屿（主角）：夜班保安",
        )
        prompt = _render_prompt(ctx)
        assert "角色名册" in prompt
        assert "陈屿（主角）" in prompt

    def test_world_settings_soft_refs_rendered(self) -> None:
        # _make_context_package 自带一条 world_setting 软引用（玄天剑设定）
        ctx = _make_context_package()
        prompt = _render_prompt(ctx)
        assert "世界观设定" in prompt
        assert "玄天剑设定" in prompt


class TestCardVersion:
    def test_writer_card_default_is_1_1_2(self) -> None:
        loader = get_prompt_loader()
        card = loader.load_card("writer")
        manifest_default = loader._manifests["writer"].default_version
        assert manifest_default == "1.1.2"
        assert card.metadata.version == "1.1.2"
