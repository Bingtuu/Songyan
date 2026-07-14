# Task 170: enforce 小窗口验证 + T12 误报率标定

> **Phase**: V7 阶段 Y（enforce 可生产化）
> **优先级**: P0（Task 171 Ch200 长跑前置）
> **状态**: ◻ 规划中
> **依赖**: Task 168 DONE（自适应门禁数据面）；Task 169 DONE（自适应 halt 判定）
> **事实入口**: `tasks/V7-README.md`；规划：`docs/v7-plan.md` §3 阶段 Y

---

## Goal

用可控小窗口验证 168/169 的自适应门禁是否满足“良性波动不误伤、真实退化能拦截”，并冻结 V7 的 **T12 门禁误报率口径**。

Task 170 是验证与标定任务，不是长跑任务。它的交付物应回答：

1. adaptive halt 在良性波动样本上是否不误伤。
2. adaptive halt 在真实退化样本上是否能给出 `halt_candidate` / `halt`。
3. 旧 `_gates.py` 绝对阈值与新 adaptive halt 的差异在哪里。
4. T12 的分母、分子、排除项和冻结阈值是什么。
5. 小窗口生成结果在可读性、文学性和叙事连贯性上是否没有明显回退。

## 背景

Task 168 已建立自适应门禁数据面：

- `adaptive_gate_signal_snapshots`
- `AdaptiveGateDataPlaneReport`
- `songyan metrics` 自适应门禁数据面段

Task 169 已建立自适应 halt 判定：

- `adaptive_halt_decisions`
- `evaluate_adaptive_halt(...)`
- phase2 observe/enforce 后处理接入

但 168/169 目前只证明了机制正确，尚未证明小窗口运行中“该停时停、不该停时不停”。Task 170 用受控样本和小窗口实跑完成这一步，避免直接把新门禁带进 Ch200。

## 总体边界

- 不启动 Ch200；Ch200 属于 Task 171。
- 不修改 Writer / RevisionHandler / SettlementExtractor。
- 不自动 rewrite。
- 不自动创建 ReplanProposal。
- 不放宽 T9/T10/T5/T6 已冻结或已校准口径。
- 不把 timeline conflict 从 report-only 临时升级为硬红线。
- 不把 T12 阈值写死到长跑前，必须先出报告。
- 验证任务允许新增脚本、seed 数据、报告、测试；治理逻辑缺陷另开修复任务。

## 验证策略

Task 170 分两类窗口：

| 窗口 | 目标 | 预期 |
|------|------|------|
| 良性波动窗口 | 模拟正常创作波动、孤立 P1、单章 context pressure、timeline observation | 不 halt；最多 warn/observe |
| 真实退化窗口 | 模拟多窗口 orphan 加速、质量债上升、schedule missed/overdue、context pressure streak | 至少 halt_candidate；enforce 小窗可 halt |

建议先用合成/seeded DB + mock phase2，再做一个极小真实生成窗口。不要在 170 阶段运行 Ch200。

## 过程监测要求

170 必须记录运行过程，而不只看最终 pass/fail：

- 每章开始/结束时间、耗时、状态。
- `gate_mode`、`adaptive_halt_enabled`、`adaptive_halt_action_mode`。
- 每章 `AdaptiveGateDataPlaneReport` 的 snapshot_count、window_count、source_status_counts。
- 每章 `AdaptiveHaltDecision.status` 和 reason codes。
- 是否触发旧 gate、是否触发 adaptive gate。
- AutoHalt 出现时的 `reason`、last_chapter、decision_id。
- context emergency、budget_used、DB size、scan latency。
- schedule lifecycle：injected / satisfied / missed / overdue。
- T9/T10/T5/T6 相关红线是否保持原口径。

建议输出两类文件：

- 机器可读：`.tmp/task170_adaptive_gate_validation_metrics.jsonl`
- 人类可读：`docs/reports/task-170-adaptive-gate-validation-report.md`

## 数据收集要求

170 的数据采集应覆盖以下事实源：

