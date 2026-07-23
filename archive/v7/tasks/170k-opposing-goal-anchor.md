# Task 170k: 路径 B 第四步 — 角色对抗性目标锚定（opposing_goal_anchor）

> **专项**: 文学提质专项（`archive/v7/tasks/170-literary-quality-remediation-README.md`）
> **类型**: 轻量策略迭代（路径 B 第四步）
> **优先级**: P0
> **依赖**: Task 170j 已完成（结论：未达标，维持 blocker）
> **状态**: 🔄 进行中
> **负责人**: songyan-agent

---

## 任务边界

Task 170k 是 170j `minimal_voice_anchor` 失败后的**下一个轻量策略**。170j 已经证明：把声纹从“多层标签”压缩为“情绪基调 + 口头禅/禁忌”只能让 voice 微升 +0.25，远未达 3.0 放行线；exposition 和 ai_tone 没有变化。

170k 不再追加新的声纹标签，而是尝试让**人类角色的对白从“目标冲突”中自然生长**：
- 每个主要人类角色必须有本章想达成的具体目标、害怕发生的具体后果、与主角目标的直接冲突点。
- Writer 必须让人类角色的出场体现这些对抗性目标，而不是让他们当信息容器或 NPC。
- 高概念信息应通过角色目标冲突/失败/代价来释放，而不是通过主角总结或非人实体独白。

本任务仍守 V7 MVP 边界：不新增 LangGraph 节点、不新增 Agent、不做全自动 LLM 改写闭环；复用 170j 建立的 **Strategy 插件框架**，只新增一个 Strategy 和两份 prompt 插件。

---

## 核心假设

170j 已证明：
1. **声纹标签本身不能解决 voice 塌陷**：给角色贴“口头禅/禁忌”只能制造表面差异，无法让角色真正“活”起来。
2. **配角缺乏真正的对抗性目标是 voice 扁平的根因之一**：当配角只是来递信息、解释设定、陪主角解谜时，他们的对白必然同质化。
3. **模型会形式化执行模板**：如果目标冲突只是 prompt 里的一句话建议，模型会把它写成“两人意见不同”的套路桥段，而不是有机冲突。

因此 170k 的设计重点：
- **给 CreativeDirector 一个结构化输出槽**：强制它为每个主要人类角色写出 `character_conflict_goals`。
- **让 Writer 把对抗性目标当作场景燃料**：不是“建议有冲突”，而是“如果某个角色的目标/恐惧没在本章体现，他就应该减少出场或不出场”。
- **保留 170j 的 `minimal_voice_anchor`**：两者以插件列表形式叠加，验证“声纹 + 目标冲突”是否比单一策略有效。

---

## 目标

1. **新增 Strategy `opposing_goal_anchor`**：
   - `strategy_id = "opposing_goal_anchor"`
   - `applicable_agents = ["creative_director", "writer"]`
   - 输出 prompt 片段，不修改核心 Agent 代码。
2. **CreativeDirector 插件**：
   - 要求 LLM 在 `style_constraints` 中以 `[对抗性目标: 角色ID]` 标记输出每个主要人类角色的：
     - `goal`：本章想达成的具体目标（一句话）
     - `fear`：本章害怕发生的具体后果（一句话）
     - `conflict_with_protagonist`：与主角目标的直接冲突点（一句话）
   - 只给 2–3 个核心人类角色。
3. **Writer 插件**：
   - 要求每个出场人类角色的行动/对白必须服务于其 `goal` 或 `fear`。
   - 禁止角色仅作为“解释设定”“提供线索”“附和主角”的容器。
   - 高概念信息必须通过角色目标冲突/失败/代价释放，而非主角总结或非人实体独白。
4. **复用 170j 实验 harness**：
   - 更新 `scripts/run_170k_experiment.py`（从 170j 复制并调整），临时 mode profile 启用 `["minimal_voice_anchor", "opposing_goal_anchor"]`。
   - 跑 Ch29–Ch32 隔离 DB 生成。
   - 用 `scripts/run_170k_reeval.py` 复评。

---

## 验收标准

### 工程验收
- `ruff check src/ tests/` 通过。
- 新增 Strategy 和插件有单测覆盖。
- 无大纲项目行为不变（`minimal_voice_anchor` / `opposing_goal_anchor` 只在 mode profile 显式启用时生效）。

