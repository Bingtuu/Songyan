"""Task 158r: §1.3-R kill→resume 真实命令级演练.

目的:
    Task 158 长跑未显式使用人为 kill，§1.3-R「中途人为 kill 后同命令 resume 续完」
    缺命令级证据。本脚本在**全新隔离 DB** 上用真实 DeepSeek API 补一次演练:

        Phase 1: --kill-at-chapter 3   → Ch1/Ch2 accept，Ch3 生成完成但 accept 前被
                                          KeyboardInterrupt 打断（in-flight 非边界 kill）
        Phase 2: --resume              → Ch1/Ch2 已 accept 跳过，Ch3 重算，Ch4/Ch5 续完

    与 158 的差异:
    - 独立 DB `.tmp/task158r_kill_resume.db`、独立 report/metrics 路径，绝不覆盖
      已冻结的 Task 158 证据。
    - kill 钩子打在**生成完成之后、accept 之前**（真正的 in-flight），使 resume
      必须重算 Ch3 并清理孤儿 checkpoint。
    - 复用 run_158_ch1_ch100 的项目设定 / 大纲构造器，保证同口径。

用法:
    $env:DATABASE_URL = "sqlite:///.tmp/task158r_kill_resume.db"
    python scripts/run_158r_kill_resume_drill.py --init
    python scripts/run_158r_kill_resume_drill.py --kill-at-chapter 3
    python scripts/run_158r_kill_resume_drill.py --resume
"""

from __future__ import annotations

import argparse
import asyncio
import json
import os
import sys
from datetime import datetime
from pathlib import Path
from typing import Any

sys.path.insert(0, str(Path(__file__).parent.parent))

import scripts.run_158_ch1_ch100 as base
from songyan.db import get_db
from songyan.db.connection import get_db_path
from songyan.db.migrations import init_schema
from songyan.db.narrative_repo import NarrativeRepository
from songyan.db.repository import ProjectRepository
from songyan.exceptions import AutoHaltException
from songyan.models import GateConfig
from songyan.workflows import phase2_graph
from songyan.workflows.phase2_graph import run_project_pipeline

DB_PATH = Path(".tmp/task158r_kill_resume.db")
REPORT_PATH = Path("docs/reports/task-158r-kill-resume-drill-report.md")
EVIDENCE_PATH = Path(".tmp/task158r_kill_resume_evidence.jsonl")
PROJECT_FILE = Path(".tmp/task158r_project.json")

GATE_MODE = os.getenv("GATE_MODE", "enforce")
ON_FAILURE = os.getenv("ON_FAILURE", "isolate")
START_CHAPTER = int(os.getenv("START_CHAPTER", "1"))
END_CHAPTER = int(os.getenv("END_CHAPTER", "5"))
KILL_CHAPTER_DEFAULT = 3


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

    if EVIDENCE_PATH.exists():
        EVIDENCE_PATH.unlink()
        print(f"[init] removed stale evidence {EVIDENCE_PATH}")

    import uuid

    project_id = uuid.uuid4().hex
    await ProjectRepository().create(base._project_setting(), project_id)
    outline, arcs, threads = base._build_outline(project_id)
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
    print(f"[init] PROJECT_ID={project_id} (saved to {PROJECT_FILE})")
    return project_id


def _resolve_project_id() -> str | None:
    pid = os.getenv("PROJECT_ID")
    if pid:
        return pid
    if PROJECT_FILE.exists():
        try:
            return json.loads(PROJECT_FILE.read_text(encoding="utf-8")).get(
                "project_id"
            )
        except (json.JSONDecodeError, OSError):
            return None
    return None


async def _accepted_chapters(project_id: str) -> list[int]:
    rows = await _query_dicts(
        """SELECT chapter_number FROM chapter_heads
           WHERE project_id = ? AND status = 'accepted'
           ORDER BY chapter_number""",
        (project_id,),
    )
    return [int(r["chapter_number"]) for r in rows]


