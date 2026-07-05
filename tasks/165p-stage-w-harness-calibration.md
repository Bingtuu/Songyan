# Task 165p: 阶段 W 出口阻断项 — T5/T6 harness 口径校准

> **Phase**: V7 阶段 W 出口补充任务（Task 165 后续）
> **优先级**: P0（阶段 W 出口闸门；未完成不得进入 166 / X 阶段）
> **依赖**: Task 165 真实 Ch1-Ch150 复跑证据 `run-11fc7c96`
> **预计工作量**: 中（纯 harness / 报告口径校准 + 复算，不跑真实 LLM）
> **事实入口**: `tasks/V7-README.md`；报告：`docs/reports/task-165-stage-w-exit-report.md`

> **执行结果**: 已完成，见 `tasks/165p-stage-w-harness-calibration-DONE.md`。复算后阶段 W 通过，T9/T10 已冻结。

---

## Goal

解除 Task 165 阶段 W 出口中唯一剩余阻断项：`不回退` 里的 **T5 扫描耗时旧口径 fail** 与 **T6c 归因口径 fail**。

本任务只处理 **V6 遗留 harness / 度量判据口径**，不修改生成、治理、门禁、Agent 行为。完成后用现有 `.tmp/task165_stage_w_ch150.db` 复算 Task 165 出口报告；只有复算后 P/L/修复对比/不回退均通过，才允许正式冻结 T9/T10 并进入 Task 166。

## Context

Task 165 已取得真实复跑证据：

- Run: `run-11fc7c96`
- DB: `.tmp/task165_stage_w_ch150.db`
- 结果：Ch1-Ch150 150/150 accepted，`failed=[]`，无 AutoHalt
- P 洁净：pass，元标记 52→0、重复长段落 19→0，时间线 3 章 report-only
- L 文学：pass，conceptual_grounding first W=5 6.80、last W=5 6.06、threshold 5.78
- 阻断项：`不回退` fail，其中 `T5=False`、`T6c=False`

阻断根因不是 Task 165 的生成质量退化，而是 V6 阶段已登记的 harness 口径遗留：

- **T5**：当前 `check_t5()` 仍使用“前 10 样本均值 ×1.5”作为扫描耗时红线。Task 159 报告已判定该口径会把开局低耗时样本当作长期基线，导致 Ch100+ 自然增长被误判。Task 159 已建议改为“全样本中位数 ×2.0 + 单点稳健采样”。
- **T6c**：当前 hard 公式要求 `T7 降幅 >= orphan 斜率降幅 ×0.5`。当新 critical 产生率已被压到接近 0 时，T7 的绝对可下降空间不足，公式会把“源头收敛过度成功”误判为归因失败。Task 157/158/159 报告均已记录该小基数失真。
- **T6b**：部分报告因 continuity audit 只在审计点产出，把无报告章节当作“缺失章”导致 insufficient。需要明确审计点覆盖下的 P1=0 判定口径，并对已 resolved / archived 的历史对象避免污染当前 P1。

## In Scope

### 165p-a — T5 稳健口径落地

- [ ] 修改 `check_t5()` 的扫描耗时判定口径：
  - DB 尺寸红线继续保持 `DB <= 300MB`。
  - 扫描耗时基线从“前 10 样本均值”改为更稳健口径：全样本中位数或稳定样本中位数。
  - 阈值采用 Task 159 冻结建议：`median ×2.0`。
  - 单点抖动不得直接导致 hard fail；需要连续破线、重复采样或明确超出稳健阈值才 fail。
- [ ] 更新 `ThresholdResult.detail`，报告中清楚说明尺寸与耗时分别是否破线。
- [ ] 更新 `tests/test_158_t5_freeze.py` 与 `tests/test_157_v6_acceptance.py` 中 T5 相关断言。

### 165p-b — T6b/T6c 小基数与 resolved 口径校准

- [ ] 校准 `check_t6b()`：
  - continuity report 按审计点产出时，不把无审计点章节直接当作 P1 未判定污染整体结论。
  - 已 resolved / archived / abandoned 的历史 orphan 不计入当前 P1 hard fail。
  - 若所有审计点 `orphan_critical == 0` 且无 state mismatch P1，则 T6b 可判 pass。
