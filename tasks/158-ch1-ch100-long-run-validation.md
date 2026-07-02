# Task 158: Ch1-Ch100 长跑验证（无人值守 + kill→resume + T5 冻结）

> **Phase**: V6 阶段 D（长窗口验证）
> **优先级**: P0（§1.3-R 可靠性判据的唯一实跑场景；T5 红线在此首次实测冻结）
> **依赖**: Task 157 已交付验收 harness 且 Ch1-Ch50 首窗达标；阶段 C（153 resume / 154 限流预算 / 155 隔离 / 156 DB 维护）已合入
> **预计工作量**: 大（长跑 >10h；拆 158a 无人值守长跑 + kill→resume 演练 + 158b 五类曲线 + T5 冻结）
> **事实入口**: `tasks/V6-README.md`；规划：`docs/v6-plan.md` §3 阶段 D

---

## Goal

用**单条命令无人值守**跑通 **Ch1-Ch100**，中途至少一次人为 kill 后用**同一命令 `--resume` 续完**（§1.3-R），全程五类长期曲线（orphan 总量 / T7 新 critical 速率 / 质量债 / 文学趋势 / 弧级伏笔兑现率）可读，且不触 T3/T4/T5/T6 任一红线。本 Task 同时**首次实测并冻结 T5**（Ch100 时 DB ≤300MB、连续性扫描耗时 ≤ 基线 ×1.5），因为 148z 已把 T5 延后到此长跑（v6-plan L54）。

## Context

设计核实（2026-07-02，创建前对主干代码核对）：

- **无人值守长跑入口**：`songyan run --project-id <p> --chapters 1-100 --auto-confirm --gate-mode enforce`（`cli/main.py:435`）→ `run_project_pipeline`（`phase2_graph.py:294`）。enforce 门禁经 `GateConfig.for_mode`（main.py L487）。
- **kill→resume（Task 153）**：`songyan run --resume`（复用最近未完成 run）或 `--run-id <id>`。resume 以 `accepted` head 为唯一完成事实源（`_compute_resume_start`）、从 `summaries` 表重建摘要、重算前 `prune_orphan_checkpoints`；stuck-at-`running`（硬 kill 遗留）可续；paused（AutoHalt）续跑仍走门禁。**这是本 Task 要实跑证明的核心能力**。
- **失败隔离（Task 155）**：`--on-failure isolate`（默认）单章失败不终止整批、进 `chapters_failed` 清单；AutoHalt/enforce 门禁仍硬停。长跑用隔离可避免单章抖动白跑，但会产生 partial（DONE 记录 on_failure 选型）。
- **限流预算（Task 154）**：`llm_run_call_budget` 默认 0（关闭）；长跑可显式设正值防失控烧调用，超预算 `LLMBudgetExceededError` → run `paused` → 可 `--resume` 续（续跑重置计数）。DONE 记录是否启用预算及取值。
- **DB 维护 + T5 遥测（Task 156）**：主循环每 `_DB_MAINTENANCE_INTERVAL=10` 章 `wal_checkpoint(TRUNCATE)+optimize`（`_run_db_maintenance`，phase2_graph.py），采样 DB/WAL 尺寸 + `find_orphaned` 扫描耗时入 `run_db_metrics`；收尾 `final=True` 且 >200MB 尝试 `VACUUM`。**T5 判定函数 `check_t5_size_redline`/`check_t5_latency_redline` 已就绪（Task 156），本 Task 提供 Ch100 真实数据把 T5 从"待测"变"冻结"**。
- **验收判据 harness（Task 157 交付）**：`evals/v6_acceptance.py` 的 `evaluate_v6_acceptance(project_id, 1, 100, run_id=..., run_logs=...)` 一次性出 T1-T8 三态。**本 Task 不重写判据，只调用**。
- **五类曲线来源**：orphan=`collect_orphan_metrics`；T7=`collect_new_critical_rate`；质量债=`compute_quality_debt`；文学趋势=`collect_literary_scores`+`detect_literary_trend`；弧级兑现=`collect_arc_fulfillment`。`render_stage_a_metrics(project_id,1,100)`（`songyan metrics --chapters 1-100`）一次性渲染五类段。
- **T5 场景依据**：148z 冻结 T3/T6a/T6b/T8，**T4/T5 延后**——T4 已在 Task 157 的 50 章满窗首判，T5 需 Ch100 规模（v6-plan L54：干净 150ch 基线 ≈196MB 待重测）。
- **历史基线对照**：`run-a2bed648`（V5.1 Ch1-Ch150 干净 single-run，STATUS 载）与 138k/138n。

**为什么现在做**：157 证明了 50 章窗口达标 + harness 可信；158 是唯一能验证"无人值守 + 中断恢复 + 100 章规模不触红线"的场景，也是 T5 唯一真实标定点。§1.3-R 只有靠一次真实 kill→resume 续完才能判真。

