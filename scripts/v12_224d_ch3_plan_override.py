"""Override Ch3 chapter_goal + creative_brief to align with supervision_spec Ch3 beats.

Ch3 has NO existing goal/brief in DB (unlike Ch2 which had LLM-generated ones
to UPDATE). This script INSERTs new spec-aligned rows for Ch3, then creates an
approved_plan marker so the runner can lock the plan via
SONGYAN_STARTUP_APPROVED_PLAN.

Ch3 numeric anchors (carry-forward from Ch2 closing values, stable this chapter):
  - unassigned_mass_delta: 21.0 kg (stable, no change)
  - breath_rate: 12.0 /min (stable, no change)
  - air_temperature: 24.0 °C (stable)

Ch3 spec beats (6 beats, introducing temporary object label V-0003):
  1. 沙盒搭建 + 导入前两份材料 → V-0003 生成
  2. V-0003 回放责任质量链 → 三类并列证据 → V-0003 待确认
  3. 测试交接规则 + 关闭外部同步 → V-0003 保留本地
  4. 便携质量计复测缺口 → 只确认结果不确认身份 → 责任质量不转移
  5. 沙盒输出不含身份字段的规则说明 → 替代归档名 → 缺失主语成核心标记
  6. 三份材料写入只读介质 → 保留会话未关闭 → V-0003 未删除
"""

from __future__ import annotations

import asyncio
import hashlib
import json
import os
import sys
import time
import uuid
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "src"))

RUNTIME_DB = ROOT / "projects" / "hard-sf-new-weird" / "runtime" / "songyan.db"
SPEC_PATH = ROOT / "projects" / "hard-sf-new-weird" / "planning" / "supervision_spec.json"

os.environ["DATABASE_URL"] = f"sqlite:///{RUNTIME_DB.as_posix()}"
os.environ["CHECKPOINTER_MODE"] = "sqlite"

PROJECT_ID = "hard-sf-new-weird-v12-224b-235415"
CHAPTER_NUMBER = 3
GOAL_ID = f"gp-{uuid.uuid4().hex[:8]}"
BRIEF_ID = f"cb-{uuid.uuid4().hex[:8]}"

# New target_events derived directly from spec Ch3 beats.
# Each event encodes the spec beat's visible_action + feedback + numeric anchors.
NEW_TARGET_EVENTS = [
    "沈砚在事故调查处的隔离终端搭建本地沙盒，导入前两份现场材料（21.0 kg 责任质量链、12.0 次/分 呼吸频率记录）。沙盒接受材料，却拒绝把空舱门和空白值班席视为同一个对象，生成临时对象 V-0003，只允许当前会话读取。他决定只把 V-0003 当作测试标签，不赋予身份解释。V-0003 出现在本地对象列表，状态为未命名，21.0 kg 缺口与 12.0 次/分 呼吸频率保持稳定。",
    "沈砚让 V-0003 只回放当前责任质量链（21.0 kg），不调用任何外部历史记录。回放到第二段时，沙盒提示证据类型不足。终端返回三类当前反馈：温度（24.0 °C）、呼吸频率（12.0 次/分）、手动扣锁声。他决定把三类反馈作为并列证据，不让系统补全第四类。沙盒接受并列证据，V-0003 的状态从未命名变成待确认，数值台账不变。",
    "沈砚测试待确认状态下的交接规则，逐项关闭外部同步。每关闭一个同步项，系统就减少一段可见记录。本地屏幕留下短协议：只在当前会话中承认缺口。他决定保留当前会话，不把 V-0003 推送到外部系统。外部同步全部关闭，V-0003 仍保留在本地，21.0 kg 责任质量与 12.0 次/分 呼吸频率未被外部修改。",
    "沈砚把便携质量计接入沙盒，复测整数缺口（21.0 kg）。质量计显示缺口稳定，但沙盒要求他确认测试对象是否存在。确认按钮旁出现提示：确认存在会转移责任质量。他决定只确认测试结果，不确认对象身份。测试结果被保存（21.0 kg 缺口稳定），责任质量没有继续转移，呼吸频率保持 12.0 次/分。",
    "沈砚让沙盒输出一份不含身份字段的当前规则说明。规则说明缺少主语，无法通过系统归档。沙盒给出替代归档名：当前会话责任质量异常。他决定接受替代归档名，并保留缺失主语。归档成功，缺失主语成为第三份材料的核心标记，21.0 kg 责任质量与 12.0 次/分 呼吸频率作为附件数据保留。",
    "沈砚准备离开隔离终端，把三份材料写入只读介质。隔离终端提示关闭会话将删除 V-0003。只读介质写入完成，但屏幕要求他选择是否继续承认当前缺口（21.0 kg）。他决定带走只读介质，并保留会话未关闭。V-0003 没有被删除，隔离终端在空白屏幕上显示下一条规则，21.0 kg 责任质量与 12.0 次/分 呼吸频率维持稳定落点。",
]

