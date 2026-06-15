# Task 080: 角色出场窗口 — 只加载当前 Arc 内出场角色

> **Phase**: V3.1 100章架构改造 — Phase B 质量提升
> **优先级**: P1
> **依赖**: 078（推荐先完成伏笔管理，因两者都在 ContextManager loading 路径中）
> **预计工作量**: 小（0.5-1 天）

---

## Goal

进一步收紧角色状态加载范围：只加载当前 arc 内出场过的角色完整档案，非 arc 角色只保留名称和 role_type，将角色相关 token 占用降到最低。

## Context

当前 `_build_character_snapshots()` 已基于`appeared_names`（来自 recent_summaries）过滤角色，但：

1. `appeared_names` 只覆盖最近 3 章的出场角色——这已经够好了，但 character_states 列表本身是全量的
2. 目前限制 `MAX_CHARACTER_STATES = 4`，但 Ch50 时 DB 中 character_states 表有 **183 条**记录
3. BudgetPruner 的 `_prune_character_states()` 可以裁剪到 4 条，但前期（1-4 条）已经是最低值了

本 Task 解决的不是"现在的问题"，而是**为 Ch100 做准备**——当角色池扩大到 30+ 时，仅靠 BudgetPruner 裁剪到 4 条不够，需要在数据加载层就做限制。

## In Scope

- [ ] 修改 `_build_character_snapshots()` 的逻辑：
  - 使用 `ArcBoundaryResolver`（已实现，87 行）获取当前 arc 的章节范围
  - 查询当前 arc 内所有 summaries 的 `characters_appeared`，构建 arc 级出场集
  - 全量档案只加载：arc 内出场过的角色 + protagonist
  - 非 arc 角色：只填充 `name` + `role_type`，其余字段为空
- [ ] 在 `ContextPackage` 新增 `character_states_total` 字段（DB 中总角色状态数）
- [ ] 修改 `workflows/_helpers.py` 中加载角色的路径，传入 `project.arc_boundaries` 信息
- [ ] 100 章场景的 token 估算验证

## Out of Scope

- 不修改 CharacterRepository（数据加载层逻辑在 Agent 层做）
- 不做跨 arc 角色状态同步（V3.2+ 储备）
- 不做角色重要性动态评分（V3.2+）

## 接口契约

```python
def _build_character_snapshots(
    characters: list[Character],
    character_states: list[CharacterState],
    recent_summaries: list[ChapterSummary] | None = None,
    arc_boundaries: list[tuple[int, int]] | None = None,
    current_chapter: int = 0,
) -> list[CharacterStateSnapshot]:
    """构建角色状态快照 — 按 arc 出场窗口过滤.

    Args:
        ...
        arc_boundaries: [(start, end), ...]，来自 ArcBoundaryResolver
        current_chapter: 当前章节号（用于确定所属 arc）

    Returns:
        角色快照列表
    """
```

## 数据模型

```python
# ContextPackage 新增监控字段
class ContextPackage(BaseModel):
    ...
    character_states_total: int = 0  # DB 中总角色状态数（监控用）
```

## 测试要求

- [ ] arc 边界正确确定当前章节所属 arc
- [ ] arc 内出场角色获得完整档案
- [ ] 非 arc 角色只返回 name + role_type
- [ ] 主角始终获得完整档案（无论是否在当前 arc）
- [ ] 无 arc_boundaries 时回退到当前行为（全量加载）
- [ ] pytest tests/ -x -q 通过

## 验收标准

- [ ] Ch50 场景：character_states 占用 ≤ 800 tokens（当前 ~1200）
- [ ] Ch100 模拟：即使角色池扩大到 40 人，character_states 占用 ≤ 1000 tokens
- [ ] 不修改 DB schema
- [ ] 不违反 AGENTS.md 规则
- [ ] 生成 DONE 交接报告
- [ ] 更新 STATUS.md
