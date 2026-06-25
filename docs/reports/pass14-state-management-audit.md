# Pass 14 — 状态管理与事实源一致性审查报告

> **范围**: ST-01 ~ ST-08 (状态管理、事实源一致性、事务边界)
> **日期**: 2026-06-25
> **审查者**: Codex
> **状态**: 完成（静态分析）

---

## 摘要

本 Pass 验证 SQLite 作为唯一长期事实源的不可违背规则是否在代码层面得到完整贯彻。

| ID | 检查项 | 状态 | 验证方法 | 说明 |
|----|--------|:----:|---------|------|
| ST-01 | `chapter_versions` 禁止覆盖 | ✅ | 全局搜索 `UPDATE chapter_versions SET` | 3 处 UPDATE 均为状态标记，无 content 覆盖 |
| ST-02 | `character_states` 永远 INSERT | ✅ | 全局搜索 `UPDATE character_states SET` | 零处 UPDATE |
| ST-03 | Agent 不直接拿 DB connection | ⚠️ | 搜索 `agents/` 目录内 `get_db` import | `continuity_health.py` 有 `get_db` import，为只读查询模块 |
| ST-04 | settlement `old_value` 一致性 | ✅ | 审查 `_validate.py` | Task 114a 修复：DB 事实源回填 |
| ST-05 | `source_quote` 去噪与存在性 | ✅ | 审查 `_quote_filter.py` + `_validate.py` | 去噪过滤 + 模糊匹配验证 |
| ST-06 | `new_setting.setting_key` 唯一性 | ✅ | 审查 `_setting_quality.py` + `__init__.py` | 规范化 + 代码层去重 |
| ST-07 | `foreshadowings.source_version_id` 记录 | ✅ | 审查 `_apply.py` + `_validate.py` | 自动回填 + 校验非空 |
| ST-08 | accepted/settlement/summary 原子事务 | ✅ | 审查 `_nodes.py` L2046-2074 | 同一 `conn` 内 commit |

**7/8 项通过，1 项需观察（ST-03）。**

---

## F1: ST-01 — `chapter_versions` 禁止覆盖

### 验证方法

全局搜索 `UPDATE chapter_versions SET` 模式。

### 验证结果

```sql
-- 当前代码库的全部 UPDATE chapter_versions 语句：
UPDATE chapter_versions SET is_abandoned = 1 WHERE version_id = ?       -- repository.py:491  ✅ 状态标记
UPDATE chapter_versions SET version_type = 'accepted' WHERE version_id = ?  -- repository.py:510  ✅ 状态标记
UPDATE chapter_versions SET score_card = ? WHERE version_id = ?         -- repository.py:547  ✅ 状态标记
```

**结论：零处 content / word_count / scenes 覆盖 UPDATE。ST-01 通过。**

修复追溯：
- `repository.py` `create()` (L422-435): INSERT 新记录
- `repository.py` `accept_version()` (L475-488): 仅 UPDATE version_type 标记
- `repository.py` `mark_abandoned()` (L491-497): 仅 UPDATE is_abandoned 标记

---

## F2: ST-02 — `character_states` 永远 INSERT

### 验证方法

全局搜索 `UPDATE character_states SET`。

### 验证结果

**零处匹配。**

`CharacterRepository.add_state_snapshot()` (L293-303) 为纯 INSERT：

```python
async def add_state_snapshot(self, state: CharacterState, conn: ... | None = None):
    async def _do(c: aiosqlite.Connection) -> int:
        cursor = await c.execute(
            """INSERT INTO character_states (
                character_id, field, value, source_version_id, created_at
            ) VALUES (?, ?, ?, ?, ?)""",
            (state.character_id, state.field, ...)
        )
```

**结论：ST-02 通过。**

---

## F3: ST-03 — Agent 不直接拿 DB connection

### 验证方法

搜索 `agents/` 目录内 `from songyan.db.connection import get_db`。