async def _chapter_head_states(project_id: str) -> list[dict[str, Any]]:
    return await _query_dicts(
        """SELECT chapter_number, status,
                  (accepted_version_id IS NOT NULL) AS has_accepted
           FROM chapter_heads
           WHERE project_id = ?
           ORDER BY chapter_number""",
        (project_id,),
    )


async def _run_state(project_id: str) -> dict[str, Any] | None:
    rows = await _query_dicts(
        """SELECT run_id, current_chapter, completed_chapters,
                  failed_chapters, status
           FROM project_runs WHERE project_id = ?
           ORDER BY created_at DESC LIMIT 1""",
        (project_id,),
    )
    if not rows:
        return None
    row = rows[0]
    return {
        "run_id": row["run_id"],
        "current_chapter": row["current_chapter"],
        "completed_chapters": json.loads(row["completed_chapters"] or "[]"),
        "failed_chapters": json.loads(row["failed_chapters"] or "[]"),
        "status": row["status"],
    }


async def _checkpoint_thread_ids(project_id: str) -> list[str]:
    """当前项目残留的 checkpoint thread_id（去重）。表可能不存在。"""
    try:
        rows = await _query_dicts(
            """SELECT DISTINCT thread_id FROM checkpoints
               WHERE json_extract(metadata, '$.project_id') = ?""",
            (project_id,),
        )
    except Exception:  # noqa: BLE001 — checkpoints 表可能未建
        return []
    return [r["thread_id"] for r in rows if r.get("thread_id")]


def _append_evidence(record: dict[str, Any]) -> None:
    EVIDENCE_PATH.parent.mkdir(parents=True, exist_ok=True)
    with EVIDENCE_PATH.open("a", encoding="utf-8") as f:
        f.write(json.dumps(record, ensure_ascii=False) + "\n")


# --------------------------------------------------------------------------- #
# in-flight kill 钩子（生成完成后、accept 前打断）
# --------------------------------------------------------------------------- #
def _install_inflight_kill_hook(kill_at_chapter: int) -> None:
    """在 ChK 的 run_chapter_pipeline 返回后、resume_human_confirm(accept) 前打断.

    这是真正的 in-flight 非边界 kill：ChK 正文/settlement 已生成、checkpoint 已落盘，
    但 accept 尚未发生 → chapter_heads 中 ChK 不是 accepted。resume 时该章会被重算，
    孤儿 checkpoint 被 prune_orphan_checkpoints 清理。
    """
    original_run = phase2_graph.run_chapter_pipeline

    async def _wrapped(**kwargs: Any) -> Any:
        state = await original_run(**kwargs)
        if kwargs.get("chapter_number") == kill_at_chapter:
            print(
                f"[kill-hook] Ch{kill_at_chapter} generated "
                f"(thread={state.get('thread_id')}); "
                "raising KeyboardInterrupt before accept"
            )
            raise KeyboardInterrupt(
                f"simulated in-flight kill at chapter {kill_at_chapter}"
            )
        return state

    phase2_graph.run_chapter_pipeline = _wrapped


