# Task 107-DONE: Repair Convergence Guardrail + Fix 150-Blockers

## 任务摘要

本 Task 合并了原计划的 Repair Convergence Guardrail（修订/重写收敛护栏）与 150-Blockers 修复。系统性 review 发现 8 项缺陷，其中 2 项 P0 级问题会直接阻断 150 章全自动验证。本次对这 8 项缺陷进行了整体修复。

## 修复清单

| # | 缺陷 | 严重度 | 修复文件 |
|---|------|--------|---------|
| 1 | skip_settlement 在 auto_confirm 下被误判为章节失败 | P0 | `_nodes.py`, `phase1_graph.py` |
| 2 | skip_settlement 跳过 settlement 导致上下文链式污染 | P0 | `_nodes.py` |
| 3 | rewrite 后劣化检测仍以初稿为基准 | P1 | `_nodes.py` |
| 4 | LiteraryAuditor 与 ScoreCard 决策冲突 | P1 | `_nodes.py` |
| 5 | quality_gate 长度标准变严未校准 | P1 | `score_aggregator.py` |
| 6 | _load_chapter_repair_state 废弃版本污染计数 | P2 | `_nodes.py` |
| 7 | accept 路径 ratio>1.40 字数守卫冗余 | P2 | `_nodes.py` |
| 8 | max_revision_rounds 参数未透传 | P2 | `phase1_graph.py`, `phase2_graph.py` |

## 关键设计决策

### 1. skip_settlement 成功路径（P0）

**问题**：`_skip_settlement=True` 时 `human_confirm_router` 路由到 `END`，最终 state 的 `status="settlement"` 而非 `"done"`，`phase2_graph._run_single_chapter` 判定为失败。

**修复**：
- `human_confirm_router` 中删除 `_skip_settlement` 特殊分支，统一走 `"accept"` → `"settlement_extractor"`
- `settlement_extractor_node` 内部检测 `_skip_settlement`：
  - 跳过 LLM 调用 (`extract_settlement` / `apply_settlement`)
  - 跳过依赖 settlement 的 `write_chapter_summary`
  - 但仍执行 `_run_lifecycle_cleanup`、RAG 索引、SettingEvaporator、分层摘要
  - 生成极简 fallback summary（正文前 300 字符）写入 `summaries` 表
- 最终 `status="done"`，`phase2_graph` 正确识别为成功

### 2. rewrite best-baseline 更新（P1）

**问题**：rewrite 后 `review_merger_node` 仍以初稿为 best 基准，rewrite 允许的字数范围（±20%，ratio=1.20）触发劣化回滚。

**修复**：
- `rewrite_node` 成功返回时注入 `"_best_version_id": version.version_id` 和 `"_best_score_card": None`
- `review_merger_node` 识别 `_best_score_card is None` 时，将当前 rewrite 版本的 `score_card` 保存为新的 best 基准
- 后续 revision 的劣化检测与 rewrite 版本比较，避免误回滚

### 3. Literary-ScoreCard 决策合并（P1）

**问题**：`literary_auditor_node` 检测到 critical 时设置 `_needs_revision=True`，但 `review_merger_node` 用 `score_card.flags.needs_revision`（仅看 coherence）覆盖。

**修复**：`review_merger_node` 中 `needs_revision = score_card.flags.needs_revision or state.get("_needs_revision", False)`，取并集。

### 4. length_ok 阈值校准（P1）

**问题**：新 score_card `length_ok = length_score >= 0.6`（ratio ≤ 1.20），旧 fallback 为 ratio > 1.30 才 fail，标准漂移导致更容易触发质量门失败。

**修复**：`length_ok` 阈值从 `>= 0.6` 放宽到 `>= 0.5`（对应 ratio ≈ 1.25），更接近历史基线。

### 5. 废弃版本过滤（P2）

**修复**：`_load_chapter_repair_state` 中 `revision_count` 只统计 `is_abandoned=False` 的版本，避免重试时废弃版本污染 repair_exhausted 判断。

### 6. max_revision_rounds 透传（P2）

**修复**：`run_chapter_pipeline` 接受 `max_revision_rounds` 参数并注入 `initial_state`；`revision_router` 从 state 读取；`phase2_graph._run_single_chapter` 透传。

## 测试

- 新增 `tests/test_108_core_nodes.py`：4 个专项测试
  - skip_settlement 跳过 LLM 但保留规则维护
  - rewrite 后返回 best_version_id / best_score_card
  - literary critical 不被 score_card 覆盖
  - 废弃版本不计入 repair state
- 更新 `tests/test_107_convergence_guardrail.py`：适配 human_confirm_router 行为变更
- 更新 `tests/test_106_scoring_system.py`：适配 length_ok 阈值变更
- 删除 `tests/test_phase1_graph.py` 中 `TestHumanGateNodeWordCountGuard`（测试已删除的守卫）

## 回归验证

```
pytest tests/ -q
# 1524 passed, 4 skipped, 2 xfailed, 3 xpassed, 10 warnings

ruff check src/songyan/workflows/_nodes.py src/songyan/workflows/phase1_graph.py \
  src/songyan/workflows/phase2_graph.py src/songyan/evals/score_aggregator.py \
  tests/test_108_core_nodes.py tests/test_106_scoring_system.py \
  tests/test_phase1_graph.py tests/test_107_convergence_guardrail.py
# All checks passed!
```

## 已知限制

- `skip_settlement` 的 fallback summary 是极简摘录（前 300 字符），不如 LLM 生成的 summary 精炼。但这是收敛失败时的降级保护，确保后续章节仍有 `previous_summary`。
- `Phase1State` 字段持续膨胀（30+ 个），到 150 章时 checkpointer 序列化开销可能增加，建议后续评估是否需要拆分。

## 下一 Task

**Task 108: CharacterLifecycleAuditor**（角色退场机制）
- 非核心角色 30 章未出场 → dormant
- 活跃角色硬上限 ≤ 10
- 支撑 150 章角色池控制
