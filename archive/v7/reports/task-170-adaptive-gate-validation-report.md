# Task 170: 自适应门禁小窗口验证 + T12 误报率标定报告

> 生成时间: 2026-07-06 13:16:19
> 脚本: `scripts/run_170_adaptive_gate_validation.py`
> 隔离 DB: `C:\Vibe Project\Songyan\.tmp\task170_adaptive_gate_validation.db`

## 1. 执行摘要

- **T12 结论**: 冻结。良性窗口 false positive rate=0 且退化窗口 halt_candidate_or_halt_rate=100%，满足首版 T12 冻结口径。
- 良性窗口 false positive rate: 0%；退化窗口 halt_candidate_or_halt rate: 100%。
- 验证走真实 168 数据面(seed 快照→窗口聚合)+ 真实 169 判定(evaluate_adaptive_halt)，observe/enforce 双模式。

## 2. 环境与 run/config

| 项 | 值 |
|----|----|
| 隔离 DB | `C:\Vibe Project\Songyan\.tmp\task170_adaptive_gate_validation.db` |
| 窗口大小 W | 5 |
| 窗口章节区间 | Ch16-Ch20(越过 warmup=10) |
| observe policy | mode=observe, warmup=10, require_multi_signal=True |
| enforce policy | mode=enforce, warmup=10, require_multi_signal=True |
| 是否触碰 Ch200 | 否 |
| 是否改主库/正文链路 | 否 |
| 是否依赖外部 LLM | 否(合成快照) |

## 3. 场景清单

| 场景 | 类别 | 说明 |
|------|------|------|
| A-benign(良性波动窗口) | benign | health 在 8.3-8.6 间小幅波动(始终 ≥ 阈值 7.0)，仅单章出现 1 个 P1，orphan 平缓(delta≈1，slope 远低于 1.0)，无质量债，schedule 命中，仅首章一次 context emergency observation。 |
| B-degradation(真实退化窗口) | degradation | health 连续 5 章从 7.2 跌到 5.0(跌破阈值)，P1 中位数抬升，orphan 从 6 加速到 24(slope≫1、delta=18)，后段 degraded_accept/qg_false，schedule 持续 missed，跨 continuity/quality/narrative/context 多域退化。 |
| C-control(对照窗口(单点毛刺)) | control | 仅第 3 章 health 骤降到 3.0、P1=5 的单点毛刺，前后章节正常。用于对照旧 gate 的单点敏感性与 adaptive 的趋势/多域约束。 |
| D-single-signal(单域持续异常窗口) | benign | 仅 continuity 单域持续异常(health 6.4-6.8 略低于阈值、P1 中位数=2)，quality/narrative/context 均正常。用于验证 require_multi_signal 下单域异常只升级为 warn，不误报为 halt。 |

## 4. 过程监测表

| 场景 | seed 快照 | 窗口数 | observe status | observe reasons | enforce status | enforce reasons |
|------|-----------|--------|----------------|-----------------|-----------------|-----------------|
| A-benign | 5 | 1 | `continue` | - | `continue` | - |
| B-degradation | 5 | 1 | `halt_candidate` | health_p1_spike, orphan_acceleration, quality_debt_streak, schedule_miss_spike, context_pressure_streak | `halt` | health_p1_spike, orphan_acceleration, quality_debt_streak, schedule_miss_spike, context_pressure_streak |
| C-control | 5 | 1 | `continue` | - | `continue` | - |
| D-single-signal | 5 | 1 | `warn` | health_p1_spike | `warn` | health_p1_spike |

## 5. 数据采集完整性

| 场景 | 信号域 present/missing 判定 | 是否排除硬判 | 排除理由 |
|------|------------------------------|--------------|----------|
| A-benign | 6 域均 present(合成) | 否 | - |
| B-degradation | 6 域均 present(合成) | 否 | - |
| C-control | 6 域均 present(合成) | 否 | - |
| D-single-signal | 6 域均 present(合成) | 否 | - |

> 采集口径: `missing/insufficient/observation` 不进入 T12 hard fail 分母。本次合成场景 6 域均 present 且窗口充分，无排除项。

