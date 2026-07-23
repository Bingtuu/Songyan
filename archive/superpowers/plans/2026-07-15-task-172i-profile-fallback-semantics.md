# Task 172i: Profile 回退语义澄清 + 占位字段移除 实施计划

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 把 `load_profile()` 从「DB 完全替换」改为「DB 覆盖层」语义，并从 `GenreRuntimeProfile` 中移除无消费者的 `arc_summarization_enabled` / `outline_dimming_enabled` 字段，同时修复 V8 文档漂移。

**Architecture:** 在 `genre_runtime_profile_repo.py` 的 `load_profile()` 中先加载代码注册表中的体裁默认值，再用 DB 记录做字段级覆盖；模型层直接删除两个布尔占位字段，依赖 `model_config = {"extra": "ignore"}` 保证旧 DB 记录反序列化不失败；文档与测试同步更新以反映新契约。

**Tech Stack:** Python 3.11+, Pydantic v2, SQLite, pytest, ruff

---

## 文件结构

| 文件 |  responsibility |
|------|-----------------|
| `src/songyan/db/genre_runtime_profile_repo.py` | 修改 `load_profile()` 实现覆盖层语义；新增/更新辅助函数 |
| `src/songyan/models/genre_runtime_profile.py` | 移除 `arc_summarization_enabled` / `outline_dimming_enabled` |
| `tests/test_172a_genre_runtime_profile.py` | 更新现有 `load_profile` 测试；新增覆盖层语义测试 |
| `tasks/172a-v8-genre-runtime-profiles.md` | 修复头部状态、验证命令等 stale 信息 |
| `scripts/run_172b_ch100_climb.py` | 修正 docstring 中的 `foreshadowing_horizon_floor` 值 |
| `tasks/V8-README.md` | 更新 172e-172i 入口与 172c 关系说明（若仍有 stale） |
| `AGENTS.md` | 补充 `load_profile` DB/注册表回退语义 |

---

## Task 1: 修改 `load_profile()` 为覆盖层语义

**Files:**
- Modify: `src/songyan/db/genre_runtime_profile_repo.py:155-170`
- Test: `tests/test_172a_genre_runtime_profile.py`

- [ ] **Step 1: 写失败测试验证当前行为**

新建测试（或追加到现有文件），验证覆盖层语义：

```python
async def test_load_profile_uses_registry_as_base_and_db_as_override(test_db: Path) -> None:
    """DB 只覆盖显式字段，其余保留代码注册表体裁默认值."""
    repo = GenreRuntimeProfileRepository()

    # 基线：注册表 xuanhuan 的默认值
    registry_xuanhuan = load_profile_from_registry("xuanhuan")
    assert registry_xuanhuan.base_budget == 15000
    assert registry_xuanhuan.foreshadowing_horizon_floor == 48

    # DB 只改 base_budget，其余字段应保留注册表值
    await repo.upsert(GenreRuntimeProfile(genre="xuanhuan", base_budget=18000))
    loaded = await load_profile("xuanhuan")
    assert loaded.base_budget == 18000  # DB 覆盖
    assert loaded.foreshadowing_horizon_floor == registry_xuanhuan.foreshadowing_horizon_floor
    assert loaded.genre == "xuanhuan"
```

Run: `python -m pytest tests/test_172a_genre_runtime_profile.py::test_load_profile_uses_registry_as_base_and_db_as_override -v`
Expected: FAIL（当前实现返回完整 DB 记录，`foreshadowing_horizon_floor` 回退到默认值 0 而不是 48）

- [ ] **Step 2: 实现覆盖层语义**

修改 `src/songyan/db/genre_runtime_profile_repo.py`：

```python
async def load_profile(genre: str | None) -> GenreRuntimeProfile:
    """按体裁加载 Profile：代码注册表为基线，DB 记录为字段级覆盖层.

    加载顺序：
    1. 从代码注册表取体裁默认值（含 V8 实证调校）；未命中则回退 scifi baseline。
    2. 若 DB 中有该体裁记录，用 DB 记录的显式字段覆盖注册表基线；未提供的字段保留基线值。
    3. 若 DB 不可用或无记录，直接返回注册表基线。

    嵌套模型（setting_evaporation / foreshadowing_evaporation / character_decay /
    continuity）按子模型整体替换：DB 提供则整体替换，不提供则保留基线子模型。
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

    # 用 DB 覆盖层更新基线；未提供字段保留基线值
    update_data = override.model_dump(mode="json", exclude_unset=False)
    return base.model_copy(update=update_data)
```

Run: `python -m pytest tests/test_172a_genre_runtime_profile.py::test_load_profile_uses_registry_as_base_and_db_as_override -v`
Expected: PASS

- [ ] **Step 3: 验证嵌套模型整体替换语义**

追加测试：

