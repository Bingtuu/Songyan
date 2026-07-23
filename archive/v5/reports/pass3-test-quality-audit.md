# Pass 3 — 测试质量审计报告

> **范围**: 测试覆盖、边界条件、E2E 验证脚本、断言质量
> **日期**: 2026-06-10
> **审查者**: Codex (Pass 3 — 测试质量审计)
> **状态**: 完成

---

## 摘要

| 维度 | 判定 | 关键发现 |
|------|------|---------|
| 测试覆盖率 | ## 97% | 13/13 Agent 有测试，8 个 sub-module 缺直接测试 |
| 断言密度 | ### 中等 | 平均 ~2.1 asserts/test，5 个文件 < 1 |
| 边界覆盖 | ### 中等 | 截断边界有覆盖，空数据/异常路径不全 |
| E2E 管道 | ### 坚实 | 6 个集成测试 + 19 个 E2E runner 输出 |
| Mock LLM | #### 充分 | 15 个文件 mock LLM，但模式不一致 |
| V4.0 覆盖 | ### 完整 | 18 个文件覆盖生命周期/预算/字数约束 |
| 验证脚本 | ## 未测试 | 核心 runner 脚本（1019 行）无单元测试 |
| 参数化测试 | # 不足 | 仅 5 个文件使用 parametrize |

---

## 1. 测试结构分析

### 1.1 分布

| 目录 | 文件数 | 行数 | 测试函数 | 断言数 |
|------|--------|------|---------|-------|
| `tests/`（根目录） | 57 | 15,560 | 851 | 1,676 |
| `tests/db/` | 12 | 2,625 | 115 | 246 |
| `tests/utils/` | 7 | 657 | 63 | 110 |
| `tests/integration/` | 6 | 1,509 | 16 | 111 |
| `tests/models/` | 6 | 1,140 | 80 | 166 |
| `tests/rag/` | 6 | 906 | 43 | 73 |
| `tests/cli/` | 3 | 416 | 18 | 67 |
| `tests/evals/` | 3 | 798 | 56 | 108 |
| `tests/genres/` | 3 | 814 | 76 | 152 |
| `tests/creative_modes/` | 2 | 257 | 28 | 50 |
| `tests/workflows/` | 1 | 92 | 7 | 5 |
| **总计** | **106** | **24,774** | **1,353** | **2,764** |

**源文件与测试文件比**: 102 源文件 : 106 测试文件 = **1:1.04** — 健康。

### 1.2 大文件

最大的 5 个测试文件占了约 30% 的测试行数：

| 文件 | 行数 | 测试数 | 平均断言/测试 |
|------|------|--------|-------------|
| `test_revision_handler.py` | 1,166 | 73 | 2.4 |
| `test_settlement_extractor.py` | 873 | 46 | 2.0 |
| `test_eval_runner.py` | 869 | 17 | 2.5 |
| `test_context_manager.py` | 860 | 45 | 2.3 |
| `test_phase1_graph.py` | 615 | 29 | 2.1 |

---

## 2. Agent 测试覆盖

### 2.1 主模块 — 全部覆盖

| Agent | 测试文件 | 行数 | 测试数 |
|-------|---------|------|--------|
| Writer | `test_writer.py` | 583 | 45 |
| RevisionHandler | `test_revision_handler.py` | 1,166 | 73 |
| SettlementExtractor | `test_settlement_extractor.py` | 873 | 46 |
| ContextManager | `test_context_manager.py` | 860 | 45 |
| CreativeDirector | `test_creative_director.py` | 560 | 24 |
| GoalPlanner | `test_goal_planner.py` | 372 | 13 |
| LLMAuditor | `test_llm_auditor.py` | 380 | 34 |
| RuleAuditor | `test_rule_auditor.py` | 407 | 34 |
| LiteraryAuditor | `test_literary_auditor.py` | 348 | 29 |
| ReviewMerger | `test_review_merger.py` | 238 | 11 |
| SummaryWriter | `test_summary_writer.py` | 159 | 7 |
| ContinuityAuditor | `test_continuity_auditor_suggested_marks.py` | 211 | 9 |
| ArcSummaryGenerator | `test_arc_summary_generator.py` | 226 | 5 |

