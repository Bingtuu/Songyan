"""Task 171a: tests for _load_literary_keywords wiring (体裁解耦注入的安全回退契约)."""

from __future__ import annotations

import asyncio

from songyan.workflows._nodes import _load_literary_keywords


def test_load_literary_keywords_returns_expected_keys() -> None:
    """契约：始终返回三组关键词键，即便加载失败也回退空集、绝不抛异常/阻断管线。"""
    # 用一个不存在的 project_id：底层查询返回空或异常，都必须安全回退。
    result = asyncio.run(_load_literary_keywords("nonexistent-project-171a"))
    assert set(result.keys()) == {
        "character_names",
        "setting_keywords",
        "non_character_keywords",
    }
    for v in result.values():
        assert isinstance(v, set)


def test_load_literary_keywords_never_raises_on_bad_input() -> None:
    """空/异常 project_id 不得抛异常——保证生成管线不被量具关键词加载中断。"""
    # 空字符串也应安全回退（不抛）。
    result = asyncio.run(_load_literary_keywords(""))
    assert result["character_names"] == set() or isinstance(result["character_names"], set)
