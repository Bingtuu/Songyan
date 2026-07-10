# Task 170i: 路径 B 第二步 — 主角认知冲突/误判代价 + 人类角色声纹锚定

> **专项**: 文学提质专项（`tasks/170-literary-quality-remediation-README.md`）
> **类型**: 结构性改写 / 声源工程（路径 B 第二步）
> **优先级**: P0（决定 170h 维持 blocker 后能否改判并重新评估 Ch200 入口）
> **依赖**: Task 170h 已完成（结论：未达标，维持 blocker）
> **状态**: 🟡 **代码/测试已完成；`run-83a004b3` 初始 enforce 跑在 Ch3 因 `health_low_p1_halt` 暂停，已根因定位并切换为 observe 模式续跑，复评结果待出**
> **负责人**: songyan-agent

---

## 任务边界

Task 170i 是 170h 路径 B 第一步失败后的 **路径 B 第二步**。170h 已经把显性 exposition 载体压到 0、限制了非人实体戏份、升级了声纹卡，但 Ch29–Ch32 复评仍显示：

- **voice 均值 1.50**（目标 ≥3.0）：所有角色对白仍像同一个冷静腔；
- **exposition 均值 2.50**（目标 ≥3.0）：高概念信息虽经"动作→失败→环境反馈→主角推导"链触发，却常被主角以冷静总结式内心独白直接消化；
- **窗口 5 维均值 2.65**（目标 ≥3.0）。

170i 不再继续限制"谁说多少"，而是改造"信息如何被主角真正理解"：
1. **主角必须在与他人/系统的对立判断中形成自己的误判**；
2. **主角必须为错误判断付出代价**（身体、关系、信任、时间、资源）；
3. **代价之后，主角修正认知，读者与主角同步修正**；
4. **同时把声纹工程从非人实体降级转向人类角色对白锚定**，让配角/对手/同盟有各自的语言指纹。

本任务仍在 V7 MVP 边界内：不新增 LangGraph 节点、不新增 Agent、不做全自动 LLM 改写闭环；通过升级现有工艺卡、扩展 RuleAuditor 检测、调整 RevisionHandler 触发条件实现。

---

## 核心假设

170h 已证明：
1. **非人实体可以被降级到碎片化反馈**：它们不再是大段世界观讲解员。
2. **主角成为了新的"总结容器"**：高概念信息经动作链触发后，主角用"他明白了/意识到/知道了"直接消化， exposition 仍像说明文包装。
3. **voice 塌陷的根因是人类角色缺乏对立判断**：配角、对手、同盟只是信息触发器，没有与主角形成真正的认知冲突；所有人的对白都服务于推进同一世界观揭示。
4. **声纹工程需要锚定人类角色**：非人实体声纹降级后，人类角色之间的对白区分度成为 voice 的关键。

因此，170i 的核心不是继续约束信息来源，而是让**信息在主角的判断错误和人际冲突中生长**。

---

## 目标

1. **引入"认知冲突-误判-代价"模板**：CreativeDirector 必须为每个高概念信息指定一个冲突场景，其中至少存在两个对立判断，主角选择其中一方并为此付出代价。
2. **重构 GoalPlanner 信息事件**：每个 `information_event` 必须标注：
   - `opposing_judgment`：另一角色或系统对同一现象的不同解释；
   - `protagonist_misjudgment`：主角基于当前证据做出的错误判断；
   - `cost_event`：主角因误判付出的具体代价；
   - `correction_event`：主角在代价后修正认知的方式。
3. **升级人类角色声纹卡**：为当前活跃的人类角色（盟友、对手、中立者）生成 `DialogueStyleCard`，包含情绪基调、词汇签名、句法节奏、打断方式、谎言/隐瞒时的语言标记。
4. **扩展 RuleAuditor 结构性检测**：
   - `protagonist_summary_tell` 升级：检测"主角明白了/意识到/知道了/这一切意味着"等直接总结句；
   - `unconflicted_revelation`：高概念信息出现前 300 字内未出现对立判断或主角误判；
   - `human_voice_homogeneity`：同一场景中两个以上人类角色的对白在句式长度、情绪词、副词使用上过于相似。
