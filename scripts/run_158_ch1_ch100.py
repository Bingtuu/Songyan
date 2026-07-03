"""Task 158b: V6 阶段 D Ch1-Ch100 长跑验证实跑.

用法:
    # 1. 初始化干净隔离 DB + 创建带大纲项目
    $env:DATABASE_URL = "sqlite:///.tmp/task158_ch1_ch100.db"
    python scripts/run_158_ch1_ch100.py --init

    # 2. 无人值守跑 Ch1-Ch100（enforce 门禁，on_failure=isolate）
    $env:DATABASE_URL = "sqlite:///.tmp/task158_ch1_ch100.db"
    $env:PROJECT_ID = "<--init 打印的 project_id>"
    python scripts/run_158_ch1_ch100.py

    # 如中途 kill / AutoHalt，可续跑
    python scripts/run_158_ch1_ch100.py --resume

    # 调试：模拟在 ChK 非边界处 kill（保存 run_state 后、执行该章前抛出 KeyboardInterrupt）
    python scripts/run_158_ch1_ch100.py --kill-at-chapter 50

说明:
    - 阶段 D（Task 158）：验证 Ch1-Ch100 无人值守 + kill→resume + T5 首次实测冻结。
    - enforce 门禁：触发候选硬门禁即 AutoHalt 暂停 run。
    - on_failure=isolate：单章硬失败隔离并继续，最后汇总失败清单。
    - 跑后调用 evals.v6_acceptance.evaluate_v6_acceptance 出 T1-T8 三态判定。
    - 产出 docs/reports/task-158-ch1-ch100-long-run-validation-report.md。
    - 逐章 metrics 追加到 .tmp/task158_ch1_ch100_metrics.jsonl。
"""

from __future__ import annotations

import argparse
import asyncio
import json
import os
import sys
import uuid
from datetime import datetime
from pathlib import Path
from typing import Any

sys.path.insert(0, str(Path(__file__).parent.parent))

from songyan.config import settings
from songyan.db import get_db
from songyan.db.connection import get_db_path
from songyan.db.continuity_repo import ContinuityReportRepository
from songyan.db.migrations import init_schema
from songyan.db.narrative_repo import NarrativeRepository
from songyan.db.repository import (
    ChapterVersionRepository,
    ProjectRepository,
)
from songyan.db.run_db_metrics_repo import RunDbMetricsRepository
from songyan.evals.db_maintenance_metrics import (
    DbSizeMetrics,
    check_t5_latency_redline,
    check_t5_size_redline,
)
from songyan.evals.db_metrics import render_stage_a_metrics
from songyan.evals.streaming_report import read_run_logs
from songyan.evals.v6_acceptance import (
    evaluate_v6_acceptance,
    render_v6_acceptance_section,
)
from songyan.exceptions import AutoHaltException
from songyan.models import (
    ArcPlan,
    GateConfig,
    PlotThread,
    ProjectSetting,
    StoryOutline,
)
from songyan.workflows import phase2_graph
from songyan.workflows.phase2_graph import run_project_pipeline

DB_PATH = Path(".tmp/task158_ch1_ch100.db")
DATABASE_URL = os.getenv("DATABASE_URL", f"sqlite:///{DB_PATH}")
GATE_MODE = os.getenv("GATE_MODE", "enforce")
ON_FAILURE = os.getenv("ON_FAILURE", "isolate")
LLM_BUDGET = os.getenv("LLM_BUDGET", "0")  # 0 = 关闭
REPORT_PATH = Path(
    "docs/reports/task-158-ch1-ch100-long-run-validation-report.md"
)
METRICS_PATH = Path(".tmp/task158_ch1_ch100_metrics.jsonl")
PROJECT_FILE = Path(".tmp/task158_project.json")

START_CHAPTER = int(os.getenv("START_CHAPTER", "1"))
END_CHAPTER = int(os.getenv("END_CHAPTER", "100"))