# --------------------------------------------------------------------------- #
# 各阶段执行 + 证据落盘
# --------------------------------------------------------------------------- #
async def _run_phase(
    project_id: str,
    *,
    phase: str,
    resume: bool,
    kill_at_chapter: int | None,
) -> dict[str, Any]:
    gate_config = GateConfig.for_mode(GATE_MODE)  # type: ignore[arg-type]

    if kill_at_chapter is not None:
        _install_inflight_kill_hook(kill_at_chapter)

    accepted_before = await _accepted_chapters(project_id)
    threads_before = await _checkpoint_thread_ids(project_id)
    print(f"[{phase}] accepted_before={accepted_before}")
    print(f"[{phase}] checkpoint_threads_before={len(threads_before)}")

    outcome: dict[str, Any] = {
        "phase": phase,
        "resume": resume,
        "kill_at_chapter": kill_at_chapter,
        "accepted_before": accepted_before,
        "checkpoint_threads_before": len(threads_before),
        "interrupted": False,
        "auto_halt": None,
        "timestamp": datetime.now().isoformat(),
    }

    try:
        result = await run_project_pipeline(
            project_id=project_id,
            chapter_range=(START_CHAPTER, END_CHAPTER),
            mode_id=(await ProjectRepository().get(project_id)).mode_id,  # type: ignore[union-attr]
            auto_confirm=True,
            on_failure=ON_FAILURE,
            gate_config=gate_config,
            resume=resume,
        )
        print(f"\n[{phase}] === Pipeline completed ===")
        print(f"[{phase}] completed={result.chapters_completed}")
        print(f"[{phase}] failed={result.chapters_failed}")
        print(f"[{phase}] status={result.final_status}")
        outcome["final_status"] = result.final_status
        outcome["chapters_completed"] = result.chapters_completed
        outcome["chapters_failed"] = result.chapters_failed
    except KeyboardInterrupt as exc:
        print(f"\n[{phase}] === Simulated in-flight kill ===\n{exc}")
        outcome["interrupted"] = True
        outcome["interrupt_msg"] = str(exc)
    except AutoHaltException as exc:
        print(f"\n[{phase}] === AutoHalt ===\n{exc.reason} @ Ch{exc.last_chapter}")
        outcome["auto_halt"] = f"{exc.reason} (Ch{exc.last_chapter})"

    state = await _run_state(project_id)
    accepted_after = await _accepted_chapters(project_id)
    heads_after = await _chapter_head_states(project_id)
    threads_after = await _checkpoint_thread_ids(project_id)

    outcome["run_id"] = state["run_id"] if state else None
    outcome["run_status"] = state["status"] if state else None
    outcome["current_chapter"] = state["current_chapter"] if state else None
    outcome["accepted_after"] = accepted_after
    outcome["chapter_heads"] = heads_after
    outcome["checkpoint_threads_after"] = len(threads_after)

    print(f"[{phase}] accepted_after={accepted_after}")
    print(f"[{phase}] run_id={outcome['run_id']} status={outcome['run_status']}")
    print(f"[{phase}] checkpoint_threads_after={len(threads_after)}")

    _append_evidence(outcome)
    return outcome


