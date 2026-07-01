# Task 101: TemporalCompressor — 时间分层压缩

> **状态**: 完成
> **完成日期**: 2026-06-13
> **Phase**: V5.0 Context Diet 2.0 — 核心组件 1/4

---

## 做了什么

### 核心修改

把 `ContextPackage` 中的 `previous_summaries` 从"平铺加载所有 Arc"改为"金字塔分层结构"，让历史信息的 token 占用从 O(n) 降到 O(log n)。

#### 1. 新增 `VolumeSummaryRepository.get_previous_volume()`

**文件**: `src/songyan/db/layered_context_repo.py`

- 添加 `get_previous_volume(project_id, chapter_number)` 方法
- 查询 `end_chapter < current_chapter` 的最近一个卷
- 用于金字塔分层：只加载历史卷，当前卷的信息由逐章摘要和弧摘要覆盖

#### 2. 重写 `load_layered_summaries()` 为金字塔策略

**文件**: `src/songyan/workflows/_helpers.py`

| 层级 | 旧策略 | 新策略（金字塔） |
|------|--------|-----------------|
| 精细层 | 最近 3 章逐章 | **最近 5 章逐章** |
| Arc 层 | 加载**所有**不重叠的 Arc | 只加载**最近一个已完成弧** |
| Volume 层 | 加载**当前卷** | 只加载**上一卷**（历史卷） |

**关键逻辑**:
- `limit=3` → `limit=5`
- `list_by_project` 遍历所有弧 → `max(completed_arcs, key=end_chapter)` 取最近一个
- `get_current_volume` → `get_previous_volume`

#### 3. 修复 `init_schema` 迁移顺序 Bug

**文件**: `src/songyan/db/migrations.py`

- `_migrate_lifecycle_status` 在 `executescript(sql)` 之前执行时，全新数据库缺少表会导致 `ALTER TABLE` 失败
- 修复：将 `_migrate_lifecycle_status` 和 `_migrate_setting_category` 移到 `executescript(sql)` 之后
- 这是 pre-existing bug，但阻碍了测试运行，一并修复

#### 4. 更新并扩充单元测试

**文件**: `tests/test_load_layered_summaries.py`

- 更新现有 5 个测试适配新策略（5 章、单弧、历史卷）
- 新增 4 个 TemporalCompressor 专属测试：
  - `test_only_single_arc_loaded`：多弧场景只取最近一个
  - `test_skips_current_arc`：未完成弧（end >= current）被排除
  - `test_skips_current_volume`：当前卷被排除
  - `test_token_budget_less_than_flat_60_percent`：Ch51 模拟场景验证 token < 60%

---

## 改了哪些文件

| 文件 | 变更类型 | 说明 |
|------|----------|------|
| `src/songyan/db/layered_context_repo.py` | 新增方法 | `get_previous_volume()` |
| `src/songyan/workflows/_helpers.py` | 重写 | `load_layered_summaries()` 金字塔策略 |
| `src/songyan/db/migrations.py` | 修复 | 迁移函数顺序调整 |
| `tests/test_load_layered_summaries.py` | 更新+新增 | 适配并扩充测试 |

---

## 测试数据

### 单元测试

```bash
pytest tests/test_load_layered_summaries.py -v
# 结果: 13 passed, 0 failed
```

### 全量回归测试

```bash
pytest tests/ -q
# 结果: 1395 passed, 20 failed, 4 skipped, 4 xfailed
```

**失败分析**:
- 20 个失败均为 **pre-existing**，与 Task 101 修改无关
- 主要类别：
  - Integration 测试 mock LLM 响应耗尽（8 个）
  - Checkpoint/Path 测试 `__interrupt__` 状态断言失败（9 个）
  - Character appearance window importance_score 断言（2 个）
  - Settlement concurrent database locked（1 个）

### ruff 检查

```bash
ruff check src/ tests/
# 结果: 323 errors（全部 pre-existing，Task 101 修改未引入新错误）
```

---

## 验证结果

| 指标 | 目标 | 实际 | 状态 |
|------|------|------|:----:|
| `previous_summaries` token 数（Ch51） | < 平铺 60% | 54.6% | ✅ |
| 弧摘要加载数量 | 1 个 | 1 个 | ✅ |
| 卷摘要加载策略 | 只加载历史卷 | 已实现 | ✅ |
| 最近逐章数量 | 5 章 | 5 章 | ✅ |
| 测试通过 | pytest 新增测试全部通过 | 13/13 | ✅ |
| 无新增 lint 错误 | 0 新增 | 0 新增 | ✅ |

---

## 已知限制

1. **Ch51 单章验证尚未执行**: 当前仅通过单元测试模拟验证 token 占比，实际 Ch51 Writer 行为需要在完整生成流程中验证（留到 Task 105 流式验证时执行）。
2. **弧边界重叠处理**: 若最近一个已完成弧与最近 5 章完全重叠（例如弧只有 3 章且都在最近 5 章内），则弧层被跳过。这在小弧场景下可能导致该弧信息仅通过逐章摘要呈现，但在标准 10 章弧边界下不常见。
3. **当前弧无摘要覆盖**: 如果 current_chapter 位于一个尚未生成摘要的弧中，该弧的信息只能通过逐章摘要（最近 5 章）覆盖。对于超过 5 章的当前弧，5 章之前的部分在此阶段无摘要可用。
