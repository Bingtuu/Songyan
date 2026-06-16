# Task 108: CharacterLifecycleAuditor — 角色退场机制

> **状态**: 完成
> **完成日期**: 2026-06-14
> **Phase**: V5.0 Phase 3 — 活跃信息池控制

---

## 做了什么

### 核心修改

将 `character_states` 生命周期清理策略从"5 章即 dormant"的旧策略升级为适配 150 章长尺度的三阶段策略，并引入活跃角色数量硬上限。

#### 1. 调整时间窗口与核心角色保护

**文件**: `src/songyan/db/context_repo.py`

| 方法 | 旧默认 | 新默认 | 保护角色 |
|------|--------|--------|----------|
| `archive_stale` | 5 | 30 | protagonist + antagonist |
| `archive_very_stale` | 15 | 60 | protagonist + antagonist |

- `archive_stale` SQL 过滤条件从 `role_type != 'protagonist'` 改为 `role_type NOT IN ('protagonist', 'antagonist')`
- `archive_very_stale` 同步更新，确保 antagonist 与 protagonist 同等保护
- 与 Task 102 CharacterFocalDecay 的"核心角色档案永不衰减"原则对齐

#### 2. 新增 `archive_overflow` 数量上限方法

**文件**: `src/songyan/db/context_repo.py`

- 新增 `archive_overflow(project_id, current_chapter, cap=10)`
- 逻辑：
  1. 统计项目下总活跃角色数（`lifecycle_status = 'active'`）
  2. 若总数 > cap，计算 excess = total_active - cap
  3. 查询 excess 个 least-recently-appeared 非核心角色（按 `cv.chapter_number` 升序）
  4. 将其最新 state 记录标记为 `dormant`
- 仅淘汰 `role_type = 'supporting'` 的角色，protagonist/antagonist 不受上限影响

#### 3. 更新 Cleaner 调用链路

**文件**: `src/songyan/db/lifecycle_cleaners.py`

- `CharacterStateCleaner._do_archive` 增加第三步调用：`archive_overflow`
- 执行顺序：stale → very_stale → overflow

---

## 补充调参（对话中追加）

#### 4. 动态 cap（封顶 25）

- `archive_overflow` 的 `cap` 参数改为 `int | None = None`
- `cap=None` 时启用 `_compute_dynamic_cap` 动态计算：
  - `demand = 最近 10 章出场角色数 + 2`
  - `pressure = (最近 5 章新增设定 + 伏笔) // 3`
  - `cap = min(25, max(12, demand - pressure))`
- 设定/伏笔越多，角色池越紧，防止上下文 Token 爆炸

#### 5. 功能性角色分层退场

- 新增 `archive_stale_functional`（window=8）
- 功能性角色判断：`role_type='supporting' AND goals='[]' AND relationships='{}'`
- 核心 supporting（有 goals/relationships）保持 30 章窗口
- `archive_overflow` 淘汰排序：功能性角色优先，其次按 last_appeared

## 改了哪些文件

| 文件 | 变更类型 | 说明 |
|------|----------|------|
| `src/songyan/db/context_repo.py` | 修改+新增 | 窗口默认值调整；antagonist 保护；动态 cap；`archive_overflow`；`archive_stale_functional` |
| `src/songyan/db/lifecycle_cleaners.py` | 修改 | `CharacterStateCleaner` 增加 `archive_stale_functional` 与 `archive_overflow` 调用 |
| `tests/db/test_character_state_lifecycle.py` | 新增测试 | 9 个 Task 108 专项测试 |
| `tests/test_087_lifecycle_integration.py` | 修改 | 适配新默认窗口的断言 |
| `docs/STATUS.md` | 修改 | 标记 Task 108 完成，更新下一 Task |

---

## 测试数据

### 单元测试

```bash
pytest tests/db/test_character_state_lifecycle.py -v
# 结果: 17 passed, 0 failed
```

