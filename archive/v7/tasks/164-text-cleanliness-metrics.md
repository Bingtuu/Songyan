# Task 164: 文本洁净度度量入库 + `songyan report` 展示（T9 harness）

> **Phase**: V7 阶段 W（篇章级质量修复）
> **优先级**: P1（把 160-162 的修复效果变成"可入库、可查、可判定"的洁净度指标；T9 判据 harness 载体）
> **依赖**: Task 160（元标记）、161（段落去重）、162（时间线）——本 Task 汇聚三者的检测信号
> **预计工作量**: 中（度量入库 + report 段渲染 + T9 harness + 单测；对齐 157/158 度量风格）
> **事实入口**: `tasks/V7-README.md`；规划：`docs/v7-plan.md` §3 阶段 W

---

## Goal

把 Task 160-162 修复的三类篇章级缺陷（元标记泄漏 / 整段落重复 / 跨章时间线矛盾）做成**可入库、可在 `songyan report`/`songyan metrics` 查询的文本洁净度指标**，并建立 **T9 判据 harness**——使"全程 accepted 正文零元标记、零整段重复、零时间线矛盾"可被不在场者独立核对（对齐 157 的 `evaluate_v6_acceptance` / `render_stage_a_metrics` 风格）。

## Context

设计核实（2026-07-04，创建前对主干代码核对）：

- **检测信号已由 160-162 产出，但未聚合入库**：160 补全 `detect_markdown_scene_titles` / `detect_meta_tag_leaks` 并通过 ReviewMerger 接入阻塞链路（元标记 count）、161 新增 `detect_duplicate_paragraphs`（重复段 count）、162 新增 `detect_timeline_conflicts`（矛盾对 count）。三者是**逐章检测结果**，但目前**无统一的"洁净度"度量入库 + report 展示**。本 Task 是聚合层。
- **度量入库/展示有成熟范式**：V6 阶段 A 的五类曲线走 `render_stage_a_metrics`（`src/songyan/evals/db_metrics.py`），逐章度量持久化 + `songyan metrics --chapters N-M` 渲染。洁净度是**第六类度量**，应沿用同一范式（逐章洁净度记录 + report 段），而非另起炉灶。
- **T9 harness 对齐 157**：V6 的 `evaluate_v6_acceptance` 产出 T1-T8 三态（pass/fail/undecided），`render_v6_acceptance_section` 渲染。T9（文本洁净度红线）应作为**同类三态判据**接入——`check_t9(project_id, start, end) -> ThresholdResult`，判"全程 accepted 正文洁净度全零"。这样 165 阶段 W 出口能一次性调用、逐章核对。
- **阈值待 165 冻结**：T9 的"零"是结构性红线（元标记=0/重复=0/矛盾=0），但"时间线矛盾"因 162 是诊断项、可能有误报，T9 是否把矛盾纳入"硬零"还是"仅报告"，需 165 用 Ch150 修复后基线实测决定。本 Task 建 harness 骨架 + 入库 + 展示，**阈值口径留 165 标定冻结**（继承 148z 纪律）。

**边界**：这是"度量聚合 + 入库 + 展示 + 判据 harness"，**不改 160-162 的检测逻辑**（只消费其输出）。不冻结 T9/T10 阈值（留 165）。对齐现有度量代码风格，不新建独立度量子系统。

## In Scope（必须完成）

- [ ] **洁净度逐章度量入库**：聚合 160-162 的逐章检测结果（元标记 count / 重复段 count / 时间线矛盾 count）为**文本洁净度度量**，逐章持久化（沿用 `render_stage_a_metrics` 的逐章度量持久化范式，不假设已有列）。
- [ ] **`songyan report`/`songyan metrics` 展示**：新增**洁净度段**——逐章三类计数曲线 + 汇总（全程总泄漏/总重复/总矛盾章数）。作为五类曲线之外的第六段接入 `render_stage_a_metrics`（或 report 渲染），`songyan metrics --chapters N-M` 可查。
- [ ] **T9 判据 harness**：新增 `check_t9(project_id, start, end) -> ThresholdResult`，判"区间内 accepted 正文元标记=0 且整段重复=0 且（时间线矛盾按 165 冻结口径）"，产出三态（pass/fail/undecided）；接入 `evaluate_v6_acceptance` 同款三态框架（或 V7 对应 harness），供 165 调用。**阈值常量/矛盾是否纳入硬零留 165 冻结**，本 Task 提供可参数化的判据骨架。
- [ ] **单测覆盖**：喂合成逐章检测结果，验证入库、report 段渲染、`check_t9` 三态判定（全零→pass、有泄漏/重复→fail、数据不足→undecided）正确。

