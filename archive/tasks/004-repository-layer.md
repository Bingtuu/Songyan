# Task 004: Repository 数据访问层

> **Phase**: Phase 1
> **优先级**: P0
> **依赖**: Task 002（Pydantic 模型）, Task 003（SQLite Schema）
> **预计工作量**: 大

---

## Goal

实现所有表的异步 CRUD Repository，负责 Pydantic 模型 ↔ SQLite 行 的序列化/反序列化。

## Context

Schema（Task 003）已就绪，13 张表、外键约束、WAL 模式。本 Task 在其上搭建数据访问层：
- JSON 字段的序列化/反序列化（`json.dumps/loads`）
- 所有 ID 由调用方生成，Repository 只做持久化
- `character_states` 永远 INSERT，Repository 不提供 UPDATE 接口
- 单文件不超过 400 行，超过时按领域拆模块

## In Scope（必须完成）

- [ ] `src/songyan/db/repository.py` — 核心 Repository（≤ 400 行）
  - `ProjectRepository`: `create(project: ProjectSetting, project_id: str) -> None`, `get(project_id) -> ProjectSetting | None`
  - `CharacterRepository`: `create`, `get`, `list_by_project`, `add_state_snapshot`（INSERT only）⭐
  - `ChapterGoalRepository`: `create`, `get_by_chapter`
  - `ChapterVersionRepository`: `create`, `get`, `list_by_chapter`, `get_chain(version_id)`（递归 parent_version_id）
  - `ChapterHeadRepository`: `get`, `update`（UPDATE 允许，非版本表）
- [ ] `src/songyan/db/review_repo.py` — 审查 Repository（≤ 400 行）
  - `CreativeBriefRepository`: `create`, `get` ⭐
  - `ReviewReportRepository`: `create`, `get_by_version`（含 rule_audit_result + llm_audit_result JSON 序列化）⭐
  - `LiteraryObservationRepository`: `create`, `get_by_version` ⭐
- [ ] `src/songyan/db/settlement_repo.py` — 结算 Repository（≤ 400 行）
  - `ForeshadowingRepository`: `create`, `update_status`, `list_active`
  - `SettingSnapshotRepository`: `create`, `list_by_project`（含 setting_key 追踪）⭐
  - `NumericalLedgerRepository`: `create`, `get_latest`
- [ ] `src/songyan/db/__init__.py` — 公共导出
- [ ] `tests/db/test_repository.py` — 所有 Repository 测试（≥ 25 个用例）

## Out of Scope（明确不做）

- Agent 逻辑（Task 008+）
- CLI（Task 007）
- 事务封装（UnitOfWork 留给 Phase 3）
- 批量写入优化
- 缓存层

## 接口契约

### 核心原则
1. **ID 由调用方生成**：Repository 不生成 UUID，只负责 INSERT/SELECT
2. **JSON 字段 Repository 层处理**：模型中的 `list`/`dict` 字段出入库时自动 `json.dumps/loads`
3. **`character_states` INSERT only**：`CharacterRepository.add_state_snapshot()` 只做 INSERT，不提供 UPDATE 方法
4. **`datetime` 存 ISO 字符串**：`created_at`, `updated_at` 存 `datetime.isoformat()`，读时解析
5. **外键错误透传**：违反 FK 时让 `aiosqlite.IntegrityError` 自然抛出，不吞异常

### 公共工具函数

```python
import json
from typing import Any

def _to_json(value: Any) -> str:
    """Pydantic 字段 → SQLite TEXT."""
    return json.dumps(value, ensure_ascii=False, default=str)

def _from_json(value: str | None, default: Any = None) -> Any:
    """SQLite TEXT → Python 对象."""
    if value is None:
        return default
    return json.loads(value)
```

### 模型 ↔ 表字段映射速查

| 模型 | 表 | JSON 字段 |
|------|-----|-----------|
| `ProjectSetting` | `projects` | `taboos`, `reference_works` |
| `Character` | `characters` | `personality_traits`, `goals`, `relationships` |
| `CharacterState` | `character_states` | 无 |
| `ChapterGoal` | `chapter_goals` | `target_events`, `hooks`, `obligations` |
| `ChapterVersion` | `chapter_versions` | `scenes`, `generation_metadata` |
| `ChapterHead` | `chapter_heads` | 无 |
| `CreativeBrief` | `creative_briefs` | `required_tensions`, `forbidden_patterns`, `allowed_fissures`, `style_constraints`, `polyphony_notes`, `chapter_goal` |
| `MergedReviewReport` | `review_reports` | `rule_audit_result`, `llm_audit_result`, `issues`, `dimension_scores` |
| `LiteraryAuditResult` | `literary_observations` | `observations` |
| `ForeshadowingItem` | `foreshadowings` | 无（但 `source_version_id` 由调用方传入） |
| `NewSetting` | `setting_snapshots` | 无 |
| `NumericalUpdate` | `numerical_ledgers` | `increments`, `decrements` |

### 重点方法签名