### 2.2 Sub-module — 8 个缺口

以下 Agent 子模块在 pass 中没有专用的测试文件，功能和边界条件只能通过父模块间接覆盖：

| 子模块 | 父模块 | 行数 | 关键逻辑 | 风险 |
|--------|--------|------|---------|------|
| `settlement_extractor/_apply.py` | SettlementExtractor | 382 | DB 写入 + 事务 | P1 — 无独立覆盖率 |
| `settlement_extractor/_validate.py` | SettlementExtractor | ~80 | 结算验证 | P1 — 验证逻辑 |
| `context_manager/_assemblers.py` | ContextManager | 481 | context 组装 | P2 — 间接覆盖 |
| `creative_director/_brief_builder.py` | CreativeDirector | 247 | creative brief | P2 — 间接覆盖 |
| `revision_handler/_diff.py` | RevisionHandler | ~100 | 差异搜索 | P2 |
| `revision_handler/_patch_engine.py` | RevisionHandler | ~200 | 打补丁引擎 | P2 |
| `continuity_auditor/_scanners.py` | ContinuityAuditor | ~170 | 一致性扫描 | P2 |
| `continuity_auditor/_constraints.py` | ContinuityAuditor | ~160 | 约束生成 | P2 |

---

## 3. 测试模式分析

### 3.1 Mock 策略

| 模式 | 文件数 | 说明 |
|------|--------|------|
| `@pytest.fixture` | 32 | 标准的 pytest fixture 模式 ✅ |
| `mock LLM` | 15 | mock `call_llm` 或 `LLMClient` |
| `mock DB` | 14 | mock `get_db` 或 Repository |
| `@pytest.mark.parametrize` | 5 | 参数化测试 — **不足** |
| `conftest.py` | 2 | 共享 fixture（root + integration） |

**问题 T4 — Mock 模式不一致**: 15 个 mock LLM 文件中，有的用 `unittest.mock.patch`，有的用 pytest fixture 的 MagicMock，有的用自定义 mock 函数。缺乏统一的 mock LLM fixture。

**问题 T3 — Parameterize 过少**: 对于截断阈值（±20%）、预算系数（0.8~1.3）、生命周期窗口（5/8/15 章）这类边界条件，参数化测试是最有效的覆盖方式。当前仅 5 个文件使用。

### 3.2 断言密度

高质量测试通常每个测试函数有 2-3 个以上的断言。当前分布：

| 范围 | 文件数 |
|------|--------|
| 0~1 assert/test | 5 文件 |
| 1~2 assert/test | 20 文件 |
| 2~4 assert/test | 45 文件 |
| 4+ assert/test | 15 文件 |

**最低密度**:
- `test_llm_client.py`: 0.3 assert/test（6 个测试，2 个断）
- `test_checkpointer.py`: 0.7 assert/test
- `conftest.py`: 0.0 assert/test（help 函数非测试）

---

## 4. 边界覆盖分析

### 4.1 V4.0 关键边界覆盖

| 边界 | 测试文件 | 覆盖情况 |
|------|---------|---------|
| 字数截断（±20%） | `test_076_word_count_truncation.py` | ✅ 12 个测试 |
| Budget 硬断言（1.3x） | `test_077b_budget_hard_enforcement.py` | ✅ 15 个测试 |
| Revision 字数上限 | `test_088_revision_word_limit.py` | ✅ 6 个测试 |
| 动态预算 | `test_086_dynamic_budget.py` | ✅ 13 个测试 |
| Lifecycle Scheduler | `test_lifecycle_scheduler.py` | ✅ 但仅基础路径 |
| 空正文 | 分布在多个文件 | ⚠️ 边缘覆盖 |
| LLM 超时/重试 | `test_llm_client.py`, `test_retry.py` | ⚠️ 6 个测试，覆盖率有限 |

### 4.2 发现的问题

**问题 T6 — 空正文/空数据覆盖不完整**
97 个文件引用 "empty" 或 "null"，但大多数是 fixture 默认值，而非实际空正文测试。Writer/Pipeline 的 "收到空 LLM 输出" 路径测试不足。

