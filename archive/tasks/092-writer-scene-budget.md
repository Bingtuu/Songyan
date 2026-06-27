# Task 092: Writer 字数预算分配 + 动态目标调整

> **Phase**: V4.0 Phase B — 修复
> **优先级**: P0
> **依赖**: Task 090b（rewrite 字数护栏已就位）
> **预计工作量**: 大（4 天）

---

## Goal

将 Writer 从"自底向上"（写完再数）改为"自顶向下"（按预算规划场景），实现精确的字数控制。同时让 GoalPlanner 根据章节类型动态调整目标字数。

---

## Context

### 当前问题（Task 091 确认）

- Writer 超标率：**46.4%**（32/69 章 >1.2x）
- 极端值：Ch46 **1.768x**（5659 字 / 3200）
- 超标根因：
  1. Writer craft card 只有 `word_count_target`，没有场景级预算
  2. Writer 先生成 2-3 个场景，每场景自然膨胀到 1500-2000 字
  3. 结构固化后 RevisionHandler 无法压缩（结构保护）
  4. Rewrite fallback 有效但代价高（4-5 版本、16-19 次 LLM 调用）

### 为什么 090b 的 rewrite 不够

090b 的 rewrite 是"事后补救"，在 Writer 已经写出 5607 字后再截断到 2646 字。这导致：
- 截断后只剩 1 个场景（叙事节奏被毁）
- 需要多轮 revision 重新修复结构
- LLM 调用翻倍

**本 Task 的目标是让 Writer "第一次就写对"**，减少 rewrite 触发频率。

---

## In Scope（必须完成）

### 1. Writer Craft Card 增加 `scene_budget` 结构

修改 `prompts/cards/writer-v1.0.6.yaml`（或升级到 v1.0.7）：

```yaml
scene_budget:
  description: "按目标字数规划每个场景的字数预算"
  rules:
    - "总字数必须严格控制在 target_word_count ±15% 范围内"
    - "每个场景的字数预算 = 场景权重 × 目标字数"
    - "过渡场景（exposition/transition）权重 ≤ 0.3"
    - "冲突场景（conflict）权重 ≤ 0.5"
    - "高潮场景（climax）权重 ≤ 0.6"
    - "结尾钩子（ending_hook）单独计算，≤ 100 字"
  output_format:
    planned_scenes:
      - scene_number: 1
        type: "conflict"
        budget_words: 1400
        min_words: 1100
        max_words: 1700
      - scene_number: 2
        type: "transition"
        budget_words: 1000
        min_words: 800
        max_words: 1300
      - scene_number: 3
        type: "exposition"
        budget_words: 600
        min_words: 400
        max_words: 900
    total_planned: 3000
    target: 3200
    tolerance: "±15%"
```

### 2. Writer 生成逻辑改造

在 `src/songyan/agents/writer.py` 中：

- **Step 1**：Writer 先输出 `scene_budget`（规划阶段，不生成正文）
- **Step 2**：Writer 按场景预算逐场景生成
- **Step 3**：每场景生成后统计字数，如果超出预算，在当前场景内截断（而非等全部写完再截断）
- **Step 4**：全部场景生成后汇总，如果总字数仍超标，触发 rewrite（但此时已有预算数据，rewrite 更精准）

### 3. GoalPlanner 动态目标调整

在 `src/songyan/agents/goal_planner.py` 中：

根据章节类型调整目标字数：

```python
WORD_COUNT_TARGETS = {
    "exposition": (2800, 3200),     #  exposition 章字数较少
    "transition": (2500, 3000),     # 过渡章字数更少
    "conflict": (3200, 3800),       # 冲突章字数较多
    "climax": (3500, 4200),         # 高潮章字数最多
    "resolution": (2800, 3200),     # 收尾章适中
    "tech_revelation": (3200, 3800), # 设定揭示章需要空间
}
```

已有部分实现（Ch60、Ch70 目标提升到 3500），但需要系统化。

### 4. 保留 090b 的 rewrite fallback

Scene budget 不是替代 rewrite，而是减少 rewrite 触发频率。090b 的硬截断逻辑完整保留。

---

## Out of Scope（明确不做）

- 修改 RevisionHandler（Task 094 负责）
- 修改 ContextManager / ContextService
- 修改 SettlementExtractor
- 废弃现有的 Writer prompt v1.0.6（保留兼容）

---

## 接口契约

### Writer 输出格式变更

```python
class WriterOutput(BaseModel):
    """Writer 的新输出格式（向后兼容）."""
    content: str                        # 正文（不变）
    scenes: list[Scene]                 # 场景列表（新增）
    scene_budget: SceneBudget | None    # 场景预算（新增）
    word_count: int                     # 总字数（不变）
    scenes_count: int                   # 场景数（不变）
    budget_compliance: bool             # 是否遵守预算（新增）
    budget_deviation: float             # 预算偏差比例（新增）

class Scene(BaseModel):
    scene_number: int
    type: str                          # exposition / conflict / climax / transition
    content: str
    word_count: int
    budget_words: int
    budget_compliance: bool
```

---

## 测试要求

### Layer 2: 模块测试
- [ ] `scene_budget` 规划阶段输出正确的字数分配
- [ ] 冲突场景预算 > 过渡场景预算
- [ ] 总预算 ≈ target_word_count ±15%
- [ ] 单场景字数超出预算时，场景内截断不破坏叙事

### Layer 3: 集成测试
- [ ] Ch1-Ch5 端到端跑通，字数达标率 > 80%
- [ ] Rewrite 触发率 < 20%（当前 ~30%）
- [ ] 单场景章节（scenes_count=1）出现率 < 5%

### 回归测试
- [ ] `pytest -x -q` 全量通过

---

## 验收标准（Acceptance Criteria）

- [ ] Writer craft card 包含 `scene_budget` 结构
- [ ] GoalPlanner 根据章节类型输出动态目标字数
- [ ] Ch1-Ch10 端到端验证：字数达标率 **> 75%**
- [ ] Ch1-Ch10 端到端验证：rewrite 触发率 **< 25%**
- [ ] Ch1-Ch10 端到端验证：单场景章节 **< 2 章**
- [ ] `pytest -x -q` 全部通过
- [ ] 生成了 `tasks/092-writer-scene-budget-DONE.md`

---

## 参考

- `evals/output/task_091_scifi_webnovel/report.md` — Task 091 完整报告
- `src/songyan/agents/writer.py`
- `src/songyan/agents/goal_planner.py`
- `prompts/cards/writer-v1.0.6.yaml`
