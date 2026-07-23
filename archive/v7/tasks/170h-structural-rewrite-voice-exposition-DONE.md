# Task 170h: 结构性改写支持 — 场景模板约束 + 非人实体戏份分配 + 声纹工程升级 — DONE（复评结果待回填）

> **专项**: 文学提质专项（`archive/v7/tasks/170-literary-quality-remediation-README.md`）
> **类型**: 结构性改写 / 声源工程（路径 B 第一步）
> **优先级**: P0（决定 170g 能否从 blocker 改判并重新评估 Ch200 入口）
> **依赖**: Task 170g Phase2 已完成（结论：未达标，保持 blocker）
> **状态**: ✅ **已完成（维持 blocker）。Ch29–Ch32 小样本复评未达 Ch200 放行标准（voice 1.50 / exposition 2.50 / 窗口均值 2.65）。生成任务 `bash-6ew98bpt` 已完成：Ch17/Ch19 因 `contamination_index` settlement 校验失败跳过，Ch18/Ch20–Ch32 accept。170h 路径 B 第一步未改判 observation，进入 170i。**
> **负责人**: songyan-agent

---

## 执行摘要

Task 170h 是 170g Phase2 失败后升级的 **路径 B 第一步**：不再追加细碎的句式/载体约束，而是从"信息生长方式"和"戏份分配"两个根因入手，用工程化手段强制中段世界观揭示必须经由**人类角色的动作、失败、代价**推导出来，同时让非人实体（建造者/残影/前代钥匙/舰队之手/守门人）退出"世界观嘴替"角色。

本任务仍在 V7 MVP 边界内：不新增 LangGraph 节点、不新增 Agent、不做全自动 LLM 改写闭环；通过升级现有工艺卡、扩展 RuleAuditor 检测、调整 RevisionHandler 触发条件实现。

**工程改动已全部完成并通过验证**：
- `ruff check src/ tests/` 通过。
- 分模块 pytest 全通过（核心、db/models/genres、rag/settlement/cli、evals/integration、顶层 `test_*.py`）。
- Ch29–Ch32 隔离 DB 重生成与复评已在后台启动（`scripts/run_170h_generation.py` → `scripts/run_170h_reeval.py`），结果将决定 170h 改判 observation 或维持 blocker。

---

## 改动清单

### 1. CreativeDirector 工艺卡 1.0.7 + 结构化 `scene_templates`

**Files:**
- `prompts/cards/creative_director/1.0.7.yaml`（新增/升级）
- `prompts/cards/creative_director/_manifest.yaml`（新增 1.0.7 条目，default 保持 1.0.5）
- `src/songyan/agents/creative_director/_brief_builder.py`（解析 `scene_templates`）
- `src/songyan/agents/creative_director/__init__.py`（有骨架时调用 1.0.7）
- `src/songyan/models/creative_mode.py`（`CreativeBrief` / `SceneTemplate` 模型）

**要点：**
- 高概念信息必须通过结构化 `scene_templates` 输出，模板 ID 限定为 `locked_door` / `failed_protocol` / `others_cost`（以及兼容旧版的 `log_fragment` / `contradictory_testimony` / `system_error_feedback` / `device_damage_trace`）。
- 每个模板必须包含 `concept_name`、`presentation_action`（人类角色动作）、`failure_or_cost_event`、`environmental_consequence`。
- 新增 RuleAuditor 结构性红线说明：`non_character_monologue_overflow` / `expository_dialogue_chain` / `unearned_revelation`。
- `_parse_scene_templates` 解析器静默丢弃无效条目，不阻断 accept。

### 2. GoalPlanner 工艺卡 1.1.1 — 删除说明文动词

**Files:**
- `prompts/cards/goal_planner/1.1.1.yaml`（新增）
- `prompts/cards/goal_planner/_manifest.yaml`（更新）
- `src/songyan/agents/goal_planner.py`（有骨架时调用 1.1.1）

**要点：**
- `target_events` 必须是"动作 → 失败/代价/冲突"推导链，禁止以"揭示/解释/告诉读者/说明"等说明文动词开头。
- 每个 `information_event` 必须映射到 `target_events` 中的失败/代价/冲突事件；找不到承载则必须重写 target_events 或删除该 information_event。

### 3. Writer 工艺卡 1.2.1 — 非人实体戏份分配 + 动作推导结构

**Files:**
- `prompts/cards/writer/1.2.1.yaml`（新增）
- `prompts/cards/writer/_manifest.yaml`（更新，default 切为 1.2.1）
- `src/songyan/agents/writer.py`（渲染 `scene_templates` 与新 DialogueStyleCard 字段）

**要点：**
- 非人实体台词配额：单章累计不超过 80 字，单个场景不超过 30 字，连续独白不超过 2 句。
- 非人实体声音降级：碎片化、命令式、故障式、协议式表达；禁止流畅完整解释。
- 高概念信息必须按 CreativeDirector 的 `scene_templates` 执行；禁止释放模板外信息。
- `scene_templates` 一致性：禁止用对白、旁白或内心独白替代"动作/失败/环境后果"链。

