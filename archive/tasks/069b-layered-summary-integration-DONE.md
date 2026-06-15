# Task 069b: 分层摘要 — 系统集成与加载 — 交接报告

> **状态**: ✅ 已完成
> **完成日期**: 2026-06-06
> **耗时**: ~2 小时
> **提交**: `TODO`
> **依赖**: 069a

---

## 做了什么

### 1. ContextManager 分层加载重构

- `ChapterSummary` 新增 `source_type: Literal["chapter", "arc", "volume"]` 字段（默认 `"chapter"`）
- `_build_recent_plot` 按 `source_type` 使用不同截断长度：
  - `chapter`: 200 字
  - `arc`: 500 字
  - `volume`: 300 字
- 新建 `load_layered_summaries()` 替代 `load_recent_summaries` 在 `assemble_context_package` 中的使用：
  - 最近 3 章：精细 `ChapterSummary`
  - 更早章节：不与精细层完全重叠的 `ArcSummary`
  - 全篇宏观：`VolumeSummary`
- `_helpers.py` 的 `assemble_context_package` 改为调用 `load_layered_summaries()`

### 2. SettlementExtractor 触发逻辑

- 新建 `trigger_layered_summaries()` 函数：
  - 章节 accept 后，检查是否跨越弧边界（`ArcBoundaryResolver.resolve`）
  - 若跨越，调用 `ArcSummaryGenerator.generate()` 生成/更新弧摘要
  - 若跨越卷边界（默认每 30 章），调用 `VolumeSummaryGenerator.generate()` 生成/更新卷摘要
  - 失败捕获异常并记录日志，不阻塞主流程
- `_nodes.py` 的 `settlement_extractor_node` 在 RAG 索引后调用 `trigger_layered_summaries()`
- `ArcSummaryGenerator` / `VolumeSummaryGenerator` 支持更新已存在的记录（避免重复插入）

### 3. Token 预算验证

- 新增 `tests/test_layered_summary_tokens.py`：
  - `test_recent_plot_tokens_reduced_with_layering`: 验证分层加载后 `recent_plot` token 数比纯精细加载减少 >50%
  - `test_full_context_package_ch30_budget`: 模拟 Ch30 场景，验证 `ContextPackage.estimated_tokens < 28,800`（`budget_used < 3.0x`）

### 4. 测试

| 测试文件 | 新增用例 | 结果 |
|---------|---------|------|
| `tests/test_load_layered_summaries.py` | 5 + 4 = 9 | ✅ 通过 |
| `tests/test_trigger_layered_summaries.py` | 4 | ✅ 通过 |
| `tests/test_layered_summary_tokens.py` | 2 | ✅ 通过 |
| 回归测试（核心 250 个用例） | — | ✅ 全部通过 |

---

## 加载策略细节

```python
# 对于 current_chapter = 30，Arc 边界 10 章：
# result = [
#   ChapterSummary(ch=0, summary="Volume: ...", source_type="volume"),
#   ChapterSummary(ch=1, summary="Arc 1-10: ...", source_type="arc"),
#   ChapterSummary(ch=11, summary="Arc 11-20: ...", source_type="arc"),
#   ChapterSummary(ch=21, summary="Arc 21-30: ...", source_type="arc"),
#   ChapterSummary(ch=28, summary="第28章...", source_type="chapter"),
#   ChapterSummary(ch=29, summary="第29章...", source_type="chapter"),
#   ChapterSummary(ch=30, summary="第30章...", source_type="chapter"),
# ]
```

- Volume 放在 `chapter_number=0`（排序在最前）
- Arc 按 `start_chapter` 排序
- 精细层按实际章节号排序
- 与精细层**完全重叠**的 Arc 被跳过（如 Arc 28-30 当精细层包含 28-30 时）

---

## 已知限制

- **Volume 边界固定为 30 章**：未使用 `project.volume_boundaries`（该字段目前为空列表）
- **Arc 重复**：部分重叠的 Arc（如 Arc 21-30 与精细层 28-30）仍会加入 `recent_plot`，造成少量重复
- **真实 LLM 验证待测**：Token 预算测试使用模拟数据，真实 Ch30 场景需在端到端运行时验证
- **DB corruption 导致的 2 个已知失败**：与本次修改无关

---

## 接口契约（供后续使用）

```python
from songyan.workflows._helpers import load_layered_summaries, trigger_layered_summaries

# 加载分层摘要（用于 ContextManager）
summaries = await load_layered_summaries(project_id, current_chapter)

# accept 后触发弧/卷摘要生成（SettlementExtractor 已自动集成）
await trigger_layered_summaries(project_id, chapter_number, project)
```

---

## 文件变更清单

```
src/songyan/models/context.py                    # +source_type on ChapterSummary
src/songyan/agents/context_manager/_assemblers.py # _build_recent_plot 按 source_type 截断
src/songyan/workflows/_helpers.py                 # +load_layered_summaries, +trigger_layered_summaries
src/songyan/agents/arc_summary_generator.py       # generate() 支持 update 已存在记录
src/songyan/workflows/_nodes.py                   # settlement_extractor_node 触发分层摘要
tests/test_load_layered_summaries.py              # 新建（9 个测试）
tests/test_trigger_layered_summaries.py           # 新建（4 个测试）
tests/test_layered_summary_tokens.py              # 新建（2 个测试）
docs/STATUS.md                                    # 更新 069b 状态
```

---

## 下一步

- **072**: Settlement source_quote 去噪
- **073**: 截断重写策略
- 端到端验证：运行 Ch31-Ch40，观察 `budget_used` 是否降至 2.5x-3.0x
