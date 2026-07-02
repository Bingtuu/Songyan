# Task 153: run 级断点续跑

> **Phase**: V6 阶段 C（工程加固）
> **优先级**: P0（阶段 C 出口"中途人为 kill 后可 run 级 resume 续完"的直接实现；阶段 D 长跑的前置底盘）
> **依赖**: 阶段 0/A/B 已落地（不改治理逻辑）；复用现有 `project_runs` 表与 `ProjectRunRepository`
> **预计工作量**: 中（拆 153a resume 点推导与 CLI 入口 + 153b in-flight 状态恢复与孤儿清理）
> **事实入口**: `tasks/V6-README.md`；规划：`docs/v6-plan.md` §3 阶段 C

---

## Goal

让一条无人值守长跑在中途被人为 kill（或崩溃）后，**用同一命令真正 resume**：已 `accepted` 的章节跳过、in-flight（生成到一半未 accept）的章节正确恢复而非从头重算整批，孤儿 checkpoint 被清理。目标是把"崩溃 = 整批白跑"变成"崩溃 = 从断点续完"，为阶段 D 的 Ch1-Ch100 长跑（§1.3-R）提供底盘。

## Context

设计核实（2026-07-02，创建前对主干代码核对）：

- **run 执行入口**：`run_project_pipeline(project_id, chapter_range, ...)`（`src/songyan/workflows/phase2_graph.py:294`），主循环 `for chapter_number in range(start, end + 1)`（`phase2_graph.py:389`），逐章调用 `_run_single_chapter`（`phase2_graph.py:412`）。CLI 入口 `songyan run`（`src/songyan/cli/main.py:435`，选项定义 `main.py:419-434`）解析 `--chapters "1-10"` 后调用 pipeline（`main.py:471`）。
- **run 进度已持久化（关键前置已存在，非从零）**：
  - 表 `project_runs`（`src/songyan/db/schema.sql:353-366`）已有 `run_id` / `current_chapter` / `completed_chapters` / `failed_chapters` / `accumulated_summary` / `status`（`running | paused | completed | failed`，见 `models/project_run.py:22`）。
  - 仓储 `ProjectRunRepository`（`src/songyan/db/project_run_repo.py`）有 `create` / `get` / `update` / `list_by_project`（**注意：当前 `list_by_project` 无 `limit` 参数**，归档脚本 `archive/v5/scripts/run_task_105b_ch51_ch100.py:86` 的 `_find_resume_point` 曾用 `limit=` 调用，是过时签名，不可照抄）。
  - 进度**逐章持久化**：每章成功/失败后调用 `_persist_run_progress(...)`（`phase2_graph.py:461` / `:477`），`run_state.current_chapter` 每章更新（`phase2_graph.py:398-399`）。
- **已有"跳过 accepted 章"能力（Bug A 修复）**：`phase2_graph.py:376-397` 读 `ChapterHeadRepository().list_by_project()`，`accepted_chapters = {h.chapter_number for h in all_heads if h.status == "accepted"}`（`:379-381`），循环内 `if chapter_number in accepted_chapters: completed.append(...); continue`（`:390-397`）。**但跳过键只认 head `status == "accepted"`**——`chapter_heads.status` 取值为 `draft | under_review | accepted`（`models/chapter.py:60`），accept 节点在事务里写 `status="accepted"`（`_nodes.py` 约 L2202），其余路径写 `draft`。
- **LangGraph checkpoint 只作单章内恢复，非 run 级**：`src/songyan/workflows/checkpointer.py` 按 `settings.checkpointer_mode` 返回 `MemorySaver` / `AsyncSqliteSaver`（`:33-48`）；`thread_id` 每章 `new_id("thread")`（`phase2_graph.py` 约 L605），`interrupt`/`Command(resume=...)` 仅用于 `human_confirm` gate。run 开始会 `reset_checkpointer()`（`phase2_graph.py:374`）清缓存，但**从不删除/清理旧 checkpoint 行**。
- **崩溃后现状**：每次 `songyan run` 都 `run_id = new_id("run")`（`phase2_graph.py:338`）新建 run，**无 `--resume` / 无 run_id 复用**。硬 kill 会把 `project_runs` 行留在 `status="running"`（`_pause_run_for_auto_halt` 只在软暂停时写 `paused`，`phase2_graph.py:127`）。唯一的隐式续跑是"重跑同区间自动跳过 accepted 章"（依赖上一条），但**从不读 `project_runs.completed_chapters` 推导 resume 点**。
- **无孤儿 checkpoint 清理**：`reset_checkpointer_instance()`（`checkpointer.py:54`）只关连接、丢单例，不 prune checkpoint 行；无 stuck-at-`running` 的 `project_runs` 清扫。

