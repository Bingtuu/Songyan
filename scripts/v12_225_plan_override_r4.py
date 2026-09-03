"""V12 Task 225 plan override round 4: Ch2 数值线 19 系 → 27 系修正。

背景：225 人工读稿判定 Ch2 STOP——spec v12.1 的 Ch2 beats 写 19.0kg 系并自称
"与第一章封存链上的整数缺口一致"，但 Ch1 accepted 正文（v-e9687c62）实际是
27.00kg；spec 自身 Ch1 beats 也写"二十七公斤"。spec 与 Ch1 正文从未对账。
呼吸线同样失真：Ch1 结尾呼吸频率已稳定在每分钟十二次（14→12），spec Ch2 却写
"稳定在 13.0 次/分"再"13.0→12.0"。

spec 已修为 v12.2（27.0kg 缺口、六段 4.0×5+7.0=27.0、第二四段 8.0kg、
已确认 19.0kg、测试增量 +3.0→30.0kg、呼吸 12.0→11.0 次/分）。
Ch2/Ch3 结算产物已回滚（scripts/v12_225_rollback_ch2_ch3.py），head 已置空。

本脚本只对 Ch2 的 round-2 覆写行（goal gp-eed7c78c / brief cb-5e710389）做
有序数值替换，不重跑 plan-only（结构已经 round-2/round-3 review 定型，本次只
修正数值）。替换后重跑确定性 review（round 4），通过后刷新 approved plan。

Ch3 行（gp-70c54a2d / cb-33cc65c0）不含数值引用，本脚本不动；Ch3 的
previous_summary 待 Ch2 重新 accepted 后由单独步骤同步。

Usage:
    python scripts/v12_225_plan_override_r4.py
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
PROJECT_ID = "hard-sf-new-weird-v12-224f-144113"
GOAL_ID = "gp-eed7c78c"
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

# 有序替换规则（顺序敏感：先处理复合形态，再处理裸数值）。
# 呼吸线：Ch1 结尾已稳定 12.0 次/分 → Ch2 开场"读数稳定在 13.0"改为 12.0；
# 测试降速 13.0→12.0 改为 12.0→11.0；接收后"频率稳定在 12.0"改为 11.0。
# 质量线：缺口 19.0→27.0；六段 3.0×5+4.0→4.0×5+7.0；无画面两段 6.0→8.0；
# 测试增量 2.0→3.0；接收 21.0→30.0。
RULES: list[tuple[str, str]] = [
    ("读数稳定在13.0次/分", "读数稳定在12.0次/分"),
    ("13.0→12.0次/分", "12.0→11.0次/分"),
    ("频率稳定在12.0次/分", "频率稳定在11.0次/分"),
    ("3.0kg×5与4.0kg", "4.0kg×5与7.0kg"),
    ("第一段3.0kg", "第一段4.0kg"),
    ("6.0kg", "8.0kg"),
    ("增加2.0kg", "增加3.0kg"),
    ("19.0kg", "27.0kg"),
    ("21.0kg", "30.0kg"),
    ("。19.0，", "。27.0，"),
]

# 替换后不允许残留的 19 系 token（"增加3.0kg" 是唯一合法的 3.0kg）
LEFTOVER_RE = re.compile(r"13\.0|16\.0|19\.0|21\.0|3\.0kg×5|6\.0kg|2\.0kg")

GOAL_JSON_FIELDS = ("target_events", "hooks")
BRIEF_JSON_FIELDS = (
    "required_tensions",
    "allowed_fissures",
    "style_constraints",
    "voice_samples",
    "protagonist_active_choice",
    "new_concept_budget",
)
BRIEF_TEXT_FIELDS = ("creative_intent",)


def _apply_rules(text: str) -> str:
    for old, new in RULES:
        text = text.replace(old, new)
    return text


def _check_clean(label: str, text: str) -> None:
    hits = LEFTOVER_RE.findall(text)
    if hits:
        raise RuntimeError(f"[225-r4] {label} leftover 19-series tokens: {hits}")
    for m in re.finditer(r"3\.0kg", text):
        ctx = text[max(0, m.start() - 6) : m.end()]
        if "增加3.0kg" not in ctx:
            raise RuntimeError(f"[225-r4] {label} unexpected 3.0kg at: ...{ctx}...")


def override_ch2(con: sqlite3.Connection) -> None:
    # --- goal：target_events / hooks ---
    row = con.execute(
        "SELECT target_events, hooks FROM chapter_goals WHERE goal_id = ?", (GOAL_ID,)
    ).fetchone()
    new_goal_values = []
    for i, raw in enumerate(row):
        items = json.loads(raw)
        new_items = [json.loads(_apply_rules(json.dumps(s, ensure_ascii=False))) for s in items]
        for s in new_items:
            _check_clean(f"goal.{GOAL_JSON_FIELDS[i]}", s)
        new_goal_values.append(json.dumps(new_items, ensure_ascii=False))
    con.execute(
        "UPDATE chapter_goals SET target_events = ?, hooks = ? WHERE goal_id = ?",
        (*new_goal_values, GOAL_ID),
    )

    # --- brief：JSON 字段 + 文本字段 + chapter_goal 冗余拷贝同步 ---
    cols = ", ".join(BRIEF_JSON_FIELDS + BRIEF_TEXT_FIELDS)
    brow = con.execute(
        f"SELECT {cols} FROM creative_briefs WHERE brief_id = ?", (BRIEF_ID,)
    ).fetchone()
    updates: dict[str, str] = {}
    for name, raw in zip(BRIEF_JSON_FIELDS + BRIEF_TEXT_FIELDS, brow, strict=True):
        new_raw = _apply_rules(raw)
        _check_clean(f"brief.{name}", new_raw)
        updates[name] = new_raw

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
    updates["chapter_goal"] = json.dumps(goal_payload, ensure_ascii=False)
    _check_clean("brief.chapter_goal", updates["chapter_goal"])

    set_clause = ", ".join(f"{k} = ?" for k in updates)
    con.execute(
        f"UPDATE creative_briefs SET {set_clause} WHERE brief_id = ?",
        (*updates.values(), BRIEF_ID),
    )
    print(f"[225-r4] Ch2 goal {GOAL_ID} + brief {BRIEF_ID} 27-series override applied")
    for k in updates:
        print(f"  - brief.{k}: updated")


async def main() -> int:
    stamp = time.strftime("%H%M%S", time.localtime())
    print(f"[225-r4] V12 Task 225 plan override round 4 (Ch2 27-series) - {stamp}")

    con = sqlite3.connect(RUNTIME_DB)
    try:
        head = con.execute(
            "SELECT status, accepted_version_id FROM chapter_heads "
            "WHERE project_id = ? AND chapter_number = 2",
            (PROJECT_ID,),
        ).fetchone()
        if head and head[1]:
            raise RuntimeError(f"Ch2 already accepted ({head[1]}); nothing to override")
        override_ch2(con)
        con.commit()
    finally:
        con.close()

    # 覆写内容留档
    con = sqlite3.connect(RUNTIME_DB)
    try:
        con.row_factory = sqlite3.Row
        dump = {
            "overridden_at": stamp,
            "round": 4,
            "note": "Ch2 数值线 19 系 → 27 系（对齐 spec v12.2 与 Ch1 accepted 正文）；"
            "规则见脚本 RULES",
            "goal": dict(
                con.execute(
                    "SELECT * FROM chapter_goals WHERE goal_id = ?", (GOAL_ID,)
                ).fetchone()
            ),
            "brief": dict(
                con.execute(
                    "SELECT * FROM creative_briefs WHERE brief_id = ?", (BRIEF_ID,)
                ).fetchone()
            ),
        }
    finally:
        con.close()
    dump_path = PLAN_RUN_DIR / "plan_override_round4.json"
    dump_path.write_text(
        json.dumps(dump, ensure_ascii=False, indent=2, default=str), encoding="utf-8"
    )
    print(f"[225-r4] override dump saved: {dump_path}")

    print("\n[225-r4] === re-run deterministic review-plan (round 4) ===")
    plan_result = PlanOnlyResult.model_validate(
        json.loads((PLAN_RUN_DIR / "plan_only_result.json").read_text(encoding="utf-8"))
    )
    spec = load_supervision_spec_file(SPEC_PATH)
    review = await review_plan_only_result(plan_result, spec)
    review_path = PLAN_RUN_DIR / "plan_review_result_round4.json"
    review_path.write_text(
        json.dumps(review.model_dump(mode="json"), ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    print(f"[225-r4] round-4 review saved: {review_path}")
    if review.findings:
        print(f"  REVIEW FAIL: {len(review.findings)} findings")
        for f in review.findings:
            print(f"    - Ch{f.chapter_number} [{f.code}] {f.message}")
            print(f"      evidence: {f.evidence}")
        print("\n[225-r4] STOP: round-4 review rejected. Report to user.")
        return 2

    print("  REVIEW PASS: 0 findings")
    approval = approve_plan_review(review)
    approval_path = PLAN_RUN_DIR / "approved_plan_ch2_3.json"
    save_approved_plan(approval_path, approval)
    print(f"[225-r4] approved-plan refreshed: {approval_path}")
    print("\nNext: Ch2-only smoke -- songyan run --project-id "
          f"{PROJECT_ID} --chapters 2-2 --auto-confirm --on-failure isolate")
    return 0


if __name__ == "__main__":
    rc = asyncio.run(main())
    sys.exit(rc)
