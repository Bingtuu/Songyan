# Task 023: 多章编排层 — DONE

**目标**: 在单章闭环（Phase1Graph）之上构建多章编排层，实现「项目 + 章节范围 → 自动按序生成多章」，支持跨章状态传递。

**完成日期**: 2026-05-30

**方案**: 简单外层循环（非 LangGraph），`run_project_pipeline` 作为纯 Python 协调器，for 循环逐章调用 `run_chapter_pipeline`。

---

## 1. 核心实现

### 1.1 新增数据模型

- `ProjectRunState` — 项目级运行状态（`src/songyan/models/project_run.py`）
- `ProjectRunResult` — 运行结果（`src/songyan/models/project_run.py`）

### 1.2 DB 层

- `project_runs` 表（第 14 张表）— 追踪多章流水线进度
- `ProjectRunRepository` — CRUD + 按项目查询

### 1.3 跨章状态传递

- `Phase1State` 新增 `previous_summary` 字段
- `run_chapter_pipeline` 增加 `previous_summary: str = ""` 参数
- `goal_planner_node` 将 `previous_summary` 注入 GoalPlanner
- **修复**: `define_chapter_goal` 中覆盖 `goal.previous_summary = previous_summary`（原代码只从 LLM 响应解析，Mock 测试中 LLM 不返回此字段）

### 1.4 Phase2 编排 (`phase2_graph.py`)

核心函数 `run_project_pipeline`：

```python
async def run_project_pipeline(
    project_id: str,
    chapter_range: tuple[int, int],
    mode_id: str = "webnovel",
    *,
    auto_confirm: bool = False,
    max_revision_rounds: int = 2,
    on_failure: str = "abort",  # "abort" | "retry"
) -> ProjectRunResult
```

**流程**:
1. 参数校验（start ≤ end，start ≥ 1，auto_confirm 必须为 True）
2. 创建 `ProjectRunState`（status="running"）
3. For 每章:
   a. 从 `summaries` 表读取上一章 `plot_summary` 作为 `previous_summary`
   b. 调用 `run_chapter_pipeline`
   c. 处理 `__interrupt__`（auto_confirm=True 时自动 resume "accept"）
   d. 失败处理："retry" 重试 1 次，"abort" 终止整批
4. 更新最终状态并返回 `ProjectRunResult`

**设计决策**:
- `auto_confirm=False` 时抛出 `ValueError`（批量模式不支持人工中断）
- 每章使用独立 `thread_id`（避免 checkpoint 冲突）
- `total_cost` 暂为 0.0（TODO: Task 025 接入精确成本追踪）

---

## 2. 测试覆盖

### Layer 1: 模型测试 (`tests/models/test_project_run.py`)
- `test_instantiation_defaults` — 默认字段
- `test_full_instantiation` — 完整字段

### Layer 2: 模块测试 (`tests/test_phase2_graph.py`, 8 个测试)
- `test_run_project_pipeline_3_chapters_success`
- `test_run_project_pipeline_previous_summary_propagation` — 验证跨章传递
- `test_run_project_pipeline_chapter_failure_abort`
- `test_run_project_pipeline_chapter_failure_retry_then_success`
- `test_run_project_pipeline_auto_confirm_handles_interrupt`
- `test_run_project_pipeline_invalid_range_start_gt_end`
- `test_run_project_pipeline_invalid_range_start_lt_1`
- `test_run_project_pipeline_auto_confirm_false_rejected`

### Layer 3: 集成测试 (`tests/integration/test_multi_chapter.py`, 3 个测试)
- `test_multi_chapter_3_success` — 3 章完整链路，验证 DB 状态
- `test_multi_chapter_previous_summary_in_goal` — 验证 chapter 2 的 goal 包含 chapter 1 summary
- `test_multi_chapter_accumulated_summary` — 验证结果拼接

---

## 3. 测试运行结果

```
pytest tests/ -x
# 698 passed in ~34s
```

