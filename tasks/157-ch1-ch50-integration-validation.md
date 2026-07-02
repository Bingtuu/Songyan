# Task 157: Ch1-Ch50 集成验证（阶段 D 首窗 + V6 验收判据 harness）

> **Phase**: V6 阶段 D（长窗口验证）
> **优先级**: P0（阶段 D 首个完整窗口；本 Task 交付的验收 harness 被 158/159 复用，是整个阶段 D 的判据基础）
> **依赖**: 阶段 0+A+B+C 全部工程实现已合入（Task 141-156）；阈值冻结见 148z / `docs/v6-plan.md` §1.4
> **预计工作量**: 中（拆 157a 验收判据 harness + 157b Ch1-Ch50 实跑验证）
> **事实入口**: `tasks/V6-README.md`；规划：`docs/v6-plan.md` §3 阶段 D

---

## Goal

跑通阶段 0+A+B+C 改动合入后的**首个完整窗口 Ch1-Ch50**（无人值守、enforce 门禁），并**同时交付一套可复用、可单测的 V6 验收判据 harness**——把 §1.4 的 T2-T8 红线从"报告里靠人眼看"升级为"函数返回 pass/fail"。Ch1-Ch50 要满足 T2（50/50 完成）、阶段 B 出口 T6、主线线索 T1 跃迁可追溯，且全程不触 T3/T4 红线。

**为什么 157 要先造 harness**：Explore 核实（下方 Context）发现，目前只有 T4（`compute_quality_debt.t4_breached`）、T5（`check_t5_*`）、T3/T8（`detect_literary_trend.breached_dimensions`）有布尔判定；**T2、T6a、T6b、T6c、T7 只在 `render_*` 里以文字/表格呈现，没有任何 `check_*` 函数，也没有聚合"跑一遍所有红线出 pass/fail"的入口**。阶段 D 有 3 个窗口（157/158/159）都要判同一批红线，若每次靠人眼读 markdown，既不可复现也易漏判。因此 157a 先补齐缺失的判据函数 + 一个聚合入口，157b/158/159 直接调用。

## Context

设计核实（2026-07-02，创建前对主干代码核对）：

- **已有度量采集（阶段 A/C 建，全部可复算历史 DB）**，`src/songyan/evals/db_metrics.py`：
  - `collect_orphan_metrics(project_id, start, end) -> list[OrphanPoint]`（L77；`OrphanPoint` 含 `chapter/orphan_total/orphan_critical/orphan_recurring/orphan_other/forgotten_items`）。
  - `collect_new_critical_rate(project_id, start, end) -> list[CriticalRatePoint]`（L121，**T7 写入侧**；含 `new_critical/new_total`）。
  - `collect_setting_lifecycle_metrics(project_id) -> SettingLifecycleMetrics`（L150；`active/resolved/abandoned/archived_count`）。
  - `compute_quality_debt(logs, window=50) -> QualityDebtReport`（L306；已有 `t4_breached` 布尔，`_T4_DEGRADED_MAX=0.20`/`_T4_CONVERGENCE_MAX=0.10`，`window_sufficient` 防小样本误判）。
  - `detect_literary_trend(points, *, baseline_n=10, window=5, drop=0.20) -> LiteraryTrendResult`（L471；**T3/T8** 已有 `breached_dimensions` 布尔）。
  - `collect_arc_fulfillment` / `collect_long_range_ledger`（L583/L624，T1/伏笔）。
  - `linear_slope(xs, ys) -> float`（L171，供 T6a 斜率复用）。
  - 主报告 `render_stage_a_metrics(project_id, start, end)`（L242，`songyan metrics` 调它）。
