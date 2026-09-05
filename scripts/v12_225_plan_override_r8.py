"""V12 Task 225 plan override round 8: Ch3 brief style_constraints 篇幅句。

背景：round-11 Ch3-only smoke（run-a3bca9be）convergence_failed——初稿 v-3-22
仅 2418 字（< 2700 硬下限），两轮 patch 不扩写，重写 draft v-3-25 更短（1892）
被字数回滚。r7 已在 chapter_goal.obligations 加篇幅下限，但 Writer 初稿仍持续
欠幅（round 8-11 初稿 2565/2650/2468/2418）。round 9-11 的重写 draft 靠
rewrite.injected_word_count_constraint 达标（3108/2736/2890），说明显式篇幅
句有效，需要前移到 Writer 初稿可见的 style_constraints 通道。

本脚本：
1. 在 Ch3 creative_briefs.style_constraints 末尾追加一条篇幅约束；
2. 在【节奏地图】条目末尾补一句篇幅分配；
3. 重跑确定性 review（round 8），通过后刷新 approved plan。

Usage:
    python scripts/v12_225_plan_override_r8.py
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

LENGTH_ENTRY = (
    "【篇幅约束】全章正文 2700-3300 字（目标 3000 字），不得低于 2700 字。"
    "若写到后段发现接近下限，优先把每个操作 Beat 的系统反馈细节与沈砚的核对动作"
    "写足写细，而不是合并或跳过任何 Beat。"
)
RHYTHM_SUFFIX = "；篇幅分配：六拍各约 450-550 字，全章约 3000 字、不得低于 2700 字"


def override_ch3(con: sqlite3.Connection) -> None:
    head = con.execute(
        "SELECT status, accepted_version_id FROM chapter_heads "
        "WHERE project_id = ? AND chapter_number = 3",
        (PROJECT_ID,),
    ).fetchone()
    if head and head[1]:
        raise RuntimeError(f"Ch3 already accepted ({head[1]}); nothing to override")

    row = con.execute(
        "SELECT style_constraints FROM creative_briefs WHERE brief_id = ?",
        (BRIEF_ID,),
    ).fetchone()
    constraints: list[str] = json.loads(row[0])
    if LENGTH_ENTRY not in constraints:
        constraints.append(LENGTH_ENTRY)
    if constraints and constraints[0].startswith("【节奏地图】"):
        if RHYTHM_SUFFIX not in constraints[0]:
            constraints[0] = constraints[0] + RHYTHM_SUFFIX
    con.execute(
        "UPDATE creative_briefs SET style_constraints = ? WHERE brief_id = ?",
        (json.dumps(constraints, ensure_ascii=False), BRIEF_ID),
    )
    print(f"[225-r8] Ch3 brief {BRIEF_ID} style_constraints -> {len(constraints)} entries, "
          f"rhythm map length clause appended")


async def main() -> int:
    stamp = time.strftime("%H%M%S", time.localtime())
    print(f"[225-r8] V12 Task 225 plan override round 8 (Ch3 style length) - {stamp}")

    con = sqlite3.connect(RUNTIME_DB)
    try:
        override_ch3(con)
        con.commit()
    finally:
        con.close()

    print("\n[225-r8] === re-run deterministic review-plan (round 8) ===")
    plan_result = PlanOnlyResult.model_validate(
        json.loads((PLAN_RUN_DIR / "plan_only_result.json").read_text(encoding="utf-8"))
    )
    spec = load_supervision_spec_file(SPEC_PATH)
    review = await review_plan_only_result(plan_result, spec)
    review_path = PLAN_RUN_DIR / "plan_review_result_round8.json"
    review_path.write_text(
        json.dumps(review.model_dump(mode="json"), ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    print(f"[225-r8] round-8 review saved: {review_path}")
    if review.findings:
        print(f"  REVIEW FAIL: {len(review.findings)} findings")
        for f in review.findings:
            print(f"    - Ch{f.chapter_number} [{f.code}] {f.message}")
            print(f"      evidence: {f.evidence}")
        print("\n[225-r8] STOP: round-8 review rejected. Report to user.")
        return 2

    print("  REVIEW PASS: 0 findings")
    approval = approve_plan_review(review)
    approval_path = PLAN_RUN_DIR / "approved_plan_ch2_3.json"
    save_approved_plan(approval_path, approval)
    print(f"[225-r8] approved-plan refreshed: {approval_path}")
    print("\nNext: Ch3-only smoke retry -- songyan run --project-id "
          f"{PROJECT_ID} --chapters 3-3 --auto-confirm --on-failure isolate")
    return 0


if __name__ == "__main__":
    rc = asyncio.run(main())
    sys.exit(rc)