```python
class ProjectRepository:
    async def create(self, project: ProjectSetting, project_id: str) -> None: ...
    async def get(self, project_id: str) -> ProjectSetting | None: ...

class CharacterRepository:
    async def create(self, character: Character) -> None: ...
    async def get(self, character_id: str) -> Character | None: ...
    async def list_by_project(self, project_id: str) -> list[Character]: ...
    async def add_state_snapshot(self, state: CharacterState) -> int: ...  # 返回 state_id

class ChapterVersionRepository:
    async def create(self, version: ChapterVersion) -> None: ...
    async def get(self, version_id: str) -> ChapterVersion | None: ...
    async def list_by_chapter(self, project_id: str, chapter_number: int) -> list[ChapterVersion]: ...
    async def get_chain(self, version_id: str) -> list[ChapterVersion]: ...  # 递归 parent_version_id

class ChapterHeadRepository:
    async def get(self, project_id: str, chapter_number: int) -> ChapterHead | None: ...
    async def update(self, head: ChapterHead) -> None: ...

class ReviewReportRepository:
    async def create(self, report: MergedReviewReport) -> None: ...
    async def get_by_version(self, chapter_version_id: str) -> MergedReviewReport | None: ...

class CreativeBriefRepository:
    async def create(self, brief: CreativeBrief, brief_id: str, project_id: str, chapter_number: int) -> None: ...
    async def get(self, brief_id: str) -> CreativeBrief | None: ...

class LiteraryObservationRepository:
    async def create(self, result: LiteraryAuditResult, observation_id: str, version_id: str) -> None: ...
    async def get_by_version(self, version_id: str) -> LiteraryAuditResult | None: ...

class ForeshadowingRepository:
    async def create(self, item: ForeshadowingItem, project_id: str) -> None: ...
    async def update_status(self, foreshadowing_id: str, status: str) -> None: ...
    async def list_active(self, project_id: str) -> list[ForeshadowingItem]: ...

class SettingSnapshotRepository:
    async def create(self, setting: NewSetting, project_id: str) -> None: ...
    async def list_by_project(self, project_id: str) -> list[NewSetting]: ...

class NumericalLedgerRepository:
    async def create(self, update: NumericalUpdate, project_id: str, chapter_number: int) -> None: ...
    async def get_latest(self, character_id: str, attribute_name: str) -> NumericalUpdate | None: ...
```

## 测试要求

### Layer 1: 基础 CRUD（每个 Repository 至少 2 个测试）
- [ ] `ProjectRepository.create` + `get` 正向用例
- [ ] `CharacterRepository.create` + `get` + `list_by_project`
- [ ] `CharacterRepository.add_state_snapshot` 可多次调用（INSERT only）
- [ ] `ChapterVersionRepository.create` + `get`
- [ ] `ChapterVersionRepository.list_by_chapter` 返回多版本
- [ ] `ChapterVersionRepository.get_chain` 递归追溯版本链
- [ ] `ChapterHeadRepository.update` 可更新（非快照表）
- [ ] `CreativeBriefRepository.create` + `get`（JSON 字段验证）⭐
- [ ] `ReviewReportRepository.create` + `get_by_version`（rule/llm JSON 验证）⭐
- [ ] `LiteraryObservationRepository.create` + `get_by_version` ⭐
- [ ] `ForeshadowingRepository.create` + `update_status` + `list_active`
- [ ] `SettingSnapshotRepository.create` + `list_by_project`（setting_key 验证）⭐
- [ ] `NumericalLedgerRepository.create` + `get_latest`

### Layer 2: 异常与边界
- [ ] `get` 不存在的 ID 返回 `None`
- [ ] 违反外键抛 `IntegrityError`
- [ ] JSON 字段默认值正确（空 list → `'[]'`）
- [ ] `datetime` 字段出入库一致性

### Layer 3: 集成
- [ ] 创建 project → character → chapter_version → review_report 全链路

## 验收标准

- [ ] `pytest tests/db/ -v` 全部通过（含 Task 003 的 26 个 + 新增的 ≥ 25 个）
- [ ] `ruff check src/songyan/db/ tests/db/` 0 errors
- [ ] 所有 Repository 方法带类型标注
- [ ] 单文件不超过 400 行（超过时按领域拆模块）
- [ ] `character_states` 只有 INSERT 接口，无 UPDATE 方法
- [ ] Agent 不直接拼 SQL（验证：grep "SELECT" src/songyan/agents/ 无匹配）
- [ ] 更新了 `docs/STATUS.md`
- [ ] 生成了 `tasks/004-repository-layer-DONE.md` 交接文件

## 参考文档

- `tasks/003-sqlite-schema-DONE.md` — Schema 设计决策 + 字段映射
- `src/songyan/db/schema.sql` — 13 张表 DDL
- `src/songyan/db/connection.py` — `get_db()` 异步连接上下文管理器
- `src/songyan/models/*.py` — 35 个 Pydantic 模型字段定义
- `docs/architecture/04-vibe-coding-engineering.md` — Task 004 原始规格
