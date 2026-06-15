# Task 069b: 分层摘要 — 系统集成与加载

> **Phase**: V3.1 — 质量跃迁
> **优先级**: P1
> **依赖**: 069a（生成器必须可用）
> **预计工作量**: ~1 天（6-8 小时）

---

## Goal

将 069a 的摘要生成器接入 ContextManager 和 SettlementExtractor，实现真正的分层加载：最近 3 章精细摘要 + 更早弧级摘要 + 最远全篇摘要，将 Ch30 的 `budget_used` 从 4.29x 降至 2.5x-3.0x。

## Context

069a 完成后，我们将拥有：
- `ArcSummaryGenerator`：能生成弧级摘要并写入 DB
- `VolumeSummaryGenerator`：能生成全篇摘要并写入 DB
- `ArcBoundaryResolver`：能确定章节所属弧边界

当前 `ContextManager` 的加载逻辑：
- `recent_plot` 加载最近 N 章的完整摘要（每章 200-400 字）
- 30 章时累计加载 6,000-12,000 字的摘要文本
- `arc_context` / `volume_context` 已传入 `ContextPackage`，但 `_helpers.py` 中只加载了当前章所在的 arc/volume（且 DB 中无数据时返回 None）

## In Scope（必须完成）

### 1. ContextManager 分层加载重构

- [ ] 修改 `ContextManager._load_recent_summaries()` 为 `load_layered_summaries()`：
  - **最近 3 章**：从 `summaries` 表加载精细 `ChapterSummary`
  - **第 4-15 章**：加载覆盖该范围的 `ArcSummary`（通过 `ArcSummaryRepository.list_by_project`）
  - **第 16 章+**：加载 `VolumeSummary`（通过 `VolumeSummaryRepository.get_current_volume`）
- [ ] 修改 `workflows/_helpers.py` 中的 `assemble_context_package`：传入分层加载后的摘要列表
- [ ] `ContextPackage.recent_plot` 的组装逻辑适配：支持混合 `ChapterSummary` + `ArcSummary` + `VolumeSummary`

### 2. SettlementExtractor 触发逻辑

- [ ] 在 `SettlementExtractor` 的 `extract_settlement()` 或 `apply_settlement()` 中：
  - 章节 accept 后，检查是否跨越弧边界（`end_chapter == current_chapter`）
  - 若跨越，调用 `ArcSummaryGenerator.generate()` 生成/更新弧级摘要
  - 若跨越卷边界，调用 `VolumeSummaryGenerator.generate()` 生成/更新全篇摘要
- [ ] 触发逻辑异步执行，失败不阻塞主流程（记录日志）

### 3. Token 预算验证

- [ ] 新增集成测试：模拟 Ch30 场景，验证 `ContextPackage.estimated_tokens < 28,800`（3.0x budget）
- [ ] 如超标，调整加载策略（如减少精细摘要章数、压缩弧级摘要长度）

### 4. 测试

- [ ] 分层加载单元测试：不同 chapter_number 返回正确的摘要组合
- [ ] Settlement 触发测试：Mock 生成器，验证跨越边界时正确触发
- [ ] 集成测试：`pytest tests/test_phase1_graph.py` + `pytest tests/test_phase2_graph.py` 通过
- [ ] 回归测试：`pytest tests/ -x -q` 通过

## Out of Scope（明确不做）

- 实时摘要更新（只在 accept 后触发）
- 多弧并行生成
- 摘要质量评估（V3.2）
- 跨项目摘要复用

## 加载策略

```python
def load_layered_summaries(
    project_id: str,
    current_chapter: int,
) -> list[RecentPlotSummary]:
    """分层加载摘要.
    
    策略：
    - 最近 3 章：章级摘要（精细）
    - 第 4-15 章：弧级摘要（中等，~500字/弧）
    - 第 16 章+：全篇摘要（压缩，~300字）
    """
```

## 验收标准

- [ ] 分层加载后，Ch30 的 context tokens < 28,800（3.0x budget）
- [ ] Settlement 触发后弧级摘要正确生成
- [ ] `pytest tests/ -x -q` 全部通过
- [ ] `docs/STATUS.md` 更新
- [ ] 生成 `tasks/069b-layered-summary-integration-DONE.md`

## 参考

- `src/songyan/agents/context_manager/__init__.py` — ContextManager
- `src/songyan/agents/settlement_extractor/__init__.py` — SettlementExtractor
- `src/songyan/workflows/_helpers.py` — `assemble_context_package`
- `tasks/069a-layered-summary-generators.md` — 上游依赖
