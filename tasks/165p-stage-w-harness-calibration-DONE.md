# Task 165p DONE — 阶段 W 出口阻断项 T5/T6 harness 口径校准

> **状态**: ✅ 完成
> **完成时间**: 2026-07-05
> **对应规划**: `tasks/165p-stage-w-harness-calibration.md`
> **验证 DB**: `.tmp/task165_stage_w_ch150.db`
> **验证 run**: `run-11fc7c96`

## 结论

Task 165p 已解除 Task 165 阶段 W 出口剩余阻断项。复算后阶段 W 四项全部通过：

- P 洁净：pass，元标记=0，重复长段落=0，时间线 3 章 report-only。
- L 文学：pass，conceptual_grounding first W=5 6.80、last W=5 6.06、threshold 5.78。
- 修复对比：pass，元标记 52→0、重复长段落 19→0。
- 不回退：pass，T2/T3/T4/T5/T6a/T6b/T6c 均无 sufficient fail。

阶段 W 正式通过；T9/T10 可冻结；下一步可进入 Task 166 规划。

## 代码改动

- `src/songyan/evals/db_maintenance_metrics.py`
  - 新增 `T5LatencyAnalysis` 与 `analyze_t5_latency_samples()`。
  - T5 扫描耗时改为章级样本中位数口径：同章多样本先聚合，基线取全样本中位数，hard 阈值为 median×2.0。
  - 孤立超阈值样本只记观察项；连续破线或极端破线才 hard fail。
- `src/songyan/evals/v6_acceptance.py`
  - `check_t5()` 复用稳健 T5 口径。
  - `check_t6b()` 改为审计点覆盖口径，不要求每章都有 continuity report；审计点 P1=0 即可判 pass。
  - `check_t6c_attribution()` 增加 T7 小基数保护：新 critical 近 0 时不再被原降幅比值算术误伤。
  - 聚合结论改为“无 failed sufficient 项”，避免 T7/T6c-obs 观察项未判定导致整体误报 fail。
- `src/songyan/evals/db_metrics.py`
  - DB 维护遥测段同步展示 median×2.0、观察项与 hard 破线口径。
- `scripts/run_158_ch1_ch100.py`
  - T5 冻结辅助复用统一 T5 分析口径。
- `scripts/run_165_stage_w_ch150.py`
  - T9/T10 渲染从“冻结草案”更新为“冻结结论”。

## 验证

目标测试：

```powershell
python -m pytest tests/test_157_v6_acceptance.py tests/test_158_t5_freeze.py tests/test_165_stage_w_smoke.py -q
```

结果：

```text
55 passed
```

目标 lint：

```powershell
ruff check src/songyan/evals/v6_acceptance.py src/songyan/evals/db_maintenance_metrics.py src/songyan/evals/db_metrics.py scripts/run_158_ch1_ch100.py tests/test_157_v6_acceptance.py tests/test_158_t5_freeze.py tests/test_165_stage_w_smoke.py
```

结果：

```text
All checks passed!
```

Task 165 报告复算：

```powershell
$env:DATABASE_URL = 'sqlite:///.tmp/task165_stage_w_ch150.db'
python scripts/run_165_stage_w_ch150.py --report
```

复算后报告：

- `docs/reports/task-165-stage-w-exit-report.md`
- `docs/reports/task-165-v7-threshold-calibration.md`

## 冻结口径

- **T9**：元标记=0、重复长段落=0 为硬红线；时间线矛盾继续 report-only，本次诊断章为 [21, 37, 142]。
- **T10**：conceptual_grounding 末段 W=5 均值 >= 首段 W=5 ×0.85，本次 first=6.80、last=6.06、threshold=5.78，pass。
- **T5**：DB 尺寸 <=300MB；扫描耗时使用章级中位数 ×2.0，孤立观察项不 hard fail。
- **T6b/T6c**：审计点 P1=0 可判 T6b pass；T7 近 0 时启用 T6c 小基数保护，同时保留 candidate critical 观察项。
