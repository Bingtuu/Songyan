# Task 104: ContextService 核心接口 + AgentContext 模型

> **Phase**: V4.0 Phase C — ContextService 演进（门控/暂缓）
> **优先级**: P1（暂缓）
> **依赖**: 决策门 1（Task 103，如 Phase B 修复后仍未达标，启动 Phase C）
> **预计工作量**: 大（4 天）
> **状态**: 暂缓 — Task 091 证明 token budget 优秀（1.073），当前问题不在上下文架构

---

## Goal

实现 ContextService 核心接口和 AgentContext 数据模型，提供分层检索能力（L0 元数据 / L1 近期剧情 / L2 档案数据），为 Task 105 的 Phase1Graph 集成提供基础。不修改任何现有 Agent 代码。

## Context

Phase C 仅在决策门 1（Task 103）触发时启动。ContextService 是一个**可选包装层**，不废弃 ContextManager，在其之上提供按需检索接口。如果 Phase A+B 已达标，本 Task 可推迟到 V4.1。

## In Scope（必须完成）

- [ ] **ContextService 接口**：
  - `get_l0_meta(project_id)` → ProjectMeta, GenreRules, ModeRules
  - `get_l1_plot(project_id, chapter_number)` → recent summaries, arc/volume summaries
  - `get_l2_characters(project_id, ...)` → CharacterStateSnapshot[]
  - `get_l2_settings(project_id, ...)` → SoftReference[]
  - `get_l2_foreshadowings(project_id, ...)` → ForeshadowingItem[]
  - `get_l2_human_marks(project_id, ...)` → HumanMark[]
- [ ] **AgentContext 模型**：取代 ContextPackage 的 Agent 专属小包
- [ ] **AgentContextProfile 注册**：各 Agent 声明需要什么上下文、要多少
- [ ] **单元测试**：所有查询接口覆盖；AgentContext 序列化正确；RuleAuditor context < 3K

## Out of Scope（明确不做）

- 修改任何 Agent 代码或 Prompt
- 修改 Phase1Graph（Task 105）
- 废弃 ContextManager（旧代码完整保留）

## 接口契约

```python
# src/songyan/context_service/core.py（新增）

class ContextService:
    """按需检索服务 — 可选层，不废弃 ContextManager."""
    
    def __init__(self, db: DBConnection) -> None: ...
    
    # Layer 0: 元数据（小数据，全量）
    async def get_l0_meta(self, project_id: str) -> L0Meta: ...
    
    # Layer 1: 近期剧情（中等数据，范围查询）
    async def get_l1_plot(self, project_id: str, chapter_number: int) -> L1Plot: ...
    
    # Layer 2: 档案数据（大数据，条件检索）
    async def get_l2_characters(self, project_id: str, **filters) -> list[CharacterStateSnapshot]: ...
    async def get_l2_settings(self, project_id: str, **filters) -> list[SoftReference]: ...
    async def get_l2_foreshadowings(self, project_id: str, **filters) -> list[ForeshadowingItem]: ...
    async def get_l2_human_marks(self, project_id: str, **filters) -> list[HumanMark]: ...
    
    # 便捷方法
    async def get_agent_context(
        self, agent_id: str, project_id: str, chapter_number: int
    ) -> AgentContext: ...

class AgentContext(BaseModel):
    """单个 Agent 的上下文 — 取代 ContextPackage."""
    l0_meta: L0Meta
    l1_plot: L1Plot
    l2_characters: list[CharacterStateSnapshot] = []
    l2_settings: list[SoftReference] = []
    l2_foreshadowings: list[ForeshadowingItem] = []
    l2_human_marks: list[HumanMark] = []
    budget_tokens: int
    used_tokens: int = 0

AGENT_CONTEXT_PROFILES = {
    "writer": {"layers": ["l0", "l1", "l2_c", "l2_s", "l2_f", "l2_m"]},
    "rule_auditor": {"layers": ["l0"]},
    "llm_auditor": {"layers": ["l0", "l1", "l2_c"]},
    "revision_handler": {"layers": ["l0", "l1", "l2_c", "l2_s"]},
    "settlement_extractor": {"layers": ["l0", "l1"]},
    "summary_writer": {"layers": ["l0", "l1"]},
}
```

## 测试要求

### Layer 2: 模块测试
- [ ] 所有 L0/L1/L2 查询接口返回正确类型
- [ ] `get_agent_context("rule_auditor")` 只包含 l0_meta
- [ ] AgentContext 序列化/反序列化正确

### Layer 3: 集成测试
- [ ] RuleAuditor context tokens < 3000

## 验收标准（Acceptance Criteria）

- [ ] `pytest tests/context_service/ -v` 全部通过
- [ ] RuleAuditor context < 3K tokens
- [ ] 生成了 `tasks/104-context-service-core-DONE.md`

## 参考

- `docs/v4.0-tech-plan.md` — 第 6.2-6.3 节
