# Task 023: 多章编排层

> **Phase**: Phase 2（编排层扩展）
> **优先级**: P1（V1.1 核心功能）
> **依赖**: Task 019（单章 LangGraph 编排已完成）、Task 022（多题材验证通过）
> **预计工作量**: 大

---

## Goal

在现有单章闭环（Phase1Graph）之上，构建多章编排层，实现「给定项目 + 章节范围 → 自动按序生成多章」的能力，支持跨章状态传递。

## Context

当前系统每次只能生成一章。用户需要手动调用 `run_chapter_pipeline()`，然后从数据库取出上一章 summary 再传给下一章。真正的长篇创作需要自动化的多章流水线：第 N 章的 settlement 和 summary 自动成为第 N+1 章的输入。

## In Scope（必须完成）

- [ ] **跨章状态传递**：SettlementExtractor 输出自动组装为下一章的 `previous_summary`
- [ ] **多章编排图**：新建 `Phase2Graph`（或外层循环），按 `chapter_number` 顺序调度单章流水线
- [ ] **项目级状态跟踪**：新增 `ProjectRunState` 模型，记录项目级运行状态（当前章节、已完成章节列表、累计 metrics）
- [ ] **批量/自动模式**：支持配置 `auto_confirm=True`（无需每章 interrupt）或保留逐章人工确认
- [ ] **失败回滚**：某章失败时可选择重试、跳过或终止整批
- [ ] **测试**：Mock 环境跑通 3 章连续生成

## Out of Scope（明确不做）

- Web UI / 可视化编排界面
- 多项目并行调度
- 分布式执行
- 实时协作编辑

## 接口契约

```python
async def run_project_pipeline(
    project_id: str,
    chapter_range: tuple[int, int],  # (start, end)，如 (1, 3)
    mode_id: str,
    *,
    auto_confirm: bool = False,
    max_revision_rounds: int = 2,
) -> ProjectRunResult:
    """运行多章流水线，逐章调用 Phase1Graph，自动传递上下文."""
    ...

class ProjectRunResult(BaseModel):
    project_id: str
    chapters_completed: list[int]
    chapters_failed: list[int]
    total_cost: float
    total_duration_sec: float
    final_status: str  # "completed" | "partial" | "failed"
```

## 数据模型

```python
class ProjectRunState(BaseModel):
    """项目级运行状态（新增表 project_runs）."""
    run_id: str
    project_id: str
    chapter_range_start: int
    chapter_range_end: int
    current_chapter: int
    completed_chapters: list[int]
    failed_chapters: list[int]
    accumulated_summary: str  # 拼接所有已完成章节的 summary
    total_cost: float
    status: str  # "running" | "paused" | "completed" | "failed"
    created_at: datetime
    updated_at: datetime
```

## 测试要求

### Layer 1: 模型测试
- [ ] `ProjectRunState` 可正确实例化和序列化
- [ ] 边界条件：空 chapter_range、start > end

### Layer 2: 模块测试
- [ ] `run_project_pipeline` Mock 测试：3 章连续成功
- [ ] 中间章失败后的回滚/跳过逻辑
- [ ] `accumulated_summary` 正确拼接

### Layer 3: 集成测试
- [ ] Mock 环境跑通 `chapter 1 → chapter 2 → chapter 3` 完整链路
- [ ] 验证 chapter 2 的 `previous_summary` 包含 chapter 1 的关键剧情

## 验收标准（Acceptance Criteria）

- [ ] `pytest tests/integration/test_multi_chapter.py -v` 全部通过
- [ ] 代码符合 CLAUDE.md 规范
- [ ] 不违反任何不可违背规则
- [ ] 更新了 `docs/STATUS.md`
- [ ] 更新了 `docs/architecture/` 相关设计文档
- [ ] 生成了 `tasks/023-multi-chapter-orchestration-DONE.md` 交接文件

## 参考文档

- `src/songyan/workflows/phase1_graph.py` — 现有单章编排
- `system_prompt/development-tech-plan-v2.md` — V2 技术方案中多章相关章节
- `docs/architecture/` — 架构设计文档
