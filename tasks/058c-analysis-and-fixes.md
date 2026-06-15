# Task 058c: 058b 验证结果分析 + 关键问题修复

> **Phase**: V3.0 Layer 2 — 核心验证层
> **优先级**: P0
> **依赖**: Task 058b（30 章封闭验证执行）
> **预计工作量**: 中（~0.5~1 天）

---

## Goal

基于 058b 30 章实际运行数据，完成三项分析 + 四项修复，将系统稳定性从"能跑通"提升到"跑得稳"。

---

## Context

058b 已成功生成 30 章（133,440 字），但运行日志暴露出 4 类问题：

| 问题类别 | 严重程度 | 现象 |
|---------|---------|------|
| 监控字段缺失 | P0 | `content_preservation_ratio` / `continuity_health_score` 全部为 `null`，058a 基础设施"有定义无接线" |
| Revision 负担过重 | P1 | 80% 章节（24/30）打到 2 轮 revision 上限，初稿质量不够稳定 |
| 字数控制失效 | P1 | 变异系数 17.7%，Ch8=6465 字 vs Ch26=2958 字，目标 4000 字基本无约束力 |
| 上下文膨胀 | P1 | Ch24 `budget_used=3.96`（38K tokens），Ch30 `budget_used=4.29`（41K tokens），预算是 9600 tokens。Prune 后仍为预算的 3.5~4.3 倍 |

本 Task 的目标不是重写 Prompt 或重构架构，而是**做最小必要修复**，让监控数据可信、revision 负担可控、字数有基本约束。

---

## In Scope（必须完成）

### P0 — 监控字段补全

- [ ] **修复 `continuity_health_score` 采集**
  - 问题：`phase2_graph.py` 第 177 行读取了 `report.overall_health_score`，但 `log_chapter_run()` 调用时未传入该参数
  - 修复：将 `continuity_health_score` 传递到 `log_chapter_run()` 调用处
  - 验证：运行后 JSONL 中该字段非 null（对于第 3/6/9/... 章）

- [ ] **修复 `content_preservation_ratio` 采集**
  - 问题：`build_chapter_run_log` 从 `state.get("_content_preservation_ratio")` 读取，但 30 章全部为 null
  - 根因分析：`revision_handler_node` 返回的 `_content_preservation_ratio` 可能被后续节点覆盖，或 `final_state`（来自 `run_chapter_pipeline` 返回值）未包含该字段
  - 修复：确保 `run_chapter_pipeline` 返回的 state 中包含 `_content_preservation_ratio`；若缺失，在 `_run_logger.py` 中从 revision 版本记录反查
  - 验证：运行后 JSONL 中该字段非 null

### P1 — Revision 负担分析与缓解

- [ ] **Issues 类型分布分析**
  - 查询 `review_reports` 表，统计 30 章 LLM audit issues 的 `issue_type` 分布
  - 重点关注：哪些 issue_type 出现频率最高？哪些 issue_type 在 revision 后仍重复出现？
  - 输出：`docs/review/058c_issue_type_distribution.md`

- [ ] **Rule Auditor 字数维度增强**
  - 在 `RuleAuditResult` 中新增 `word_count` 和 `word_count_ratio` 字段
  - 在 `rule_auditor_node` 中计算实际字数 / 目标字数（从 `ChapterGoal.word_count_target` 读取）
  - 当 `word_count_ratio > 1.3`（即超标 30%）时，标记为 violation
  - 这样字数超标将进入 revision 流程（Writer 被强制修正）

- [ ] **Writer Prompt 字数约束强化（最小修改）**
  - 在现有 Prompt 的字数段落中增加一句硬约束："若输出超过目标字数 20%，输出将被拒绝并重写"
  - 不修改 Prompt 整体结构，只增加威慑性语句

### P1 — 上下文膨胀修复

基于日志数据分析（Ch15~Ch30 prune 后 33K~41K tokens，预算 9600），根因是大量分区完全不被裁剪 + 角色未过滤 + prune 终止条件有 bug。

- [ ] **修复 prune 终止条件 Bug**
  - 问题：`BudgetPruner._prune_character_states()` 后没有检查 `current <= budget`，直接返回，导致超标无感知
  - 修复：最后一层裁剪后也检查是否达标，不达标时记录 `context_manager.prune_failed_hard_limit` warning
  - 位置：`src/songyan/agents/context_manager/__init__.py` line 144-148

- [ ] **过滤不出场角色**
  - 问题：`_build_character_snapshots()` 遍历项目中所有角色，不区分是否出场（违反 AGENTS.md #42）
  - 修复：在 `_build_character_snapshots()` 中增加出场过滤，只加载 `current_chapter` 的 `characters_appeared` 中的角色 + 主角（importance_score >= 0.9）
  - 回退：若无出场记录，保留主角 + importance_score 最高的 3 个角色