# --------------------------------------------------------------------------- #
# 项目设定 + 叙事骨架（阶段 0；与 157b 完全一致，便于纵向对比）
# --------------------------------------------------------------------------- #
def _project_setting() -> ProjectSetting:
    """与 139b/157b 基线一致的 scifi / webnovel_intense 项目."""
    return ProjectSetting(
        title="轨道蜃景",
        genre_id="scifi",
        mode_id="webnovel_intense",
        protagonist_name="林渊",
        protagonist_background="前星际考古学家，因一次事故失去搭档，独自追查真相",
        core_hook="人类在太阳系边缘发现一座无法解析的黑色结构『方舟』，"
        "林渊是唯一能与之产生共鸣的个体",
        target_reader_expectation="硬科幻+太空悬疑，要求科学细节与剧情张力兼顾",
        target_word_count=450000,
        tone="热血",
        estimated_chapters=150,
        words_per_chapter=3000,
        story_structure="serial",
        sub_genre_id="space_opera",
        arc_boundaries=[25, 50, 75, 100, 125],
        arc_boundaries_auto=True,
    )


def _build_outline(
    project_id: str,
) -> tuple[StoryOutline, list[ArcPlan], list[PlotThread]]:
    """构造全书大纲 + 弧规划 + 主线线索（阶段 0 骨架）."""
    outline = StoryOutline(
        project_id=project_id,
        core_conflict="人类文明存续与深空黑色结构『方舟』的意志之间的对抗",
        mainline_synopsis=(
            "太阳系边缘出现一座无法解析的黑色结构『方舟』。前星际考古学家林渊"
            "是唯一能与之产生『共鸣』的个体。随着军方、财团与神秘教团先后介入，"
            "林渊在追查方舟真相的过程中，逐渐揭开当年那场夺走搭档性命的事故背后"
            "的隐情——『旧日搭档』之死并非意外，而与方舟的苏醒直接相关。林渊必须"
            "在人类被方舟同化之前，破解共鸣的本质，并决定是唤醒还是封存这座方舟。"
        ),
        themes=["存续与牺牲", "认知的边界", "信任与背叛"],
        intended_ending="林渊以自身共鸣为代价封存方舟，人类文明得以延续但代价沉重",
    )

    threads = [
        PlotThread(
            thread_id="t_ark",
            project_id=project_id,
            title="方舟",
            description="太阳系边缘的黑色结构，无法解析，疑似具有意志",
            is_mainline=True,
            expected_resolve_arc=5,
        ),
        PlotThread(
            thread_id="t_resonance",
            project_id=project_id,
            title="共鸣",
            description="林渊与方舟之间独有的感应能力，本质未知",
            is_mainline=True,
            expected_resolve_arc=4,
        ),
        PlotThread(
            thread_id="t_partner",
            project_id=project_id,
            title="旧日搭档",
            description="林渊失去的搭档之死背后的隐情",
            is_mainline=True,
            expected_resolve_arc=3,
        ),
    ]

    arcs = [
        ArcPlan(
            arc_id=f"{project_id}-arc0",
            project_id=project_id,
            arc_index=0,
            start_chapter=1,
            end_chapter=25,
            arc_goal="发现方舟、确立林渊的共鸣者身份，开启三条主线",
            threads_to_open=["t_ark", "t_resonance", "t_partner"],
            threads_to_resolve=[],
            is_mainline=True,
        ),
        ArcPlan(
            arc_id=f"{project_id}-arc1",
            project_id=project_id,
            arc_index=1,
            start_chapter=26,
            end_chapter=50,
            arc_goal="多方势力介入，共鸣加深，旧日搭档之谜浮现关键线索",
            threads_to_open=[],
            threads_to_resolve=[],
            is_mainline=True,
        ),
        ArcPlan(
            arc_id=f"{project_id}-arc2",
            project_id=project_id,
            arc_index=2,
            start_chapter=51,
            end_chapter=75,
            arc_goal="旧日搭档真相收束，方舟意志显现",
            threads_to_open=[],
            threads_to_resolve=["t_partner"],
            is_mainline=True,
        ),
        ArcPlan(
            arc_id=f"{project_id}-arc3",
            project_id=project_id,
            arc_index=3,
            start_chapter=76,
            end_chapter=100,
            arc_goal="共鸣本质揭示",
            threads_to_open=[],
            threads_to_resolve=[],
            is_mainline=True,
        ),
        ArcPlan(
            arc_id=f"{project_id}-arc4",
            project_id=project_id,
            arc_index=4,
            start_chapter=101,
            end_chapter=125,
            arc_goal="共鸣线收束，方舟决战前奏",
            threads_to_open=[],
            threads_to_resolve=["t_resonance"],
            is_mainline=True,
        ),
        ArcPlan(
            arc_id=f"{project_id}-arc5",
            project_id=project_id,
            arc_index=5,
            start_chapter=126,
            end_chapter=150,
            arc_goal="方舟命运收束，主线终局",
            threads_to_open=[],
            threads_to_resolve=["t_ark"],
            is_mainline=True,
        ),
    ]
    return outline, arcs, threads


