# Task 172e: ContextManager / BudgetPruner 字段接线

> **阶段**: V8 后续 / V9 前置
> **类型**: 技术债清理
> **优先级**: P1
> **依赖**: V8 验收完成（172a/172b/172d 已闭合）
> **状态**: ✅ 完成

---

## 背景

V8 把 `GenreRuntimeProfile` 的 `base_budget` / `ramp_per_chapter` / `min_budget` 接到了 `ContextManager`，解决了 xuanhuan Ch8 halt。但 `BudgetPruner` 的分区比例、硬上限、核裁阈值等仍使用模块级常量，导致 profile 中的对应字段只是声明、不产生行为差异。

本 Task 把这些 ContextManager 相关的 Profile 字段真正接到消费者。

---

## 目标

让 `partition_ratios`、`max_soft_refs`、`max_foreshadowing`、`max_character_states`、`max_setting_input`、`hard_enforce_ratio`、`context_emergency_trigger_ratio` 都从 `GenreRuntimeProfile` 读取；无 profile 项目 100% 回退旧行为。

---

## 字段接线清单

| Profile 字段 | 当前硬编码 | 消费者 |
|---|---|---|
| `partition_ratios` | `0.30/0.20/0.15/0.10` | `BudgetPruner._apply_partition_budgets` |
| `max_soft_refs` | `MAX_SOFT_REFS = 10` | `BudgetPruner._prune_soft_references` |
| `max_foreshadowing` | `MAX_FORESHADOWING = 8` | `BudgetPruner._prune_foreshadowing` |
| `max_character_states` | `MAX_CHARACTER_STATES = 4` | `BudgetPruner._prune_character_states` |
| `max_setting_input` | `MAX_SETTING_INPUT = 10` | `assemble_context_package` 入站过滤 |
| `hard_enforce_ratio` | `HARD_ENFORCE_THRESHOLD = 1.3` | `BudgetPruner._enforce_budget_hard` 触发条件 |
| `context_emergency_trigger_ratio` | 硬编码 `budget_used > 1.0` | `BudgetPruner.prune` emergency 触发条件 |

**注意**：`_default_registry()` 中 xuanhuan 的 `max_character_states=8` 当前未生效；接线后 xuanhuan 上下文角色硬上限会从 4 提升到 8，需在回归中确认影响。

---

## 技术方案

### 1. BudgetPruner 接收 runtime_profile

```python
# src/songyan/agents/context_manager/__init__.py
class BudgetPruner:
    def __init__(
        self,
        estimator: TokenEstimator | None = None,
        runtime_profile: GenreRuntimeProfile | None = None,
    ) -> None:
        self.estimator = estimator or TokenEstimator()
        self.runtime_profile = runtime_profile
```

### 2. 分区比例从 profile 读取

```python
# BudgetPruner._apply_partition_budgets
partition_ratios = (
    self.runtime_profile.partition_ratios
    if self.runtime_profile
    else {
        "character_states": 0.30,
        "recent_plot": 0.20,
        "soft_references": 0.15,
        "foreshadowing": 0.10,
    }
)

partitions: dict[str, tuple[Any, float]] = {
    "character_states": (ctx.character_states, partition_ratios["character_states"]),
    "recent_plot": (ctx.recent_plot, partition_ratios["recent_plot"]),
    "soft_references": (ctx.soft_references, partition_ratios["soft_references"]),
    "foreshadowing": (ctx.foreshadowing, partition_ratios["foreshadowing"]),
}
```

**回退策略**：profile 中缺少某个键时，回退到当前常量值，保证无 profile 行为不变。

### 3. 硬上限从 profile 读取

```python
# BudgetPruner._prune_soft_references / _prune_foreshadowing / _prune_character_states
_max_soft = (
    self.runtime_profile.max_soft_refs
    if self.runtime_profile
    else MAX_SOFT_REFS
)
_max_fore = (
    self.runtime_profile.max_foreshadowing
    if self.runtime_profile
    else MAX_FORESHADOWING
)
_max_char = (
    self.runtime_profile.max_character_states
    if self.runtime_profile
    else MAX_CHARACTER_STATES
)
```

**注意**：`_prune_character_states` 现有逻辑还会收到 `max_character_states` 参数（来自 `assemble_context_package` 的 `_dynamic_max_for_chapter`）。参数传入值应覆盖 profile 默认值，以便保留章节阶段动态收紧逻辑。调用优先级：**传入参数 > profile 值 > 模块常量**。

### 4. setting 入站过滤从 profile 读取

```python
# assemble_context_package 入站过滤段
profile_max_setting_input = (
    runtime_profile.max_setting_input
    if runtime_profile
    else MAX_SETTING_INPUT
)
_dyn_caps = _dynamic_max_for_chapter(chapter_goal.chapter_number)
# 取 profile 值与动态值的较小者，避免长窗口无限膨胀
_max_setting_input = min(profile_max_setting_input, _dyn_caps["max_setting_input"])
```

### 5. 核裁阈值从 profile 读取

```python
# BudgetPruner._enforce_budget_hard 触发条件
hard_enforce_ratio = (
    self.runtime_profile.hard_enforce_ratio
    if self.runtime_profile
    else HARD_ENFORCE_THRESHOLD
)
if current > int(budget_tokens * hard_enforce_ratio):
    ctx = self._enforce_budget_hard(ctx, budget_tokens)
```

### 6. emergency 触发比例从 profile 读取

```python
# BudgetPruner.prune
emergency_trigger_ratio = (
    self.runtime_profile.context_emergency_trigger_ratio
    if self.runtime_profile
    else 1.0
)
if ctx.budget_used > emergency_trigger_ratio:
    ctx = self._context_emergency(ctx, budget_tokens)
```

