# Task 137: 设定回收闭环与 tracking 刷新机制（V5.2）

> **类型**: 底层缺陷修复 / 实跑验证  
> **日期**: 2026-06-27  
> **前置**: Task 135、Task 136  
> **目标**: 让“设定回收”从“提示 LLM”变成可验证、可自动闭环的机制，降低 enforce 模式下 `orphaned_settings` 的虚假累积，使 Ch12–Ch15 orphan 增长速率降至 Ch9–Ch12 的一半以下。

---

## 1. 背景

### 1.1 Task 127-136 完成情况复核

| Task | DONE 文档 | 结论 | 对 Task 137 的影响 |
|---|---|---|---|
| 127 | `tasks/127-health-low-score-halt-refactor-DONE.md` | 已完成。`health_low_score_halt` 改为“历史新低 + P1 同步激增”复合条件，Ch1-Ch19 enforce 小窗口零 gate 触发，pytest 1842 passed。 | health_low 硬门禁不再是当前主阻塞，后续验证可聚焦 orphan/continuity。 |
| 128 | `tasks/128-strict-mode-fault-tolerance-and-quality-ramp-DONE.md` | 已完成。QG false 在开局期可走 `degraded_accept`，RevisionHandler 增加 readability 专项路径，pytest/ruff 通过。 | enforce 流程容错已具备，但 degraded_accept 章节仍需在验证口径中单独统计 settlement/summary。 |
| 129 | `tasks/129-enforce-mode-ch1-ch50-validation-DONE.md` | 条件完成。`run-89d7a2d4` Ch1-Ch15 后因 quality gate streak 暂停，暴露 Writer 单场景退化、SettlementExtractor 提取失败、orphan 快速累积。 | 明确 V5.2 底层缺陷来源；Task 133/134/135 已分别承接前三类缺陷。 |
| 130 | `tasks/130-gate-mode-default-decision-DONE.md` | 已完成。默认 `gate_mode` 保持 `observe`，CLI 暴露 `--gate-mode`，报告支持 gate 汇总。 | 当前不应默认切换 enforce；Task 137 仍使用显式验证窗口收集证据。 |
| 131 | `tasks/131-task-docs-archive-and-status-cleanup-DONE.md` | 已完成。历史规划稿归档，索引优先指向 `-DONE.md`。 | 后续任务必须保持活跃规划稿与 DONE 文档边界清晰。 |
| 132 | `tasks/132-v51-final-acceptance-package-DONE.md` | 已完成。V5.1 通过，Task 129 暴露的底层缺陷转入 V5.2。 | Task 137 属于 V5.2 收口，不影响 V5.1 通过结论。 |
| 133 | `tasks/133-writer-multi-scene-structure-fix-DONE.md` | 已完成。Writer 1.2.0 多场景结构在 Task 136 采集窗口中达到 100%。 | 多场景结构不是当前阻塞；Writer 1.2.0 仍需显式启用，默认仍为 1.1.0。 |
| 134 | `tasks/134-settlement-character-numerical-extraction-fix-DONE.md` | 已完成。SettlementExtractor 角色/数值提取旧口径在成功 settlement 章节中达标。 | 后续复跑必须同时统计全窗口 settlement+summary，不能只看成功 settlement 子集。 |
| 135 | `tasks/135-setting-recycling-and-continuity-health-governance-DONE.md` | 已完成。health floor 达标，但 orphan 增速问题未完全解决。 | Task 137 的直接前置：继续治理 orphan 虚假累积与 tracking 刷新。 |
| 136 | `tasks/136-v52-enforce-ch1-ch20-validation-DONE.md` | 已完成但整体验收未通过。Ch1-Ch20 完成率、多场景、health floor 通过；orphan 增长速率未减半，Ch15/Ch16 以 degraded_accept 完成。 | 触发 Task 137；当前不能扩大默认 enforce 验证，需先修 orphan 收口。 |

### 1.2 下一任务编号决策

基于 Task 127-136 DONE 事实，Task 137 的剩余工作拆分为 Task 138a-138e：

- Task 127-132 已完成 V5.1 收口、候选硬门禁和默认 gate_mode 决策。
- Task 133/134/135 已完成 Task 129 暴露的三类 V5.2 底层缺陷修复。
- Task 136 是验证任务，结论为“多场景、旧 settlement、health floor 通过，但 orphan 增速未减半”。
- Task 137 正是 Task 136 未通过项的直接收口任务；当前最新证据为 Task 138d `run-4fd48756` Ch10-Ch12 completed，Ch12 orphan 从 baseline 19 降至 16，但 health 仍为 3.0。
- 剩余工作已经超出单一 Task 137 文档内部 checklist 的粒度，应拆成连续任务文档承接。

因此 Task 137 保持活跃，当前已完成 **Task 138a-138e** 第一轮闭环；下一轮继续复用 Task 138a 入口，对 `run-4fd48756` 的 16 个 orphan 重新分类：

1. `tasks/138a-remaining-orphan-classification.md`：分类最新剩余 16 个 orphan。
2. `tasks/138b-orphan-root-cause-decision.md`：基于分类结果决定最小动作。
3. `tasks/138c-orphan-minimal-fix.md`：实施最小修复或 human mark。
4. `tasks/138d-ch10-ch12-post-fix-rerun.md`：用副本 DB 复跑 Ch10-Ch12。
5. `tasks/138e-task137-fact-sync-and-closure.md`：同步事实源并决定 Task 137 归档或进入下一轮。

原 Task 132 中提到的后置 “Task 138 候选”顺延为 Task 139；原 “Task 139 候选”顺延为 Task 140。

### 1.3 Task 136 到 Task 137 的当前事实

Task 136 Ch1–Ch20 采集窗口实跑显示（验证期间临时启用 Writer 1.2.0，基于 enforce profile 但关闭 health_low halt）：

- Task 133 目标已达成（多场景 100%）。
- Task 134 旧口径目标已达成（settlement 成功章节中有记录占比 100%）；Task 137 复跑需改用 Ch1–Ch20 全窗口分母并同时要求 summary 成功。
- Task 135 的 health floor 指标通过，但 **orphan 增长速率未减半**，Ch12–Ch15 反而高于 Ch9–Ch12（4.0 / 章 vs 2.667 / 章）。
- 主要增长类别为 `background`（Ch15 时 28/33 个）。

根因分析：

1. **已有设定被正文提及后，不会刷新 `last_mentioned_chapter`**。`SettlementExtractor` 在提取 `new_settings` 时过滤掉已存在的 `setting_key`，导致 `apply_settlement._update_continuity_tracking` 中的 `update_last_mentioned` 分支无法执行。
2. **`setting_tracking` 与 `setting_snapshots` 生命周期不同步**。`SettingEvaporator` 只 archive `setting_snapshots`，`setting_tracking.status` 仍保持 `active`，继续被 ContinuityAuditor 计为 orphan。
3. **`SettingEvaporator` 时间衰减过慢**。固定分母 50 章导致 Ch20 之前 background 设定几乎不可能被蒸发。
4. **已回收的 continuity_auditor human_mark 不会自动 resolve**，Writer 可能反复看到同一批“必须回收”的设定。

---

## 2. 目标

建立“检测回收/呼应 → 刷新 tracking → 自动 resolve human_mark → 减少虚假 orphan”的闭环。

---

## 3. 具体改动

### 3.1 正文 setting 提及扫描（不依赖 LLM）

- **文件**: `src/songyan/agents/settlement_extractor/_apply.py`
- **新增**: `_detect_setting_references(content: str, active_settings: list[dict]) -> dict[str, str]`
- 使用 `setting_name` 对正文做子串匹配；若命中项后紧跟另一个中文字符（如「天剑宗」中的「天剑」），则视为更长词的一部分并跳过。
- 在 `apply_settlement` 事务中，对命中的 setting 调用 `setting_tracking_repo.update_last_mentioned(..., chapter_number)`。

### 3.2 SettlementExtractor 显式输出 `recycled_settings`

- **文件**: `prompts/cards/settlement_extractor/1.0.2.yaml`
- **新增 JSON 字段**:

```json
{
  "recycled_settings": ["xuanhuan.lin.xxx"]
}
```

- 与 3.1 的扫描结果合并，作为刷新 `last_mentioned` 和 resolve human_mark 的证据。