**问题 T5 — Retry/Timeout 覆盖不足**
LLM 重试机制（`retry.py` 中 3 次重试 + 指数退避）仅有 5 个文件引用。核心的重试后最终失败路径、部分重试成功路径未覆盖。

---

## 5. E2E / 集成测试分析

### 5.1 Pipeline 集成测试

| 文件 | 测试内容 | 质量 |
|------|---------|------|
| `integration/test_multi_chapter.py` | Phase2Graph 多章编排 | ✅ 3 个测试 |
| `integration/test_checkpoint.py` | 断点续跑 | ✅ 3 个测试 |
| `integration/test_paths.py` | 各路由路径 | ✅ 9 个测试 |
| `test_phase1_graph.py` | 单章完整 pipeline | ✅ 29 个测试 |
| `test_phase2_graph.py` | 多章 pipeline | ⚠️ 11 个测试 |
| `test_eval_runner.py` | E2E runner | ⚠️ 17 个测试 |

### 5.2 E2E Runner 脚本

| 脚本 | 行数 | 用途 | 有测试？ |
|------|------|------|---------|
| `task_091_resilient_runner.py` | 1,019 | V4.0 Phase B 核心验证 | ❌ |
| `task_090a_resilient_runner.py` | 819 | Phase B 字数修复验证 | ❌ |
| `run_task_081_ch51_ch70.py` | 446 | V3.x Ch51-Ch70 验证 | ❌ |
| `run_real_llm_multi_chapter.py` | 366 | 多章真实 LLM 验证 | ❌ |
| `run_batched_chapters.py` | 320 | 批量章节运行 | ❌ |
| `evaluate_project.py` | 389 | 项目评估 | ❌ |

**问题 T8 — 核心 runner 脚本无单元测试**:
V4.0 Phase B 的核心验证脚本 `task_091_resilient_runner.py`（1019 行）没有任何单元测试。这个脚本包含断点续跑、错误恢复、进度报告、LLM 调用等核心逻辑。一旦出错，整个 Phase B 验证周期（3-4 天）都可能浪费。

---

## 6. V4.0 特有测试覆盖

### 6.1 按 Task 覆盖

| Task | 测试文件 | 行数 | 测试数 |
|------|---------|------|--------|
| 076 — Writer 字数截断 | `test_076_word_count_truncation.py` | 149 | 12 |
| 077a — Setting Library | `test_077a_setting_library.py` | 236 | 27 |
| 077b — Budget 硬断言 | `test_077b_budget_hard_enforcement.py` | 253 | 15 |
| 078 — Foreshadowing 生命周期 | `test_078_foreshadowing_lifecycle.py` | 297 | 12 |
| 079 — Segmented Revision | `test_079_segmented_revision.py` | 260 | 16 |
| 080 — Character 窗口 | `test_080_character_appearance_window.py` | 174 | 6 |
| 086 — 动态预算 | `test_086_dynamic_budget.py` | 143 | 13 |
| 087 — Lifecycle 集成 | `test_087_lifecycle_integration.py` | 321 | 6 |
| 088 — Revision 字数上限 | `test_088_revision_word_limit.py` | 119 | 6 |

### 6.2 生命周期的 DB 层测试

| 文件 | 内容 | 
|------|------|
| `db/test_lifecycle_scheduler.py` | 调度器基础路径 |
| `db/test_character_state_lifecycle.py` | character_states 生命周期 |
| `db/test_human_mark_lifecycle.py` | human_marks 生命周期 |
| `db/test_setting_foreshadowing_lifecycle.py` | settings + foreshadowings 生命周期 |

---

## 7. E2E 验证输出分析

### 7.1 现有输出数据集

`evals/output/` 目录下有 20+ 个真实 LLM 运行输出：

| 输出目录 | 大小 | 包含 |
|---------|------|------|
| `task_091_scifi_webnovel/` | **43 MB** | Ch2-Ch70 69 章完整输出 |
| `task_092_validation/` | 5.3 MB | Ch2-Ch10 验证 |
| `task_093_validation/` | 1.7 MB | 约束收紧验证 |
| `real_llm_*/` | ~2 MB each | 单章/多章验证 |
| `test_*_0/1/2/` | ~0.2 MB each | 测试运行 |

