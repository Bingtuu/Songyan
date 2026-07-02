# Task 151: MR 上限自适应 + 相关性排序

> **Phase**: V6 阶段 B（末端治理）
> **优先级**: P1（缓解 Writer 过载 / MR 截断丢失关键设定；配合 Task 149/150 稳住 orphan 回收闭环）
> **依赖**: 阶段 0（Task 144 PlotThread 线索结构，供相关性排序复用）+ 阶段 A 度量；**建议在 Task 149 之后**（上限升到 16 的安全性依赖 149 压低 active_critical 基数，见 Cross-Task Coordination）
> **预计工作量**: 中（拆 151a 自适应上限 + 151b 相关性排序）
> **事实入口**: `tasks/V6-README.md`；规划：`docs/v6-plan.md` §3 阶段 B

---

## Goal

把强制引用（mandatory references, MR）的上限从"固定封顶"改为"随活跃 critical 数自适应"，并把排序从"仅按沉默章数 + 引入章"升级为"主线相关性 + 沉默"综合，使真正该被 Writer 回收的关键设定不被固定上限挤掉，同时不让 MR 列表膨胀压垮 Writer。

## Context

设计核实（2026-07-02，创建前对主干代码核对，含对规划稿口径的修正）：

- **MR 装配**：`src/songyan/workflows/_helpers.py` 的 `_load_critical_mandatory_references(project_id, chapter_number, scenes_count=3, max_mandatory_references=None)`（L484-571）。
  - 上限默认：`max_mandatory_references = min(max(scenes_count * 2, 6), 12)`（L516-517）——**即当前 MR 封顶是 12，且只随场景数微调，与活跃 critical 数无关**。
  - 过滤：仅取 `status == "active"` 且 `category == "critical"` 且沉寂 ≥ `ORPHANED_THRESHOLDS["critical"]`（默认 3）；排序 `(silent_chapters, -introduced_in_chapter)` 降序（L548-551）；截断 `result[:max_mandatory_references]`（L552-554），并记 `task138n.mandatory_references_truncated` 日志。
  - **与 149/152 的天然一致性**：因 MR 只取 `status == "active"`，Task 149 的 `candidate` 与 Task 152 的 `resolved`/`abandoned` 已自动不进 MR，无需在本 Task 额外过滤（但需在各自 DONE 交叉验证该假设仍成立）。
- **规划稿口径修正**：`docs/v6-plan.md` / 早期笔记提到 `MAX_ORPHANED=8`。核实后：
  1. MR 的封顶不是 `MAX_ORPHANED`，而是上面的 `min(max(scenes_count*2,6),12)`；
  2. `MAX_ORPHANED` 实际值是 **12**（不是 8），且定义在 `continuity_auditor/_constraints.py:15`，用于 `_generate_constraints` 里 `report.orphaned_settings[:MAX_ORPHANED]`（连续性约束生成，另有 `MAX_CONSTRAINTS_GENERATED=30`），**与 MR 装配是两条不同链路**。
  → 本 Task 主改 MR 装配链路的上限与排序；`MAX_ORPHANED`（约束生成侧）是否同步自适应作为**可选子项**评估，不默认改动，避免误扩范围。
- **相关性信号来源**：Task 144 已建 `PlotThread`（含 `is_mainline`）与 settlement 证据匹配思路；可据"设定 key/name 是否关联某条 `is_mainline` 线索 / 是否在临近弧的 `threads_to_resolve`"给相关性打分。无骨架项目退化为旧排序（仅沉默 + 引入章）。

### Cross-Task Coordination

- **MR 过滤一致性**：MR 装配只取 `status == 'active'` 且 `category == 'critical'`。Task 149 的 `candidate`、Task 152 的 `resolved`/`abandoned` 自动不进 MR，本 Task 无需额外过滤。需在各自 DONE 中交叉验证该假设仍成立。
- **自适应公式初版**：
  ```python
  cap = min(max(active_critical_count, scenes_count * 2, 6), 16)
  ```
  即下限 6（保证少量关键设定必注入），上限 16（防 Writer 过载），活跃 critical 数本身作为主力因子，scenes_count 作为辅助因子。参数在 Layer 3 用 138m/138n/138k 校准并在 DONE 中记录来源。
  > **上限 16 > 现状 12 不是单纯放宽**：138m 的过载根因是 MR 列表长达 43 条。本 Task 的净效果依赖两个前置——(1) Task 149 把超额 critical 降级为 candidate、压低 `active_critical_count` 基数；(2) 151b 相关性排序优先注入主线相关项。在这两者作用下，即便 cap 顶到 16，实际注入量也应低于现状且更相关。**若 Task 149 未先合入，本 Task 上限应临时保守回退到 ≤12**，避免在高 active_critical 基数下反而加重过载（DONE 需记录合入顺序与实测注入量）。
- **主线相关性定义**：给定 `mainline_thread_keys: set[str]`（由 Task 144 的 `is_mainline=true` PlotThread 的 `thread_key` + 临近弧 `threads_to_resolve` 组成）。若 critical 设定的 `setting_key` 或 `name` 与任一 mainline key 子串匹配，则视为"主线相关"。
- **`MAX_ORPHANED` 边界**：本 Task 默认不改 `continuity_auditor/_constraints.py` 的 `MAX_ORPHANED=12`（约束生成侧）。若 Layer 3 发现约束侧硬截断导致 orphan 误判，作为可选子项评估并单独单测，不隐式扩散范围。