## Out of Scope（明确不做）

- 不改 160/161/162 的检测器逻辑（只消费其输出聚合）。
- **不冻结 T9/T10 阈值**（留 Task 165 用 Ch150 修复后基线标定冻结）；本 Task 判据可参数化。
- 不做文学维度趋势（那是 147 已有的五类之一，T10 冻结在 165）。
- 不新建独立度量子系统——沿用 `render_stage_a_metrics` 范式接第六段。
- 不阻塞 accept（洁净度是否作为 accept 硬门在 160 已通过 `RuleAuditor -> ReviewMerger -> ReviewIssue` 对元标记做阻塞；本 Task 是**度量与验收判据**，不新增门禁）。

## 接口契约

```python
# 洁净度逐章度量（聚合 160-162 输出）
class TextCleanlinessMetric(BaseModel):
    chapter_no: int
    meta_tag_leak_count: int         # 来自 160
    duplicate_paragraph_count: int   # 来自 161
    timeline_conflict_count: int     # 来自 162（诊断）

# report 展示（接入 render_stage_a_metrics 第六段）
async def render_text_cleanliness_section(project_id: str, start: int, end: int) -> str: ...

# T9 判据 harness（三态，阈值口径待 165 冻结）
def check_t9(
    project_id: str, start: int, end: int,
    *, include_timeline_in_redline: bool = False,  # 165 决定
) -> ThresholdResult: ...
```

## 测试要求

### Layer 2: 模块测试（`tests/test_164_text_cleanliness.py`）
- [ ] **入库 + 回读**：合成逐章检测结果入库，回读还原三类计数曲线正确、无断档。
- [ ] **report 段渲染**：`render_text_cleanliness_section` 输出含逐章曲线 + 汇总，格式对齐现有度量段。
- [ ] **T9 三态**：全零→pass；含元标记/重复→fail 且列出违规章；数据不足→undecided；`include_timeline_in_redline` 开关按参数改变矛盾是否计入红线。
- [ ] **接入 harness**：`check_t9` 能被 `evaluate_v6_acceptance`/V7 harness 汇总调用，三态与其它 T 项一致。

## 验收标准（Acceptance Criteria）

- [ ] `pytest tests/test_164_*.py -v` 全过；`ruff check src/ tests/` 通过；全量 pytest 不回归。
- [ ] 洁净度三类计数逐章入库、可回读；`songyan metrics --chapters N-M` 输出洁净度段；`check_t9` 产出正确三态。
- [ ] T9 判据可参数化（矛盾是否纳入硬零），阈值口径明确标注"待 165 冻结"。
- [ ] 不违反不可违背规则：只消费 160-162 输出、不改检测逻辑；不新增门禁/Agent；沿用现有度量范式；纯度量判据。
- [ ] 生成 `archive/v7/tasks/164-text-cleanliness-metrics-DONE.md`（含度量入库设计、report 段样例、T9 harness 接口、参数化说明）。
- [ ] 更新 `tasks/V7-README.md`（164 状态）与 `docs/STATUS.md`。

## 参考文档

- `docs/v7-plan.md` §3 阶段 W（Task 164 行）、§4 T9/T10
- 度量范式：`src/songyan/evals/db_metrics.py`（`render_stage_a_metrics` / 逐章度量持久化 / `collect_*`）、Task 145-148（五类曲线入库先例）
- 判据 harness：`src/songyan/evals/v6_acceptance.py`（`evaluate_v6_acceptance` / `ThresholdResult` / `render_v6_acceptance_section`）、Task 157 `archive/v6/tasks/157-ch1-ch50-integration-validation-DONE.md`
- 上游检测源：Task 160/161/162 的 `detect_markdown_scene_titles` / `detect_duplicate_paragraphs` / `detect_timeline_conflicts`
- 阈值冻结纪律：`archive/v6/tasks/148z-stage-a-threshold-calibration-DONE.md`（148z 先实测再冻结）