测试覆盖：
- `archive_stale` 默认窗口 30：非核心角色 30 章未出场 → dormant
- `archive_stale` antagonist 保护：40 章未出场仍保持 active
- `archive_very_stale` 默认窗口 60：dormant 角色 60 章未出场 → archived
- `archive_stale_functional` 窗口 8：功能性角色 8 章未出场 → dormant
- `archive_stale_functional` 保护核心 supporting：有 goals/relationships 的角色不受影响
- `archive_overflow` cap=10：13 活跃角色 → 淘汰 3 个
- `archive_overflow` LRU 排序：最后出场章节最早的优先淘汰
- `archive_overflow` 功能性优先：功能性角色比核心角色优先被淘汰
- `archive_overflow` 核心角色保护：protagonist/antagonist 不被淘汰

### 全量回归测试

```bash
pytest tests/ -q
# 结果: 1533 passed, 4 skipped, 2 xfailed, 3 xpassed, 0 failed
```

**对比**: Task 107 完成时为 1524 passed，本次新增 9 个测试全部通过，无新增失败。

### ruff 检查

```bash
ruff check src/songyan/db/context_repo.py src/songyan/db/lifecycle_cleaners.py tests/db/test_character_state_lifecycle.py tests/test_087_lifecycle_integration.py
# 结果: 8 errors（全部 pre-existing，Task 108 修改未引入新错误）
# - aiosqlite 未导入导致的 F821（原文件已有）
# - lifecycle_status 行过长 E501（原文件已有）
```

---

## 验证结果

| 指标 | 目标 | 实际 | 状态 |
|------|------|------|:----:|
| archive_stale 窗口 | 默认 30 | 30 | ✅ |
| archive_very_stale 窗口 | 默认 60 | 60 | ✅ |
| antagonist 保护 | 与 protagonist 同等 | SQL 已更新 | ✅ |
| 活跃角色上限 | 动态 12-25 | `_compute_dynamic_cap` 已启用 | ✅ |
| 上下文压强抵消 | 设定/伏笔越多 cap 越紧 | pressure = (settings + foreshadowings) // 3 | ✅ |
| LRU 淘汰顺序 | 最后出场最早的先淘汰 | ORDER BY cv.chapter_number ASC | ✅ |
| 功能性优先淘汰 | 无 goals/relationships 先淘汰 | CASE WHEN goals='[]' AND relationships='{}' THEN 0 ELSE 1 END | ✅ |
| 核心角色豁免 | protagonist/antagonist 不被淘汰 | 测试通过 | ✅ |
| 全量回归 | 0 新增失败 | 1533 passed | ✅ |
| 无新增 lint | 0 新增 | 0 新增 | ✅ |

---

## 已知限制

1. **`archive_overflow` 只检查最新 state 记录的 `lifecycle_status`**：如果角色有多个 active state 记录（不同 field），只更新 `MAX(state_id)` 的那一条。这与 `archive_stale`/`archive_very_stale` 的行为一致。
2. **极端核心角色过剩场景**：若项目中 protagonist + antagonist 总数已超过 cap（如 12 个 protagonist），`archive_overflow` 无法将总数压到 cap 以下，因为核心角色被硬保护。此情况在标准项目中极少出现。
3. **`last_appeared` 精度仍依赖 Settlement 时机**：与 Task 102 相同，角色最后出场章节按 `character_states` 最新记录关联的 `chapter_versions.chapter_number` 计算。
4. **`setting_snapshots` 无 `source_version_id`**：动态 cap 中统计"最近 5 章新增设定"依赖 `created_at` 近似，若 settlement 批量重放或时间戳异常，pressure 计算会有偏差。`foreshadowings` 因有 `planted_in_chapter` 更精确。
5. **功能性角色判断仅基于 goals/relationships 空值**：未考虑角色出场频次、对话量等更细粒度指标，但此标准足够区分"有弧光的配角"与"一次性 NPC"。
