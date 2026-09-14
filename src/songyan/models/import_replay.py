"""V15 Task 236: 导入回放模型."""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, ConfigDict, Field


class ReplayMark(BaseModel):
    """单章回放幂等标记：已应用的 (project_id, chapter_number) 事实."""

    model_config = ConfigDict(extra="forbid")

    project_id: str
    run_id: str
    chapter_number: int = Field(ge=1)
    draft_version_id: str
    accepted_version_id: str
    summary_id: str | None = None
    source_fingerprint: str = Field(min_length=64, max_length=64)


class ChapterReplayOutcome(BaseModel):
    """单章回放结果（含跳过与失败）."""

    model_config = ConfigDict(extra="forbid")

    chapter_number: int
    title: str
    status: Literal["applied", "skipped", "failed"]
    accepted_version_id: str | None = None
    summary_missing_facts: int = 0
    over_token_budget: bool = False
    error: str | None = None
    # Task 238: H 组观察项（report-only，不影响 exit code）
    observation_counts: dict[str, int] = Field(default_factory=dict)
    opening_closing_mismatch: int = 0


class ReplayReport(BaseModel):
    """一次回放 run 的结果汇总."""

    model_config = ConfigDict(extra="forbid")

    run_id: str
    project_id: str
    outcomes: list[ChapterReplayOutcome] = Field(default_factory=list)

    def by_status(self, status: str) -> list[ChapterReplayOutcome]:
        """按状态过滤章节结果."""
        return [o for o in self.outcomes if o.status == status]

    def render_text(self) -> str:
        """渲染纯文本报告（纯内存，不调用 LLM、不访问 DB），供 CLI 直接输出.

        包含：总体统计、失败章清单（含错误与恢复建议）、
        over_token_budget 章清单（F2 观察项）、missing_facts 汇总（观察项）。
        """
        applied = self.by_status("applied")
        skipped = self.by_status("skipped")
        failed = self.by_status("failed")
        lines = [
            f"导入回放报告（run_id={self.run_id}，project_id={self.project_id}）",
            (
                f"章节统计：共 {len(self.outcomes)} 章，"
                f"applied={len(applied)}，skipped={len(skipped)}，failed={len(failed)}"
            ),
        ]
        if failed:
            lines.append("失败章节：")
            for outcome in failed:
                lines.append(
                    f"  - 第 {outcome.chapter_number} 章《{outcome.title}》："
                    f"{outcome.error or '未知错误'}"
                )
            lines.append(
                "  恢复建议：修正后重跑同一命令即可续跑"
                "（已应用章节按幂等标记自动跳过，零重复 LLM 调用）。"
            )
        over_budget = [o for o in self.outcomes if o.over_token_budget]
        if over_budget:
            listing = "、".join(f"第 {o.chapter_number} 章" for o in over_budget)
            lines.append(
                f"超 token 预算章节（F2 观察项，不阻塞回放）：{listing}。"
            )
        total_missing = sum(o.summary_missing_facts for o in self.outcomes)
        if total_missing:
            detail = "、".join(
                f"第 {o.chapter_number} 章 {o.summary_missing_facts} 条"
                for o in self.outcomes
                if o.summary_missing_facts
            )
            lines.append(
                f"摘要 missing_facts 汇总（观察项）：共 {total_missing} 条（{detail}）。"
            )
        # Task 238 H 组观察项：F4 计数（settlement 丢弃/回收）+ F6 跨章 diff。
        # 纯观察，不影响 exit code；全零时整段省略（沿用可选段惯例）。
        observation_totals: dict[str, int] = {}
        observation_by_chapter: dict[str, list[tuple[int, int]]] = {}
        for outcome in self.outcomes:
            for key, value in outcome.observation_counts.items():
                if not value:
                    continue
                observation_totals[key] = observation_totals.get(key, 0) + value
                observation_by_chapter.setdefault(key, []).append(
                    (outcome.chapter_number, value)
                )
        total_mismatch = sum(o.opening_closing_mismatch for o in self.outcomes)
        if observation_totals or total_mismatch:
            lines.append("H 组观察项（report-only，不影响回放结果与验收结论）：")
            for key in sorted(observation_totals):
                detail = "、".join(
                    f"第 {chapter} 章 {count} 次"
                    for chapter, count in observation_by_chapter[key]
                )
                lines.append(f"  {key}：共 {observation_totals[key]} 次（{detail}）")
            if total_mismatch:
                detail = "、".join(
                    f"第 {o.chapter_number} 章 {o.opening_closing_mismatch} 处"
                    for o in self.outcomes
                    if o.opening_closing_mismatch
                )
                lines.append(
                    "  opening_closing_mismatch（F6 数值台账跨章 "
                    f"opening/closing 不一致）：共 {total_mismatch} 处（{detail}）"
                )
        return "\n".join(lines)