### 3.3 自动 resolve 已回收的 continuity_auditor human_mark

- **文件**: `src/songyan/agents/settlement_extractor/_apply.py`
- 在 apply 事务中，若 `human_mark.source == "continuity_auditor"` 且 `target_key` 被检测到在正文中出现，则调用 `HumanMarkRepository.resolve(mark_id, chapter_number)`。

### 3.4 `setting_tracking` 生命周期与 snapshots 同步

- **文件**: `src/songyan/db/settlement_repo.py`
- 当 `SettingSnapshotRepository.archive_stale()` / `archive_by_confidence()` 修改 `setting_snapshots.lifecycle_status` 时，同步将对应 `setting_tracking.status` 置为 `dormant` / `archived`（保留记录，但退出 orphan 统计）。

### 3.5 按 category 调整 SettingEvaporator 时间衰减

- **文件**: `src/songyan/agents/setting_evaporator/__init__.py`
- 将固定分母 50 改为按 category：
  - `background`: 25
  - `technical`: 30
  - `historical`: 20
  - `recurring`: 80
  - `critical`: 100

### 3.6 CreativeDirector 回收列表按 orphan 优先级排序

- **文件**: `src/songyan/agents/creative_director/__init__.py`
- `_load_active_settings_to_recycle` 新增 `min_silent_chapters=2` 过滤，仅展示已沉寂至少 2 章的 active 设定；同类别内按 `last_mentioned_chapter` 升序排列，让最久未提及的设定优先被 Writer 看到。

---

## 4. 验收标准

### 4.1 代码与测试

- [x] `ruff check src/ tests/` 通过。
- [x] 全量 `pytest tests/` 通过，且新增 Task 137 相关测试：
  - [x] 正文提及 setting 后 `setting_tracking.last_mentioned_chapter` 被刷新。
  - [x] `recycled_settings` 提取字段被正确解析并入库。
  - [x] continuity_auditor human_mark 在目标 setting 被回收后 `resolved_at` 更新。
  - [x] `setting_snapshots` archive 后对应 `setting_tracking.status` 同步变更。
  - [x] SettingEvaporator 按 category 使用不同衰减分母。

### 4.2 实跑验证

- [x] 使用 Task 136 脚本或等效显式配置重新实跑 Ch1–Ch20；必须覆盖 Writer 1.2.0，不能直接使用普通 pipeline 默认 Writer 1.1.0。
- [x] 当前本地复跑基线使用 `SOURCE_PROJECT_ID=e95a1fa3`、`BASELINE_RUN_ID=run-a2bed648`；该项目有 Ch1–Ch150 accepted 证据，且本地存在对应 run log。
- [x] 复跑报告必须明确：本窗口基于 enforce profile，但为完整采集指标关闭 health_low 相关 halt；它不是完整默认 `gate_mode="enforce"` 的通过证据。
- [ ] Ch12–Ch15 orphan 平均增长/章 ≤ Ch9–Ch12 平均增长/章的一半。
- [ ] Ch15 `orphaned_settings` 中 `background` 数量不再单调上升（相对 Ch12 减少或持平）。
- [ ] Ch12/Ch15 health score ≥ 3.0。
- [x] Multi-scene ratio ≥ 90%。
- [ ] Ch1–Ch20 全窗口中，Settlement+Summary 成功且含角色/数值记录的章节占比 ≥ 95%；不得只以 `settlement_success=True` 的章节为分母。

### 4.2.1 2026-06-28 复跑结果

- 运行命令: `python scripts/run_136_v52_enforce_validation.py`
- 验证项目 ID: `56fbb888d78f4b29bb1a0e8aa7e6a675`
- Run ID: `run-06ae5101`
- 结果: `partial`，完成 Ch1-Ch11，Ch12 在 `settlement_review` 阶段失败。
- 报告: `docs/reports/task-137-v52-enforce-ch1-ch20-rerun-report.md`
- 结论: Task 137 实跑验证未通过；由于未跑到 Ch15/Ch20，orphan 增速减半目标不可完整判定。
- 直接阻塞:
  - Ch12 settlement 数值更新校验失败，触发 human review 并中断 run。（2026-06-28 已修复：温度/倒计时等读数型 numerical_update 在有正文读数证据时规整为 telemetry snapshot，避免过度台账化。）
  - Ch11 run log 标记 success，但 QG false、settlement/summary false，且 DB `chapter_heads` 仍为 draft、无 accepted head，存在章节成功判定与 head 状态一致性缺陷。
  - Ch9 已出现 `orphaned_settings=10`、`health_score=7.1`，设定回收闭环仍需继续修复或调参。

### 4.2.2 2026-06-28 Ch12 settlement_review 修复

- 修复范围: 真实科幻读数场景下，SettlementExtractor 将“温度/倒计时/仪表读数”过度台账化导致 `closing_value != opening_value + increments - decrements` 的问题。
- Prompt 约束: `prompts/cards/settlement_extractor/1.0.2.yaml` 明确要求 numerical_update 输出前自检公式；温度、倒计时、传感器读数若只是当前读数，应输出为 snapshot，`increments` / `decrements` 为空；倒计时统一换算为秒。
- 代码修复: `src/songyan/agents/settlement_extractor/_validate.py` 在公式校验前，仅对明确读数型属性且正文/quote 存在对应读数的 numerical_update 规整为 `telemetry_snapshot`；无读数证据时仍保持硬错误。
- 测试: `tests/test_settlement_extractor.py` 新增温度读数、倒计时读数、无证据不静默修正 3 个回归测试；`python -m pytest tests\test_settlement_extractor.py -q` 通过（65 passed, 1 xfailed）；后续 telemetry snapshot 扩展后当时全量 `python -m pytest tests/ -q` 通过（1914 passed, 1 xfailed）；最新全量结果见 4.2.6。
- 状态: Ch12 直接 settlement_review 阻塞已做代码修复，仍需在处理 Ch11 状态一致性后复跑 Ch1-Ch20 验证。

### 4.2.3 2026-06-28 Ch10 起点聚焦验证

- 运行方式: 将 `songyan.db` 备份到 `.tmp\task137_ch10_focus_20260628_120356.db`，在副本中清理 Task 137 项目 Ch11+ 残留，保留 Ch1-Ch10 accepted 锚点，执行 `python scripts/run_137_ch10_focus_validation.py`。
- Run ID: `run-b1ca636f`
- 运行窗口: Ch10-Ch12；Ch10 被 pipeline 识别为已 accepted 并跳过。
- 结果: `partial`，completed `[10]`，failed `[11]`，未进入 Ch12。
- 报告: `docs/reports/task-137-ch10-focus-validation-report.md`
- 结论:
  - 清理策略有效，未污染主库。
  - Ch11 不再出现上一轮 `success=true` 但 DB head 为 draft 的伪成功；本次 run log 正确记录 `success=false`、`error_stage=settlement_review`。
  - Ch12 读数型修复已覆盖温度字段；日志显示 `义肢温度` 被规整为 `telemetry_snapshot`。
  - 新阻塞: `数据同步完成度 closing_value (94.0)` 不等于公式值 `0.000`，说明“完成度/进度/百分比”也应纳入读数型 snapshot 规则。

### 4.2.4 完成度 / 进度 / 百分比读数 snapshot 扩展（已修复）

- 任务归属: 该问题不新增独立 task，归入 Task 137 的直接阻塞修复。
- 归属理由:
  - 触发证据来自 Task 137 Ch10 聚焦验证 `run-b1ca636f`。
  - 根因仍是“真实科幻读数被过度台账化”，只是读数类型从温度/倒计时扩展到完成度、进度、百分比。
  - 修复面较小，直接服务 Task 137 Ch10/Ch11 小窗口复跑与后续 Ch1-Ch20 验收。
- 触发证据:
  - Ch11 `settlement_review` 失败。
  - `数据同步完成度 closing_value (94.0)` 不等于公式值 `0.000`。
  - 同一轮日志显示 `义肢温度` 已被规整为 `telemetry_snapshot`，说明现有机制方向正确，但读数类型覆盖不足。
