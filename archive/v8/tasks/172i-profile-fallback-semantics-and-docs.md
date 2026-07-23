# Task 172i: Profile 回退语义澄清 + 占位字段移除 + V8 文档修复

> **阶段**: V8 后续 / V9 前置
> **类型**: 技术债清理 / 文档治理
> **优先级**: P1
> **依赖**: V8 验收完成（172a/172b/172d 已闭合）
> **状态**: ✅ 完成
> **实施计划**: `archive/superpowers/plans/2026-07-15-task-172i-profile-fallback-semantics.md`

---

## 背景

V8 实现了 `load_profile()` 的加载链：`DB → 代码注册表 → scifi`。但 DB 记录与代码注册表的语义未明确：当前 DB 记录会**完整替换**代码注册表条目。这意味着如果 DB 中只存了 `base_budget`，其他字段会回退到 scifi 默认值，而不是保留代码注册表中该体裁的调校值。

同时，`GenreRuntimeProfile` 中声明了 `arc_summarization_enabled` / `outline_dimming_enabled` 两个「高级策略开关」，但全仓库无消费者，也无 V9 imminent 需求，造成契约空心化。

V8 文档中还有少量 stale 信息：172a 任务头部状态、验证命令、run_172b docstring 中的 floor 值等。

---

## 目标

1. 把 `load_profile()` 从「DB 完全替换」改为「代码注册表基线 + DB 字段级覆盖层」语义；
2. 从 `GenreRuntimeProfile` 模型中移除 `arc_summarization_enabled` / `outline_dimming_enabled`；
3. 修复 V8 文档漂移，并在 `AGENTS.md` 中显式文档化回退语义。

---

## 文件修改清单

| 文件 | 修改内容 |
|------|----------|
| `src/songyan/db/genre_runtime_profile_repo.py` | 重写 `load_profile()` 为覆盖层语义；更新模块 docstring |
| `src/songyan/models/genre_runtime_profile.py` | 移除两个占位字段 |
| `tests/test_172a_genre_runtime_profile.py` | 更新/新增覆盖层语义测试、占位字段移除测试、旧 DB 记录兼容测试 |
| `tasks/172a-v8-genre-runtime-profiles.md` | 修复头部状态、验证命令、模型示例中的占位字段 |
| `scripts/run_172b_ch100_climb.py` | 修正 docstring 中的 `foreshadowing_horizon_floor` 值 |
| `tasks/V8-README.md` | 确认 172e-172i 入口与 172c 关系说明无 stale |
| `AGENTS.md` | 补充 `load_profile` DB/注册表回退语义 |

---

## 技术方案

### 1. `load_profile()` 覆盖层语义

```python
# src/songyan/db/genre_runtime_profile_repo.py
async def load_profile(genre: str | None) -> GenreRuntimeProfile:
    """按体裁加载 Profile：代码注册表为基线，DB 记录为字段级覆盖层.

    加载顺序与语义：
    1. 先从代码注册表取体裁默认值（含 V8 实证调校）；未知体裁回退 scifi baseline。
    2. 若 DB 中有该体裁记录，用 DB 记录的显式字段覆盖注册表基线；未提供的字段
       保留基线值。
    3. 若 DB 不可用或无记录，直接返回注册表基线。

    嵌套模型（setting_evaporation / foreshadowing_evaporation / character_decay /
    continuity）按子模型整体替换：DB 提供则整体替换，不提供则保留基线子模型，
    不细粒度合并子模型内部键，避免歧义。
    """
    key = (genre or "").strip().lower()
    base = load_profile_from_registry(key)

    if not key:
        return base

    try:
        repo = GenreRuntimeProfileRepository()
        override = await repo.get(key)
    except Exception as exc:  # noqa: BLE001 - DB 不可用时回退基线，不阻断生成
        logger.warning(
            "genre_runtime_profile.db_load_failed",
            genre=key,
            error=str(exc),
        )
        return base

    if override is None:
        return base

    # 字段级覆盖：DB 中异于模型默认值的字段视为显式覆盖，覆盖注册表基线；
    # 与默认值相同的字段视为未显式覆盖，保留注册表基线。
    # 嵌套子模型按整体替换：DB 提供且异于默认时替换整个子模型，否则保留基线子模型。
    base_data = base.model_dump(mode="json")
    override_data = override.model_dump(mode="json")
    default_for_genre = GenreRuntimeProfile(genre=override.genre)
    default_data = default_for_genre.model_dump(mode="json")
    diff = {
        k: v
        for k, v in override_data.items()
        if k != "genre" and v != default_data.get(k)
    }
    merged = {**base_data, **diff}
    return GenreRuntimeProfile.model_validate(merged)
```

**关键行为**：
- DB 为空/无记录 → 返回注册表基线（与现在一致）；
- DB 只改 `base_budget` → 其他字段保留代码注册表的 xuanhuan 调校值；
- DB 完整写一遍且字段异于模型默认值 → 等效于完全替换；
- DB 提供 `setting_evaporation` 且异于默认 → 整体替换基线子模型，不合并内部键；
- DB 异常 → 回退注册表基线，不阻断生成。