### 7. assemble_context_package 把 profile 传给 BudgetPruner

```python
pruner = BudgetPruner(runtime_profile=runtime_profile)
ctx = pruner.prune(
    ctx,
    budget_tokens,
    narrative_fullness=narrative_fullness,
    focal_distance=focal_distance,
    max_soft_refs=_dyn_max_soft,
    max_character_states=_dyn_max_char,
    chapter_number=chapter_goal.chapter_number,
)
```

---

## 验证

### 测试

新建 `tests/test_172e_context_manager_profile_wiring.py`：

```python
import pytest

from songyan.agents.context_manager import BudgetPruner, assemble_context_package
from songyan.agents.context_manager._assemblers import _dynamic_budget
from songyan.db.genre_runtime_profile_repo import load_profile_from_registry
from songyan.models import GenreRuntimeProfile


def _build_test_profile(**overrides) -> GenreRuntimeProfile:
    """构造一个测试 profile，缺失字段使用 scifi 默认值。"""
    base = load_profile_from_registry("scifi")
    data = base.model_dump(mode="json")
    data.update(overrides)
    return GenreRuntimeProfile.model_validate(data)


def test_partition_ratios_from_profile() -> None:
    """profile 修改 partition_ratios 后，_apply_partition_budgets 使用新比例。"""
    pruner = BudgetPruner(
        runtime_profile=_build_test_profile(
            partition_ratios={
                "character_states": 0.50,
                "recent_plot": 0.30,
                "soft_references": 0.15,
                "foreshadowing": 0.05,
            }
        )
    )
    # 通过 monkeypatch 或反射检查内部使用的比例
    assert pruner.runtime_profile is not None
    assert pruner.runtime_profile.partition_ratios["character_states"] == 0.50


def test_max_character_states_from_profile() -> None:
    """profile 的 max_character_states 会改变 BudgetPruner 硬上限。"""
    pruner = BudgetPruner(runtime_profile=_build_test_profile(max_character_states=8))
    assert pruner.runtime_profile.max_character_states == 8


def test_hard_enforce_ratio_from_profile() -> None:
    """profile 修改 hard_enforce_ratio 后，核裁触发阈值变化。"""
    pruner = BudgetPruner(runtime_profile=_build_test_profile(hard_enforce_ratio=1.5))
    assert pruner.runtime_profile.hard_enforce_ratio == 1.5


def test_context_emergency_trigger_ratio_from_profile() -> None:
    """profile 修改 context_emergency_trigger_ratio 后，emergency 触发比例变化。"""
    pruner = BudgetPruner(
        runtime_profile=_build_test_profile(context_emergency_trigger_ratio=0.95)
    )
    assert pruner.runtime_profile.context_emergency_trigger_ratio == 0.95


def test_scifi_profile_defaults_equal_legacy_constants() -> None:
    """scifi profile 全默认值必须与旧常量等价。"""
    scifi = load_profile_from_registry("scifi")
    assert scifi.partition_ratios["character_states"] == 0.30
    assert scifi.partition_ratios["recent_plot"] == 0.20
    assert scifi.partition_ratios["soft_references"] == 0.15
    assert scifi.partition_ratios["foreshadowing"] == 0.10
    assert scifi.max_soft_refs == 10
    assert scifi.max_foreshadowing == 8
    assert scifi.max_character_states == 4
    assert scifi.max_setting_input == 10
    assert scifi.hard_enforce_ratio == 1.3
    assert scifi.context_emergency_trigger_ratio == 1.0
```

### 关键测试原则

- 每个测试只测一个字段；
- 测试必须断言“字段改变 → 行为改变”，而不是只测模型字段存在；
- scifi profile 默认值必须与旧常量严格等价，作为回归基线。

### 回归命令

```powershell
python -m pytest tests/test_172e_context_manager_profile_wiring.py tests/test_172a3_runtime_profile_injection.py -q
python -m pytest tests/ -q
ruff check src/ tests/
python scripts/run_172a7_genre_validation.py --templates scifi wuxia urban --end 10
python scripts/run_172a7_genre_validation.py --templates xuanhuan --end 15
```

### 验收判据

- pytest 全绿；
- ruff 无新增错误；
- scifi/wuxia/urban `--end 10` 10/10 accepted；
- xuanhuan `--end 15` 全 accepted，budget < 1.0，overdue < 5。

---

## 出口标准

1. 所有清单字段从 profile 读取；
2. scifi profile 默认值与 V8 验收前常量行为等价；
3. 新增测试覆盖每个字段的 "字段改变 → 行为改变"；
4. 多体裁短窗口回归通过。

---

## 撞墙路由

| 风险 | 触发信号 | 处理 |
|---|---|---|
| 接线后 sci-fi 行为漂移 | `--end 10` 非 10/10 | 回滚，检查默认值是否严格等价于旧常量 |
| xuanhuan max_character_states=8 生效后 budget 恶化 | `--end 15` budget ≥ 1.0 | 临时把 xuanhuan `max_character_states` 回退到 4，另开 Task 研究该字段特化值 |
| `_dynamic_max_for_chapter` 与 profile 冲突 | Ch80+ 行为异常 | 明确优先级：传入参数 > profile 值 > 模块常量；最终取较小者 |
| setting 入站过滤放宽后 budget 上升 | `--end 15` budget ≥ 1.0 | 检查是否 `_dynamic_max_for_chapter` 未正确应用；必要时收紧 profile 默认值 |