- [ ] **chapter_goal.obligations 硬上限**
  - 问题：SettlementExtractor 每章提取的 obligations 全部累积到 ChapterGoal，无上限
  - 修复：`_build_hard_constraints()` 中只保留最近 `MAX_OBLIGATIONS = 10` 条 obligations
  - 更早的 obligations 转为 soft_references（降低优先级但保留可检索性）

- [ ] **recent_plot.key_events 截断**
  - 问题：`_build_recent_plot()` 对 `summary` 做 200 字符截断，但 `key_events`、`characters_appeared` 等字段未被截断
  - 修复：`ChapterSummary` 构建时限制 `key_events` 最多 3 条，`characters_appeared` 最多 5 个
  - 位置：`src/songyan/agents/context_manager/_assemblers.py`

- [ ] **上下文膨胀根因分析报告**
  - 输出：`docs/review/058c_context_bloat_analysis.md`
  - 内容：实际数据趋势、各分区 token 占比估算、修复后预期效果

### 数据归档

- [ ] **将 JSONL 日志合并归档到 `docs/review/v30_layer2_runlog.jsonl`**
- [ ] **更新 `docs/STATUS.md`**：填入 058b 实际运行数据
- [ ] **生成 `tasks/058c-analysis-and-fixes-DONE.md`**

---

## Out of Scope（明确不做）

- 不重写 Writer Prompt（V3.1 任务）
- 不修改 LLM 模型或温度参数
- 不做人工质量评分或盲测
- 不修复 RAG（`vector_store.total_chunks=0` 属于已知问题，不在 058c 范围）
- 不修复 Settlement 数据噪声（source_quote 验证错误属于数据质量问题，非阻塞性）

---

## 接口契约

### 修改点 1：log_chapter_run 调用处

```python
# src/songyan/workflows/phase2_graph.py
# 在 run_project_pipeline 的 chapter 循环中

# 修复前：
await log_chapter_run(
    ...,
    final_state=final_state,
    duration_sec=duration_sec,
)

# 修复后：
await log_chapter_run(
    ...,
    final_state=final_state,
    continuity_health_score=continuity_health_score,  # 新增
    duration_sec=duration_sec,
)
```

### 修改点 2：RuleAuditResult 扩展

```python
# src/songyan/models/review_models.py

class RuleAuditResult(BaseModel):
    # ... 现有字段 ...
    word_count: int = 0
    word_count_target: int = 0
    word_count_ratio: float = 0.0  # 实际/目标，>1.3 为超标
```

### 修改点 3：rule_auditor_node 字数检查

```python
# src/songyan/workflows/_nodes.py

async def rule_auditor_node(state: dict[str, Any]) -> dict[str, Any]:
    # ... 现有逻辑 ...
    
    # 新增：字数检查
    goal = await load_chapter_goal(state["project_id"], state["chapter_number"])
    word_count = _count_chinese_words(version.content)
    word_count_target = goal.word_count_target if goal else 4000
    word_count_ratio = word_count / word_count_target if word_count_target > 0 else 0
    
    result.word_count = word_count
    result.word_count_target = word_count_target
    result.word_count_ratio = round(word_count_ratio, 2)
    
    if word_count_ratio > 1.3:
        result.violations.append(Violation(
            type="word_count_exceeded",
            severity="major",
            message=f"字数超标 {int((word_count_ratio-1)*100)}%",
            evidence=f"实际 {word_count} 字，目标 {word_count_target} 字",
        ))
    
    # ... 现有保存逻辑 ...
```

### 修改点 4：prune 终止条件修复

```python
# src/songyan/agents/context_manager/__init__.py
# BudgetPruner.prune() line 144-148

# 修复前：
ctx = self._prune_character_states(ctx, budget_tokens)
current = self._estimate_package(ctx)
ctx.estimated_tokens = current
ctx.budget_used = current / budget_tokens
return ctx

# 修复后：
ctx = self._prune_character_states(ctx, budget_tokens)
current = self._estimate_package(ctx)
ctx.estimated_tokens = current
ctx.budget_used = current / budget_tokens if budget_tokens > 0 else 0.0

if current > budget_tokens:
    logger.warning(
        "context_manager.prune_failed_hard_limit",
        final_tokens=current,
        budget=budget_tokens,
        overage=current - budget_tokens,
    )
return ctx
```

### 修改点 5：过滤不出场角色

```python
# src/songyan/agents/context_manager/_assemblers.py
# _build_character_snapshots()

# 修复前：
for char in characters:
    ...

# 修复后：
# 只保留出场角色 + 主角
from collections import Counter
appeared_ids = set()
for state in character_states:
    appeared_ids.add(state.character_id)

# 获取当前章的出场记录（从 recent_summaries 中）
# 若无记录，回退到主角 + 高分角色
filtered_chars = []
for char in characters:
    if char.character_id in appeared_ids or char.importance_score >= 0.9:
        filtered_chars.append(char)

# 若过滤后为空，回退到 importance_score 最高的 3 个
if not filtered_chars and characters:
    filtered_chars = sorted(characters, key=lambda c: c.importance_score, reverse=True)[:3]

for char in filtered_chars:
    ...
```