- 修复内容:
  - 已扩展 `_TELEMETRY_ATTRIBUTE_KEYWORDS`，覆盖 `完成度`、`进度`、`百分比`、`percent`、`progress`、`completion`。
  - 已增加百分比/进度读数解析，支持 `94%`、`94.0%`、`百分之九十四`、`九十四个百分点`，以及“完成度达到九十四”这类明确读数。
  - 仅在正文或 `source_quote` 存在明确读数证据时规整为 `telemetry_snapshot`；无证据时继续触发公式硬校验。
  - 已更新 `prompts/cards/settlement_extractor/1.0.2.yaml`，明确完成度/进度/百分比属于状态快照，不应编造增减台账。
  - 已补充回归测试：百分比读数可 snapshot、中文百分比可 snapshot、无证据不静默修正。
- 验证:
  - `python -m pytest tests\test_settlement_extractor.py -q` 通过（68 passed, 1 xfailed）。
  - `ruff check src\songyan\agents\settlement_extractor\_validate.py tests\test_settlement_extractor.py` 通过。
  - `python -m pytest tests/ -q` 当时通过（1914 passed, 1 xfailed）；最新全量结果见 4.2.6。
  - `ruff check src/ tests/` 通过。
  - 已复用副本 DB 策略从 Ch10 聚焦复跑，Ch11/Ch12 均通过；见 4.2.5。
- 非目标:
  - 不引入新的 numerical_update schema。
  - 不把所有数值错误都静默修正；修为、货币、生命值、库存等真实台账仍必须满足公式。

### 4.2.5 2026-06-28 telemetry 修复后 Ch10 起点聚焦复跑

- 运行方式: 删除旧 `.tmp\task137_ch10_focus_20260628_120356.db` 后，将 `songyan.db` 备份到 `.tmp\task137_ch10_focus_20260628_124015.db`，在副本中清理 Task 137 项目 Ch11+ 残留，保留 Ch1-Ch10 accepted 锚点，执行 `python scripts/run_137_ch10_focus_validation.py`。
- Run ID: `run-78f8d139`
- 运行窗口: Ch10-Ch12；Ch10 被 pipeline 识别为已 accepted 并跳过。
- 结果: `completed`，completed `[10, 11, 12]`，failed `[]`。
- 报告: `docs/reports/task-137-ch10-focus-validation-report.md`
- 关键验证:
  - Ch11 accepted: `v-11-6-ff4cea3d`。
  - Ch12 accepted: `rev-12-2-afa88d37`。
  - Ch11 run log: `success=true`、`settlement_success=true`、`summary_success=true`、`quality_gate_passed=true`、`skip_settlement=false`。
  - Ch12 run log: `success=true`、`settlement_success=true`、`summary_success=true`、`quality_gate_passed=true`、`skip_settlement=false`。
  - Writer manifest 退出后已恢复到 `default_version: "1.1.0"`。
- 结论:
  - 完成度/进度/百分比 telemetry snapshot 修复通过聚焦验证；`数据同步完成度` 不再阻断 settlement。
  - 温度/倒计时读数型 settlement 阻塞未复现。
  - Ch11 `success=true` / draft head 状态不一致未复现；本次 head 与 run log 一致。
  - 当前剩余主阻塞回到 Task 137 原目标：Ch12 continuity health 为 `3.0`，`orphaned_settings=27`，其中 P1=7；设定回收/刷新闭环仍需继续处理。

### 4.2.6 2026-06-28 orphan 分析后的刷新检测与 critical 优先级修复

- 触发证据: `run-78f8d139` Ch12 continuity report 中 `orphaned_settings=27`，其中 P1/critical 7 个。
- 分析结论:
  - 正文提及刷新检测过窄：`量子纠缠中继通信的相位偏移模式` 这类“术语 + 的”未被视为有效边界。
  - 复合 setting_name 缺少轻量别名：`第7远征队·静默节点`、`斐波那契周期循环（时间闭环）` 只能完整命中，无法由 `第7远征队` / `时间闭环` 刷新。
  - CreativeDirector 待回收列表只按 `last_mentioned_chapter` 排序，早期 background 会挤占更重要的 critical orphan。
- 修复内容:
  - `_term_in_content()` 允许术语后接 `的/了/在/为/与/、/，/。` 等常见语法边界，同时继续避免 `天剑` 误匹配 `天剑宗`。
  - 新增 `_setting_reference_terms()`，从复合 `setting_name` 中拆出轻量别名，支持 `第7远征队`、`静默节点`、`时间闭环` 这类片段命中。
  - `_load_active_settings_to_recycle()` 改为 `critical > recurring > technical > background > historical`，同类别内再按沉寂章数排序。
- 离线验证:
  - 使用本次 Ch12 accepted 正文重跑检测，新规则可命中 `SS-047号骸骨及日志` 与 `量子纠缠中继通信`。
- 测试:
  - `python -m pytest tests\test_task137_setting_recycling.py -q` 通过（15 passed）。
  - `python -m pytest tests\test_task135_continuity_governance.py tests\test_continuity_health_governance.py -q` 通过（33 passed）。
  - `ruff check src/ tests/` 通过。
  - `python -m pytest tests/ -q` 通过（1917 passed, 1 xfailed）。
- 状态:
  - 该修复尚未构成 Ch10-Ch12 实跑通过证据；下一步需复用副本 DB 从 Ch10 聚焦复跑，观察 Ch12 orphan 是否下降。

### 4.2.7 2026-06-28 刷新检测与 critical 优先级修复后 Ch10-Ch12 聚焦复跑

- 运行方式: 将 `songyan.db` 备份到 `.tmp\task137_ch10_focus_20260628_131959.db`，在副本中清理 Task 137 项目 Ch11+ 残留，保留 Ch1-Ch10 accepted 锚点，执行 `python scripts/run_137_ch10_focus_validation.py`。
- Run ID: `run-3c81be53`
- 运行窗口: Ch10-Ch12；Ch10 被 pipeline 识别为已 accepted 并跳过。
- 结果: `partial`，completed `[10, 11]`，failed `[12]`。
- 报告: `docs/reports/task-137-ch10-focus-validation-report.md`
- 关键验证:
  - Ch11 accepted: `rev-11-5-d6bfa9ae`。
  - Ch11 run log: `success=true`、`settlement_success=true`、`summary_success=true`、`quality_gate_passed=true`、`skip_settlement=false`。
  - Ch12 current head: `v-12-4-043289ad`，status=`draft`，无 accepted head。
  - Ch12 run log: `success=false`、`error_stage=settlement_review`、`settlement_success=false`、`settlement_needs_human_review=true`、`summary_success=false`、`quality_gate_passed=true`。
  - Writer manifest 退出后已恢复到 `default_version: "1.1.0"`。
- 结论:
  - Ch11 状态一致性继续通过，完成度/进度/百分比 telemetry 阻塞未复现。
  - Ch12 在 settlement_review 阶段阻断，未生成 continuity report；因此本轮无法判断 Ch12 `orphaned_settings=27` 是否下降。
  - 刷新检测与 critical 优先级修复仍缺少实跑 orphan 改善证据。
- 下一步:
  - 先定位本轮 Ch12 settlement validation 具体失败项，再复用副本 DB 从 Ch10 锚点重跑。

### 4.2.8 2026-06-28 Ch12 settlement_review 调查结论

- 调查对象: `run-3c81be53`、Ch12、DB `.tmp\task137_ch10_focus_20260628_131959.db`。
- 持久化缺口: Ch12 run log 只记录 `success=false`、`error_stage=settlement_review`、`settlement_success=false`、`settlement_needs_human_review=true`，但未持久化具体 `validation_errors`；当前仅凭 run log/DB 不能直接还原失败字段和值。
- 版本确认: 进入 settlement_review 的 Ch12 版本为 `v-12-4-043289ad`，该版本为 current head，status=`draft`，无 accepted head。
- 离线复现结论: 针对该版本离线复现 SettlementExtractor validation，暴露 `_build_numerical_update` 对 `opening_value='无'` 的 parse/build 脆弱点；该值在构造 numerical update 时会进入数值解析路径，导致 validation/build 阶段对“无值/未知初值”处理不稳定。
- 根因归类: 这不是应放宽公式硬校验的问题，而是无值数值字段在进入公式校验前缺少规范化语义，导致“无”这类非数值 opening value 进入台账公式链路。
- 修复方向: 保持 `closing_value == opening_value + increments - decrements` 的硬校验不放宽；仅规范 `opening_value` / 相关数值字段中“无、未知、未记录”等无值表达的解析与构造，并补充诊断输出和回归测试，确保下一次失败能记录具体 validation error。
- 状态: Task 137 仍不能归档；需先完成上述最小修复，再复用副本 DB 从 Ch10 锚点复跑 Ch10-Ch12，重新获取 Ch12 continuity/orphan 证据。

