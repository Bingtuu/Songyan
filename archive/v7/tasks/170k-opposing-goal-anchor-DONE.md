# Task 170k: 路径 B 第四步 — 角色对抗性目标锚定（opposing_goal_anchor）— DONE（维持 blocker）

> **专项**: 文学提质专项（`tasks/170-literary-quality-remediation-README.md`）
> **类型**: 轻量策略迭代（路径 B 第四步）
> **优先级**: P0
> **依赖**: Task 170j 已完成（结论：未达标，维持 blocker）
> **状态**: ✅ **已完成（维持 blocker）。Ch29–Ch32 小样本复评未达 Ch200 放行标准（voice 2.00 / exposition 2.50 / 窗口均值 3.00）。170k 不放行 Task 171 Ch200，阶段 Z 入口继续冻结。**
> **负责人**: songyan-agent
> **复评报告**: `docs/reports/task-170k-opposing-goal-anchor-reeval-report.md`
> **生成日志**: `logs/chapter_runs/run-f9fc6a07.jsonl`
> **隔离 DB**: `.tmp/task170k_opposing_goal_anchor.db`
> **Run ID**: `run-f9fc6a07`（Ch29–Ch32，4/4 success）

---

## 结论

Task 170k 在 170j `minimal_voice_anchor` 失败后尝试叠加**角色对抗性目标锚定**：让主要人类角色从“目标/恐惧/与主角冲突”中生长对白与行动，而不是作为信息容器或 NPC。

**复评结论：仍未达标，维持 blocker。**

| 维度 | 窗口均值 | Ch200 放行线 | 判定 |
|---:|:---:|:---:|:---|
| voice | **2.00** | ≥3.0 | ❌ 塌陷（较 170j 2.25 下降 -0.25） |
| exposition | **2.50** | ≥3.0 | ❌ 未达标（较 170j 2.25 微升 +0.25） |
| pacing | **3.75** | ≥3.0 | ✅ 保持达标 |
| concept | **3.75** | ≥3.0 | ✅ 保持达标 |
| ai_tone | **2.75** | ≥3.0 | ❌ 未达标（较 170j 2.00 微升 +0.75） |
| **窗口 5 维均值** | **3.00** | ≥3.0 | ⚠️ 均值擦线，但主要维度 voice / exposition 未达标 |
| exposition_carrier_count | **0** | ≤1 | ✅ 代码检测未回升 |
| T9 硬红线 | **0/0** | 0/0 | ✅ 元标记泄漏 0、整段落重复 0 |
| 机器/LLM 偏差大章数 | **0/4** | <3 分 | ✅ 量具可信 |

基于“量具优先 + 真实证据”原则，**170k 小样本未同时满足 Ch200 入口标准（voice ≥3.0 / exposition ≥3.0 / 窗口均值 ≥3.0 / T9 0/0 / carrier ≤1），不放行 Task 171 Ch200 长跑**。`opposing_goal_anchor` 单一策略未能解决 voice 塌陷，exposition 虽有微升但未过线。

---

## 与 170j 基线对比

| 维度 | 170j 实测 | 170k 实测 | 变化 |
|---:|:---:|:---:|:---|
| voice | 2.25 | 2.00 | -0.25 |
| exposition | 2.25 | 2.50 | +0.25 |
| pacing | 3.25 | 3.75 | +0.50 |
| concept | 3.25 | 3.75 | +0.50 |
| ai_tone | 2.00 | 2.75 | +0.75 |
| **窗口均值** | **2.60** | **3.00** | **+0.40** |
| T9 硬红线 | 0/0 | 0/0 | 保持 |
| exposition_carrier_count | 0 | 0 | 保持 |

**认知更新**：
1. `opposing_goal_anchor` 叠加 `minimal_voice_anchor` 后，模型对“冲突”的执行表现为**pacing / concept / ai_tone 同步提升**，说明目标冲突确实给场景带来了推进感和概念落地感。
2. 但 **voice 反而下降 0.25**（2.25 → 2.00），说明当角色被强制赋予冲突目标时，模型把角色写成“冷静对峙/理性交锋”的同质化形象——所有角色都在“有条理地表达立场”，反而削弱了个性化声纹。
3. exposition 仅微升 0.25（2.25 → 2.50），仍未达 3.0；说明对抗性目标让信息“有冲突外壳”，但高概念内容仍以说明性方式被角色说出，未真正融入动作与代价。
4. 窗口均值 3.00 擦线，主要归因于 pacing/concept 提升；这不是文学质量全面提升，而是**结构性冲突带来的节奏改善掩盖了 voice/exposition 的深层塌陷**。
5. 量具可信（偏差 0/4、T9 0/0、carrier 0），问题仍在**生成侧深层结构/模型能力边界**。

---

## 工程改动清单

### 1. 新增 Strategy：`opposing_goal_anchor`

**Files:**
- `src/songyan/literary_optimization/strategies/opposing_goal_anchor.py`

**要点：**
- 继承 `LiteraryOptimizationStrategy`。
- `strategy_id = "opposing_goal_anchor"`。
- `applicable_agents = ["creative_director", "writer"]`。
- 与 `minimal_voice_anchor` 叠加使用。

