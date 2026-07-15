# Task 172g: 角色归档窗口字段接线

> **阶段**: V8 后续 / V9 前置
> **类型**: 技术债清理
> **优先级**: P1
> **依赖**: V8 验收完成（172a/172b/172d 已闭合）
> **状态**: ✅ 完成

---

## 背景

V8 已经把 `character_decay.focal_gaps` 接到 `_resolve_profile_level()`，用于控制角色档案加载密度。但角色状态生命周期归档窗口（dormant / archived / functional）仍硬编码在 `CharacterStateRepository` 中：`archive_stale(window=30)`、`archive_very_stale(window=60)`、`archive_stale_functional(window=8)`。`character_decay.dormant_window`、`archive_window`、`functional_window` 当前未生效。

---

## 目标

让 `CharacterStateRepository` 的归档窗口从 `GenreRuntimeProfile.character_decay` 读取；遵守 AGENTS.md 对 `character_states` 表只 INSERT 的约束（仅 `lifecycle_status` 元数据可 UPDATE）。

---

## 文件修改清单

| 文件 | 修改内容 |
|------|----------|
| `src/songyan/db/context_repo.py` | `archive_stale` / `archive_very_stale` / `archive_stale_functional` 接收 `runtime_profile` 或窗口参数；默认从 profile 读取 |
| `src/songyan/db/lifecycle_cleaners.py` | `CharacterStateCleaner._do_archive()` 加载 `runtime_profile` 并传入 |
| `tests/test_172g_character_decay_profile_wiring.py` | 新增覆盖层语义测试 |

---

## 字段接线清单

| Profile 字段 | 当前硬编码 | 消费者 |
|---|---|---|
| `character_decay.dormant_window` | `archive_stale(window=30)` | `CharacterStateRepository.archive_stale` |
| `character_decay.archive_window` | `archive_very_stale(window=60)` | `CharacterStateRepository.archive_very_stale` |
| `character_decay.functional_window` | `archive_stale_functional(window=8)` | `CharacterStateRepository.archive_stale_functional` |

---

## 技术方案

### 1. CharacterStateRepository 归档方法接收 runtime_profile

```python
# src/songyan/db/context_repo.py
async def archive_stale(
    self,
    project_id: str,
    current_chapter: int,
    window: int | None = None,
    conn: aiosqlite.Connection | None = None,
    runtime_profile: GenreRuntimeProfile | None = None,
) -> int:
    """将未出场 window 章的非核心角色标记为 dormant.

    window 优先级：显式传入值 > profile.character_decay.dormant_window > 默认值 30。
    """
    if window is None:
        if runtime_profile is not None:
            window = runtime_profile.character_decay.dormant_window
        else:
            window = 30

    async def _do(c: aiosqlite.Connection) -> int:
        threshold = current_chapter - window
        # ... 原有 SQL 不变 ...

    # ... 原有逻辑不变 ...
```

同理修改 `archive_very_stale` 和 `archive_stale_functional`：

```python
async def archive_very_stale(
    self,
    project_id: str,
    current_chapter: int,
    window: int | None = None,
    conn: aiosqlite.Connection | None = None,
    runtime_profile: GenreRuntimeProfile | None = None,
) -> int:
    if window is None:
        if runtime_profile is not None:
            window = runtime_profile.character_decay.archive_window
        else:
            window = 60
    # ...

async def archive_stale_functional(
    self,
    project_id: str,
    current_chapter: int,
    window: int | None = None,
    conn: aiosqlite.Connection | None = None,
    runtime_profile: GenreRuntimeProfile | None = None,
) -> int:
    if window is None:
        if runtime_profile is not None:
            window = runtime_profile.character_decay.functional_window
        else:
            window = 8
    # ...
```

### 2. CharacterStateCleaner 加载 runtime_profile 并传入