# --------------------------------------------------------------------------- #
# DB 辅助
# --------------------------------------------------------------------------- #
async def _query_dicts(
    sql: str, params: tuple[Any, ...] = ()
) -> list[dict[str, Any]]:
    async with get_db() as conn:
        conn.row_factory = lambda cursor, row: {
            col[0]: row[i] for i, col in enumerate(cursor.description)
        }
        cursor = await conn.execute(sql, params)
        return await cursor.fetchall()


async def _init_db() -> str:
    db_path = get_db_path()
    for suffix in ("", "-wal", "-shm"):
        p = db_path.with_name(db_path.name + suffix) if suffix else db_path
        if p.exists():
            p.unlink()
            print(f"[init] removed {p}")
    await init_schema()
    print(f"[init] schema initialized at {db_path}")

    project_id = uuid.uuid4().hex
    await ProjectRepository().create(_project_setting(), project_id)
    outline, arcs, threads = _build_outline(project_id)
    await NarrativeRepository().import_outline(project_id, outline, arcs, threads)
    print(f"[init] project created {project_id}")
    print(f"[init] outline imported: {len(arcs)} arcs, {len(threads)} threads")

    PROJECT_FILE.parent.mkdir(parents=True, exist_ok=True)
    PROJECT_FILE.write_text(
        json.dumps(
            {"project_id": project_id, "db": str(db_path.as_posix())},
            ensure_ascii=False,
        ),
        encoding="utf-8",
    )
    print(f"[init] PROJECT_ID={project_id} (also saved to {PROJECT_FILE})")
    return project_id


def _resolve_project_id() -> str | None:
    pid = os.getenv("PROJECT_ID")
    if pid:
        return pid
    if PROJECT_FILE.exists():
        try:
            return json.loads(PROJECT_FILE.read_text(encoding="utf-8")).get("project_id")
        except (json.JSONDecodeError, OSError):
            return None
    return None


async def _find_run_id(project_id: str) -> str | None:
    rows = await _query_dicts(
        """SELECT run_id FROM project_runs
           WHERE project_id = ?
           ORDER BY created_at DESC
           LIMIT 1""",
        (project_id,),
    )
    return rows[0]["run_id"] if rows else None


async def _load_run_state(run_id: str) -> dict[str, Any] | None:
    rows = await _query_dicts(
        """SELECT current_chapter, completed_chapters, failed_chapters, status
           FROM project_runs WHERE run_id = ?""",
        (run_id,),
    )
    if not rows:
        return None
    row = rows[0]
    return {
        "current_chapter": row["current_chapter"],
        "completed_chapters": json.loads(row["completed_chapters"] or "[]"),
        "failed_chapters": json.loads(row["failed_chapters"] or "[]"),
        "status": row["status"],
    }


async def _load_accepted_versions(project_id: str) -> dict[int, Any]:
    repo = ChapterVersionRepository()
    result: dict[int, Any] = {}
    rows = await _query_dicts(
        """SELECT * FROM chapter_versions
           WHERE project_id = ?
             AND version_type IN ('accepted', 'revision', 'edited')
             AND is_abandoned = 0
           ORDER BY chapter_number, version_number""",
        (project_id,),
    )
    for row in rows:
        result[row["chapter_number"]] = await repo.get(row["version_id"])
    return result


