# src/songyan/literary_optimization/base.py
from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Any


@dataclass
class LiteraryContext:
    """Strategy 可读上下文 — 按需填充，Strategy 不应强依赖任何字段."""

    project_id: str = ""
    chapter_number: int = 0
    mode_id: str = ""
    characters: list[Any] = field(default_factory=list)
    creative_brief: Any | None = None
    chapter_goal: Any | None = None
    project_setting: Any | None = None


@dataclass
class LiteraryOptimizationResult:
    """Strategy 输出 — prompt 片段、检测规则、修订触发条件."""

    prompt_fragments: dict[str, list[str]] = field(default_factory=dict)
    audit_rules: list[dict[str, Any]] = field(default_factory=list)
    revision_hints: list[str] = field(default_factory=list)


class LiteraryOptimizationStrategy(ABC):
    """文学性/可读性优化策略基类."""

    @property
    @abstractmethod
    def strategy_id(self) -> str: ...

    @property
    @abstractmethod
    def applicable_agents(self) -> list[str]: ...

    @abstractmethod
    def apply(self, context: LiteraryContext) -> LiteraryOptimizationResult: ...
