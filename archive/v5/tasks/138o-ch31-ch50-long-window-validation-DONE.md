# Task 138o：Ch31-Ch50 长窗口延续验证

> **类型**: 实跑验证 / 稳定性测试
> **状态**: 已完成（Ch31-Ch50 全部通过）
> **前置**: Task 138n 已完成，Ch1-Ch30 重跑验证通过，Ch30 health 8.5、P1/P2 critical orphan 0。
> **依赖**: Task 138n 代码改动已落地，延续脚本 `scripts/run_138o_ch31_ch50_continuation.py` 已创建。
>
> **执行结果**: Run `run-01a32b97`；Ch31-Ch50 20/20 完成，无失败，无 AutoHalt；settlement/QG 通过率 20/20；Ch50 health 8.8，P1/P2 critical orphan 0；报告见 `archive/v5/reports/task-138o-ch31-ch50-long-window-validation-report.md`。

## 目标

在 Task 138n 的 30 章基础上继续跑 **Ch31-Ch50**，验证 138n 的 A+C 改动能否将高 health / 零 P1 critical orphan 的状态维持到更长序列。

核心问题：

1. Ch50 的 continuity health 是否仍 ≥ 6.0？
2. Ch50 的 P1/P2 critical orphan 是否仍 ≤ 5？
3. Ch31-Ch50 的平均 settlement/QG 通过率是否 ≥ 85%？
4. 是否会出现新的 AutoHalt 或系统性质量退化？

## 验收标准

- [ ] Ch31-Ch50 全部完成，或出现明确 AutoHalt 原因。
- [ ] Ch50 continuity health ≥ 6.0（理想 ≥ 7.0）。
- [ ] Ch50 的 P1/P2 critical orphan ≤ 5（理想 0）。
- [ ] Ch31-Ch50 中 settlement/QG 通过率 ≥ 85%。
- [ ] 若 health 在某一章跌至 < 5.0，记录该章并停止，分析根因后决定是否继续。
- [ ] 输出报告 `archive/v5/reports/task-138o-ch31-ch50-long-window-validation-report.md`。
- [ ] 更新 `docs/STATUS.md`、`tasks/V5-README.md`、`docs/INDEX.md`。

## 不做的事

- **不修改业务代码**：本任务只验证，不修复；若发现新问题，创建 Task 138p 处理。
- **不复写 Ch1-Ch30**：使用 138n 的现有项目和 DB，从 Ch31 继续。
- **不删除 138n DB**：`.tmp/task138n_ch1_ch30_rerun.db` 保留作为证据。

## 实现步骤

### 1. 创建延续脚本

新建 `scripts/run_138o_ch31_ch50_continuation.py`，基于 `scripts/run_138n_ch1_ch30_rerun.py` 修改：

- 固定 `START_CHAPTER=31`、`END_CHAPTER=50`。
- 固定 `PROJECT_ID` 为 138n 验证项目 ID（`987fccbd53414e3da76da0fe07f887a9`）。
- 移除源项目克隆逻辑；如果项目不存在则报错。
- `chapter_range=(START_CHAPTER, END_CHAPTER)`。
- 报告输出到 `archive/v5/reports/task-138o-ch31-ch50-long-window-validation-report.md`。
- metrics 追加到 `.tmp/task138o_ch31_ch50_metrics.jsonl`。
- 仍临时切换 Writer default_version 为 1.2.0，退出时恢复。

### 2. 确认前置条件

```powershell
# 检查 138n 项目是否存在
python - <<'PY'
import asyncio
from songyan.db.repository import ProjectRepository
async def main():
    p = await ProjectRepository().get("987fccbd53414e3da76da0fe07f887a9")
    print(p is not None)
asyncio.run(main())
PY
```

预期输出：`True`

### 3. 启动后台运行

```powershell
$env:DATABASE_URL = "sqlite:///.tmp/task138n_ch1_ch30_rerun.db"
$env:PROJECT_ID = "987fccbd53414e3da76da0fe07f887a9"
python scripts/run_138o_ch31_ch50_continuation.py
```

预计耗时：20 章 × 5-8 分钟 ≈ **2-3 小时**。

### 4. 监控与中断策略

每章输出关键指标。若出现以下情况，人工评估是否停止：

- 连续 3 章 settlement 失败；
- 连续 3 章 quality_gate 未通过；
- continuity health 单章跌幅 > 2.0；
- AutoHalt 触发。

### 5. 报告与结论

报告必须包含：

- Ch31-Ch50 每章关键指标表（同 138n 报告格式）；
- Ch30/Ch40/Ch50 三个检查点的 continuity 趋势对比；
- 与 138n Ch1-Ch30 的对比总结；
- 是否达到验收标准；
- 若未达标，明确下一步 Task 编号与假设。

## 风险与 Fallback

- **风险 1**：Ch31-Ch50 引入新主线/新 critical 设定，导致 health 快速下滑。
  - Fallback：若 Ch40 health < 5.0，停止并创建 Task 138p 分析新设定管理策略。
- **风险 2**：MR 上限在 50 章后不足以覆盖所有待回收设定。
  - Fallback：调整 `max_mandatory_references` 上限或排序权重，小窗口验证后再跑。
- **风险 3**：单一章节像 Ch13 一样降级接受，拉低 settlement/QG 通过率。
  - Fallback：若通过率 < 85% 但 health 正常，记录为可接受波动；否则分析。

## 参考

- Task 138n DONE：`archive/v5/tasks/138n-qg-mandatory-reference-revision-loop-DONE.md`
- 138n 报告：`archive/v5/reports/task-138n-ch1-ch30-rerun-report.md`
- 138m 根因报告：`archive/v5/reports/task-138m-critical-orphan-root-cause-report.md`
- 138k 基线报告：`archive/v5/reports/task-138k-long-window-rehearsal-report.md`
- 延续 DB：`.tmp/task138n_ch1_ch30_rerun.db`
- 延续项目 ID：`987fccbd53414e3da76da0fe07f887a9`