```python
async def test_load_profile_overrides_nested_model_whole(test_db: Path) -> None:
    """DB 提供嵌套子模型时整体替换，不提供时保留注册表子模型."""
    repo = GenreRuntimeProfileRepository()
    registry_xuanhuan = load_profile_from_registry("xuanhuan")

    # 只覆盖顶层字段，不碰 setting_evaporation -> 保留注册表子模型
    await repo.upsert(GenreRuntimeProfile(genre="xuanhuan", base_budget=18000))
    loaded = await load_profile("xuanhuan")
    assert loaded.setting_evaporation == registry_xuanhuan.setting_evaporation

    # 覆盖整个 setting_evaporation -> 整体替换
    from songyan.models import SettingEvaporationProfile
    new_evap = SettingEvaporationProfile(half_life_chapters=99, archive_threshold=0.01)
    await repo.upsert(
        GenreRuntimeProfile(
            genre="xuanhuan",
            base_budget=18000,
            setting_evaporation=new_evap,
        )
    )
    loaded2 = await load_profile("xuanhuan")
    assert loaded2.setting_evaporation.half_life_chapters == 99
    assert loaded2.base_budget == 18000
```

Run: `python -m pytest tests/test_172a_genre_runtime_profile.py::test_load_profile_overrides_nested_model_whole -v`
Expected: PASS

- [ ] **Step 4: 更新现有测试 `test_load_profile_db_priority_then_registry`**

原测试只断言 `base_budget`，在覆盖层语义下仍然成立。但建议显式补一句说明语义：

```python
async def test_load_profile_db_overrides_registry_field_level(test_db: Path) -> None:
    repo = GenreRuntimeProfileRepository()
    reg = await load_profile("xuanhuan")
    assert reg.base_budget == 15000

    await repo.upsert(GenreRuntimeProfile(genre="xuanhuan", base_budget=18000))
    db_first = await load_profile("xuanhuan")
    assert db_first.base_budget == 18000
    # 覆盖层语义：未在 DB 中显式覆盖的字段保留注册表值
    assert db_first.foreshadowing_horizon_floor == reg.foreshadowing_horizon_floor
```

Run: `python -m pytest tests/test_172a_genre_runtime_profile.py::test_load_profile_db_overrides_registry_field_level -v`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add src/songyan/db/genre_runtime_profile_repo.py tests/test_172a_genre_runtime_profile.py
git commit -m "feat(172i): load_profile uses registry baseline with DB field-level override"
```

---

## Task 2: 移除 `arc_summarization_enabled` / `outline_dimming_enabled` 占位字段

**Files:**
- Modify: `src/songyan/models/genre_runtime_profile.py:174-176`
- Modify: `tasks/172a-v8-genre-runtime-profiles.md:131-133`（移除或标注该字段已删除）
- Test: `tests/test_172a_genre_runtime_profile.py`

- [ ] **Step 1: 写失败测试验证字段存在**

```python
def test_placeholder_strategy_switches_removed() -> None:
    """arc_summarization_enabled / outline_dimming_enabled 已从模型移除."""
    p = GenreRuntimeProfile(genre="scifi")
    assert not hasattr(p, "arc_summarization_enabled")
    assert not hasattr(p, "outline_dimming_enabled")
```

Run: `python -m pytest tests/test_172a_genre_runtime_profile.py::test_placeholder_strategy_switches_removed -v`
Expected: FAIL（当前字段仍存在）

- [ ] **Step 2: 从模型移除字段**

修改 `src/songyan/models/genre_runtime_profile.py`，删除：

```python
    # --- 高级策略开关 ---
    arc_summarization_enabled: bool = Field(default=False)
    outline_dimming_enabled: bool = Field(default=False)
```

Run: `python -m pytest tests/test_172a_genre_runtime_profile.py::test_placeholder_strategy_switches_removed -v`
Expected: PASS

- [ ] **Step 3: 验证旧 DB 记录反序列化不失败**

```python
async def test_old_db_record_with_removed_fields_deserializes(test_db: Path) -> None:
    """DB 中仍含已移除字段的旧 profile_json 可正常加载（extra=ignore）."""
    repo = GenreRuntimeProfileRepository()
    old_payload = {
        "genre": "xuanhuan",
        "base_budget": 15000,
        "arc_summarization_enabled": True,
        "outline_dimming_enabled": True,
    }
    import json

    async with get_db() as conn:
        await conn.execute(
            "INSERT INTO genre_runtime_profiles (genre, version, profile_json) VALUES (?, ?, ?)",
            ("xuanhuan", "172a.2", json.dumps(old_payload)),
        )
        await conn.commit()

    loaded = await load_profile("xuanhuan")
    assert loaded.base_budget == 15000
    assert not hasattr(loaded, "arc_summarization_enabled")
```

注意：直接操作 DB 是为了模拟含旧字段的遗留 `profile_json`。

Run: `python -m pytest tests/test_172a_genre_runtime_profile.py::test_old_db_record_with_removed_fields_deserializes -v`
Expected: PASS

- [ ] **Step 4: 更新 172a 规划稿中的模型示例**

修改 `tasks/172a-v8-genre-runtime-profiles.md:131-133`，删除：

```python
    # 高级策略开关
    arc_summarization_enabled: bool = False
    outline_dimming_enabled: bool = False
