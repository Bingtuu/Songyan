# Task 172h: 连续性审计字段接线 + 消除重复常量

> **阶段**: V8 后续 / V9 前置
> **类型**: 技术债清理
> **优先级**: P1
> **依赖**: V8 验收完成（172a/172b/172d 已闭合）
> **状态**: ✅ 完成

---

## 背景

`GenreRuntimeProfile` 声明了 `continuity` 字段（`orphaned_thresholds`、`forgotten_threshold`、`state_mismatch_window`、`mismatch_tolerance`），但 `ContinuityAuditor` 和 `_scanners.py` 仍在使用模块级常量。同时这些常量还在 `continuity_auditor/__init__.py` 中重复定义，形成维护风险。

---

## 目标

1. 让连续性审计阈值从 `GenreRuntimeProfile.continuity` 读取；
2. 消除 `ORPHANED_THRESHOLDS` / `FORGOTTEN_THRESHOLD` / `STATE_MISMATCH_WINDOW` 的重复定义；
3. 无 profile 项目回退旧行为。

---

## 文件修改清单

| 文件 | 修改内容 |
|------|----------|
| `src/songyan/agents/continuity_auditor/_scanners.py` | `_find_orphaned_settings` / `_find_forgotten_items` / `_find_state_mismatches` 接收 `runtime_profile` 并读取阈值 |
| `src/songyan/agents/continuity_auditor/__init__.py` | `ContinuityAuditor.__init__` / `audit()` 接收 `runtime_profile`；删除类属性 `FORGOTTEN_THRESHOLD` / `STATE_MISMATCH_WINDOW` |
| `src/songyan/workflows/phase2_graph.py` | `ContinuityAuditor()` 构造时传入 `runtime_profile` |
| `tests/test_172h_continuity_profile_wiring.py` | 新增覆盖层语义测试 |

---

## 字段接线清单

| Profile 字段 | 当前硬编码 | 消费者 |
|---|---|---|
| `continuity.orphaned_thresholds` | `ORPHANED_THRESHOLDS` | `_find_orphaned_settings` |
| `continuity.forgotten_threshold` | `FORGOTTEN_THRESHOLD = 3` | `_find_forgotten_items` |
| `continuity.state_mismatch_window` | `STATE_MISMATCH_WINDOW = 2` | `_find_state_mismatches` |
| `continuity.mismatch_tolerance` | 当前汇总逻辑未使用 | 172h 中确认是否接入或从模型移除 |

---

## 技术方案

### 1. _scanners.py 函数接收 runtime_profile

```python
# src/songyan/agents/continuity_auditor/_scanners.py
async def _find_orphaned_settings(
    project_id: str,
    up_to_chapter: int,
    setting_repo: SettingTrackingRepository,
    runtime_profile: GenreRuntimeProfile | None = None,
) -> list[OrphanedSetting]:
    """按类别阈值找出 last_mentioned_chapter 距离当前过远的 setting."""
    if runtime_profile is not None:
        thresholds = runtime_profile.continuity.orphaned_thresholds
    else:
        thresholds = ORPHANED_THRESHOLDS

    # ... 后续用 thresholds.items() 替代 ORPHANED_THRESHOLDS.items() ...


async def _find_forgotten_items(
    project_id: str,
    up_to_chapter: int,
    inventory_repo: InventoryTrackerRepository,
    runtime_profile: GenreRuntimeProfile | None = None,
) -> list[ForgottenItem]:
    """找出 last_used_chapter 距离当前超过阈值的物品."""
    if runtime_profile is not None:
        threshold = runtime_profile.continuity.forgotten_threshold
    else:
        threshold = FORGOTTEN_THRESHOLD

    # ... 后续用 threshold 替代 FORGOTTEN_THRESHOLD ...


async def _find_state_mismatches(
    project_id: str,
    up_to_chapter: int,
    runtime_profile: GenreRuntimeProfile | None = None,
) -> list[StateMismatch]:
    """检测角色状态在短时间内剧烈变化."""
    if runtime_profile is not None:
        window = runtime_profile.continuity.state_mismatch_window
    else:
        window = STATE_MISMATCH_WINDOW

    # ... 后续用 window 替代 STATE_MISMATCH_WINDOW ...
```

### 2. ContinuityAuditor 接收 runtime_profile

