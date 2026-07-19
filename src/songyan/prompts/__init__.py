"""Craft Card Prompt system — structured, versioned, observable prompts."""

from typing import Any

from songyan.prompts._models import (
    CraftCard,
    CraftCardMetadata,
    CraftCardSection,
    CraftCardVariable,
    Manifest,
    RenderedPrompt,
    VersionInfo,
)
from songyan.prompts.loader import PromptLoader, get_prompt_loader, reset_prompt_loader


def render_agent_prompt(
    agent: str,
    variables: dict[str, Any],
    *,
    version: str | None = None,
    tags: list[str] | None = None,
) -> str:
    """加载并渲染指定 Agent 的工艺卡，返回完整 prompt 字符串.

    Args:
        agent: Agent 名称（对应包内 ``songyan.prompts/cards`` 子目录）.
        variables: Jinja2 模板变量字典.
        version: 指定版本号，None 时使用最新版本.
        tags: 用于过滤 sections 的标签列表.

    Returns:
        渲染后的完整 prompt 字符串.
    """
    loader = get_prompt_loader()
    card = loader.load_card(agent, version=version)
    rendered = loader.render_card(card, variables, tags=tags)
    return rendered.full_prompt


__all__ = [
    "CraftCard",
    "CraftCardMetadata",
    "CraftCardSection",
    "CraftCardVariable",
    "Manifest",
    "PromptLoader",
    "RenderedPrompt",
    "VersionInfo",
    "get_prompt_loader",
    "render_agent_prompt",
    "reset_prompt_loader",
]