### 2. 移除占位字段

```python
# src/songyan/models/genre_runtime_profile.py
# 删除以下整块：
#     # --- 高级策略开关 ---
#     arc_summarization_enabled: bool = Field(default=False)
#     outline_dimming_enabled: bool = Field(default=False)
```

由于模型已配置 `model_config = {"extra": "ignore"}`，DB 中遗留的 `profile_json` 即使包含这两个字段，反序列化时也不会报错。

### 3. 文档修复

| 文件 | 修复项 |
|------|--------|
| `tasks/172a-v8-genre-runtime-profiles.md:7` | 头部状态改为 “✅ 完成（172i 补完接线后归档）” |
| `tasks/172a-v8-genre-runtime-profiles.md:131-133` | 删除模型示例中的 `arc_summarization_enabled` / `outline_dimming_enabled` |
| `tasks/172a-v8-genre-runtime-profiles.md` | 把任何旧验证命令名改为实际存在的 `scripts/run_172a7_genre_validation.py` |
| `scripts/run_172b_ch100_climb.py:7` | docstring 中的 `foreshadowing_horizon_floor=12` 改为 `48` |
| `tasks/V8-README.md` | 确认 172e-172i 入口与 172c 关系说明准确 |
| `AGENTS.md` | 在「Context Diet 2.0」或「数据与状态」小节补充：`load_profile()` 以代码注册表为体裁默认值基线，DB 记录作为字段级覆盖层；DB 未命中/不可用时回退代码注册表；未知体裁回退 scifi baseline |

---

## 验证

### 测试

修改 `tests/test_172a_genre_runtime_profile.py`，新增/更新以下测试：

```python
import json

import pytest

from songyan.db.connection import get_db
from songyan.db.genre_runtime_profile_repo import (
    FALLBACK_GENRE,
    GenreRuntimeProfileRepository,
    load_profile,
    load_profile_from_registry,
)
from songyan.models import GenreRuntimeProfile, SettingEvaporationProfile


async def test_load_profile_uses_registry_as_base_and_db_as_override(test_db: Path) -> None:
    """DB 只覆盖显式字段，其余保留代码注册表体裁默认值."""
    repo = GenreRuntimeProfileRepository()
    registry_xuanhuan = load_profile_from_registry("xuanhuan")
    assert registry_xuanhuan.foreshadowing_horizon_floor == 48

    await repo.upsert(GenreRuntimeProfile(genre="xuanhuan", base_budget=18000))
    loaded = await load_profile("xuanhuan")

    assert loaded.base_budget == 18000  # DB 覆盖
    assert loaded.foreshadowing_horizon_floor == registry_xuanhuan.foreshadowing_horizon_floor
    assert loaded.genre == "xuanhuan"


async def test_load_profile_overrides_nested_model_whole(test_db: Path) -> None:
    """DB 提供嵌套子模型时整体替换，不提供时保留注册表子模型."""
    repo = GenreRuntimeProfileRepository()
    registry_xuanhuan = load_profile_from_registry("xuanhuan")

    # 只覆盖顶层字段，不碰 setting_evaporation -> 保留注册表子模型
    await repo.upsert(GenreRuntimeProfile(genre="xuanhuan", base_budget=18000))
    loaded = await load_profile("xuanhuan")
    assert loaded.setting_evaporation == registry_xuanhuan.setting_evaporation

    # 覆盖整个 setting_evaporation -> 整体替换
    new_evap = SettingEvaporationProfile(
        legacy_archive_threshold=0.01, legacy_time_denominator=99
    )
    await repo.upsert(
        GenreRuntimeProfile(
            genre="xuanhuan",
            base_budget=18000,
            setting_evaporation=new_evap,
        )
    )
    loaded2 = await load_profile("xuanhuan")
    assert loaded2.setting_evaporation.legacy_time_denominator == 99
    assert loaded2.setting_evaporation.legacy_archive_threshold == 0.01
    assert loaded2.base_budget == 18000


async def test_load_profile_db_unavailable_falls_back_to_registry(test_db: Path) -> None:
    """DB 异常时回退注册表基线，不阻断生成."""
    # 该测试可通过 monkeypatch GenreRuntimeProfileRepository.get 抛异常实现
    from unittest.mock import AsyncMock, patch

    with patch.object(
        GenreRuntimeProfileRepository,
        "get",
        new_callable=AsyncMock,
        side_effect=RuntimeError("db down"),
    ):
        loaded = await load_profile("xuanhuan")

    assert loaded.genre == "xuanhuan"
    assert loaded.base_budget == load_profile_from_registry("xuanhuan").base_budget


def test_placeholder_strategy_switches_removed() -> None:
    """arc_summarization_enabled / outline_dimming_enabled 已从模型移除."""
    p = GenreRuntimeProfile(genre="scifi")
    assert not hasattr(p, "arc_summarization_enabled")
    assert not hasattr(p, "outline_dimming_enabled")


async def test_old_db_record_with_removed_fields_deserializes(test_db: Path) -> None:
    """DB 中仍含已移除字段的旧 profile_json 可正常加载（extra=ignore）."""
    old_payload = {
        "genre": "xuanhuan",
        "base_budget": 15000,
        "arc_summarization_enabled": True,
        "outline_dimming_enabled": True,
    }
    async with get_db() as conn:
        await conn.execute(
            "INSERT INTO genre_runtime_profiles (genre, version, profile_json) VALUES (?, ?, ?)",
            ("xuanhuan", "172a.2", json.dumps(old_payload)),
        )
        await conn.commit()

    loaded = await load_profile("xuanhuan")
    assert loaded.base_budget == 15000
    assert not hasattr(loaded, "arc_summarization_enabled")
    assert not hasattr(loaded, "outline_dimming_enabled")
```