## Cross-Task Coordination（阶段 D 统一口径）

- **判据复用 157**：T1-T8 全部经 `evaluate_v6_acceptance` 判，158 不新增/不修改判据函数。若 100 章暴露 harness 判据本身的 bug（如某红线在大样本下口径偏差），回 157 的 `v6_acceptance.py` 修并补 Layer 2 单测，不在 158 里 fork 逻辑。
- **T5 冻结产物**：本 Task 产出 Ch100 的 DB 尺寸/扫描耗时实测 → 写入标定报告，**冻结 T5 的 ⚙ 阈值**（若实测显示 300MB/1.5× 首版值不合理，按 148z 同样纪律记录并调整后冻结，**不在撞线后临时放宽**）。冻结结论回写 v6-plan §1.4 T5 行 + 148z 后继。
- **kill→resume 判据**：至少一次人为 kill 发生在**非章节边界**（生成中/结算中，制造 in-flight 章），验证 153 的 in-flight 重算 + 孤儿 checkpoint 清理；resume 后最终完成章集合与"不中断跑"一致，无人工改命令/清 DB。**报告必须记录三个检查点**：kill 前最后一次 `_save_run_state` 的 `current_chapter`、resume 后 `_compute_resume_start` 返回的起点、最终 `completed_chapters` 集合与"不中断跑"预期是否一致。
- **纯验证边界**：不改 153-156 任何代码；发现真缺陷 → 新开修复 Task（如 158p），阶段 D 暂停到修复合入。

### T5 冻结口径（权威定义）

- **尺寸**：Ch100 时 `run_db_metrics` 最末样本 `db_size_bytes` ≤ 300MB（含 `-wal`，但 `wal_checkpoint(TRUNCATE)` 后 `-wal` 应趋 0）。
- **扫描耗时**：`scan_latency_ms`（`find_orphaned` 计时）Ch100 值 ≤ **该 run 前 10 样本均值 ×1.5**（基线口径与 T3 前 10 章一致，`check_t5_latency_redline`）。
- **样本充分**：T5 判定要求 run_db_metrics 有 ≥ 一定样本数（每 10 章 1 个，Ch100 约 10 个）；不足则标未判定，不冻结。
- **冻结动作**：把实测的干净 100ch 尺寸/耗时基线写入 `docs/reports/task-158-*` 与 v6-plan T5 行；若维持首版 300MB/1.5×，注明"实测未超，维持首版"；若调整，注明依据。

## In Scope（必须完成）

### 158a — 无人值守 Ch1-Ch100 长跑 + kill→resume 演练
- [ ] 隔离副本 DB（带大纲项目）单命令无人值守跑 Ch1-Ch100，enforce 门禁；metrics 逐章追加 `.tmp/task158_ch1_ch100_metrics.jsonl`。on_failure/预算选型写入 DONE。
- [ ] **kill→resume 演练**：跑到中段（约 Ch40-Ch60，含一个 in-flight 非边界 kill）人为 kill；用**同一命令 `--resume`** 续完到 Ch100。记录：kill 点、kill 前 `current_chapter`、resume 起点、in-flight 章是否正确重算、孤儿 checkpoint 清理条数、最终 `completed_chapters` 集合与"不中断跑"预期是否一致。
- [ ] 若触 AutoHalt/预算熔断：记录 `paused` 原因，`--resume` 续跑演示门禁仍生效（不静默跳）。
- [ ] 全程无需人工改命令/清 DB（§1.3-R）。

### 158b — 五类曲线可读 + T5 冻结 + harness 判定
- [ ] `songyan metrics --project-id <p> --chapters 1-100` 一次性渲染五类曲线（orphan/T7/质量债/文学趋势/弧级兑现），确认全程可读、无断档。
- [ ] `evaluate_v6_acceptance(1,100)`：T2=100/100（隔离模式下允许少量 partial，但需 DONE 说明并评估是否达 §1.3-R 的"完成"）、T3/T4/T6 不破、T1 主线跃迁可追溯；输出 harness 原始三态结果入报告。
- [ ] **T5 首次实测冻结**：按 **Cross-Task Coordination「T5 冻结口径」** 用 Ch100 `run_db_metrics` 判 T5 并冻结阈值，回写 v6-plan T5 行。
- [ ] 产出报告 `docs/reports/task-158-ch1-ch100-long-run-validation-report.md`：逐章/检查点（Ch1/Ch50/Ch100）关键指标 + kill→resume 时间线（含 kill 前 `current_chapter` / resume 起点 / 最终 `completed_chapters` 与预期对比）+ 五类曲线 + harness 判定 + T5 冻结结论 + 与 a2bed648/138k 对比。

## Out of Scope（明确不做）

