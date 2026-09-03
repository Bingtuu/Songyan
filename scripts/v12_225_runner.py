"""V12 Task 225 runner: plan-only + review-plan for Ch2-Ch3 on the 224f project.

背景：Task 224f 已在同一 DB 中完成 Ch1-only closure（project
hard-sf-new-weird-v12-224f-144113，accepted v-e9687c62，人工 GO）。
Task 225 复用该项目，只对 Ch2/Ch3 做 plan-only → review-plan → approve；
real smoke 用 --chapters 1-3，已 accepted 的 Ch1 会被 pipeline 自动跳过
（phase2_graph skip_accepted_chapters），只生成 Ch2/Ch3。

Ch2 的 plan-only 显式传入 Ch1 plot_summary（与真实 pipeline 的
_get_summary_text 行为一致）；Ch3 暂无 Ch2 summary，留空——这是批量
plan-only 的固有限制，与真实顺序流程一致地接受。

Usage:
    python scripts/v12_225_runner.py
"""

from __future__ import annotations

import asyncio
import json
import os
import sqlite3
import sys
import time
from pathlib import Path

# 项目根
ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "src"))

SPEC_PATH = ROOT / "projects" / "hard-sf-new-weird" / "planning" / "supervision_spec.json"
RUN_DIR = ROOT / "projects" / "hard-sf-new-weird" / "runs"
RUNTIME_DB = ROOT / "projects" / "hard-sf-new-weird" / "runtime" / "songyan.db"

PROJECT_ID = "hard-sf-new-weird-v12-224f-144113"
PLAN_CHAPTERS = [2, 3]

# 环境：DB + supervision spec（必须在 import songyan 之前设置）
os.environ["DATABASE_URL"] = f"sqlite:///{RUNTIME_DB.as_posix()}"
os.environ["CHECKPOINTER_MODE"] = "sqlite"
os.environ["SONGYAN_STARTUP_SUPERVISION_SPEC"] = str(SPEC_PATH)

from songyan.services.plan_review import (  # noqa: E402
    approve_plan_review,
    review_plan_only_result,
    run_plan_only,
    save_approved_plan,
)
from songyan.services.supervision_spec import load_supervision_spec_file  # noqa: E402

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")


def gen_suffix() -> str:
    return time.strftime("%H%M%S", time.localtime())


def load_previous_summaries(project_id: str) -> dict[int, str]:
    """为 plan-only 提供 previous_summary：Ch2 用 Ch1 plot_summary，Ch3 留空。

    与 phase2_graph._get_summary_text 口径一致（只取 plot_summary）。
    """
    con = sqlite3.connect(RUNTIME_DB)
    try:
        row = con.execute(
            """SELECT plot_summary FROM summaries
               WHERE project_id = ? AND chapter_number = 1
               ORDER BY created_at DESC LIMIT 1""",
            (project_id,),
        ).fetchone()
        if row is None:
            raise RuntimeError(f"Ch1 summary not found for {project_id}; 224f 未闭环？")
        print(f"[225] loaded Ch1 plot_summary for Ch2 plan-only ({len(row[0])} chars)")
        return {2: row[0]}
    finally:
        con.close()


def check_preconditions(project_id: str) -> None:
    """确认 Ch1 已 accepted 且 Ch2/Ch3 尚无 chapter 产物。"""
    con = sqlite3.connect(RUNTIME_DB)
    try:
        head = con.execute(
            "SELECT status, accepted_version_id FROM chapter_heads "
            "WHERE project_id = ? AND chapter_number = 1",
            (project_id,),
        ).fetchone()
        if head is None or head[0] != "accepted" or not head[1]:
            raise RuntimeError(f"Ch1 head not accepted for {project_id}: {head}")
        existing = con.execute(
            "SELECT chapter_number, version_id FROM chapter_versions "
            "WHERE project_id = ? AND chapter_number IN (2, 3)",
            (project_id,),
        ).fetchall()
        if existing:
            raise RuntimeError(f"Ch2/Ch3 already have versions for {project_id}: {existing}")
        print(f"[225] preconditions OK: Ch1 accepted ({head[1]}), Ch2/Ch3 clean")
    finally:
        con.close()


