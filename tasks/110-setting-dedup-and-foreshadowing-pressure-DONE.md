# Task 110: SettingDeduplication + ForeshadowingPressure — DONE

## 做了什么

### 1. Setting Semantic Deduplication（设定语义去重）

新增 `SettingDeduplicationService`：
- 基于 `difflib.SequenceMatcher` 计算 `(setting_name + description)` 的文本相似度
- 对 `setting_tracking` 中 `status='active'` 的记录做两两比较
- 相似度 ≥ 0.85 时视为重复，保留 `introduced_in_chapter` 最早的主记录
- 将重复记录的 `status` 设为 `archived`，同步更新 `setting_snapshots.lifecycle_status`
- 更新主记录的 `last_mentioned_chapter` 为所有重复记录中的最新值

新增 `SettingDeduplicationCleaner`：
- 注册到 `LifecycleScheduler`，每 10 章触发一次（`current_chapter % 10 == 0`）
- 与 `SettingSnapshotCleaner`、`ForeshadowingCleaner` 等并行运行

### 2. Foreshadowing Pressure Tracking（伏笔压力监控）

`ForeshadowingRepository` 新增：
- `mark_overdue(project_id, current_chapter)`：将 `expected_resolve_chapter < current_chapter` 且 `status IN ('planted', 'due')` 的伏笔自动标记为 `overdue`
- `get_unresolved_ratio(project_id, current_chapter)`：计算 `(planted + due) / current_chapter`

`settlement_extractor/_apply.py` 集成：
- settlement 应用后自动调用 `mark_overdue` 和 `get_unresolved_ratio`
- 根据比例设置 `settlement.foreshadowing_pressure`：
  - ratio ≤ 0.20 → `"low"`
  - 0.20 < ratio ≤ 0.30 → `"medium"`
  - ratio > 0.30 → `"high"`

`StateSettlement` 模型新增 `foreshadowing_pressure: str = "low"` 字段。

## 改了哪些文件

| 文件 | 变更类型 | 说明 |
|------|----------|------|
| `src/songyan/models/settlement.py` | 修改 | `StateSettlement` 新增 `foreshadowing_pressure` |
| `src/songyan/db/settlement_repo.py` | 修改+新增 | `ForeshadowingRepository` 新增 `mark_overdue`、`get_unresolved_ratio`；新增 `SettingDeduplicationService` |
| `src/songyan/db/lifecycle_cleaners.py` | 修改 | 新增 `SettingDeduplicationCleaner`；注册到 `get_default_scheduler` |
| `src/songyan/agents/settlement_extractor/_apply.py` | 修改 | settlement 后集成 foreshadowing pressure 计算 |
| `tests/db/test_setting_deduplication.py` | 新增 | 11 个 Task 110 专项测试 |
| `tests/test_settlement_extractor.py` | 新增 | 3 个 foreshadowing pressure 测试 |

## 测试数据

### 单元测试

```bash
pytest tests/db/test_setting_deduplication.py -v
# 结果: 11 passed, 0 failed
```

测试覆盖：
- `_similarity`：完全相同 = 1.0，完全不同 < 0.3，相似中文 0.3~0.8
- `deduplicate`：检测重复、保留最老主记录、更新 `last_mentioned_chapter`、同步 archive `setting_snapshots`、无 false positives、跳过已 archived
- `mark_overdue`：只更新超过期限的 planted/due 伏笔
- `get_unresolved_ratio`：排除 resolved 伏笔，计算正确比例

```bash
pytest tests/test_settlement_extractor.py -v
# 结果: 48 passed, 1 xfailed (预存在)
```

新增测试覆盖：
- `test_sets_foreshadowing_pressure_high`：ratio=0.40 → "high"
- `test_sets_foreshadowing_pressure_low`：ratio=0.10 → "low"
- `test_sets_foreshadowing_pressure_medium`：ratio=0.25 → "medium"

### 全量回归测试

```bash
pytest tests/ -q
# 结果: 1547 passed, 4 skipped, 2 xfailed, 3 xpassed, 0 failed
```

**对比**: Task 109 完成时为 1533 passed，本次新增 14 个测试全部通过，无新增失败。

### 代码检查

```bash
ruff check src/ tests/
# 修改文件未引入新 lint 错误
# 预存在 8 个错误（1 F821 in _apply.py, 7 E501 in test_settlement_extractor.py）
```

## 已知限制

1. **`difflib.SequenceMatcher` 对中文相似度偏保守**：相同设定用不同措辞描述时，相似度可能低于 0.85 阈值。当前 threshold=0.85 是生产默认值，若实际去重率不足可考虑引入更先进的文本相似度算法（如 sentence-transformers）。
2. **`setting_snapshots.created_at` 无 `source_version_id`**：与 Task 109 相同，`setting_snapshots` 无法精确关联到章节，去重只基于 `setting_tracking` 的时间戳。
3. **去重 Cleaner 每 10 章触发一次**：短窗口内（<10 章）的重复设定不会立即被合并，但通常语义漂移需要多章积累才会出现。
4. **`foreshadowing_pressure` 未直接注入 CreativeBrief**：当前仅写入 `StateSettlement`，后续若 GoalPlanner/CreativeDirector 需要读取，需额外透传逻辑。

## 下一 Task

按 STATUS.md 规划，进入 **Task 111: Ch101-Ch150 流式验证 + 决策门 DG-2**（Phase 4 规模化验证）。
