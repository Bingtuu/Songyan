"""V12 Task 225 plan override round 5: Ch3 previous_summary 同步（Ch2 重跑后）。

背景：round-4 把 Ch2 plan 修到 27 系并重跑 Ch2。Ch3 的 plan 行
（goal gp-70c54a2d / brief cb-33cc65c0）内容无数值引用、round-3 已定型，
唯一缺口是 previous_summary——round-1 plan-only 时 Ch3 留空（当时 Ch2 尚无
summary），且旧 Ch2 summary 已在回滚中删除。本脚本在 Ch2 重新 accepted 后，
把 Ch3 goal 的 previous_summary 同步为新 Ch2 plot_summary（并同步
brief.chapter_goal 冗余拷贝），重跑确定性 review（round 5）后刷新
approved plan。

previous_summary 已被 c7f510e 扫描器校准排除在 _plan_text 之外，本同步对
review findings 中性。

Usage:
    python scripts/v12_225_plan_override_r5.py
"""

from __future__ import annotations

import asyncio
import json
import os
import sqlite3
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "src"))

SPEC_PATH = ROOT / "projects" / "hard-sf-new-weird" / "planning" / "supervision_spec.json"
RUNTIME_DB = ROOT / "projects" / "hard-sf-new-weird" / "runtime" / "songyan.db"
PLAN_RUN_DIR = (
    ROOT / "projects" / "hard-sf-new-weird" / "runs" / "v12_task225_ch2_3_plan_200216"
)
PROJECT_ID = "hard-sf-new-weird-v12-224f-144113"
GOAL_ID = "gp-70c54a2d"
BRIEF_ID = "cb-33cc65c0"

os.environ["DATABASE_URL"] = f"sqlite:///{RUNTIME_DB.as_posix()}"
os.environ["CHECKPOINTER_MODE"] = "sqlite"
os.environ["SONGYAN_STARTUP_SUPERVISION_SPEC"] = str(SPEC_PATH)

from songyan.models import PlanOnlyResult  # noqa: E402
from songyan.services.plan_review import (  # noqa: E402
    approve_plan_review,
    review_plan_only_result,
    save_approved_plan,
)
from songyan.services.supervision_spec import load_supervision_spec_file  # noqa: E402

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")


def sync_previous_summary(con: sqlite3.Connection) -> None:
    head2 = con.execute(
        "SELECT status, accepted_version_id FROM chapter_heads "
        "WHERE project_id = ? AND chapter_number = 2",
        (PROJECT_ID,),
    ).fetchone()
    if not head2 or not head2[1]:
        raise RuntimeError(f"Ch2 not accepted yet: {head2}; run Ch2 smoke first")
    head3 = con.execute(
        "SELECT status, accepted_version_id FROM chapter_heads "
        "WHERE project_id = ? AND chapter_number = 3",
        (PROJECT_ID,),
    ).fetchone()
    if head3 and head3[1]:
        raise RuntimeError(f"Ch3 already accepted ({head3[1]}); nothing to sync")

    row = con.execute(
        "SELECT plot_summary FROM summaries "
        "WHERE project_id = ? AND chapter_number = 2 "
        "ORDER BY created_at DESC LIMIT 1",
        (PROJECT_ID,),
    ).fetchone()
    if row is None:
        raise RuntimeError("Ch2 summary not found; Ch2 settlement incomplete?")
    new_summary: str = row[0]

    # 19 系污染防线：新 Ch2 summary 不得含旧数值线 token
    for bad in ("19.0", "21.0", "16.0", "13.0"):
        if bad in new_summary:
            raise RuntimeError(
                f"new Ch2 summary contains stale 19-series token {bad!r}; "
                "do not sync polluted summary into Ch3 plan"
            )

    con.execute(
        "UPDATE chapter_goals SET previous_summary = ? WHERE goal_id = ?",
        (new_summary, GOAL_ID),
    )

    goal_row = con.execute(
        "SELECT chapter_number, previous_summary, target_events, emotional_arc, hooks,"
        " obligations, word_count_target, chapter_type, derived_from_arc"
        " FROM chapter_goals WHERE goal_id = ?",
        (GOAL_ID,),
    ).fetchone()
    goal_payload = {
        "chapter_number": goal_row[0],
        "previous_summary": goal_row[1],
        "target_events": json.loads(goal_row[2]),
        "emotional_arc": goal_row[3],
        "hooks": json.loads(goal_row[4]),
        "obligations": json.loads(goal_row[5]),
        "word_count_target": goal_row[6],
        "chapter_type": goal_row[7],
        "derived_from_arc": goal_row[8],
    }
    con.execute(
        "UPDATE creative_briefs SET chapter_goal = ? WHERE brief_id = ?",
        (json.dumps(goal_payload, ensure_ascii=False), BRIEF_ID),
    )
    print(
        f"[225-r5] Ch3 goal {GOAL_ID} previous_summary synced "
        f"({len(new_summary)} chars from new Ch2), brief.chapter_goal refreshed"
    )


async def main() -> int:
    stamp = time.strftime("%H%M%S", time.localtime())
    print(f"[225-r5] V12 Task 225 plan override round 5 (Ch3 prev_summary) - {stamp}")

    con = sqlite3.connect(RUNTIME_DB)
    try:
        sync_previous_summary(con)
        con.commit()
    finally:
        con.close()

    print("\n[225-r5] === re-run deterministic review-plan (round 5) ===")
    plan_result = PlanOnlyResult.model_validate(
        json.loads((PLAN_RUN_DIR / "plan_only_result.json").read_text(encoding="utf-8"))
    )
    spec = load_supervision_spec_file(SPEC_PATH)
    review = await review_plan_only_result(plan_result, spec)
    review_path = PLAN_RUN_DIR / "plan_review_result_round5.json"
    review_path.write_text(
        json.dumps(review.model_dump(mode="json"), ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    print(f"[225-r5] round-5 review saved: {review_path}")
    if review.findings:
        print(f"  REVIEW FAIL: {len(review.findings)} findings")
        for f in review.findings:
            print(f"    - Ch{f.chapter_number} [{f.code}] {f.message}")
            print(f"      evidence: {f.evidence}")
        print("\n[225-r5] STOP: round-5 review rejected. Report to user.")
        return 2

    print("  REVIEW PASS: 0 findings")
    approval = approve_plan_review(review)
    approval_path = PLAN_RUN_DIR / "approved_plan_ch2_3.json"
    save_approved_plan(approval_path, approval)
    print(f"[225-r5] approved-plan refreshed: {approval_path}")
    print("\nNext: Ch3-only smoke -- songyan run --project-id "
          f"{PROJECT_ID} --chapters 3-3 --auto-confirm --on-failure isolate")
    return 0


if __name__ == "__main__":
    rc = asyncio.run(main())
    sys.exit(rc)
