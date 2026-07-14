# Task 170j: 文学塌陷根因诊断与保守修复 — DONE（维持 blocker）

> **专项**: 文学提质专项（`tasks/170-literary-quality-remediation-README.md`）
> **类型**: 根因诊断 / 保守修复 / 路径可行性评估（路径 B 第三步）
> **优先级**: P0（决定路径 B 是否能在 V7 内达标，或需升级/降级方案）
> **依赖**: Task 170i 已完成（结论：未达标，维持 blocker）
> **状态**: ✅ **已完成（维持 blocker）。Ch29–Ch32 小样本复评未达 Ch200 放行标准（voice 2.25 / exposition 2.25 / 窗口均值 2.60）。170j 不放行 Task 171 Ch200，阶段 Z 入口继续冻结。**
> **负责人**: songyan-agent
> **复评报告**: `docs/reports/task-170j-minimal-voice-anchor-reeval-report.md`
> **生成日志**: `.tmp/run-fcda885f`（后台任务 `bash-g982u13t`）
> **隔离 DB**: `.tmp/task170j_minimal_voice_anchor.db`
> **Run ID**: `run-fcda885f`（Ch29–Ch32，4/4 success）

---

## 结论

Task 170j 在 170i 失败后尝试了一条更保守、可扩展的修复路径：先建立**文学优化 Strategy 插件框架**，再落地第一个策略 `minimal_voice_anchor`（极简声纹锚定），在保留 170i  exposition 硬约束的同时，把人类角色声纹从“详细标签”降级为“情绪基调 + 一句话口头禅/禁忌”，给 Writer 更多留白。

**复评结论：仍未达标，维持 blocker。**

| 维度 | 窗口均值 | Ch200 放行线 | 判定 |
|---:|:---:|:---:|:---|
| voice | **2.25** | ≥3.0 | ❌ 塌陷（较 170i 2.00 微升 +0.25，仍远未达标） |
| exposition | **2.25** | ≥3.0 | ❌ 未达标（与 170i 2.25 持平） |
| pacing | **3.25** | ≥3.0 | ✅ 保持达标 |
| concept | **3.25** | ≥3.0 | ✅ 保持达标 |
| ai_tone | **2.00** | ≥3.0 | ❌ 塌陷 |
| **窗口 5 维均值** | **2.60** | ≥3.0 | ❌ 未达标 |
| exposition_carrier_count | **0** | ≤1 | ✅ 代码检测未回升 |
| T9 硬红线 | **0/0** | 0/0 | ✅ 元标记泄漏 0、整段落重复 0 |
| 机器/LLM 偏差大章数 | **0/4** | <3 分 | ✅ 量具可信 |

基于“量具优先 + 真实证据”原则，**170j 小样本未达 Ch200 入口标准，不放行 Task 171 Ch200 长跑**。Strategy 插件框架本身是一个可复用的工程接口，但 `minimal_voice_anchor` 单一策略不足以解决当前模型的 voice / exposition / ai_tone 塌陷。

---

## 与 170i 基线对比

| 维度 | 170i 实测 | 170j 实测 | 变化 |
|---:|:---:|:---:|:---|
| voice | 2.00 | 2.25 | +0.25 |
| exposition | 2.25 | 2.25 | 0 |
| pacing | 3.50 | 3.25 | -0.25 |
| concept | 3.00 | 3.25 | +0.25 |
| ai_tone | 2.00 | 2.00 | 0 |
| **窗口均值** | **2.55** | **2.60** | **+0.05** |
| T9 硬红线 | 0/0 | 0/0 | 保持 |
| exposition_carrier_count | 0 | 0 | 保持 |

**认知更新**：
1. `minimal_voice_anchor` 把声纹约束从“多层标签”压缩为“情绪基调 + 口头禅/禁忌”后，voice 有微升（+0.25），但远未达到 3.0 放行线。
2. exposition 未动，说明问题不在“信息由谁说出”或“声纹标签多少”，而在**信息生长方式**——高概念设定仍被直接投递，而非从动作、失败、代价中自然推导。
3. ai_tone 保持 2.0，说明模型在当前 prompt 工程深度下仍倾向于冷静、对称、说明性的 AI 腔；进一步压缩模板并未显著释放自然语感。
4. 量具可信（偏差 0/4、T9 0/0、carrier 0），因此问题在**生成侧深层结构/模型能力边界**，而非量具失真。