- **P1/P2/P3 分级**：`src/songyan/agents/continuity_auditor/continuity_health.py` `classify_report(report) -> {"P1","P2","P3": int}`（L114，critical→P1）；`collect_continuity_health_metrics(project_id, start, end)`（L143，返回 `health_low_chapters`(<7.0)/`chapter_details[{chapter_number,health_score}]`）。continuity health 存 `continuity_reports`，经 `ContinuityReportRepository.list_by_chapter_range`（continuity_repo.py L610）读。
- **CLI**：`songyan metrics --project-id --chapters 1-50`（main.py L606）→ `render_stage_a_metrics`。`songyan run --gate-mode enforce`（默认，L429）→ `GateConfig.for_mode`。`songyan run --resume`（Task 153）。
- **已冻结阈值（148z / v6-plan §1.4）**：T6a orphan 斜率 ≤ **3.14/章**（=138n 6.2836×0.5）；T6b P1 critical orphan **=0**；T6c T7 基线 **1.767/章**（138k），且 hard 口径只判 "T7 降幅 ≥ orphan 斜率降幅 50%"；"被降级为 candidate 的 critical 占比"因当前 DB 无法区分"原生 candidate"与"降级 candidate"，**降级为观察口径，不进入 `all_passed` 硬判定**；T3 W=5 均值较前 10 章降 ≥20%；T4 degraded ≤20% & convergence ≤10%；T8 N=5。**这些数字目前散落在代码常量（T3/T4/T5）与 v6-plan 散文（T6a/T6b/T6c）里，T6* 没有代码常量**。
- **缺口（本 Task 要补）**：无 `check_t2/check_t6a/check_t6b/check_t6c/check_t7_attribution` 函数；无聚合 `evaluate_v6_acceptance(...)`；`songyan report` 仍不读 continuity DB（度量只在 `songyan metrics`）。

## Cross-Task Coordination（阶段 D 统一口径）

> 阶段 D 三个窗口（157 Ch50 / 158 Ch100 / 159 Ch150）判同一批红线。157a 交付的 harness 是**唯一判定实现**，158/159 只调用、不重写判据，避免三处阈值漂移。

- **判据唯一来源**：所有 T2-T8 的布尔判定收敛到 `src/songyan/evals/v6_acceptance.py`（新增），阈值常量集中在该模块顶部（T6a/T6b/T6c 从 v6-plan 散文落为**有出处注释的常量**；T3/T4/T5 复用/re-export `db_metrics`/`db_maintenance_metrics` 里已有的常量，不复制数值）。
- **判据只读、不改治理**：harness 纯读 DB + run log 派生 pass/fail；**不改** 149-156 任何业务逻辑、不改门禁阈值、不新增 Agent/LLM。发现真缺陷 → 记录并新开修复 Task（如 157p），不在验证 Task 里顺手改治理。
- **"完成"口径**：T2 完成 = 目标区间每章有 `accepted` 或 `edited` head（`degraded_accept` 计入完成但同时计入 T4 债；`failed`/未决 `human_review_required` 算未完成）。与 Task 153 resume 的"accepted head 为完成事实源"一致，但 T2 额外接纳 `edited`。**实现前需确认 `chapter_heads.status` 是否存在 `edited` 值；若不存在，T2 先只认 `accepted`，并在 DONE 中说明**。
- **窗口出口分工**：157 判 Ch1-Ch50 满足 T2 + 阶段 B 出口 T6 + T1 + 不触 T3/T4；T5（DB/性能）在 157 只**采样入库**、红线判定归 158（Ch100 才是 T5 冻结场景，见 v6-plan L54）；T4 的 50 章满窗在 157 恰好首次可判（`window_sufficient` 需 ≥50 章）。

### 验收 harness 判据口径（权威定义）

`evaluate_v6_acceptance(project_id, start, end, *, run_id, run_logs)` 依次调用下列单项判据，返回一个 `V6AcceptanceResult`（每项含 `passed: bool` + `detail`/实测值 + `threshold` + `sufficient`）：

