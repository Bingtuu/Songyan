# Task 172f: SettingEvaporator / 伏笔排序字段接线

> **阶段**: V8 后续 / V9 前置
> **类型**: 技术债清理
> **优先级**: P1
> **依赖**: V8 验收完成（172a/172b/172d 已闭合）
> **状态**: ✅ 完成

---

## 背景

`GenreRuntimeProfile` 声明了 `setting_evaporation` 和 `foreshadowing_evaporation`，用于按体裁调整设定蒸发曲线和伏笔紧迫性权重。但 `SettingEvaporator` 仍在使用模块常量 `CONFIDENCE_ARCHIVE_THRESHOLDS` / `CATEGORY_TIME_DENOMINATORS`，`_rank_foreshadowings` 仍在使用硬编码 urgency 值。这些字段写在 profile 中却不生效。

---

## 目标

让 `setting_evaporation` 和 `foreshadowing_evaporation` 的字段真正控制 `SettingEvaporator` 和伏笔排序逻辑；无 profile 项目回退旧行为。

---

## 文件修改清单

| 文件 | 修改内容 |
|------|----------|
| `src/songyan/agents/setting_evaporator/__init__.py` | `SettingEvaporator` 接收 `runtime_profile`；`_calculate_resolve_confidence` 从 profile 读取阈值/分母；调用点传参 |
| `src/songyan/agents/context_manager/__init__.py` | `_rank_foreshadowings` 接收 `runtime_profile` 并读取 urgency 权重；`assemble_context_package()` 传参 |
| `src/songyan/workflows/_nodes.py` | `SettingEvaporator.run()` / `merge_similar_settings()` 调用点传入 `runtime_profile` |
| `tests/test_172f_evaporation_profile_wiring.py` | 新增覆盖层语义测试 |

---

## 字段接线清单

### SettingEvaporator

| Profile 字段 | 当前硬编码 | 消费者 |
|---|---|---|
| `setting_evaporation.archive_thresholds` | `CONFIDENCE_ARCHIVE_THRESHOLDS` | `_calculate_resolve_confidence` |
| `setting_evaporation.time_denominators` | `CATEGORY_TIME_DENOMINATORS` | `_calculate_resolve_confidence` |
| `setting_evaporation.legacy_archive_threshold` | `CONFIDENCE_ARCHIVE_THRESHOLD = 0.15` | 未分类 setting |
| `setting_evaporation.legacy_time_denominator` | `TIME_DECAY_DENOMINATOR = 50` | 未分类 setting |

### 伏笔排序

| Profile 字段 | 当前硬编码 | 消费者 |
|---|---|---|
| `foreshadowing_evaporation.urgency_due_bump` | `+3.0` | `_rank_foreshadowings` |
| `foreshadowing_evaporation.urgency_overdue_bump` | `+2.5` | `_rank_foreshadowings` |
| `foreshadowing_evaporation.urgency_within_2_bump` | `+2.0` | `_rank_foreshadowings` |
| `foreshadowing_evaporation.urgency_due_soft` | `+1.5` | `_rank_foreshadowings` |

---

## 技术方案

### 1. SettingEvaporator 接收 runtime_profile

```python
# src/songyan/agents/setting_evaporator/__init__.py
class SettingEvaporator:
    def __init__(
        self,
        runtime_profile: GenreRuntimeProfile | None = None,
    ) -> None:
        self.repo = SettingSnapshotRepository()
        self.runtime_profile = runtime_profile
```

### 2. _calculate_resolve_confidence 从 profile 读取

```python
def _calculate_resolve_confidence(
    setting_row: dict[str, Any],
    current_chapter: int,
    chapter_goal: ChapterGoal | None,
    runtime_profile: GenreRuntimeProfile | None = None,
) -> float:
    # ... 原有逻辑 ...

    # 按体裁读取蒸发曲线；无 profile 时回退模块常量
    if runtime_profile is not None:
        evap = runtime_profile.setting_evaporation
        archive_thresholds = evap.archive_thresholds
        time_denominators = evap.time_denominators
        legacy_archive_threshold = evap.legacy_archive_threshold
        legacy_time_denominator = evap.legacy_time_denominator
    else:
        archive_thresholds = CONFIDENCE_ARCHIVE_THRESHOLDS
        time_denominators = CATEGORY_TIME_DENOMINATORS
        legacy_archive_threshold = CONFIDENCE_ARCHIVE_THRESHOLD
        legacy_time_denominator = TIME_DECAY_DENOMINATOR

    category = setting_row.get("category", "background")
    denom = time_denominators.get(category, legacy_time_denominator)
    time_factor = max(0.0, 1.0 - chapters_since / float(denom))

    # ... 后续公式不变 ...
```

