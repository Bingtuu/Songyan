"""Task 123: ContextEmergency / health_low 候选硬门禁配置模型.

本模型提供可配置的开关与阈值，支持观测模式（只记录不阻断）和门禁模式
（触发即 pause run）。默认全部开关关闭，确保 V5.0 已验证的 150 章长跑能力
不被误伤。
"""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, Field


class GateConfig(BaseModel):
    """ContextEmergency / health_low 候选硬门禁配置.

    所有 `*_halt` 开关默认关闭；`gate_mode` 默认 `"observe"`，即只记录 gate
    触发事件到 ChapterRunLog，不抛出 AutoHaltException。
    """

    gate_mode: Literal["observe", "enforce"] = Field(
        default="observe",
        description="运行模式：observe 只记录，enforce 触发即 pause run",
    )

    # health_low 门禁
    health_low_gate_enabled: bool = Field(
        default=False,
        description="是否启用 health_low 相关门禁总开关",
    )
    health_low_p1_halt: bool = Field(
        default=False,
        description="任意 P1（state_mismatch / critical orphaned setting）触发门禁",
    )
    health_low_streak_halt: bool = Field(
        default=False,
        description="连续多个审计点 health_low 且达到 P1/P2 阈值时触发门禁",
    )
    health_low_streak_window: int = Field(
        default=3,
        ge=1,
        description="health_low streak 窗口大小（章数）",
    )
    health_low_streak_p1_limit: int = Field(
        default=1,
        ge=0,
        description="窗口内 P1 计数达到该值即触发 streak 门禁",
    )
    health_low_streak_p2_limit: int = Field(
        default=2,
        ge=0,
        description="窗口内 P2 计数达到该值即触发 streak 门禁（需同时无 P1）",
    )
    # Task 127: health_low score halt 复合条件（历史新低 + P1 同步激增）
    health_low_score_halt_enabled: bool = Field(
        default=False,
        description="是否启用 health_low score halt 复合条件门禁",
    )
    health_low_score_halt_window: int = Field(
        default=3,
        ge=1,
        description="计算 P1 近期中位数的审计点窗口大小",
    )
    health_low_score_halt_min_p1: int = Field(
        default=20,
        ge=0,
        description="P1 计数绝对下限，避免均值极小时的小波动",
    )
    health_low_score_halt_anomaly_factor: float = Field(
        default=1.8,
        ge=1.0,
        description="P1 计数超过近期中位数多少倍视为异常",
    )

    # Task 125: 更精细的 health_low 阈值，用于避免对正常叙事累积过度敏感
    health_low_p1_min_absolute: int | None = Field(
        default=None,
        ge=0,
        description="P1 异常门禁的最小绝对触发数量（None 表示不启用绝对阈值）",
    )
    health_low_p1_anomaly_factor: float | None = Field(
        default=None,
        ge=1.0,
        description="P1 异常门禁的滚动中位数倍数（None 表示不启用异常检测）",
    )
    health_low_streak_audit_window: int | None = Field(
        default=None,
        ge=1,
        description="health_low streak 审计点窗口大小（None 表示使用章数窗口）",
    )

    # ContextEmergency 门禁
    context_emergency_gate_enabled: bool = Field(
        default=False,
        description="是否启用 ContextEmergency 相关门禁总开关",
    )
    context_emergency_single_halt: bool = Field(
        default=False,
        description="单章 ContextEmergency 且超预算比例超过阈值时触发门禁",
    )
    context_emergency_budget_ratio_threshold: float = Field(
        default=1.3,
        ge=1.0,
        description="ContextEmergency 单章门禁的 budget_used_before_emergency 阈值",
    )
    context_emergency_failure_halt: bool = Field(
        default=False,
        description="ContextEmergency 导致 settlement/summary 失败时触发门禁",
    )
    context_emergency_streak_halt: bool = Field(
        default=True,
        description="保留已有行为：连续 3 章 ContextEmergency 且伴随降级时触发 AutoHalt",
    )

    def is_enforce(self) -> bool:
        """当前是否为门禁模式."""
        return self.gate_mode == "enforce"

    def is_observe(self) -> bool:
        """当前是否为观测模式."""
        return self.gate_mode == "observe"
