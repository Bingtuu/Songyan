"""Task 172a.2: GenreRuntimeProfile — Context Diet 2.0 的体裁运行时契约.

把 V7 隐式的科幻默认运行时参数（预算爬坡、可裁分区权重/上限、门禁阈值、
状态压缩、蒸发曲线）显式化为按体裁可插拔的 Profile。

设计要点（三轮审计结论）：
- 真实预算机制是 base_budget + chapter * ramp_per_chapter（非静态 32K），
  溢出发生在不可裁核心（genre_rules 等），因此真正杠杆是 base_budget，
  而非可裁分区权重。
- 两个 1.3 阈值语义不同，必须分成两个字段：
    hard_enforce_ratio       -> 核裁（context_manager.HARD_ENFORCE_THRESHOLD）
    emergency_halt_ratio     -> 门禁 halt（gate_config.context_emergency_budget_ratio_threshold）
- 无 Profile 体裁必须 100% 回退旧行为（scifi baseline），满足 AGENTS.md 硬约束。

字段默认值 = docs/reports/172a.1-scifi-baseline-profile.json（当前代码常量固化）。
"""

from __future__ import annotations

from pydantic import BaseModel, Field


class SettingEvaporationProfile(BaseModel):
    """设定蒸发曲线（setting_evaporator 常量的 Profile 化）."""

    archive_thresholds: dict[str, float] = Field(
        default_factory=lambda: {
            "critical": 0.25,
            "recurring": 0.20,
            "background": 0.15,
            "technical": 0.12,
            "historical": 0.10,
        },
        description="按类别的 resolve_confidence 归档阈值（低于即 archive）",
    )
    time_denominators: dict[str, int] = Field(
        default_factory=lambda: {
            "critical": 100,
            "recurring": 80,
            "background": 25,
            "technical": 30,
            "historical": 20,
        },
        description="按类别的时间衰减分母（越大衰减越慢）",
    )
    legacy_archive_threshold: float = Field(
        default=0.15, description="未分类设定的归档阈值回退值"
    )
    legacy_time_denominator: int = Field(
        default=50, description="未分类设定的时间衰减分母回退值"
    )


class ForeshadowingEvaporationProfile(BaseModel):
    """伏笔紧迫性/回收窗口（_rank_foreshadowings 常量的 Profile 化）."""

    urgency_due_bump: float = Field(default=3.0, description="due 列表伏笔紧迫性加权")
    urgency_overdue_bump: float = Field(default=2.5, description="overdue 伏笔紧迫性加权")
    urgency_within_2_bump: float = Field(
        default=2.0, description="预计 2 章内回收伏笔的紧迫性加权"
    )
    urgency_due_soft: float = Field(default=1.5, description="status=due 的软加权")


class CharacterDecayProfile(BaseModel):
    """角色衰减窗口（劈裂在 context_repo 生命周期 + _assemblers focal 两处）."""

    dormant_window: int = Field(default=30, description="未出场多少章归档为 dormant")
    archive_window: int = Field(default=60, description="未出场多少章归档为 archived")
    functional_window: int = Field(
        default=8, description="功能性角色未出场多少章归为 dormant"
    )
    focal_gaps: dict[str, int] = Field(
        default_factory=lambda: {"full": 3, "compact": 10, "symbol": 30},
        description="档案密度降级的未出场章数阈值（full/compact/symbol，>symbol 则 skip）",
    )


class ContinuityToleranceProfile(BaseModel):
    """连续性审计敏感度（continuity_auditor / _scanners 常量的 Profile 化）."""

    forgotten_threshold: int = Field(
        default=3, description="设定未提及多少章判为 forgotten"
    )
    state_mismatch_window: int = Field(
        default=2, description="状态不一致检测的章节窗口"
    )
    orphaned_thresholds: dict[str, int] = Field(
        default_factory=lambda: {
            "critical": 3,
            "recurring": 4,
            "background": 5,
            "technical": 7,
            "historical": 10,
        },
        description="按类别的孤立设定回收窗口",
    )
    mismatch_tolerance: dict[str, int] = Field(
        default_factory=lambda: {"critical": 0, "major": 1, "minor": 3},
        description="按严重度可容忍的 mismatch 数",
    )


class GenreRuntimeProfile(BaseModel):
    """体裁运行时画像 — Context Diet 2.0 的运行时契约.

    每个体裁一条记录；无记录体裁回退 scifi baseline（load_profile 保证）。
    """

    model_config = {"extra": "ignore"}

    genre: str = Field(description="体裁 id，与 project.genre_id 对齐")
    version: str = Field(default="172a.2", description="Profile 版本号")

    # --- 上下文预算：真实机制 base + chapter * ramp（_assemblers._dynamic_budget） ---
    base_budget: int = Field(default=8000, ge=1000, description="预算基数")
    ramp_per_chapter: int = Field(default=250, ge=0, description="每章预算增量")
    min_budget: int = Field(default=2000, ge=500, description="最小预算下限")

    # --- 可裁分区（仅作用于 character_states/recent_plot/soft_references/foreshadowing） ---
    partition_ratios: dict[str, float] = Field(
        default_factory=lambda: {
            "character_states": 0.30,
            "recent_plot": 0.20,
            "soft_references": 0.15,
            "foreshadowing": 0.10,
        },
        description="可裁分区的预算比例（压不动不可裁核心）",
    )
    max_soft_refs: int = Field(default=10, ge=1)
    max_foreshadowing: int = Field(default=8, ge=1)
    max_character_states: int = Field(default=4, ge=1)
    max_setting_input: int = Field(default=10, ge=1)

    # --- 门禁阈值：两个不同的 1.3 ---
    hard_enforce_ratio: float = Field(
        default=1.3, ge=1.0, description="核裁阈值（context_manager.HARD_ENFORCE_THRESHOLD）"
    )
    emergency_halt_ratio: float = Field(
        default=1.3,
        ge=1.0,
        description="门禁 halt 阈值（gate_config.context_emergency_budget_ratio_threshold）",
    )
    context_emergency_trigger_ratio: float = Field(
        default=1.0, ge=0.5, description="ContextEmergency 触发比例（budget_used >）"
    )

    # --- 状态压缩 / 蒸发 ---
    setting_evaporation: SettingEvaporationProfile = Field(
        default_factory=SettingEvaporationProfile
    )
    foreshadowing_evaporation: ForeshadowingEvaporationProfile = Field(
        default_factory=ForeshadowingEvaporationProfile
    )
    character_decay: CharacterDecayProfile = Field(default_factory=CharacterDecayProfile)
    continuity: ContinuityToleranceProfile = Field(
        default_factory=ContinuityToleranceProfile
    )

    # --- 高级策略开关 ---
    arc_summarization_enabled: bool = Field(default=False)
    outline_dimming_enabled: bool = Field(default=False)

    def dynamic_budget(self, chapter_number: int) -> int:
        """按本 Profile 计算某章的动态预算（等价 _assemblers._dynamic_budget）."""
        return self.base_budget + chapter_number * self.ramp_per_chapter