```python
# src/songyan/db/lifecycle_cleaners.py
from songyan.db.genre_runtime_profile_repo import load_profile as _load_runtime_profile
from songyan.workflows._helpers import load_project as _load_project_for_cleaner

class CharacterStateCleaner(LifecycleCleaner):
    # ...

    async def _do_archive(
        self, project_id: str, current_chapter: int, conn: aiosqlite.Connection
    ) -> None:
        project = await _load_project_for_cleaner(project_id)
        runtime_profile = None
        if project is not None:
            runtime_profile = await _load_runtime_profile(project.genre_id)

        await self.repo.archive_stale(
            project_id, current_chapter, conn=conn, runtime_profile=runtime_profile
        )
        await self.repo.archive_stale_functional(
            project_id, current_chapter, conn=conn, runtime_profile=runtime_profile
        )
        await self.repo.archive_very_stale(
            project_id, current_chapter, conn=conn, runtime_profile=runtime_profile
        )
        await self.repo.archive_overflow(project_id, current_chapter, conn=conn)
```

### 3. 其他直接调用点检查

搜索 `archive_stale(`、`archive_very_stale(`、`archive_stale_functional(` 的所有调用点，确保：
- 要么显式传入 `window`；
- 要么传入 `runtime_profile`；
- 要么接受默认值（仅在旧代码兼容路径中允许）。

---

## 验证

### 测试

新建 `tests/test_172g_character_decay_profile_wiring.py`：

```python
from __future__ import annotations

import pytest

from songyan.db.context_repo import CharacterStateRepository
from songyan.db.genre_runtime_profile_repo import load_profile_from_registry
from songyan.models import CharacterDecayProfile, GenreRuntimeProfile


def _build_test_profile(**overrides) -> GenreRuntimeProfile:
    base = load_profile_from_registry("scifi")
    data = base.model_dump(mode="json")
    data.update(overrides)
    return GenreRuntimeProfile.model_validate(data)


async def test_archive_stale_uses_profile_dormant_window(test_db: Path) -> None:
    """profile 修改 dormant_window 后，archive_stale 使用的阈值变化."""
    repo = CharacterStateRepository()
    profile = _build_test_profile(
        character_decay=CharacterDecayProfile(dormant_window=5)
    )

    # 通过 monkeypatch 捕获 SQL 中使用的 threshold
    called_threshold: int | None = None
    original_execute = None

    async def spy_execute(self, sql, parameters):
        nonlocal called_threshold
        if "cv.chapter_number < ?" in sql:
            called_threshold = parameters[-1]
        return await original_execute(self, sql, parameters)

    import aiosqlite

    original_execute = aiosqlite.Connection.execute
    aiosqlite.Connection.execute = spy_execute

    try:
        await repo.archive_stale(
            project_id="test-project",
            current_chapter=100,
            runtime_profile=profile,
        )
    finally:
        aiosqlite.Connection.execute = original_execute

    assert called_threshold == 95  # 100 - 5


async def test_archive_very_stale_uses_profile_archive_window(test_db: Path) -> None:
    """profile 修改 archive_window 后，archive_very_stale 使用的阈值变化."""
    repo = CharacterStateRepository()
    profile = _build_test_profile(
        character_decay=CharacterDecayProfile(archive_window=10)
    )

    called_threshold: int | None = None
    original_execute = None

    async def spy_execute(self, sql, parameters):
        nonlocal called_threshold
        if "cv.chapter_number < ?" in sql:
            called_threshold = parameters[-1]
        return await original_execute(self, sql, parameters)

    import aiosqlite

    original_execute = aiosqlite.Connection.execute
    aiosqlite.Connection.execute = spy_execute

    try:
        await repo.archive_very_stale(
            project_id="test-project",
            current_chapter=100,
            runtime_profile=profile,
        )
    finally:
        aiosqlite.Connection.execute = original_execute

    assert called_threshold == 90  # 100 - 10


async def test_archive_stale_functional_uses_profile_functional_window(test_db: Path) -> None:
    """profile 修改 functional_window 后，archive_stale_functional 使用的阈值变化."""
    repo = CharacterStateRepository()
    profile = _build_test_profile(
        character_decay=CharacterDecayProfile(functional_window=3)
    )

    called_threshold: int | None = None
    original_execute = None

    async def spy_execute(self, sql, parameters):
        nonlocal called_threshold
        if "cv.chapter_number < ?" in sql:
            called_threshold = parameters[-1]
        return await original_execute(self, sql, parameters)

    import aiosqlite

    original_execute = aiosqlite.Connection.execute
    aiosqlite.Connection.execute = spy_execute

    try:
        await repo.archive_stale_functional(
            project_id="test-project",
            current_chapter=100,
            runtime_profile=profile,
        )
    finally:
        aiosqlite.Connection.execute = original_execute

    assert called_threshold == 97  # 100 - 3


def test_scifi_profile_defaults_equal_legacy_constants() -> None:
    """scifi profile 默认值必须与旧常量等价."""
    scifi = load_profile_from_registry("scifi")
    assert scifi.character_decay.dormant_window == 30
    assert scifi.character_decay.archive_window == 60
    assert scifi.character_decay.functional_window == 8


async def test_no_profile_falls_back_to_legacy_windows(test_db: Path) -> None:
    """无 profile 时 archive_stale 使用旧默认 30."""
    repo = CharacterStateRepository()

    called_threshold: int | None = None
    original_execute = None

    async def spy_execute(self, sql, parameters):
        nonlocal called_threshold
        if "cv.chapter_number < ?" in sql:
            called_threshold = parameters[-1]
        return await original_execute(self, sql, parameters)

    import aiosqlite

    original_execute = aiosqlite.Connection.execute
    aiosqlite.Connection.execute = spy_execute

    try:
        await repo.archive_stale(
            project_id="test-project",
            current_chapter=100,
            runtime_profile=None,
        )
    finally:
        aiosqlite.Connection.execute = original_execute

    assert called_threshold == 70  # 100 - 30
```