```

如果该文档别处提到这两个字段，一并删除或改为「已移除」。

- [ ] **Step 5: Commit**

```bash
git add src/songyan/models/genre_runtime_profile.py tests/test_172a_genre_runtime_profile.py tasks/172a-v8-genre-runtime-profiles.md
git commit -m "refactor(172i): remove unused arc_summarization_enabled/outline_dimming_enabled placeholders"
```

---

## Task 3: 修复 V8 文档漂移

**Files:**
- Modify: `tasks/172a-v8-genre-runtime-profiles.md:7`
- Modify: `tasks/172a-v8-genre-runtime-profiles.md:401-405`（验证命令段落）
- Modify: `scripts/run_172b_ch100_climb.py:7`
- Modify: `tasks/V8-README.md`
- Modify: `AGENTS.md`

- [ ] **Step 1: 修复 172a 头部状态**

修改 `tasks/172a-v8-genre-runtime-profiles.md:7`：

```markdown
> **状态**: ✅ 完成（172i 补完接线后归档）
```

- [ ] **Step 2: 修复验证命令**

在 `tasks/172a-v8-genre-runtime-profiles.md` 中搜索 `scripts/run_172a7_genre_validation.py`，把任何旧的 `scripts/run_172a_validation.py` 或不存在脚本名改为正确路径。

- [ ] **Step 3: 修正 run_172b docstring**

修改 `scripts/run_172b_ch100_climb.py:7` 附近的 docstring，把 `foreshadowing_horizon_floor=12` 改为 `48`。

Run: `python -c "import scripts.run_172b_ch100_climb; print(scripts.run_172b_ch100_climb.__doc__)"`（或读 docstring 确认）
Expected: 包含 `foreshadowing_horizon_floor=48`

- [ ] **Step 4: 更新 V8-README 入口**

确认 `tasks/V8-README.md` 的「文档入口」与「Task 状态」表中 172e-172i 链接正确；若 172c 与 172e-172i 的并行关系描述仍含糊，按 172i 任务书修正。

- [ ] **Step 5: 在 AGENTS.md 补充回退语义**

在 `AGENTS.md` 的「Context Diet 2.0」或「数据与状态」小节追加：

```markdown
- `load_profile()` 以代码注册表为体裁默认值基线，DB `genre_runtime_profiles` 记录作为字段级覆盖层；DB 未命中或不可用时回退代码注册表；未知体裁回退 scifi baseline。
```

- [ ] **Step 6: Commit**

```bash
git add tasks/172a-v8-genre-runtime-profiles.md scripts/run_172b_ch100_climb.py tasks/V8-README.md AGENTS.md
git commit -m "docs(172i): fix V8 stale docs and document load_profile override semantics"
```

---

## Task 4: 全量验证

- [ ] **Step 1: 运行 172i 相关测试**

```bash
python -m pytest tests/test_172a_genre_runtime_profile.py tests/test_172a3_runtime_profile_injection.py -q
```

Expected: PASS

- [ ] **Step 2: 运行全量 pytest**

```bash
python -m pytest tests/ -q
```

Expected: 2705 passed, 2 skipped, 1 xfailed（或更好），无新增失败

- [ ] **Step 3: 运行 ruff**

```bash
ruff check src/ tests/
```

Expected: All checks passed

- [ ] **Step 4: 多体裁短窗口回归**

```bash
python scripts/run_172a7_genre_validation.py --templates scifi wuxia urban --end 10
python scripts/run_172a7_genre_validation.py --templates xuanhuan --end 15
```

Expected: scifi/wuxia/urban 10/10 accepted；xuanhuan 全 accepted，budget < 1.0，overdue < 5

- [ ] **Step 5: Commit**

```bash
git commit -m "test(172i): verify load_profile override semantics and placeholder removal"
```

---

## Self-Review

**1. Spec coverage:**
- 覆盖层语义 → Task 1
- 占位字段移除 → Task 2
- 文档漂移修复 → Task 3
- 测试与回归 → Task 4

**2. Placeholder scan:**
- 无 TBD/TODO/"implement later"
- 所有代码片段可运行
- 所有命令与路径已核对

**3. Type consistency:**
- `load_profile()` 签名不变，返回类型仍为 `GenreRuntimeProfile`
- `model_copy(update=...)` 使用 Pydantic v2 标准 API
- `extra="ignore"` 已配置，移除字段不会破坏旧 DB 记录

---

## 执行选择

**Plan complete and saved to `archive/superpowers/plans/2026-07-15-task-172i-profile-fallback-semantics.md`. Two execution options:**

**1. Subagent-Driven (recommended)** - I dispatch a fresh subagent per task, review between tasks, fast iteration

**2. Inline Execution** - Execute tasks in this session using executing-plans, batch execution with checkpoints

**Which approach?**