### 4. 非角色声纹卡工程化升级

**Files:**
- `src/songyan/models/character.py`（`DialogueStyleCard` 新增 `vocabulary_signature` / `sentence_rhythm` / `emotional_register` / `interruption_pattern` / `max_words_per_chapter`）
- `src/songyan/workflows/_helpers.py`（`_NON_CHARACTER_VOICE_STYLES` 与 `_build_non_character_voice_cards` 升级）

**要点：**
- 为每个非人实体（建造者、残影、前代钥匙、舰队之手、意识碎片、守门人等）定义差异化词汇签名、句法节奏、情绪范围、打断方式、单章台词上限。
- Writer 渲染时把这些字段注入 prompt。

### 5. RuleAuditor 结构性检测升级

**Files:**
- `src/songyan/agents/rule_auditor.py`
- `src/songyan/models/review.py`（`ExpositionCarrierMatch.carrier_type` 扩展）
- `tests/test_rule_auditor.py`

**新增检测：**
- `non_character_monologue_overflow`：非人实体单章台词/独白超过阈值（>100 字或连续 >2 句）。
- `expository_dialogue_chain`：连续 3 句以上对话用于传递设定且无冲突/疑问/动作打断。
- `unearned_revelation`：非人实体揭示前 200 字内未出现失败/损坏/代价/锁死等动作线索。

以上均为 report-only 指标，不直接阻断 accept。

### 6. RevisionHandler 触发条件扩展 + 1.1.1 prompt

**Files:**
- `src/songyan/agents/revision_handler/__init__.py`
- `prompts/cards/revision_handler/1.1.1.yaml`（新增）
- `prompts/cards/revision_handler/_manifest.yaml`（更新）
- `tests/test_revision_handler_literary.py`

**要点：**
- `_readability_driven` 新增触发：LLMAuditor `voice < 3.0` 或 `exposition < 3.0` 直接触发文学 patch。
- `_build_literary_issues` 新增 voice / exposition 低分兜底 issue。
- 1.1.1 prompt 增加 voice / exposition 指标、动作-失败-后果链改写示例。

### 7. LLMAuditor 1.0.3 — 新增 voice / exposition 维度

**Files:**
- `prompts/cards/llm_auditor/1.0.3.yaml`（新增）
- `prompts/cards/llm_auditor/_manifest.yaml`（default 切为 1.0.3）
- `src/songyan/models/review.py`（`ReviewCategory` 新增 `VOICE` / `EXPOSITION`）
- `tests/models/test_batch2_context_review.py`
- `tests/test_prompt_loader.py`

**要点：**
- 审查维度从 12 扩展到 14，新增 `voice`（声纹区分度与质感）和 `exposition`（信息生长方式）。
- `voice` 评分覆盖非人实体是否讲解员化。
- `exposition` 评分覆盖信息是否从动作-失败-后果链推导。

---

## 验证结果

### 工程验证

```text
ruff check src/ tests/          # 通过
python -m pytest tests/test_rule_auditor.py tests/test_prompt_loader.py tests/test_llm_auditor.py -q   # 118 passed
python -m pytest tests/db tests/models tests/genres -q                                                   # 357 passed
python -m pytest tests/rag tests/settlement_extractor tests/creative_modes tests/cli -q                  # 133 passed
python -m pytest tests/evals tests/integration -q -k "not test_ch1_20"                                   # 76 passed, 4 skipped
python -m pytest tests/test_*.py -q                                                                      # 1889 passed, 1 xfailed
```

新增/更新单测：
- `tests/test_rule_auditor.py`：结构性检测用例（已随 RuleAuditor 升级完成）。
- `tests/test_prompt_loader.py`：writer 版本数、llm_auditor 14 维度 / voice / exposition 断言。
- `tests/test_revision_handler_literary.py`：voice / exposition 低分触发与兜底 issue 断言。
- `tests/models/test_batch2_context_review.py`：ReviewCategory 14 维度断言。

### 小样本复评结果

- 隔离 DB：`.tmp/task170h_ch1_ch40.db`
- 项目 ID：`995b5623470f4b8792bfc1854e6030e9`
- 后台生成任务：`bash-6ew98bpt`（`GATE_MODE=observe ON_FAILURE=isolate`，从 Ch18 续跑）
- 完成章节：Ch18、Ch20–Ch32 accepted；Ch17、Ch19 失败（均为 `contamination_index` settlement 校验失败）。
- 复评窗口：Ch29–Ch32（`scripts/run_170h_reeval.py`）
- 复评报告：`archive/v7/reports/task-170h-remediation-reeval-report.md`

**LLM rubric 初评（1–5 分）**

| Ch | ai_tone | voice | concept | exposition | pacing | 均值 | 最差维 |
|---:|:---:|:---:|:---:|:---:|:---:|:---:|:---:|
| 29 | 3 | 2 | 4 | 3 | 4 | 3.20 | voice |
| 30 | 2 | 2 | 3 | 3 | 4 | 2.80 | ai_tone |
| 31 | 2 | 1 | 3 | 2 | 4 | 2.40 | voice |
| 32 | 2 | 1 | 3 | 2 | 3 | 2.20 | voice |

