# Task 162 DONE: 跨章时间线一致性检测

> **Phase**: V7 阶段 W（篇章级质量修复）
> **完成时间**: 2026-07-04
> **结论**: 完成。已新增规则化时间信号抽取、跨章时间线冲突诊断，并接入 `songyan metrics` 报告段；保持诊断项，不阻塞 accept。

---

## 目标回放

Task 162 针对 V6 `run-bba292da` 暴露的跨章时间线矛盾，要求：

- 抽取确定性时间信号：倒计时、日期/时间戳、明确相对时序；
- 检出相邻/近邻章中倒计时反增、日期回跳等矛盾；
- 作为 report/metrics 诊断项展示；
- 不接入 ReviewIssue、QualityGate 或 accept 阻塞。

## 已完成改动

| 模块 | 改动 |
|------|------|
| `src/songyan/evals/timeline_consistency.py` | 新增 `TimeSignal` / `TimelineConflict`；实现 `extract_time_signals`、`detect_timeline_conflicts`、`collect_timeline_signals`、`collect_timeline_conflicts`、`render_timeline_consistency_section`。 |
| `src/songyan/evals/db_metrics.py` | `render_stage_a_metrics` 追加“跨章时间线一致性诊断”段；通过 `_guard` 降级，历史 DB/缺数据不影响其它度量段。 |
| `tests/test_162_timeline_consistency.py` | 新增 Task 162 专项测试，覆盖抽取、倒计时反增、日期回跳、闪回/档案上下文豁免、accepted 正文回读、metrics 报告渲染。 |

## 抽取口径

- **倒计时**：仅抽取显式倒计时/剩余表述，如“还剩三天”“倒计时 24 小时”“距启动还有 30 分钟”。归一化为小时用于比较。
- **绝对日期**：抽取 `YYYY-MM-DD` / `YYYY/MM/DD` / `YYYY年M月D日` / `M月D日`。有年份时使用真实日期序号；无年份时使用月日序号。
- **相对时序**：抽取“次日”“翌日”“第二天”“三天后”等，进入诊断明细，但本 Task 不用它直接判冲突。
- **闪回/档案上下文**：包含“闪回、回忆、梦境、旧日、档案、日志、录音、历史记录”等上下文的信号仍展示，但 `ignored_for_conflict=True`，不参与冲突判定。

## 判定规则

- **倒计时反增**：后续章节的倒计时归一化小时数大于前一个倒计时信号，记为 `countdown_increase`。
- **日期回跳**：后续章节的绝对日期早于前一个绝对日期信号，记为 `date_rewind`。
- **诊断边界**：不判定模糊主观时间感；不自动修复；不阻塞 accept；是否纳入 T9 红线留 Task 164/165 标定。

## 验收点

- 能检出 Ch75 式“还剩 3 天 → 还剩 5 天”的倒计时反增。
- 能检出“2040-07-03 → 2040-07-01”的日期回跳。
- 正常单调推进不误报。
- 明确闪回/档案上下文不误报。
- `render_stage_a_metrics` 可展示时间线诊断段。

## 验证

```powershell
python -m pytest tests/test_162_timeline_consistency.py -q
```

结果：`9 passed`

```powershell
python -m pytest tests/ -q
```

结果：`2296 passed, 2 skipped, 1 xfailed, 2 warnings`

```powershell
ruff check src/ tests/
```

结果：`All checks passed!`

## 边界

- 未执行 `run-bba292da` Ch75 等真实章节复算；真实样本覆盖率留 Task 164/165 的洁净度入库与 Ch150 复跑统一核验。
- 不做跨线/多视角复杂时间轴建模。
- 不引入 LLM 时间逻辑判断。
- 不接入门禁或 ReviewIssue。

## 下一步

进入 Task 163：概念预算约束（治概念通胀）。
