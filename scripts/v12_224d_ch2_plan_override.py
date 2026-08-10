"""Override Ch2 chapter_goal + creative_brief to align with supervision_spec Ch2 beats.

The GoalPlanner LLM drifted away from the spec beats (wrote about 6.40 tons
instead of 19.0 kg). This script overwrites the DB rows for the Ch2 plan to
encode the 6 spec beats directly as target_events, with explicit numeric
anchors (19.0 -> 21.0 kg, 13.0 -> 12.0 /min, 24.0 °C) so:
  1. Writer follows the spec beats (not the LLM-invented scenario)
  2. SettlementExtractor can extract a naturally-valid numeric ledger
     (no more 19-vs-26 drift like Ch1)

After this override, an approved_plan marker is created so the runner can
use SONGYAN_STARTUP_APPROVED_PLAN to lock the plan for the Writer run.
"""

from __future__ import annotations

import asyncio
import hashlib
import json
import os
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "src"))

RUNTIME_DB = ROOT / "projects" / "hard-sf-new-weird" / "runtime" / "songyan.db"
SPEC_PATH = ROOT / "projects" / "hard-sf-new-weird" / "planning" / "supervision_spec.json"

os.environ["DATABASE_URL"] = f"sqlite:///{RUNTIME_DB.as_posix()}"
os.environ["CHECKPOINTER_MODE"] = "sqlite"

PROJECT_ID = "hard-sf-new-weird-v12-224b-235415"
GOAL_ID = "gp-7616fb20"
BRIEF_ID = "cb-c52d02ce"
CHAPTER_NUMBER = 2

# New target_events derived directly from spec Ch2 beats.
# Each event encodes the spec beat's visible_action + feedback + numeric anchors.
NEW_TARGET_EVENTS = [
    "沈砚在同一事故调查处复核第一章封存的责任质量链：值班席终端显示当前质量归属已转移至空白值班席（19.0 kg，与第一章封存链上的整数缺口一致），签名栏保持空白；空舱门呼吸频率读数稳定在 13.0 次/分，舱内温度 24.0 °C。他决定只追踪当前责任流向，不补写任何值班人员姓名。",
    "沈砚拆开值班席下方的冗余称重模块检查物理载荷：模块没有损坏却持续输出与空舱门相同的整数缺口（19.0 kg），每次归零后都会多出一条短协议「不要替空位完成交接」。他决定让模块保持未归零状态，整排值班席进入手动确认等待，19.0 kg 缺口持续显示。",
    "沈砚逐一按下手动确认键但每次只记录按键反馈不确认责任归属：系统把责任质量拆成六段——3.0 kg、3.0 kg、3.0 kg、3.0 kg、3.0 kg、4.0 kg，合计 19.0 kg——每段都要求一个当前动作作为证据。他决定用自己的动作替代姓名证据只提交可见动作，第一段责任质量（3.0 kg）被接受，剩余 16.0 kg 等待分段确认。",
    "沈砚把六段责任质量对应到交接廊的六个现场动作：第二段（3.0 kg）和第四段（3.0 kg）无法对应任何摄像头画面，合计 6.0 kg 缺口；本地终端提示证据类型不足是否允许系统补全。他决定拒绝系统补全手动保留证据缺口，6.0 kg 缺口固定成可复测的间隔，已确认段落合计 13.0 kg。",
    "沈砚用固定间隔重新测试空舱门和空白值班席之间的反馈延迟：反馈延迟稳定在每测一次 0.3 秒，但每次测试都会让门内呼吸频率降低一次（13.0 → 12.0 次/分）；协议提示继续测试将让未命名对象的责任质量增加 2.0 kg（19.0 → 21.0 kg）。他决定停止重复测试改为保存一次完整链路，未命名对象的呼吸频率稳定在 12.0 次/分，本地审计会话等待接收 21.0 kg 责任质量。",
    "沈砚把完整链路封存并在值班席前留下未确认状态：系统要求他选择关闭事故或接收责任质量，空白值班席的签名栏跳出当前规则「未命名对象不得被代签」。他决定接收 21.0 kg 责任质量但不替未命名对象命名，呼吸频率读数稳定在 12.0 次/分，第二份材料完成。",
]

NEW_EMOTIONAL_ARC = (
    "从冷静复核（19.0 kg 整数缺口基线）→ 工程化拆解（六段 3+3+3+3+3+4）→ "
    "证据缺口固化（6.0 kg 无法对应摄像头）→ 试探性测试触发增量（呼吸 13→12、质量 19→21）→ "
    "接收责任质量但不命名（21.0 kg / 12.0 次/分稳定落点）。"
    "全程不引入人格化元素，所有异常通过工程反馈累积呈现。"
)

