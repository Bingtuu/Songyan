# Task 110c: 加载端智能过滤与分级裁剪 — DONE

> **完成日期**: 2026-06-17
> **阶段**: V5.0 Phase 4
> **上一 Task**: 110b-setting-summary-quality-control

---

## 做了什么

### 1. 加载端智能过滤

#### 1.1 非 arc 角色直接 skip
- **文件**: `src/songyan/agents/context_manager/_assemblers.py`
- **修改**: `_build_character_snapshots` 中，非当前 arc 且非 protagonist/antagonist 的角色直接 `continue` 跳过，不再降级为 `compact` 档案
- **影响**: 显著减少长尺度章节初始加载的 character_states 数量

#### 1.2 soft_references 关键词过滤
- **文件**: `src/songyan/agents/context_manager/__init__.py`
- **修改**: `assemble_context_package` 中，从 `chapter_goal.target_events + hooks` 提取关键词，只保留 `content` 包含关键词的 soft_reference（`is_critical` 的不过滤）
- **关键词提取**: `_extract_keywords`（已存在，本次从 `_assemblers` 导入到 `__init__`）

#### 1.3 foreshadowings 按紧迫性过滤
- **文件**: `src/songyan/agents/context_manager/__init__.py`
- **修改**: 只保留 `due/overdue` + 补充到动态上限的最近 `planted` 项
- **逻辑**: `high_priority_fs + rest_fs[:keep_rest]`，其中 `keep_rest = max(0, _max_fs - len(high_priority_fs))`

### 2. 动态硬上限（章节阶段相关）

- **文件**: `src/songyan/agents/context_manager/__init__.py`
- **新增函数**: `_dynamic_max_for_chapter(chapter_number: int) -> dict[str, int]`
- **策略**:
  - Ch1-80: `max_setting_input=10`, `max_foreshadowing=8`, `max_character_states=4`
  - Ch81+: `max_setting_input=6`, `max_foreshadowing=5`, `max_character_states=3`
- **集成点**: `assemble_context_package` 中用于 `setting_snapshots` 入站过滤 和 `foreshadowings` 过滤

### 3. 分级 ContextEmergency（Task 110c 核心）

- **文件**: `src/songyan/agents/context_manager/__init__.py`
- **修改**: `_context_emergency` 从单一核裁模式改为三级降级策略

| 级别 | budget_used 范围 | 行为 |
|------|------------------|------|
| Level 1 | 1.0 – 1.2 | 保留主角+top2 配角；soft_refs critical+top5；foreshadowing due/overdue；arc/volume 截断 50% |
| Level 2 | 1.2 – 1.5 | 只保留主角；soft_refs critical+top3；foreshadowing overdue；清空 open_threads/permanent_scenes |
| Level 3 | > 1.5 | 核裁模式（原 Task 104 行为） |

- **新增字段**: `ContextPackage.context_emergency_level: int = 0`（`models/context.py`）

### 4. 分区预算制

- **文件**: `src/songyan/agents/context_manager/__init__.py`
- **新增方法**: `BudgetPruner._apply_partition_budgets`
- **策略**: 在跨分区裁剪前，各分区先按 Token 比例内部压缩
  - character_states: 30%
  - recent_plot: 20%
  - soft_references: 15%
  - foreshadowing: 10%
- **压缩规则**:
  - character_states: 超预算时保留 70%（按 importance_score 排序）
  - recent_plot: 超预算时 summaries 减半
  - soft_references: 超预算时保留 60%（按 relevance_score 排序）
  - foreshadowing: 超预算时保留所有 due/overdue + 50% rest

### 5. 代码清理

- 补全 `__init__.py` 缺失的导入（`Any`, `HumanMark`, `SoftReference`）
- 移除未使用的 `_calculate_dynamic_relevance` 导入
- 修复 docstring 和条件语句的 E501 行过长

---

## 改了哪些文件

| 文件 | 修改类型 | 说明 |
|------|---------|------|
| `src/songyan/agents/context_manager/__init__.py` | 修改 | 动态上限、关键词过滤、分级 emergency、分区预算制 |
| `src/songyan/agents/context_manager/_assemblers.py` | 修改 | 非 arc 角色 skip |
| `src/songyan/models/context.py` | 修改 | 新增 `context_emergency_level` 字段 |
| `tests/test_context_manager.py` | 修改 | 新增 16 个 Task 110c 单元测试 |
| `tests/test_077b_budget_hard_enforcement.py` | 修改 | 更新硬断言触发测试数据（适配分区预算制） |
| `tests/test_080_character_appearance_window.py` | 修改 | 更新断言适配非 arc 角色 skip 行为 |
| `tests/test_104_budget_hard_ceiling.py` | 修改 | 更新断言适配分级 emergency 行为 |

---

## 测试数据

### 单元测试
- `TestDynamicMaxForChapter`: 3 个测试（早期章节默认上限、晚期章节收紧、边界值）
- `TestContextEmergencyLevels`: 3 个测试（Level 1/2/3 各自断言）
- `TestPartitionBudgets`: 4 个测试（character_states/recent_plot/soft_refs/foreshadowing 压缩）
- `TestArcCharacterSkip`: 3 个测试（非 arc supporting skip、antagonist 保留、arc 角色保留）
- `TestAssembleContextPackage110c`: 3 个测试（soft_refs 关键词过滤、foreshadowings 过滤、Ch90 动态上限）

### 回归测试
```bash
pytest tests/ -q
```
- **结果**: 1619 passed, 4 skipped, 2 xfailed, 3 xpassed, 11 warnings
- **与基线对比**: 从 1603 提升到 1619（新增 16 个测试全部通过）
- **新增失败**: 无

### 代码检查
```bash
ruff check src/ tests/
```
- **结果**: 无新增 lint 错误（修复了 2 个 F401/F821，剩余 E501 均为 pre-existing）

---

## 验证结果

- [x] 单元测试通过（pytest tests/test_context_manager.py -v: 77 passed）
- [x] 全量回归测试通过（1619 passed，无新增失败）
- [x] 代码检查无新增错误
- [x] 旧测试适配完成（077b/080/104 共 6 个失败已修复）

---

## 已知限制

1. **分级 emergency 不保证 budget_used <= 1.0**: Level 1/2 只是降低 token，极端情况下仍可能超预算。这是设计意图——避免直接清空所有软信息导致 Writer 失去上下文。
2. **分区预算比例固定**: character_states:30%/recent_plot:20%/soft_refs:15%/foreshadowing:10% 是硬编码的，未按章节类型动态调整。
3. **soft_refs 关键词过滤依赖中文分词精度**: `_extract_keywords` 使用简单标点切分 + 停用词过滤，复杂语义关联可能漏检。
4. **Ch80+ 硬上限是经验值**: 6/5/3 的上限未经过大规模实跑验证，Task 110d 验证阶段可能需要微调。

---

## 下一 Task

**Task 110d**: Ch80-Ch100 快速验证与调优 — 验证 110a-110c 综合效果并调参。