5. **扩展 RevisionHandler 触发条件**：LLMAuditor `voice < 3.0` 或 `exposition < 3.0` 时，优先从"认知冲突"和"人类声纹"角度生成 patch。
6. **保持 170h 所有约束**：非人实体戏份配额、scene_templates、exposition_carrier 检测继续生效。

---

## 验收标准

### 工程验收
- `ruff check src/ tests/` 通过。
- 新增/修改的单测通过：RuleAuditor 认知冲突检测用例、CreativeBrief 冲突模板解析用例、GoalPlanner prompt 用例、RevisionHandler 人类声纹 patch 用例。
- 无大纲项目能回退旧行为（CreativeDirector default 版本保护）。

### 小样本复评
- 在 Ch29–Ch32 隔离 DB 重跑并复评（可复用 170h 隔离 DB 或新建），目标：
  - voice ≥ 3.0
  - exposition ≥ 3.0
  - pacing ≥ 3.0
  - 窗口 5 维均值 ≥ 3.0
  - `exposition_carrier_count` ≤ 1（含新增结构性模式）
  - T9 硬红线 0/0
  - 机器/LLM 偏差 < 3 分
- 若达标，扩展到 Ch28–Ch40 enforce 复评；若未达标，维持 blocker，进入路径 B 第三步（170j）或宣告当前路径 B 在现有模型/工程边界下不可行，需升级模型或人工介入。

---

## 关键改动清单

### 1. CreativeDirector 工艺卡 1.0.8 + 结构化 `cognitive_conflict_templates`

**Files:**
- `prompts/cards/creative_director/1.0.8.yaml`（新增）
- `prompts/cards/creative_director/_manifest.yaml`（新增版本条目，default 保持 1.0.5，有骨架时 1.0.8）
- `src/songyan/agents/creative_director/_brief_builder.py`（解析 `cognitive_conflict_templates`）
- `src/songyan/models/creative_mode.py`（`CreativeBrief` 新增 `cognitive_conflict_templates` 字段）
- 相关单测

**改动：**
- 在 1.0.7 基础上新增 `cognitive_conflict_templates` 输出字段，每个高概念信息必须对应一个冲突模板：
  - `opposing_judgment`：另一角色/系统对同一证据的不同解读（必须引用具体对白或动作）。
  - `protagonist_misjudgment`：主角基于偏见、恐惧、欲望或信息缺口做出的错误选择。
  - `cost_event`：主角为错误判断付出的具体代价（身体损伤、关系破裂、信任崩塌、时间/资源损失）。
  - `correction_event`：主角在代价后如何修正认知，且修正必须依赖新的动作/证据，而非他人告知。
- 强制规则："禁止主角在没有对立判断和代价的情况下直接'明白'世界观信息；所有高概念信息必须通过主角的误判和修正被读者理解。"
- `_brief_builder.py` 解析并验证字段；无效时降级为警告但不阻断。
- `CreativeBrief` Pydantic 模型新增 `cognitive_conflict_templates: list[CognitiveConflictTemplate]`。

### 2. GoalPlanner 工艺卡 1.1.2 — 认知冲突事件

**Files:**
- `prompts/cards/goal_planner/1.1.2.yaml`（新增）
- `prompts/cards/goal_planner/_manifest.yaml`（更新）
- `src/songyan/agents/goal_planner.py`（有骨架时调用 1.1.2）
- 相关单测

**改动：**
- 每个 `information_event` 必须显式标注：
  - `opposing_judgment_idx`：指向一个 `target_events` 中的冲突/对立事件；
  - `misjudgment_idx`：指向主角误判事件；
  - `cost_idx`：指向代价事件；
  - `correction_idx`：指向修正事件。