### 关键测试原则

- 每个测试只验证一个语义点；
- 覆盖层测试必须断言「未覆盖字段保留注册表值」，而不是只测 DB 值；
- 嵌套模型测试明确「整体替换」语义；
- 移除字段测试必须验证旧 DB 记录仍能反序列化。

### 回归命令

```powershell
python -m pytest tests/test_172a_genre_runtime_profile.py tests/test_172a3_runtime_profile_injection.py -q
python -m pytest tests/ -q
ruff check src/ tests/
python scripts/run_172a7_genre_validation.py --templates scifi wuxia urban --end 10
python scripts/run_172a7_genre_validation.py --templates xuanhuan --end 15
```

### 验收判据

- `load_profile()` 以注册表为基线、DB 为字段级覆盖层；
- 未知体裁 / DB 不可用 / DB 无记录时均回退到合适基线；
- `GenreRuntimeProfile` 不再包含 `arc_summarization_enabled` / `outline_dimming_enabled`；
- 旧 DB 记录（含已移除字段）反序列化不失败；
- pytest 全绿；ruff 无新增错误；
- 多体裁短窗口回归不劣化。

---

## 出口标准

1. `load_profile()` 覆盖层语义已实现、测试覆盖、文档化；
2. `arc_summarization_enabled` / `outline_dimming_enabled` 已从模型与文档中移除；
3. V8 文档漂移已清除；
4. `AGENTS.md` 已补充回退语义；
5. 全量 pytest/ruff/短窗口回归通过。

---

## 撞墙路由

| 风险 | 触发信号 | 处理 |
|---|---|---|
| 覆盖层语义改变现有 DB 行为 | 现有项目加载异常或回归失败 | 回滚到完全替换语义，或提供 migration 把现有 DB 记录补全为覆盖层期望形态 |
| `model_copy(update=...)` 对嵌套模型行为不符预期 | 嵌套模型测试失败 | 改用 `base.model_copy(update=override.model_dump(mode="json"))` 已可整体替换；若需细粒度合并则重新设计 |
| 移除占位字段影响其他序列化路径 | 全量 pytest 出现 `ValidationError` | 检查是否有序列化代码显式访问这两个字段；`extra="ignore"` 应已覆盖 |
| 旧 DB 记录反序列化失败 | `test_old_db_record_with_removed_fields_deserializes` 失败 | 确认 `model_config` 仍为 `{"extra": "ignore"}` |
| GateConfig 时序重构需求 | 未来每新增一个 profile 化阈值都要写覆盖逻辑 | 单独开 172i.p 定点重构 `cli/main.py:521` 的 `GateConfig` 构建时序 |

---

## 与 172e/172f/172g/172h 的关系

- 172e-172h 各自完成字段接线；
- 172i 处理跨字段的加载语义和文档问题，可与 172e-172h 并行；
- 172i 落地后，172e-172h 的测试应补充「DB 部分覆盖时仍保留注册表默认值」的用例，确保字段默认值不被 scifi baseline 污染。


---

## 执行记录（2026-07-18 补录，数据汇总自 `docs/STATUS.md` 最近验证表）

- 新增测试：并入 `tests/test_172a_genre_runtime_profile.py`（现 22 用例，其中本 Task 新增 5；172e-172i 五任务合计 41 = 12+14+5+5+5）。
- 合入时全量 `python -m pytest tests/ -q --ignore=tests/cli/test_cli.py` → **2746 passed, 2 skipped, 1 xfailed**（172c 收口后 2791 passed 含 cli）；`ruff check src/ tests/` → All checks passed。
- 落地内容：`load_profile()` 语义定为注册表基线 + DB 字段级覆盖层（未知体裁回退 scifi baseline；嵌套子模型整体替换）；占位字段 `arc_summarization_enabled` / `outline_dimming_enabled` 已从模型删除；V8-README 注入点与回退语义段落同步修复。
- 已知边界（2026-07-18 review 确认）：DB 存全量 `profile_json`，覆盖以代码默认值为 diff 基准，**无法把注册表调优值降回代码默认**；该边界的文档化收口归 **172j**。
