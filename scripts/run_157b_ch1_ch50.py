"""Task 157b: V6 阶段 D 首窗 Ch1-Ch50 集成验证实跑.

用法:
    # 1. 初始化干净隔离 DB + 创建带大纲项目（骨架：StoryOutline/ArcPlan/PlotThread）
    $env:DATABASE_URL = "sqlite:///.tmp/task157_ch1_ch50.db"
    python scripts/run_157b_ch1_ch50.py --init

    # 2. 无人值守跑 Ch1-Ch50（enforce 门禁，on_failure=isolate），并出 harness 判定
    $env:DATABASE_URL = "sqlite:///.tmp/task157_ch1_ch50.db"
    $env:PROJECT_ID = "<--init 打印的 project_id>"
    python scripts/run_157b_ch1_ch50.py

    # 如中途 kill / AutoHalt，可续跑（复用同一 run_id，跳过已 accepted 章）
    python scripts/run_157b_ch1_ch50.py --resume

说明:
    - 阶段 0+A+B+C 全部合入后的首个完整窗口 rehearsal（v6-plan §3 阶段 D / Task 157）。
    - enforce 门禁：触发候选硬门禁即 AutoHalt 暂停 run（本 Task 不改治理）。
    - on_failure=isolate：单章硬失败隔离并继续，最后汇总失败清单。
    - 跑后调用 evals.v6_acceptance.evaluate_v6_acceptance 出 T1/T2/T3/T4/T6/T7 三态判定。
    - 产出 docs/reports/task-157-ch1-ch50-integration-validation-report.md。
    - 逐章 metrics 追加到 .tmp/task157_ch1_ch50_metrics.jsonl。
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

from songyan.db import get_db
from songyan.db.connection import get_db_path
from songyan.db.continuity_repo import ContinuityReportRepository
from songyan.db.migrations import init_schema
from songyan.db.narrative_repo import NarrativeRepository
from songyan.db.repository import (
    ChapterVersionRepository,
    ProjectRepository,
)
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
from songyan.workflows.phase2_graph import run_project_pipeline

DB_PATH = Path(".tmp/task157_ch1_ch50.db")
DATABASE_URL = os.getenv("DATABASE_URL", f"sqlite:///{DB_PATH}")
GATE_MODE = os.getenv("GATE_MODE", "enforce")
ON_FAILURE = os.getenv("ON_FAILURE", "isolate")
REPORT_PATH = Path(
    "docs/reports/task-157-ch1-ch50-integration-validation-report.md"
)
METRICS_PATH = Path(".tmp/task157_ch1_ch50_metrics.jsonl")
PROJECT_FILE = Path(".tmp/task157_project.json")

START_CHAPTER = int(os.getenv("START_CHAPTER", "1"))
END_CHAPTER = int(os.getenv("END_CHAPTER", "50"))


# --------------------------------------------------------------------------- #
# 项目设定 + 叙事骨架（阶段 0）
# --------------------------------------------------------------------------- #
def _project_setting() -> ProjectSetting:
    """与 139b 基线一致的 scifi / webnovel_intense 项目（便于逐项对比）."""
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


def _build_outline(project_id: str) -> tuple[StoryOutline, list[ArcPlan], list[PlotThread]]:
    """构造全书大纲 + 弧规划 + 主线线索（阶段 0 骨架）.

    - 弧按 arc_boundaries [25,50,75,100,125] 切分（arc0:1-25, arc1:26-50, ...）。
    - 至少一条 is_mainline 线索在 arc0 开启，供 T1（opened→advanced）在 Ch1-50 内可追溯。
    - 主线核心名词（方舟 / 共鸣 / 旧日搭档）作为线索 title，随 GoalPlanner 注入正文，
      使 settlement 证据自然引用 → 推进线索状态机（Task 144 thread economy）。
    """
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
async def _query_dicts(sql: str, params: tuple[Any, ...] = ()) -> list[dict[str, Any]]:
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
        json.dumps({"project_id": project_id, "db": str(db_path)}, ensure_ascii=False),
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


def _write_report(
    project_id: str,
    run_id: str | None,
    halt_reason: str | None,
    chapters: list[dict[str, Any]],
    continuity: list[dict[str, Any]],
    threads: list[dict[str, Any]],
    harness_section: str,
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
        "# Task 157b：V6 阶段 D 首窗 Ch1-Ch50 集成验证报告",
        "",
        f"- 生成时间: {datetime.now().isoformat()}",
        f"- DB: `{get_db_path()}`",
        f"- 项目 ID: `{project_id}`",
        f"- Run ID: `{run_id}`",
        f"- 章节范围: Ch{START_CHAPTER}-Ch{END_CHAPTER}",
        f"- Gate 模式: {GATE_MODE}",
        f"- on_failure: {ON_FAILURE}",
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

    lines.extend(["", "## V6 验收 harness 判定", "", harness_section])

    lines.extend(["", "## 结论", ""])
    if halt_reason:
        lines.append(
            f"实跑触发 halt：{halt_reason}。按 Task 157 纪律记录根因，"
            "不在本 Task 改治理；判定为真退化 → 新开修复 Task，环境波动 → 记录后续跑。"
        )
    elif len(completed) == target_count:
        lines.append(
            f"Ch{START_CHAPTER}-Ch{END_CHAPTER} 全部完成 {len(completed)}/{target_count}，"
            "无 AutoHalt。阶段 D 首窗出口判定以上方 harness 三态为准。"
        )
    else:
        lines.append(
            f"未完成全部章节（完成 {len(completed)}/{target_count}），"
            "未触发 AutoHalt，请检查失败清单与日志。"
        )

    REPORT_PATH.write_text("\n".join(lines) + "\n", encoding="utf-8")
    print(f"[report] {REPORT_PATH}")


async def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--init", action="store_true", help="初始化干净 DB + 建项目 + 导入大纲")
    parser.add_argument("--resume", action="store_true", help="复用最近一次未完成 run 续跑")
    parser.add_argument("--project-id", default=None, help="覆盖 PROJECT_ID")
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
    print(f"[preflight] gate_mode={GATE_MODE}, on_failure={ON_FAILURE}, resume={args.resume}")

    project = await ProjectRepository().get(project_id)
    if project is None:
        raise ValueError(f"Project not found: {project_id}")

    gate_config = GateConfig.for_mode(GATE_MODE)  # type: ignore[arg-type]

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
    except AutoHaltException as exc:
        halt_reason = f"{exc.reason} (last chapter: {exc.last_chapter})"
        print("\n=== AutoHalt / Gate triggered ===")
        print(halt_reason)

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

    _write_report(
        project_id, run_id, halt_reason, chapters, continuity, threads, harness_section
    )

    print("\n=== Summary ===")
    print(f"Project: {project_id}")
    print(f"Run ID: {run_id}")
    completed_count = sum(1 for c in chapters if c["accepted"])
    target_count = END_CHAPTER - START_CHAPTER + 1
    print(f"Completed: {completed_count} / {target_count}")
    print(f"Halt: {halt_reason or 'None'}")
    print(f"harness all_passed(sufficient): {harness.all_passed}; undecided={harness.undecided}")


if __name__ == "__main__":
    asyncio.run(main())