NEW_EMOTIONAL_ARC = (
    "从隔离操作（沙盒搭建、V-0003 生成）→ 证据并列（温度/呼吸/扣锁声三类）→ "
    "同步隔离（关闭外部同步保留本地）→ 身份拒绝（只确认结果不确认身份）→ "
    "归档妥协（接受替代归档名、缺失主语）→ 会话保留（V-0003 未删除）。"
    "全程不引入人格化元素，所有异常通过沙盒反馈与稳定数值台账（21.0 kg / 12.0 次/分）累积呈现。"
)

NEW_HOOKS = [
    "沈砚带走三份材料写入只读介质后，隔离终端会话未关闭，V-0003 仍保留在本地；"
    "屏幕显示下一条规则，21.0 kg 责任质量与 12.0 次/分 呼吸频率维持稳定——"
    "第三份材料完成但缺失主语成为核心标记，缺口仍未归因。"
]

NEW_OBLIGATIONS = [
    "必须严格按 6 个 spec beats 顺序展开，每个 beat 写满 5 层（可见动作、系统/环境反馈、生理/情绪反应、微决策、状态落点）。",
    "必须复述并复用前两章的数值锚点：unassigned_mass_delta 21.0 kg（稳定不变）、breath_rate 12.0 次/分（稳定不变）、air_temperature 24.0 °C。",
    "本章 numeric ledger 必须可验证：unassigned_mass_delta 21.0 → 21.0 kg（无变化），breath_rate 12.0 → 12.0 /min（无变化）——本章是数值稳定章，不引入新数值变更。",
    "必须维持冷静、精确、压迫的基调，不引入任何人格化元素或角色背景；不引入新命名角色（V-0003 是临时对象标签不是角色名）；不使用相对时间（如「三天前」）；不引入坐标。",
    "必须通过沈砚的沙盒操作自然展现世界观（本地审计端口、短协议、责任质量、隔离终端、只读介质、V-0003 临时标签），避免大段说明。",
]

# Creative brief updates — only the fields that reference target_events / beats.
NEW_CREATIVE_INTENT = (
    "本章让读者跟随沈砚在隔离终端的本地沙盒中完成对 V-0003 临时对象的工程化测试："
    "三类并列证据的固化、外部同步的逐项关闭、身份确认的拒绝、替代归档名的接受，"
    "最终保留会话未关闭让 V-0003 存续。"
    "全程不引入新角色、不回溯历史、不使用相对时间，所有异常通过沙盒反馈与稳定数值台账（21.0 kg / 12.0 次/分）累积呈现。"
)