- 不改阶段 C（153-156）或治理（149-152）任何代码（纯验证；缺陷另开 Task）。
- 不重写/不 fork 157 的验收判据 harness。
- 不做 Ch150 复现（Task 159）。
- 不在本 Task 冻结 T5 以外的阈值（T3/T4/T6/T8 已在 148z/157 处理）。
- 不改 CLI 命令语义（只使用 153-156 已交付的 `--resume`/`--on-failure`/预算/维护）。

## 测试要求

> **测试哲学**：Task 158 的核心"测试"是**真实长跑 + 中断恢复演练**（Layer 3），判据可信度由 Task 157 的 Layer 2 harness 单测保证，本 Task 不重复造判据单测。但对本 Task **新增的一次性长跑脚本**（若有 resume 演练编排、metrics jsonl 追加逻辑）需有最小 Layer 2 冒烟测试，确保脚本本身不因参数解析/断点计算出错而误伤长跑。

### Layer 2: 长跑脚本 + T5 冻结逻辑冒烟（临时 SQLite，Mock/短程）
- [ ] 长跑脚本的章范围解析、resume 起点计算调用、metrics jsonl 追加：用 3-5 章 Mock 跑跑通，断言 jsonl 行数、run_id 记录、resume 参数正确透传（不跑真 LLM）。
- [ ] **kill→resume 编排单测**（可 Mock `_run_single_chapter`）：模拟 Ch1-ChK 后中断 → `--resume` → 从 accepted head 续、in-flight 章重算、`prune_orphan_checkpoints` 被调用；最终完成集合正确（复用 Task 153 测试范式，聚焦"长跑脚本层"编排）。
- [ ] T5 冻结判定：喂合成 Ch100 `run_db_metrics`（299MB/301MB、扫描 1.4×/1.6×）验证冻结逻辑走 `check_t5_*` 得正确 pass/fail 与"维持/调整"分支（复用 157/156 的判据，不重写）。

### Layer 3: Ch1-Ch100 无人值守长跑（§1.3-R 唯一实跑证据）
- [ ] 单命令无人值守跑完 Ch1-Ch100（或明确 AutoHalt 根因）。
- [ ] 至少一次中段人为 kill（含 in-flight 非边界）→ 同命令 `--resume` 续完；已 accept 跳过、in-flight 重算、无人工干预。
- [ ] 五类曲线全程可读；`evaluate_v6_acceptance(1,100)` 判 T2/T3/T4/T6/T1；T5 首次实测并冻结。
- [ ] 全部证据入 `docs/reports/task-158-ch1-ch100-long-run-validation-report.md`。

## 验收标准（Acceptance Criteria）

- [ ] `pytest tests/test_158_*.py -v` 全过（长跑脚本 + kill→resume 编排 + T5 冻结逻辑冒烟）；`ruff check` 通过；全量 pytest 不回归。
- [ ] Ch1-Ch100 单命令无人值守完成（T2；隔离模式 partial 需评估达 §1.3-R）；**中途至少一次 kill→resume 成功续完，无人工干预**。
- [ ] 五类曲线（orphan/T7/质量债/文学趋势/弧级兑现）全程可读；`evaluate_v6_acceptance` 判 T3/T4/T6/T1 不破。
- [ ] **T5 首次实测并冻结**（Ch100 DB ≤300MB、扫描 ≤基线×1.5，或按纪律调整后冻结），结论回写 v6-plan §1.4 T5 行。
- [ ] 不违反不可违背规则：纯验证、不改治理/阶段 C 代码、不 fork harness；缺陷另开 Task。
- [ ] 生成 `tasks/158-ch1-ch100-long-run-validation-DONE.md`，含长跑参数（on_failure/预算/gate）、kill→resume 时间线、五类曲线、harness 判定、T5 冻结结论、与 a2bed648 对比。
- [ ] 更新 `tasks/V6-README.md`（158 状态）与 `docs/STATUS.md`。

## 参考文档

- `docs/v6-plan.md` §1.3-R、§1.4-T5（DB/性能红线，本 Task 冻结）、§3 阶段 D（Task 158 行）
- Task 157（验收 harness）：`tasks/157-ch1-ch50-integration-validation.md`
- 阶段 C 能力：`tasks/153-run-level-resume-DONE.md`（resume）、`tasks/154-llm-rate-limit-and-budget-DONE.md`（预算）、`tasks/155-failure-isolation-DONE.md`（隔离）、`tasks/156-in-run-db-maintenance-DONE.md`（DB 维护/T5 遥测）
- T5 延后依据：`docs/reports/v6-stageA-threshold-calibration.md`（L48-49/L54）
- 历史长跑脚本范式：`archive/v5/scripts/run_139c_enforce_ch51_ch150.py`；基线 run `run-a2bed648`（见 `docs/STATUS.md`）