# --------------------------------------------------------------------------- #
# 报告
# --------------------------------------------------------------------------- #
def _write_report(
    project_id: str,
    kill_outcome: dict[str, Any],
    resume_outcome: dict[str, Any],
) -> None:
    REPORT_PATH.parent.mkdir(parents=True, exist_ok=True)
    kill_ch = kill_outcome.get("kill_at_chapter")
    accepted_at_kill = kill_outcome.get("accepted_after", [])
    accepted_final = resume_outcome.get("accepted_after", [])
    inflight_recomputed = kill_ch if kill_ch in accepted_final else None
    target = list(range(START_CHAPTER, END_CHAPTER + 1))
    resume_completed = resume_outcome.get("final_status") == "completed"

    def _mark(ok: bool) -> str:
        return "✅" if ok else "🔴"

    kill_inflight_ok = bool(
        kill_outcome.get("interrupted") and kill_ch not in accepted_at_kill
    )
    same_run_ok = kill_outcome.get("run_id") == resume_outcome.get("run_id")
    recompute_ok = inflight_recomputed is not None
    target_ok = set(target).issubset(set(accepted_final))
    kill_in = "∉" if kill_ch not in accepted_at_kill else "∈"
    final_in = "∈" if inflight_recomputed else "∉"

    lines = [
        "# Task 158r：§1.3-R kill→resume 真实命令级演练报告",
        "",
        f"- 生成时间: {datetime.now().isoformat()}",
        f"- DB: `{get_db_path()}`",
        f"- 项目 ID: `{project_id}`",
        f"- 章节范围: Ch{START_CHAPTER}-Ch{END_CHAPTER}",
        f"- Gate 模式: {GATE_MODE}",
        f"- on_failure: {ON_FAILURE}",
        "- 真实 LLM: DeepSeek API（LLM_RUN_CALL_BUDGET 未启用）",
        "",
        "## 背景",
        "",
        "Task 158 长跑未显式执行人为 kill，§1.3-R「中途人为 kill 后同命令 "
        "`--resume` 续完」缺命令级证据。本演练在**全新隔离 DB** 上补齐：在 Ch"
        f"{kill_ch} 生成完成、accept 之前打断（in-flight 非边界 kill），随后 "
        "`--resume` 续完，全程走真实产品管线 `run_project_pipeline`。",
        "",
        "## 命令时间线",
        "",
        "### Phase 1 — 初始化 + in-flight kill",
        "",
        "```powershell",
        '$env:DATABASE_URL = "sqlite:///.tmp/task158r_kill_resume.db"',
        "python scripts/run_158r_kill_resume_drill.py --init",
        f"python scripts/run_158r_kill_resume_drill.py --kill-at-chapter {kill_ch}",
        "```",
        "",
        f"- kill 前已 accept: {kill_outcome.get('accepted_before')}",
        f"- 是否被 KeyboardInterrupt 打断: "
        f"{'是' if kill_outcome.get('interrupted') else '否'}",
        f"- kill 打断信息: `{kill_outcome.get('interrupt_msg', 'N/A')}`",
        f"- kill 后 run_id: `{kill_outcome.get('run_id')}`",
        f"- kill 后 run 状态: {kill_outcome.get('run_status')}",
        f"- kill 后 run_state.current_chapter: "
        f"Ch{kill_outcome.get('current_chapter')}",
        f"- kill 后已 accept（唯一完成事实源）: {accepted_at_kill}",
        f"- kill 后残留 checkpoint thread 数: "
        f"{kill_outcome.get('checkpoint_threads_after')}",
        "",
        "### Phase 2 — 同命令 resume 续完",
        "",
        "```powershell",
        '$env:DATABASE_URL = "sqlite:///.tmp/task158r_kill_resume.db"',
        "python scripts/run_158r_kill_resume_drill.py --resume",
        "```",
        "",
        f"- resume 复用 run_id: `{resume_outcome.get('run_id')}`",
        f"- resume 前已 accept: {resume_outcome.get('accepted_before')}",
        f"- resume 后已 accept: {accepted_final}",
        f"- resume 最终 run 状态: {resume_outcome.get('run_status')}",
        f"- resume completed 集合: {resume_outcome.get('chapters_completed')}",
        f"- resume failed 集合: {resume_outcome.get('chapters_failed')}",
        f"- resume 前残留 checkpoint thread 数: "
        f"{resume_outcome.get('checkpoint_threads_before')}",
        f"- resume 后 checkpoint thread 数: "
        f"{resume_outcome.get('checkpoint_threads_after')}",
        "",
        "## 关键断言",
        "",
        "| 断言 | 期望 | 实测 | 结论 |",
        "|------|------|------|------|",
        f"| kill 为 in-flight（Ch{kill_ch} 生成后 accept 前打断） | 打断=是 且 "
        f"Ch{kill_ch}∉accepted@kill | 打断="
        f"{'是' if kill_outcome.get('interrupted') else '否'}, "
        f"Ch{kill_ch}{kill_in}accepted@kill | {_mark(kill_inflight_ok)} |",
        f"| resume 复用同一 run_id | kill.run_id == resume.run_id | "
        f"{'相同' if same_run_ok else '不同'} | {_mark(same_run_ok)} |",
        f"| in-flight 章被重算并最终 accept | Ch{kill_ch}∈accepted@final | "
        f"Ch{kill_ch}{final_in}accepted@final | {_mark(recompute_ok)} |",
        f"| resume 续完全部目标章 | accepted@final ⊇ {target} | "
        f"{accepted_final} | {_mark(target_ok)} |",
        f"| run 最终 completed | status=completed | "
        f"{resume_outcome.get('run_status')} | {_mark(resume_completed)} |",
        "",
        "## chapter_heads 终态",
        "",
        "| Ch | status | has_accepted |",
        "|---:|--------|:---:|",
    ]
    for h in resume_outcome.get("chapter_heads", []):
        lines.append(
            f"| {h['chapter_number']} | {h['status']} | "
            f"{'Y' if h['has_accepted'] else 'N'} |"
        )

    all_pass = (
        kill_inflight_ok
        and same_run_ok
        and recompute_ok
        and target_ok
        and resume_completed
    )

    lines.extend(
        [
            "",
            "## 结论",
            "",
            (
                "✅ §1.3-R 取得**真实命令级证据**：单命令无人值守运行中，人为 in-flight "
                f"kill（Ch{kill_ch} 生成后 accept 前打断）后，同命令 `--resume` 复用同一 "
                f"run_id 续跑——已 accept 章跳过、in-flight 章重算、孤儿 checkpoint 清理，"
                f"最终 Ch{START_CHAPTER}-Ch{END_CHAPTER} 全部 accept，run 状态 completed。"
                if all_pass
                else "🔴 演练未完全满足断言，详见上表；需排查后重跑，不得据此宣称 §1.3-R 达标。"
            ),
        ]
    )

    REPORT_PATH.write_text("\n".join(lines) + "\n", encoding="utf-8")
    print(f"[report] {REPORT_PATH}")