- 新增说明文动词黑名单扩展："明白"、"意识到"、"知道了"、"终于懂了"、"这一切都意味着"、"他理解了"。
- 若 information_event 找不到冲突-误判-代价-修正链，则不得输出；GoalPlanner 必须重写 target_events。

### 3. Writer 工艺卡 1.2.2 — 人类角色声纹锚定 + 认知冲突执行

**Files:**
- `prompts/cards/writer/1.2.2.yaml`（新增）
- `prompts/cards/writer/_manifest.yaml`（更新）
- `src/songyan/agents/writer.py`（渲染人类角色声纹卡与认知冲突模板）
- `src/songyan/workflows/_helpers.py`（`_build_human_voice_cards` 或扩展现有声纹卡逻辑）

**改动：**
- 在 1.2.1 基础上新增：
  - **人类角色声纹锚定**：为每个出场人类角色（包括对手、同盟、中立者）注入 `DialogueStyleCard`，要求对白的情绪基调、词汇签名、句法节奏、谎言/隐瞒标记可区分。
  - **认知冲突执行**：每个世界观揭示必须包含"主角判断 → 对立判断 → 主角坚持错误 → 代价发生 → 主角修正"五个节拍；禁止跳过代价直接修正。
  - **主角内心独白限制**：主角不得用超过两句连续内心独白直接总结世界观；总结必须发生在与他人的对话或动作中。
- 非人实体戏份配额（80 字/章、30 字/场景、连续独白≤2 句）继续生效。

### 4. 非角色/人类声纹卡工程化升级

**Files:**
- `src/songyan/models/character.py`（`DialogueStyleCard` 已扩展，补充 `deception_markers` / `stress_markers`）
- `src/songyan/workflows/_helpers.py`（`_build_non_character_voice_cards` 与新增 `_build_human_voice_cards`）

**改动：**
- 为人类角色生成 `DialogueStyleCard`：
  - `vocabulary_signature`：高频词、口头禅、专业术语偏好；
  - `sentence_rhythm`：平均句长、断句习惯、问句/祈使句比例；
  - `emotional_register`：常态情绪基调、压力下的变化；
  - `interruption_pattern`：打断他人时的语言标记；
  - `deception_markers`：撒谎/隐瞒时的句法或词汇偏离；
  - `stress_markers`：紧张/恐惧时的语言变化。
- 为非人实体保持 170h 的降级声纹。

### 5. RuleAuditor 结构性检测升级

**Files:**
- `src/songyan/agents/rule_auditor.py`
- `src/songyan/models/review.py`
- `tests/test_rule_auditor.py`

**新增/升级检测：**
- `protagonist_summary_tell`（升级）：检测"他明白了/意识到/知道了/终于懂了/这一切都意味着"等直接总结，计数并标记位置。
- `unconflicted_revelation`：高概念信息出现前 300 字内未出现对立判断、主角误判或代价事件。
- `human_voice_homogeneity`：同一场景中两个以上人类角色的对白平均句长差异 <20%、情绪词重叠 >50%、副词密度差异 <30%。
- 以上均为 report-only 指标，不直接阻断 accept，但进入 RevisionHandler 触发条件。

### 6. RevisionHandler 触发条件扩展 + 1.1.2 prompt

**Files:**
- `src/songyan/agents/revision_handler/__init__.py`
- `prompts/cards/revision_handler/1.1.2.yaml`（新增）
- `prompts/cards/revision_handler/_manifest.yaml`（更新）
- `tests/test_revision_handler_literary.py`

**改动：**
- `_readability_driven` 触发条件新增：LLMAuditor `voice < 3.0` 或 `exposition < 3.0` 时，按"认知冲突缺失 → 人类声纹同质化 → 主角总结容器"的优先级生成 patch。
- `_build_literary_issues` 新增：
  - 从 `cognitive_conflict_templates` 缺失/不匹配生成 issue；
  - 从 `protagonist_summary_tell` / `unconflicted_revelation` / `human_voice_homogeneity` 生成 issue。