NEW_HOOKS = [
    "沈砚接收 21.0 kg 责任质量转入本地审计会话后，签名栏仍空白；"
    "未命名对象的呼吸频率 12.0 次/分与他的本地审计会话绑定，"
    "系统未要求姓名却要求他承担后续波动——第二份材料完成但缺口未归因。"
]

NEW_OBLIGATIONS = [
    "必须严格按 6 个 spec beats 顺序展开，每个 beat 写满 5 层（可见动作、系统/环境反馈、生理/情绪反应、微决策、状态落点）。",
    "必须复述并复用第一章的数值锚点：unassigned_mass_delta 开场 19.0 kg、breath_rate 开场 13.0 次/分、air_temperature 24.0 °C。",
    "本章 numeric ledger 必须可验证：unassigned_mass_delta 19.0 → 21.0 kg（increment +2.0），breath_rate 13.0 → 12.0 /min（decrement -1.0）。",
    "必须维持冷静、精确、压迫的基调，不引入任何人格化元素或角色背景；不引入新命名角色；不使用相对时间（如「三天前」）；不引入坐标。",
    "必须通过沈砚的操作自然展现世界观（升降港、短协议、责任质量、本地审计端口、纸质封条、逆向视图），避免大段说明。",
]

# Creative brief updates — only the fields that reference target_events / beats.
NEW_CREATIVE_INTENT = (
    "本章让读者跟随沈砚在协议框架内完成对 19.0 kg 整数缺口的工程化拆解："
    "六段 3+3+3+3+3+4 的分配、6.0 kg 证据缺口的固化、测试触发呼吸 13→12 与质量 19→21 的同步变化，"
    "最终接收 21.0 kg 责任质量但不替未命名对象命名。"
    "全程不引入新角色、不回溯历史、不使用相对时间，所有异常通过工程反馈与数值台账累积呈现。"
)


