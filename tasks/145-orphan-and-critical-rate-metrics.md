# Task 145: orphan 绝对量 + 新 critical 产生速率监控（阶段 A 度量框架）

> **Phase**: V6 阶段 A（度量同步）
> **优先级**: P0（阶段 A 前置：建立"从 DB 读逐章度量"的能力，146/147/148 复用）
> **依赖**: Task 141-144（骨架已落地）；无新数据依赖（复用 continuity_reports / setting_tracking）
> **预计工作量**: 大
> **事实入口**: `tasks/V6-README.md`；规划：`docs/v6-plan.md` §3 阶段 A

---

## Goal

把 orphan **绝对总数**及分类分布（critical/recurring/other）与「每章新 critical 产生速率」（T7，写入侧）做成**可从 DB 逐章还原的曲线**，并通过一个 DB 支撑的度量出口暴露。这是阶段 A 的框架任务：146/147/148 复用同一模块（`evals/db_metrics.py`）与 `songyan metrics` 出口。

## Context（代码核实）

- `songyan report`（`cli/main.py` L498-581）**只读 JSONL** run 日志（`evals/streaming_report.py`，全程无 DB 访问）。这是 v6-plan §3 修正说明点 1 指出的真实前置 gap。
- `continuity_reports` 表**无逐章计数列**，只存 JSON blob。`ContinuityReportRepository.list_by_chapter_range(project_id, start, end)`（`db/continuity_repo.py:442`）返回完整水合的 `ContinuityReport` 列表（`orphaned_settings[i].category` 可用），按 `checked_up_to_chapter` 升序。
- **orphan 计数直接从 `report.orphaned_settings` 按 `category` 派生**（`OrphanedSetting.category`，`models/continuity.py:21`，值域 critical/recurring/background/technical/historical）。
  - **不要复用 `classify_report`（`continuity_health.py:114`）来做 orphan 计数**：该函数返回的 `{P1,P2,P3}` 是 **orphan + state_mismatches + overdue_foreshadowings + forgotten_items 四类的聚合**（P1 含 state_mismatches，P3 含 forgotten_items，recurring orphan 落 P2），会污染 orphan 绝对量、并破坏 T6(b)「P1 critical orphan=0」口径。`classify_report` 仅供 health-severity 视图，本 Task 不用它算 orphan。
- T7 源：`setting_tracking` 表 `category` 列（CHECK 约束五值）+ `introduced_in_chapter`。每章新 critical = `COUNT(*) WHERE category='critical' AND introduced_in_chapter=N`。category 由 `_infer_setting_category`（`agents/settlement_extractor/_apply.py:688`）在结算时赋值。**当前无对应 repo 查询方法。**
- 历史 DB `.tmp/task138n_ch1_ch30_rerun.db`（continuity_reports 273 行、setting_tracking 1376 行、覆盖 150 章）与 `task138k_...db` 都含上述表 → **derive-on-read 设计可直接复算历史曲线**（满足"复跑 138n 还原曲线"验收）。

### 关键设计决策（本 Task 确立，146/147/148 遵循）

1. **derive-on-read，不新增逐章计数表**：orphan 已在 continuity_reports、T7 已在 setting_tracking 持久化，逐章曲线在读取时派生。好处：无新写路径、无 pipeline 侵入、且**能在历史 DB 上复算**（新表历史 DB 没有）。满足 v6-plan §3 修正说明点 3 的"逐章 continuity 记录"选项（记录已存在，只需派生计数）。
   - D 维度说明（回应"五类长期指标已入库"）：源数据已入库（continuity_reports/setting_tracking），指标在读取时派生即视为"可查"；仅 146 因运行态信号不在 DB 而新增一张 run 级汇总表。
2. **DB 支撑的度量出口 = 新增 `songyan metrics` 命令**（keyed on `--project-id` + `--chapters`），不改动现有 `songyan report`（后者是 run_id/JSONL 的流式验证报告）。理由：run 报告是"单次运行验证"，V6 长期度量是"项目/DB 维度、可跨 run、可复算历史 DB"；新命令用 `DATABASE_URL` 覆盖即可指向 138n/138k 历史库，直接满足复算验收，且对现有 report 零回归。**为消除与 §1.3-D 字面"在 songyan report 查看"的漂移，v6-plan §1.3-D/§3 与 V6-README D 的措辞同步改为"songyan report/metrics"**（本 Task 一并改），确保 Task 159 的 D 核对不落空。
3. 度量模块统一放 `src/songyan/evals/db_metrics.py`（纯异步 collector，读 DB，不写）；146/147/148 的 collector 也放此文件（或 `evals/metrics/` 包），不各自散落。CLI 渲染放 `songyan metrics`。

## In Scope（必须完成）

- [ ] `src/songyan/evals/db_metrics.py`：
  - `async collect_orphan_metrics(project_id, start, end) -> list[OrphanPoint]`：按 `checked_up_to_chapter` 取每章最新 continuity_report，**直接统计 `report.orphaned_settings` 的 category**：`orphan_total=len(orphaned_settings)`、`orphan_critical`(=='critical')、`orphan_recurring`(=='recurring')、`orphan_other`(其余)。不变量 `critical+recurring+other==total`。`forgotten_items` 另存独立字段（非 orphan）。
  - `async collect_new_critical_rate(project_id, start, end) -> list[CriticalRatePoint]`：从 setting_tracking 派生 `{chapter, new_critical, new_total}`（按 `introduced_in_chapter` 聚合，`category='critical'` 计 new_critical）。
  - 轻量 Pydantic 行模型；提供把两组曲线按 chapter 对齐的辅助（缺失章补 0）。
