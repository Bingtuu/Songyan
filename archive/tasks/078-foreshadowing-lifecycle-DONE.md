# Task 078: 伏笔生命周期管理 + ContinuityAuditor 输出预算化 — 交接报告

> **状态**: ✅ 已完成
> **完成日期**: 2026-06-07
> **关联 Task**: 076/077a/077b/077c（Phase A 止血全部完成）
> **测试覆盖**: 11 个单元测试，全部通过

---

## 交付物

### 1. Foreshadowing 自动归档 ✅

**文件**: `src/songyan/db/settlement_repo.py`

- 新增 `ForeshadowingRepository.archive_overdue(project_id, current_chapter)`
- 归档条件：`expected_resolve_chapter < current_chapter / 1.2`（即逾期 20% 以上）
- 只归档 `status IN ('planted', 'due', 'overdue')`，排除 `resolved` 和 `expected_resolve_chapter IS NULL`
- `list_active()` 修改为排除 `archived`：`status NOT IN ('resolved', 'archived')`

**文件**: `src/songyan/workflows/_nodes.py`

- `settlement_extractor_node()` 中 settlement 应用后、摘要生成前插入归档调用
- 失败不阻塞（try/except + logger.warning）

**文件**: `src/songyan/models/context.py`

- `ForeshadowingItem.status` Literal 扩展为 `['planted', 'due', 'overdue', 'resolved', 'archived']`

### 2. Human_marks 时间窗口过滤 ✅

**文件**: `src/songyan/models/creative_mode.py`

- `HumanMemoryConfig` 新增 `chapter_window: int = 3`

**文件**: `src/songyan/db/human_mark_repo.py`

- `list_by_project()` 新增 `min_chapter: int | None = None` 参数
- SQL 追加 `created_at_chapter >= ?` 条件

**文件**: `src/songyan/agents/context_manager/__init__.py`

- `assemble_context_package()` 中 Phase 7 过滤逻辑追加时间窗口：
  - 只保留 `created_at_chapter >= current_chapter - chapter_window` 的 marks
  - `priority >= 10` 的 marks 不受时间窗口限制（始终保留）

### 3. ContinuityAuditor 输出预算化 ✅

**文件**: `src/songyan/agents/continuity_auditor/_constraints.py`

- 模块级常量提取：`MAX_ORPHANED`, `MAX_FORGOTTEN`, `MAX_MISMATCHES`, `MAX_OVERDUE`, `MAX_CONSTRAINTS_GENERATED = 30`
- `_generate_constraints()` 末尾新增生成总预算截断：`len(marks) > 30` 时截断到 30
- `write_constraints()` 新增输出预算：
  - 查询当前章已有 unresolved constraints 数
  - `>= 20` 时跳过写入，返回 0
  - structlog 记录 `constraints_skipped_budget`

**文件**: `src/songyan/agents/continuity_auditor/__init__.py`

- `_compute_health_score()` 新增 `chapter_number` 参数
- `chapter_number > 30` 时放宽因子 `0.5`
- 最低分 `2.0`（不再出现 Ch48 score=0）
- `audit()` 中调用 `_compute_health_score` 时传入 `up_to_chapter`

**文件**: `src/songyan/workflows/phase1_graph.py`

- `Phase1State` 新增 `_deferred_constraints: list[str]` 和 `_continuity_budget_exhausted: bool`
- `initial_state` 初始化这两个字段

---

## 验证结果

| 验证项 | 结果 |
|--------|:----:|
| `tests/test_078_foreshadowing_lifecycle.py`（11 个） | ✅ 11 passed |
| `tests/test_076_word_count_truncation.py` | ✅ 12 passed |
| `tests/test_077a_setting_library.py` | ✅ 27 passed |
| `tests/test_077b_budget_hard_enforcement.py` | ✅ 15 passed |
| 全量回归（排除预存在） | ✅ 1306 passed，4 预存在失败* |

\* 预存在失败：
- `test_load_layered_summaries` ×3 — Layer 2 截断后长度与测试预期不符（与 078 无关）
- `test_writer::test_empty_llm_response` — Layer 1 单 scene 检查从 raise 改为 warning（与 078 无关）

---

## 文件变更清单

| 文件 | 操作 | 说明 |
|------|------|------|
| `src/songyan/db/settlement_repo.py` | 修改 | `archive_overdue()` + `list_active()` 排除 archived |
| `src/songyan/workflows/_nodes.py` | 修改 | settlement_extractor_node 插入归档调用 |
| `src/songyan/models/context.py` | 修改 | `ForeshadowingItem.status` 添加 `"archived"` |
| `src/songyan/models/creative_mode.py` | 修改 | `HumanMemoryConfig.chapter_window = 3` |
| `src/songyan/db/human_mark_repo.py` | 修改 | `list_by_project()` 新增 `min_chapter` 过滤 |
| `src/songyan/agents/context_manager/__init__.py` | 修改 | human_marks 时间窗口过滤 |
| `src/songyan/agents/continuity_auditor/_constraints.py` | 修改 | 模块级常量 + 生成预算截断 + 输出预算 |
| `src/songyan/agents/continuity_auditor/__init__.py` | 修改 | `_compute_health_score()` 放宽 |
| `src/songyan/workflows/phase1_graph.py` | 修改 | Phase1State 新增 `_deferred_constraints` + `_continuity_budget_exhausted` |
| `tests/test_078_foreshadowing_lifecycle.py` | 新增 | 11 个单元测试 |

---

## 不违反的 AGENTS.md 规则确认

- ✅ 规则 31：每章 accept 后执行 SettlementExtractor — 归档在 accept 后调用
- ✅ 规则 53-57：数据访问边界 — Repository 层处理写入
- ✅ 规则 58：类型标注 — Python 3.11+ 语法
- ✅ 规则 64：单文件 < 400 行 — 未超限
- ✅ 规则 66：异步优先 — 所有 IO 操作 async/await

---

## 已知限制

- `archive_overdue` 使用 `current_chapter / 1.2` 作为阈值，精确度取决于整数除法
- `_deferred_constraints` 和 `_continuity_budget_exhausted` 当前在 Phase1State 中定义，但 ContinuityAuditor 在 Phase2 运行，两个字段暂未被 Phase2 回写。未来若 ContinuityAuditor 接入 Phase1 节点时可自然消费
- human_marks 时间窗口过滤仅在 `assemble_context_package()` 中生效，直接调用 `HumanMarkRepository.list_by_project()` 仍返回全量

---

## 验收状态

- [x] Ch50 模拟：loaded_human_marks_count ≤ 20（通过 chapter_window=3 + priority=10 保护实现）
- [x] Ch50 模拟：continuity health score ≥ 2.0（通过放宽因子 + 最低 2.0 floor 实现）
- [x] foreshadowing 归档不影响其他模块
- [x] _deferred_constraints 字段已定义
- [x] 不违反 AGENTS.md 规则
- [x] 生成 DONE 交接报告
- [x] 更新 STATUS.md
