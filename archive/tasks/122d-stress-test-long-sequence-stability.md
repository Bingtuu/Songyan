# Task 122d: Stress Test — Long Sequence Stability

> **日期**: 2026-06-23（更新于 2026-06-26）
> **类型**: V5.1 压力测试
> **状态**: **✅ DONE**
> **前置**: 122a + 122b + 122c 已完成
> **测试文件**: `tests/integration/test_122d_long_sequence_stability.py`

---

## 1. 目标

在不调用 LLM（或最小化调用）的情况下，验证 150 章长序列的上下文管理、状态机和 AutoHalt 策略的稳定性。

---

## 2. 测试矩阵

| 测试名 | 方法 | 断言 |
|--------|------|------|
| `test_context_budget_150_chapters` | mock LLM，模拟 budget_used 趋势 | 无 >1.2 的异常跳变 |
| `test_human_marks_decay_6_chapters` | 注入 marks，验证蒸发 | 第7章 marks 数量为 0 |
| `test_auto_halt_false_positive` | 连续3章 emergency + QG pass | AutoHalt **不**触发 |
| `test_auto_halt_true_positive` | 连续3章 emergency + QG fail | AutoHalt 触发 |
| `test_accepted_chapter_skip` | pipeline 遇到 accepted 章节 | 跳过，不重复执行 |

---

## 3. 执行流程

### 3.1 环境准备

**方式 A: 纯 Mock（推荐，快速）**

无需 LLM API Key，无需数据库初始化，直接运行 pytest：

```powershell
cd "c:\Vibe Project\Songyan"
pip install -e .[dev]
```

**方式 B: 半 Mock（使用真实 SQLite，Mock LLM）**

```powershell
# 初始化干净数据库
Remove-Item -Path "data/songyan_stress_test.db" -ErrorAction SilentlyContinue
$env:SONGYAN_DB_PATH="data/songyan_stress_test.db"
python -m songyan init-db
```

**方式 C: 实跑（成本最高，仅作为最终验收）**

```powershell
# 需要完整环境 + API Key
# 参考 122c 的环境准备步骤
cd "c:\Vibe Project\Songyan"
python -m songyan generate --chapters 1-150 --mode auto > logs/stress_150_$(Get-Date -Format 'yyyyMMdd_HHmmss').log 2>&1
```

### 3.2 Mock 策略详解

**核心原则**：用预设的 `ChapterContent` 和 `ReviewReport` 替代真实 LLM 调用，但保留完整的 pipeline 路由和状态机逻辑。

**Mock 层级**：

| 层级 | Mock 对象 | 保留的真实逻辑 |
|------|-----------|----------------|
| LLM 调用 | `Writer.write()`, `LLMAuditor.audit()`, `CreativeDirector.plan()`, `SummaryWriter.write()` | 全部 Mock |
| Pipeline 路由 | 不 Mock | `QualityGate.evaluate()`, `RevisionRouter.route()`, `AutoHalt.check()` |
| 状态管理 | 不 Mock | `ContextManager.assemble()`, `BudgetHardCeiling.check()` |
| 数据库 | 使用内存 SQLite 或文件 SQLite | 全部真实 |

**Mock 数据工厂示例**：

```python
def make_mock_chapter_content(chapter_number: int, text: str) -> ChapterContent:
    return ChapterContent(
        chapter_number=chapter_number,
        title=f"第{chapter_number}章",
        text=text,
        word_count=len(text),
    )

def make_mock_review_report(
    chapter_number: int,
    overall_score: float,
    quality_gate_pass: bool,
    context_emergency: bool = False,
) -> ReviewReport:
    return ReviewReport(
        chapter_version_id=f"v_{chapter_number}",
        overall_score=overall_score,
        quality_gate_pass=quality_gate_pass,
        context_emergency=context_emergency,
        # ... 其他字段按场景填充
    )
```

### 3.3 执行步骤

```powershell
# Step 1: 运行 122d 专属压力测试（Mock 模式，预计 30-60 秒）
python -m pytest tests/integration/test_122d_long_sequence_stability.py -v

# Step 2: 全量回归
python -m pytest tests/ -q

# Step 3: Lint
ruff check src/ tests/
```