### 小样本对照实验
- 实验窗口：Ch29–Ch32（与 170i/170j 相同大纲/起点）。
- 评估指标：voice / exposition / pacing / concept / ai_tone，窗口 5 维均值，T9 硬红线，`exposition_carrier_count`，机器/LLM 偏差。
- 达标线：
  - voice ≥ 3.0
  - exposition ≥ 3.0
  - pacing ≥ 3.0
  - 窗口 5 维均值 ≥ 3.0
  - `exposition_carrier_count` ≤ 1
  - T9 硬红线 0/0
  - 机器/LLM 偏差 < 3 分

### 决策交付
- `archive/v7/tasks/170k-opposing-goal-anchor-DONE.md` 必须明确给出：
  - 与 170j 基线对比表；
  - 是否改判 observation/pass；
  - 若未达标，下一步建议（继续轻量迭代 / 升级 / 降级）。

---

## 关键改动清单

### 1. 新增 Strategy：`opposing_goal_anchor`

**Files:**
- `src/songyan/literary_optimization/strategies/opposing_goal_anchor.py`
- `src/songyan/literary_optimization/registry.py`

**要点：**
- 继承 `LiteraryOptimizationStrategy`。
- `apply` 返回 creative_director / writer 的 prompt 片段占位。
- 实际文本放在 prompt 插件 YAML，便于迭代。

### 2. 新增 Prompt 插件

**Files:**
- `prompts/literary_plugins/opposing_goal_anchor/creative_director.yaml`
- `prompts/literary_plugins/opposing_goal_anchor/writer.yaml`

**要点：**
- CreativeDirector 插件：要求在 `style_constraints` 中输出 `[对抗性目标: 角色ID]` 三段式目标/恐惧/冲突。
- Writer 插件：要求出场角色必须有目标驱动的行动/对白；禁止 NPC 容器化。

### 3. 实验 harness

**Files:**
- `scripts/run_170k_experiment.py`（基于 170j 调整）
- `scripts/run_170k_reeval.py`（基于 170j 调整）

**要点：**
- `--init` 创建隔离 DB，临时 mode profile 启用 `["minimal_voice_anchor", "opposing_goal_anchor"]`。
- `--start 29 --end 32` 跑生成。
- 自动生成 `archive/v7/reports/task-170k-opposing-goal-anchor-reeval-report.md`。

### 4. 单测

**Files:**
- `tests/literary_optimization/test_opposing_goal_anchor.py`
- 更新 `tests/literary_optimization/test_registry.py`（如果存在）

---

## 执行顺序

1. 建立本 task 文档（当前步骤）。
2. 实现 `opposing_goal_anchor` Strategy + 插件 YAML。
3. 复制并调整 170j harness 为 170k。
4. 新增单测并通过。
5. 跑 `ruff check src/ tests/`。
6. `--init` 创建实验项目。
7. 后台/前台跑 Ch29–Ch32 生成。
8. 跑 `run_170k_reeval.py` 出报告。
9. 根据复评结果回填 `archive/v7/tasks/170k-opposing-goal-anchor-DONE.md`。
10. 更新 `docs/STATUS.md`、`tasks/V7-README.md`、`README.md`、`archive/v7/tasks/170-literary-quality-remediation-README.md`。
11. 跑 pytest 全批次验证。

---

## 风险与回退

| 风险 | 缓解 |
|------|------|
| 模型把“对抗性目标”写成套路冲突 | Writer 插件要求冲突必须体现为具体动作/选择/代价，而非口头争执 |
| prompt 过长 | 只给 2–3 个核心角色；叠加 minimal_voice_anchor 后仍可控 |
| 与 170j 框架不兼容 | 沿用插件框架，不修改核心 Agent 代码 |
| 仍未达标 | 在 DONE 文档中诚实记录，建议升级/降级，不继续空转 |

---

## 交付物

- `src/songyan/literary_optimization/strategies/opposing_goal_anchor.py`
- `prompts/literary_plugins/opposing_goal_anchor/creative_director.yaml`
- `prompts/literary_plugins/opposing_goal_anchor/writer.yaml`
- `scripts/run_170k_experiment.py`
- `scripts/run_170k_reeval.py`
- `tests/literary_optimization/test_opposing_goal_anchor.py`
- `archive/v7/reports/task-170k-opposing-goal-anchor-reeval-report.md`
- `archive/v7/tasks/170k-opposing-goal-anchor-DONE.md`
