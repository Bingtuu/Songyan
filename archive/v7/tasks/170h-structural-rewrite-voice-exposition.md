# Task 170h: 结构性改写支持 — 场景模板约束 + 非人实体戏份分配 + 声纹工程升级

> **专项**: 文学提质专项（`archive/v7/tasks/170-literary-quality-remediation-README.md`）
> **类型**: 结构性改写 / 声源工程（路径 B 第一步）
> **优先级**: P0（决定 170g 能否从 blocker 改判并重新评估 Ch200 入口）
> **依赖**: Task 170g Phase2 已完成（结论：未达标，保持 blocker）
> **状态**: 🟡 **规划中，待 review 后执行**
> **负责人**: songyan-agent

---

## 任务边界

Task 170h 是 170g Phase2 失败后升级的 **路径 B 第一步**：不再追加细碎的句式/载体约束，而是从"信息生长方式"和"戏份分配"两个根因入手，用工程化手段强制中段世界观揭示必须经由**人类角色的动作、失败、代价**推导出来，同时让非人实体（建造者/残影/前代钥匙/舰队之手/守门人）退出"世界观嘴替"角色。

本任务仍在 V7 MVP 边界内：不新增 LangGraph 节点、不新增 Agent、不做全自动 LLM 改写闭环；通过升级现有工艺卡、扩展 RuleAuditor 检测、调整 RevisionHandler 触发条件实现。

---

## 核心假设

170g Phase2 已证明：
1. **显性 exposition 载体可以被压到 0**：模型不再用信息流/意识触须硬灌，但换壳为"非人实体大段独白 + 主角总结容器"。
2. **voice 塌陷的根因是戏份分配**：非人实体占据高概念信息输出的核心戏份，人类角色被边缘化。
3. **exposition 说明性的根因是信息生长方式**：设定仍被直接投递，而非从失败/代价/冲突中推导。

因此，本任务不再检测"怎么说"，而是约束"**谁在说、为什么说、在什么代价之后说**"。

---

## 目标

1. **建立"场景-信息"正路径模板库**：CreativeDirector 必须为每个高概念信息指定一个具体场景模板（日志残片 / 矛盾证词 / 错误反馈 / 设备损坏 / 他人代价 / 锁死的门 / 失效的协议），并生成结构化 `scene_templates` 字段。
2. **重构非人实体戏份分配**：限制非人实体单章台词/独白量，强制世界观揭示必须由人类角色在动作/失败/代价中推导。
3. **声纹机制工程化升级**：把非人实体声纹从单条 style 描述升级为包含情绪节奏、词汇偏好、句法特征的 `DialogueStyleCard`，并要求不同非人实体之间可区分。
4. **升级 GoalPlanner 信息交付约束**：删除所有说明文动词，要求每个 information_event 必须映射到一个失败/代价/冲突事件。
5. **扩展 RuleAuditor 结构性检测**：新增"非人实体独白超标"、"主角总结容器"、"无动作支撑的揭示"检测。
6. **扩展 RevisionHandler 触发条件**：把 LLMAuditor `voice` / `exposition` rubric 低分直接接入 readability 路径，不依赖代码检测触发。

---

## 验收标准

### 工程验收
- `ruff check src/ tests/` 通过。
- 新增/修改的单测通过：RuleAuditor 结构性检测用例、CreativeBrief 解析用例、GoalPlanner prompt 用例、RevisionHandler 文学触发用例。
- 无大纲项目能回退旧行为（CreativeDirector default 版本保护）。

### 小样本复评
- 在 Ch29–Ch32 隔离 DB 重跑并复评，目标：
  - voice ≥ 3.0
  - exposition ≥ 3.0
  - pacing ≥ 3.0
  - 窗口 5 维均值 ≥ 3.0
  - `exposition_carrier_count` ≤ 1（含新增结构性模式）
  - T9 硬红线 0/0
  - 机器/LLM 偏差 < 3 分
- 若达标，扩展到 Ch28–Ch40 enforce 复评；若未达标，保持 blocker，进入路径 B 第二步（170i）。

---

## 关键改动清单

### 1. CreativeDirector 工艺卡 1.0.7 + 结构化 scene_templates

**Files:**
- `prompts/cards/creative_director/1.0.7.yaml`（新增）
- `prompts/cards/creative_director/_manifest.yaml`（新增版本条目，default 保持 1.0.5）
- `src/songyan/agents/creative_director/_brief_builder.py`（解析 `scene_templates` 字段）
- `src/songyan/models/creative_mode.py`（`CreativeBrief` 新增 `scene_templates` 字段）
- `tests/test_creative_director.py` 或相关单测

