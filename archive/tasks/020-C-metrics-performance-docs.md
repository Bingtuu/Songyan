# Task 020-C: 验收指标收集 + 性能测试 + 文档收尾

> **Phase**: Phase 4 — 评测与优化
> **优先级**: P0
> **依赖**: Task 001 ~ 019（全部完成），Task 020-A（集成测试），Task 020-B（评测集基础设施）
> **预计工作量**: 小
> **前置子任务**: 020-A、020-B

---

## Goal

在 020-B 的评测 runner 基础上实现 10 项验收指标的自动计算逻辑，完成 mock 模式下的性能基准测试，更新项目文档标记 Phase 4 完成，生成交接文件。

## Context

020-A 验证了工作流链路正确，020-B 构建了可重复的评测基础设施。本 Task 是 Phase 4 的**收尾阶段**，负责：

1. **量化验收**：把"设定硬错误数 = 0"等主观目标转化为可自动计算的代码
2. **性能基线**：确立 mock LLM 下的性能基准，作为后续真实 LLM 优化的参照
3. **文档闭环**：更新 STATUS.md、README.md，标记 V1.0 工程阶段全部完成

本 Task 完成后，V1.0 进入**真实题材评测阶段**（手动调用真实 LLM 跑种子项目）。

---

## In Scope（必须完成）

### 1. 验收指标计算模块

- [ ] 创建 `evals/metrics.py`（若逻辑简单可合并到 `evals/runner.py`，但建议独立文件）
- [ ] 实现 `class MetricsCollector`：

```python
class MetricsCollector:
    def __init__(
        self,
        version: ChapterVersion,
        review_report: MergedReviewReport,
        settlement: StateSettlement,
        literary_result: LiteraryAuditResult | None,
        duration_ms: int,
    ): ...

    def collect(self) -> dict[str, float | int]:
        """返回所有验收指标."""
        ...
```

- [ ] 必须实现的 10 项指标：

| 指标键 | 计算逻辑 | 目标值 |
|--------|----------|--------|
| `pipeline_success` | `1` 如果流程到达 `done`，否则 `0` | `1` |
| `hard_errors` | `review_report.critical_issues` 中 `category == "world_consistency"` 的数量 | `0` |
| `ai_tell_count` | `review_report.rule_result.ai_tells_count` | `< 2` |
| `fatigue_word_count` | `review_report.rule_result.fatigue_words_count` | `< 3` |
| `hook_opening_pass` | `review_report.rule_result.opening_hook_pass` 或 `review_report.llm_result.opening_hook_score >= 0.7` | `1` |
| `hook_closing_pass` | `review_report.rule_result.closing_hook_pass` 或 `review_report.llm_result.closing_hook_score >= 0.7` | `1` |
| `settlement_field_accuracy` | `settlement.character_updates` 中 `old_value == db_current_value` 的比例 | `> 0.9` |
| `setting_key_accuracy` | `settlement.new_settings` 中 `setting_key` 唯一且 `source_quote in content` 的比例 | `> 0.9` |
| `conceptual_idling_count` | `literary_result.observations` 中 `type == "conceptual_idling"` 的数量 | `0`（网文/混合） |
| `revision_new_issues` | 第 2 轮审查产生的 critical/major issue 数量（通过对比两轮 review_report） | `0` |

- [ ] 指标计算必须基于**真实 DB 数据**（从 repository 读取），不能基于 mock 的假设值
- [ ] 对于需要人工评分的指标（如"人物语言区分度 > 70%"），本阶段标记为 `None` 或跳过，在真实 LLM 评测阶段手动补充

### 2. 性能基准测试

- [ ] 在 `tests/test_integration.py` 中新增性能测试类，或在 `tests/test_eval_runner.py` 中新增：

| 测试项 | 目标 | 测量方式 |
|--------|------|----------|
| 单章完整闭环（mock LLM） | `< 5000 ms` | `time.perf_counter()` 包裹 `run_chapter_pipeline` + `resume_human_confirm` |
| 审查串联（Rule + LLM + Merger + Literary） | `< 1000 ms`（mock 下） | 单独测量 4 个节点耗时 |
| 双层审查（Rule + LLM） | `< 100 ms`（mock 下，Rule < 200ms + LLM mock ≈ 0ms） | 单独测量 |

- [ ] 性能测试**不阻塞 CI**（标记为 `pytest.mark.performance`，默认不运行）
- [ ] 性能测试失败时输出实际耗时，方便后续优化参照

### 3. 评测结果断言

- [ ] 在 `tests/test_eval_runner.py` 中，对 3 个种子项目的 mock 运行结果断言指标：
  - `hard_errors == 0`
  - `ai_tell_count < 2`
  - `fatigue_word_count < 3`
  - `hook_opening_pass == 1`
  - `hook_closing_pass == 1`
  - `settlement_field_accuracy > 0.9`
  - `setting_key_accuracy > 0.9`

> **注意**：mock 模式下部分指标可能因 mock 数据设计而恒成立，本阶段重点验证**指标计算逻辑正确**，而非指标值本身达标。真实 LLM 评测阶段才是指标达标的最终验证。