async def _load_continuity_reports(project_id: str) -> list[dict[str, Any]]:
    reports = await ContinuityReportRepository().list_by_chapter_range(
        project_id, START_CHAPTER, END_CHAPTER
    )
    out: list[dict[str, Any]] = []
    for r in reports:
        orphan_critical = sum(
            1
            for s in r.orphaned_settings
            if getattr(s, "category", "background") == "critical"
        )
        out.append(
            {
                "chapter": r.checked_up_to_chapter,
                "health_score": r.overall_health_score,
                "orphaned_count": len(r.orphaned_settings),
                "orphan_critical": orphan_critical,
                "forgotten_count": len(r.forgotten_items),
                "mismatch_count": len(r.state_mismatches),
                "overdue_count": len(r.overdue_foreshadowings),
            }
        )
    return out


async def _load_thread_states(project_id: str) -> list[dict[str, Any]]:
    repo = NarrativeRepository()
    threads = await repo.list_threads(project_id)
    return [
        {
            "thread_id": t.thread_id,
            "title": t.title,
            "is_mainline": t.is_mainline,
            "status": t.status,
            "opened_chapter": t.opened_chapter,
            "last_status_chapter": t.last_status_chapter,
            "last_status_version_id": t.last_status_version_id,
        }
        for t in threads
    ]


def _fmt(value: Any) -> str:
    if value is None:
        return "N/A"
    if isinstance(value, float):
        return f"{value:.3f}"
    return str(value)


def _fmt_bool(value: bool | None) -> str:
    if value is True:
        return "Y"
    if value is False:
        return "N"
    return ""


def _append_metric(record: dict[str, Any]) -> None:
    METRICS_PATH.parent.mkdir(parents=True, exist_ok=True)
    with METRICS_PATH.open("a", encoding="utf-8") as f:
        f.write(json.dumps(record, ensure_ascii=False) + "\n")


# --------------------------------------------------------------------------- #
# T5 冻结判定
# --------------------------------------------------------------------------- #
async def _evaluate_t5(
    project_id: str, run_id: str | None
) -> dict[str, Any]:
    """读取 run_db_metrics，判定 T5 尺寸/耗时红线并给出冻结建议."""
    samples = (
        await RunDbMetricsRepository().list_by_run(run_id) if run_id else []
    )
    if len(samples) < 3:
        return {
            "sufficient": False,
            "size_passed": None,
            "latency_passed": None,
            "db_size_mb": None,
            "baseline_ms": None,
            "max_latency_ms": None,
            "recommendation": "样本不足（<3），暂不冻结 T5",
        }

    last = samples[-1]
    db_size_bytes = int(last["db_size_bytes"])
    db_size_mb = db_size_bytes / (1024 * 1024)
    size_metrics = DbSizeMetrics(
        db_size_bytes=db_size_bytes,
        wal_size_bytes=int(last["wal_size_bytes"]),
        page_count=int(last["page_count"]),
        page_size=int(last["page_size"]),
    )
    size_breached = check_t5_size_redline(size_metrics)

    baseline_values = [
        float(s["scan_latency_ms"])
        for s in samples[:10]
        if s.get("scan_latency_ms") is not None
    ]
    baseline_ms = sum(baseline_values) / len(baseline_values) if baseline_values else 0.0
    max_latency_ms = max(float(s["scan_latency_ms"]) for s in samples)
    latency_breached = any(
        check_t5_latency_redline(float(s["scan_latency_ms"]), baseline_ms)
        for s in samples
    )

    recommendation = "维持首版阈值：DB≤300MB、扫描≤基线1.5×"
    if size_breached or latency_breached:
        recommendation = "实测破线，需按 148z 纪律记录并调整阈值后再冻结"

    return {
        "sufficient": True,
        "size_passed": not size_breached,
        "latency_passed": not latency_breached,
        "db_size_mb": db_size_mb,
        "baseline_ms": baseline_ms,
        "baseline_sample_count": len(baseline_values),
        "max_latency_ms": max_latency_ms,
        "size_breach_chapters": [
            int(s["chapter_number"])
            for s in samples
            if check_t5_size_redline(
                DbSizeMetrics(
                    db_size_bytes=int(s["db_size_bytes"]),
                    wal_size_bytes=int(s["wal_size_bytes"]),
                    page_count=int(s["page_count"]),
                    page_size=int(s["page_size"]),
                )
            )
        ],
        "latency_breach_chapters": [
            int(s["chapter_number"])
            for s in samples
            if check_t5_latency_redline(float(s["scan_latency_ms"]), baseline_ms)
        ],
        "recommendation": recommendation,
    }