### 4.2.9 2026-06-28 Ch11 settlement_review 新阻断

- 调查对象: `run-0017b263`、Ch11、DB `.tmp\task137_ch10_focus_20260628_140250.db`。
- 运行结果: Ch10 已 accepted 并跳过；Ch11 `success=false`、`settlement_success=false`、`summary_success=false`、`quality_gate_passed=true`、`skip_settlement=false`，未进入 Ch12。
- 版本确认: 进入 settlement 的 Ch11 版本为 `rev-11-4-83d61722`，当前 head status=`draft`，无 accepted head。
- 已确认的非阻断项: `义肢温度` 已被规整为 `telemetry_snapshot`，上一轮温度读数型修复方向有效。
- 失败项: `char_001.舱壁文字数量`、`char_001.破译文字数量`、`char_001.自毁指令脉冲数`、`char_001.新组织生长速度` 的 telemetry snapshot 未被现有规则覆盖，导致这些读数仍进入 numerical formula validation 并失败。
- 根因归类: 这是 telemetry snapshot 规则覆盖不足导致的公式校验失败，不是 `source_quote`、`old_value` 或 `source_version_id` 问题。
- 状态: Task 137 仍不能归档；下一步应补齐上述 Ch11 telemetry snapshot 覆盖后，再复用副本 DB 从 Ch10 锚点复跑 Ch10-Ch12，重新获取 Ch12 continuity/orphan 证据。

### 4.2.10 2026-06-28 Ch11 遥测字段阻断复现

- 调查对象: `run-9e54a36d`、Ch11、DB `.tmp\task137_ch10_focus_20260628_144643.db`。
- 运行结果: Ch10 已 accepted 并跳过；Ch11 仍在 `settlement_review` 阶段失败，`success=false`、`settlement_success=false`、`summary_success=false`、`quality_gate_passed=true`、`skip_settlement=false`，未进入 Ch12。
- 版本确认: Ch11 current head 为 `v-11-6-10830627`，status=`draft`，无 accepted head。
- validation_errors:
  - `char_001.heart_rate`: closing value `130` vs expected `72`。
  - `char_001.oxygen_concentration`: closing value `16` vs expected `21`。
  - `char_001.chamber_pressure`: closing value `0.7` vs expected `1`。
  - `char_001.emp_countdown`: closing value `0` vs expected `3`。
- 已确认的非阻断项: `left_leg_prosthetic_temperature` 已被规整为 `telemetry_snapshot`，温度读数修复仍有效。
- 根因归类: 本轮失败项仍属于遥测读数/倒计时字段未覆盖，导致心率、氧浓度、舱压、EMP 倒计时这些当前读数被误送入 numerical formula validation；这不是应放宽真实台账公式硬校验的问题。
- Writer manifest 退出后已恢复到 `default_version: "1.1.0"`。
- 状态: Task 137 仍不能归档；下一步应最小扩展 telemetry snapshot 覆盖 `heart_rate`、`oxygen_concentration`、`chamber_pressure`、`emp_countdown`，再复用副本 DB 从 Ch10 锚点复跑 Ch10-Ch12，重新获取 Ch12 continuity/orphan 证据。

### 4.2.11 2026-06-28 Ch11 telemetry 通用读数规则缺口

- 调查对象: `run-a593705b`、Ch11、DB `.tmp\task137_ch10_focus_20260628_150218.db`。
- 运行结果: Ch10 已 accepted 并跳过；Ch11 仍在 `settlement_review` 阶段失败，`success=false`、`settlement_success=false`、`summary_success=false`、`quality_gate_passed=true`、`skip_settlement=false`，未进入 Ch12。
- 版本确认: Ch11 current head 为 `v-11-3-a9529bd9`，status=`draft`，无 accepted head。
- validation_errors:
  - `char_001.neck_chip_vibration_frequency`: closing value `42.7` vs expected `0`。
  - `char_001.heartbeat_to_breath_sync_ratio`: closing value `3.0` vs expected `0`。
  - `ss047_residual.phase_offset`: closing value `0.1` vs expected `0`。
- 根因归类: 单字段白名单仍不足；继续逐项补 `heart_rate`、`oxygen_concentration` 这类字段会反复遗漏同类传感器读数。应收敛为窄通用 telemetry 读数规则，覆盖 `frequency`、`ratio`、`phase_offset` 等读数型字段。
- 规则边界: 该通用规则只适用于有正文或 `source_quote` 明确读数证据的 telemetry snapshot；无证据字段、真实数量台账、资源/库存/修为/货币等仍必须走 `closing_value == opening_value + increments - decrements` 的公式硬校验。
- 状态: Task 137 仍不能归档；下一步应实现窄通用 telemetry 读数规则并补充测试，再复用副本 DB 从 Ch10 锚点复跑 Ch10-Ch12，重新获取 Ch12 continuity/orphan 证据。

### 4.2.12 2026-06-28 Ch11 时间/耗时读数阻断

- 任务归属: Task 4B.1 文档记录；本轮只记录阻断，不改代码。
- 调查对象: `run-28c904e3`、Ch11、DB `.tmp\task137_ch10_focus_20260628_172052.db`。
- 运行结果: Ch10 已 accepted 并跳过；Ch11 在 `settlement_review` 阶段失败，`success=false`、`settlement_success=false`、`summary_success=false`、`quality_gate_passed=true`、`skip_settlement=false`，未进入 Ch12。
- 版本确认: Ch11 current head 为 `rev-11-4-18909880`，status=`draft`，无 accepted head。
- validation_errors:
  - `laser_cutter_activation_time`: closing value `0.8` vs expected `0`。
- 根因归类: 该字段属于时间/耗时/激活时间类读数，但现有 telemetry snapshot 规则尚未覆盖，导致当前读数被误送入 numerical formula validation；这不是应放宽真实台账公式硬校验的问题。
- Writer manifest 退出后已恢复到 `default_version: "1.1.0"`。
- 状态: Task 137 仍不能归档；下一步应按 Task 4B.2 最小扩展 telemetry snapshot 规则覆盖有明确证据的时间/耗时/激活时间读数，并补测试后复跑 Ch10-Ch12。

### 4.2.13 2026-06-28 Ch11 门缝读数与倒计时归零阻断

- 任务归属: Task 4C.1 文档记录；本轮只记录阻断，不改代码。
- 调查对象: `run-66f6a266`、Ch11、DB `.tmp\task137_ch10_focus_20260628_173917.db`。
- 运行结果: Ch10 已 accepted 并跳过；Ch11 在 `settlement_review` 阶段失败，`success=false`、`settlement_success=false`、`summary_success=false`、`quality_gate_passed=true`、`skip_settlement=false`，未进入 Ch12。
- 版本确认: Ch11 current head 为 `rev-11-5-22e623a0`，status=`draft`，无 accepted head。
- validation_errors:
  - `core_chamber_door_gap`: closing_value `0.0` vs formula `50.000`。
  - `conversion_countdown`: closing_value `0.0` vs formula `30.000`。
- 根因归类: 门缝/间隙读数与倒计时归零读数尚未被现有 telemetry snapshot 规则覆盖，导致当前读数被误送入 numerical formula validation；这不是应放宽真实台账公式硬校验的问题。
- Writer manifest 退出后已恢复到 `default_version: "1.1.0"`。
- 状态: Task 137 仍不能归档；下一步应按 Task 4C.2 最小扩展 telemetry snapshot 规则覆盖有明确证据的 gap/间隙/门缝读数与 countdown 归零读数，并补测试后复跑 Ch10-Ch12。

### 4.2.14 2026-06-28 settlement_review 诊断持久化缺口