**为什么"跳过 accepted"不等于"run 级续跑"**：现状能跳过已 accept 章，但 (a) 不认 in-flight（生成到一半、有 draft/version 但未 accept）章节，会整章从头重算，浪费；(b) 无从 `project_runs` 断点恢复 `accumulated_summary` 的路径，续跑的上下文可能断裂；(c) stuck-at-`running` 行与孤儿 checkpoint 会累积。本 Task 把隐式跳过升级为**显式、可解释的 run 级 resume**。

## Cross-Task Coordination（阶段 C 统一口径）

> 阶段 C（153-156）都在 run 编排层（`phase2_graph.py` / `cli/main.py`）改动，彼此有接触面，统一口径如下，避免 4 个 Task 各改一处产生冲突。

- **章节状态权威口径**：`chapter_heads.status ∈ {draft, under_review, accepted}`（`models/chapter.py:60`）。"已完成可跳过" = head `status == "accepted"`。`degraded_accept` / `human_review_required` 是 graph **state** 标记（`_nodes.py`），**不是** head status，不作为跳过键（避免把降级/待人工复核章误判为已完成）。
- **`project_runs.status` 语义**：`running`（进行中，含被硬 kill 的 stuck 行）/ `paused`（AutoHalt 或候选硬门禁软暂停）/ `completed` / `failed`。Task 155（失败隔离）产出的 `partial` 是 `ProjectRunResult.final_status`（`models/project_run.py:36`），**与 `project_runs.status` 不同字段**，勿混。
- **resume 与 155 的边界**：153 负责"崩溃/kill 后从断点续"；155 负责"单章失败后隔离继续"。二者可叠加（隔离模式下的失败章在下次 resume 时按策略决定是否重试），但**本 Task 不改 `on_failure` 分支逻辑**，只保证 resume 点推导正确读取 `completed`/`failed`。
- **resume 不弱化 AutoHalt**：resume 后仍走 `_check_auto_halt_window`（`phase2_graph.py:484`/`:520`）；被 AutoHalt 判为 `paused` 的 run，resume 应打印明确提示（"上次因质量熔断暂停"），由用户决定是否续跑，不静默跳过质量门禁。

### resume 点推导口径（权威定义）

给定 `--resume`（或 `--run-id <id>`），resume 起点按以下优先级确定，**以 head `accepted` 为唯一"已完成"事实源**，`project_runs` 仅作断点/摘要辅助：

1. 读该 run 或该项目最近一条 `project_runs` 行；若 `status == "completed"` → 无事可做，提示并退出。
2. 已完成集合 = `{h.chapter_number | h.status == "accepted"}`（复用现有 skip-set 口径），**不信任仅 `project_runs.completed_chapters`**（后者可能领先于真正落库的 accepted head，硬 kill 时刻有差）。
3. resume 起点 = 原始 `chapter_range` 内第一个不在已完成集合的章号；其后的章正常执行、已 accept 章继续跳过。
4. `accumulated_summary` 恢复：优先由 `_get_previous_summary`（`phase2_graph.py:39`，读 `summaries` 表）逐章重建，而非直接信任 `project_runs.accumulated_summary` 字符串（后者可能停在崩溃前一刷）。

### in-flight 章恢复口径

