# Task 058b: 30 章封闭验证执行

> **Phase**: V3.0 Layer 2 — 核心验证层
> **优先级**: P0
> **依赖**: Task 058a（监控与韧性基础设施）
> **预计工作量**: 大（取决于 API 速度，~2-5 小时生成等待 + 0.5 天分析准备）

---

## Goal

在全自动 `auto_confirm=True` 模式下，实际运行生成 30 章，验证 058a 基础设施在真实 LLM 调用场景下的稳定性，并产出完整的运行日志与章节文本。

---

## Context

058a 已完成监控基础设施（`ChapterRunLog` + `_run_logger` + 失败处理增强），现在需要**在真实 API 调用下验证**这些机制是否有效。

这是 V3.0 最核心的实验。前面的所有 Layer 0/1/058a 工作都是为它做准备。成功意味着：Songyan 的工程底座已被证明可以支撑长篇小说连续生成。

**当前基线**：
- `projects/orbital_horror_v2/` 有 Ch1~Ch9 的文本文件，但**未在主数据库注册**
- 主数据库（`songyan.db`）中无任何 scifi 项目
- API 已配置（DeepSeek `deepseek-chat`）
- 监控基础设施就绪（JSONL 日志写入 `logs/chapter_runs/`）

---

## In Scope（必须完成）

### 1. 运行前准备
- [ ] **项目初始化**：在主数据库创建 scifi 项目（`genre_id=scifi`, `mode_id=webnovel`）
  - 使用 `evals/seeds/scifi_new_weird.json` 作为 seed
  - 通过 `evals.runner.import_seed_project()` 导入
- [ ] **种子章节导入**：将 `evals/seeds/chapters/scifi_new_weird_ch1.md` 作为 Ch1 导入
  - 通过 `evals.runner.import_seed_chapter()` 导入
  - 确保 Ch1 的 `version_type="accepted"`， settlement 和 summary 完整
- [ ] **运行方式决策**：
  - 方案 A：使用 `scripts/run_batched_chapters.py`（每章独立进程，独立 test.db，有 progress.json）
  - 方案 B：直接调用 `phase2_graph.run_project_pipeline(project_id, chapter_range=(2, 30), auto_confirm=True)`（写入主 songyan.db，JSONL 日志自动采集）
  - **推荐方案 B**：因为 058a 的监控基础设施已集成到 `phase2_graph.py` 中

### 2. 实际运行
- [ ] **执行生成**：`chapter_range=(2, 30)`，即从 Ch2 生成到 Ch30（Ch1 为 seed）
  - `auto_confirm=True`
  - `on_failure="retry"`
  - `continuity_health_threshold=7.0`
- [ ] **运行时监控**：
  - 观察 `logs/chapter_runs/{run_id}.jsonl` 是否正确追加
  - 观察每章的 `duration_sec`、`word_count`、`revision_rounds`
  - 检查是否有 `settlement_needs_human_review` 标记
  - 检查是否有 `content_preservation_ratio < 0.5` 的截断回退

### 3. 失败处理验证
- [ ] **database locked**：观察 053 的 WAL + 指数退避是否在真实场景有效
- [ ] **LLM 超时/错误**：观察重试后是否能恢复
- [ ] **RevisionHandler 截断**：观察是否有截断回退日志（`revision_handler.truncated_skip`）
- [ ] **Settlement 部分失败**：观察是否有 `settlement_needs_human_review` 标记但流程不中断

### 4. 结果收集
- [ ] **JSONL 日志归档**：将 `logs/chapter_runs/{run_id}.jsonl` 复制到 `docs/review/v30_layer2_runlog.jsonl`
- [ ] **章节文本导出**：将数据库中 accepted 版本导出为 Markdown（参考 `scripts/run_batched_chapters.py` 的 `_export_chapter_markdown`）
- [ ] **项目索引生成**：生成 `README.md` 列出所有章节
- [ ] **连续性报告**：每 3 章的 `ContinuityAuditor` 结果整理

### 5. 基线数据记录
- [ ] **总耗时**：30 章平均耗时/章
- [ ] **总成本**：LLM 调用次数 × 预估费用
- [ ] **失败率**：失败章节数 / 30
- [ ] **平均 revision 轮数**
- [ ] **content_preservation_ratio 分布**
- [ ] **continuity_health_score 趋势**

---

## Out of Scope（明确不做）

