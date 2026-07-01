# Task 020-A: Mock 端到端集成测试 + Checkpoint 恢复

> **Phase**: Phase 4 — 评测与优化
> **优先级**: P0
> **依赖**: Task 001 ~ 019（全部完成）
> **预计工作量**: 中
> **前置子任务**: 无（020-A 是 Phase 4 首个子任务）

---

## Goal

用 mock 数据验证 LangGraph 工作流各节点通过 ID 从 DB 加载数据的端到端链路正确，覆盖全部 6 条用户决策路径和 checkpoint 中断恢复机制。

## Context

Task 019 已完成 LangGraph 编排（12 节点状态机），所有 Agent 独立测试通过（617 tests）。但当前尚未验证：

1. **端到端数据链路**：各节点通过 `version_id` / `report_id` 从 DB 加载，而非从 state 取正文，这条链路是否正确
2. **循环路径**：`revision_handler → rule_auditor → llm_auditor → review_merger` 循环是否能在 2 轮后正确退出
3. **人工确认恢复**：`interrupt → Command(resume) → 继续执行` 的 checkpoint 恢复机制
4. **状态副作用**：`accept/edit/reject/back` 四种决策对 `chapter_heads` / `chapter_versions` / `revision_round` 的影响是否正确

本 Task 是 020 拆分后的第一个子任务，完成后 020-B 才能基于稳定的集成基线构建评测集。

---

## In Scope（必须完成）

### 1. 测试基础设施搭建

- [ ] 创建 `tests/test_integration.py`（单文件，若超过 400 行拆为 `tests/integration/` 包）
- [ ] 实现 `MockLLMClient`：按场景返回预置的 JSON 响应（ChapterGoal / CreativeBrief / ChapterVersion / LLMAuditResult / LiteraryAuditResult / RevisionOutput / StateSettlement / Summary）
- [ ] 实现 `IntegrationTestDB`：基于 `db/connection.py` 创建隔离的内存 SQLite（`:memory:` 或临时文件），每个测试独立 schema
- [ ] 实现辅助函数 `seed_project(db)`：快速插入一个 xuanhuan + webnovel 项目 + 角色档案，供各路径复用

### 2. 六条端到端路径测试

每条路径须 mock 所有 LLM 调用，真实写入 SQLite，验证最终 DB 状态。

- [ ] **路径 A（无 issue，直接 accept）**
  - 流程：`goal_planner → creative_director → context_manager → writer → rule_auditor → llm_auditor → review_merger → literary_auditor → revision_router(pass) → human_confirm(accept) → settlement_extractor → done`
  - 验证：
    - 最终 `state["status"] == "done"`
    - `state["settlement_id"]` 和 `state["summary_id"]` 非空
    - `chapter_heads.accepted_version_id == current_version_id`
    - `chapter_versions` 中该版本 `version_type == "draft"`（由 writer 创建）且 `chapter_heads.status == "accepted"`
    - `revision_round == 0`

- [ ] **路径 B（1 轮修订后 accept）**
  - mock `review_merger` 第 1 轮产出 `_needs_revision = True`（含 critical issue）
  - mock `revision_handler` 返回 patch 后正文
  - mock 第 2 轮 `review_merger` 产出 `_needs_revision = False`
  - 验证：
    - `revision_round == 1`
    - `current_version_id` 已更新为新版本（revision 版本）
    - `chapter_versions` 存在 2 条记录（draft + revision）
    - 最终 state 到达 `done`

- [ ] **路径 C（2 轮修订后强制退出）**
  - mock `review_merger` 连续 2 轮产出 `_needs_revision = True`
  - 第 3 轮 `revision_router` 因 `revision_round >= 2` 强制路由到 `pass`
  - 验证：
    - `revision_round == 2`（不超过 2）
    - `chapter_versions` 存在 3 条记录（draft + revision × 2）
    - 流程进入 `human_confirm`

- [ ] **路径 D（reject 后重置）**
  - `human_confirm` 返回 `reject`
  - 验证：
    - 最终路由回 `goal_planner`（state 状态为 `goal_planning`）
    - `revision_round == 0`
    - `chapter_heads` 未被标记为 accepted

- [ ] **路径 E（back 后 writer 重写）**
  - `human_confirm` 返回 `back`
  - mock `writer` 第 2 次调用返回新版本正文
  - 验证：
    - 最终路由回 `writer`，生成新 `current_version_id`
    - `chapter_versions` 存在 2 条 draft 记录（第 1 稿 + 第 2 稿）
    - `revision_round == 0`

- [ ] **路径 F（edit 后保存 edited 版本）**
  - `human_confirm` 返回 `edit`
  - inject `set_editor_callable(lambda c: c + "\n\n[人工编辑补充]")`
  - 验证：
    - `chapter_versions` 存在 edited 版本，`version_type == "edited"`
    - `chapter_heads.accepted_version_id` 指向 edited 版本
    - `settlement_extractor` 在 edit 后继续执行并到达 `done`

### 3. Checkpoint 恢复测试