---

## 4. 测试场景详细设计

### 4.1 `test_context_budget_150_chapters`

**输入**：150 章的 mock 内容，每章字数递增模拟上下文膨胀。
**模拟逻辑**：`budget_used = 0.5 + (chapter_number * 0.003)`（线性增长）。
**断言**：
- 所有章节的 `budget_used` < 1.0（不触发 ContextEmergency）
- 或若故意注入跳变：`budget_used` 从 0.8 跳到 1.3 的章节必须触发 ContextEmergency

### 4.2 `test_human_marks_decay_6_chapters`

**输入**：在第 10 章注入 3 条 `human_marks`（priority=high）。
**断言**：
- 第 10-15 章：`human_marks` 数量 > 0
- 第 16 章：`human_marks` 数量 = 0（已蒸发）

### 4.3 `test_auto_halt_false_positive`

**输入**：连续 3 章（Ch20, Ch21, Ch22）触发 ContextEmergency，但 QG pass。
**断言**：`AutoHalt.check()` 返回 `False`。

### 4.4 `test_auto_halt_true_positive`

**输入**：连续 3 章（Ch20, Ch21, Ch22）触发 ContextEmergency，且 QG fail。
**断言**：`AutoHalt.check()` 返回 `True`，pipeline 暂停。

### 4.5 `test_accepted_chapter_skip`

**输入**：Ch5 已被标记为 `accepted`，pipeline 再次遇到 Ch5。
**断言**：pipeline 跳过 Ch5，不重复生成、不重复审计。

---

## 5. 当前进度

- **状态**：已完成。
- **实现文件**：`tests/integration/test_122d_long_sequence_stability.py`
- **测试结果**：5 项压力测试全部通过；全量回归 `1784 passed, 1 xfailed, 2 warnings`；`ruff check src/ tests/` 通过。
- **关键实现要点**：
  - `test_context_budget_150_chapters`：构造 150 章递增摘要，验证 `budget_used` 平滑增长、无异常跳变、ContextEmergency 次数 ≤ 5。
  - `test_human_marks_decay_6_chapters`：验证 priority<8 的 human_marks 在 6 章窗口后自动 archive。
  - `test_auto_halt_false_positive` / `test_auto_halt_true_positive`：直接驱动 `_check_auto_halt_window`，验证连续 ContextEmergency 伴随/不伴随真实降级时的熔断行为。
  - `test_accepted_chapter_skip`：复用 `run_project_pipeline`，预先写入 Ch5 accepted 版本，验证 pipeline 跳过 accepted 章节且不生成新版本。

---

## 6. 交付标准

- [x] 5 项压力测试全部通过（Mock 模式，< 60 秒）
- [x] pytest 全量通过（1784 passed，零回归）
- [x] ruff 通过
- [x] 150 章实跑一次性通过已由 Task 121q `run-a2bed648` 完成（150/150）
- [x] 测试文档完整（每个测试附带输入/断言/ Mock 策略说明）

---

## 7. 风险与缓解

| 风险 | 影响 | 缓解 |
|------|------|------|
| 150 章 Mock 数据构造复杂 | 测试代码冗长 | 使用工厂函数 + 参数化测试（`@pytest.mark.parametrize`） |
| 状态机逻辑变更导致测试失效 | 维护成本 | 将压力测试与具体状态机实现解耦，聚焦输入输出契约 |
| 实跑 150 章成本过高 | 时间和费用 | 实跑仅作为最终验收，日常开发用 Mock 模式 |

---

## 8. 相关文档

- 主文档：[122-v51-systematic-test-matrix.md](122-v51-systematic-test-matrix.md)
- 上下文管理实现：`src/songyan/context/`
- AutoHalt 策略：[tasks/121l-context-emergency-autohalt-review.md](121l-context-emergency-autohalt-review.md)
- 全量实跑记录：[tasks/121q-ch1-ch150-full-single-run-DONE.md](121q-ch1-ch150-full-single-run-DONE.md)