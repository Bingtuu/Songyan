"""V12 Task 225 plan override: 人工覆写 Ch2/Ch3 plan 对齐 supervision spec beats.

背景：225 round-1 plan-only（runs/v12_task225_ch2_3_plan_200216）review FAIL：
  - Ch2 forbidden_pattern/cross_location_chase："前往"（首个命中在 previous_summary
    回顾文本——已由此前的 _plan_text 扫描器校准排除；target_events 中另有
    "前往货舱外部观察窗"的真实命中）；
  - Ch3 relative_time：hooks 中"时间戳指向明天凌晨"，真阳性；
  - 结构问题：GoalPlanner 看不到 spec allowed_beats，Ch2/Ch3 自由规划的故事线
    （哈希值篡改 / 0.37吨质量差值）与 spec beats（责任质量链 / 沙盒 V-0003）冲突，
    Writer 会同时收到矛盾的 chapter_goal 与 startup_beat_sheet。

approved-plan 机制原生支持 "hand-overridden ChapterGoal"（_nodes.py 注释）。
本脚本按 spec beats 覆写 Ch2/Ch3 的 chapter_goals / creative_briefs 行
（保持 goal_id / brief_id 不变，real run 的 approved-plan short-circuit
按 project+chapter 查最新行，UPDATE 原地生效），然后对同一 plan_only_result
重跑确定性 review；通过后 approve 并保存 approved_plan_ch2_3.json。

覆写原则：
  - target_events/hooks/obligations 从 spec allowed_beats 直接改写，数值与
    协议文本保持 spec 原文（19.0kg、3.0×5+4.0、13.0→12.0 次/分、21.0kg、
    V-0003、"不要替空位完成交接"、"只在当前会话中承认缺口"等）；
  - brief 的通用护栏（forbidden_patterns、语言指纹、概念预算、设定回收）保留
    原文；storyline 相关字段（creative_intent/required_tensions/allowed_fissures/
    行动承载/设定推导/reader_contract/voice_samples/主动选择护栏引用）重写为
    beats 故事线；
  - 不再出现 "前往"、"明天凌晨"、"历史记录" 等 spec 禁止表述。

Usage:
    python scripts/v12_225_plan_override.py
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

os.environ["DATABASE_URL"] = f"sqlite:///{RUNTIME_DB.as_posix()}"
os.environ["CHECKPOINTER_MODE"] = "sqlite"
os.environ["SONGYAN_STARTUP_SUPERVISION_SPEC"] = str(SPEC_PATH)

from songyan.models import ChapterGoal, PlanOnlyResult  # noqa: E402
from songyan.services.plan_review import (  # noqa: E402
    approve_plan_review,
    review_plan_only_result,
    save_approved_plan,
)
from songyan.services.supervision_spec import load_supervision_spec_file  # noqa: E402

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

GOAL_IDS = {2: "gp-eed7c78c", 3: "gp-70c54a2d"}
BRIEF_IDS = {2: "cb-5e710389", 3: "cb-33cc65c0"}

# ---------------------------------------------------------------------------
# Ch2 覆写内容（对齐 spec beats：责任质量链 → 称重模块 → 分段确认 → 证据缺口
# → 反馈延迟 → 接收 21.0kg 但不命名）
# ---------------------------------------------------------------------------

CH2_TARGET_EVENTS = [
    "沈砚在事故调查处复核封存的责任质量链，发现责任质量归属已转移至一个空白值班席："
    "19.0kg整数缺口与封存链一致，签名栏保持空白，空舱门呼吸频率读数稳定在13.0次/分，"
    "舱内温度24.0°C。",
    "沈砚拆开值班席下方的冗余称重模块，模块无损坏却持续输出同一整数缺口，每次归零后"
    "多出一条短协议'不要替空位完成交接'；他决定让模块保持未归零状态，整排值班席进入"
    "手动确认等待。",
    "沈砚把拆成六段的责任质量（3.0kg×5与4.0kg，合计19.0kg）逐一对应到交接廊的六个"
    "现场动作，第二、四段无法对应任何摄像头画面，他拒绝系统补全，6.0kg缺口固定成一个"
    "可复测的间隔。",
    "沈砚复测空舱门与空白值班席之间的反馈延迟，发现每次测试使门内呼吸频率下降一次"
    "（13.0→12.0次/分），且协议提示继续测试将使未命名对象的责任质量增至21.0kg；"
    "他停止重复测试、保存完整链路，最终决定接收21.0kg责任质量，但不替未命名对象命名。",
]

CH2_HOOKS = [
    "空白值班席的质量归属开始与沈砚的本地记录同步闪烁，整数缺口始终是19.0kg，"
    "签名栏始终空白。",
    "本地审计会话接收21.0kg责任质量后，空舱门呼吸频率稳定在12.0次/分——读数稳定"
    "本身，像是一种等待。",
]

CH2_OBLIGATIONS = [
    "必须延续双链确认制、地面磁锁与压力膜的可复测异常设定，新增异常需基于现有工程反馈，"
    "不得引入外部势力或人格化实体。",
    "必须保持沈砚作为调查员的冷静、精确视角，不展开家庭旧事、人员背景或身份秘密。",
    "必须遵守禁忌，不得出现新增具名角色、人名、工牌、质检员、证人等，所有异常通过系统"
    "反馈、数据日志和物理观察呈现。",
    "必须通过科技揭示与叙事推进交替，避免大段说明文，异常发现需通过行动和观察自然带出。",
    "必须落地'不替未命名对象命名'的决定：沈砚只接收责任质量，不为空白签名栏补写任何姓名。",
]

CH2_EMOTIONAL_ARC = (
    "沈砚从最初的警觉逐步过渡到冷静的压迫感，他意识到异常并非孤立事件，而是系统层面存在"
    "协同性偏差，但始终保持专业克制，不流露恐慌，只有通过细微动作（如手指敲击桌面、呼吸"
    "节奏变化）暗示内心的紧绷。"
)

CH2_CREATIVE_INTENT = (
    "本章通过让沈砚复核封存的责任质量链，发现19.0kg整数缺口已被系统转移至一个空白值班席，"
    "并被要求用自己的现场动作逐段认领，从而让读者从'异常已被封存'的暂安，跌入'责任正在"
    "寻找宿主'的压迫感——沈砚最终选择接收责任质量，却不替未命名对象命名，把悬念压在"
    "'承认缺口但不解释缺口'的临界点上。"
)

CH2_TENSIONS = [
    {
        "tension_id": "tension_001",
        "description": "系统把19.0kg责任质量归属转移至空白值班席，并要求逐段确认；短协议"
        "'不要替空位完成交接'与沈砚的复核职责直接冲突——确认意味着替空位签收，不确认"
        "意味着审计阻塞。",
        "tension_type": "value_conflict",
        "characters_involved": ["沈砚", "系统协议"],
        "resolution": "",
        "intensity": 0.9,
    },
    {
        "tension_id": "tension_002",
        "description": "六段责任质量中有两段（合计6.0kg）无法对应任何摄像头画面，只对应温度"
        "和呼吸频率；系统提示'证据类型不足，是否允许补全'——补全意味着让系统虚构证据，"
        "拒绝意味着保留永久缺口。",
        "tension_type": "information_asymmetry",
        "characters_involved": ["沈砚", "空白值班席"],
        "resolution": "",
        "intensity": 0.85,
    },
    {
        "tension_id": "tension_003",
        "description": "每复测一次反馈延迟，门内呼吸频率就下降一次，且协议提示继续测试将使"
        "未命名对象的责任质量增加2.0kg——测量本身在改变被测对象，沈砚的每一步取证都在"
        "消耗某个无法命名的东西。",
        "tension_type": "temporal_pressure",
        "characters_involved": ["沈砚", "空舱门"],
        "resolution": "",
        "intensity": 0.8,
    },
]

CH2_ALLOWED_FISSURES = [
    "沈砚决定用自己的现场动作替代姓名证据去认领第一段3.0kg——他对系统规则的顺从开始"
    "带有试探意味，像是在测量系统的边界而非遵守它。",
    "接收21.0kg责任质量却不替未命名对象命名——他接受了责任的重量，但拒绝给重量一个身份，"
    "这个不一致没有被任何人看到，裂隙只留在他的本地记录里。",
]

CH2_STYLE_CONSTRAINTS = [
    "【节奏地图】段落1-3：慢/事故调查处复核责任质量链，数据逐行核对 → 段落4-6：中/拆开"
    "称重模块，短协议出现 → 段落7-9：快/六段拆分与现场动作对应，拒绝补全 → 段落10-12："
    "中偏快/反馈延迟复测，呼吸频率下降 → 结尾：悬停/接收21.0kg但不命名，第二份材料完成",
    "【行动承载】责任质量转移至空白值班席 → 通过沈砚逐行比对封存链与当前归属记录、发现"
    "19.0kg整数缺口完全一致、签名栏空白同步闪烁的过程来呈现，而非旁白说明",
    "【行动承载】短协议'不要替空位完成交接' → 通过称重模块每次归零后多出一行协议文本、"
    "沈砚三次归零三次复现的过程来呈现",
    "【行动承载】拒绝系统补全证据缺口 → 通过沈砚在'是否允许系统补全'提示前停留、手动把"
    "6.0kg缺口标记为可复测间隔的操作序列来呈现",
    "【行动承载】测量改变被测对象 → 通过每次复测后呼吸频率读数下降一格、协议即时弹出"
    "责任质量增加预告的因果链来呈现",
    "【角色语言指纹】沈砚：内心独白极简、技术术语自然融入思维、习惯用数据假设代替情绪表达、"
    "在紧张时表现为呼吸节奏变化和手指敲击桌面的细微动作，无口头禅，语言高度精确",
    "每个场景的内心活动必须有至少一层潜台词——表面在分析数据，实际在评估系统意图；表面在"
    "遵循流程，实际在测试系统反应边界",
    "【设定推导】冗余称重模块 ← 地面磁锁与压力膜：磁锁与压力膜构成承重链的双证据，值班席"
    "下方的冗余模块是同一证据链在人工席位上的延伸，它输出同一整数缺口是对既有感知差异设定"
    "的复用，不是新概念",
    "【设定推导】分段确认 ← 双链确认制：双链确认制要求每条数据链闭合，责任质量被拆成六段"
    "并要求逐段动作证据，是闭合机制在空白签名栏场景下的退化形态",
]

# 保留原 brief 的通用约束块（概念预算/设定回收引用 Ch1 设定，与故事线无关）
CH2_STYLE_KEEP_SUFFIXES = ("## 概念预算约束", "## 角色主动选择护栏", "## 概念密度护栏")

CH2_READER_CONTRACT = (
    "读完本章，读者应感受到异常并未被封存，而是换了一种方式逼近：责任质量找到了一个空白"
    "值班席作为宿主，并开始用沈砚自己的动作作为证据——他不替未命名对象命名的决定，是"
    "第一章'拒绝确认'的延续，也让'空白签名栏'成为比任何具名角色都更具压迫感的存在。"
)

CH2_VOICE_SAMPLES = [
    {
        "character_id": "shen_yan",
        "character_name": "沈砚",
        "sample_lines": [
            "缺口是整数。19.0，和封存链一致。",
            "协议多了一行。不要替空位完成交接。",
            "再测一次，它就再少一次呼吸。停止测试。",
        ],
        "forbidden_patterns": ["我感到", "我意识到", "仿佛", "好像"],
        "mood_anchor": "冷静克制下的警觉与压迫感",
    }
]

# ---------------------------------------------------------------------------
# Ch3 覆写内容（对齐 spec beats：隔离沙盒 V-0003 → 并列证据 → 关闭外部同步
# → 不确认对象身份 → 缺失主语归档 → 只读介质带走三份材料）
# ---------------------------------------------------------------------------

CH3_TARGET_EVENTS = [
    "沈砚在事故调查处的隔离终端搭建本地沙盒，导入前两份现场材料；沙盒接受材料，却拒绝把"
    "空舱门和空白值班席视为同一对象，生成一个只允许当前会话读取的临时对象V-0003，状态为"
    "未命名。",
    "沈砚让V-0003只回放当前责任质量链，不调用任何外部记录；回放到第二段时沙盒提示证据"
    "类型不足，他把温度、呼吸频率、手动扣锁声三类当前反馈作为并列证据，拒绝系统补全第四类，"
    "V-0003的状态从未命名变为待确认。",
    "沈砚逐项关闭外部同步，每关闭一个同步项系统就减少一段可见记录，本地屏幕留下短协议"
    "'只在当前会话中承认缺口'；他把便携质量计接入沙盒复测整数缺口，面对'确认对象是否存在'"
    "的要求，他只确认测试结果，不确认对象身份，责任质量没有继续转移。",
    "沈砚让沙盒输出一份不含身份字段的当前规则说明，接受替代归档名'当前会话责任质量异常'"
    "并保留缺失主语；随后他把三份材料写入只读介质，在'关闭会话将删除V-0003'的提示前选择"
    "带走介质、保留会话未关闭，V-0003没有被删除。",
]

CH3_HOOKS = [
    "归档成功的规则说明缺失主语——'当前会话责任质量异常'成为第三份材料的核心标记，一个"
    "没有主体的归档名第一次被系统接受。",
    "沈砚离开后，隔离终端在空白屏幕上显示下一条规则，内容尚未刷新；未关闭的会话里，"
    "V-0003仍在等待被读取。",
]

CH3_OBLIGATIONS = [
    "必须保持主角沈砚作为调查员的理性视角，不引入人格化或具名角色，所有异常均通过工程数据、"
    "影像、记录等客观手段呈现。",
    "必须延续近未来硬科幻新怪谈基调，所有揭示均基于可复测的工程异常，不得解释为超自然或"
    "旧事故。",
    "本章必须完成从沙盒建立到三份材料写入只读介质的完整事件链，'缺失主语'必须成为可识别"
    "的核心标记。",
    "必须落地'不确认对象身份'的决定：沈砚只确认测试结果，V-0003始终保持未命名。",
]

CH3_EMOTIONAL_ARC = (
    "从隔离终端前的冷静搭建，到V-0003状态变迁中的紧绷专注，再到'带走介质但保留会话'的"
    "决断中收束为克制的警觉——他承认了缺口，却拒绝给缺口一个名字。"
)

CH3_CREATIVE_INTENT = (
    "本章让沈砚把前两份现场材料导入隔离沙盒，与一个'只允许当前会话读取'的临时对象V-0003"
    "周旋：系统反复要求他确认对象是否存在，而他只确认测试结果、不确认对象身份——读者将看到"
    "异常被收拢进一个本地会话，'不承认，异常就无处安放'的静默对峙取代外部追踪，成为新的"
    "张力来源。"
)

CH3_TENSIONS = [
    {
        "tension_id": "tension_001",
        "description": "沙盒要求沈砚确认测试对象是否存在：确认存在将转移责任质量，不确认则"
        "测试无法闭环——他的方法论要求他承认可复测的结果，他的判断禁止他承认一个未命名的"
        "对象。",
        "tension_type": "value_conflict",
        "characters_involved": ["沈砚", "沙盒协议"],
        "resolution": "",
        "intensity": 0.9,
    },
    {
        "tension_id": "tension_002",
        "description": "每关闭一个外部同步项，系统就减少一段可见记录——沈砚为保住V-0003的"
        "本地性，必须主动放弃证据的外部冗余：材料越安全，记录越稀薄。",
        "tension_type": "information_asymmetry",
        "characters_involved": ["沈砚"],
        "resolution": "",
        "intensity": 0.8,
    },
    {
        "tension_id": "tension_003",
        "description": "隔离终端提示关闭会话将删除V-0003，而带走只读介质意味着离开——保留"
        "会话未关闭，等于把未命名对象留在一台无人看守的终端里继续存在。",
        "tension_type": "temporal_pressure",
        "characters_involved": ["沈砚", "V-0003"],
        "resolution": "",
        "intensity": 0.75,
    },
]

CH3_ALLOWED_FISSURES = [
    "沈砚接受替代归档名'当前会话责任质量异常'并主动保留缺失主语——他宁可让材料不完整，"
    "也不让对象获得身份，这个选择没有写在任何协议里。",
    "他把三份材料写入只读介质带走，却让会话保持未关闭——V-0003因此继续存在于一台他离开的"
    "终端里，他没有回头确认屏幕。",
]

CH3_FORBIDDEN_PATTERNS = [
    "【可执行约束】禁止角色直白说出内心想法（如'我知道''我感到''我意识到'）——RuleAuditor "
    "会检测，所有情绪必须通过操作动作的节奏变化（如敲击键盘的停顿、调取数据的速度）来外化。",
    "【可执行约束】禁止解释性对话——本章沈砚是唯一在场角色，不得通过自言自语或对系统说话的"
    "方式向读者复述已呈现的数据逻辑，所有推理必须以操作步骤和界面反馈来展现。",
    "【可执行约束】禁止引入与种子设定无逻辑推导关系的新组织、新机构、新概念——本章只允许"
    "使用已给出的四个设定（双链确认制、空白确认栏、本地审计模式、地面磁锁与压力膜）进行"
    "组合推演，不得出现新机构缩写或专有名词。",
    "【可执行约束】禁止将异常归因于超自然、旧事故或具名嫌疑方——所有描述必须停留在'可复测"
    "的工程异常'层面，沈砚的推断只能指向关联性，不能指向动机或来源。",
    "【可执行约束】禁止使用'冷笑''皱眉''瞳孔一缩'等面部表情套语来表达情绪，沈砚的紧张感"
    "必须通过生理细节（指节叩击台面的频率、呼吸间隔）或环境反馈（界面刷新延迟）来传递。",
    "【可执行约束】禁止把沙盒界面操作写成说明书式流水账——每个操作必须伴随一层系统反馈的"
    "异常感（如记录减少、状态变迁），而非纯功能描述。",
    "【可执行约束】禁止在'确认对象是否存在'的对峙段落插入内心独白或犹豫描写——沈砚的拒绝"
    "只能通过选择'只确认测试结果'的操作动作体现，而非语言。",
]

CH3_STYLE_CONSTRAINTS = [
    "【节奏地图】开头：慢/隔离终端搭建沙盒、导入材料，操作序列如装配仪器 → 中段：中/回放"
    "责任质量链、并列证据、逐项关闭外部同步，每一步操作伴随记录减少 → 后段：收紧/质量计"
    "复测与'确认存在'要求的对峙 → 结尾：决断/接受替代归档名、写入只读介质 → 悬停/带走"
    "介质保留会话，空白屏幕上的下一条规则",
    "【行动承载】V-0003的生成 → 通过沙盒拒绝合并空舱门与空白值班席、弹出临时对象编号并"
    "标注'只允许当前会话读取'的界面序列来呈现",
    "【行动承载】证据类型不足 → 通过回放进度条停在第二段、三类当前反馈（温度、呼吸频率、"
    "手动扣锁声）被逐项勾选为并列证据的操作来呈现",
    "【行动承载】关闭外部同步的代价 → 通过每关闭一个同步项、右侧记录列表就灰掉一段的即时"
    "反馈来呈现，让读者直观看到'安全'与'记录'此消彼长",
    "【行动承载】不确认对象身份 → 通过'确认对象是否存在'对话框与'只确认测试结果'选项之间"
    "的选择动作来呈现，而非内心独白",
    "【角色语言指纹】沈砚：几乎零对话，所有'语言'都是操作指令、界面文本和系统回执的转述；"
    "内心活动完全规避第一人称，全部转化为对数据关系的第三人称观察（如'回放停在第二段，"
    "证据类型缺一类'而非'我觉得有问题'）。",
    "【潜台词要求】本章虽无对话场景，但系统界面文本、错误回执、状态标签本身构成'对话'——"
    "沈砚与沙盒之间的每次交互都应包含字面信息与真实状态之间的错位（如系统显示'待确认'但"
    "沈砚的行为序列已经是'不确认'）。",
    "【节奏约束】每个操作步骤的描写必须包含三个层次：操作动作（沈砚输入什么）、系统反馈"
    "（界面显示什么）、数据状态（逻辑上意味着什么），但三者不得同时出现，至少一层留白让"
    "读者自行连接。",
]

CH3_STYLE_KEEP_PREFIXES = ("## 设定回收约束", "## 概念预算约束")
CH3_STYLE_KEEP_QUOTE_PREFIXES = ("## 角色主动选择护栏", "## 概念密度护栏")

CH3_READER_CONTRACT = (
    "读完本章，读者应理解异常已经从'外部系统的问题'变成'沈砚本地会话里的同居者'：V-0003"
    "没有被解释、没有被命名、也没有被删除——缺失主语的归档名是沈砚与系统之间达成的第一份"
    "脆弱停战协议，而空白屏幕上的下一条规则预示着协议随时会被改写。"
)


def _j(value: object) -> str:
    return json.dumps(value, ensure_ascii=False)


def _sync_quoted_goal(text: str, new_event0: str) -> str:
    """把护栏块中引用的 target_events[0] 原文替换为覆写后的版本。"""
    start = text.find("“")
    end = text.find("”", start + 1)
    if start < 0 or end < 0:
        return text
    return text[: start + 1] + new_event0 + text[end:]


def override_chapter(con: sqlite3.Connection, chapter: int) -> None:
    goal_id = GOAL_IDS[chapter]
    brief_id = BRIEF_IDS[chapter]

    if chapter == 2:
        target_events = CH2_TARGET_EVENTS
        hooks = CH2_HOOKS
        obligations = CH2_OBLIGATIONS
        emotional_arc = CH2_EMOTIONAL_ARC
        creative_intent = CH2_CREATIVE_INTENT
        tensions = CH2_TENSIONS
        fissures = CH2_ALLOWED_FISSURES
        reader_contract = CH2_READER_CONTRACT
        word_count_target = 3200
    else:
        target_events = CH3_TARGET_EVENTS
        hooks = CH3_HOOKS
        obligations = CH3_OBLIGATIONS
        emotional_arc = CH3_EMOTIONAL_ARC
        creative_intent = CH3_CREATIVE_INTENT
        tensions = CH3_TENSIONS
        fissures = CH3_ALLOWED_FISSURES
        reader_contract = CH3_READER_CONTRACT
        word_count_target = 3000

    # 覆写 chapter_goals 行（previous_summary / chapter_type / created_at 保持原值）
    con.execute(
        """UPDATE chapter_goals
           SET target_events = ?, emotional_arc = ?, hooks = ?, obligations = ?,
               word_count_target = ?
           WHERE goal_id = ?""",
        (_j(target_events), emotional_arc, _j(hooks), _j(obligations),
         word_count_target, goal_id),
    )

    goal_payload = {
        "chapter_number": chapter,
        "previous_summary": "",
        "target_events": target_events,
        "emotional_arc": emotional_arc,
        "hooks": hooks,
        "obligations": obligations,
        "word_count_target": word_count_target,
        "chapter_type": "exploration",
        "derived_from_arc": None,
    }
    # previous_summary 保留 DB 原值，同步进 brief.chapter_goal 时保持一致
    row = con.execute(
        "SELECT previous_summary FROM chapter_goals WHERE goal_id = ?", (goal_id,)
    ).fetchone()
    goal_payload["previous_summary"] = row[0] if row else ""

    # 覆写 creative_briefs 行：保留通用护栏块，替换 storyline 相关字段
    brow = con.execute(
        "SELECT style_constraints, voice_anchors FROM creative_briefs WHERE brief_id = ?",
        (brief_id,),
    ).fetchone()
    old_style: list[str] = json.loads(brow[0])
    if chapter == 2:
        style = list(CH2_STYLE_CONSTRAINTS)
        kept = [s for s in old_style if s.startswith(CH2_STYLE_KEEP_SUFFIXES)]
        style.extend(_sync_quoted_goal(s, target_events[0]) for s in kept)
        voice_anchors = brow[1]
        voice_samples = _j(CH2_VOICE_SAMPLES)
        forbidden_patterns = None  # 保留原值
    else:
        style = list(CH3_STYLE_CONSTRAINTS)
        kept = [s for s in old_style if s.startswith(CH3_STYLE_KEEP_PREFIXES)]
        style.extend(kept)
        kept_quoted = [s for s in old_style if s.startswith(CH3_STYLE_KEEP_QUOTE_PREFIXES)]
        style.extend(_sync_quoted_goal(s, target_events[0]) for s in kept_quoted)
        voice_anchors = brow[1]
        voice_samples = "[]"
        forbidden_patterns = _j(CH3_FORBIDDEN_PATTERNS)

    active_choice = {
        "choice": f"沈砚主动选择用行动推进“{target_events[0]}”，而不是只被危机推动。",
        "alternatives": [
            "等待协议、倒计时或外部敌人逼迫下一步",
            "继续破解/承受现有压力但不改变局面",
        ],
        "cost": "必须付出资源、暴露位置、牺牲时间或承担误判风险之一。",
        "irreversible_consequence": "选择后路线、关系、资源或敌我态势必须发生不可撤回的变化。",
    }
    concept_budget = {
        "max_new_core_concepts": 1,
        "grounding_scene": f"若引入新核心概念，必须绑定到“{target_events[0]}”中的行动、失败、对话或物理后果。",
        "forbidden_mode": "禁止连续解释协议机制",
    }

    if forbidden_patterns is None:
        con.execute(
            """UPDATE creative_briefs
               SET creative_intent = ?, required_tensions = ?, allowed_fissures = ?,
                   style_constraints = ?, reader_contract = ?, chapter_goal = ?,
                   voice_samples = ?, protagonist_active_choice = ?, new_concept_budget = ?
               WHERE brief_id = ?""",
            (creative_intent, _j(tensions), _j(fissures), _j(style), reader_contract,
             _j(goal_payload), voice_samples, _j(active_choice), _j(concept_budget), brief_id),
        )
    else:
        con.execute(
            """UPDATE creative_briefs
               SET creative_intent = ?, required_tensions = ?, allowed_fissures = ?,
                   style_constraints = ?, reader_contract = ?, chapter_goal = ?,
                   voice_samples = ?, protagonist_active_choice = ?, new_concept_budget = ?,
                   forbidden_patterns = ?
               WHERE brief_id = ?""",
            (creative_intent, _j(tensions), _j(fissures), _j(style), reader_contract,
             _j(goal_payload), voice_samples, _j(active_choice), _j(concept_budget),
             forbidden_patterns, brief_id),
        )
    print(f"[225-override] Ch{chapter}: goal {goal_id} / brief {brief_id} overridden")


async def main() -> int:
    stamp = time.strftime("%H%M%S", time.localtime())
    print(f"[225-override] V12 Task 225 plan override - started at {stamp}")

    plan_result_path = PLAN_RUN_DIR / "plan_only_result.json"
    plan_result = PlanOnlyResult.model_validate(
        json.loads(plan_result_path.read_text(encoding="utf-8"))
    )

    con = sqlite3.connect(RUNTIME_DB)
    try:
        for chapter in (2, 3):
            override_chapter(con, chapter)
        con.commit()
    finally:
        con.close()

    # 覆写内容留档（供审计复查）
    override_dump = {
        "overridden_at": stamp,
        "goals": {},
        "note": "人工覆写对齐 supervision_spec allowed_beats；round-1 findings 见 plan_review_result.json",
    }
    con = sqlite3.connect(RUNTIME_DB)
    try:
        con.row_factory = sqlite3.Row
        for chapter in (2, 3):
            grow = con.execute(
                "SELECT * FROM chapter_goals WHERE goal_id = ?", (GOAL_IDS[chapter],)
            ).fetchone()
            brow = con.execute(
                "SELECT * FROM creative_briefs WHERE brief_id = ?", (BRIEF_IDS[chapter],)
            ).fetchone()
            override_dump["goals"][str(chapter)] = {
                "goal": dict(grow),
                "brief": dict(brow),
            }
    finally:
        con.close()
    dump_path = PLAN_RUN_DIR / "plan_override_round2.json"
    dump_path.write_text(
        json.dumps(override_dump, ensure_ascii=False, indent=2, default=str), encoding="utf-8"
    )
    print(f"[225-override] override dump saved: {dump_path}")

    print("\n[225-override] === re-run deterministic review-plan (round 2) ===")
    spec = load_supervision_spec_file(SPEC_PATH)
    review = await review_plan_only_result(plan_result, spec)
    review_path = PLAN_RUN_DIR / "plan_review_result_round2.json"
    review_path.write_text(
        json.dumps(review.model_dump(mode="json"), ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    print(f"[225-override] round-2 review saved: {review_path}")
    if review.findings:
        print(f"  REVIEW FAIL: {len(review.findings)} findings")
        for f in review.findings:
            print(f"    - Ch{f.chapter_number} [{f.code}] {f.message}")
            print(f"      evidence: {f.evidence}")
        print("\n[225-override] STOP: round-2 review rejected. Report to user.")
        return 2

    print("  REVIEW PASS: 0 findings")
    approval = approve_plan_review(review)
    approval_path = PLAN_RUN_DIR / "approved_plan_ch2_3.json"
    save_approved_plan(approval_path, approval)
    print(f"[225-override] approved-plan saved: {approval_path}")
    print("\nNext: python scripts/v12_225_smoke.py")
    return 0


if __name__ == "__main__":
    rc = asyncio.run(main())
    sys.exit(rc)