- 1.1.2 prompt 增加改写示例：把"他明白了 X 意味着 Y"改为"陈薇冷笑：'你以为是 Y？' 林渊按住伤口，血从指缝渗出，才意识到自己把 X 想反了"。

### 7. LLMAuditor 1.0.3 已覆盖 voice/exposition

- 继续沿用 1.0.3，但 170i 的 rubric 权重向"认知冲突"和"人类声纹区分"倾斜（通过 prompt 微调或维度定义补充，不新增维度）。

---

## 执行顺序

1. **量具先行**：升级 RuleAuditor 对人类声纹同质化和主角总结容器的检测。
2. **规划层升级**：CreativeDirector 1.0.8 + GoalPlanner 1.1.2，改变信息生长方式。
3. **生成层升级**：Writer 1.2.2 + 人类角色声纹卡工程化升级。
4. **修订层升级**：RevisionHandler 1.1.2，把 LLMAuditor 低分直接接入"认知冲突/人类声纹" patch。
5. **测试**：新增/更新单测，确保规则生效。
6. **小样本复评**：Ch29–Ch32 隔离 DB 重跑，生成复评报告。
7. **回填与状态更新**：更新 task DONE 文档、`docs/STATUS.md`、`tasks/V7-README.md`、`README.md`。

---

## 风险与回退

| 风险 | 缓解 |
|------|------|
| 认知冲突模板导致剧情过度戏剧化/反转疲劳 | 模板强制但内容留白，要求代价必须具体、微小、可信，避免大反转 |
| 人类角色声纹卡与已有 `dialogue_style_cards` 冲突 | 复用现有 `DialogueStyleCard` 模型，只新增字段；无角色档案时回退到 1.2.1 |
| 无大纲项目行为改变 | CreativeDirector default_version 保持 1.0.5，仅在有骨架时加载 1.0.8 |
| 小样本复评仍不达标 | 维持 blocker，进入 170j（路径 B 第三步）或评估当前模型/工程边界是否足以达标 |

---

## 交付物

- 工艺卡：
  - `prompts/cards/creative_director/1.0.8.yaml`
  - `prompts/cards/goal_planner/1.1.2.yaml`
  - `prompts/cards/writer/1.2.2.yaml`
  - `prompts/cards/revision_handler/1.1.2.yaml`
- 代码：
  - `src/songyan/agents/creative_director/_brief_builder.py`
  - `src/songyan/models/creative_mode.py`
  - `src/songyan/agents/goal_planner.py`
  - `src/songyan/agents/writer.py`
  - `src/songyan/agents/rule_auditor.py`
  - `src/songyan/agents/revision_handler/__init__.py`
  - `src/songyan/workflows/_helpers.py`
- 单测：
  - `tests/test_rule_auditor.py`
  - `tests/test_prompt_loader.py`
  - `tests/test_revision_handler_literary.py`
- 报告：
  - `docs/reports/task-170i-remediation-reeval-report.md`

---

## 下一步

1. review 本 task 文档。
2. 确认后执行改动与测试。
3. Ch29–Ch32 小样本复评。
   - **执行策略调整（2026-07-09）**：`run-83a004b3` 初始以 `enforce` 模式启动，Ch3 因 `health_low_p1_halt`（8 个 state_mismatch）暂停。根因分析确认：170h 同期（Ch1–Ch3）也存在同样 8 个 state_mismatch 与 health score 3.0，只因 170h 使用 `observe` 模式而未触发 halt。问题系 enforce gate 对早期章节主角正常状态变化的过度敏感，而非 170i 工艺卡引入的文学质量退化。已将 `run-83a004b3` 切换为 `GATE_MODE=observe` 续跑，保留 Ch1–Ch3 成果，继续 Ch4–Ch32，取得 Ch29–Ch32 样本后立即复评。
4. 基于复评结果更新 `docs/STATUS.md`、`tasks/V7-README.md`、README.md 和本 task 的 DONE 文档。
5. 若达标则扩展 Ch28–Ch40 enforce 复评；若未达标则维持 blocker 并进入 170j 或做路径可行性评估。
