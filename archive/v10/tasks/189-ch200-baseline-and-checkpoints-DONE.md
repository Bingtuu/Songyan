# Task 189: Ch200 baseline 与 checkpoint 冻结 — DONE

> **阶段**: V10.1 Ch200 口径与工具
> **类型**: 只读重放 / baseline 冻结 / 工具口径校验
> **优先级**: P0（所有非 sci-fi Ch200 终判的标尺）
> **状态**: ✅ 完成
> **日期**: 2026-07-23

---

## 任务边界

本任务只冻结 sci-fi Ch200 对标口径，不启动 xuanhuan / wuxia / urban Ch200，不修改 five-gate / CED / T9 判定函数，不引入优秀度信号。

---

## 事实源

| 项 | 值 |
|----|----|
| DB | `.tmp/task171_ch1_ch200.db` |
| project_id | `835afdf11a294b5eac74a5d8998bd9a2` |
| Ch200 run_id | `run-fb39245c` |
| Ch200 run 状态 | `completed`，范围 Ch1-Ch200，current_chapter=200 |
| DB 追加事实 | 同库另有 Ch201-Ch220 run `run-e27b763f`；Task 189 只取 Ch1-Ch200 |
| accepted head | Ch1-Ch200 = 200/200 |
| D1 clean | 使用 171t/171u 后当前 accepted head；T9 复算为 0 |

---

## 产物

| 文件 | 内容 |
|------|------|
| `.tmp/189_scifi_ch200_at125.json` ... `.tmp/189_scifi_ch200_at200.json` | 原始 checkpoint 指标采集。使用默认 Ch100 baseline 判定会 FAIL，仅取 metrics |
| `archive/v10/artifacts/189-scifi-ch200-baseline.json` | 受版本管理的 canonical baseline，适用范围 Ch125-Ch200 |
| `.tmp/189_scifi_ch200_baseline.json` | 本轮工作副本，不作为长期事实入口 |
| `.tmp/189_scifi_ch200_with_baseline_at125.json` ... `.tmp/189_scifi_ch200_with_baseline_at200.json` | 显式 Ch200 baseline 回放结果，四档均 PASS |
| `.tmp/189_scifi_ch200_segment_audit.json` | Ch200 segment audit；review 修复后按 `up_to=200` 截断 health / setting 状态 |
| `.tmp/189_scifi_ch200_metrics.md` | 只读 T9 复算报告 |

---

## Ch200 checkpoint baseline

| up_to | accepted | gap | budget_peak | before_emergency_peak | emergency_count | CED/1k | CED issues | words | overdue | health | halt |
|-------|----------|-----|-------------|-----------------------|-----------------|--------|------------|-------|---------|--------|------|
| 125 | 125 | 0 | 0.9888 | 1.2671 | 32 | 0.3896 | 193 | 495425 | 184 | 9.5 | null |
| 150 | 150 | 0 | 0.9888 | 1.2671 | 32 | 0.3844 | 228 | 593168 | 248 | 9.6 | null |
| 175 | 175 | 0 | 0.9888 | 1.2671 | 32 | 0.3846 | 266 | 691659 | 304 | 9.7 | null |
| 200 | 200 | 0 | 0.9888 | 1.2671 | 32 | 0.3803 | 300 | 788864 | 352 | 9.8 | null |

CED 口径：consistency-only、merged/source、正文证据；不含 literary craft、优秀度、同质化、AI 腔或 `rule-mr-*` 聚合。

---

## 验证命令与结果

### 原始 metrics 采集

```powershell
python scripts/five_gate_check.py --genre scifi --db .tmp/task171_ch1_ch200.db --project-id 835afdf11a294b5eac74a5d8998bd9a2 --up-to 125 --format json
python scripts/five_gate_check.py --genre scifi --db .tmp/task171_ch1_ch200.db --project-id 835afdf11a294b5eac74a5d8998bd9a2 --up-to 150 --format json
python scripts/five_gate_check.py --genre scifi --db .tmp/task171_ch1_ch200.db --project-id 835afdf11a294b5eac74a5d8998bd9a2 --up-to 175 --format json
python scripts/five_gate_check.py --genre scifi --db .tmp/task171_ch1_ch200.db --project-id 835afdf11a294b5eac74a5d8998bd9a2 --up-to 200 --format json
```

