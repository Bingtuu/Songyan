# Task 170l: 路径 B 第五步 — 声纹工程升级接口化（few_shot_voice_anchor + AI 腔禁用表）— DONE（维持 blocker）

> **专项**: 文学提质专项（`archive/v7/tasks/170-literary-quality-remediation-README.md`）
> **类型**: 路径 B 第五步 / 升级方案轻量入口
> **优先级**: P0
> **依赖**: Task 170k 已完成（结论：未达标，维持 blocker）
> **状态**: ✅ **已完成（维持 blocker）。Ch29–Ch32 小样本复评未达 Ch200 放行标准（voice 2.00 / exposition 2.00 / 窗口均值 2.40；exposition_carrier 72 处）。170l 不放行 Task 171 Ch200，阶段 Z 入口继续冻结。**
> **负责人**: songyan-agent
> **复评报告**: `archive/v7/reports/task-170l-few-shot-voice-anchor-reeval-report.md`
> **生成日志**: `logs/chapter_runs/run-fa235fb4.jsonl`
> **隔离 DB**: `.tmp/task170l_few_shot_voice_anchor.db`
> **Run ID**: `run-fa235fb4`（Ch29–Ch32，4/4 success；Ch29 settlement/summary 失败，Ch30–Ch32 accept）

---

## 结论

Task 170l 在 170k `opposing_goal_anchor` 失败后升级到**声纹工程接口化**：叠加 `few_shot_voice_anchor`（少样本声纹示例）与 `ai_tone_blocklist`（AI 腔句式禁用表），保留 170j/170k 的 `minimal_voice_anchor` + `opposing_goal_anchor`。

**复评结论：仍未达标，维持 blocker；且暴露关键量具 bug——RuleAuditor exposition carrier 检测器只匹配 ASCII 直角引号、漏报中文弯引号，导致 170h–170k 的 `exposition_carrier_count=0` 是失真的。**

| 维度 | 窗口均值 | Ch200 放行线 | 判定 |
|---:|:---:|:---:|:---|
| voice | **2.00** | ≥3.0 | ❌ 塌陷（较 170k 2.00 持平） |
| exposition | **2.00** | ≥3.0 | ❌ 未达标（较 170k 2.50 下降 -0.50） |
| pacing | **3.00** | ≥3.0 | ✅ 保持达标（较 170k 3.75 下降） |
| concept | **3.00** | ≥3.0 | ✅ 保持达标（较 170k 3.75 下降） |
| ai_tone | **2.00** | ≥3.0 | ❌ 未达标（较 170k 2.75 下降 -0.75） |
| **窗口 5 维均值** | **2.40** | ≥3.0 | ❌ 未达标 |
| exposition_carrier_count | **72**（Ch30=27, Ch31=24, Ch32=21） | ≤1 | ❌ 严重超标 |
| T9 硬红线 | **0/0** | 0/0 | ✅ 元标记泄漏 0、整段落重复 0 |
| 机器/LLM 偏差大章数 | **0/3** | <3 分 | ✅ 量具可信 |

基于“量具优先 + 真实证据”原则，**170l 小样本未同时满足 Ch200 入口标准（voice ≥3.0 / exposition ≥3.0 / 窗口均值 ≥3.0 / T9 0/0 / carrier ≤1），不放行 Task 171 Ch200 长跑**。`few_shot_voice_anchor` + `ai_tone_blocklist` 叠加策略**未能解决 voice 塌陷，反而触发大量 info_delivery_dialogue / direct_revelation_monologue**， exposition 显著劣化。

---

## 与 170k 基线对比

| 维度 | 170k 实测 | 170l 实测 | 变化 |
|---:|:---:|:---:|:---|
| voice | 2.00 | 2.00 | 持平 |
| exposition | 2.50 | 2.00 | -0.50 |
| pacing | 3.75 | 3.00 | -0.75 |
| concept | 3.75 | 3.00 | -0.75 |
| ai_tone | 2.75 | 2.00 | -0.75 |
| **窗口均值** | **3.00** | **2.40** | **-0.60** |
| T9 硬红线 | 0/0 | 0/0 | 保持 |
| exposition_carrier_count | 0 | 72 | 暴增 |