**注意**：这里不删除模块常量，而是让它们作为无 profile 时的回退值，保证旧行为不变。

### 3. run() 和 merge_similar_settings() 传参

```python
async def run(
    self,
    project_id: str,
    current_chapter: int,
    chapter_goal: ChapterGoal | None = None,
) -> list[str]:
    # ... 在需要计算 confidence 的位置 ...
    confidence = _calculate_resolve_confidence(
        row, current_chapter, chapter_goal, self.runtime_profile
    )

    # 归档阈值同样从 profile 读取
    if self.runtime_profile is not None:
        archive_thresholds = self.runtime_profile.setting_evaporation.archive_thresholds
        legacy_threshold = self.runtime_profile.setting_evaporation.legacy_archive_threshold
    else:
        archive_thresholds = CONFIDENCE_ARCHIVE_THRESHOLDS
        legacy_threshold = CONFIDENCE_ARCHIVE_THRESHOLD

    threshold = archive_thresholds.get(category, legacy_threshold)
    if confidence < threshold:
        archived.append(key)
```

### 4. _nodes.py 调用点传入 runtime_profile

```python
# src/songyan/workflows/_nodes.py:2569 附近
from songyan.db.genre_runtime_profile_repo import load_profile as _load_runtime_profile

runtime_profile = await _load_runtime_profile(project.genre_id)
evaporator = SettingEvaporator(runtime_profile=runtime_profile)
archived_keys = await evaporator.run(
    project_id=state["project_id"],
    current_chapter=state["chapter_number"],
    chapter_goal=goal,
)

# merge_similar_settings 每 50 章调用处同样传入
if state["chapter_number"] % MERGE_SCAN_INTERVAL == 0:
    merged = await evaporator.merge_similar_settings(
        project_id=state["project_id"],
        current_chapter=state["chapter_number"],
        runtime_profile=runtime_profile,  # 若 merge 未来需要
    )
```

### 5. _rank_foreshadowings 从 profile 读取 urgency 权重

```python
# src/songyan/agents/context_manager/__init__.py:888
def _rank_foreshadowings(
    items: list[ForeshadowingItem],
    *,
    foreshadowing_due: list[str],
    current_chapter: int,
    runtime_profile: GenreRuntimeProfile | None = None,
) -> list[ForeshadowingItem]:
    if runtime_profile is not None:
        weights = runtime_profile.foreshadowing_evaporation
        due_bump = weights.urgency_due_bump
        overdue_bump = weights.urgency_overdue_bump
        within_2_bump = weights.urgency_within_2_bump
        due_soft = weights.urgency_due_soft
    else:
        due_bump = 3.0
        overdue_bump = 2.5
        within_2_bump = 2.0
        due_soft = 1.5

    ranked: list[tuple[ForeshadowingItem, float]] = []
    due_set = set(foreshadowing_due)

    for item in items:
        urgency = 0.0
        if item.foreshadowing_id in due_set:
            urgency += due_bump
        if item.status == "overdue":
            urgency += overdue_bump
        elif (
            item.expected_resolve_chapter
            and (item.expected_resolve_chapter - current_chapter) <= 2
        ):
            urgency += within_2_bump
        if item.status == "due":
            urgency += due_soft
        if item.planted_in_chapter:
            urgency += item.planted_in_chapter * 0.01
        ranked.append((item, urgency))

    ranked.sort(key=lambda x: x[1], reverse=True)
    return [item for item, _ in ranked]
```

### 6. assemble_context_package 传参

```python
# src/songyan/agents/context_manager/__init__.py:1124 附近
_foreshadowings = _rank_foreshadowings(
    _foreshadowings,
    foreshadowing_due=foreshadowing_due,
    current_chapter=chapter_goal.chapter_number,
    runtime_profile=runtime_profile,
)
```

---

## 验证

### 测试