- [ ] 校准 `check_t6c_attribution()`：
  - 新 critical 当前值接近 0 时，进入小基数保护，不用原比值公式强行 fail。
  - 同时检查 `T6c-obs`：candidate critical 占比不得异常；避免通过降级/丢弃粉饰下降。
  - 输出 detail 区分“真实归因失败”与“小基数下源头收敛已达标”。
- [ ] 更新 T6b/T6c 单测，覆盖：
  - 审计点 P1=0 但逐章报告不完整。
  - T7 当前接近 0 且 candidate critical=0 时不 fail。
  - candidate critical 占比异常时仍 fail 或至少不 pass。

### 165p-c — 复算 Task 165 阶段 W 出口

- [ ] 使用现有 `.tmp/task165_stage_w_ch150.db` 重新运行：

```powershell
$env:DATABASE_URL = 'sqlite:///.tmp/task165_stage_w_ch150.db'
python scripts/run_165_stage_w_ch150.py --report
```

- [ ] 核对 `docs/reports/task-165-stage-w-exit-report.md`：
  - P 洁净 pass
  - L 文学 pass
  - 修复对比 pass
  - 不回退 pass 或给出新的真实阻断项
- [ ] 若四项均 pass：
  - 冻结 T9/T10 正式口径到 `docs/v7-plan.md` §4。
  - 将 Task 165 从“条件完成”收口为 DONE 或创建对应 DONE 文档。
  - 更新 `docs/STATUS.md`、`tasks/V7-README.md`、`README.md`，允许进入 166。
- [ ] 若仍 fail：
  - 不进入 X/Y/Z。
  - 把新的真实阻断拆为后续 `165q` 或专项修复 Task。

## Out of Scope

- 不跑真实 LLM 长跑；只复算现有 Task 165 DB 与报告。
- 不修改 Writer / CreativeDirector / RevisionHandler / SettlementExtractor / Gate 行为。
- 不调整 T9/T10 文学与洁净度判据本身；T9/T10 只在 165p 复算通过后正式冻结。
- 不启动 Task 166 / 阶段 X。
- 不用阈值放宽掩盖真实生成退化；若复算发现真实退化，必须如实拆新 Task。

## 测试要求

- [ ] 目标测试：

```powershell
python -m pytest tests/test_157_v6_acceptance.py tests/test_158_t5_freeze.py -q
```

- [ ] 若改动影响报告渲染或 Task 165 脚本，补跑：

```powershell
python -m pytest tests/test_165_stage_w_smoke.py -q
```

- [ ] 常规收尾：

```powershell
python -m pytest tests/ -q
ruff check src/ tests/
```

## Acceptance Criteria

- [ ] T5 口径与 Task 159 已冻结建议一致：DB 尺寸仍硬红线，扫描耗时使用稳健中位数口径，不再被开局低样本误伤。
- [ ] T6b 在审计点覆盖足够、P1=0 时可判 pass，不因非审计点缺报告误判。
- [ ] T6c 在新 critical 小基数 / 近 0 场景下不再算术性 fail，同时保留 candidate critical 占比异常保护。
- [ ] Task 165 报告复算后，不回退项不再因已知 harness 缺陷 fail。
- [ ] 若 Task 165 四项全部 pass，T9/T10 正式冻结并更新事实入口；否则如实记录新阻断。

## 参考文档

- `docs/reports/task-165-stage-w-exit-report.md`
- `docs/reports/task-165-v7-threshold-calibration.md`
- `docs/reports/task-159-v6-final-acceptance-report.md`
- `docs/reports/task-157-ch1-ch50-integration-validation-report.md`
- `docs/reports/task-158-ch1-ch100-long-run-validation-report.md`
- `tasks/148z-stage-a-threshold-calibration-DONE.md`
- `tasks/156-in-run-db-maintenance-DONE.md`
- `tests/test_157_v6_acceptance.py`
- `tests/test_158_t5_freeze.py`