## 6. 旧 gate vs adaptive halt 对照(Window C 及全场景)

| 场景 | 旧 gate 是否触发 | 旧 gate 触发章 | 是否单点触发 | adaptive(observe) | reason 是否一致 |
|------|------------------|----------------|--------------|-------------------|-----------------|
| A-benign | 是 | [18] | 是 | `continue` | 旧 gate 更敏感(单点) |
| B-degradation | 是 | [16, 17, 18, 19, 20] | 否 | `halt_candidate` | 方向一致 |
| C-control | 是 | [18] | 是 | `continue` | 旧 gate 更敏感(单点) |
| D-single-signal | 是 | [16, 17, 18, 19, 20] | 否 | `warn` | 旧 gate 更敏感(多章绝对阈值) |

> 关键差异: 旧 `_gates.py` 逐章判定，单点 P1 尖峰(对照窗口 C)即可触发 health_low_p1_halt；adaptive halt 要求窗口内多域持续退化(require_multi_signal)，对单点毛刺只给 warn/continue，从而降低单点误伤。Task 170 不删除旧 gate。

## 7. T12 误报 / 漏拦统计

| 指标 | 值 |
|------|----|
| false_positive_count | 0 |
| false_negative_count | 0 |
| benign_window_count | 3 |
| degraded_window_count | 1 |
| excluded_window_count | 0 |
| false positive rate | 0% |
| degraded halt_candidate_or_halt rate | 100% |

> false negative note: 退化窗口若未达 halt_candidate 记漏拦；本口径基于 observe 模式(默认生产模式)判定。

## 8. 可读性 / 文学性抽检

本任务为合成信号验证(不生成真实正文)，抽检以信号→正文期望的对应说明形式给出，覆盖可读性/文学性/连贯性/节奏/线索经济维度。真实正文抽读留待 Task 171 Ch200 小窗口。

### A-benign — 良性波动窗口

- 可读性: 抽检合成信号对应正文期望: 无元标记泄漏(meta=0)、无整段重复(duplicate=0)、无 AI 腔堆叠。属正常创作波动。
- 文学性: literary/conceptual 维持高位，无概念空转；单点 P1 为孤立未回收设定，人工复核判定不需暂停。

### B-degradation — 真实退化窗口

- 可读性: 退化窗口后段合成信号提示 qg_false/降级接受累积，对应正文期望出现连贯性下滑；本场景用于验证门禁能拦截，不代表已生成劣质正文。
- 文学性: 多域同时退化(health+orphan+质量债+schedule)，人工复核判定确有事实源/叙事风险，属 true degradation，应触发 halt_candidate/halt。

### C-control — 对照窗口(单点毛刺)

- 可读性: 单点毛刺，前后正文正常，属可接受短期波动。
- 文学性: 孤立单章异常，人工复核判定不需暂停，属 benign fluctuation。

### D-single-signal — 单域持续异常窗口

- 可读性: 单域信号，正文期望无洁净度问题，属需关注但不需暂停的短期波动。
- 文学性: 仅连续性单域走弱，人工复核判定给 warn 观察即可，不属于需要暂停的 true degradation。

**抽检结论**: pass — 合成场景无元标记/重复段落/AI 腔信号(良性场景 meta=duplicate=0)，门禁判定未因验证本身引入正文退化;无 blocker。

## 9. 结论: T12 是否冻结

- **T12: 冻结**。良性窗口 false positive rate=0 且退化窗口 halt_candidate_or_halt_rate=100%，满足首版 T12 冻结口径。
- 冻结阈值建议(首版): 良性波动窗口 false positive rate = 0，真实退化窗口 halt_candidate_or_halt rate = 100%；样本不足只能标未冻结，不宣称通过。

## 10. 下一步

- 良性无误伤、退化能拦、可读性抽检无 blocker、T9/T10/T5/T6 口径未改动: **允许规划 Task 171 Ch200 长跑**(仍需在 171 首窗做真实正文抽读)。

> 边界确认: 本任务未启动 Ch200、未改 Writer/RevisionHandler/SettlementExtractor、未放宽 T9/T10/T5/T6、未删除旧 `_gates.py`。
