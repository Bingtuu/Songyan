# Task 170l: 路径 B 第五步 — 声纹工程升级接口化（few_shot_voice_anchor + AI 腔句式禁用表）

> **专项**: 文学提质专项（`tasks/170-literary-quality-remediation-README.md`）
> **类型**: 路径 B 第五步 / 升级方案轻量入口
> **优先级**: P0
> **依赖**: Task 170k 已完成（结论：未达标，维持 blocker）
> **状态**: 🔄 进行中
> **负责人**: songyan-agent

---

## 任务边界

Task 170l 是 170h–170k **连续四步轻量策略均未让 voice/exposition 同时达标**后的下一步。按路径 B 纪律，**不再追加同层级细碎约束**，而是升级到更聚焦的声纹工程，但**以接口化、可扩展、可叠加的方式落地**，避免一次性引入激进风险。

170k 暴露的核心问题：
- `opposing_goal_anchor` 让 pacing / concept / ai_tone 提升，但 **voice 反而下降**（2.25 → 2.00）。
- 模型把"对抗性目标"写成**冷静、理性、对称的交锋对白**，所有角色都像在"有条理地表达立场"。
- exposition 仅微升（2.25 → 2.50），说明信息仍有说明性外壳。

170l 的假设：
- 角色声纹不能仅靠"情绪基调 + 口头禅 + 目标冲突"生成，需要**具体可模仿的对白示例**作为 few-shot anchor。
- AI 腔不能仅靠软约束消除，需要**明确的句式禁用表 + 替代方向**。
- 两者都应通过 Strategy 插件框架注入，保持**与 A（强制性 exposition_carrier 约束）兼容、与 B（可选声纹/冲突接口）可叠加**。

---

## 核心设计

170l 采用**C 混合精简版**思路：先落地最小可用的一小步，但设计好扩展接口，让文学性和可读性优化成为长工程。

### 1. 新增 Strategy `few_shot_voice_anchor`

- `strategy_id = "few_shot_voice_anchor"`
- `applicable_agents = ["creative_director", "writer"]`
- 功能：
  - CreativeDirector 插件：为每个核心人类角色生成 1–2 句**具体对白示例**（`voice_samples`），体现该角色的语气、节奏、常用句式、情绪缺陷。
  - Writer 插件：在生成对白时，要求主要人类角色的台词必须**与对应 voice_samples 的语气/句式保持一致**；禁止把角色写成冷静 AI 腔。

### 2. 新增 Strategy `ai_tone_blocklist`

- `strategy_id = "ai_tone_blocklist"`
- `applicable_agents = ["writer", "revision_handler"]`
- 功能：
  - Writer 插件：给出明确的 AI 腔高频句式禁用表（如"也就是说"、"换句话说"、"他知道"、"她明白"、"事实上"、"不可否认的是"等），并给出替代方向（用动作、省略、打断、重复、口误替代）。
  - RevisionHandler 插件：当检测到禁用句式时，优先做局部 rewrite，而不是整段重写。

### 3. 扩展接口设计

- `VoiceSample` 模型：
  - `character_id` / `character_name`
  - `sample_lines`: list[str]（1–3 句示例对白）
  - `forbidden_patterns`: list[str]（该角色不应出现的句式）
  - `mood_anchor`: str（情绪基调，与 170j 的 emotional_register 兼容）
- `CreativeBrief` 新增 `voice_samples: list[VoiceSample]`，DB 持久化。
- Strategy 插件框架支持多个 strategies 叠加，170l harness 默认启用 `["minimal_voice_anchor", "opposing_goal_anchor", "few_shot_voice_anchor", "ai_tone_blocklist"]`，验证叠加效果。

### 4. 保留 170j/170k 成果

- `minimal_voice_anchor` 继续启用（情绪基调 + 口头禅/禁忌）。
- `opposing_goal_anchor` 继续启用（目标/恐惧/冲突）。
- 新增两个策略作为**声纹工程升级接口**。

---

## 目标

1. **新增 `few_shot_voice_anchor` Strategy + prompt 插件**：
   - CreativeDirector 输出每个核心角色的 1–2 句 voice_samples。
   - Writer 按 samples 模仿语气生成对白。
2. **新增 `ai_tone_blocklist` Strategy + prompt 插件**：
   - Writer 获得 AI 腔禁用表与替代方向。
   - RevisionHandler 获得禁用句式局部 rewrite 提示。
3. **扩展 `CreativeBrief` / DB schema / repository**：
   - 新增 `voice_samples` 字段与 `VoiceSample` 模型。
   - `creative_briefs` 表新增 `voice_samples TEXT` 列。
4. **复用 170k harness 结构**：
   - 新建 `scripts/run_170l_experiment.py` 和 `scripts/run_170l_reeval.py`。
   - 临时 mode profile 启用四个策略叠加。
   - 跑 Ch29–Ch32 隔离 DB 生成与复评。

---

## 验收标准

### 工程验收
- `ruff check src/ tests/` 通过。
- 新增 Strategy 和插件有单测覆盖。
- 无大纲项目行为不变（策略只在 mode profile 显式启用时生效）。
- 临时 mode profile 不影响 `tests/creative_modes/test_registry.py`。

### 小样本对照实验
- 实验窗口：Ch29–Ch32。
- 达标线：
  - voice ≥ 3.0
  - exposition ≥ 3.0
  - 窗口 5 维均值 ≥ 3.0
  - `exposition_carrier_count` ≤ 1
  - T9 硬红线 0/0
  - 机器/LLM 偏差 < 3 分