```python
# src/songyan/agents/continuity_auditor/__init__.py
class ContinuityAuditor:
    """跨章一致性审计器."""

    # 删除以下类属性（单一事实源迁移到 _scanners.py 和 profile）
    # FORGOTTEN_THRESHOLD = 3
    # STATE_MISMATCH_WINDOW = 2

    def __init__(
        self,
        runtime_profile: GenreRuntimeProfile | None = None,
    ) -> None:
        self.runtime_profile = runtime_profile
        self.setting_repo = SettingTrackingRepository()
        self.inventory_repo = InventoryTrackerRepository()
        self.location_repo = LocationTrackerRepository()
        self.foreshadowing_repo = ForeshadowingRepository()
        self.report_repo = ContinuityReportRepository()

    async def audit(self, project_id: str, up_to_chapter: int) -> ContinuityReport:
        # ...
        orphaned = await _find_orphaned_settings(
            project_id, up_to_chapter, self.setting_repo, self.runtime_profile
        )
        forgotten = await _find_forgotten_items(
            project_id, up_to_chapter, self.inventory_repo, self.runtime_profile
        )
        mismatches = await _find_state_mismatches(
            project_id, up_to_chapter, self.runtime_profile
        )
        # ...
```

### 3. phase2_graph.py 调用点传入 runtime_profile

```python
# src/songyan/workflows/phase2_graph.py:1137 附近
from songyan.db.genre_runtime_profile_repo import load_profile as _load_runtime_profile
from songyan.workflows._helpers import load_project as _load_project_for_audit

if chapter_number % 3 == 0:
    project_for_audit = await _load_project_for_audit(project_id)
    runtime_profile = None
    if project_for_audit is not None:
        runtime_profile = await _load_runtime_profile(project_for_audit.genre_id)

    auditor = ContinuityAuditor(runtime_profile=runtime_profile)
    report = await auditor.audit(
        project_id=project_id,
        up_to_chapter=chapter_number,
    )
```

### 4. 消除重复常量

- 保留 `src/songyan/agents/continuity_auditor/_scanners.py` 中的模块级常量作为**无 profile 时的回退值**；
- 删除 `src/songyan/agents/continuity_auditor/__init__.py` 中的 `FORGOTTEN_THRESHOLD` / `STATE_MISMATCH_WINDOW` 类属性；
- 如果其他文件从 `ContinuityAuditor.FORGOTTEN_THRESHOLD` 或 `ContinuityAuditor.STATE_MISMATCH_WINDOW` 读取，改为从 `_scanners` 导入或直接从 profile 读取。

### 5. mismatch_tolerance 处理

`continuity.mismatch_tolerance` 当前在代码中无消费者。172h 中建议：
- **方案 A（推荐）**：从 `ContinuityToleranceProfile` 中移除该字段，减少占位；
- **方案 B**：保留并标注为「预留字段，未接线」。

若选择方案 A，同步修改：
- `src/songyan/models/genre_runtime_profile.py` 中的 `ContinuityToleranceProfile`；
- `tasks/172a-v8-genre-runtime-profiles.md` 中的模型示例；
- `tasks/V8-README.md` 中对该字段的描述。

---

## 验证

### 测试

新建 `tests/test_172h_continuity_profile_wiring.py`：