| 判据 | 口径（可判定） | 数据来源 | 现状 |
|------|----------------|----------|------|
| **T2** 完成率 | 目标区间每章都有 `accepted`/`edited` head；若 `edited` 不在 `chapter_heads.status` 中，先只认 `accepted` | `ChapterHeadRepository` + run log | 新增 `check_t2` |
| **T6a** orphan 斜率 | 窗口内 `orphan_total` 线性斜率 ≤ 3.14/章 | `collect_orphan_metrics` + `linear_slope` | 新增 `check_t6a` |
| **T6b** P1 critical orphan | 全程每章 `orphan_critical` == 0；缺 continuity_report 的章视为未判定 | `collect_orphan_metrics.orphan_critical`（或 `classify_report` P1） | 新增 `check_t6b` |
| **T6c** 归因（hard） | T7 速率较 138k 基线 1.767 的降幅 ≥ orphan 斜率降幅的 50% | `collect_new_critical_rate` + T7 基线 | 新增 `check_t6c` |
| **T6c-obs** 降级观察 | 被降级 candidate 的 critical ≤ 同窗新增 critical 总数 15%（观察项，不进入 `all_passed`） | `collect_new_critical_rate` + `SettingLifecycleMetrics` | 新增 `check_t6c_obs`（返回实测占比，不判 pass/fail） |
| **T7** 速率 | 每章 `new_critical` 速率曲线（供 T6c，本身不设独立红线） | `collect_new_critical_rate` | 新增 `check_t7_rate`（返回速率，不判 pass/fail） |
| **T3/T8** 文学趋势 | 任一维度 W=5 均值较前 10 章降 ≥20% 即破 | `detect_literary_trend` | **复用** `breached_dimensions` |
| **T4** 质量债 | 50 章窗 degraded ≤20% & convergence ≤10% | `compute_quality_debt.t4_breached` | **复用** |
| **T5** DB/性能 | DB ≤300MB & 扫描 ≤基线 ×1.5 | `check_t5_size_redline`/`check_t5_latency_redline` | **复用**（157 采样，158 判） |
| **T1** 主线跃迁 | ≥1 条 `is_mainline` PlotThread 在窗口内发生 `opened→advanced` 或 `advanced→resolved`，且 `last_status_chapter > opened_chapter`、`last_status_version_id` 非空 | `NarrativeRepository.list_mainline_threads` / `plot_threads` 表 | 新增 `check_t1` |

- **样本充分性护栏**：每项判据带 `sufficient` 标志（如 T4 需满 50 章、T6a 需 ≥ 一定点数、T6c 需有 138k 基线）。**样本不足时该项返回 `passed=None`（未判定）而非 `False`**，避免小窗口误判红线（沿用 `compute_quality_debt.window_sufficient` 精神）。聚合结果区分"通过/未通过/未判定"三态。
- **基线注入**：T6a 阈值 3.14、T6c 的 138k T7 基线（1.767）作为**显式参数/常量**传入，出处注释指向 148z 报告，不在 harness 里重算历史基线。

## In Scope（必须完成）

### 157a — V6 验收判据 harness（可复用 + 可单测）
- [ ] 新增 `src/songyan/evals/v6_acceptance.py`：实现 `check_t1/check_t2/check_t6a/check_t6b/check_t6c/check_t6c_obs/check_t7_rate` + 聚合 `evaluate_v6_acceptance(...)`，按 **Cross-Task Coordination「判据口径」** 返回三态结果；T3/T4/T5 复用现有布尔函数（import，不复制数值）。
- [ ] 阈值常量集中在模块顶部，T6a/T6b/T6c 从 v6-plan 散文落为带出处注释的常量（引用 148z）。
- [ ] `render_v6_acceptance_section` 并入 `render_stage_a_metrics` 尾部，`songyan metrics --chapters N-M` 直接输出验收判定段（DONE 说明此选型）。
- [ ] 纯读实现：不改任何治理/门禁/Agent；无新增 LLM 调用。

