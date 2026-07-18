"""ContinuityHealth — 连续性健康分治理模块.

Task 118: 定义 health_low 分级策略，使 continuity 信号可追踪、可分类、可报告。
"""

from __future__ import annotations

from typing import Any, Literal, cast

from songyan.db.continuity_repo import ContinuityReportRepository
from songyan.db.human_mark_repo import HumanMarkRepository
from songyan.models.continuity import ContinuityReport
from songyan.models.human_mark import HumanMark


def classify_continuity_mark(mark: HumanMark | dict[str, object]) -> Literal["P1", "P2", "P3"]:
    """将连续性标记分类为 P1/P2/P3 严重等级.

    分类规则（Task 118 三档策略）:
    - P1: 涉及角色生死、设定硬冲突、重大时间线冲突（critical category）
    - P2: 同章多次 health_low 或涉及主线事实（recurring category 或 overdue foreshadowing）
    - P3: 低置信或轻微连续性疑点（background/technical/historical category
      或 state_mismatch 观测项）

    Args:
        mark: HumanMark 实例或包含 mark_type/priority/category 等字段的字典

    Returns:
        P1/P2/P3 严重等级
    """
    # 从 HumanMark 实例或字典中提取字段
    if isinstance(mark, HumanMark):
        mark_type = mark.mark_type
        priority = mark.priority
        note = mark.note
        severity = mark.severity
    else:
        raw = mark
        mark_type = cast(
            Literal["setting", "character", "foreshadowing", "item", "custom"],
            raw.get("mark_type", ""),
        )
        priority = cast(int, raw.get("priority", 5))
        note = cast(str, raw.get("note", ""))
        severity = cast(str | None, raw.get("severity"))

    if severity in {"P1", "P2", "P3"}:
        return severity

    # 旧记录兜底：显式 severity 缺失时，沿用旧 character mark 的保守分类。
    if mark_type == "character" or "mismatch" in note.lower() or "矛盾" in note:
        return "P1"

    # forgotten item → P3（尽管 priority=10，不属于 critical）
    if mark_type == "item":
        return "P3"

    # recurring / overdue 关键词 → P2（无论 priority 多高）
    if "recurring" in note.lower() or "overdue" in note.lower() or "逾期" in note:
        return "P2"

    # background/technical/historical → P3（低敏感度，即使 setting + priority >= 10）
    if "background" in note.lower() or "technical" in note.lower() or "historical" in note.lower():
        return "P3"

    # setting 类型：priority >= 10 且无低敏感度关键词 → P1（critical orphaned）
    if mark_type == "setting" and priority >= 10:
        return "P1"

    # priority >= 10 的其他情况 → P3
    if priority >= 10:
        return "P3"

    # priority 9（state_mismatch 生成）→ P1
    if priority == 9:
        return "P1"

    # priority 7-8 → P2
    if 7 <= priority <= 8:
        return "P2"

    # priority < 7 → P3（轻微疑点）
    return "P3"


def classify_health_score(
    health_score: float,
    orphaned_settings: list[object] | None = None,
    state_mismatches: list[object] | None = None,
) -> Literal["P1", "P2", "P3"]:
    """基于 health_score 和构成项分类整体连续性严重等级.

    Args:
        health_score: 0-10 连续性健康分
        orphaned_settings: orphaned settings 列表（用于检测 critical category）
        state_mismatches: state mismatches 列表（有 state_mismatch 即 P1）

    Returns:
        P1/P2/P3 严重等级
    """
    # 有 state_mismatch → P1（无论 health_score 多高）
    if state_mismatches:
        return "P1"

    # 有 critical orphaned → P1（无论 health_score 多高）
    if orphaned_settings:
        for s in orphaned_settings:
            cat = getattr(s, "category", "") if hasattr(s, "category") else ""
            if cat == "critical":
                return "P1"

    if health_score < 3.0:
        return "P1"

    if health_score < 5.0:
        return "P2"

    if health_score < 7.0:
        return "P3"

    return "P3"  # >= 7.0 也在 P3 范围（低于阈值但轻微）


def classify_report(report: ContinuityReport) -> dict[Literal["P1", "P2", "P3"], int]:
    """对 ContinuityReport 中各类问题按严重等级分组计数.

    Returns:
        {"P1": count, "P2": count, "P3": count}
    """
    counts: dict[Literal["P1", "P2", "P3"], int] = {"P1": 0, "P2": 0, "P3": 0}

    for setting in report.orphaned_settings:
        cat = getattr(setting, "category", "background")
        if cat == "critical":
            counts["P1"] += 1
        elif cat == "recurring":
            counts["P2"] += 1
        else:
            counts["P3"] += 1

    for item in report.forgotten_items:
        counts["P3"] += 1

    # Task 171r: state_mismatch 降为 P3（Tier 2 观测）——code-only 启发式
    # 无法区分进展与矛盾，不应参与任何阻塞判定。仍入库、可查、进报告。
    for mismatch in report.state_mismatches:
        counts["P3"] += 1

    for fs in report.overdue_foreshadowings:
        counts["P2"] += 1

    return counts