- in-flight = 该章有 `draft`/`under_review` head 或残留 checkpoint、但无 `accepted` head。
- 恢复策略首版取**保守重算**：in-flight 章不被跳过（按第 3 条从它开始重跑），但其**残留 LangGraph checkpoint（旧 `thread_id`）必须先清理**，避免脏状态污染重算。真正的"单章内精确续跑"（从 revision 中间步恢复）留作可选子项，不在 MVP 强求。

## In Scope（必须完成）

### 153a — resume 点推导 + CLI 入口
- [ ] `songyan run` 新增 `--resume`（复用最近一次同项目 run）与/或 `--run-id <id>`（指定 run）选项（`cli/main.py:419-434` 加 option，`:435` 加参数，`:471` 透传）。默认不传 = 现状全新 run（行为不变）。
- [ ] `run_project_pipeline` 支持 resume 模式：传入 `resume=True`/`run_id` 时**复用**已有 `run_id`（不 `new_id("run")`），按 **Cross-Task Coordination「resume 点推导口径」** 计算起点，`accumulated_summary` 按口径重建。
- [ ] `ProjectRunRepository`：如需"取项目最近一条 run"，给 `list_by_project` 已有的 `ORDER BY created_at DESC` 直接取首条即可（**不新增过时的 `limit=` 签名**）；如需按 run_id 取用现有 `get(run_id)`。
- [ ] resume 时打印可解释提示：原 run_id、上次 `status`、已完成章数、本次 resume 起点。若上次 `status == "paused"`（AutoHalt），提示原因并要求用户确认续跑意图（不静默续跑）。

### 153b — in-flight 状态恢复 + 孤儿 checkpoint 清理
- [ ] in-flight 章按 **Cross-Task Coordination「in-flight 章恢复口径」** 处理：不跳过、从其重算；重算前清理该章残留 checkpoint。
- [ ] 孤儿 checkpoint 清理：新增清理入口（复用/扩展 `checkpointer.py` 的连接管理），删除**不再属于任何未完成章**的 checkpoint 行（sqlite checkpointer 模式）；memory 模式天然无残留。清理幂等、不误删当前 in-flight 章正在用的行。
- [ ] stuck-at-`running` 行处理：resume 时若发现上次 `project_runs.status == "running"`（硬 kill 遗留），视为可续跑并在续完后正常收尾为 `completed`/`partial`；不把 stuck 行当异常阻断。
- [ ] 遵守边界：只在 run 编排/仓储层改动；不改单章 graph 逻辑、不改治理（149-152）与门禁；不新增 Agent/LLM 调用。

## Out of Scope（明确不做）

- 不做"单章内精确续跑"（从 revision 第 k 轮中间恢复）——in-flight 章 MVP 用保守重算 + checkpoint 清理（可选子项另评）。
- 不改 `on_failure` 失败隔离语义（Task 155）。
- 不做 LLM 限流/预算/熔断（Task 154）与运行中 DB 维护（Task 156）。
- 不引入分布式/多进程并发 run 协调（V6 仍单进程 asyncio）。
- 不改 `human_confirm` 的 `interrupt`/`Command(resume=...)` 语义（那是单章人工确认，非 run 级续跑）。

## 接口契约

```python
# workflows/phase2_graph.py
async def run_project_pipeline(
    project_id: str,
    chapter_range: tuple[int, int],
    mode_id: str = "webnovel",
    *,
    auto_confirm: bool = False,
    max_revision_rounds: int = 2,
    on_failure: str = "abort",
    continuity_health_threshold: float = 7.0,
    gate_config: GateConfig | None = None,
    resume: bool = False,           # 新增：复用最近一次同项目 run
    run_id: str | None = None,      # 新增：指定 run（优先于 resume 的"最近一次"）
) -> ProjectRunResult:
    """resume/run_id 提供时进入续跑：复用 run_id、按 accepted head 推导起点、重建摘要。"""

# 孤儿 checkpoint 清理（workflows/checkpointer.py 或同层新模块）
async def prune_orphan_checkpoints(project_id: str, active_thread_ids: set[str]) -> int:
    """删除不属于任何未完成章的残留 checkpoint 行；返回清理条数（幂等）."""
```