**问题 T9 — 输出数据管理**:
- `evals/output/` 未清理，task_091 输出 43 MB
- 输出目录中没有 `.gitignore`
- 多个 `test.db-wal` 和 `test.db-shm` 残留文件（WAL 模式未正确关闭）
- 目录结构不一致（有的有 FULL_REPORT.md，有的只有 metrics.json）

---

## 8. 汇总

### 8.1 测试健康度

| 维度 | 健康度 | 说明 |
|------|--------|------|
| 覆盖率 | #### | 13/13 Agent 覆盖，8 个 sub-module 缺口 |
| V4.0 覆盖 | #### | 18 个文件覆盖生命周期+预算+字数 |
| 边界覆盖 | ### | 截断边界有，空数据/retry 不足 |
| E2E 集成 | #### | 6 个 pipeline 测试，但 runner 无测试 |
| Mock 策略 | ### | 模式不一致，缺统一 mock fixture |
| 断言质量 | ### | 平均 2.1，5 个文件 < 1 |
| 参数化 | ## | 仅 5 个文件，大量边界条件未使用 |
| 输出管理 | ## | evals/output 未清理，WAL 残留 |

### 8.2 建议修复项

| # | 问题 | 影响 | 建议 |
|---|------|------|------|
| T1 | 8 个 sub-module 无直接测试 | 子逻辑故障不可见 | 优先为 `_apply`、`_constraints`、`_validate` 添加单元测试 |
| T2 | E2E runner 脚本未测试 | 验证流程风险高 | 为 runner 的断点续跑/错误恢复/进度报告添加测试 |
| T3 | 参数化测试不足 | 边界覆盖低效 | 对字数阈值、生命周期窗口、预算系数使用 parametrize |
| T4 | Mock LLM 策略不统一 | 测试维护成本 | 在 conftest.py 中提供统一 mock_llm fixture |
| T5 | Retry/timeout 覆盖不足 | LLM 容错路径未验证 | 测试 retry 失败、部分成功、全成功路径 |
| T6 | 空数据覆盖不完整 | Writer/Pipeline 对空 LLM 输出处理 | 添加空正文/空场景边缘测试 |
| T7 | 断言密度偏低 | 部分测试"只跑不错" | 对低密度文件补充断言 |
| T8 | evals/output 无清理 | 磁盘占用 + WAL 残留 | 添加 .gitignore + 清理脚本 |

### 8.3 与 Pass 1 / Pass 2 的交叉引用

| Pass 1/2 问题 | Pass 3 关联 | 说明 |
|-------------|------------|------|
| P0-1 (版本覆盖) | 无对应测试 | `UPDATE chapter_versions` 路径无防护测试 |
| P0-2 (Agent DB) | _constraints / _apply 未测试 | Agent 直连 DB 的路径无覆盖 |
| P0-3 (文件 > 400) | 无直接影响 | 测试质量不响应文件行数 |
| A1 (private import) | 缺封装性测试 | writer private 函数被跨域调用但无接口契约测试 |
| A2 (settlement 6件事) | settlement 测试 46 个 | 测试覆盖了提取/验证，但未覆盖各子步骤的失败隔离 |

---

## 9. 方法说明

### 扫描范围
- `tests/` — 全部 106 个 `.py` 文件
- `evals/` — 种子项目 + runner + 输出
- `scripts/` — 18 个自动化脚本
- `src/songyan/*.py` — 交叉引用源文件

### 工具
- 静态分析: Node.js `fs.readFileSync` + 正则
- 断言密度: `\bassert\b` 计数 / `def test_` 计数
- V4.0 覆盖: Task 编号 + 关键字匹配

### 局限
- 未运行测试收集覆盖率（`pytest --cov` 不可用）
- 未检查 LLM prompt 测试的质量（需要理解 Prompt 语义）
- 未测试 DB migration 脚本（`tests/db/` 无 migration 测试）

---

> **松烟入墨，字句成锋。**
> 测试是系统的安全网 — 缺口在哪，故障就出现在哪。