### 验证结果

```python
# agents/ 目录内唯一匹配：
c:\Vibe Project\Songyan\src\songyan\agents\continuity_auditor\continuity_health.py:13
from songyan.db.connection import get_db
```

**上下文分析**：
- `continuity_health.py` 是 Task 118（ContinuityAuditor Health 低分治理）的辅助模块
- 职责：读取 `continuity_reports` 和 `human_marks` 表，生成分类报告
- 无写操作，仅执行 `SELECT` 查询
- 属于诊断/报告工具，不是核心生成/审查/修订 Agent

**判定**：⚠️ **观察项（P2）**。虽然该模块为只读，且功能上更接近数据报告工具，但物理位置在 `agents/` 目录内，违反了 AGENTS.md "Agent 不直接拿 DB connection" 的字面规则。建议将其迁移到 `db/` 或 `utils/` 目录，或通过 Repository 封装查询。

---

## F4: ST-04 — settlement `old_value` 一致性

### 验证方法

审查 `agents/settlement_extractor/_validate.py`。

### 验证结果

```python
# _validate.py L79-99
state_map: dict[tuple[str, str], str] = {
    (s.character_id, s.field): s.value for s in current_states
}
for update in settlement.character_updates:
    key = (update.character_id, update.field)
    if key in state_map:
        db_value = state_map[key]
        if db_value != update.old_value:
            # Task 114a: 用 DB 事实源回填 old_value
            logger.info("settlement.old_value_backfilled", ...)
            update.old_value = db_value
    else:
        # 未知角色/字段：记录警告但不阻断
        logger.warning("settlement.unknown_character_field", ...)
```

**结论：ST-04 通过。** `old_value` 由 DB 当前事实源回填，不再依赖 LLM 精确复现。不一致时静默修复并记录日志，不阻断流程。

---

## F5: ST-05 — `source_quote` 去噪与存在性

### 验证方法

审查 `_quote_filter.py` + `_validate.py`。

### 验证结果

**去噪（`_quote_filter.py`）**：
- `_is_valid_source_quote()`: 检查长度、关键词存在性、归一化匹配
- `filter_settlement_source_quotes()`: 对 CharacterUpdate / NewSetting / NumericalUpdate 的 source_quote 逐条过滤
- 同一 `setting_key` 去重：保留 source_quote 最短的版本

**存在性验证（`_validate.py`）**：
```python
def _quote_in_content(quote: str, content: str, threshold: float = 0.8) -> bool:
    # 1. 精确子串匹配（归一化后）
    # 2. 模糊匹配：滑动窗口找最佳相似度
```

**结论：ST-05 通过。** 去噪 + 存在性校验双层保护。

---

## F6: ST-06 — `new_setting.setting_key` 唯一性

### 验证方法

审查 `_setting_quality.py` + `__init__.py`。

### 验证结果

**规范化（`_setting_quality.py`）**：
```python
def _normalize_setting_key(key: str, setting_name: str) -> str | None:
    # 将 key 转换为 category.subcategory.name 三段式 ASCII 标识符
```

**去重（`__init__.py` L581-587）**：
```python
# Task 094: 代码层去重 — 跳过已存在的 setting_key
existing_keys = {s.setting_key for s in current_settings if s.setting_key}
duplicates = [s for s in settlement.new_settings if s.setting_key in existing_keys]
if duplicates:
    settlement.new_settings = [
        s for s in settlement.new_settings if s.setting_key not in existing_keys
    ]
```

**结论：ST-06 通过。** 规范化 + 当前 lineage 去重双重保障。

---

## F7: ST-07 — `foreshadowings.source_version_id` 记录

### 验证方法

审查 `_apply.py` + `__init__.py` + `_validate.py`。

### 验证结果

**自动回填（`__init__.py` L365-374）**：
```python
def _backfill_foreshadowing_source_version_ids(settlement, version_id):
    for fs in settlement.foreshadowing_updates:
        if not fs.source_version_id:
            fs.source_version_id = version_id
            updated += 1
```