**改动：**
- 在 1.0.6 基础上新增 `scene_templates` 输出字段，要求每个高概念信息必须对应一个具体模板：
  - `log_fragment`：发现日志/记录残片，信息从残缺、矛盾的记录中浮现。
  - `contradictory_testimony`：两个角色对同一事件给出矛盾说法，主角必须判断哪一方在说谎/哪一方信息更可靠。
  - `system_error_feedback`：主角调用系统/设备/协议，系统返回非预期错误，主角从错误中反推规则。
  - `device_damage_trace`：设备/环境损坏留下的痕迹，主角通过痕迹推断发生过什么。
  - `others_cost`：另一角色在主角面前失败、损伤、死亡或被抹除，主角目睹规则运行。
  - `locked_door`：主角试图打开/通过/破解出口，发现被从另一侧锁死或存在隐藏规则。
  - `failed_protocol`：主角依赖某协议/权限/承诺，系统返回错误/异物/非预期结果。
- 每个 `scene_template` 必须包含：`template_id`、`concept_name`、`presentation_action`（人类角色动作）、`failure_or_cost_event`（失败/代价事件）、`environmental_consequence`（环境/系统反馈）、`non_character_source`（若涉及非人实体，必须标注且限制台词量）。
- 新增强制规则："禁止高概念信息通过非人实体直接向主角解释；非人实体只能作为环境线索/碎片化反馈出现，不能担任世界观讲解员。"
- `_brief_builder.py` 解析并验证 `scene_templates` 字段；无效时降级为警告但不阻断（保持 observe 模式轻量约束）。
- `CreativeBrief` Pydantic 模型新增 `scene_templates: list[SceneTemplate]`。

### 2. GoalPlanner 工艺卡 1.1.1 — 删除说明文动词

**Files:**
- `prompts/cards/goal_planner/1.1.1.yaml`（新增）
- `prompts/cards/goal_planner/_manifest.yaml`（更新）
- `src/songyan/agents/goal_planner.py`（可能无需改动，取决于 prompt 是否改变字段）
- `tests/test_prompt_loader.py`（新增断言）

**改动：**
- 新增说明文动词黑名单，强制改写："揭示"、"解释"、"告诉读者"、"说明"、"交代"、"展现设定"、"补充世界观"、"让读者知道"。
- 要求每个 `information_event` 必须显式标注对应的 `target_events` 索引（如 `info_idx: 0 → target_idx: 1`），并验证 target_event 是动作/冲突/失败事件。
- 新增规则：若 information_event 找不到对应的失败/代价/冲突事件，则该 information_event 不得输出；GoalPlanner 必须重写 target_events。

### 3. Writer 工艺卡 1.2.1 — 非人实体戏份分配 + 动作推导结构

**Files:**
- `prompts/cards/writer/1.2.1.yaml`（新增）
- `prompts/cards/writer/_manifest.yaml`（更新，考虑是否作为 default）
- `src/songyan/workflows/_helpers.py`（非角色声纹卡升级，已存在 `_build_non_character_voice_cards`）

**改动：**
- 在 1.2.0 基础上新增：
  - "非人实体戏份配额"：单章中建造者/残影/前代钥匙/舰队之手/守门人等非人实体的台词总量不得超过 100 字（约 3–4 句），且不得连续独白超过 2 句。
  - "高概念信息推导链"：每个世界观揭示必须遵循"人类角色动作 → 失败/代价/冲突 → 环境/系统反馈 → 主角（和读者）推导"四步链。禁止跳过推导直接给出结论。
  - "非人实体声音降级"：非人实体只能作为环境反馈（如系统提示音、残影碎片、门上的刻痕），不能进行完整解释。
- `_helpers.py` 的 `_build_non_character_voice_cards` 升级：为每个非人实体生成更详细的 `DialogueStyleCard`，包含 `vocabulary_signature`（高频词）、`sentence_rhythm`（句法节奏）、`emotional_register`（情绪范围）、`interruption_pattern`（打断方式），并限制 `max_words_per_chapter`。

### 4. RuleAuditor 结构性检测升级

**Files:**
- `src/songyan/agents/rule_auditor.py`
- `src/songyan/models/review.py`
- `tests/test_rule_auditor.py`