- 任务归属: Task 4E 文档记录；本轮只更新文档，不改代码。
- 调查对象: `run-7ea2e546`、Ch11、DB `.tmp\task137_ch10_focus_20260628_175609.db`。
- 运行结果: Ch10 已 accepted 并跳过；Ch11 停在 `settlement_review`，JSONL 记录 `error_stage=settlement_review`、`success=false`、`settlement_success=false`、`summary_success=false`、`quality_gate_passed=true`、`skip_settlement=false`，未进入 Ch12。
- 版本确认: Ch11 current head 为 `v-11-4-968ff60f`，status=`draft`，无 accepted head；但 run log 未持久化本次 settlement 输出对应的 `version_id`。
- 持久化缺口: JSONL/DB 可确认 `error_stage=settlement_review`，但没有可查询的 `validation_errors`；仅凭既有运行证据无法还原失败字段、closing value、expected/formula 或规整前后的 settlement payload。
- 复现成本: 离线复现必须重新调用 SettlementExtractor LLM，才能重新生成 settlement payload 并进入 validation；这会引入非确定性，也不符合“失败后直接从事实源定位”的闭环要求。
- 根因归类: 当前优先问题不是继续补单个 telemetry 字段，而是 settlement_review 失败诊断没有被持久化，导致每次失败定位依赖重新生成。
- 下一步: 先完成 Task 4E.1/4E.2，将 settlement `validation_errors` 与对应 `version_id` 写入 run log 或等价持久化证据，并补测试证明 settlement_review 失败时 JSONL/DB 可查；随后再复跑 Ch10-Ch12，用持久化诊断直接定位下一项。

### 4.2.15 2026-06-28 诊断持久化后 Ch10-Ch12 聚焦复跑

- 任务归属: Task 4E.3 / Task 138a.1-138a.2。
- 运行方式: 将 `songyan.db` 备份到 `.tmp\task137_ch10_focus_20260628_183255.db`，在副本中清理 Task 137 项目 Ch11+ 残留，保留 Ch1-Ch10 accepted 锚点，执行 `python scripts/run_137_ch10_focus_validation.py`。
- Run ID: `run-4ba8de9d`
- 运行窗口: Ch10-Ch12；Ch10 被 pipeline 识别为已 accepted 并跳过。
- 结果: `completed`，Ch11/Ch12 均 accepted。
- 关键验证:
  - Ch11 accepted: `rev-11-3-82c931d0`。
  - Ch12 accepted: `v-12-6-75a4b0c7`。
  - Ch12 run log: `success=true`、`settlement_success=true`、`summary_success=true`、`quality_gate_passed=true`、`settlement_validation_errors=[]`。
  - Ch12 continuity: `health=3.0`、`orphaned=19`、`forgotten=2`、`mismatches=0`。
  - Writer manifest 退出后已恢复到 `default_version: "1.1.0"`。
- 结论:
  - Task 4E 的诊断持久化修复没有引入回归；本轮已越过 settlement_review，Ch10-Ch12 聚焦复跑完成。
  - archive/合并策略有改善：Ch12 orphan 从上一轮成功复跑 `run-65fe0040` 的 24 降到 19；但 health 仍为 3.0，Task 137 不能归档。
  - 剩余阻塞转为 continuity health 收口：需继续定位剩余 19 个 orphan 中 background 未 archive 与 critical 未刷新/未合并的最小根因。

### 4.2.16 2026-06-28 后续任务拆分为 Task 138a-138e

- 触发原因: `run-4ba8de9d` 已越过 Ch11/Ch12 settlement、summary、quality gate，当前阻塞不再是 `settlement_review`，而是 Ch12 continuity `health=3.0`、`orphaned=19`。
- 调整原则:
  - 不再直接扩大到 Ch1-Ch20/default run。
  - 先分类剩余 orphan，再决定是否修代码、调规则、补 human mark 或文档收尾。
  - 只有完成最小修复后，才复跑 Ch10-Ch12 验证。
- 新顺序:
  1. Task 138a: 分类剩余 19 个 orphan，输出 category / tracking / snapshot / last mention / root cause 表。
  2. Task 138b: 基于分类结果确定最小动作，明确做什么、不做什么、验收指标。
  3. Task 138c: 实施最小修复或 human mark，补目标测试并记录风险边界。
  4. Task 138d: 使用副本 DB 复跑 Ch10-Ch12，比较 `run-4ba8de9d` 的 `orphaned=19`、`health=3.0`。
  5. Task 138e: 同步事实源、运行必要测试，并决定归档或进入下一轮 Task 138a。
- 任务文件: `.trae/specs/complete-v51-remaining-tasks/tasks.md`

### 4.2.17 2026-06-28 Task 138a 剩余 orphan 分类结论

- 数据源: `.tmp\task137_ch10_focus_20260628_183255.db`、`run-4ba8de9d`、Ch12 accepted `v-12-6-75a4b0c7`、continuity report `cont_e754c0a9`。
- 只读查询结论:
  - Ch12 continuity 仍为 `health=3.0`、`orphaned=19`、`forgotten=2`、`mismatches=0`。
  - orphan 原始类别: `critical=4`、`background=13`、`technical=2`。
  - 19/19 均为 `setting_tracking.status=active`、`recovery_required=0`、`setting_snapshots.lifecycle_status=active(1)`。
  - 8/19 存在 active unresolved setting human mark；11/19 无 active human mark。
- 分类结果:
  - `critical 未刷新/未合并`: 2 个，代表 `第7远征队·静默节点`、`相位冲刷机制`。
  - `background/technical 未 archive`: 9 个，代表 `手掌凹槽识别系统`、`量子态数据晶体`、`遗迹通道辐射标记`。
  - `命名/别名/canonical 未命中`: 7 个，代表 `英仙臂外侧巨型遗迹`、`非本地时空标记系统`、`斐波那契频率跳变序列`。
  - `应转 human mark 或人工保留`: 1 个，`《边缘星域紧急征召法》第七条`。
  - `真实 orphan`: 0 个，待 Task 138b 在 human mark/archive 决策后再复核。
- 最小根因:
  - stale `background/technical` 未 archive 是数量主因。
  - 正文已有提及但 canonical/alias 粒度未命中是误报主因。
  - active human mark 未形成“促成回收或 resolve”的闭环。
  - 2 个 critical 项确实未在 Ch11/Ch12 accepted 正文中出现，需要单独决策。
- Task 138b 输入:
  - 先决定 7 个 alias/canonical miss 是否以规则/同簇 merge 修正。
  - 再决定 9 个 stale background/technical 的 archive 或评分过滤边界，保护 `critical`、`recurring`、`recovery_required=1` 与人工保留项。
  - 对 `《边缘星域紧急征召法》第七条` 明确保留为人工事实源还是取消强制回收并 archive。
  - 对 2 个 critical 真缺口决定补回收、合并或人工保留；在此之前不扩大到 Ch1-Ch20/default run。

### 4.2.18 2026-06-28 Task 138b 最小动作决策

- 决策原则:
  - 继续只处理 `run-4ba8de9d` Ch12 剩余 19 个 orphan 的局部根因，不直接扩大到 Ch1-Ch20/default run。
  - 误报类优先走代码/规则收口；人工保留类必须进入 human mark 或等价事实源；critical 不 archive、不从评分中过滤。
  - Task 138c 完成目标测试和 lint 后，才进入 Task 138d 用副本 DB 复跑 Ch10-Ch12。
- 分类处理:
  - `critical 未刷新/未合并` 2 个: 代码修复 + human mark 闭环。将 active unresolved critical mark 或 critical stale setting 纳入 CreativeDirector/回收输入高优先级目标；若存在同簇 setting，走 canonical/alias 合并；仍无正文证据时保留为人工待回收项。
  - `background/technical 未 archive` 9 个: 阈值/规则调整为主。对 `recovery_required=0`、非 critical/recurring、无 active human mark 的长期沉寂项 archive 或从 ContinuityAuditor orphan 评分中过滤；有 active human mark 的项先进入人工保留/待回收判定。
  - `命名/别名/canonical 未命中` 7 个: 代码修复。扩展正文引用检测与 canonical alias 规则，覆盖“巨型遗迹外层/巨型遗迹”、“斐波那契序列频率/频率跳变序列”、“时空标记系统/非本地时空标记”等同簇表达，同时保留边界和长度约束。
  - `应转 human mark 或人工保留` 1 个: `《边缘星域紧急征召法》第七条` 默认作为人工保留世界观前提，写入可查询 human mark/等价事实源并从自动 orphan 惩罚中豁免；若后续证据证明不保留，再按 background stale archive。
  - `真实 orphan` 0 个: 本轮暂不处理，不新增正文重写或大范围 prompt 改造。