async def main() -> int:
    print(f"[ch3-plan-override] project      : {PROJECT_ID}")
    print(f"[ch3-plan-override] goal_id      : {GOAL_ID}")
    print(f"[ch3-plan-override] brief_id     : {BRIEF_ID}")
    print(f"[ch3-plan-override] chapter      : {CHAPTER_NUMBER}")
    print()

    # Verify spec still has 6 beats for Ch3
    from songyan.services.supervision_spec import load_supervision_spec_file
    spec = load_supervision_spec_file(SPEC_PATH)
    ch3_beats = spec.beat_sheet_for_chapter(CHAPTER_NUMBER)
    print(f"[ch3-plan-override] spec Ch3 beats: {len(ch3_beats)}")
    if len(ch3_beats) != len(NEW_TARGET_EVENTS):
        print(f"ERROR: spec beats ({len(ch3_beats)}) != new target_events ({len(NEW_TARGET_EVENTS)})")
        return 2
    print()

    from songyan.db.connection import get_db

    # ---- INSERT chapter_goals row (Ch3 has no existing row)
    print("[ch3-plan-override] INSERTing chapter_goals row...")
    async with get_db() as conn:
        await conn.execute(
            """INSERT INTO chapter_goals (
                goal_id, project_id, chapter_number, previous_summary,
                target_events, emotional_arc, hooks, obligations,
                word_count_target, chapter_type, derived_from_arc
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
            (
                GOAL_ID,
                PROJECT_ID,
                CHAPTER_NUMBER,
                "",
                json.dumps(NEW_TARGET_EVENTS, ensure_ascii=False),
                NEW_EMOTIONAL_ARC,
                json.dumps(NEW_HOOKS, ensure_ascii=False),
                json.dumps(NEW_OBLIGATIONS, ensure_ascii=False),
                3000,
                "exploration",
                None,
            ),
        )
        await conn.commit()
    print(f"  target_events  : {len(NEW_TARGET_EVENTS)} events")
    print(f"  emotional_arc  : {len(NEW_EMOTIONAL_ARC)} chars")
    print(f"  hooks          : {len(NEW_HOOKS)} hooks")
    print(f"  obligations    : {len(NEW_OBLIGATIONS)} obligations")

    # ---- INSERT creative_briefs row
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
            "沈砚主动选择只确认测试结果不确认 V-0003 的对象身份，"
            "并接受替代归档名「当前会话责任质量异常」保留缺失主语，"
            "而不是确认对象存在（会转移责任质量）或关闭会话（会删除 V-0003）。"
        ),
        "alternatives": [
            "确认 V-0003 对象存在，让 21.0 kg 责任质量转移到外部系统",
            "关闭会话让 V-0003 被删除，三份材料失去本地锚点",
            "拒绝替代归档名，让规则说明无法归档",
        ],
        "cost": "V-0003 保留在本地但缺失主语，21.0 kg 责任质量与 12.0 次/分 呼吸频率的后续波动绑定到沈砚的未关闭会话。",
        "irreversible_consequence": "V-0003 作为未命名临时对象存续在隔离终端，缺失主语成为第三份材料的核心标记，会话不可关闭。",
    }

    new_concept_budget = {
        "max_new_core_concepts": 1,
        "grounding_scene": (
            "本章引入一个临时对象标签 V-0003（非角色名，是沙盒生成的测试标签），"
            "其余全部复用前两章的设定（本地审计端口、纸质封条、隔离终端、只读介质、空舱门、空白确认栏）。"
            "所有行动绑定到 21.0 kg 责任质量链与 12.0 次/分 呼吸频率的稳定数值台账。"
        ),
        "forbidden_mode": "禁止连续解释协议机制；禁止引入新命名角色；禁止使用相对时间；禁止引入坐标；禁止把 V-0003 拟人化。",
    }

    # Reuse Ch2's voice_anchors and voice_samples (same protagonist, same voice)
    voice_anchors = [
        {"character_id": "shen_yan", "emotional_register": "冷静但逐渐紧绷", "verbal_tick": "复测", "taboo_phrase": "我怀疑"}
    ]
    voice_samples = [
        {
            "character_id": "shen_yan",
            "character_name": "沈砚",
            "sample_lines": [
                "沙盒生成 V-0003，状态未命名——只作测试标签，不赋予身份解释。",
                "三类反馈并列：温度 24.0 °C、呼吸 12.0 次/分、扣锁声。不补全第四类。",
                "确认测试结果，不确认对象身份。21.0 kg 缺口稳定，责任质量不转移。",
            ],
            "forbidden_patterns": ["换句话说", "不可否认的是", "他知道", "我怀疑"],
            "mood_anchor": "冷静但逐渐紧绷",
        }
    ]

    # Reuse Ch2's required_tensions structure, adapted for Ch3
    required_tensions = [
        {
            "tension_id": "tension_001",
            "description": "沙盒拒绝把空舱门和空白值班席视为同一对象——数据链在物理层面闭合，却在程序层面被强制拆分，主角必须在沙盒框架内寻找定性依据。",
            "tension_type": "value_conflict",
            "characters_involved": ["沈砚"],
            "resolution": "",
            "intensity": 0.7,
        },
        {
            "tension_id": "tension_002",
            "description": "沙盒要求确认 V-0003 对象存在，但确认会转移 21.0 kg 责任质量——主角面临确认即丢失、不确认即无法归档的双重束缚。",
            "tension_type": "value_conflict",
            "characters_involved": ["沈砚"],
            "resolution": "",
            "intensity": 0.8,
        },
    ]

    forbidden_patterns = [
        "【可执行约束】禁止使用'冷笑''皱眉''眯眼'等疲劳词——已列入GenreRules，RuleAuditor会检测",
        "【可执行约束】禁止角色直白说出内心想法（如'我知道''我感到''我意识到'）——RuleAuditor会检测",
        "【可执行约束】禁止解释性对话——沈砚不会向系统或已知信息的对象重复说明已发生的事情",
        "【可执行约束】禁止引入与种子设定无逻辑推导关系的新组织、新机构、新概念——所有术语必须从seed_setting中自然延伸",
        "【可执行约束】禁止markdown场景标题（### Scene N）——必须使用空行分隔场景",
        "【可执行约束】禁止HTML注释和元数据",
        "【可执行约束】禁止把 V-0003 拟人化——它是沙盒生成的临时对象标签，不是角色",
    ]

    allowed_fissures = [
        "沈砚在关闭外部同步时，可能跳过某一项保留最小同步通道——这看似不彻底，但源自他在沙盒测试中保留回滚路径的工程习惯",
        "沈砚接受替代归档名时没有坚持补全主语——这看似妥协，实则是他判断缺失主语本身比强行命名更有证据价值",
    ]

    style_constraints = [
        "【节奏地图】段落1-2：慢/铺垫（沙盒搭建、V-0003 生成、三类并列证据）→ 段落3-4：中速/异常累积（关闭外部同步、复测缺口、身份确认拒绝）→ 段落5-6：快/冲突升级（替代归档名、只读介质写入、会话保留）→ 结尾：悬停/钩子（V-0003 未删除，屏幕显示下一条规则）",
        "【角色语言指纹】沈砚：技术术语精确且密集，句式简短，习惯用'记录''复测''比对'等动词开头，几乎不用形容词表达情绪；当他面对异常时，会用提问代替判断",
        "【角色语言指纹】系统播报：中性、无感情、严格遵循协议格式，每段播报以数据编号开头，句末不带情感色彩",
        "【施工单契约】6 个 beats 必须按顺序展开，每个 beat 写满 5 层：可见动作 + 系统/环境反馈 + 生理/情绪反应 + 微决策 + 状态落点。每 beat 约 450-550 字，总计 2700-3300 字。",
    ]

    reader_contract = (
        "读完本章，读者应感受到：主角在沙盒框架内步步紧逼却始终无法给 V-0003 定性的窒息感，"
        "同时被'会话未关闭、V-0003 未删除'的钩子拽入下一章的悬念。"
    )

    print("[ch3-plan-override] INSERTing creative_briefs row...")
    async with get_db() as conn:
        await conn.execute(
            """INSERT INTO creative_briefs (
                brief_id, project_id, chapter_number, mode_id, creative_intent,
                required_tensions, forbidden_patterns, allowed_fissures,
                style_constraints, reader_contract, polyphony_notes, chapter_goal,
                punch_points, emotion_arc, voice_anchors, voice_samples,
                protagonist_active_choice, new_concept_budget,
                fatigue_motif_replacements, supporting_character_goal
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
            (
                BRIEF_ID,
                PROJECT_ID,
                CHAPTER_NUMBER,
                "webnovel",
                NEW_CREATIVE_INTENT,
                json.dumps(required_tensions, ensure_ascii=False),
                json.dumps(forbidden_patterns, ensure_ascii=False),
                json.dumps(allowed_fissures, ensure_ascii=False),
                json.dumps(style_constraints, ensure_ascii=False),
                reader_contract,
                json.dumps([], ensure_ascii=False),  # polyphony_notes
                json.dumps(new_chapter_goal_json, ensure_ascii=False),
                json.dumps([], ensure_ascii=False),  # punch_points
                json.dumps([], ensure_ascii=False),  # emotion_arc
                json.dumps(voice_anchors, ensure_ascii=False),
                json.dumps(voice_samples, ensure_ascii=False),
                json.dumps(new_protagonist_active_choice, ensure_ascii=False),
                json.dumps(new_concept_budget, ensure_ascii=False),
                json.dumps([], ensure_ascii=False),  # fatigue_motif_replacements
                json.dumps({}, ensure_ascii=False),  # supporting_character_goal
            ),
        )
        await conn.commit()
    print(f"  creative_intent         : {len(NEW_CREATIVE_INTENT)} chars")
    print(f"  chapter_goal JSON       : {len(json.dumps(new_chapter_goal_json, ensure_ascii=False))} chars")
    print(f"  protagonist_active_choice: {len(json.dumps(new_protagonist_active_choice, ensure_ascii=False))} chars")
    print(f"  new_concept_budget      : {len(json.dumps(new_concept_budget, ensure_ascii=False))} chars")

    # ---- Create approved_plan marker
    stamp = time.strftime("%H%M%S", time.localtime())
    run_dir = ROOT / "projects" / "hard-sf-new-weird" / "runs" / f"v12_task224d_ch3_plan_{stamp}"
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
    print(f"✅ Ch3 plan override complete")
    print(f"  approved_plan dir : {run_dir}")
    print(f"  approved_plan file: {run_dir / f'approved_plan_ch{CHAPTER_NUMBER}.json'}")
    print(f"  artifact_token    : {artifact_token[:16]}...")
    print()
    print("Next step: run v12_224d_ch3_runner.py")
    return 0


if __name__ == "__main__":
    sys.exit(asyncio.run(main()))
