"""Narrative skeleton models — 自顶向下叙事规划（V6 阶段 0 / Task 141）.

区别于回顾型的 ``ArcSummary`` / ``OpenThread``（``models/context.py``）：本模块的
``StoryOutline`` / ``ArcPlan`` / ``PlotThread`` 是 **前置规划实体**，用于让 GoalPlanner
从全书大纲/弧规划派生章节目标，并追踪线索的开启-兑现生命周期。
"""

from __future__ import annotations

from datetime import datetime
from typing import Literal

from pydantic import BaseModel, Field

PlotThreadStatus = Literal["planned", "opened", "advanced", "resolved", "abandoned"]


class StoryOutline(BaseModel):
    """全书大纲 — 自顶向下叙事骨架的顶层."""

    project_id: str
    core_conflict: str = ""            # 全书核心冲突（一句话）
    mainline_synopsis: str = ""        # 主线梗概（~300 字）
    themes: list[str] = Field(default_factory=list)
    intended_ending: str = ""          # 预期结局方向
    created_at: datetime = Field(default_factory=datetime.now)
    updated_at: datetime = Field(default_factory=datetime.now)


class ArcPlan(BaseModel):
    """弧规划 — 前置规划（区别于回顾型 ArcSummary）."""

    arc_id: str
    project_id: str
    arc_index: int = Field(ge=0)       # 第几个弧
    start_chapter: int = Field(ge=1)
    end_chapter: int = Field(ge=1)
    arc_goal: str = ""                 # 本弧要达成的叙事目标
    threads_to_open: list[str] = Field(default_factory=list)   # 应开启的 thread_id
    threads_to_resolve: list[str] = Field(default_factory=list)  # 应收束的 thread_id
    is_mainline: bool = False          # 是否主线弧（T1 判据依赖）
    created_at: datetime = Field(default_factory=datetime.now)


class PlotThread(BaseModel):
    """剧情线索 — 规划实体，有生命周期状态机."""

    thread_id: str
    project_id: str
    title: str = ""
    description: str = ""
    is_mainline: bool = False          # 主线线索（T1 判据依赖）
    opened_chapter: int | None = None  # 实际开启章（opened 时写入）
    expected_resolve_arc: int | None = None  # 预期收束弧 arc_index
    status: PlotThreadStatus = "planned"
    last_status_chapter: int | None = None    # 最近一次状态变更章
    last_status_version_id: str | None = None  # 变更来源 version（T1 可追溯要求）
    created_at: datetime = Field(default_factory=datetime.now)
    updated_at: datetime = Field(default_factory=datetime.now)