```python
from __future__ import annotations

import pytest

from songyan.agents.continuity_auditor import ContinuityAuditor
from songyan.agents.continuity_auditor._scanners import (
    FORGOTTEN_THRESHOLD,
    ORPHANED_THRESHOLDS,
    STATE_MISMATCH_WINDOW,
    _find_forgotten_items,
    _find_orphaned_settings,
    _find_state_mismatches,
)
from songyan.db.genre_runtime_profile_repo import load_profile_from_registry
from songyan.models import ContinuityToleranceProfile, GenreRuntimeProfile


def _build_test_profile(**overrides) -> GenreRuntimeProfile:
    base = load_profile_from_registry("scifi")
    data = base.model_dump(mode="json")
    data.update(overrides)
    return GenreRuntimeProfile.model_validate(data)


def test_auditor_no_longer_defines_duplicate_constants() -> None:
    """__init__.py 不应再定义 FORGOTTEN_THRESHOLD / STATE_MISMATCH_WINDOW 类属性."""
    assert not hasattr(ContinuityAuditor, "FORGOTTEN_THRESHOLD")
    assert not hasattr(ContinuityAuditor, "STATE_MISMATCH_WINDOW")


async def test_find_orphaned_settings_uses_profile_thresholds(monkeypatch) -> None:
    """profile 修改 orphaned_thresholds 后，使用的阈值变化."""
    from unittest.mock import AsyncMock

    profile = _build_test_profile(
        continuity=ContinuityToleranceProfile(
            orphaned_thresholds={"critical": 99}
        )
    )

    called_thresholds: list[int] = []
    repo_mock = AsyncMock()
    repo_mock.active_setting_mark_keys = AsyncMock(return_value=set())
    repo_mock.find_orphaned = AsyncMock(return_value=[])

    async def capture_find_orphaned(*args, **kwargs):
        called_thresholds.append(kwargs["threshold"])
        return []

    repo_mock.find_orphaned = capture_find_orphaned

    await _find_orphaned_settings(
        "proj", 100, repo_mock, runtime_profile=profile
    )

    assert 99 in called_thresholds


async def test_find_forgotten_items_uses_profile_threshold(monkeypatch) -> None:
    """profile 修改 forgotten_threshold 后，判断 forgotten 的窗口变化."""
    profile = _build_test_profile(
        continuity=ContinuityToleranceProfile(forgotten_threshold=10)
    )

    rows = [
        {
            "status": "held",
            "last_used_chapter": 1,
            "acquired_in_chapter": 1,
            "track_id": "t1",
            "character_id": "c1",
            "item_name": "item",
        }
    ]
    repo_mock = type("Repo", (), {"list_by_project": lambda self, pid: rows})()

    result = await _find_forgotten_items(
        "proj", 100, repo_mock, runtime_profile=profile
    )
    assert len(result) == 1  # 100 - 1 = 99 >= 10

    result_default = await _find_forgotten_items(
        "proj", 4, repo_mock, runtime_profile=profile
    )
    assert len(result_default) == 0  # 4 - 1 = 3 < 10


def test_scifi_profile_defaults_equal_legacy_constants() -> None:
    """scifi profile 默认值必须与旧常量等价."""
    scifi = load_profile_from_registry("scifi")
    assert scifi.continuity.orphaned_thresholds == ORPHANED_THRESHOLDS
    assert scifi.continuity.forgotten_threshold == FORGOTTEN_THRESHOLD
    assert scifi.continuity.state_mismatch_window == STATE_MISMATCH_WINDOW


async def test_no_profile_falls_back_to_legacy_constants(monkeypatch) -> None:
    """无 profile 时 _find_orphaned_settings 使用旧常量."""
    from unittest.mock import AsyncMock

    repo_mock = AsyncMock()
    repo_mock.active_setting_mark_keys = AsyncMock(return_value=set())
    called_categories: list[str] = []

    async def capture_find_orphaned(*args, **kwargs):
        called_categories.extend(kwargs["categories"])
        return []

    repo_mock.find_orphaned = capture_find_orphaned

    await _find_orphaned_settings("proj", 100, repo_mock, runtime_profile=None)

    assert set(called_categories) == set(ORPHANED_THRESHOLDS.keys())
```

### 关键测试原则

- 每个阈值单独测试「字段改变 → 行为改变」；
- 断言 `ContinuityAuditor` 不再持有重复常量；
- scifi profile 默认值严格等价于旧常量；
- 无 profile 路径保留旧行为。

### 回归命令

```powershell
python -m pytest tests/test_172h_continuity_profile_wiring.py tests/test_172a_genre_runtime_profile.py -q
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
- `_helpers.py` / `creative_director/__init__.py` 导入路径仍可工作；
- 重复常量已消除。

---

## 出口标准

1. 连续性审计阈值从 profile 读取；
2. `continuity_auditor/__init__.py` 不再定义重复常量；
3. `ORPHANED_THRESHOLDS` / `FORGOTTEN_THRESHOLD` / `STATE_MISMATCH_WINDOW` 单一事实源在 `_scanners.py`（作为无 profile 回退）；
4. scifi profile 默认值与旧常量等价；
5. 新增测试覆盖行为变化；
6. 多体裁短窗口回归通过。

---

## 撞墙路由

| 风险 | 触发信号 | 处理 |
|---|---|---|
| 阈值变化导致假 orphan/mismatch 增加 | `--end 15` health 下降或 halt 增多 | 回退该字段默认值到旧常量，研究体裁特化值 |
| 删除 `__init__.py` 常量导致外部导入失败 | 测试/CLI 报错 | 保留从 `_scanners` 的兼容导入，不改外部接口 |
| `mismatch_tolerance` 移除影响序列化 | DB 中旧 profile_json 仍含该字段 | `model_config = {"extra": "ignore"}` 已处理 |
| phase2_graph 调用点拿不到 project/genre | 运行时报 `AttributeError` | 检查 `project` 对象加载位置，确保 genre_id 可用 |

---

## 与 172e/172f/172g/172i 的关系

- 172e 完成 ContextManager / BudgetPruner 字段接线；
- 172f 完成蒸发/伏笔排序字段接线；
- 172g 完成角色衰减窗口接线；
- 172h 完成连续性审计字段接线；
- 172i 处理跨字段的 `load_profile()` 覆盖层语义。172i 落地后，172h 的测试应补充「DB 部分覆盖时仍保留注册表默认值」的用例。