（最终签名以实现为准；核心：resume 复用 run_id + 以 accepted head 为完成事实源 + in-flight 重算前清 checkpoint。）

## 测试要求

### Layer 2: 模块测试（真实临时 SQLite；Mock LLM）
- [ ] **resume 点推导**：造 `project_runs` + 部分 `accepted` head，验证 resume 起点 = 第一个非 accepted 章；已 accept 章仍被跳过并计入 completed。
- [ ] **completed_chapters 领先容错**：构造 `project_runs.completed_chapters` 比真正落库 accepted head 多 1（模拟硬 kill 时刻），验证 resume 以 accepted head 为准、不跳过未真正落库的章。
- [ ] **摘要重建**：resume 后 `previous_summary` 由 `summaries` 表逐章重建，不依赖崩溃前的 `accumulated_summary` 字符串。
- [ ] **in-flight 重算 + checkpoint 清理**：造带 draft head / 残留 checkpoint 的 in-flight 章，验证其被重算且旧 checkpoint 先清理；`prune_orphan_checkpoints` 幂等、不误删活跃章。
- [ ] **stuck-at-running**：上次 `status="running"` 的 run 可被 resume 续完并正常收尾。
- [ ] **paused 提示**：上次 `status="paused"`（AutoHalt）时 resume 打印原因、需显式续跑意图，不静默跳门禁。
- [ ] **默认行为不变**：不传 `--resume`/`--run-id` 时全新 run，与现状逐条一致。

### Layer 3: 小窗口 kill→resume 实跑（阶段 C 出口佐证，可用隔离副本 DB）
- [ ] Ch1-ChN 小窗口跑到中途人为 kill（含一个 in-flight 章），用同一命令 `--resume` 续完：已 accept 章跳过、in-flight 章正确恢复、最终章数与不中断跑一致；无需人工改命令/清 DB。
- [ ] 证据入 `docs/reports/`（kill 点、resume 起点、最终章数、跳过/重算清单）。

## 验收标准（Acceptance Criteria）

- [ ] `pytest tests/test_153_*.py -v` 全过；`ruff check src/ tests/` 通过；全量 pytest 不回归。
- [ ] `songyan run --resume`（及/或 `--run-id`）可用；resume 以 accepted head 为完成事实源；in-flight 章重算前清 checkpoint；孤儿 checkpoint 被清理且幂等。
- [ ] Layer 3 证明中途 kill 后同命令 resume 续完，已 accept 跳过、in-flight 恢复，无人工干预（证据入 `docs/reports/`）。
- [ ] 不违反不可违背规则：只改 run 编排/仓储；不改单章 graph、治理与门禁；不弱化 AutoHalt；不新增 Agent/LLM。
- [ ] 生成 `tasks/153-run-level-resume-DONE.md`，含 resume 点推导口径、in-flight 恢复策略、孤儿清理范围、Layer 3 kill→resume 证据。
- [ ] 更新 `tasks/V6-README.md`（153 状态）与 `docs/STATUS.md`。

## 参考文档

- `docs/v6-plan.md` §1.3-R（可靠性判据）、§3 阶段 C（Task 153 行 + 阶段 C 出口）
- 现有代码：`workflows/phase2_graph.py`（`run_project_pipeline` 主循环 / `_persist_run_progress` / `_get_previous_summary` / skip-accepted）、`workflows/checkpointer.py`（`reset_checkpointer`/`reset_checkpointer_instance`）、`db/project_run_repo.py`（`ProjectRunRepository`）、`db/schema.sql:353`（`project_runs`）、`cli/main.py:419`（`run` 命令）
- 归档参考（**过时签名，仅作思路参考，不可照抄 `limit=`**）：`archive/v5/scripts/run_task_105b_ch51_ch100.py:86`（`_find_resume_point`）