**认知更新**：
1. **量具 bug 被修复后，真实 exposition_carrier 暴露**：170h–170k 的 `exposition_carrier_count=0` 是因为 `rule_auditor.py` 中 `_DIRECT_REVELATION_QUOTE_RE`、`_NON_CHARACTER_QUOTE_RE`、`_INFO_DELIVERY_DIALOGUE_RE`、`_FAQ_DIALOGUE_PATTERN`、`_REVELATION_BEAT_PATTERNS` 只匹配 ASCII `"..."`，而正文全部使用中文弯引号 `"..."`。修复后 170l 窗口真实 carrier 达 72 处，说明**此前“carrier=0”不可信**。
2. `few_shot_voice_anchor` 让模型把“声纹示例”理解为“让角色更详细地解释设定”，导致 `info_delivery_dialogue` 暴增（34 处）——角色用冷静、完整、有条理的句式大段说明协议/坐标/历史。
3. `opposing_goal_anchor` 叠加后本就存在的“理性交锋”倾向，在 `few_shot_voice_anchor` 作用下进一步固化为**说明性对白模板**：每个角色都在“清晰表达立场 + 补充背景信息”。
4. `ai_tone_blocklist` 未能有效抵消模板化；模型避开禁用句式的同时，转向更正式、更完整的说明性表达，反而加剧了 AI 腔。
5. **连续四步路径 B 轻量策略（170h → 170i → 170j → 170k → 170l）均未让 voice/exposition 同时达标**，轻量 prompt 工程收益递减甚至产生劣化，必须升级路径或降级目标。

---

## 工程改动清单

### 1. 新增模型与 DB schema

**Files:**
- `src/songyan/models/creative_mode.py`
- `src/songyan/models/__init__.py`
- `src/songyan/db/schema.sql`
- `src/songyan/db/migrations.py`
- `src/songyan/db/review_repo.py`

**要点：**
- 新增 `VoiceSample` 模型（`character_id` / `character_name` / `sample_lines` / `forbidden_patterns` / `mood_anchor`）。
- `CreativeBrief` 新增 `voice_samples: list[VoiceSample]`。
- `creative_briefs` 表新增 `voice_samples TEXT DEFAULT '[]'` 列。
- `CreativeBriefRepository` 负责序列化/反序列化。
- 迁移同时补全 170j 遗漏的 `run_migrations` 中 `voice_anchors` 迁移调用。

### 2. 新增 Strategy

**Files:**
- `src/songyan/literary_optimization/strategies/few_shot_voice_anchor.py`
- `src/songyan/literary_optimization/strategies/ai_tone_blocklist.py`
- `src/songyan/literary_optimization/registry.py`

**要点：**
- `few_shot_voice_anchor`：`applicable_agents = ["creative_director", "writer"]`。
- `ai_tone_blocklist`：`applicable_agents = ["writer", "revision_handler"]`。
- 均在 `_REGISTRY` 注册。

### 3. 新增 Prompt 插件

**Files:**
- `prompts/literary_plugins/few_shot_voice_anchor/creative_director.yaml`
- `prompts/literary_plugins/few_shot_voice_anchor/writer.yaml`
- `prompts/literary_plugins/ai_tone_blocklist/writer.yaml`
- `prompts/literary_plugins/ai_tone_blocklist/revision_handler.yaml`

**要点：**
- CreativeDirector 插件要求输出 2–3 个核心人类角色的 `voice_samples`。
- Writer 插件要求按 sample_lines 模仿语气，禁止复制原句，避开 forbidden_patterns。
- AI 腔禁用表给出高频禁用句式与替代方向（动作/省略/打断/重复/潜台词）。

### 4. CreativeDirector / Writer / RevisionHandler 集成