- [ ] repo 查询方法（放 `SettingTrackingRepository`）：`async new_settings_by_chapter(project_id, start, end) -> list[dict]`（`SELECT introduced_in_chapter, category, COUNT(*) ... GROUP BY introduced_in_chapter, category`）。orphan 侧复用 `list_by_chapter_range`，不新增 repo 方法。
- [ ] `songyan metrics` CLI 命令（`cli/main.py`）：`--project-id`（必填）、`--chapters a-b`（必填）、`--output`（可选，默认 `logs/reports/metrics-<project_id>.md`）。渲染 markdown：orphan 总数/critical/recurring/other 曲线 + T7（new_critical/章）曲线 + 斜率摘要。**至少输出 orphan 总数 / critical / P3(=other) + T7 四条曲线**（满足 v6-plan 验收）。
- [ ] 单测：seed 临时 DB（continuity_reports + setting_tracking）→ 断言 orphan 分类计数（不变量 critical+recurring+other=total）与 T7 写入侧计数；两类口径各有独立断言。

## Out of Scope（明确不做）

- 不改 `songyan report`（run 日志报告）现有行为；不改 `classify_report`/continuity_auditor 分类逻辑（只消费 orphaned_settings）。
- 不新增逐章计数持久化表（derive-on-read）。
- 质量债（146）/文学趋势（147）/伏笔兑现（148）各自任务实现；本 Task 只建框架 + orphan/T7 两组曲线。
- **阈值标定报告（T3/T4/T5/T6/T8 冻结）属阶段 A 出口，由专门的标定步骤产出**（见 `tasks/148z-stage-a-threshold-calibration.md`），非本 Task。
- **T6 归因边界**：本 Task 只产出 T6(a) orphan 斜率曲线与 T7 写入侧曲线；T6c 的"T7 降幅 ≥ orphan 斜率降幅 50%"比值在标定报告中用两条曲线**手工**计算；T6c 的"被降级 critical ≤15%"子句依赖 **Task 149**（阶段 B 录入侧降级）尚未落地，Stage A 不评估该子句。

## 接口契约

```python
# db_metrics.py
class OrphanPoint(BaseModel):
    chapter: int
    orphan_total: int        # == len(report.orphaned_settings)
    orphan_critical: int     # category == 'critical'
    orphan_recurring: int    # category == 'recurring'
    orphan_other: int        # background/technical/historical（对应 v6-plan 口径的 P3）
    forgotten_items: int = 0 # 独立计数（非 orphaned_settings），单列曲线
    # 不变量：orphan_critical + orphan_recurring + orphan_other == orphan_total

class CriticalRatePoint(BaseModel):
    chapter: int
    new_critical: int
    new_total: int

async def collect_orphan_metrics(project_id: str, start: int, end: int) -> list[OrphanPoint]: ...
async def collect_new_critical_rate(project_id: str, start: int, end: int) -> list[CriticalRatePoint]: ...
```

## 验收标准（Acceptance Criteria）

- [ ] `pytest tests/test_145_stage_a_metrics.py -v` 全通过（orphan 分类不变量 + T7 写入侧口径 + CLI 渲染）。
- [ ] `ruff check src/ tests/` 通过；全量 pytest 不回归。
- [ ] **复跑 138n 验收（可直接复制执行）**：先取项目 id `DATABASE_URL=sqlite:///.tmp/task138n_ch1_ch30_rerun.db python -c "import sqlite3;print(sqlite3.connect('.tmp/task138n_ch1_ch30_rerun.db').execute('SELECT project_id FROM project_runs LIMIT 1').fetchone())"`，再 `DATABASE_URL=sqlite:///.tmp/task138n_ch1_ch30_rerun.db songyan metrics --project-id <id> --chapters 1-150`，还原 orphan 总量斜率与 T7 速率两条独立曲线（标定报告引用）。
- [ ] report/metrics 输出 orphan 总数/critical/P3 + T7 共四条曲线。
- [ ] 不违反不可违背规则：只读 DB 派生，无新写路径；类型标注齐全。
- [ ] 生成 `tasks/145-...-DONE.md`；更新 `tasks/V6-README.md` 与 `docs/STATUS.md`。

## 参考文档

- `docs/v6-plan.md` §3 阶段 A（Task 145 行 + 修正说明点 1/3）、§1.4-T6/T7
- 代码：`agents/continuity_auditor/continuity_health.py`（`classify_report` L114 — 仅 health 视图，不用于 orphan 计数）、`db/continuity_repo.py`（`SettingTrackingRepository`、`ContinuityReportRepository.list_by_chapter_range` L442）、`models/continuity.py:21`（`OrphanedSetting.category`）、`agents/settlement_extractor/_apply.py:688`（`_infer_setting_category`）、`evals/streaming_report.py`、`cli/main.py` report_cmd