### 157b — Ch1-Ch50 实跑验证
- [ ] 用隔离副本 DB（带大纲项目）无人值守跑 Ch1-Ch50，enforce 门禁，`on_failure` 取隔离或 retry（DONE 记录选型与理由）；metrics 逐章追加到 `.tmp/task157_ch1_ch50_metrics.jsonl`。
- [ ] 跑后用 157a 的 `evaluate_v6_acceptance` 判 Ch1-Ch50：T2=50/50、阶段 B 出口 T6（a/b/c 全过）、T1 ≥1 条主线跃迁可追溯、全程不触 T3/T4；health ≥7.0（阶段 B 出口附加项）。T5 仅采样入库。
- [ ] 产出报告 `docs/reports/task-157-ch1-ch50-integration-validation-report.md`：逐章关键指标表 + 三检查点（Ch1/Ch25/Ch50）趋势 + harness 判定结果 + 与 138k/138n 基线对比。
- [ ] 若中途触 AutoHalt 或某红线破：记录确切章号与根因，判定是"真退化"（→ 新开修复 Task，阶段 D 暂停）还是"样本/环境波动"（记录后续跑），**不在本 Task 改治理代码**。

## Out of Scope（明确不做）

- 不改 149-156 的任何治理/门禁/Agent 逻辑（纯验证；发现缺陷另开 Task）。
- 不做 Ch100（Task 158）/ Ch150（Task 159）长跑本身。
- 不在本窗口冻结 T5 最终阈值（Ch100 才是 T5 场景，归 158）。
- 不给 `songyan report`（JSONL 侧）加 DB 读取——度量继续走 `songyan metrics`/harness。
- 不新增 LLM 语义判据——所有红线判定是确定性 DB/日志派生。

## 接口契约

```python
# src/songyan/evals/v6_acceptance.py
class ThresholdResult(BaseModel):
    key: str                 # "T2" / "T6a" / ...
    passed: bool | None      # None = 样本不足未判定
    measured: float | str | None
    threshold: float | str | None
    sufficient: bool
    detail: str

class V6AcceptanceResult(BaseModel):
    project_id: str
    chapter_start: int
    chapter_end: int
    results: list[ThresholdResult]
    all_passed: bool         # 所有 sufficient 项均 passed（未判定项单列）
    undecided: list[str]

async def evaluate_v6_acceptance(
    project_id: str, start: int, end: int, *,
    run_id: str | None = None,
    run_logs: list[ChapterRunLog] | None = None,
    orphan_slope_threshold: float = 3.14,   # =138n 6.2836×0.5，出处 148z
    t7_rate_baseline: float = 1.767,        # 138k，出处 148z
) -> V6AcceptanceResult: ...

def render_v6_acceptance_section(result: V6AcceptanceResult) -> str: ...
```

（最终签名以实现为准；核心：单项判据 + 聚合三态 + 样本充分性护栏 + 基线显式注入。）

## 测试要求

> **测试哲学**：阶段 D 的"测试"分两层——Layer 2 用**合成 DB 数据**把 harness 的每条红线判定（含边界与三态）钉死，使判据本身在无需长跑的情况下即可回归；Layer 3 才是**真实长跑**，用已验证的 harness 出结论。Layer 2 是 158/159 复用 harness 的信心来源，必须严格。

