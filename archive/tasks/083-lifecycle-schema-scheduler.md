# Task 083: 数据生命周期 Schema 迁移 + LifecycleScheduler 通用框架

> **Phase**: V4.0 Phase A — 数据生命周期 + 动态预算
> **优先级**: P0
> **依赖**: Task 081（V3.x 基线已冻结）
> **预计工作量**: 中（2 天）

---

## Goal

为所有元数据表新增 `status` 字段和生命周期索引，并实现 `LifecycleScheduler` 通用调度框架（状态机、异步触发、异常处理、手动触发接口），为 Task 084/085 的具体表策略提供基础设施。

## Context

V3.x 中所有元数据表只增不减，导致 Ch70 时 setting_snapshots=129 条、foreshadowings=62 条、human_marks=100+。Phase A 的核心前提是让这些表支持 `active → dormant → archived` 三级状态。本 Task 不做具体表的策略逻辑，只提供通用框架和 Schema 变更。

## In Scope（必须完成）

- [ ] **Schema 迁移**：为 5 张表新增 `status` 字段（`TEXT CHECK(status IN ('active', 'dormant', 'archived')) DEFAULT 'active'`）
  - `setting_snapshots`
  - `foreshadowings`
  - `human_marks`
  - `character_states`
  - `chapter_chunks`
- [ ] **索引优化**：为 `(project_id, status, chapter_number)` 或等效字段建复合索引
- [ ] **LifecycleScheduler 框架**：
  - `LifecycleScheduler` 类，支持每 N 章异步触发
  - 状态机：`transition(entity, from_status, to_status, reason)`，带日志
  - 异常处理：单表失败不阻塞其他表，记录到 `lifecycle_errors` 日志表
  - 手动触发接口：`run_cleanup(project_id, current_chapter)` 供 SettlementExtractor 后调用
- [ ] **向后兼容**：现有数据 `status` 默认 `'active'`，不影响任何现有查询
- [ ] **单元测试**：
  - 迁移后 Schema 正确（新插入数据默认 active）
  - Scheduler 状态转换逻辑正确
  - 异常处理（单表失败不级联）
  - 手动触发接口可用

## Out of Scope（明确不做）

- 具体表的休眠/归档策略逻辑（Task 084/085）
- BudgetPruner 的过滤逻辑改造（Task 086）
- 任何 Agent 代码修改
- 任何 Prompt 修改

## 接口契约

```python
# src/songyan/db/lifecycle_scheduler.py
class LifecycleScheduler:
    def __init__(self, db: DBConnection) -> None: ...
    
    async def run_cleanup(
        self,
        project_id: str,
        current_chapter: int,
    ) -> LifecycleCleanupResult:
        """运行全表生命周期清理。SettlementExtractor 后调用。"""
        ...
    
    async def transition(
        self,
        table: str,
        entity_id: str,
        from_status: LifecycleStatus,
        to_status: LifecycleStatus,
        reason: str,
    ) -> None:
        """单条记录状态转换，带校验和日志。"""
        ...

class LifecycleCleanupResult(BaseModel):
    project_id: str
    current_chapter: int
    transitions: list[TransitionLog]
    errors: list[str] = []
    
class TransitionLog(BaseModel):
    table: str
    entity_id: str
    from_status: LifecycleStatus
    to_status: LifecycleStatus
    reason: str
    timestamp: datetime

LifecycleStatus = Literal["active", "dormant", "archived"]
```

## 数据模型

```python
# 新增/修改的模型（Pydantic v2）

# 5 张表新增字段（通过 Alembic/SQLite ALTER TABLE）
# ALTER TABLE setting_snapshots ADD COLUMN status TEXT CHECK(status IN ('active', 'dormant', 'archived')) DEFAULT 'active';
# ALTER TABLE foreshadowings ADD COLUMN status TEXT ...;
# ...（共 5 张表）

class LifecycleConfig(BaseModel):
    """各表生命周期策略配置（供 Task 084/085 填充）。"""
    table: str
    active_to_dormant_window: int  # 章数
    dormant_to_archived_window: int  # 章数
    exceptions: list[str] = []  # 如 ["is_critical", "protagonist"]
```

## 测试要求

### Layer 1: 模型测试
- [ ] `LifecycleStatus` 枚举约束正确（只允许 active/dormant/archived）
- [ ] `LifecycleCleanupResult` 序列化/反序列化正确

### Layer 2: 模块测试
- [ ] 正向：迁移后插入数据，status 默认 active
- [ ] 正向：Scheduler.transition() 正常状态流转
- [ ] 异常：from_status ≠ 当前状态 → 拒绝转换
- [ ] 异常：单表 transition 失败不级联影响其他表
- [ ] Mock：DB 连接失败时 graceful degrade

### Layer 3: 集成测试
- [ ] SettlementExtractor 后调用 `run_cleanup()` 不阻塞主流程

## 验收标准（Acceptance Criteria）

- [ ] `pytest tests/db/test_lifecycle_scheduler.py -v` 全部通过
- [ ] `pytest tests/db/test_schema_migration.py -v` 验证 5 张表 status 字段正确
- [ ] 代码符合 CLAUDE.md 规范（类型标注、单文件 < 400 行等）
- [ ] 不违反任何不可违背规则（Agent 不直接拿 DB connection — 通过 Service 层）
- [ ] 生成了 `tasks/083-lifecycle-schema-scheduler-DONE.md` 交接文件

## 参考

- `docs/v4.0-tech-plan.md` — 第 4.1 节数据生命周期管理
- `archive/v3/reports/v3.1_ch51_ch70_validation_report.md` — Ch70 数据膨胀基线