**Files:**
- `src/songyan/agents/creative_director/_brief_builder.py`
- `src/songyan/agents/creative_director/__init__.py`（via prompt cards）
- `src/songyan/agents/writer.py`
- `src/songyan/agents/revision_handler/__init__.py`
- `src/songyan/workflows/_nodes.py`
- `prompts/cards/creative_director/1.0.5.yaml`
- `prompts/cards/creative_director/1.0.6.yaml`
- `prompts/cards/writer/1.1.0.yaml`
- `prompts/cards/revision_handler/1.0.0.yaml`
- `prompts/cards/revision_handler/1.1.0.yaml`

**要点：**
- `_brief_builder.py` 解析 `voice_samples` 字段并写入 `CreativeBrief`。
- Writer 渲染 `voice_samples` 文本块供 prompt 使用。
- RevisionHandler 加载 `revision_handler` 插件并注入 `literary_plugins` 变量。
- 工艺卡 YAML 声明 `voice_samples` 与 `literary_plugins` 变量。

### 5. 实验 harness

**Files:**
- `scripts/run_170l_experiment.py`
- `scripts/run_170l_reeval.py`
- `creative_modes/webnovel_intense_few_shot_voice_anchor.json`（临时，实验后已删除）

**要点：**
- 临时 mode profile 启用 `["minimal_voice_anchor", "opposing_goal_anchor", "few_shot_voice_anchor", "ai_tone_blocklist"]`。
- 隔离 DB `.tmp/task170l_few_shot_voice_anchor.db`。
- 复评报告 `archive/v7/reports/task-170l-few-shot-voice-anchor-reeval-report.md`。

### 6. 关键量具修复：RuleAuditor 引号匹配 bug（170l 执行中发现）

**Files:**
- `src/songyan/agents/rule_auditor.py`
- `src/songyan/models/review.py`
- `src/songyan/models/__init__.py`
- `tests/test_rule_auditor.py`

**要点：**
- 发现 `_DIRECT_REVELATION_QUOTE_RE`、`_NON_CHARACTER_QUOTE_RE`、`_INFO_DELIVERY_DIALOGUE_RE`、`_FAQ_DIALOGUE_PATTERN`、`_REVELATION_BEAT_PATTERNS` 仅匹配 ASCII `"..."`，漏报中文弯引号 `"..."`。
- 所有相关正则改为同时匹配 `[\"“”]` 与 `[^\"“”]`。
- Worktree 补齐此前缺失的 `ExpositionCarrierMatch` 模型、`RuleAuditResult` 字段、`__init__.py` 导出。
- 新增 `TestExpositionCarrierCurlyQuotes` 单测，覆盖弯引号下的 carrier 检测。

---

## 验证清单

- [x] `ruff check src/ tests/` 通过。
- [x] 新增 Strategy 和插件有单测覆盖。
- [x] 无大纲项目行为不变（策略只在 mode profile 显式启用时生效）。
- [x] RuleAuditor 引号匹配 bug 已修复并新增弯引号覆盖测试。
- [x] Ch29–Ch32 隔离 DB 重生成完成（`run-fa235fb4`）。
- [x] `python scripts/run_170l_reeval.py` 复评报告产出：`archive/v7/reports/task-170l-few-shot-voice-anchor-reeval-report.md`。
- [x] T9 硬红线：元标记泄漏 0、整段落重复 0。
- [x] 机器/LLM 偏差：0 / 3 章，量具可信。
- [x] 回填本 DONE 文档判定并更新 `docs/STATUS.md` / `tasks/V7-README.md` / `README.md` / `archive/v7/tasks/170-literary-quality-remediation-README.md`。
- [x] 清理临时 mode profile：`creative_modes/webnovel_intense_few_shot_voice_anchor.json` 已删除。

---

## 交付物

- 代码：
  - `src/songyan/models/creative_mode.py`
  - `src/songyan/models/__init__.py`
  - `src/songyan/db/schema.sql`
  - `src/songyan/db/migrations.py`
  - `src/songyan/db/review_repo.py`
  - `src/songyan/literary_optimization/strategies/few_shot_voice_anchor.py`
  - `src/songyan/literary_optimization/strategies/ai_tone_blocklist.py`
  - `src/songyan/literary_optimization/registry.py`
  - `src/songyan/agents/creative_director/_brief_builder.py`
  - `src/songyan/agents/writer.py`
  - `src/songyan/agents/revision_handler/__init__.py`
  - `src/songyan/workflows/_nodes.py`