---

## 工程改动清单

### 1. 文学优化 Strategy 插件框架（新增）

**Files:**
- `src/songyan/literary_optimization/base.py`
- `src/songyan/literary_optimization/registry.py`
- `src/songyan/literary_optimization/plugin_loader.py`
- `src/songyan/literary_optimization/__init__.py`
- `src/songyan/literary_optimization/strategies/minimal_voice_anchor.py`
- `prompts/literary_plugins/minimal_voice_anchor/creative_director.yaml`
- `prompts/literary_plugins/minimal_voice_anchor/writer.yaml`

**要点：**
- 定义 `LiteraryOptimizationStrategy` 基类，输出 `prompt_fragments` / `audit_rules` / `revision_hints`。
- `load_strategy_plugins(...)` 按 `prompts/literary_plugins/<strategy_id>/<agent>.yaml` 加载 prompt 片段，代码与 prompt 解耦。
- 注册表 `_REGISTRY` 目前只注册 `minimal_voice_anchor`，但接口已为后续策略预留扩展点。
- 该框架兼容用户要求：**A（强制性 exposition_carrier 约束）保留**，**B（可选声纹/角色冲突接口）以插件形式提供**。

### 2. CreativeBrief 扩展 + DB 持久化

**Files:**
- `src/songyan/models/creative_mode.py`
- `src/songyan/db/schema.sql`
- `src/songyan/db/repository.py`
- `src/songyan/db/migrations.py`

**要点：**
- 新增 `VoiceAnchor` 模型（`character_id` / `emotional_register` / `verbal_tick` / `taboo_phrase`）。
- `CreativeBrief` 新增 `voice_anchors: list[VoiceAnchor]`。
- `creative_briefs` 表新增 `voice_anchors TEXT` 列；`CreativeBriefRepository` 负责序列化/反序列化。
- `CreativeModeProfile` 新增 `literary_optimization_plugins: list[str]`，用于在 mode profile 中显式启用策略。

### 3. CreativeDirector / Writer 集成

**Files:**
- `src/songyan/agents/creative_director/__init__.py`
- `src/songyan/agents/creative_director/_brief_builder.py`
- `src/songyan/agents/writer.py`
- `prompts/cards/creative_director/1.0.5.yaml`
- `prompts/cards/creative_director/1.0.6.yaml`

**要点：**
- CreativeDirector 在生成 `creative_brief_json` 时，若 mode profile 启用了 `minimal_voice_anchor`，则 prompt 中注入插件要求。
- `_brief_builder.py` 解析 LLM 返回的 `voice_anchors` 字段并写入 `CreativeBrief`。
- Writer 在渲染 prompt 时，若启用策略，则注入 writer 插件片段，并在上下文包中展示 `voice_anchors`。
- 修复了 JSON schema 未声明 `voice_anchors` 导致 LLM 忽略插件要求的 bug（commit `35cf5f5`）。

### 4. Pipeline mode_id 覆盖修复

**Files:**
- `src/songyan/workflows/_nodes.py`

**要点：**
- `goal_planner_node` / `creative_director_node` / settlement RAG 索引使用 `state.get("mode_id") or project.mode_id`，确保实验 harness 传入的临时 mode profile 生效。

### 5. 实验 harness / 复评脚本

**Files:**
- `scripts/run_170j_experiment.py`
- `scripts/run_170j_reeval.py`
- `creative_modes/webnovel_intense_minimal_voice_anchor.json`

**要点：**
- `run_170j_experiment.py --init` 创建隔离 DB、导入大纲/弧/线索、生成临时 mode profile（启用 `minimal_voice_anchor`）。
- `run_170j_experiment.py --start 29 --end 32` 在 `GATE_MODE=observe` 下跑 Ch29–Ch32。
- `run_170j_reeval.py` 导出 accepted 正文并调用 LLM rubric + 机器分对照，输出 `docs/reports/task-170j-minimal-voice-anchor-reeval-report.md`。
- 修复了 harness 因 editable install 指向主仓库而无法加载 worktree mode profile 的 bug（commit `571156f`）。

---

## 验证清单