### 决策交付
- `tasks/170l-few-shot-voice-anchor-DONE.md` 必须明确给出：
  - 与 170k 基线对比表；
  - 是否改判 observation/pass；
  - 若未达标，下一步建议（继续叠加 / 升级 / 降级）。

---

## 关键改动清单

### 1. 新增模型与 DB schema

**Files:**
- `src/songyan/models/creative_mode.py`：新增 `VoiceSample` 模型，扩展 `CreativeBrief`。
- `src/songyan/db/schema.sql`：`creative_briefs` 表新增 `voice_samples TEXT`。
- `src/songyan/db/repository.py`：`CreativeBriefRepository` 序列化/反序列化 `voice_samples`。
- `src/songyan/db/migrations.py`：补充 migration。

### 2. 新增 Strategy

**Files:**
- `src/songyan/literary_optimization/strategies/few_shot_voice_anchor.py`
- `src/songyan/literary_optimization/strategies/ai_tone_blocklist.py`
- `src/songyan/literary_optimization/registry.py`

### 3. 新增 Prompt 插件

**Files:**
- `prompts/literary_plugins/few_shot_voice_anchor/creative_director.yaml`
- `prompts/literary_plugins/few_shot_voice_anchor/writer.yaml`
- `prompts/literary_plugins/ai_tone_blocklist/writer.yaml`
- `prompts/literary_plugins/ai_tone_blocklist/revision_handler.yaml`

### 4. CreativeDirector / Writer / RevisionHandler 集成

**Files:**
- `src/songyan/agents/creative_director/__init__.py`
- `src/songyan/agents/creative_director/_brief_builder.py`
- `src/songyan/agents/writer.py`
- `src/songyan/agents/revision_handler/__init__.py`

**要点：**
- CreativeDirector JSON schema 声明 `voice_samples`。
- `_brief_builder.py` 解析并写入 `CreativeBrief`。
- Writer 渲染 `voice_samples` 和 AI 腔禁用表。
- RevisionHandler 在 readability_driven 路径中检测禁用句式并局部 rewrite。

### 5. 实验 harness

**Files:**
- `scripts/run_170l_experiment.py`
- `scripts/run_170l_reeval.py`

**要点：**
- `--init` 创建隔离 DB，临时 mode profile 启用四个策略。
- `--start 29 --end 32` 跑生成。
- 自动生成 `docs/reports/task-170l-few-shot-voice-anchor-reeval-report.md`。

### 6. 单测

**Files:**
- `tests/literary_optimization/test_base.py`：增加新策略断言。
- 可选 `tests/literary_optimization/test_voice_samples.py`：验证 `VoiceSample` 模型与 DB 序列化。

---

## 执行顺序

1. 建立本 task 文档（当前步骤）。
2. Review task 文档。
3. 实现 `VoiceSample` 模型 + DB schema + repository。
4. 实现 `few_shot_voice_anchor` / `ai_tone_blocklist` Strategy + 插件。
5. 集成 CreativeDirector / Writer / RevisionHandler。
6. 新增/更新单测并通过。
7. 跑 `ruff check src/ tests/`。
8. `--init` 创建实验项目。
9. 后台/前台跑 Ch29–Ch32 生成。
10. 跑 `run_170l_reeval.py` 出报告。
11. 根据复评结果回填 `tasks/170l-few-shot-voice-anchor-DONE.md`。
12. 更新 `docs/STATUS.md`、`tasks/V7-README.md`、`README.md`、`tasks/170-literary-quality-remediation-README.md`。
13. 跑 pytest 全批次验证。

---

## 风险与回退

| 风险 | 缓解 |
|------|------|
| few-shot samples 被模型机械复制 | 要求 samples 体现"语气/节奏"而非具体台词，Writer 插件强调"风格一致，内容贴合当前场景" |
| AI 腔禁用表导致表达生硬 | 给出替代方向（动作、省略、打断），不是简单删除 |
| prompt 过长 | 只给 2–3 个核心角色的 voice_samples；禁用表固定 10–15 条 |
| 与 170j/170k 框架不兼容 | 沿用 Strategy 插件框架，不修改核心 Agent 代码 |
| 仍未达标 | 在 DONE 文档中诚实记录，建议继续升级或降级，不继续空转 |

---

## 交付物

- `src/songyan/models/creative_mode.py`（扩展 VoiceSample）
- `src/songyan/db/schema.sql`
- `src/songyan/db/repository.py`
- `src/songyan/db/migrations.py`
- `src/songyan/literary_optimization/strategies/few_shot_voice_anchor.py`
- `src/songyan/literary_optimization/strategies/ai_tone_blocklist.py`
- `src/songyan/literary_optimization/registry.py`
- `prompts/literary_plugins/few_shot_voice_anchor/creative_director.yaml`
- `prompts/literary_plugins/few_shot_voice_anchor/writer.yaml`
- `prompts/literary_plugins/ai_tone_blocklist/writer.yaml`
- `prompts/literary_plugins/ai_tone_blocklist/revision_handler.yaml`
- `scripts/run_170l_experiment.py`
- `scripts/run_170l_reeval.py`
- `tests/literary_optimization/test_base.py`（更新）
- `docs/reports/task-170l-few-shot-voice-anchor-reeval-report.md`
- `tasks/170l-few-shot-voice-anchor-DONE.md`