async def step_plan_only(project_id: str):
    print(f"\n[225] === plan-only for Ch{PLAN_CHAPTERS} (project={project_id}) ===")
    prev = load_previous_summaries(project_id)
    result = await run_plan_only(
        project_id=project_id,
        chapters=PLAN_CHAPTERS,
        previous_summary_by_chapter=prev,
    )
    for art in result.artifacts:
        print(f"  - Ch{art.chapter_number}: goal={art.chapter_goal_id} brief={art.creative_brief_id}")
    return result


async def step_review(plan_result):
    print("\n[225] === deterministic review-plan ===")
    spec = load_supervision_spec_file(SPEC_PATH)
    review = await review_plan_only_result(plan_result, spec)
    if review.findings:
        print(f"  REVIEW FAIL: {len(review.findings)} findings")
        for f in review.findings:
            print(f"    - Ch{f.chapter_number} [{f.code}] {f.message}")
            print(f"      evidence: {f.evidence}")
    else:
        print("  REVIEW PASS: 0 findings")
    return review


def step_save_artifacts(plan_result, review, stamp: str) -> Path | None:
    run_dir = RUN_DIR / f"v12_task225_ch2_3_plan_{stamp}"
    run_dir.mkdir(parents=True, exist_ok=True)

    plan_path = run_dir / "plan_only_result.json"
    plan_path.write_text(
        json.dumps(plan_result.model_dump(mode="json"), ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    print(f"  plan-only saved: {plan_path}")

    review_path = run_dir / "plan_review_result.json"
    review_path.write_text(
        json.dumps(review.model_dump(mode="json"), ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    print(f"  review-plan saved: {review_path}")

    if not review.passed:
        return None

    approval = approve_plan_review(review)
    approval_path = run_dir / "approved_plan_ch2_3.json"
    save_approved_plan(approval_path, approval)
    print(f"  approved-plan saved: {approval_path}")
    return approval_path


async def main() -> int:
    stamp = gen_suffix()

    print(f"[225] V12 Task 225 Ch2-Ch3 plan closure - started at {stamp}")
    print(f"[225] project_id        : {PROJECT_ID}")
    print(f"[225] plan chapters     : {PLAN_CHAPTERS}")
    print(f"[225] supervision spec  : {SPEC_PATH}")

    check_preconditions(PROJECT_ID)

    plan_result = await step_plan_only(PROJECT_ID)
    review = await step_review(plan_result)
    approval_path = step_save_artifacts(plan_result, review, stamp)

    if not review.passed:
        print("\n[225] STOP: review-plan rejected. Report findings to user; do NOT auto-retry.")
        return 2

    print("\n" + "=" * 60)
    print("[225] Plan review PASSED. Now run REAL SMOKE with:")
    print("=" * 60)
    print(f"""
$env:DATABASE_URL = "sqlite:///{RUNTIME_DB.as_posix()}"
$env:CHECKPOINTER_MODE = "sqlite"
$env:SONGYAN_STARTUP_SUPERVISION_SPEC = "{SPEC_PATH}"
$env:SONGYAN_STARTUP_APPROVED_PLAN = "{approval_path}"

powershell -File scripts/run_with_timeout.ps1 -TimeoutSec 7200 -- `
  songyan run --project-id {PROJECT_ID} --chapters 1-3 --auto-confirm --on-failure isolate
""")
    print("(Ch1 已 accepted，会被 pipeline 自动跳过，只实际生成 Ch2/Ch3)")
    print("After run completes:")
    print(f"""
songyan report --project-id {PROJECT_ID} --last-run
songyan export --project-id {PROJECT_ID} --chapters 1-3 --format md --output projects/hard-sf-new-weird/exports/ch001_003_round_v12_225/
songyan bundle-run --run-id <run_id> --output projects/hard-sf-new-weird/bundles/
""")
    return 0


if __name__ == "__main__":
    rc = asyncio.run(main())
    sys.exit(rc)