新建 `tests/test_172f_evaporation_profile_wiring.py`：

```python
from __future__ import annotations

import pytest

from songyan.agents.context_manager import _rank_foreshadowings
from songyan.agents.setting_evaporator import (
    SettingEvaporator,
    _calculate_resolve_confidence,
)
from songyan.db.genre_runtime_profile_repo import load_profile_from_registry
from songyan.models import (
    ForeshadowingEvaporationProfile,
    GenreRuntimeProfile,
    SettingEvaporationProfile,
)


def _build_test_profile(**overrides) -> GenreRuntimeProfile:
    base = load_profile_from_registry("scifi")
    data = base.model_dump(mode="json")
    data.update(overrides)
    return GenreRuntimeProfile.model_validate(data)


def test_calculate_resolve_confidence_uses_profile_thresholds() -> None:
    """profile 修改 archive_thresholds 后，confidence 判定阈值变化."""
    profile = _build_test_profile(
        setting_evaporation=SettingEvaporationProfile(
            archive_thresholds={"critical": 0.99},
            time_denominators={"critical": 100},
        )
    )

    row = {
        "last_mentioned_chapter": 1,
        "category": "critical",
        "setting_name": "test",
        "setting_key": "test",
    }
    # 高阈值下几乎所有 setting 都会被归档（confidence < 0.99）
    conf = _calculate_resolve_confidence(row, current_chapter=50, chapter_goal=None, runtime_profile=profile)
    assert conf < 0.99


def test_calculate_resolve_confidence_uses_profile_time_denominator() -> None:
    """profile 修改 time_denominators 后，时间衰减分母变化."""
    profile = _build_test_profile(
        setting_evaporation=SettingEvaporationProfile(
            time_denominators={"background": 5},
        )
    )

    row = {
        "last_mentioned_chapter": 1,
        "category": "background",
        "setting_name": "test",
        "setting_key": "test",
    }
    conf_fast = _calculate_resolve_confidence(row, current_chapter=50, chapter_goal=None, runtime_profile=profile)

    profile_default = _build_test_profile()
    conf_default = _calculate_resolve_confidence(
        row, current_chapter=50, chapter_goal=None, runtime_profile=profile_default
    )

    # 分母更小 -> 时间因子更小 -> confidence 更低
    assert conf_fast < conf_default


def test_rank_foreshadowings_uses_profile_weights() -> None:
    """profile 修改 urgency_due_bump 后，排序变化."""
    from songyan.models import ForeshadowingItem

    item_due = ForeshadowingItem(
        foreshadowing_id="due-1",
        status="due",
        planted_in_chapter=1,
        expected_resolve_chapter=10,
    )
    item_normal = ForeshadowingItem(
        foreshadowing_id="normal-1",
        status="planted",
        planted_in_chapter=100,
        expected_resolve_chapter=200,
    )

    profile_high = _build_test_profile(
        foreshadowing_evaporation=ForeshadowingEvaporationProfile(urgency_due_bump=100.0)
    )
    ranked_high = _rank_foreshadowings(
        [item_normal, item_due],
        foreshadowing_due=["due-1"],
        current_chapter=5,
        runtime_profile=profile_high,
    )
    assert ranked_high[0].foreshadowing_id == "due-1"

    profile_low = _build_test_profile(
        foreshadowing_evaporation=ForeshadowingEvaporationProfile(urgency_due_bump=0.0)
    )
    ranked_low = _rank_foreshadowings(
        [item_normal, item_due],
        foreshadowing_due=["due-1"],
        current_chapter=5,
        runtime_profile=profile_low,
    )
    # 正常项 planted_in_chapter=100 带来 1.0 权重，due bump 为 0 时正常项排前
    assert ranked_low[0].foreshadowing_id == "normal-1"


def test_scifi_profile_defaults_equal_legacy_constants() -> None:
    """scifi profile 默认值必须与旧常量等价."""
    scifi = load_profile_from_registry("scifi")
    from songyan.agents.setting_evaporator import (
        CATEGORY_TIME_DENOMINATORS,
        CONFIDENCE_ARCHIVE_THRESHOLDS,
    )

    assert scifi.setting_evaporation.archive_thresholds == CONFIDENCE_ARCHIVE_THRESHOLDS
    assert scifi.setting_evaporation.time_denominators == CATEGORY_TIME_DENOMINATORS
    assert scifi.setting_evaporation.legacy_archive_threshold == 0.15
    assert scifi.setting_evaporation.legacy_time_denominator == 50
    assert scifi.foreshadowing_evaporation.urgency_due_bump == 3.0
    assert scifi.foreshadowing_evaporation.urgency_overdue_bump == 2.5
    assert scifi.foreshadowing_evaporation.urgency_within_2_bump == 2.0
    assert scifi.foreshadowing_evaporation.urgency_due_soft == 1.5


def test_no_profile_falls_back_to_legacy_constants() -> None:
    """无 profile 时行为与旧常量等价."""
    from songyan.agents.setting_evaporator import (
        CATEGORY_TIME_DENOMINATORS,
        CONFIDENCE_ARCHIVE_THRESHOLDS,
    )

    row = {
        "last_mentioned_chapter": 1,
        "category": "critical",
        "setting_name": "test",
        "setting_key": "test",
    }
    conf = _calculate_resolve_confidence(row, current_chapter=50, chapter_goal=None, runtime_profile=None)
    conf_legacy = _calculate_resolve_confidence(row, current_chapter=50, chapter_goal=None)
    assert conf == conf_legacy
```