- [ ] **中断恢复**：
  - 启动 workflow，在 `human_confirm` 中断前停止（通过 `thread_id` 保持 checkpoint）
  - 新 graph 实例使用相同 `thread_id` 和 `MemorySaver`
  - 调用 `resume_human_confirm(thread_id, "accept")`
  - 验证流程从 `settlement_extractor` 继续并到达 `done`

- [ ] **状态一致性**：
  - 恢复后的 state 与中断前 state 的 `project_id / chapter_number / current_version_id / revision_round` 完全一致
  - 验证 DB 中没有重复写入同一版本

---

## Out of Scope（明确不做）

- 真实 LLM 调用（全部 mock）
- 评测集 runner 和种子项目配置（属于 020-B）
- 验收指标的计算与断言（属于 020-C）
- 性能基准测试（属于 020-C）
- 多章连续生成（V1.0 只验证单章闭环）
- PostgreSQL / Redis / Qdrant
- Web UI / TUI

---

## 接口契约

本 Task **不新增公共接口**，只编写测试代码。测试中需直接调用以下已有接口：

```python
# 测试入口
from songyan.workflows.phase1_graph import (
    run_chapter_pipeline,
    resume_human_confirm,
    build_phase1_graph,
)
from songyan.workflows._nodes import set_editor_callable

# 测试辅助（已在代码中暴露）
async def run_chapter_pipeline(
    project_id: str,
    chapter_number: int,
    mode_id: str = "webnovel",
    thread_id: str | None = None,
) -> Phase1State: ...

async def resume_human_confirm(
    thread_id: str,
    decision: str,
    edited_content: str | None = None,
) -> Phase1State: ...

def set_editor_callable(editor: Callable[[str], str] | None) -> None: ...
```

**Mock 策略**：

```python
# 1. Mock LLM 调用（统一入口）
@pytest.fixture
def mock_llm(monkeypatch):
    async def fake_call_llm(prompt: str, **kwargs) -> str:
        # 根据 prompt 内容或 kwargs 中的 node_id 返回预置 JSON
        ...
    monkeypatch.setattr("songyan.llm.client.call_llm", fake_call_llm)

# 2. 隔离数据库
@pytest.fixture
async def test_db():
    # 创建临时 SQLite，执行 schema.sql，yield 后清理
    ...

# 3. human_confirm 不阻塞测试
# 通过设置 state 使 interrupt 行为可被注入，或通过 mock interrupt 函数
```

> **注意**：`human_confirm_node` 使用了 `langgraph.types.interrupt`，在测试中可通过 patch `interrupt` 返回值或使用 `Command(resume=...)` 恢复。路径 A~F 的测试策略为：先 `run_chapter_pipeline` 到中断，再 `resume_human_confirm`。

---

## 数据模型

本 Task **不新增业务模型**。测试中使用的辅助模型（若需要）：

```python
class MockLLMScenario(BaseModel):
    """预置 mock 响应场景."""
    scenario_id: str
    responses: dict[str, str]  # node_name -> JSON response
```

---

## 测试要求

### Layer 1: 路径正向测试
- [ ] 路径 A（无 issue）mock 通过
- [ ] 路径 B（1 轮修订）mock 通过
- [ ] 路径 C（2 轮后强制退出）mock 通过
- [ ] 路径 D（reject）mock 通过
- [ ] 路径 E（back）mock 通过
- [ ] 路径 F（edit）mock 通过

### Layer 2: Checkpoint 测试
- [ ] 中断后 `resume_human_confirm("accept")` 成功到达 `done`
- [ ] 中断后 `resume_human_confirm("reject")` 成功回到 `goal_planner`
- [ ] 恢复后的 state 与中断前一致
- [ ] 相同 `thread_id` 不会重复创建记录

### Layer 3: DB 副作用验证
- [ ] 每条路径结束后，DB 中 `chapter_versions` 数量正确
- [ ] `chapter_heads` 指向正确的 `accepted_version_id`
- [ ] `revision_round` 符合预期
- [ ] `settlement_id` / `summary_id` 在 accept/edit 后非空，reject/back 后为空

---

## 验收标准（Acceptance Criteria）

- [ ] `pytest tests/test_integration.py -v` 全部通过（≥ 9 个测试用例：6 条路径 + 3 个 checkpoint）
- [ ] 代码符合 CLAUDE.md 规范（类型标注、单文件 < 400 行等）
- [ ] 不违反任何不可违背规则（特别是：state 只存 ID、版本不覆盖、character_states INSERT only）
- [ ] 每个测试独立数据库，互不污染
- [ ] 生成了 `tasks/020-A-mock-e2e-integration-DONE.md` 交接文件
- [ ] **不更新 docs/STATUS.md**（Phase 4 整体完成后再统一更新，由 020-C 负责）

---

## 参考文档

- `tasks/020-e2e-evaluation.md` — 父任务总纲
- `src/songyan/workflows/phase1_graph.py` — LangGraph 编排入口
- `src/songyan/workflows/_nodes.py` — 12 个节点函数
- `src/songyan/workflows/_helpers.py` — 数据加载辅助
- `docs/architecture/04-vibe-coding-engineering.md` — 工程手册 + 验收指标
- `system_prompt/development-tech-plan-v2.md` — V2 技术方案第 9~10 章