- 不做 Prompt 优化（字数控制、钩子质量提升属于 V3.1）
- 不做人工盲测或质量评分
- 不做多 genre 交叉验证
- 不修复 058b 运行中发现的问题（归入 Task 058c）
- 不修改任何 Agent 代码（除非发现阻塞性 bug）

---

## 接口契约

```python
# 主入口 — 直接调用已有 API
from songyan.workflows.phase2_graph import run_project_pipeline

result = await run_project_pipeline(
    project_id=project_id,           # seed 导入后获得
    chapter_range=(2, 30),           # Ch1 为 seed，从 Ch2 生成
    mode_id="webnovel",
    auto_confirm=True,
    on_failure="retry",
    continuity_health_threshold=7.0,
)
# result: ProjectRunResult
#   - chapters_completed: list[int]
#   - chapters_failed: list[int]
#   - total_duration_sec: float
#   - final_status: "completed" | "partial" | "failed"
```

---

## 数据模型

本 Task 不新增模型，复用 058a 的 `ChapterRunLog`：

```python
class ChapterRunLog(BaseModel):
    log_id: str
    run_id: str | None
    project_id: str
    chapter_number: int
    started_at: datetime
    finished_at: datetime
    success: bool
    error: str | None
    error_stage: str | None
    word_count: int
    rule_violations: int
    rule_audit_score: float
    llm_audit_issues: int
    llm_audit_critical: int
    revision_rounds: int
    content_preservation_ratio: float | None
    continuity_health_score: float | None
    settlement_success: bool
    settlement_needs_human_review: bool
    duration_sec: float
```

---

## 运行脚本（可选增强）

如果直接调用 `run_project_pipeline` 不方便监控，可以写一个轻量包装脚本：

```python
# scripts/run_30ch_validation.py
import asyncio
from songyan.workflows.phase2_graph import run_project_pipeline

async def main():
    project_id = "..."  # seed 导入后获得
    result = await run_project_pipeline(
        project_id=project_id,
        chapter_range=(2, 30),
        auto_confirm=True,
        on_failure="retry",
    )
    print(f"Status: {result.final_status}")
    print(f"Completed: {result.chapters_completed}")
    print(f"Failed: {result.chapters_failed}")
    print(f"Duration: {result.total_duration_sec / 60:.1f} min")

if __name__ == "__main__":
    asyncio.run(main())
```

---

## 测试要求

058b 是**运行任务**而非开发任务，测试要求与常规 Task 不同：

- [ ] **运行前检查**：`pytest tests/ --ignore=tests/integration -q` 基线通过（≥1025 passed）
- [ ] **Mock 预演**：用 mock LLM 跑 3 章，验证 `run_project_pipeline` 调用链路正常
- [ ] **日志格式验证**：运行后验证 JSONL 每行均可正确解析为 `ChapterRunLog`

---

## 验收标准

- [ ] 30 章全部生成完成，无不可恢复的崩溃（允许 retry 后恢复）
- [ ] 每章 settlement 写入完整性 = 100%（允许 `needs_human_review` 标记）
- [ ] Content preservation ratio 全程 >= 0.5（058a 截断回退机制生效）
- [ ] 生成速度无指数衰减（30 章平均耗时 <= 5 分钟/章）
- [ ] 运行日志完整归档至 `docs/review/v30_layer2_runlog.jsonl`
- [ ] `docs/STATUS.md` 更新（实际运行数据填入）
- [ ] 生成 `tasks/058b-30ch-execution-DONE.md`

### 关键阈值

| 指标 | 最低接受 | 理想 |
|------|---------|------|
| 完成率 | 100% (30/30) | 100% |
| 连续性健康分 | >= 6.0 | >= 8.0 |
| 平均耗时/章 | <= 5 min | <= 3 min |
| content_preservation_ratio | >= 0.5 | >= 0.7 |
| settlement 成功率 | >= 90% | 100% |

---

## 参考文档

- `tasks/058-30ch-generation.md` — 父 Task 规格
- `tasks/058a-monitoring-infrastructure-DONE.md` — 058a 交接报告
- `scripts/run_batched_chapters.py` — 现有分批运行脚本（参考用）
- `evals/runner.py` — seed 导入函数
- `src/songyan/workflows/phase2_graph.py` — 多章编排层
- `src/songyan/workflows/_run_logger.py` — 监控日志服务
