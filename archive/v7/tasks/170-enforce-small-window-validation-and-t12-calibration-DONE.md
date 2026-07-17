# Task 170 DONE: enforce 小窗口验证 + T12 误报率标定

> **完成时间**: 2026-07-06
> **阶段**: V7 阶段 Y（enforce 可生产化）
> **结论**: 完成，**T12 冻结**。良性波动窗口 false positive rate=0、真实退化窗口 halt_candidate_or_halt rate=100%，可读性/文学性抽检无 blocker，未改动 T9/T10/T5/T6 口径，未启动 Ch200。**允许规划 Task 171 Ch200 长跑**。

---

## 交付内容

- 验证脚本 `scripts/run_170_adaptive_gate_validation.py`：
  - 隔离 DB（覆盖 `settings.database_url` + `init_schema`，可重复运行、覆盖旧文件）。
  - seed 4 类合成场景快照（真实 168 数据面 `build_adaptive_gate_data_plane_report`）。
  - 真实 169 判定 `evaluate_adaptive_halt`，observe / enforce 双模式。
  - decision 落库 `adaptive_halt_decisions`（验证 repo 往返）。
  - 旧 `_gates.py` `evaluate_all_gates` 用同批信号构造 `ContinuityReport` 逐章对照。
  - T12 误报/漏拦统计 + 冻结判定。
  - 输出机器可读 `.tmp/task170_adaptive_gate_validation_metrics.jsonl`。
  - 输出人类可读 `docs/reports/task-170-adaptive-gate-validation-report.md`（10 小节）。
- 自动化测试 `tests/test_170_adaptive_gate_validation.py`（17 tests）。
- 验证报告 `docs/reports/task-170-adaptive-gate-validation-report.md`。

## 验证场景与结果

| 场景 | 类别 | observe | enforce | 旧 gate | T12 归类 |
|------|------|---------|---------|---------|----------|
| A-benign（良性波动） | benign | `continue` | `continue` | 触发（单点 Ch18） | correct_negative |
| B-degradation（真实退化，多域） | degradation | `halt_candidate` | `halt` | 触发（Ch16-20） | correct_positive |
| C-control（单点毛刺） | control | `continue` | `continue` | 触发（单点） | correct_negative |
| D-single-signal（单域持续） | benign | `warn` | `warn` | 触发（多章绝对阈值） | correct_warn |

关键证据：**A/C 场景旧 `_gates.py` 因单点 P1 尖峰触发 health_low_p1_halt，而 adaptive halt 保持 `continue`** —— 证明自适应门禁用窗口趋势/多域约束（`require_multi_signal`）降低了单点误伤；D 场景单域持续异常只升级为 `warn` 不误报；B 场景多域真实退化被 `halt_candidate`/`halt` 拦截。

## T12 冻结口径

| 指标 | 值 |
|------|----|
| false_positive_count | 0 |
| false_negative_count | 0 |
| benign_window_count | 3 |
| degraded_window_count | 1 |
| excluded_window_count | 0 |
| false positive rate | 0% |
| degraded halt_candidate_or_halt rate | 100% |

- **首版 T12 冻结口径**：良性波动窗口 false positive rate = 0，且真实退化窗口 halt_candidate_or_halt rate = 100%；样本不足只能标未冻结，不宣称通过。
- 分母口径：`missing/insufficient/observation` 与样本不足窗口不计入 T12 hard fail 分母；warn-on-benign 记 correct_warn（可接受），不计 false positive。

## 可读性 / 文学性抽检

- 合成信号验证不生成真实正文，抽检以信号→正文期望对应说明形式给出，覆盖可读性/文学性/连贯性/节奏/线索经济维度。
- 结论：**pass**，无元标记/重复段落/AI 腔信号，门禁判定未因验证本身引入正文退化，无 blocker。
- 真实正文抽读留待 Task 171 Ch200 首窗。

## 行为边界（本任务未越界）

- 不启动 Ch200（窗口区间固定 Ch16-Ch20）。
- 不改 Writer / RevisionHandler / SettlementExtractor。
- 不改主库业务数据（隔离 DB）。
- 不依赖外部 LLM（合成快照）。
- 不放宽 T9/T10/T5/T6 已冻结/已校准口径。
- 不删除旧 `_gates.py`。
- 不把 timeline conflict 从 report-only 升级为硬红线。

## 验证结果

```powershell
python scripts/run_170_adaptive_gate_validation.py --scenario all
# A=continue, B=halt_candidate/halt, C=continue, D=warn；T12 frozen=True FP_rate=0.0 catch_rate=1.0

python -m pytest tests/test_170_adaptive_gate_validation.py -q
# 17 passed

ruff check src/ tests/ scripts/run_170_adaptive_gate_validation.py
# All checks passed
```

## 与 Task 171 的关系

Task 170 报告同时满足：T12 冻结、可读性/文学性抽检无 blocker、adaptive halt 小窗口无良性误伤、真实退化能被拦截 —— **允许规划 Task 171 Ch200 长跑**（171 首窗仍需做真实正文抽读）。
