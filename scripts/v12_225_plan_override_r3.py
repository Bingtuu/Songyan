"""V12 Task 225 plan override round 3: Ch3-only 增量覆写 + Ch3-only smoke 前置.

背景：round-2 覆写后 real smoke（run-67f225ff）Ch2 accepted（v-d00dd445，
3299 字，元引用零命中），Ch3 被 summary missing facts 门拦下
（"缺少主角决策/认知变化"）。人工通读 Ch3 被拦正文 rev-3-2 发现三个硬伤：

1. beats 3-6 完全未写——全文停在沙盒回放后的大段锁舌二次谐波自创推演，
   未走到关闭外部同步 / 不确认对象身份 / 缺失主语归档 / 只读介质封存；
2. 「第1章」元引用泄漏——brief「设定回收约束」块的元标注"引入第1章，最近
   提及第1章"被 Writer 直接抄进正文（"第1章复核时留下的监测记录"）；
3. 「复核员留下的批注」——凭空出现半具名角色，擦边 224f 已前移的红线。

本脚本对 Ch3 做增量覆写（Ch2 已 accepted，不动）：

- goal obligations 追加：六 Beat 全覆盖要求 + 决策锚点句
  「沈砚决定带走只读介质，并保留会话未关闭」（取自 spec beat 6 原文）；
- brief forbidden_patterns 追加：禁止「第N章/本章」元引用、禁止「复核员/
  值班员/技术员」等具名或半具名角色；
- brief style_constraints 保留块消毒：剥除「引入第N章，最近提及第N章」与
  「引入 ChN，最近 ChN」元标注（泄漏源）；
- 同步 brief.chapter_goal 冗余拷贝；
- 重跑确定性 review（round 3），通过后重新生成 approved_plan_ch2_3.json。

Usage:
    python scripts/v12_225_plan_override_r3.py
"""

from __future__ import annotations

import asyncio
import json
import os
import re
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

GOAL_ID = "gp-70c54a2d"
BRIEF_ID = "cb-33cc65c0"

NEW_OBLIGATIONS = [
    "必须覆盖全部六个施工 Beat（沙盒建立与V-0003、并列证据、关闭外部同步、不确认对象身份、"
    "缺失主语归档、只读介质封存），不得在单一 Beat 上超支篇幅导致后续 Beat 缺失。",
    "必须落地决策锚点句：沈砚决定带走只读介质，并保留会话未关闭。",
]

NEW_FORBIDDEN = [
    "【可执行约束】禁止正文出现'第1章''第2章''本章'等元引用——角色不知道章节编号，"
    "此前事件只能以'前两份材料''封存链''上一份记录'等故事内称呼指代。",
    "【可执行约束】禁止出现'复核员''值班员''技术员'等任何具名或半具名角色——所有记录、"
    "批注与日志的来源只能是系统、协议文本或无署名数据。",
]

# 元标注消毒：剥除 setting 回收/概念预算块中的章节编号标注（Writer 会抄进正文）
_META_ZH = re.compile(r"，引入第\d+章，最近提及第\d+章")
_META_EN = re.compile(r"，引入 Ch\d+，最近 Ch\d+")


def _j(value: object) -> str:
    return json.dumps(value, ensure_ascii=False)


def sanitize_meta(text: str) -> str:
    return _META_EN.sub("", _META_ZH.sub("", text))


def main_precheck(con: sqlite3.Connection) -> None:
    head = con.execute(
        "SELECT status, accepted_version_id FROM chapter_heads "
        "WHERE project_id = ? AND chapter_number = 3",
        ("hard-sf-new-weird-v12-224f-144113",),
    ).fetchone()
    if head and head[1]:
        raise RuntimeError(f"Ch3 already accepted ({head[1]}); nothing to override")
    print(f"[225-r3] precheck OK: Ch3 head status={head[0] if head else None} (not accepted)")


def override_ch3(con: sqlite3.Connection) -> None:
    # --- goal：追加 obligations ---
    row = con.execute(
        "SELECT obligations FROM chapter_goals WHERE goal_id = ?", (GOAL_ID,)
    ).fetchone()
    obligations: list[str] = json.loads(row[0])
    for item in NEW_OBLIGATIONS:
        if item not in obligations:
            obligations.append(item)
    con.execute(
        "UPDATE chapter_goals SET obligations = ? WHERE goal_id = ?",
        (_j(obligations), GOAL_ID),
    )

    # --- brief：追加 forbidden_patterns + 消毒 style_constraints + 同步 chapter_goal ---
    brow = con.execute(
        "SELECT forbidden_patterns, style_constraints FROM creative_briefs WHERE brief_id = ?",
        (BRIEF_ID,),
    ).fetchone()
    forbidden: list[str] = json.loads(brow[0])
    for item in NEW_FORBIDDEN:
        if item not in forbidden:
            forbidden.append(item)
    style: list[str] = [sanitize_meta(s) for s in json.loads(brow[1])]

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
        "obligations": obligations,
        "word_count_target": goal_row[6],
        "chapter_type": goal_row[7],
        "derived_from_arc": goal_row[8],
    }
    con.execute(
        """UPDATE creative_briefs
           SET forbidden_patterns = ?, style_constraints = ?, chapter_goal = ?
           WHERE brief_id = ?""",
        (_j(forbidden), _j(style), _j(goal_payload), BRIEF_ID),
    )
    print(f"[225-r3] Ch3 goal {GOAL_ID} + brief {BRIEF_ID} overridden")
    print(f"[225-r3] obligations={len(obligations)} forbidden={len(forbidden)} style={len(style)}")


async def main() -> int:
    stamp = time.strftime("%H%M%S", time.localtime())
    print(f"[225-r3] V12 Task 225 plan override round 3 (Ch3-only) - {stamp}")

    con = sqlite3.connect(RUNTIME_DB)
    try:
        main_precheck(con)
        override_ch3(con)
        con.commit()
    finally:
        con.close()

    plan_result = PlanOnlyResult.model_validate(
        json.loads((PLAN_RUN_DIR / "plan_only_result.json").read_text(encoding="utf-8"))
    )
    spec = load_supervision_spec_file(SPEC_PATH)
    review = await review_plan_only_result(plan_result, spec)
    review_path = PLAN_RUN_DIR / "plan_review_result_round3.json"
    review_path.write_text(
        json.dumps(review.model_dump(mode="json"), ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    print(f"[225-r3] round-3 review saved: {review_path}")
    if review.findings:
        print(f"  REVIEW FAIL: {len(review.findings)} findings")
        for f in review.findings:
            print(f"    - Ch{f.chapter_number} [{f.code}] {f.message}")
            print(f"      evidence: {f.evidence}")
        print("\n[225-r3] STOP: round-3 review rejected. Report to user.")
        return 2

    print("  REVIEW PASS: 0 findings")
    approval = approve_plan_review(review)
    approval_path = PLAN_RUN_DIR / "approved_plan_ch2_3.json"
    save_approved_plan(approval_path, approval)
    print(f"[225-r3] approved-plan refreshed: {approval_path}")
    print("\nNext: python scripts/v12_225_smoke_ch3.py")
    return 0


if __name__ == "__main__":
    rc = asyncio.run(main())
    sys.exit(rc)