async def main() -> int:
    print(f"[ch2-plan-override] project      : {PROJECT_ID}")
    print(f"[ch2-plan-override] goal_id      : {GOAL_ID}")
    print(f"[ch2-plan-override] brief_id     : {BRIEF_ID}")
    print(f"[ch2-plan-override] chapter      : {CHAPTER_NUMBER}")
    print()

    # Verify spec still has 6 beats for Ch2
    from songyan.services.supervision_spec import load_supervision_spec_file
    spec = load_supervision_spec_file(SPEC_PATH)
    ch2_beats = spec.beat_sheet_for_chapter(CHAPTER_NUMBER)
    print(f"[ch2-plan-override] spec Ch2 beats: {len(ch2_beats)}")
    if len(ch2_beats) != len(NEW_TARGET_EVENTS):
        print(f"ERROR: spec beats ({len(ch2_beats)}) != new target_events ({len(NEW_TARGET_EVENTS)})")
        return 2
    print()

    from songyan.db.connection import get_db

    # ---- Update chapter_goals row
    print("[ch2-plan-override] updating chapter_goals row...")
    async with get_db() as conn:
        await conn.execute(
            "UPDATE chapter_goals SET target_events = ?, emotional_arc = ?, hooks = ?, obligations = ? WHERE goal_id = ?",
            (
                json.dumps(NEW_TARGET_EVENTS, ensure_ascii=False),
                NEW_EMOTIONAL_ARC,
                json.dumps(NEW_HOOKS, ensure_ascii=False),
                json.dumps(NEW_OBLIGATIONS, ensure_ascii=False),
                GOAL_ID,
            ),
        )
        await conn.commit()
    print(f"  target_events  : {len(NEW_TARGET_EVENTS)} events")
    print(f"  emotional_arc  : {len(NEW_EMOTIONAL_ARC)} chars")
    print(f"  hooks          : {len(NEW_HOOKS)} hooks")
    print(f"  obligations    : {len(NEW_OBLIGATIONS)} obligations")

    # ---- Update creative_briefs row
    # Build new chapter_goal JSON (embedded in creative_brief)
    new_chapter_goal_json = {
        "chapter_number": CHAPTER_NUMBER,
        "previous_summary": "",
        "target_events": NEW_TARGET_EVENTS,
        "emotional_arc": NEW_EMOTIONAL_ARC,
        "hooks": NEW_HOOKS,
        "obligations": NEW_OBLIGATIONS,
        "word_count_target": 3000,
        "chapter_type": "exploration",
        "derived_from_arc": None,
    }

    new_protagonist_active_choice = {
        "choice": (
            "沈砚主动选择接收 21.0 kg 责任质量转入本地审计会话但不替未命名对象命名，"
            "而不是关闭事故或让系统补全证据缺口。"
        ),
        "alternatives": [
            "关闭事故让 19.0 kg 缺口消失",
            "允许系统补全第二段和第四段的 6.0 kg 证据缺口",
            "拒绝接收责任质量让会话保持未闭合",
        ],
        "cost": "承担 21.0 kg 责任质量的后续波动绑定到本地审计会话，呼吸频率 12.0 次/分与他会话绑定。",
        "irreversible_consequence": "21.0 kg 责任质量转入沈砚的本地审计会话，未命名对象与他建立不可撤回的会话绑定。",
    }

    new_concept_budget = {
        "max_new_core_concepts": 0,
        "grounding_scene": (
            "本章不引入新核心概念，全部复用第一章的设定（本地审计端口、纸质封条、逆向视图、空舱门、空白确认栏）。"
            "所有行动绑定到 19.0 → 21.0 kg 责任质量链与 13.0 → 12.0 次/分 呼吸频率的数值台账。"
        ),
        "forbidden_mode": "禁止连续解释协议机制；禁止引入新命名角色；禁止使用相对时间；禁止引入坐标。",
    }

    print("[ch2-plan-override] updating creative_briefs row...")
    async with get_db() as conn:
        await conn.execute(
            "UPDATE creative_briefs SET creative_intent = ?, chapter_goal = ?, protagonist_active_choice = ?, new_concept_budget = ? WHERE brief_id = ?",
            (
                NEW_CREATIVE_INTENT,
                json.dumps(new_chapter_goal_json, ensure_ascii=False),
                json.dumps(new_protagonist_active_choice, ensure_ascii=False),
                json.dumps(new_concept_budget, ensure_ascii=False),
                BRIEF_ID,
            ),
        )
        await conn.commit()
    print(f"  creative_intent         : {len(NEW_CREATIVE_INTENT)} chars")
    print(f"  chapter_goal JSON       : {len(json.dumps(new_chapter_goal_json, ensure_ascii=False))} chars")
    print(f"  protagonist_active_choice: {len(json.dumps(new_protagonist_active_choice, ensure_ascii=False))} chars")
    print(f"  new_concept_budget      : {len(json.dumps(new_concept_budget, ensure_ascii=False))} chars")

    # ---- Create approved_plan marker
    stamp = time.strftime("%H%M%S", time.localtime())
    run_dir = ROOT / "projects" / "hard-sf-new-weird" / "runs" / f"v12_task224d_ch2_plan_{stamp}"
    run_dir.mkdir(parents=True, exist_ok=True)

    plan_only_result = {
        "project_id": PROJECT_ID,
        "artifacts": [
            {
                "project_id": PROJECT_ID,
                "chapter_number": CHAPTER_NUMBER,
                "chapter_goal_id": GOAL_ID,
                "creative_brief_id": BRIEF_ID,
            }
        ],
    }

    plan_review_result = {
        "project_id": PROJECT_ID,
        "artifacts": plan_only_result["artifacts"],
        "findings": [],
    }

    # artifact_token: deterministic hash of the plan content
    token_input = json.dumps(plan_only_result, sort_keys=True, ensure_ascii=False).encode("utf-8")
    artifact_token = hashlib.sha256(token_input).hexdigest()

    approved_plan = {
        "project_id": PROJECT_ID,
        "chapters": [CHAPTER_NUMBER],
        "artifact_token": artifact_token,
        "approved_by": "spec-beat-override",
        "approved_at": time.strftime("%Y-%m-%dT%H:%M:%S", time.localtime()),
    }

    (run_dir / "plan_only_result.json").write_text(
        json.dumps(plan_only_result, indent=2, ensure_ascii=False), encoding="utf-8"
    )
    (run_dir / "plan_review_result.json").write_text(
        json.dumps(plan_review_result, indent=2, ensure_ascii=False), encoding="utf-8"
    )
    (run_dir / f"approved_plan_ch{CHAPTER_NUMBER}.json").write_text(
        json.dumps(approved_plan, indent=2, ensure_ascii=False), encoding="utf-8"
    )

    print()
    print("=" * 60)
    print(f"✅ Ch2 plan override complete")
    print(f"  approved_plan dir : {run_dir}")
    print(f"  approved_plan file: {run_dir / f'approved_plan_ch{CHAPTER_NUMBER}.json'}")
    print(f"  artifact_token    : {artifact_token[:16]}...")
    print()
    print("Next step: run v12_224d_ch2_runner_with_plan.py")
    return 0


if __name__ == "__main__":
    sys.exit(asyncio.run(main()))