# --------------------------------------------------------------------------- #
# 报告生成
# --------------------------------------------------------------------------- #
def _write_report(
    project_id: str,
    run_id: str | None,
    halt_reason: str | None,
    kill_timeline: dict[str, Any] | None,
    chapters: list[dict[str, Any]],
    continuity: list[dict[str, Any]],
    threads: list[dict[str, Any]],
    harness_section: str,
    t5: dict[str, Any],
    stage_a_section: str,
) -> None:
    REPORT_PATH.parent.mkdir(parents=True, exist_ok=True)
    completed = [c for c in chapters if c.get("accepted")]
    failed = [c for c in chapters if not c.get("accepted")]
    settlement_ok = [c for c in chapters if c.get("settlement_success") is True]
    qg_ok = [c for c in chapters if c.get("quality_gate_passed") is True]
    duration_total = sum(c.get("duration_sec") or 0 for c in chapters)
    target_count = END_CHAPTER - START_CHAPTER + 1
    gate_triggers = [c for c in chapters if c.get("gate_triggered")]
    emergency = [c for c in chapters if c.get("context_emergency")]
    mainline_transitions = [
        t
        for t in threads
        if t["is_mainline"] and t["status"] in ("advanced", "resolved")
    ]

    lines: list[str] = [
        "# Task 158：V6 阶段 D Ch1-Ch100 长跑验证报告",
        "",
        f"- 生成时间: {datetime.now().isoformat()}",
        f"- DB: `{get_db_path()}`",
        f"- 项目 ID: `{project_id}`",
        f"- Run ID: `{run_id}`",
        f"- 章节范围: Ch{START_CHAPTER}-Ch{END_CHAPTER}",
        f"- Gate 模式: {GATE_MODE}",
        f"- on_failure: {ON_FAILURE}",
        f"- LLM 预算: {LLM_BUDGET}（0=关闭）",
        f"- Halt 原因: {halt_reason or 'None'}",
        "",
        "## 总体统计",
        "",
        f"- 完成/目标: {len(completed)} / {target_count}",
        f"- 失败章节: {[c['chapter'] for c in failed]}",
        f"- settlement 成功: {len(settlement_ok)} / {len(chapters)}",
        f"- QG 通过: {len(qg_ok)} / {len(chapters)}",
        f"- Gate 触发章节: {[c['chapter'] for c in gate_triggers]}",
        f"- Context Emergency 章节: {[c['chapter'] for c in emergency]}",
        f"- 总耗时: {duration_total:.1f}s ({duration_total / 60:.1f} min)",
        "",
        "## 主线线索状态（T1 可追溯）",
        "",
        f"- 达到 advanced/resolved 的主线线索数: {len(mainline_transitions)}",
        "",
        "| thread_id | title | mainline | status | opened@ | last_change@ | version |",
        "|---|---|:---:|---|---:|---:|---|",
    ]
    for t in threads:
        lines.append(
            f"| {t['thread_id']} | {t['title']} | {_fmt_bool(t['is_mainline'])} | "
            f"{t['status']} | {_fmt(t['opened_chapter'])} | "
            f"{_fmt(t['last_status_chapter'])} | "
            f"{(t['last_status_version_id'] or '')[:12]} |"
        )

    lines.extend(
        [
            "",
            "## 每章关键指标",
            "",
            "| Ch | Word | Settlement | Summary | QG | Rev | Rule | LLM | "
            "Gate | Budget | Emerg | Dur(s) |",
            "|---:|---:|:---:|:---:|:---:|---:|---:|---:|:---:|---:|:---:|---:|",
        ]
    )
    for c in chapters:
        lines.append(
            f"| {c['chapter']} | {c.get('word_count', '')} | "
            f"{_fmt_bool(c.get('settlement_success'))} | "
            f"{_fmt_bool(c.get('summary_success'))} | "
            f"{_fmt_bool(c.get('quality_gate_passed'))} | "
            f"{c.get('revision_rounds', '')} | "
            f"{c.get('rule_violations', '')} | "
            f"{c.get('llm_audit_issues', '')} | "
            f"{_fmt_bool(c.get('gate_triggered'))} | "
            f"{_fmt(c.get('budget_used'))} | "
            f"{_fmt_bool(c.get('context_emergency'))} | "
            f"{c.get('duration_sec', '')} |"
        )

    lines.extend(["", "## Continuity 趋势", ""])
    lines.append(
        "| Ch | Health | Orphaned | OrphanCritical | Forgotten | Mismatch | Overdue |"
    )
    lines.append("|---:|---:|---:|---:|---:|---:|---:|")
    for r in continuity:
        lines.append(
            f"| {r['chapter']} | {_fmt(r['health_score'])} | {r['orphaned_count']} | "
            f"{r['orphan_critical']} | {r['forgotten_count']} | "
            f"{r['mismatch_count']} | {r['overdue_count']} |"
        )

    lines.extend(["", "## 五类长期曲线（Stage A 度量）", "", stage_a_section])

    lines.extend(["", "## V6 验收 harness 判定", "", harness_section])

    lines.extend(["", "## T5 首次实测冻结结论", ""])
    if t5["sufficient"]:
        lines.append(
            f"- Ch100 DB 尺寸：{t5['db_size_mb']:.2f} MB（红线 300MB）"
        )
        baseline_count = min(10, t5["baseline_sample_count"])
        lines.append(
            f"- 扫描耗时基线（前{baseline_count}样本均值）："
            f"{_fmt(t5['baseline_ms'])} ms"
        )
        lines.append(f"- 最大扫描耗时：{_fmt(t5['max_latency_ms'])} ms")
        lines.append(
            f"- 尺寸红线：{'✓ 未超' if t5['size_passed'] else '🔴 破线'}"
        )
        lines.append(
            f"- 耗时红线：{'✓ 未超' if t5['latency_passed'] else '🔴 破线'}"
        )
        if t5.get("size_breach_chapters"):
            lines.append(f"- 尺寸破线章：{t5['size_breach_chapters']}")
        if t5.get("latency_breach_chapters"):
            lines.append(f"- 耗时破线章：{t5['latency_breach_chapters']}")
        lines.append(f"- 冻结建议：**{t5['recommendation']}**")
    else:
        lines.append(f"- {t5['recommendation']}")

    if kill_timeline:
        lines.extend(["", "## Kill→Resume 时间线", ""])
        lines.append(f"- 模拟 kill 章：Ch{kill_timeline.get('kill_chapter')}")
        lines.append(
            f"- kill 前保存的 current_chapter：Ch{kill_timeline.get('saved_current_chapter')}"
        )
        lines.append(f"- resume 起点：Ch{kill_timeline.get('resume_start')}")
        lines.append(
            f"- in-flight 重算章：{kill_timeline.get('inflight_recomputed')}"
        )
        lines.append(
            f"- 最终 completed 集合：{sorted(kill_timeline.get('final_completed', []))}"
        )
        lines.append(
            f"- prune_orphan_checkpoints 清理数：{kill_timeline.get('pruned_count')}"
        )

    lines.extend(["", "## 结论", ""])
    if halt_reason:
        lines.append(
            f"实跑触发 halt：{halt_reason}。按 Task 158 纪律记录根因，"
            "不在本 Task 改治理；判定为真退化 → 新开修复 Task。"
        )
    elif len(completed) == target_count:
        lines.append(
            f"Ch{START_CHAPTER}-Ch{END_CHAPTER} 全部完成 {len(completed)}/{target_count}，"
            "无 AutoHalt。阶段 D 100 章出口判定以上方 harness 三态为准。"
        )
    else:
        lines.append(
            f"未完成全部章节（完成 {len(completed)}/{target_count}），"
            "未触发 AutoHalt，请检查失败清单与日志。"
        )

    REPORT_PATH.write_text("\n".join(lines) + "\n", encoding="utf-8")
    print(f"[report] {REPORT_PATH}")