**改动：**
- 新增 `StructuralExpositionMatch` 或扩展 `ExpositionCarrierMatch`：
  - `non_character_monologue_overflow`：非人实体单章台词/独白超过阈值（如 >100 字或连续 >2 句）。
  - `protagonist_summary_container`：主角用"他明白了/意识到/知道了/这一切意味着"直接总结世界观（已存在 `protagonist_summary_tell`，升级计数规则）。
  - `unearned_revelation`：高概念信息出现前没有动作/失败/代价/环境反馈支撑（通过正则 + 位置检测）。
  - `expository_dialogue_chain`：连续 3 句以上对话用于传递设定且无冲突/疑问/动作打断。
- 作为 report-only 指标进入 `RuleAuditResult`，不直接阻断 accept。

### 5. RevisionHandler 触发条件扩展

**Files:**
- `src/songyan/agents/revision_handler/__init__.py`
- `prompts/cards/revision_handler/1.1.1.yaml`（新增）
- `prompts/cards/revision_handler/_manifest.yaml`（更新）
- `tests/test_revision_handler_literary.py`

**改动：**
- `_readability_driven` 触发条件新增：LLMAuditor `voice < 3.0` 或 `exposition < 3.0` 时直接触发文学 patch（不依赖 `exposition_carrier_count`）。
- `_build_literary_issues` 新增：从 `scene_templates` 缺失/不匹配生成 issue；从非人实体独白超标生成 issue。
- 1.1.1 prompt 增加"动作推导链"改写示例：把"角色 A 解释设定"改为"角色 A 操作设备失败，系统返回错误，主角从错误中推导"。

---

## 执行顺序

1. **量具先行**：先升级 RuleAuditor 结构性检测，确保能检测到"非人实体独白超标"和"无动作支撑的揭示"。
2. **规划层升级**：CreativeDirector 1.0.7 + GoalPlanner 1.1.1，改变章节目标的信息生长方式。
3. **生成层升级**：Writer 1.2.1 + 非角色声纹卡工程化升级，限制非人实体戏份。
4. **修订层升级**：RevisionHandler 1.1.1，把 LLMAuditor 低分直接接入 patch。
5. **测试**：新增/更新单测，确保规则生效。
6. **小样本复评**：Ch29–Ch32 隔离 DB 重跑，生成复评报告。
7. **回填与状态更新**：更新 task DONE 文档、docs/STATUS.md、tasks/V7-README.md。

---

## 风险与回退

| 风险 | 缓解 |
|------|------|
| 非人实体戏份限制过严导致剧情断裂 | 初始阈值较宽松（100 字/章），后续根据复评调整 |
| scene_templates 结构化输出失败率高 | 解析器降级为警告，不阻断 accept；单测覆盖缺失字段回退 |
| 无大纲项目行为改变 | CreativeDirector default_version 保持 1.0.5，仅在有骨架时加载 1.0.7 |
| 小样本复评仍不达标 | 保持 blocker，进入 170i（声源工程 / 情节结构重构） |

---

## 交付物

- 工艺卡：
  - `prompts/cards/creative_director/1.0.7.yaml`
  - `prompts/cards/goal_planner/1.1.1.yaml`
  - `prompts/cards/writer/1.2.1.yaml`
  - `prompts/cards/revision_handler/1.1.1.yaml`
- 代码：
  - `src/songyan/agents/creative_director/_brief_builder.py`
  - `src/songyan/models/creative_mode.py`
  - `src/songyan/agents/rule_auditor.py`
  - `src/songyan/models/review.py`
  - `src/songyan/agents/revision_handler/__init__.py`
  - `src/songyan/workflows/_helpers.py`
- 单测：
  - `tests/test_rule_auditor.py`
  - `tests/test_prompt_loader.py`
  - `tests/test_revision_handler_literary.py`
  - 可能的 `tests/test_creative_brief_scene_templates.py`
- 报告：
  - `docs/reports/task-170h-structural-rewrite-reeval-report.md`

---

## 下一步

1. review 本 task 文档。
2. 确认后执行改动与测试。
3. Ch29–Ch32 小样本复评。
4. 基于复评结果更新 `docs/STATUS.md`、`tasks/V7-README.md` 和本 task 的 DONE 文档。
5. 若达标则扩展 Ch28–Ch40 enforce 复评；若未达标则进入路径 B 第二步（170i）。