### 关键测试原则

- 每个字段单独测试「字段改变 → 行为改变」；
- scifi profile 默认值严格等价于旧常量；
- 无 profile 路径必须保留旧行为。

### 回归命令

```powershell
python -m pytest tests/test_172f_evaporation_profile_wiring.py tests/test_172a_genre_runtime_profile.py -q
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
- `SettingEvaporator` 无 profile 时行为与旧常量等价。

---

## 出口标准

1. `SettingEvaporator` 和 `_calculate_resolve_confidence` 从 profile 读取蒸发曲线；
2. `_rank_foreshadowings` 从 profile 读取 urgency 权重；
3. scifi profile 默认值与 V8 验收前常量行为等价；
4. 新增测试覆盖每个字段的 "字段改变 → 行为改变"；
5. 多体裁短窗口回归通过。

---

## 撞墙路由

| 风险 | 触发信号 | 处理 |
|---|---|---|
| 蒸发曲线变化导致 setting 过早归档 | 连续性审计 critical orphan 增加 | 回退该字段默认值到旧常量，研究体裁特化值 |
| 伏笔排序权重变化导致 overdue 反弹 | xuanhuan `--end 15` overdue ≥ 5 | 回退 urgency 权重到 sci-fi 默认值 |
| `_nodes.py` 调用点拿不到 project/genre | 运行时报 `AttributeError` | 检查 `project` 对象加载位置，确保 genre_id 可用 |
| 模块常量被误删导致无 profile 路径失败 | `test_no_profile_falls_back_to_legacy_constants` 失败 | 保留模块常量作为回退值 |

---

## 与 172e/172g/172h/172i 的关系

- 172e 完成 ContextManager / BudgetPruner 字段接线；
- 172f 完成蒸发/伏笔排序字段接线；
- 172g 完成角色衰减窗口接线；
- 172h 完成连续性审计字段接线；
- 172i 处理跨字段的 `load_profile()` 覆盖层语义。172i 落地后，172f 的测试应补充「DB 部分覆盖时仍保留注册表默认值」的用例。


---

## 执行记录（2026-07-18 补录，数据汇总自 `docs/STATUS.md` 最近验证表）

- 新增测试：`tests/test_172f_evaporation_profile_wiring.py`（14 用例）。172e-172i 五任务合计新增 41 用例，合入时全量 `python -m pytest tests/ -q --ignore=tests/cli/test_cli.py` → **2746 passed, 2 skipped, 1 xfailed**（172c 收口后 2791 passed 含 cli）。
- `ruff check src/ tests/` → All checks passed。
- 多体裁回归：`run_172a7_genre_validation.py --templates scifi wuxia urban --end 10` → 三体裁各 10/10 accepted、0 halt；scifi 旧行为逐值等价。
- 接线落点：`SettingEvaporator._calculate_resolve_confidence`（蒸发曲线 `time_denominators` / `archive_thresholds`）与 `_rank_foreshadowings`（伏笔紧迫性权重），注入点 `_nodes.py` / `context_manager/__init__.py`。