**写入（`_apply.py` L378）**：
```python
source_version_id=version_id,
```

**校验（`_validate.py` L157-162）**：
```python
for fs in settlement.foreshadowing_updates:
    if not fs.source_version_id:
        errors.append(f"伏笔 '{fs.description[:30]}...' 的 source_version_id 为空")
```

**结论：ST-07 通过。** 自动回填 + 校验非空。

---

## F8: ST-08 — accepted/settlement/summary 事务边界

### 验证方法

审查 `_nodes.py` 中 settlement + accept 的事务处理。

### 验证结果

```python
# _nodes.py L2046-2074
async def _apply_settlement_and_accept(...):
    """在同一事务内完成 settlement apply 与 accept 状态更新."""
    async with get_db() as conn:
        try:
            if settlement is not None:
                await apply_settlement(..., conn=conn)
            await ChapterVersionRepository().accept_version(version_id, conn=conn)
            await ChapterHeadRepository().update(..., conn=conn)
            await conn.commit()
        except Exception:
            await conn.rollback()
            raise
```

**同一事务内完成**：
1. `apply_settlement`（角色状态 INSERT + 设定 INSERT + 伏笔 INSERT + 数值账本 INSERT）
2. `accept_version`（version_type → 'accepted'）
3. `ChapterHeadRepository().update`（current_version_id + accepted_version_id + status）

**Summary 处理（L2195-2217）**：
```python
# 2. 生成章节摘要（非阻塞：失败不导致 settlement 回滚）
if settlement_applied and settlement is not None:
    try:
        summary_id, _summary = await write_chapter_summary(...)
    except Exception:
        # fallback 摘要
        summary_id = await _write_fallback_chapter_summary(...)
```

**结论：ST-08 通过。** Settlement + Accept + Head 更新在同一事务内原子提交。Summary 为独立事务，且设计为"非阻塞"（失败不导致 settlement 回滚），符合 AGENTS.md "Settlement 完成后执行 SummaryWriter" 的语义。

---

## Pass R 回归检查

| ID | 检查项 | 状态 |
|----|--------|:----:|
| RG1 | 新增 import 是否引入未声明依赖 | ✅ 无新增 import |
| RG2 | 新增 except 是否用了裸 Exception | ✅ 无代码变更 |
| RG3 | 修改文件是否保持 < 400 行 | ✅ 无代码变更 |
| RG4 | pytest 回归全绿 | ⏸️ 需要 Python 运行时验证 |

---

## 发现汇总

| ID | 严重度 | 发现 | 文件 | 建议 |
|----|:------:|------|------|------|
| ST-03-obs | P2 | `continuity_health.py` 在 `agents/` 目录内直接 import `get_db` | `agents/continuity_auditor/continuity_health.py` | 迁移到 `db/` 或 `utils/`，或通过 Repository 封装只读查询 |

---

## 汇总

```
Pass 14 状态:
  ST-01 (版本覆盖)          ██████████  ✅
  ST-02 (character_states)  ██████████  ✅
  ST-03 (Agent DB)          ████████▁▁  ⚠️ 观察项
  ST-04 (old_value)         ██████████  ✅
  ST-05 (source_quote)      ██████████  ✅
  ST-06 (setting_key)       ██████████  ✅
  ST-07 (source_version_id) ██████████  ✅
  ST-08 (事务边界)          ██████████  ✅

  通过:  7/8
  观察:  1/8 (ST-03)
```

**状态管理核心契约（7/8 通过）**。唯一观察项是 `continuity_health.py` 的目录归属问题，不影响运行时正确性。

---

> **松烟入墨，字句成锋。**
> 事实源是系统的锚点 — 当每一章的状态都能追溯到不可变版本，150 章的长跑才有了可复现的脚印。