### 4. 文档更新

- [ ] 更新 `docs/STATUS.md`：
  - 当前阶段改为 "Phase 4 — 评测与优化 **已完成**"
  - 在"已完成"列表中追加 Task 020-A / 020-B / 020-C
  - 待开始列表清空（或改为 "V1.0 真实题材评测阶段"）
  - 阻塞项保持"无"
  - 最近变更追加 020-A/B/C 完成记录

- [ ] 更新 `README.md`：
  - 项目状态改为 "Phase 4 已完成（22/22 Task），共 XXX 个测试全部通过"
  - Phase 表格追加 Phase 4 行
  - 快速开始追加 `python -m evals` 示例命令
  - 验证命令更新测试总数

### 5. 交接文件

- [ ] 生成 `tasks/020-e2e-evaluation-DONE.md`（父任务总交接文件）
  - 汇总 020-A / 020-B / 020-C 的交付内容
  - 记录测试总数增量
  - 记录已知限制（mock 评测 ≠ 真实 LLM 评测）

---

## Out of Scope（明确不做）

- 真实 LLM 调用跑评测（V1.0 验收阶段手动执行）
- 指标不达标时的自动调优
- 多模型路由对比评测
- 连续多章生成评测
- Web UI / TUI 展示评测仪表盘
- PostgreSQL / Redis / Qdrant 迁移

---

## 接口契约

```python
# evals/metrics.py

class MetricsCollector:
    """从已生成的章节产物中计算验收指标."""

    def __init__(
        self,
        version: ChapterVersion,
        review_report: MergedReviewReport,
        settlement: StateSettlement,
        literary_result: LiteraryAuditResult | None = None,
        duration_ms: int = 0,
        previous_report: MergedReviewReport | None = None,  # 用于计算 revision_new_issues
    ) -> None: ...

    def collect(self) -> dict[str, float | int | None]:
        """返回指标字典.

        键名与 Task 020 验收指标表一致。
        无法自动计算的指标返回 None。
        """
        ...

    def is_pass(self) -> bool:
        """返回是否所有可计算指标均达标."""
        ...

# runner.py 中的 EvaluationResult.metrics 由 MetricsCollector 填充
```

---

## 数据模型

本 Task **不新增业务模型**。`MetricsCollector` 为纯计算类，无 Pydantic 模型要求。

---

## 测试要求

### Layer 1: 指标计算单元测试
- [ ] `hard_errors` 计算正确（mock 含/不含 world_consistency critical）
- [ ] `ai_tell_count` 从 RuleAuditResult 正确提取
- [ ] `fatigue_word_count` 从 RuleAuditResult 正确提取
- [ ] `hook_opening_pass` / `hook_closing_pass` 正确合并 Rule + LLM 结果
- [ ] `settlement_field_accuracy` 正确对比 old_value 与 DB 当前值
- [ ] `setting_key_accuracy` 正确检查唯一性和 source_quote 存在性
- [ ] `conceptual_idling_count` 从 LiteraryAuditResult 正确提取
- [ ] `revision_new_issues` 正确对比两轮 review_report

### Layer 2: 性能测试
- [ ] mock 下单章闭环耗时 < 5s（`pytest.mark.performance`）
- [ ] mock 下审查串联耗时 < 1s（`pytest.mark.performance`）
- [ ] 性能测试输出实际耗时到日志

### Layer 3: 集成断言
- [ ] 3 个种子项目 mock 运行后指标计算不报错
- [ ] `EvaluationResult.metrics` 包含全部 10 个键
- [ ] 指标值类型正确（int / float / None）

---

## 验收标准（Acceptance Criteria）

- [ ] `pytest tests/test_eval_runner.py -v` 全部通过（含指标断言）
- [ ] `pytest tests/test_integration.py -v` 全部通过（含性能测试，若标记为 performance 则默认运行单元测试路径）
- [ ] `pytest -m "not performance"` 通过（不含性能测试的常规 CI 集）
- [ ] `docs/STATUS.md` 已更新为 Phase 4 完成状态
- [ ] `README.md` 已更新 Phase 4 完成状态、测试总数、`python -m evals` 命令
- [ ] 代码符合 CLAUDE.md 规范（类型标注、单文件 < 400 行等）
- [ ] 不违反任何不可违背规则
- [ ] 生成了 `tasks/020-C-metrics-performance-docs-DONE.md` 交接文件
- [ ] 生成了 `tasks/020-e2e-evaluation-DONE.md` 父任务总交接文件

---

## 参考文档

- `tasks/020-e2e-evaluation.md` — 父任务总纲
- `tasks/020-A-mock-e2e-integration.md` — 上游子任务
- `tasks/020-B-eval-seed-infrastructure.md` — 上游子任务
- `docs/STATUS.md` — 需要更新的状态看板
- `README.md` — 需要更新的项目说明
- `docs/architecture/04-vibe-coding-engineering.md` — 工程手册 + 验收指标定义
- `system_prompt/development-tech-plan-v2.md` — V2 技术方案第 10 章（验收指标）