| 数据 | 来源 |
|------|------|
| adaptive gate snapshots | `adaptive_gate_signal_snapshots` |
| adaptive halt decisions | `adaptive_halt_decisions` |
| run log | `logs/chapter_runs/<run_id>.jsonl` |
| quality debt | `run_quality_debt` / `ChapterRunLog` |
| continuity/orphan | `continuity_reports` / 168 snapshot |
| T9 | `text_cleanliness_metrics` |
| T10 | `literary_observations` / Task 147 trend |
| T5 | `run_db_metrics` |
| schedule lifecycle | `foreshadowing_schedule_items` / 168 snapshot |

所有采集必须区分：

- sufficient
- insufficient
- missing
- observation

其中 `missing/insufficient/observation` 不应进入 T12 hard fail 分母，除非报告明确说明原因。

## T12 标定口径

### 术语

| 术语 | 定义 |
|------|------|
| true degradation | 多信号持续退化，且人工复核认为确有事实源/质量/叙事风险 |
| benign fluctuation | 孤立波动或可接受的短期波动，人工复核不认为需要暂停 |
| false positive | benign fluctuation 被 adaptive halt 暂停，或在 enforce 下会暂停 |
| false negative | true degradation 未达到 `halt_candidate` |
| observation-only | 样本不足、timeline report-only、T5 单点观察等不能计入硬判 |

### 状态计数建议

| decision status | 良性波动窗口 | 真实退化窗口 |
|-----------------|--------------|--------------|
| `continue` | 正确 | 漏拦候选 |
| `observe` | 正确或样本不足 | 若样本充分则漏拦候选 |
| `warn` | 可接受 | 偏弱，需人工判断是否漏拦 |
| `halt_candidate` | 误报候选 | 正确 |
| `halt` | 误报（若良性） | 正确 |

### T12 冻结输出

报告必须给出：

- `false_positive_count`
- `false_negative_count`
- `benign_window_count`
- `degraded_window_count`
- `excluded_window_count`
- false positive rate
- false negative note
- 冻结建议阈值

建议首版 T12 口径：

> T12 pass = 良性波动窗口 false positive rate = 0，且真实退化窗口 `halt_candidate_or_halt_rate = 100%`。若样本不足，只能标为“未冻结”，不能宣称通过。

## 可读性 / 文学性验证要求

170 虽然主要验证 gate，但必须加入小窗口正文抽检，避免门禁验证只看数字。

抽检范围建议：

- 良性波动窗口：至少抽 2 章 accepted 正文。
- 真实退化窗口：至少抽 2 章触发前后的正文或合成片段说明。
- 若使用真实 LLM 小窗口，则必须抽读全部生成章节。

抽检维度：

| 维度 | 检查点 |
|------|--------|
| 可读性 | 是否有元标记、重复段落、明显 AI 腔句式复用 |
| 文学性 | 是否出现概念空转、人物声纹同质、说明文堆叠 |
| 连贯性 | 章节目标是否连贯，状态/设定是否可追踪 |
| 节奏 | 是否因门禁/约束注入导致场景僵硬或停滞 |
| 线索经济 | schedule item 是否自然进入剧情，而不是机械旁白交代 |

抽检结果必须写入报告，结论分为：

- pass：无明显可读性/文学性回退。
- observation：有轻微风格债，但不影响 170 gate 验证。
- blocker：门禁接入导致正文明显退化，需要先修复再进 171。

## In Scope

- [ ] 新增 170 验证脚本：
  - `scripts/run_170_adaptive_gate_validation.py`
- [ ] 新增合成/seeded 小窗口样本：
  - benign fluctuation
  - true degradation
- [ ] 运行 adaptive gate observe/enforce 小窗口验证。
- [ ] 对比旧 `_gates.py` 和新 adaptive halt 的判定差异。
- [ ] 采集过程监测 JSONL。
- [ ] 生成 T12 标定报告。
- [ ] 加入可读性/文学性抽检章节。
- [ ] 新增自动化测试：
  - `tests/test_170_adaptive_gate_validation.py`

## Out of Scope