### Layer 2: harness 模块测试（真实临时 SQLite，合成度量数据；不跑 LLM）
- [ ] **T2**：造 50 章全 `accepted` → pass；造 1 章 `failed`/仅 `draft` → fail 并列出缺口章；若 `edited` 在状态机中，`edited` 计入完成（`degraded_accept` 计入完成但被 T4 单独捕获）。
- [ ] **T6a 斜率**：合成 `orphan_total` 序列斜率 3.0 → pass、3.2 → fail（跨 3.14 边界）；点数不足 → `passed=None`（未判定）。
- [ ] **T6b P1**：任一章 `orphan_critical>0` → fail 并列章号；全 0 → pass；某章缺 continuity_report → 该章视为未判定，不直接 fail。
- [ ] **T6c 归因**：T7 降幅 ≥ orphan 斜率降幅 50% → pass、恰好不足 → fail；无 138k 基线 → 该项 `None`。
- [ ] **T6c-obs 降级观察**：返回 candidate critical 占同窗新增 critical 总数比例（不判 pass/fail），作为 `detail` 补充。
- [ ] **T3/T8**：构造某维度 W=5 均值较前 10 章降 19%→ 不破、21%→ 破（复用 `detect_literary_trend`，验证 harness 正确读取 `breached_dimensions`）。
- [ ] **T4**：50 章窗 degraded 19%→ 不破、21%→ 破；convergence 9%→ 不破、11%→ 破；<50 章 → `window_sufficient=False` → 未判定。
- [ ] **T5**：DB 299MB→ 不破、301MB→ 破；扫描 1.4×→ 不破、1.6×→ 破；无基线 → 未判定（复用 `check_t5_*`）。
- [ ] **T1**：造 1 条 `is_mainline` thread 发生 `opened→advanced` 且 `last_status_chapter > opened_chapter`、`last_status_version_id` 非空 → pass；无主线跃迁 → fail。
- [ ] **聚合三态**：`evaluate_v6_acceptance` 在"全 sufficient 且 pass"→ `all_passed=True`；含未判定项 → `all_passed` 只看 sufficient 项且 `undecided` 非空；任一 sufficient 项 fail → `all_passed=False`。
- [ ] **只读**：调用 harness 前后业务表行数/内容不变（纯读断言）。

### Layer 3: Ch1-Ch50 实跑验证（阶段 D 首窗出口）
- [ ] 隔离副本 DB 无人值守 Ch1-Ch50 完成，或有明确 AutoHalt 根因记录。
- [ ] `evaluate_v6_acceptance(Ch1-Ch50)`：T2=50/50；T6a/T6b/T6c 全 pass（阶段 B 出口）；T1 ≥1 条主线跃迁可定位；T3/T4 不破；health ≥7.0。T5 采样入库（判定归 158）。
- [ ] 报告入 `docs/reports/task-157-ch1-ch50-integration-validation-report.md`，含 harness 判定原始输出。

## 验收标准（Acceptance Criteria）

- [ ] `pytest tests/test_157_*.py -v` 全过（harness Layer 2 全覆盖，含所有红线边界与三态）；`ruff check src/ tests/` 通过；全量 pytest 不回归。
- [ ] `evaluate_v6_acceptance` 可对任意 (project, 章范围) 出 T1-T8 三态判定 + T6c-obs 观察项，阈值集中、基线显式、样本不足不误判。
- [ ] Layer 3 Ch1-Ch50 达成阶段 D 首窗出口：T2=50/50 + 阶段 B 出口 T6 全过 + T1 可追溯 + 不触 T3/T4 + health≥7.0（证据入 `docs/reports/`）。
- [ ] 不违反不可违背规则：harness 纯读、不改治理/门禁/Agent；无新增 LLM；实跑发现缺陷另开 Task 而非顺手改。
- [ ] 生成 `tasks/157-ch1-ch50-integration-validation-DONE.md`，含 harness 判据口径、阈值出处、Ch1-Ch50 实跑证据、与基线对比、（如有）新缺陷 Task 编号。
- [ ] 更新 `tasks/V6-README.md`（157 状态）与 `docs/STATUS.md`。

## 参考文档

- `docs/v6-plan.md` §1.3 N/D/S/R/V、§1.4 T1-T8、§3 阶段 D（Task 157 行 + 阶段 D 出口）
- 阶段 A 阈值冻结：`tasks/148z-stage-a-threshold-calibration-DONE.md`、`docs/reports/v6-stageA-threshold-calibration.md`
- 现有度量代码：`evals/db_metrics.py`（`collect_*`/`compute_quality_debt`/`detect_literary_trend`/`render_stage_a_metrics`/`linear_slope`）、`evals/db_maintenance_metrics.py`（`check_t5_*`）、`agents/continuity_auditor/continuity_health.py`（`classify_report`/`collect_continuity_health_metrics`）
- 基线 DB：`.tmp/task138n_ch1_ch30_rerun.db`、`.tmp/task138k_ch1_ch30_rehearsal_20260629.db`
- 历史长跑脚本范式：`archive/v5/scripts/run_139c_enforce_ch51_ch150.py`