- 不扩大到 Ch1-Ch20/default run 的理由:
  - Task 138a 已证明剩余 19 个 orphan 主要由局部 alias、archive/过滤与 human mark 闭环导致，尚未到“局部修复无法继续下降”的阶段。
  - Ch10-Ch12 baseline 已 completed 且 settlement/summary/QG 通过；直接扩大窗口会混入 Writer 生成差异、长窗口累积和 default run 成本，削弱因果判断。
  - 正确顺序是 Task 138c 先完成最小代码/规则/human mark 修复，再由 Task 138d 复跑 Ch10-Ch12 比较 `orphaned=19`、`health=3.0`。
- Task 138c 输入:
  - 改动范围: SettingEvaporator/archive 触发、ContinuityAuditor orphan 评分过滤、setting reference/alias 检测、CreativeDirector/回收输入组装、human mark resolve/豁免逻辑；不改 Writer/Revision/LLMAuditor 职责边界，不放宽 settlement 硬校验。
  - 测试范围: 覆盖 stale background/technical archive 或过滤、alias/canonical 刷新、active human mark 人工保留/豁免，并加入负例保护 `critical`、`recurring`、`recovery_required=1` 与宽泛词误匹配。
  - 验收指标: 目标测试证明 7 个 alias/canonical miss 可刷新或同簇识别，9 个 stale background/technical 中无 active human mark 的项可 archive/过滤，active human mark 项不被静默 archive，2 个 critical 缺口进入高优先级回收输入或人工待回收事实源；随后 Task 138d 复跑 Ch10-Ch12 时 Ch12 `orphaned` 必须低于 19，目标降至 8 以下或 health 脱离 `3.0`。

### 4.2.19 2026-06-28 Task 138c 剩余 orphan 最小修复

- 代码修复:
  - `archive_long_silent_nonessential()` 现在保护所有 active unresolved setting human mark，不再只保护 `priority >= 8`；critical/recurring/recovery_required 仍不被 archive。
  - ContinuityAuditor orphan 扫描对非 critical/recurring 且存在 active human mark 的设定豁免自动 orphan 惩罚；critical/recurring 不过滤。
  - setting reference/canonical alias 扩展到 `巨型遗迹外层/表面/非欧几何合金`、`斐波那契序列频率/频率跳变序列`、`时空标记系统/非本地时空标记`、`墙壁能量纹路/遗迹墙壁活体特性`。
  - CreativeDirector 回收输入纳入 active unresolved setting human mark；active critical mark 即使未达到沉寂章数也会进入高优先级回收目标。
- 负例保护:
  - 裸 `频率`、裸 `墙壁`、裸 `巨型遗迹` 不作为 alias 刷新依据。
  - active human mark 项不被静默吞掉：非关键项只豁免自动 orphan 惩罚，仍保留 human mark/回收输入路径。
  - 未修改 Writer 生成策略，未放宽 settlement numerical ledger 硬校验。
- 测试:
  - `python -m pytest tests/test_task137_setting_recycling.py -q` -> `24 passed`。
  - `python -m pytest tests/test_task137_setting_recycling.py tests/test_task135_continuity_governance.py tests/test_continuity_health_governance.py -q` -> `57 passed`。
  - `ruff check src/ tests/` -> passed。
- 状态:
  - Task 138c 已完成代码/测试/文档。
  - Task 138d 已执行 Ch10-Ch12 副本 DB 复跑；Ch12 continuity 从 baseline `orphaned=19` 下降到 `orphaned=16`，`health=3.0` 持平。

### 4.2.20 2026-06-28 Task 138d Ch10-Ch12 副本 DB 聚焦复跑

- Run ID: `run-4fd48756`
- DB: `.tmp/task138d_ch10_focus_20260628_201716.db`
- 运行窗口: Ch10-Ch12；保留 Ch1-Ch10 accepted，清理 Ch11+ 残留后运行。
- 结果: `completed`，`current_chapter=12`，`completed_chapters=[10, 11, 12]`，`failed_chapters=[]`。
- Heads:
  - Ch10 accepted: `v-10-6-4c80f8c7`
  - Ch11 accepted: `rev-11-3-a31b2add`
  - Ch12 accepted: `v-12-3-a240b75d`
- Run log:
  - Ch11/Ch12 均 `success=true`、`settlement_success=true`、`summary_success=true`、`quality_gate_passed=true`。
  - `settlement_validation_errors=[]`，未出现新的 settlement_review 阻断。
- Writer manifest:
  - 运行期间临时启用 Writer `1.2.0`。
  - 退出后已恢复为 `default_version: "1.1.0"`。
- Ch12 continuity 对比:
  - Baseline `run-4ba8de9d`: `health=3.0`、`orphaned=19`、`forgotten=2`、`mismatches=0`。
  - Task 138d `run-4fd48756`: `health=3.0`、`orphaned=16`、`forgotten=2`、`mismatches=0`。
  - orphan 下降 3，health 仍未脱离 3.0。
- 结论:
  - Task 138c 的局部 alias/archive/human mark 相关修复在同口径复跑中有效，但不足以归档 Task 137。
  - 下一步进入 Task 138e 同步事实源并判断收尾路径；若不归档，则基于 `run-4fd48756` 的剩余 16 个 orphan 重新分类，不直接扩大到 Ch1-Ch20/default run。

### 4.2.21 2026-06-28 Task 138e 事实源同步与收尾判断

- 同步对象: `.trae/specs/complete-v51-remaining-tasks/tasks.md`、`checklist.md`、`progress.md`、`docs/STATUS.md`、`tasks/V5-README.md`、`README.md`、`docs/INDEX.md`、`tasks/138e-task137-fact-sync-and-closure.md`、`docs/reports/task-137-ch10-focus-validation-report.md`。
- 最新证据仍以 Task 138d 为准: `run-4fd48756`、DB `.tmp/task138d_ch10_focus_20260628_201716.db`，Ch10-Ch12 completed；Ch11/Ch12 settlement、summary、quality gate 均通过，`settlement_validation_errors=[]`。
- Continuity 判断: Ch12 orphan 从 baseline `run-4ba8de9d` 的 19 降至 16，但 `health=3.0` 持平，`forgotten=2`、`mismatches=0` 持平。
- 验证结果: `python -m pytest tests/test_task137_setting_recycling.py tests/test_task135_continuity_governance.py tests/test_continuity_health_governance.py -q` -> `57 passed in 4.72s`；`ruff check src/ tests/` -> `All checks passed!`。
- 收尾结论: Task 137 不能归档；不创建 `tasks/137-setting-recycling-closed-loop-DONE.md`。
- 下一轮入口: 保持本文件活跃，回到 Task 138a，对 `run-4fd48756` 的 16 个 orphan 重新分类；继续不扩大到 Ch1-Ch20/default run。

### 4.2.22 2026-06-28 Task 138a-R2 剩余 16 个 orphan 重新分类

- 数据源: `.tmp\task138d_ch10_focus_20260628_201716.db`、`run-4fd48756`、Ch12 accepted `v-12-3-a240b75d`、continuity report `cont_6ff93a98`。
- 运行状态复核: Ch10-Ch12 completed；Ch11/Ch12 均 `success=true`、`settlement_success=true`、`summary_success=true`、`quality_gate_passed=true`，`settlement_validation_errors=[]`。
- 当前 continuity: `health=3.0`、`orphaned=16`、`forgotten=2`、`mismatches=0`。
- 只读查询结论:
  - 原始类别: `critical=4`、`background=9`、`technical=3`。
  - 16/16 均为 `setting_tracking.status=active`、`recovery_required=0`、`setting_snapshots.lifecycle_status=active(1)`。
  - 8/16 存在 active unresolved setting mark；这些 mark 均由本次 Ch12 continuity report 生成，不是复跑前人工保留事实。
