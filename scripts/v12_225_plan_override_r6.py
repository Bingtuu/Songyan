"""V12 Task 225 plan override round 6: Ch2 brief 追加禁令（相对时间/注释/元引用）。

背景：round-4 后 Ch2-only smoke（run-bf87f214）失败——startup validation 以
blocker 拦下最终 draft v-2-9：正文两处用「三天前」相对时间指代 Ch1 封存事件
（spec forbidden pattern 真阳性），另有 forbidden literal「注释」一处
（"像是系统自动生成的注释"）。数值线验证通过：被拦正文全程 27 系
（27.0→30.0kg、呼吸 12.0→11.0、已确认 19.0+缺口 8.0），说明 round-4 覆写
已生效，唯一缺口是 Writer 看不到 spec 的 forbidden_literals/patterns
（它们是门级约束），brief.forbidden_patterns 才是 Writer 可见的禁令通道。

本脚本对 Ch2 brief（cb-5e710389）追加三条禁令（与 r3 对 Ch3 的处理同构）：
  1. 禁「第N章/本章」元引用（旧 Ch2 accepted 正文曾有「第一章」中文数字变体）；
  2. 禁相对时间指代此前事件——条目内用 'N天前' 占位，不写实例（plan review
     扫描 _plan_text 含 forbidden_patterns 字段，写真实例会自触发）；
  3. 系统生成文字只能称「短协议/灰色小字/提示/回执」——不点名被禁词
     （同理避免自触发 forbidden literal 扫描）。

goal 行不动。覆写后重跑确定性 review（round 6），通过后刷新 approved plan。

Usage:
    python scripts/v12_225_plan_override_r6.py
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
BRIEF_ID = "cb-5e710389"

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

NEW_FORBIDDEN = [
    "【可执行约束】禁止正文出现'第1章''第2章''本章'等元引用——角色不知道章节编号，"
    "此前事件只能以'封存链''第一份材料''上一份记录'等故事内称呼指代。",
    "【可执行约束】禁止用相对时间指代此前事件（'N天前''N年前''N个月前'等）——封存链"
    "上的事件没有日期，只能以'封存时''上次复核'等故事内时点称呼。",
    "【可执行约束】系统生成的文字只能称为'短协议''灰色小字''提示'或'回执'，不得使用"
    "其他名目（特别是编辑/文档类术语）。",
]


def main_override(con: sqlite3.Connection) -> None:
    head = con.execute(
        "SELECT status, accepted_version_id FROM chapter_heads "
        "WHERE project_id = ? AND chapter_number = 2",
        (PROJECT_ID,),
    ).fetchone()
    if head and head[1]:
        raise RuntimeError(f"Ch2 already accepted ({head[1]}); nothing to override")

    row = con.execute(
        "SELECT forbidden_patterns FROM creative_briefs WHERE brief_id = ?", (BRIEF_ID,)
    ).fetchone()
    forbidden: list[str] = json.loads(row[0])
    for item in NEW_FORBIDDEN:
        if item not in forbidden:
            forbidden.append(item)
    con.execute(
        "UPDATE creative_briefs SET forbidden_patterns = ? WHERE brief_id = ?",
        (json.dumps(forbidden, ensure_ascii=False), BRIEF_ID),
    )
    print(f"[225-r6] Ch2 brief {BRIEF_ID} forbidden_patterns -> {len(forbidden)} entries")


async def main() -> int:
    stamp = time.strftime("%H%M%S", time.localtime())
    print(f"[225-r6] V12 Task 225 plan override round 6 (Ch2 forbidden+) - {stamp}")

    con = sqlite3.connect(RUNTIME_DB)
    try:
        main_override(con)
        con.commit()
    finally:
        con.close()

    print("\n[225-r6] === re-run deterministic review-plan (round 6) ===")
    plan_result = PlanOnlyResult.model_validate(
        json.loads((PLAN_RUN_DIR / "plan_only_result.json").read_text(encoding="utf-8"))
    )
    spec = load_supervision_spec_file(SPEC_PATH)
    review = await review_plan_only_result(plan_result, spec)
    review_path = PLAN_RUN_DIR / "plan_review_result_round6.json"
    review_path.write_text(
        json.dumps(review.model_dump(mode="json"), ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    print(f"[225-r6] round-6 review saved: {review_path}")
    if review.findings:
        print(f"  REVIEW FAIL: {len(review.findings)} findings")
        for f in review.findings:
            print(f"    - Ch{f.chapter_number} [{f.code}] {f.message}")
            print(f"      evidence: {f.evidence}")
        print("\n[225-r6] STOP: round-6 review rejected. Report to user.")
        return 2

    print("  REVIEW PASS: 0 findings")
    approval = approve_plan_review(review)
    approval_path = PLAN_RUN_DIR / "approved_plan_ch2_3.json"
    save_approved_plan(approval_path, approval)
    print(f"[225-r6] approved-plan refreshed: {approval_path}")
    print("\nNext: Ch2-only smoke retry -- songyan run --project-id "
          f"{PROJECT_ID} --chapters 2-2 --auto-confirm --on-failure isolate")
    return 0


if __name__ == "__main__":
    rc = asyncio.run(main())
    sys.exit(rc)