# --------------------------------------------------------------------------- #
# kill→resume 调试钩子（仅 --kill-at-chapter，不改产品代码）
# --------------------------------------------------------------------------- #
def _install_kill_hook(kill_at_chapter: int) -> None:
    """在指定章的 _run_single_chapter 调用前抛出 KeyboardInterrupt.

    模拟非边界 kill：run_state 已保存 current_chapter=K，但第 K 章尚未执行。
    """
    original = phase2_graph._run_single_chapter

    async def _wrapped(**kwargs: Any) -> Any:
        if kwargs.get("chapter_number") == kill_at_chapter:
            raise KeyboardInterrupt(
                f"simulated kill at chapter {kill_at_chapter}"
            )
        return await original(**kwargs)

    phase2_graph._run_single_chapter = _wrapped


def _load_run_log_metrics(run_id: str | None) -> dict[int, dict[str, Any]]:
    metrics: dict[int, dict[str, Any]] = {}
    if run_id is None:
        return metrics
    path = Path(f"logs/chapter_runs/{run_id}.jsonl")
    if not path.exists():
        return metrics
    for line in path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line:
            continue
        try:
            entry = json.loads(line)
        except json.JSONDecodeError:
            continue
        ch = entry.get("chapter_number")
        if not isinstance(ch, int):
            continue
        metrics[ch] = {
            "success": entry.get("success"),
            "settlement_success": entry.get("settlement_success"),
            "summary_success": entry.get("summary_success"),
            "quality_gate_passed": entry.get("quality_gate_passed"),
            "revision_rounds": entry.get("revision_rounds"),
            "rule_violations": entry.get("rule_violations"),
            "llm_audit_issues": entry.get("llm_audit_issues"),
            "gate_triggered": entry.get("gate_triggered"),
            "gate_reasons": entry.get("gate_reasons") or [],
            "budget_used": entry.get("budget_used"),
            "context_emergency": entry.get("context_emergency"),
            "duration_sec": entry.get("duration_sec"),
            "word_count": entry.get("word_count"),
            "continuity_health_score": entry.get("continuity_health_score"),
        }
    return metrics