- 分类结果:
  - `critical 真缺口`: 3 个，`第7远征队·静默节点`、`相位冲刷机制`、`遗迹墙壁活体特性`。
  - `background/technical 未 archive`: 12 个，代表 `手掌凹槽识别系统`、`非本地时空标记系统`、`斐波那契相位偏移参数`。
  - `alias/canonical 未命中`: 1 个，`巨型遗迹表面材料特性`；Ch12 accepted 有“非欧几何合金碎片”“巨型遗迹表面的能量纹路”，但 tracking 仍停在 Ch3。
  - `human mark/人工保留`: 0 个；当前 8 条 active mark 均为本次 report 新建的待回收诊断。
  - `真实 orphan`: 0 个，待 Task 138b-R2 决策 archive/human mark 策略后再复核。
- 与上一轮 19 项对比:
  - key 级事实是 4 个旧项消失 + 1 个新项出现 = orphan 净减少 3。
  - 消失旧项: `location.perseus.arm_mega_ruin`、`law.emergency.conscription_act_article_7`、`artifact.silent_ruins.gate_inscription`、`artifact.mega_ruin.space_folding_defense`。
  - 新增项: `technology.fibonacci.phase_shift_parameter`。
  - 可能原因: `英仙臂外侧巨型遗迹` 被 Ch12 明确提及并 refresh；另外 3 个消失项主要受 Task 138c 的 active human mark 豁免影响，其中 `静默遗迹门禁铭文` 也有 Ch12 正文提及证据。
- 最小根因:
  - stale `background/technical` active 项未 archive/过滤仍是数量主因。
  - critical 回收输入仍不足，当前 3 个 critical 在 Ch11/Ch12 accepted 正文中没有足够证据。
  - alias/canonical 仍有窄缺口，尤其是 `巨型遗迹表面材料特性`。
- 下一步: 建议进入 Task 138b-R2，继续做最小动作决策；不建议直接扩大到 Ch1-Ch20/default run。

### 4.2.23 2026-06-28 Task 138b-R2 最小动作决策

- 决策对象: `run-4fd48756` / `.tmp\task138d_ch10_focus_20260628_201716.db` / Ch12 continuity `health=3.0`、`orphaned=16`、`forgotten=2`、`mismatches=0`。
- 分类处理:
  - `critical 真缺口` 3 个: `第7远征队·静默节点`、`相位冲刷机制`、`遗迹墙壁活体特性` 不 archive、不评分过滤；Task 138c-R2 应让 stale critical setting 在章节生成前进入高优先级回收输入，并保留 Ch12 新建 P1 mark 作为人工待回收证据。
  - `background/technical 未 archive` 12 个: 以 archive 或 ContinuityAuditor orphan 评分过滤为主；这些项均为 non-critical、non-recurring、`recovery_required=0`，且 Ch11/Ch12 无足够 accepted 正文证据。Ch12 report 新建 mark 只视为诊断，不升级为人工保留。
  - `alias/canonical 未命中` 1 个: `artifact.mega_ruin.surface_material` 走窄代码修复，允许“非欧几何合金碎片”“巨型遗迹表面的能量纹路”刷新，禁止裸 `巨型遗迹` 或裸 `能量纹路` 误命中。
  - `human mark/人工保留` 0 个、`真实 orphan` 0 个: 本轮暂不新增人工保留项，不做正文重写或大范围 prompt 改造。
- 本轮边界: 只更新决策文档与规格勾选；不改 `src/`、`prompts/`、数据库或脚本，不复跑，不运行 pytest/ruff。
- 不扩大到 Ch1-Ch20/default run 的理由: `run-4fd48756` 已证明局部修复仍能让 orphan 从 19 降到 16，剩余根因仍集中在局部规则与回收输入；直接扩大窗口会混入 Writer 生成波动、human mark 生命周期和 default 配置差异，削弱因果判断。
- Task 138c-R2 输入:
  - 改动范围: stale background/technical archive 或 orphan 评分过滤、stale critical 前置回收输入、`surface_material` 窄 alias/canonical refresh、区分 report 新建诊断 mark 与复跑前人工保留 mark。
  - 测试范围: 目标单测覆盖上述四条分支，并加入 critical/recurring/recovery_required 保护、宽泛词误匹配、人工保留 mark 不被静默 archive 的负例；完成后跑目标 pytest 与 `ruff check src/ tests/`。
  - 风险边界: 不放宽 settlement 硬校验，不新增 Agent/Workflow 节点，不让 current report 新建 mark 成为永久豁免，不用 alias 宽匹配吞掉真实 orphan。
  - 验收指标: Task 138d-R2 副本 DB 复跑 Ch10-Ch12 时 Ch11/Ch12 settlement、summary、QG 均通过，`settlement_validation_errors=[]`；Ch12 `orphaned` 低于 `run-4fd48756` baseline 16，目标降至 8 以下或 health 脱离 `3.0`。

### 4.2.24 2026-06-28 Task 138c-R2 第二轮最小修复

- 代码修复:
  - `archive_long_silent_nonessential()` 与 ContinuityAuditor orphan 过滤开始区分人工/历史 mark 与当前章节同章 `continuity_auditor` 诊断 mark；同章诊断 mark 不再永久豁免 non-critical stale orphan。
  - stale background/technical 处理仍保护 `critical`、`recurring`、`recovery_required=1`，且保护复跑前已有人工 mark 或历史 continuity mark。
  - CreativeDirector 回收输入忽略当前章节同章诊断 mark，但 stale critical setting 仍按类别优先级进入章节生成前回收输入，不依赖同章 report 事后 mark。
  - `artifact.mega_ruin.surface_material` alias 收紧为“非欧几何合金碎片”“巨型遗迹表面的能量纹路”等明确短语；移除“巨型遗迹表面”“巨型遗迹外层”等过宽刷新词。
- 负例保护:
  - 裸 `巨型遗迹`、裸 `能量纹路` 不刷新 `surface_material`。
  - current report 新建 non-critical diagnostic mark 不阻止 archive/过滤；历史 mark 仍可作为人工保留或待回收事实源。
  - critical/recurring 不因 human mark 被 ContinuityAuditor 过滤。
- 测试:
  - `python -m pytest tests/test_task137_setting_recycling.py tests/test_task135_continuity_governance.py tests/test_continuity_health_governance.py -q` -> `60 passed in 4.36s`。
  - `ruff check src/ tests/` -> `All checks passed!`。
- 状态:
  - Task 138c-R2 已完成代码/规则/测试/文档。
  - 本轮未执行 Ch10-Ch12 复跑，未执行 Ch1-Ch20/default run。
  - 可以进入 Task 138d-R2：使用副本 DB 复跑 Ch10-Ch12，验证 Ch12 `orphaned` 是否低于 `run-4fd48756` baseline 16，目标降至 8 以下或 health 脱离 `3.0`。

### 4.2.25 2026-06-28 Task 138d-R2 settlement_review 温度读数阻断

- 失败证据:
  - Run ID: `run-5054ac69`
  - DB: `.tmp/task138d_r2_ch10_focus_20260628_212448.db`
  - Ch12 version: `v-12-3-b76b6b4f`
  - Ch12 停在 `settlement_review`，run log 记录 `settlement_validation_errors=["角色 lin_shen 的 left_leg_prosthetic_temperature closing_value (50.6) 不等于 公式值 (52.000)"]`。
  - Ch12 正文存在明确遥测读数证据: `左腿义肢的温度继续下降。52.0，51.3，50.6。`
- 根因:
  - `left_leg_prosthetic_temperature` 已被识别为 telemetry attribute。
  - 现有温度读数规则只提取带 `度` 的数字/中文数字，未覆盖“温度关键词 + 无单位小数序列”。
  - 因未规整为 `telemetry_snapshot`，validation 继续按真实 numerical ledger 公式校验并阻断。
- 最小修复:
  - `src/songyan/agents/settlement_extractor/_validate.py` 扩展温度读数提取：明确温度关键词后的短窗口可提取无单位小数序列。
  - 证据仍必须来自正文或 `source_quote`，`formula` 不作为证据。
  - 真实资源/库存/数量类 numerical ledger 仍走 `closing_value == formula` 硬校验。