### 2. 新增 Prompt 插件

**Files:**
- `prompts/literary_plugins/opposing_goal_anchor/creative_director.yaml`
- `prompts/literary_plugins/opposing_goal_anchor/writer.yaml`

**要点：**
- CreativeDirector 插件：要求在 `style_constraints` 中为每个核心人类角色输出 `[对抗性目标: 角色ID]` 三段式（goal / fear / conflict_with_protagonist）。
- Writer 插件：要求出场角色必须服务于其 goal/fear，禁止 NPC 容器化；高概念信息必须通过角色目标冲突/失败/代价释放。

### 3. 更新 Strategy 注册表

**Files:**
- `src/songyan/literary_optimization/registry.py`

**要点：**
- 注册 `OpposingGoalAnchorStrategy`。

### 4. 实验 harness / 复评脚本

**Files:**
- `scripts/run_170k_experiment.py`
- `scripts/run_170k_reeval.py`
- `creative_modes/webnovel_intense_opposing_goal_anchor.json`

**要点：**
- 临时 mode profile 启用 `["minimal_voice_anchor", "opposing_goal_anchor"]`。
- 隔离 DB `.tmp/task170k_opposing_goal_anchor.db`。
- `run_170k_reeval.py` 输出 `docs/reports/task-170k-opposing-goal-anchor-reeval-report.md`。

### 5. 单测

**Files:**
- `tests/literary_optimization/test_base.py`

**要点：**
- 增加 `opposing_goal_anchor` 注册表断言与 Strategy 加载断言。

---

## 验证清单

- [x] `ruff check src/ tests/` 通过。
- [x] `tests/literary_optimization/test_base.py` 通过，registry 包含 `minimal_voice_anchor` / `opposing_goal_anchor`。
- [x] Ch29–Ch32 隔离 DB 重生成完成（`run-f9fc6a07`，4/4 success，failed=[]）。
- [x] `python scripts/run_170k_reeval.py` 复评报告产出：`docs/reports/task-170k-opposing-goal-anchor-reeval-report.md`。
- [x] T9 硬红线：元标记泄漏 0、整段落重复 0。
- [x] 机器/LLM 偏差：0 / 4 章，量具可信。
- [x] 回填本 DONE 文档并更新 `docs/STATUS.md` / `tasks/V7-README.md` / `README.md` / `tasks/170-literary-quality-remediation-README.md`。

---

## 交付物

- 代码：
  - `src/songyan/literary_optimization/strategies/opposing_goal_anchor.py`
  - `src/songyan/literary_optimization/registry.py`
- 工艺卡插件：
  - `prompts/literary_plugins/opposing_goal_anchor/creative_director.yaml`
  - `prompts/literary_plugins/opposing_goal_anchor/writer.yaml`
- 实验脚本：
  - `scripts/run_170k_experiment.py`
  - `scripts/run_170k_reeval.py`
- 临时 mode profile：
  - `creative_modes/webnovel_intense_opposing_goal_anchor.json`
- 复评报告：
  - `docs/reports/task-170k-opposing-goal-anchor-reeval-report.md`
- DONE 文档：
  - `tasks/170k-opposing-goal-anchor-DONE.md`

---

## 关键判定记录

> **170k 复评结论：blocker。不放行 Task 171 Ch200 长跑。**
>
> 本判定基于 Ch29–Ch32 小样本真实生成 + LLM rubric 初筛 + 代码检测 + T9 硬红线，量具可信；窗口均值虽达 3.00，但 voice / exposition 两个核心维度仍未达 Ch200 入口标准，`opposing_goal_anchor` 策略边际收益不足且 voice 下降。

---

## 下一步（按路径 B 纪律）

1. **不启动 Task 171 Ch200 长跑**。阶段 Z 入口继续冻结。
2. **评估路径 B 是否继续**：
   - 选项 A：在 Strategy 插件框架内继续尝试下一个轻量策略（如 `micro_conflict_seed` 微观冲突种子、`dialogue_rewrite_seed` 对白重写种子、`non_human_quota` 非人实体戏份硬配额），再跑一轮 Ch29–Ch32 小样本。
   - 选项 B：升级到更激进的声源工程 / 结构性改写（如逐角色少样本语音示例注入、强制句式/词汇禁用表、AI 腔后处理 rewrite 规则）。这超出当前 V7 MVP 边界，需用户显式授权并评估工程量。
   - 选项 C：诚实判定当前 LLM（deepseek-chat）在当前 prompt 工程深度下难以在 V7 内让 voice/exposition 同时 ≥3.0，将文学质量目标降级为“保持 pacing / concept / T9 不劣化”，先放行 Ch200 并在长跑中持续人工抽读修复。
3. **若继续迭代**：每个新策略必须在 Ch29–Ch32 独立跑小样本，voice ≥3.0 / exposition ≥3.0 / 窗口均值 ≥3.0 / T9 0/0 方可考虑扩展窗口。
4. **路径纪律**：连续三轮（170h → 170i → 170j → 170k）同层级轻量策略均未让 voice/exposition 达标，必须诚实记录“路径 B 轻量策略收益递减”，并在下次 DONE 文档中明确给出路径升级/降级的量化评估。
