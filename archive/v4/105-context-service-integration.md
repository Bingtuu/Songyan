# Task 105: Phase1Graph ContextService 集成

> **Phase**: V4.0 Phase C — ContextService 演进（门控/暂缓）
> **优先级**: P1（暂缓）
> **依赖**: Task 104（ContextService 核心接口就绪）
> **预计工作量**: 中（3 天）

---

## Goal

在 Phase1Graph 中集成 ContextService，通过 `USE_CONTEXT_SERVICE` 配置开关选择旧路径（ContextPackage）或新路径（AgentContext）。不修改任何工作流节点签名，旧代码完整保留。

## Context

Phase C 门控任务。本 Task 只做一个 gateway：读取配置开关，决定走 ContextManager 旧路径还是 ContextService 新路径。所有节点函数签名不变。

## In Scope（必须完成）

- [ ] **配置开关**：`USE_CONTEXT_SERVICE = False`（默认）
- [ ] **Gateway 函数**：在 Phase1Graph 入口判断走哪个路径
- [ ] **兼容字段**：`context_package` 保留为兼容字段（新路径下也填充）
- [ ] **单元测试**：开关切换正确；旧模式回归通过；新模式 Ch1-Ch5 端到端跑通

## Out of Scope（明确不做）

- 修改任何 Agent Prompt
- 修改工作流节点签名
- 废弃 ContextManager
- 重写 Phase1Graph

## 接口契约

```python
# src/songyan/config.py（新增）
USE_CONTEXT_SERVICE: bool = False  # 默认关闭

# src/songyan/workflows/_helpers.py（修改）
async def load_context(
    project_id: str,
    chapter_number: int,
    agent_id: str | None = None,
) -> ContextPackage | AgentContext:
    """Gateway：根据配置选择旧路径或新路径."""
    if settings.USE_CONTEXT_SERVICE and agent_id:
        return await context_service.get_agent_context(agent_id, project_id, chapter_number)
    return await context_manager.assemble(project_id, chapter_number)
```

## 测试要求

### Layer 2: 模块测试
- [ ] `USE_CONTEXT_SERVICE=False` → 返回 ContextPackage
- [ ] `USE_CONTEXT_SERVICE=True` → 返回 AgentContext

### Layer 3: 集成测试
- [ ] 旧模式 Ch1-Ch5 端到端跑通
- [ ] 新模式 Ch1-Ch5 端到端跑通

## 验收标准（Acceptance Criteria）

- [ ] `pytest tests/workflows/ -v` 全部通过
- [ ] 旧模式全量回归通过
- [ ] 新模式 Ch1-Ch5 端到端跑通
- [ ] 生成了 `tasks/105-context-service-integration-DONE.md`

## 参考

- `docs/v4.0-tech-plan.md` — 第 6.4 节
