# Task 111f: Context Snapshot、Prompt 与 Metadata 一致性修复

> **Phase**: V5.0 Phase 4 前置修复 — Context/Prompt Replayability
> **优先级**: P1
> **依赖**: Task 111d、111e 完成
> **预计工作量**: 1-2 天

---

## Goal

修复 ContextManager 组装结果在 Writer/Auditor 之间反复重组导致的字段丢失问题，并补齐 `generation_metadata` 的 creative brief 快照，使每个版本的 prompt 输入可回放、可审计、与 Task 111c 的上下文契约一致。

## Context

post-111 review 确认：

1. `context_manager_node()` 组装 ContextPackage 时会注入 `human_instructions`，并根据 CreativeBrief 派生 `narrative_fullness`、`character_focus`、`foreshadowing_due`、`focal_distance` 等动态字段。
2. Task 111b 后 LangGraph state 不保存完整 ContextPackage；Writer、LLMAuditor、LiteraryAuditor 通过 `_get_context_package()` 重新组装上下文。
3. 重新组装路径没有带上 `human_instructions`，也没有复用 ContextManager 当时的动态组装参数，导致 Writer prompt 与 ContextManager 输出不一致。
4. `generation_metadata` 只保存 `context_snapshot` 和 `creative_brief_id`，没有保存 creative brief 内容快照，不利于回放和审计。

## In Scope（必须完成）

- [ ] **定义轻量 context snapshot 方案**
  - 不在 LangGraph state 存完整业务对象
  - state 只存 `context_snapshot_id` 或等价轻量 ID
  - snapshot 中保存 Writer/Auditor 需要的裁剪后上下文输入
  - snapshot 可在测试 DB 中写入、读取、清理

- [ ] **统一 Writer/Auditor 上下文来源**
  - Writer 使用 ContextManager 产生的同一份上下文快照
  - LLMAuditor / LiteraryAuditor 若需要上下文，也复用同一 snapshot 或明确只读取轻量派生字段
  - 不再因为重新组装而丢失 `human_instructions` 或 CreativeBrief 动态字段

- [ ] **补齐 generation metadata**
  - `generation_metadata` 写入 `context_snapshot_id`
  - `generation_metadata` 写入精简 `creative_brief_snapshot`
  - 保留现有 `creative_brief_id` 外键
  - metadata 不应保存完整超大对象或 LLM 原始响应

- [ ] **保持 Task 111b state 规则**
  - LangGraph state 仍只保存 ID、轻量 metrics、路由字段
  - 不把完整 ContextPackage 放回 state

## Out of Scope（明确不做）

- 不做 ContextManager DB 查询性能优化，该项进入 Task 111g
- 不调 Writer 文学风格 prompt
- 不改变 Craft Card 权重规则
- 不新增大型缓存系统；优先使用 SQLite snapshot 或已有 repository 模式

## Snapshot 建议契约

```python
class ContextSnapshot(BaseModel):
    snapshot_id: str
    project_id: str
    chapter_number: int
    chapter_goal_id: str | None
    creative_brief_id: str | None
    budget_used: float | None
    context_emergency: bool
    payload: dict[str, Any]  # 裁剪后、可序列化、供 prompt/audit 使用
```

实际模型可更简单，但必须满足：

- 可序列化
- 可由 ID 读取
- 不进入 LangGraph state 的完整对象
- 能保留 human instructions 和动态 brief 字段

## 关键测试标准

### Layer 1: 单元测试

- [ ] `context_manager_node` 返回 `context_snapshot_id` 和 `_context_metrics`，不返回完整 `context_package`
- [ ] Writer 读取 snapshot 后，prompt 中包含 human instruction 内容
- [ ] Writer 读取 snapshot 后，prompt 或上下文变量中包含 CreativeBrief 派生字段
- [ ] `generation_metadata` 包含 `context_snapshot_id`
- [ ] `generation_metadata` 包含 `creative_brief_snapshot`
- [ ] `generation_metadata` 不包含完整不可控大对象

### Layer 2: 模块测试

- [ ] 同一章节同一版本 Writer、LLMAuditor、LiteraryAuditor 使用同一 `context_snapshot_id`
- [ ] snapshot 缺失时有明确错误或兼容 fallback，不静默丢字段
- [ ] human instruction 使用旧 `type` 字段和新 `action` 字段时，snapshot/prompt 均能稳定渲染

### Layer 3: 回归测试

- [ ] `pytest tests/test_phase1_graph.py tests/test_writer.py tests/test_context_manager.py -q`
- [ ] `pytest tests/test_prompt_loader.py tests/test_rule_auditor.py -q`
- [ ] `pytest tests/ -q`
- [ ] 本次触及文件 `ruff check` 通过

## 验收标准（Acceptance Criteria）

- [ ] Writer prompt 不再因 context 重组丢失 human instructions
- [ ] Writer prompt / metadata 不再因 context 重组丢失 CreativeBrief 动态字段
- [ ] LangGraph state 仍不保存完整 ContextPackage
- [ ] 每个 `chapter_versions` 记录可追踪 `context_snapshot_id` 和 `creative_brief_snapshot`
- [ ] 生成 `tasks/111f-context-snapshot-prompt-metadata-fix-DONE.md`
- [ ] 更新 `docs/STATUS.md`
- [ ] Git commit 包含代码、测试、DONE 文档和状态更新

## 参考证据

- `src/songyan/workflows/_nodes.py` — `context_manager_node()`、`_get_context_package()`、`writer_node()`
- `src/songyan/workflows/_helpers.py` — ContextPackage 组装参数
- `src/songyan/agents/writer.py` — `generation_metadata`
- `src/songyan/db/schema.sql` — `chapter_versions.generation_metadata`

## 下一 Task

**Task 111g: 长跑性能缺陷收敛**