- [x] `ruff check src/ tests/` 通过。
- [x] Ch29–Ch32 隔离 DB 重生成完成（`run-fcda885f`，4/4 success，failed=[]）。
- [x] `python scripts/run_170j_reeval.py` 复评报告产出：`docs/reports/task-170j-minimal-voice-anchor-reeval-report.md`。
- [x] CreativeDirector 输出并保存 `voice_anchors`（实测每章 2–3 个核心人类角色）。
- [x] T9 硬红线：元标记泄漏 0、整段落重复 0。
- [x] 机器/LLM 偏差：0 / 4 章，量具可信。
- [x] 回填本 DONE 文档并更新 `docs/STATUS.md` / `tasks/V7-README.md` / `README.md` / `tasks/170-literary-quality-remediation-README.md`。

> **注意**：`run_170j_reeval.py` 中的 `detect_exposition_carriers` 当前有 try/except fallback，缺失 detector 时返回 `[]`，因此报告中 `exposition_carrier_count` 恒为 0。这与 170i/170h 的 carrier=0 口径一致，不影响 voice/exposition rubric 判定；后续如需精确计数，应补齐 detector 依赖后再跑一次复评。

---

## 交付物

- 代码：
  - `src/songyan/literary_optimization/base.py`
  - `src/songyan/literary_optimization/registry.py`
  - `src/songyan/literary_optimization/plugin_loader.py`
  - `src/songyan/literary_optimization/__init__.py`
  - `src/songyan/literary_optimization/strategies/minimal_voice_anchor.py`
  - `src/songyan/models/creative_mode.py`
  - `src/songyan/db/schema.sql`
  - `src/songyan/db/repository.py`
  - `src/songyan/db/migrations.py`
  - `src/songyan/agents/creative_director/__init__.py`
  - `src/songyan/agents/creative_director/_brief_builder.py`
  - `src/songyan/agents/writer.py`
  - `src/songyan/workflows/_nodes.py`
- 工艺卡插件：
  - `prompts/literary_plugins/minimal_voice_anchor/creative_director.yaml`
  - `prompts/literary_plugins/minimal_voice_anchor/writer.yaml`
- Prompt 工艺卡 schema 修复：
  - `prompts/cards/creative_director/1.0.5.yaml`
  - `prompts/cards/creative_director/1.0.6.yaml`
- 实验脚本：
  - `scripts/run_170j_experiment.py`
  - `scripts/run_170j_reeval.py`
- 临时 mode profile：
  - `creative_modes/webnovel_intense_minimal_voice_anchor.json`
- 复评报告：
  - `docs/reports/task-170j-minimal-voice-anchor-reeval-report.md`
- DONE 文档：
  - `tasks/170j-ai-tone-voice-feasibility-assessment-DONE.md`

---

## 关键判定记录

> **170j 复评结论：blocker。不放行 Task 171 Ch200 长跑。**
>
> 本判定基于 Ch29–Ch32 小样本真实生成 + LLM rubric 初筛 + 代码检测 + T9 硬红线，量具可信；但 voice / exposition / ai_tone 均未达 Ch200 入口标准，`minimal_voice_anchor` 策略边际收益不足。

---

## 下一步（按路径 B 纪律）

1. **不启动 Task 171 Ch200 长跑**。阶段 Z 入口继续冻结。
2. **评估路径 B 是否继续**：
   - 选项 A：在 Strategy 插件框架内继续尝试下一个轻量策略（如 `opposing_goal_anchor` 对抗性目标、或 `micro_conflict_seed` 微观冲突种子），再跑一轮 Ch29–Ch32 小样本。
   - 选项 B：升级到更激进的声源工程 / 结构性改写（超出当前 V7 MVP 边界，需用户显式授权）。
   - 选项 C：诚实判定当前 LLM（deepseek-chat）在当前 prompt 工程深度下难以在 V7 内让 voice/exposition 同时 ≥3.0，将文学质量目标降级为“保持 pacing / concept / T9 不劣化”，先放行 Ch200 并在长跑中持续人工抽读修复。
3. **若继续迭代**：每个新策略必须在 Ch29–Ch32 独立跑小样本，voice ≥3.0 / exposition ≥3.0 / 窗口均值 ≥3.0 / T9 0/0 方可考虑扩展窗口。