- 测试:
  - `python -m pytest tests/test_settlement_extractor.py -q` -> `103 passed, 1 xfailed in 27.21s`。
  - `ruff check src/songyan/agents/settlement_extractor/_validate.py tests/test_settlement_extractor.py` -> `All checks passed!`。
- 状态:
  - 本轮只完成阻断定位与最小代码修复，未执行 Ch10-Ch12 复跑。
  - Task 138d-R2 仍未完成；下一步可重新发起新的 138d-R2 retry。

### 4.3 文档

- [x] 更新 `docs/STATUS.md`、`tasks/V5-README.md`、`README.md`、`docs/INDEX.md`。
- [ ] 将本文件归档为 `tasks/137-setting-recycling-closed-loop-DONE.md`。（Task 138e 判断未达归档条件，暂不创建 DONE。）

### 4.4 2026-06-28 Task 138d-R2 retry 结果

- 已执行新的副本 DB retry:
  - `run-1155c92a` / `.tmp/task138d_r2_retry_ch10_focus_20260628_221500.db`
  - `run-9f87da6f` / `.tmp/task138d_r2_retry2_ch10_focus_20260628_222000.db`
- 中间修复:
  - `neural_pattern_match_rate` 的明确百分比读数可规整为 telemetry snapshot。
  - `47小时21分03秒` 这类中文小时/分钟/秒倒计时可换算为秒并规整为 telemetry snapshot。
  - `python -m pytest tests/test_settlement_extractor.py -q` -> `106 passed, 1 xfailed in 28.71s`。
  - `ruff check src/songyan/agents/settlement_extractor/_validate.py tests/test_settlement_extractor.py` -> `All checks passed!`。
- 最新 retry 结果:
  - `run-9f87da6f` 停在 Ch11 `settlement_review`，Ch11 draft `v-11-6-f0aea93b`，未进入 Ch12。
  - run log validation error: `角色 lin_shen 的 consciousness_upload_progress closing_value (60.0) 不等于 公式值 (33.300)`。
  - Ch11 正文未找到明确 `60%/60.0` 读数证据，不能按无证据 telemetry snapshot 静默放过。
  - Writer manifest 已恢复为 `default_version: "1.1.0"`。
- 状态:
  - Task 138d-R2 未完成，未生成 Ch12 continuity，无法验证 Ch12 orphan 是否低于 baseline 16。
  - 不创建 Task 138e-R2，不归档 Task 137。
  - 下一步应先处理 `consciousness_upload_progress` 的 settlement 输出/证据缺口，再重新发起副本 DB 复跑。

### 4.5 2026-06-28 Task 138f Settlement 数值证据门禁完成

- 目标:
  - 结束 Task 138d-R2 中“每复跑一次补一个 numerical_update 字段”的模式。
  - 将 SettlementExtractor 的数值结算从 LLM 自由生成改为 evidence-gated 候选。
- 证据定位:
  - `run-9f87da6f` / Ch11 `v-11-6-f0aea93b` 正文有“进度条”“大约三分之一”等图形化/概念性描述。
  - 正文没有明确 `60.0`、`60%`、`60％`、`六十`、`百分之六十` 读数证据。
  - `consciousness_upload_progress=60.0` 判定为无证据 telemetry 候选，不应作为硬结算阻断继续卡住复跑。
- 代码修复:
  - `_validate_settlement()` 引入 numerical_update evidence gate。
  - 有明确读数证据的 telemetry snapshot 继续规整为 `telemetry_snapshot`。
  - 无明确读数证据且公式不闭合的 telemetry numerical_update 被过滤，并记录 `settlement.numerical_unevidenced_filtered` warning。
  - 非 telemetry 的真实 ledger 公式错误仍进入 `validation_errors`，不放宽硬校验。
- Prompt 修复:
  - `prompts/cards/settlement_extractor/1.0.2.yaml` 增加证据门禁要求。
  - 没有正文或 `source_quote` 明确数字证据时禁止输出 numerical_update。
- 测试:
  - `python -m pytest tests/test_settlement_extractor.py -q` -> `111 passed, 1 xfailed in 18.83s`。
  - `ruff check src/songyan/agents/settlement_extractor/_validate.py tests/test_settlement_extractor.py` -> `All checks passed!`。
  - `ruff check src/ tests/` -> `All checks passed!`。
  - `python -m pytest tests/ -q` -> `1973 passed, 1 xfailed, 2 warnings in 299.26s`。
- 状态:
  - Task 138f 已完成。
  - 可以重新发起新的 Task 138d-R2 Ch10-Ch12 副本 DB retry。

### 4.6 2026-06-29 Task 138g critical orphan 根因复核与复跑

- 背景:
  - Task 138d-R2 retry4 `run-bcee6ab6` 已解除 settlement 阻断，Ch12 continuity 为 `health=3.0`、`orphaned=14`。
  - health 仍为 3.0 的直接原因是剩余 3 个 critical orphan。
- 语义复核:
  - `artifact.mega_ruin.surface_material`: Ch12 retry4 正文曾有明确材料证据，判定为 `refresh_missing`。
  - `organization.expedition.team_7`: Ch12 retry4 无明确证据，判定为 `planner_recall`，不 archive、不降级、不伪刷新。
  - `artifact.ruin.phase_flush_mechanism`: Ch12 retry4 无完整机制证据，判定为 `planner_recall`，不使用裸 `相位` / `相位偏移` 刷新。
- 代码/测试:
  - `surface_material` 窄 alias 已补强。
  - CreativeDirector 对 stale critical 项输出 P1 处理要求。
  - `python -m pytest tests/test_task137_setting_recycling.py tests/test_task135_continuity_governance.py tests/test_continuity_health_governance.py -q` -> `70 passed`。
  - `ruff check src/ tests/` -> `All checks passed!`。
- 复跑:
  - Run ID: `run-715f7d09`
  - DB: `.tmp/task138g_ch10_focus_20260629_105803.db`
  - Ch11/Ch12 settlement、summary、QG 全过，`settlement_validation_errors=[]`。
  - Ch12 continuity: `health=3.0`、`orphaned=16`、critical orphan=4、`mismatches=0`。
- 结论:
  - Task 138g 未收口。
  - `organization.expedition.team_7` 被本次 Ch12 正文提及后不再 orphan，但 `surface_material` 没有出现在本次 Ch12 正文，仍无法刷新。
  - 新增 E-7 critical orphan，说明仅增强 CreativeDirector 提示不足以稳定落实 critical recall。
  - 下一步应复核 Writer 输入中的连续性审计约束是否足够具体，以及 critical orphan 是否需要进入更强的 Writer/QG 前置检查；不应继续补单个 alias。

---

## 5. 风险与回滚

| 风险 | 影响 | 缓解 |
|---|---|---|
| 正文扫描误匹配导致错误刷新 | 让本应为 orphan 的设定被“伪回收” | 要求匹配词长度 ≥3 且为完整词边界；结合 LLM 显式 `recycled_settings` 交叉验证 |
| SettingEvaporator 分母变小导致重要设定被 archive | 关键伏笔丢失 | critical/recurring 仍使用较大分母；archive 仅改 `status`，记录保留，可随时恢复 |
| human_mark 自动 resolve 后，下章又变 orphan | resolve 条件过宽 | 要求 setting 被提及且为“有意义的剧情参与”，由 source_quote 过滤短/无意义匹配 |

---

## 6. 依赖关系

```
Task 135 设定回收与 continuity health 治理 ──┐
Task 136 V5.2 enforce Ch1–Ch20 验证 ──────────┼──► Task 137 设定回收闭环与 tracking 刷新机制
```

---

## 7. 交付物

- `tasks/137-setting-recycling-closed-loop-DONE.md`（暂不创建；Task 138e 判断 Task 137 仍活跃）
- `src/songyan/agents/settlement_extractor/_apply.py` 改动
- `prompts/cards/settlement_extractor/1.0.2.yaml` 改动
- `src/songyan/agents/settlement_extractor/_validate.py` 改动
- `src/songyan/db/lifecycle_cleaners.py` / `src/songyan/agents/setting_evaporator/__init__.py` 改动
- `src/songyan/agents/creative_director/__init__.py` 改动
- 新增/补强测试文件
- `docs/reports/task-137-v52-enforce-ch1-ch20-rerun-report.md`（实跑后生成，结果未通过）