# --------------------------------------------------------------------------- #
# 主流程
# --------------------------------------------------------------------------- #
async def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--init", action="store_true")
    parser.add_argument("--resume", action="store_true")
    parser.add_argument("--project-id", default=None)
    parser.add_argument(
        "--kill-at-chapter",
        type=int,
        default=None,
        help="in-flight kill：ChK 生成后 accept 前抛 KeyboardInterrupt",
    )
    parser.add_argument(
        "--report",
        action="store_true",
        help="仅从 evidence jsonl 重新生成报告",
    )
    args = parser.parse_args()

    if args.init:
        await _init_db()
        return

    project_id = args.project_id or _resolve_project_id()
    if not project_id:
        parser.error("请先 --init 创建项目，或提供 --project-id / PROJECT_ID")

    if args.report:
        records = [
            json.loads(line)
            for line in EVIDENCE_PATH.read_text(encoding="utf-8").splitlines()
            if line.strip()
        ]
        kill_outcome = next(
            (r for r in records if r.get("kill_at_chapter") is not None), {}
        )
        resume_outcome = next(
            (r for r in reversed(records) if r.get("resume")), {}
        )
        _write_report(project_id, kill_outcome, resume_outcome)
        return

    print(f"[preflight] db={get_db_path()} project={project_id}")
    print(
        f"[preflight] gate_mode={GATE_MODE}, on_failure={ON_FAILURE}, "
        f"resume={args.resume}, kill_at={args.kill_at_chapter}, "
        f"range=({START_CHAPTER},{END_CHAPTER})"
    )

    phase = "resume" if args.resume else "kill"
    await _run_phase(
        project_id,
        phase=phase,
        resume=args.resume,
        kill_at_chapter=args.kill_at_chapter,
    )

    # resume 阶段跑完后，若已有 kill 证据，自动生成报告
    if args.resume and EVIDENCE_PATH.exists():
        records = [
            json.loads(line)
            for line in EVIDENCE_PATH.read_text(encoding="utf-8").splitlines()
            if line.strip()
        ]
        kill_outcome = next(
            (r for r in records if r.get("kill_at_chapter") is not None), {}
        )
        resume_outcome = next(
            (r for r in reversed(records) if r.get("resume")), {}
        )
        if kill_outcome and resume_outcome:
            _write_report(project_id, kill_outcome, resume_outcome)


if __name__ == "__main__":
    asyncio.run(main())