- 工艺卡插件：
  - `prompts/literary_plugins/few_shot_voice_anchor/creative_director.yaml`
  - `prompts/literary_plugins/few_shot_voice_anchor/writer.yaml`
  - `prompts/literary_plugins/ai_tone_blocklist/writer.yaml`
  - `prompts/literary_plugins/ai_tone_blocklist/revision_handler.yaml`
- 工艺卡 schema 更新：
  - `prompts/cards/creative_director/1.0.5.yaml`
  - `prompts/cards/creative_director/1.0.6.yaml`
  - `prompts/cards/writer/1.1.0.yaml`
  - `prompts/cards/revision_handler/1.0.0.yaml`
  - `prompts/cards/revision_handler/1.1.0.yaml`
- 实验脚本：
  - `scripts/run_170l_experiment.py`
  - `scripts/run_170l_reeval.py`
- 单测：
  - `tests/literary_optimization/test_base.py`
  - `tests/test_creative_director.py`
- 复评报告：
  - `archive/v7/reports/task-170l-few-shot-voice-anchor-reeval-report.md`
- DONE 文档：
  - `archive/v7/tasks/170l-few-shot-voice-anchor-DONE.md`

---

## 关键判定记录

> **170l 复评结论：blocker。不放行 Task 171 Ch200 长跑。**
>
> 本判定基于 Ch29–Ch32 小样本真实生成 + LLM rubric 初筛 + 代码检测 + T9 硬红线。量具可信（偏差 0/3、T9 0/0），但 voice / exposition / 窗口均值均未达 Ch200 入口标准，且 exposition_carrier 真实值暴增至 72 处，说明叠加 `few_shot_voice_anchor` + `ai_tone_blocklist` 不仅没有修复 voice 塌陷，反而触发了新的说明性对白模板化。
>
> 同时修复了 RuleAuditor 引号匹配 bug：此前 170h–170k `exposition_carrier_count=0` 因只匹配 ASCII 引号而漏报中文弯引号，量具失真问题已在本任务中一并解决。

---

## 下一步（按路径 B 纪律）

1. **不启动 Task 171 Ch200 长跑**。阶段 Z 入口继续冻结。
2. **路径 B 轻量策略收益已耗尽**：170h → 170i → 170j → 170k → 170l 连续五步均未让 voice/exposition 同时达标；170l 甚至造成 exposition 劣化与 carrier 暴增。必须停止继续追加同层级细碎约束。
3. **必须做出方向决策**：
   - **选项 A：继续路径 B 升级（需用户授权并评估工程量）**：升级到更激进的结构性改写——例如强制人类角色戏份配额/台词上限、非人实体单句信息上限、对白-动作交替硬节拍、认知冲突前置模板等。这可能超出 V7 MVP 边界。
   - **选项 B：引入 AI 腔后处理 / 反模板化 rewrite 规则**：在 RevisionHandler 中针对 `info_delivery_dialogue` / `direct_revelation_monologue` 做硬性拆分/改写，把说明性对白压缩或转化为动作/代价/冲突。先做量具验证再小样本验证。
   - **选项 C：诚实降级目标**：判定当前 deepseek-chat 在当前 prompt 工程深度下难以在 V7 内让 voice/exposition 同时 ≥3.0，将文学质量目标调整为“保持 pacing/concept/T9 不劣化”，先放行 Ch200 并在长跑中持续人工抽读修复。
4. **若继续迭代**：任何新方案必须先确认量具能可靠检测其目标问题，然后在 Ch29–Ch32 独立跑小样本，voice ≥3.0 / exposition ≥3.0 / 窗口均值 ≥3.0 / T9 0/0 / carrier ≤1 方可考虑扩展窗口。
5. **状态文档更新**：已更新 `docs/STATUS.md`、`tasks/V7-README.md`、`README.md`、`archive/v7/tasks/170-literary-quality-remediation-README.md`。