- 不启动 Ch200。
- 不直接改 Writer / RevisionHandler。
- 不直接重调 Prompt。
- 不替换旧 `_gates.py`。
- 不冻结 T11。
- 不做跨题材验证。

## 验证窗口设计

### Window A: 良性波动

构造信号：

- health 小幅下降但仍可接受。
- P1 只有单点或小基数。
- context emergency 单章 observation。
- timeline conflict 仅 report-only。
- schedule 无 missed 或只有小基数 observation。

预期：

- adaptive decision 不应为 `halt`。
- enforce 模式不应 AutoHalt。
- 可读性抽检不应 blocker。

### Window B: 真实退化

构造信号：

- 连续窗口 health 下降。
- P1/P2 或 orphan slope 抬升。
- quality debt 比例偏高。
- schedule missed / overdue 抬升。
- context pressure streak 可选。

预期：

- adaptive decision 至少 `halt_candidate`。
- explicit enforce 模式可 `halt`。
- 报告必须说明触发 reason 和 evidence window。

### Window C: 对照旧 gate

用同一批数据比较：

- 旧 `_gates.py` 是否会被单点误伤。
- adaptive halt 是否因样本不足选择 observe。
- 两者 reason 是否一致。

预期：

- 报告给出差异表。
- 不在 Task 170 内删除旧 gate。

## 脚本要求

建议 CLI：

```powershell
python scripts/run_170_adaptive_gate_validation.py --scenario all --output docs/reports/task-170-adaptive-gate-validation-report.md
```

脚本职责：

- 初始化隔离 DB。
- seed project / snapshots / decisions / optional run logs。
- 运行 169a/169b 验证路径。
- 输出 JSONL 过程数据。
- 输出 Markdown 报告。
- 可重复运行，覆盖旧 `.tmp/task170_*` 文件。

脚本禁止：

- 调真实长跑 Ch200。
- 修改主库业务数据。
- 依赖外部 LLM 才能通过测试。

## 报告结构

`docs/reports/task-170-adaptive-gate-validation-report.md` 应包含：

1. 执行摘要。
2. 环境和 run/config。
3. 场景清单。
4. 过程监测表。
5. 数据采集完整性。
6. 旧 gate vs adaptive halt 对照。
7. T12 误报/漏拦统计。
8. 可读性/文学性抽检。
9. 结论：T12 是否冻结。
10. 下一步：是否允许进入 171，或是否需要 170p 修复。

## 测试要求

目标测试：

```powershell
python -m pytest tests/test_170_adaptive_gate_validation.py -q
```

必要覆盖：

- [ ] 良性波动窗口不 halt。
- [ ] 真实退化窗口 halt_candidate / halt。
- [ ] missing/insufficient 不计入 hard fail。
- [ ] T12 统计分母/分子正确。
- [ ] 报告包含过程监测、数据采集、可读性/文学性抽检段。
- [ ] 脚本可重复运行。
- [ ] 不触碰 Ch200。

## 验收标准

Task 170 完成时必须满足：

- [ ] 小窗口验证脚本可运行。
- [ ] 良性波动样本无误伤。
- [ ] 真实退化样本能拦或至少给出 halt_candidate。
- [ ] T12 口径明确，报告给出冻结/未冻结结论。
- [ ] 可读性/文学性抽检无 blocker。
- [ ] 不改变 T9/T10/T5/T6 既有口径。
- [ ] 更新 `tasks/V7-README.md` / `docs/STATUS.md` / `docs/v7-plan.md`。
- [ ] 生成 `tasks/170-enforce-small-window-validation-and-t12-calibration-DONE.md`。

## 与 Task 171 的关系

只有当 Task 170 报告同时满足：

- T12 可冻结或明确条件通过；
- 可读性/文学性抽检无 blocker；
- adaptive halt 小窗口无良性误伤；
- 真实退化能被拦截或至少 halt_candidate；

才允许规划 Task 171 Ch200 长跑。

若 170 不通过，应先开 `170p` 定点修复，不进入 Ch200。