def count_hard_p1_for_halt(report: ContinuityReport) -> int:
    """计算用于 run-level 硬 halt 的 P1 数——**排除 state_mismatch**（Task 171p2）.

    构念依据：`state_mismatch` 由 `_find_state_mismatches` 的字符串不等启发式产生，
    无法语义区分「角色进展」与「真实矛盾」（Task 171 小窗口实证：Ch3 P1=11/6 全为
    进展被误判）。**真实的语义矛盾由 LLM 一致性审查（coherence_critical/major）在章级
    revision 阻断**，与本 P1 halt 独立且更准。因此 state_mismatch 降为 Tier 2 观测
    （仍入库、仍进 `classify_report` 供报告/抽读），但**不再驱动 run-level 硬 halt**。
    critical orphaned setting 仍计入硬 P1（那是有明确类别、非启发式的真实治理信号）。

    与冻结口径关系：T5/T6/T9/T12 均不含 state_mismatch（T6b 只查 orphan_critical），
    故本变更不放宽任何冻结阈值，属量具构念修正。
    """
    hard = 0
    for setting in report.orphaned_settings:
        if getattr(setting, "category", "background") == "critical":
            hard += 1
    return hard


async def collect_continuity_health_metrics(
    project_id: str,
    chapter_start: int,
    chapter_end: int,
) -> dict[str, object]:
    """收集指定章节范围内的 continuity health 指标（Task 118）.

    Args:
        project_id: 项目 ID
        chapter_start: 起始章节号（包含）
        chapter_end: 结束章节号（包含）

    Returns:
        包含以下键的字典:
        - health_low_chapters: health_score < 7.0 的章节列表
        - total_reports: 章节范围内的 continuity_reports 总数
        - affected_chapters: 受 health_low 影响的章节列表
        - human_marks_summary: {"total": N, "P1": N, "P2": N, "P3": N, "unresolved": N}
        - chapter_details: 每章详细数据列表
    """
    result: dict[str, object] = {
        "health_low_chapters": [],
        "total_reports": 0,
        "affected_chapters": [],
        "human_marks_summary": {"total": 0, "P1": 0, "P2": 0, "P3": 0, "unresolved": 0},
        "chapter_details": [],
    }

    report_repo = ContinuityReportRepository()
    mark_repo = HumanMarkRepository()

    reports = await report_repo.list_by_chapter_range(project_id, chapter_start, chapter_end)
    marks = await mark_repo.list_by_chapter_range(
        project_id, chapter_start, chapter_end, source="continuity_auditor"
    )

    health_low_chapters: list[int] = []
    chapter_details: list[dict[str, Any]] = []

    for report in reports:
        chapter = report.checked_up_to_chapter
        score = report.overall_health_score
        is_health_low = score < 7.0

        if is_health_low:
            health_low_chapters.append(chapter)

        chapter_details.append({
            "chapter_number": chapter,
            "health_score": score,
            "health_low": is_health_low,
        })

    result["health_low_chapters"] = health_low_chapters
    result["affected_chapters"] = health_low_chapters
    result["total_reports"] = len(reports)
    result["chapter_details"] = chapter_details

    marks_summary: dict[str, int] = {
        "total": len(marks), "P1": 0, "P2": 0, "P3": 0, "unresolved": 0
    }
    for mark in marks:
        severity = mark.severity if mark.severity else classify_mark_as_severity(mark)
        if severity == "P1":
            marks_summary["P1"] += 1
        elif severity == "P2":
            marks_summary["P2"] += 1
        else:
            marks_summary["P3"] += 1
        if mark.resolved_at is None:
            marks_summary["unresolved"] += 1

    result["human_marks_summary"] = marks_summary

    return result


def classify_mark_as_severity(mark: HumanMark) -> Literal["P1", "P2", "P3"]:
    """从 HumanMark 推断 severity（用于旧记录或 DB 列缺失时）。"""
    mark_type = mark.mark_type
    priority = mark.priority
    note = mark.note or ""

    if mark_type == "character" or "mismatch" in note.lower() or "矛盾" in note:
        return "P1"
    if priority >= 10:
        if "background" in note or "technical" in note or "historical" in note:
            return "P3"
        return "P1"
    if priority == 9:
        return "P1"
    if 7 <= priority <= 8:
        return "P2"
    return "P3"