### 修改点 6：obligations 硬上限 + key_events 截断

```python
# src/songyan/agents/context_manager/_assemblers.py

# obligations 硬上限（_build_hard_constraints）
MAX_OBLIGATIONS = 10
obligations = chapter_goal.obligations[-MAX_OBLIGATIONS:] if len(chapter_goal.obligations) > MAX_OBLIGATIONS else chapter_goal.obligations

# key_events 截断（_build_recent_plot 或 ChapterSummary 构建时）
MAX_KEY_EVENTS = 3
MAX_CHARACTERS_APPEARED = 5
for s in summaries:
    s.key_events = s.key_events[:MAX_KEY_EVENTS]
    s.characters_appeared = s.characters_appeared[:MAX_CHARACTERS_APPEARED]
```

---

## 数据模型

本 Task 主要复用现有模型，仅扩展 `RuleAuditResult`：

```python
class RuleAuditResult(BaseModel):
    """规则审计结果."""
    
    # 现有字段保留...
    ai_tell_count: int = 0
    fatigue_word_count: int = 0
    has_opening_hook: bool = False
    has_ending_hook: bool = False
    violations: list[Violation] = Field(default_factory=list)
    
    # 新增字段
    word_count: int = 0
    word_count_target: int = 0
    word_count_ratio: float = 0.0
```

---

## 测试要求

### Layer 1: 模型测试
- [ ] `RuleAuditResult(word_count=5000, word_count_target=4000, word_count_ratio=1.25)` 可正确实例化

### Layer 2: 模块测试
- [ ] `_run_logger.build_chapter_run_log()` 传入 `continuity_health_score=8.5` 后，输出 JSONL 包含该值
- [ ] `rule_auditor_node` 在字数超标 30% 时正确生成 `word_count_exceeded` violation
- [ ] `rule_auditor_node` 在字数正常时不生成该 violation
- [ ] `BudgetPruner.prune()` 在无法压入预算时记录 `prune_failed_hard_limit` warning
- [ ] `_build_character_snapshots()` 过滤后只包含出场角色 + 主角
- [ ] `_build_hard_constraints()` 对超过 10 条的 obligations 只保留最近 10 条

### Layer 3: 集成测试
- [ ] Mock 跑 1 章完整流程，验证 JSONL 中 `continuity_health_score` 和 `content_preservation_ratio` 均非 null
- [ ] 组装 ContextPackage 后验证 `budget_used < 3.0`（修复前 3.5x，目标显著下降）

---

## 验收标准

- [ ] `content_preservation_ratio` 和 `continuity_health_score` 在 JSONL 日志中正常采集（非 null）
- [ ] `RuleAuditResult` 新增字数字段，字数超标 30% 触发 violation
- [ ] Issues 类型分布分析报告完成
- [ ] 上下文膨胀 4 项修复完成（prune 终止条件 + 角色过滤 + obligations 上限 + key_events 截断）
- [ ] 上下文膨胀根因分析报告完成（结论写入 `docs/review/058c_context_bloat_analysis.md`）
- [ ] `pytest tests/ --ignore=tests/integration -q` 基线通过（≥1025 passed）
- [ ] 不违反 AGENTS.md 任何规则（尤其 #58-67 代码规范）
- [ ] 更新了 `docs/STATUS.md`
- [ ] 生成了 `tasks/058c-analysis-and-fixes-DONE.md`

### 关键阈值

| 指标 | 修复前 | 修复后目标 |
|------|--------|-----------|
| 监控字段 null 率 | 100% | 0% |
| 字数超标检测覆盖率 | 0% | 100%（超标 30% 必检） |
| 平均 revision 轮数 | 1.80 | 目标 ≤1.5（Writer Prompt 威慑效果） |
| 上下文 budget_used（Ch30） | 4.29x（41K tokens） | 目标 < 3.0x（< 28K tokens） |

---

## 参考文档

- `tasks/058b-30ch-execution.md` — 058b 规格
- `tasks/058a-monitoring-infrastructure-DONE.md` — 058a 交接报告
- `src/songyan/workflows/_run_logger.py` — 监控日志服务
- `src/songyan/workflows/phase2_graph.py` — 多章编排层
- `src/songyan/workflows/_nodes.py` — 节点函数
- `src/songyan/models/review_models.py` — 审查模型
- `src/songyan/agents/context_manager/__init__.py` — BudgetPruner 与上下文组装
- `src/songyan/agents/context_manager/_assemblers.py` — 分区构建器
- `src/songyan/utils/token_estimator.py` — Token 估算器
- `projects/orbital_horror_058b/logs/` — 058b 归档日志