结果：四档均输出有效 metrics；因默认 baseline 是包内 `scifi_ch100_baseline.json`，Ch125+ 判定使用 Ch100 末点而 FAIL。该 FAIL 不作为验收失败，只用于确认必须显式传入 Ch200 baseline。

### 显式 Ch200 baseline 回放

```powershell
python scripts/five_gate_check.py --genre scifi --db .tmp/task171_ch1_ch200.db --project-id 835afdf11a294b5eac74a5d8998bd9a2 --up-to 125 --baseline archive/v10/artifacts/189-scifi-ch200-baseline.json --format json
python scripts/five_gate_check.py --genre scifi --db .tmp/task171_ch1_ch200.db --project-id 835afdf11a294b5eac74a5d8998bd9a2 --up-to 150 --baseline archive/v10/artifacts/189-scifi-ch200-baseline.json --format json
python scripts/five_gate_check.py --genre scifi --db .tmp/task171_ch1_ch200.db --project-id 835afdf11a294b5eac74a5d8998bd9a2 --up-to 175 --baseline archive/v10/artifacts/189-scifi-ch200-baseline.json --format json
python scripts/five_gate_check.py --genre scifi --db .tmp/task171_ch1_ch200.db --project-id 835afdf11a294b5eac74a5d8998bd9a2 --up-to 200 --baseline archive/v10/artifacts/189-scifi-ch200-baseline.json --format json
```

结果：Ch125 / Ch150 / Ch175 / Ch200 全部 PASS。

### segment audit

```powershell
python scripts/segment_audit.py --db .tmp/task171_ch1_ch200.db --project-id 835afdf11a294b5eac74a5d8998bd9a2 --up-to 200 --format json
```

结果：`critical_orphans=0`，`total_orphans=0`，`halt_would_fire=false`，`next_audit_chapter=201`。

review 修复说明：初版 `segment_audit` 在含 Ch201-Ch220 的 DB 上会把 Ch200 之后的 `continuity_reports` 与 `setting_tracking` 当前态混入 Ch200 报告。已修复为按 `up_to` 截断 health trajectory，并排除 `last_mentioned_chapter > up_to` 的未来状态；修复后重新生成 `.tmp/189_scifi_ch200_segment_audit.json`。

### T9 复算

完整 `songyan metrics --chapters 1-200` 在本轮运行数分钟无输出，按防卡纪律中止。为保持 Task 189 只读边界，改用同一 `songyan.evals.text_cleanliness` 检测器对 accepted head 执行 `persist=False` 复算：

```powershell
python -c "from songyan.evals.text_cleanliness import collect_text_cleanliness_metrics, render_text_cleanliness_section; ..."
```

结果：`rows=200`，元标记/artifact=0，重复长段落=0，时间线矛盾=0。报告落盘 `.tmp/189_scifi_ch200_metrics.md`。

完整 `songyan metrics` Ch200 历史库复算路径未作为 Task 189 完成证据；该慢路径应在 Task 191 harness/metrics 准备或后缀修复中处理，不阻塞本任务的 Ch200 baseline 与 T9-only 冻结结论。

---

## 后续使用要求

1. Task 192/193/194 以及任何 Ch125+ five-gate 命令不得依赖默认 baseline。
2. canonical baseline 路径：

```powershell
--baseline archive/v10/artifacts/189-scifi-ch200-baseline.json
```

3. 如需 `.tmp` 工作副本，可从 canonical baseline 显式复制，不得反向依赖 `.tmp`：

```powershell
Copy-Item archive/v10/artifacts/189-scifi-ch200-baseline.json .tmp/189_scifi_ch200_baseline.json
```

4. `src/songyan/evals/baselines/scifi_ch100_baseline.json` 保持不变，本任务不改变工具默认行为。

---

## 结论

Task 189 已完成。V10 Ch200 checkpoint 对照表已冻结，sci-fi Ch200 baseline 已有临时证据与受版本管理副本。后续应进入 Task 190：盘点 xuanhuan / wuxia / urban 的 clean Ch100 终点事实源；在 Task 190/191 完成前仍不得启动非 sci-fi Ch200 长跑。
