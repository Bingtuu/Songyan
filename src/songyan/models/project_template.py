"""ProjectTemplate 数据模型 — 定义项目模板的标准结构."""

from __future__ import annotations

from pathlib import Path
from typing import Any, Literal

from pydantic import BaseModel, Field, PrivateAttr

from songyan.models.narrative import ArcPlan, PlotThread, StoryOutline
from songyan.models.project import ProjectSetting


class TemplateSeedCharacter(BaseModel):
    """模板中的初始角色."""

    name: str
    role: Literal["protagonist", "supporting", "antagonist"] = "supporting"
    age: int | None = None
    description: str = ""
    initial_state: dict[str, Any] = Field(default_factory=dict)


class TemplateSeedSetting(BaseModel):
    """模板中的初始设定."""

    setting_key: str
    setting_name: str
    description: str
    source_quote: str = ""


class TemplateSeedNumericalSystem(BaseModel):
    """模板中的数值体系定义."""

    name: str = ""
    levels: list[str] = Field(default_factory=list)
    base_unit: str = ""
    formula_hint: str = ""


class TemplateSeed(BaseModel):
    """模板种子：角色、设定、数值体系."""

    characters: list[TemplateSeedCharacter] = Field(default_factory=list)
    initial_settings: list[TemplateSeedSetting] = Field(default_factory=list)
    numerical_system: TemplateSeedNumericalSystem | None = None


class ProjectTemplate(BaseModel):
    """项目模板 — 包含项目设定、种子、大纲."""

    id: str
    name: str = ""
    extends: str | None = None
    overwrite: dict[str, Any] = Field(default_factory=dict)
    source_dir: Path | None = None

    project_setting: ProjectSetting
    seed: TemplateSeed = Field(default_factory=TemplateSeed)

    # outline 不直接序列化；加载器解析 outline.json 后通过属性暴露
    _outline: StoryOutline | None = PrivateAttr(default=None)
    _arc_plans: list[ArcPlan] = PrivateAttr(default_factory=list)
    _plot_threads: list[PlotThread] = PrivateAttr(default_factory=list)

    @property
    def has_outline(self) -> bool:
        return self._outline is not None

    @property
    def outline_tuple(self) -> tuple[StoryOutline, list[ArcPlan], list[PlotThread]] | None:
        if self._outline is None:
            return None
        return (self._outline, self._arc_plans, self._plot_threads)

    def set_outline(
        self,
        outline: StoryOutline,
        arc_plans: list[ArcPlan],
        plot_threads: list[PlotThread],
    ) -> None:
        self._outline = outline
        self._arc_plans = arc_plans
        self._plot_threads = plot_threads