### 关键测试原则

- 通过拦截 SQL threshold 来验证「字段改变 → 行为改变」，而不是只看方法参数；
- scifi profile 默认值严格等价于旧常量；
- 无 profile 路径保留旧行为；
- protagonist/antagonist 不被归档的约束由原有 SQL 保证，无需重复测试。

### 回归命令

```powershell
python -m pytest tests/test_172g_character_decay_profile_wiring.py tests/test_172a6_character_decay_profile.py -q
python -m pytest tests/ -q
ruff check src/ tests/
python scripts/run_172a7_genre_validation.py --templates scifi wuxia urban --end 10
python scripts/run_172a7_genre_validation.py --templates xuanhuan --end 15
```

### 验收判据

- pytest 全绿；
- ruff 无新增错误；
- scifi/wuxia/urban `--end 10` 10/10 accepted；
- xuanhuan `--end 15` 全 accepted，budget < 1.0，overdue < 5；
- `character_states` 表没有业务字段 UPDATE（仅有 lifecycle_status UPDATE）。

---

## 出口标准

1. `archive_stale` / `archive_very_stale` / `archive_stale_functional` 从 profile 读取窗口；
2. scifi profile 默认值与 V8 验收前硬编码窗口等价；
3. 新增测试覆盖每个窗口的 "字段改变 → 行为改变"；
4. 多体裁短窗口回归通过；
5. `character_states` 表只 UPDATE `lifecycle_status`。

---

## 撞墙路由

| 风险 | 触发信号 | 处理 |
|---|---|---|
| 窗口缩短导致角色过早归档 | continuity 报告提示角色状态缺失 | 回退窗口到旧默认值，研究体裁特化值 |
| 窗口拉长导致角色状态膨胀 | budget 上升 | 评估是否需要配合 `max_character_states` 同时调整 |
| `functional_window` 与 `dormant_window` 冲突 | 功能性角色被 archive_stale 而非 archive_stale_functional 处理 | 确认 SQL 中 `goals = '[]' AND relationships = '{}'` 条件正确区分 |
| 调用点遗漏传参 | 某条调用路径仍使用硬编码 30/60/8 | 全仓库搜索 `archive_stale(` 并补传 runtime_profile |

---

## 与 172e/172f/172h/172i 的关系

- 172e 完成 ContextManager / BudgetPruner 字段接线；
- 172f 完成蒸发/伏笔排序字段接线；
- 172g 完成角色衰减窗口接线；
- 172h 完成连续性审计字段接线；
- 172i 处理跨字段的 `load_profile()` 覆盖层语义。172i 落地后，172g 的测试应补充「DB 部分覆盖时仍保留注册表默认值」的用例。