- **voice 均值**: 1.50（目标 ≥3.0）
- **exposition 均值**: 2.50（目标 ≥3.0）
- **pacing 均值**: 3.75（≥3.0，保持）
- **窗口 5 维均值**: 2.65（目标 ≥3.0）
- **T9 硬红线**: 元标记泄漏 0、整段落重复 0
- **exposition 载体硬灌**: 0 处
- **机器/LLM 偏差**: 0 / 4 章（无 ⚠️）

**结论**: 结构性改写（场景模板 + 非人实体戏份配额 + 声纹工程）将 exposition 载体压到 0、T9 保持 0/0、pacing 稳定，但 **voice 与 exposition 核心文学维度仍未达到 Ch200 放行线**。说明当前约束层级仍不足以让模型在动作-失败-后果链中自然生长高概念信息，非人实体虽已降级、但人类角色声纹和人类推导链仍显扁平。170h 判 **blocker 维持**。

**临时观察（Ch1–Ch32）**
- Ch1–Ch12 均成功生成并 accept，exposition_carrier_count 均为 0，LLMAuditor 1.0.3 新增 voice/exposition 维度已生效。
- Ch3 与 Ch6 连续因 `health_low_p1_halt`（P1 state_mismatch 8 / 20 处）触发 AutoHalt；`--resume` 无法稳定爬坡，故改用 observe 模式先取得文学复评正文。
- Ch17 因 settlement 校验失败（`contamination_index closing_value 34.0 != formula 26.0`）无法 accept；Ch19 同样因 `contamination_index closing_value 47.0 != formula 53.0` 失败。两章均跳过，不影响 Ch29–Ch32 复评窗口。
- Ch12 出现 `missing_ending_hook` 并触发 struct integrity rollback，最终回滚到 `rev-12-3` accept；此为 170h 新约束下次要的结构完整性波动。

---

## 风险与回退

| 风险 | 缓解 |
|------|------|
| 非人实体戏份限制过严导致剧情断裂 | 初始阈值较宽松（80 字/章，单场景 30 字），后续根据复评调整 |
| scene_templates 结构化输出失败率高 | 解析器降级为警告，不阻断 accept；单测覆盖缺失字段回退 |
| 无大纲项目行为改变 | CreativeDirector default_version 保持 1.0.5，仅在有骨架时加载 1.0.7；Writer default 切 1.2.1 但 1.2.1 兼容无 scene_templates |
| 小样本复评仍不达标 | 维持 blocker，进入 170i（声源工程 / 情节结构重构） |

---

## 交付物

- 工艺卡：
  - `prompts/cards/creative_director/1.0.7.yaml`
  - `prompts/cards/goal_planner/1.1.1.yaml`
  - `prompts/cards/writer/1.2.1.yaml`
  - `prompts/cards/revision_handler/1.1.1.yaml`
  - `prompts/cards/llm_auditor/1.0.3.yaml`
- 代码：
  - `src/songyan/agents/creative_director/_brief_builder.py`
  - `src/songyan/agents/creative_director/__init__.py`
  - `src/songyan/models/creative_mode.py`
  - `src/songyan/agents/goal_planner.py`
  - `src/songyan/agents/writer.py`
  - `src/songyan/agents/rule_auditor.py`
  - `src/songyan/agents/revision_handler/__init__.py`
  - `src/songyan/models/review.py`
  - `src/songyan/models/character.py`
  - `src/songyan/workflows/_helpers.py`
- 脚本：
  - `scripts/run_170h_generation.py`
  - `scripts/run_170h_reeval.py`
- 单测：
  - `tests/test_rule_auditor.py`
  - `tests/test_prompt_loader.py`
  - `tests/test_revision_handler_literary.py`
  - `tests/models/test_batch2_context_review.py`
- 报告：
  - `archive/v7/reports/task-170h-remediation-reeval-report.md`

---

## 结论与下一步

- **工程侧**：Task 170h 所有规划改动已落地，单元测试与 lint 全通过。
- **复评侧**：Ch29–Ch32 隔离 DB 重生成与复评已完成。结构性改写把 exposition 载体压到 0、T9 保持 0/0、pacing 稳定 ≥3.0，但 **voice 1.50 / exposition 2.50 / 窗口均值 2.65 仍未达 Ch200 放行线**。
- **判定**：**170h 维持 blocker，不改判 observation；Task 171 Ch200 长跑继续冻结**。
- **下一步**：进入 **Task 170i（路径 B 第二步）**。在 170h 已限制"谁在说"和"谁说多少"的基础上，170i 需要进一步约束"信息如何被主角真正理解/误判/付出代价"——把世界观揭示从"主角看到线索并推导"升级为"主角在冲突中与他人形成对立判断、因判断错误付出代价、在代价中修正认知"，同时把声纹工程从非人实体降级转向人类角色对白锚定。170i 文档待建立并 review。
