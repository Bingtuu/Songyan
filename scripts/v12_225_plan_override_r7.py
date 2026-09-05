"""V12 Task 225 plan override round 7: Ch3 篇幅下限 obligation 追加。

背景：round-7 Ch3-only smoke（run-48405d84）失败——非重复问题，是长度收敛失败：
初稿 v-3-9 即只有 2565 字（< 2700 硬下限），两轮 patch 修订只修 issue 不扩写
（round-2 甚至 no_patchable_issues），重写 draft v-3-12 更短（2185）被字数回滚，
convergence_failed。length 门（needs_revision 恒 True）锁死 accept。

Ch3 goal/brief 现有 obligation 只限制"不得在单一 Beat 上超支导致后续 Beat 缺失"
（上限侧），没有下限侧表述。本脚本追加一条篇幅下限 obligation（Writer 可见的
chapter_goal.obligations 通道），并同步 brief.chapter_goal 冗余拷贝；重跑确定性
review（round 7），通过后刷新 approved plan。

Usage:
    python scripts/v12_225_plan_override_r7.py
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

NEW_OBLIGATION = (
    "篇幅硬约束：全章正文不少于 2700 字（目标 3000 字）。六个施工 Beat 按每个约 "
    "450-550 字均衡分配，每个 Beat 都必须有完整的操作动作—系统反馈—沈砚决定三段"
    "展开，不得压缩合并或一笔带过。"
)


def override_ch3(con: sqlite3.Connection) -> None:
    head = con.execute(
        "SELECT status, accepted_version_id FROM chapter_heads "
        "WHERE project_id = ? AND chapter_number = 3",
        (PROJECT_ID,),
    ).fetchone()
    if head and head[1]:
        raise RuntimeError(f"Ch3 already accepted ({head[1]}); nothing to override")

    row = con.execute(
        "SELECT obligations FROM chapter_goals WHERE goal_id = ?", (GOAL_ID,)
    ).fetchone()
    obligations: list[str] = json.loads(row[0])
    if NEW_OBLIGATION not in obligations:
        obligations.append(NEW_OBLIGATION)
    con.execute(
        "UPDATE chapter_goals SET obligations = ? WHERE goal_id = ?",
        (json.dumps(obligations, ensure_ascii=False), GOAL_ID),
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
    print(f"[225-r7] Ch3 goal {GOAL_ID} obligations -> {len(obligations)} entries, "
          f"brief.chapter_goal refreshed")


async def main() -> int:
    stamp = time.strftime("%H%M%S", time.localtime())
    print(f"[225-r7] V12 Task 225 plan override round 7 (Ch3 length floor) - {stamp}")

    con = sqlite3.connect(RUNTIME_DB)
    try:
        override_ch3(con)
        con.commit()
    finally:
        con.close()

    print("\n[225-r7] === re-run deterministic review-plan (round 7) ===")
    plan_result = PlanOnlyResult.model_validate(
        json.loads((PLAN_RUN_DIR / "plan_only_result.json").read_text(encoding="utf-8"))
    )
    spec = load_supervision_spec_file(SPEC_PATH)
    review = await review_plan_only_result(plan_result, spec)
    review_path = PLAN_RUN_DIR / "plan_review_result_round7.json"
    review_path.write_text(
        json.dumps(review.model_dump(mode="json"), ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    print(f"[225-r7] round-7 review saved: {review_path}")
    if review.findings:
        print(f"  REVIEW FAIL: {len(review.findings)} findings")
        for f in review.findings:
            print(f"    - Ch{f.chapter_number} [{f.code}] {f.message}")
            print(f"      evidence: {f.evidence}")
        print("\n[225-r7] STOP: round-7 review rejected. Report to user.")
        return 2

    print("  REVIEW PASS: 0 findings")
    approval = approve_plan_review(review)
    approval_path = PLAN_RUN_DIR / "approved_plan_ch2_3.json"
    save_approved_plan(approval_path, approval)
    print(f"[225-r7] approved-plan refreshed: {approval_path}")
    print("\nNext: Ch3-only smoke retry -- songyan run --project-id "
          f"{PROJECT_ID} --chapters 3-3 --auto-confirm --on-failure isolate")
    return 0


if __name__ == "__main__":
    rc = asyncio.run(main())
    sys.exit(rc)