## In Scope（必须完成）

### 151a — MR 上限自适应
- [ ] MR 上限随**活跃 critical 数**自适应（而非恒定 12 / 仅随 scenes_count）。首版公式 `cap = min(max(active_critical_count, scenes_count * 2, 6), 16)`，有下限 6 与上限 16；**上限 16 的安全前提见 Cross-Task Coordination（依赖 Task 149 压基数 + 151b 排序）；若 149 未先合入则临时回退 ≤12**。公式参数结合 138m/138n/138k 分布定，来源写入 DONE。
- [ ] 保留 `scenes_count` 作为影响因子之一（Writer 场景越多可承载越多 MR），但不再是唯一因子。
- [ ] 截断日志保留/增强，便于长跑观测截断是否仍高频发生。

### 151b — 相关性排序
- [ ] 排序键从 `(silent_chapters, -introduced_in_chapter)` 升级为"主线相关性 + 沉默"综合：主线相关 critical 优先（`mainline_thread_keys` 子串匹配 `setting_key` 或 `name`），其次久未回收（沉默）。
- [ ] **无骨架 / 无线索项目回退**：拿不到主线相关性时退化为旧排序，行为不劣化。
- [ ] 遵守边界：MR 装配仍在 context_manager service 层；ContextManager 不做生成/审查判断；不新增 LLM 调用；硬约束（`protagonist_profile` 等）不受本改动裁剪。

## Out of Scope（明确不做）

- 不做录入侧降级（Task 149）、分类收紧（Task 150）、resolve/作废出口（Task 152）。
- 默认不改 `_constraints.py` 的 `MAX_ORPHANED`/`MAX_CONSTRAINTS_GENERATED`（如评估需同步，作为 151 的可选子项并单独单测，不隐式扩散）。
- 不改 Context Diet 2.0 的预算硬顶与硬约束不裁剪规则。

## 接口契约

```python
# context_manager/_assemblers.py
async def _load_critical_mandatory_references(
    project_id: str,
    chapter_number: int,
    scenes_count: int = 3,
    max_mandatory_references: int | None = None,   # None -> 自适应计算
    *,
    active_critical_count: int | None = None,       # 自适应上限输入
    mainline_thread_keys: set[str] | None = None,   # 相关性排序输入；None -> 旧排序
) -> list[...]:
    ...
```

（最终签名以实现为准；核心：上限自适应 + 相关性排序，且两者输入缺失时安全回退。）

## 测试要求

### Layer 2: 模块测试
- [ ] **自适应上限**：活跃 critical 数少 → 上限小；数多 → 上限在下限与封顶之间随之提高（边界值：0 活跃、恰好下限、超封顶）。
- [ ] **相关性排序**：给定含主线相关与非相关的 critical，验证主线相关优先于纯沉默项被选入；平级再按沉默排序。
- [ ] **回退**：`mainline_thread_keys=None`（无骨架）→ 与旧 `(silent, -introduced)` 排序逐条一致。
- [ ] **不违反硬约束**：MR 变化不影响 `protagonist_profile` 等硬约束注入。

### Layer 3: 历史/小窗口验证（阶段 B 出口佐证）
- [ ] 在 Ch~100 位置（用 138n 或复跑数据）核对：`rule_auditor.mandatory_reference_missing` 命中率**较 138n 不升高**（自适应 + 排序没有把真正该回收的关键设定挤掉）。
- [ ] 观测 `mandatory_references_truncated` 频率变化，入报告。

## 验收标准（Acceptance Criteria）

- [ ] `pytest tests/test_151_*.py -v` 全过；`ruff check src/ tests/` 通过；全量 pytest 不回归。
- [ ] MR 上限随活跃 critical 数自适应（非恒定 12），有明确下限/上限；排序体现主线相关性 + 沉默；无骨架回退与旧排序一致。
- [ ] Ch100 处 `mandatory_reference_missing` 命中率不高于 138n（证据入 `docs/reports/`）。
- [ ] 不违反不可违背规则：MR 经 context_manager service；不新增 Agent/LLM；硬约束不裁剪；默认不动 `_constraints.py` 常量。
- [ ] 生成 `tasks/151-mr-adaptive-cap-and-relevance-DONE.md`，含自适应公式来源、排序规则、MR 封顶口径澄清（区分 MR 装配上限 vs `MAX_ORPHANED=12`）、Ch100 命中率对比。
- [ ] 更新 `tasks/V6-README.md`（151 状态）与 `docs/STATUS.md`。

## 参考文档

- `docs/v6-plan.md` §3 阶段 B（Task 151 行）；§1.4-T5/T6 相关
- 现有代码：`workflows/_helpers.py`（`_load_critical_mandatory_references`）、`continuity_auditor/_constraints.py`（`MAX_ORPHANED`/`MAX_CONSTRAINTS_GENERATED`，非本 Task 主改）、`db/continuity_repo.py`（`find_orphaned`/`ORPHANED_THRESHOLDS`）
- 138m 根因报告（MR 上限/过载分析）：`docs/reports/task-138m-critical-orphan-root-cause-report.md`
- Task 144（PlotThread `is_mainline` / 弧线索结构）