# --------------------------------------------------------------------------- #
# 主流程
# --------------------------------------------------------------------------- #
async def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--init", action="store_true", help="初始化干净 DB + 建项目 + 导入大纲"
    )
    parser.add_argument(
        "--resume", action="store_true", help="复用最近一次未完成 run 续跑"
    )
    parser.add_argument("--project-id", default=None, help="覆盖 PROJECT_ID")
    parser.add_argument(
        "--kill-at-chapter",
        type=int,
        default=None,
        help="调试：在指定章执行前抛出 KeyboardInterrupt 模拟 kill",
    )
    args = parser.parse_args()

    if args.init:
        await _init_db()
        return

    project_id = args.project_id or _resolve_project_id()
    if not project_id:
        parser.error("请先用 --init 创建项目，或提供 --project-id / PROJECT_ID")

    db_path = get_db_path()
    print(f"[preflight] db={db_path}")
    print(f"[preflight] project={project_id}, range=({START_CHAPTER}, {END_CHAPTER})")
    print(
        f"[preflight] gate_mode={GATE_MODE}, on_failure={ON_FAILURE}, "
        f"resume={args.resume}, kill_at={args.kill_at_chapter}"
    )

    project = await ProjectRepository().get(project_id)
    if project is None:
        raise ValueError(f"Project not found: {project_id}")

    # 应用 LLM 预算（0 表示关闭）
    budget_value = int(LLM_BUDGET)
    if budget_value > 0:
        settings.llm_run_call_budget = budget_value
        print(f"[preflight] llm_run_call_budget={budget_value}")

    gate_config = GateConfig.for_mode(GATE_MODE)  # type: ignore[arg-type]

    kill_timeline: dict[str, Any] | None = None
    if args.kill_at_chapter is not None:
        _install_kill_hook(args.kill_at_chapter)
        kill_timeline = {"kill_chapter": args.kill_at_chapter}

    halt_reason: str | None = None
    try:
        result = await run_project_pipeline(
            project_id=project_id,
            chapter_range=(START_CHAPTER, END_CHAPTER),
            mode_id=project.mode_id,
            auto_confirm=True,
            on_failure=ON_FAILURE,
            gate_config=gate_config,
            resume=args.resume,
        )
        print("\n=== Pipeline completed ===")
        print(f"Completed: {result.chapters_completed}")
        print(f"Failed: {result.chapters_failed}")
        print(f"Status: {result.final_status}")
        print(f"Duration: {result.total_duration_sec:.1f}s")
        if kill_timeline is not None:
            kill_timeline["final_completed"] = result.chapters_completed
    except AutoHaltException as exc:
        halt_reason = f"{exc.reason} (last chapter: {exc.last_chapter})"
        print("\n=== AutoHalt / Gate triggered ===")
        print(halt_reason)
    except KeyboardInterrupt as exc:
        halt_reason = f"KeyboardInterrupt: {exc}"
        print("\n=== Simulated kill ===")
        print(halt_reason)
        # 落盘 kill 时间线，便于报告生成
        if kill_timeline is not None:
            run_id = await _find_run_id(project_id)
            state = await _load_run_state(run_id) if run_id else None
            if state:
                kill_timeline["saved_current_chapter"] = state["current_chapter"]
                kill_timeline["saved_completed"] = state["completed_chapters"]

    # --- 收集证据 ---
    run_id = await _find_run_id(project_id)
    accepted_versions = await _load_accepted_versions(project_id)
    run_log = _load_run_log_metrics(run_id)
    continuity = await _load_continuity_reports(project_id)
    threads = await _load_thread_states(project_id)

    chapters: list[dict[str, Any]] = []
    for ch in sorted(set(list(accepted_versions.keys()) + list(run_log.keys()))):
        if ch < START_CHAPTER or ch > END_CHAPTER:
            continue
        version = accepted_versions.get(ch)
        log = run_log.get(ch, {})
        record = {
            "chapter": ch,
            "accepted": ch in accepted_versions,
            "word_count": version.word_count if version else log.get("word_count"),
            "settlement_success": log.get("settlement_success"),
            "summary_success": log.get("summary_success"),
            "quality_gate_passed": log.get("quality_gate_passed"),
            "revision_rounds": log.get("revision_rounds"),
            "rule_violations": log.get("rule_violations"),
            "llm_audit_issues": log.get("llm_audit_issues"),
            "gate_triggered": log.get("gate_triggered"),
            "gate_reasons": log.get("gate_reasons") or [],
            "budget_used": log.get("budget_used"),
            "context_emergency": log.get("context_emergency"),
            "duration_sec": log.get("duration_sec"),
            "continuity_health_score": log.get("continuity_health_score"),
        }
        chapters.append(record)
        _append_metric(record)

    # 如刚经历 kill，补充 resume 时间线
    if kill_timeline is not None and args.resume:
        state = await _load_run_state(run_id) if run_id else None
        if state:
            kill_timeline.setdefault(
                "resume_start", state.get("current_chapter")
            )
            kill_timeline.setdefault(
                "final_completed", state.get("completed_chapters")
            )

    # --- harness 三态判定 ---
    run_logs = read_run_logs(run_id) if run_id else []
    harness = await evaluate_v6_acceptance(
        project_id,
        START_CHAPTER,
        END_CHAPTER,
        run_id=run_id,
        run_logs=run_logs,
    )
    harness_section = render_v6_acceptance_section(harness)
    print("\n=== V6 Acceptance harness ===")
    print(harness_section)

    # --- Stage A 五类曲线 ---
    stage_a_section = await render_stage_a_metrics(
        project_id, START_CHAPTER, END_CHAPTER
    )

    # --- T5 冻结判定 ---
    t5 = await _evaluate_t5(project_id, run_id)
    print("\n=== T5 freeze evaluation ===")
    print(t5)

    _write_report(
        project_id,
        run_id,
        halt_reason,
        kill_timeline,
        chapters,
        continuity,
        threads,
        harness_section,
        t5,
        stage_a_section,
    )

    print("\n=== Summary ===")
    print(f"Project: {project_id}")
    print(f"Run ID: {run_id}")
    completed_count = sum(1 for c in chapters if c["accepted"])
    target_count = END_CHAPTER - START_CHAPTER + 1
    print(f"Completed: {completed_count} / {target_count}")
    print(f"Halt: {halt_reason or 'None'}")
    print(
        f"harness all_passed(sufficient): {harness.all_passed}; undecided={harness.undecided}"
    )
    print(f"T5: {t5['recommendation']}")


if __name__ == "__main__":
    asyncio.run(main())