新增测试: 17 个（模型 2 + 模块 8 + 集成 3 + 回归修复 4）

## 4. 真实 LLM 验证

**验证时间**: 2026-05-30
**种子**: 玄幻 (`xuanhuan_webnovel.json`)
**范围**: Chapter 2（从种子 Chapter 1 继续）
**成本**: ~¥0.11（13 LLM calls）
**耗时**: ~206s

### 验证结果

| 检查项 | 结果 | 说明 |
|--------|------|------|
| Pipeline 完成 | ✅ | `final_status=completed`, `completed=[2]` |
| 跨章传递 | ✅ | Ch2 `previous_summary` 与 Ch1 summary 重叠词数=6 |
| project_runs 记录 | ✅ | 状态正确持久化 |
| Settlement 外键 | ⚠️→✅ | LLM hallucinate 角色 `lu_chen` 不在项目中，已修复跳过 |
| Revision 反弹 | ✅ | 正确检测并回滚到最佳版本 |

### 发现的问题与修复

1. **SettlementExtractor 外键约束失败**：LLM 提取了不存在的角色（`zhao_tianheng`、`lu_chen`）的 character_update，导致 `FOREIGN KEY constraint failed`
   - **修复**: `apply_settlement` 预加载项目角色白名单，跳过不存在角色
2. **chapter_goals 双写**：`define_chapter_goal` 内部和 `goal_planner_node` 各保存一次（每章 2 条记录）
   - 不影响功能，已记录为已知限制

## 5. Code Review

| 项 | 发现 | 修复 |
|----|------|------|
| max_revision_rounds | 参数未透传给 Phase1Graph | 添加 TODO 注释，待 Phase1Graph 支持外部配置后透传 |
| updated_at | `ProjectRunRepository.update()` 不刷新时间戳 | 自动更新 `updated_at = datetime.now()` |
| retry 日志 | `unexpected_status` 时无日志 | 添加 `chapter_retry_unexpected_status` 日志 |

## 6. 文件变更清单

---

## 4. 文件变更清单

| 文件 | 变更 |
|------|------|
| `src/songyan/models/project_run.py` | 新增 ProjectRunState, ProjectRunResult |
| `src/songyan/models/__init__.py` | 导出新模型 |
| `src/songyan/db/schema.sql` | 新增 project_runs 表 |
| `src/songyan/db/migrations.py` | _EXPECTED_TABLES 增加 project_runs |
| `src/songyan/db/project_run_repo.py` | 新增 ProjectRunRepository |
| `src/songyan/workflows/phase1_graph.py` | Phase1State + previous_summary + thread_id 返回 |
| `src/songyan/workflows/_nodes.py` | goal_planner_node 传入 previous_summary |
| `src/songyan/workflows/phase2_graph.py` | 新增 run_project_pipeline 协调器 |
| `src/songyan/workflows/__init__.py` | 导出 run_project_pipeline |
| `src/songyan/agents/goal_planner.py` | 修复 previous_summary 注入 |
| `tests/models/test_project_run.py` | 新增 |
| `tests/test_phase2_graph.py` | 新增 |
| `tests/integration/test_multi_chapter.py` | 新增 |
| `tests/db/test_schema.py` | 修复硬编码表数 |
| `tests/test_prompt_loader.py` | 修复版本号断言 |

---

## 7. 已知限制 / 待 Task 025 处理

1. **total_cost 为 0.0**: 未接入精确 LLM 调用成本追踪
2. **chapter_goals 双写**: `define_chapter_goal` 内部和 `goal_planner_node` 各保存一次 goal，每章产生 2 条记录（不影响功能，但可优化）
3. **auto_confirm=False 不支持**: 批量模式下不支持逐章人工确认（未来可通过 paused 状态 + 外部 resume 实现）
4. **on_failure="skip" 未实现**: 跳过失败章节的策略未支持（会影响后续章节的 previous_summary 连贯性）
