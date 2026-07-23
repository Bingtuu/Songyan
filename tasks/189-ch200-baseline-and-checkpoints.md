# Task 189: Ch200 baseline 与 checkpoint 冻结

> **阶段**: V10.1 Ch200 口径与工具
> **类型**: 只读重放 / baseline 冻结 / 工具口径校验
> **优先级**: P0（所有非 sci-fi Ch200 终判的标尺）
> **状态**: ◻ 规划中
> **来源**: `tasks/V10-README.md` Task 189

---

## 任务边界

本任务只冻结 Ch200 对标口径，不启动任何非 sci-fi Ch200 爬坡，不修改五门判定函数，不引入优秀度信号。

目标是把 sci-fi Ch200 的历史事实源用 V9 正式工具重放，形成 V10 后续所有体裁 Ch200 使用的 checkpoint baseline。

---

## 背景

V7 已取得 sci-fi/space_opera + webnovel_intense Ch200 证据：200/200 accepted，D1 hard clean pass；171w 后 Ch201-Ch220 20/20 accepted。V8/V9 则把多体裁验证推进到 Ch100，并正式收编了 `scripts/five_gate_check.py`、`scripts/segment_audit.py` 与包内 sci-fi baseline。

V10 要把 xuanhuan/wuxia/urban 从 Ch100 推到 Ch200。进入实跑前，必须先明确 sci-fi Ch125 / Ch150 / Ch175 / Ch200 的五门对照值，否则后续 Ch200 PASS/FAIL 没有稳定标尺。

---

## 输入与事实源

| 类别 | 路径 / 说明 |
|------|-------------|
| V7 Ch200 报告 | `archive/v7/reports/task-171-ch200-long-run-report.md` |
| V7 Ch200 分析 | `archive/v7/reports/task-171-ch200-analysis-and-next-step-report.md` |
| V7 Ch200 任务 | `archive/v7/tasks/171-ch200-long-run.md` |
| V7 D1 清洁 | `archive/v7/tasks/171t-ch200-d1-hard-clean.md`、`archive/v7/tasks/171u-ch200-d1-clean-application-and-report-refresh.md` |
| V9 五门工具 | `scripts/five_gate_check.py` |
| V9 段审计工具 | `scripts/segment_audit.py` |
| 当前 sci-fi baseline 包资源 | `src/songyan/evals/baselines/` |

本任务开工第一步必须定位可重放的 sci-fi Ch200 DB / project_id / run_id。若历史 DB 不在工作区，需先登记缺口，给出“从报告抽取临时 baseline”与“重建/恢复 DB”的取舍建议，不能伪造重放结论。

---

## 工作内容

### A. 事实源定位

1. 定位 V7 sci-fi Ch200 终判 DB、project_id、run_id。
2. 确认 accepted head 是否已包含 171t/171u D1 清洁应用后的版本。
3. 记录 DB 路径、project_id、run_id、章节范围、是否可只读重放。
4. 若 DB 缺失，输出缺口报告，不继续写入 baseline。

### B. baseline 生成与工具重放

先从 sci-fi Ch200 DB 生成 V10 专用 baseline 文件：

```powershell
python scripts/five_gate_check.py --genre scifi --db <scifi_ch200.db> --project-id <project_id> --up-to 125 --format json > .tmp/189_scifi_ch200_at125.json
python scripts/five_gate_check.py --genre scifi --db <scifi_ch200.db> --project-id <project_id> --up-to 150 --format json > .tmp/189_scifi_ch200_at150.json
python scripts/five_gate_check.py --genre scifi --db <scifi_ch200.db> --project-id <project_id> --up-to 175 --format json > .tmp/189_scifi_ch200_at175.json
python scripts/five_gate_check.py --genre scifi --db <scifi_ch200.db> --project-id <project_id> --up-to 200 --format json > .tmp/189_scifi_ch200_at200.json
```

注意：上述命令只用于采集 sci-fi 自身指标。当前 `five_gate_check.py` 默认 baseline 是包内 `scifi_ch100_baseline.json`，对 Ch125+ 会回退到最后一个 Ch100 点。因此，执行者必须从这些输出中提取 metrics，生成 `.tmp/189_scifi_ch200_baseline.json`，供后续非 sci-fi Ch200 显式传入。不得把默认 baseline 输出误当作 Ch200 对照值。

生成 `.tmp/189_scifi_ch200_baseline.json` 后，再用正式工具验证 baseline 文件可被读取：

```powershell
python scripts/five_gate_check.py --genre scifi --db <scifi_ch200.db> --project-id <project_id> --up-to 125 --baseline .tmp/189_scifi_ch200_baseline.json --format json
python scripts/five_gate_check.py --genre scifi --db <scifi_ch200.db> --project-id <project_id> --up-to 150 --baseline .tmp/189_scifi_ch200_baseline.json --format json
python scripts/five_gate_check.py --genre scifi --db <scifi_ch200.db> --project-id <project_id> --up-to 175 --baseline .tmp/189_scifi_ch200_baseline.json --format json
python scripts/five_gate_check.py --genre scifi --db <scifi_ch200.db> --project-id <project_id> --up-to 200 --baseline .tmp/189_scifi_ch200_baseline.json --format json

python scripts/segment_audit.py --db <scifi_ch200.db> --project-id <project_id> --up-to 200 --format json
```

metrics/T9 也必须复算：

```powershell
$env:DATABASE_URL = "sqlite:///<scifi_ch200.db>"
songyan metrics --project-id <project_id> --chapters 1-200 -o .tmp/189_scifi_ch200_metrics.md
Remove-Item Env:\DATABASE_URL
```

### C. baseline 产物

至少落盘：

| 文件 | 内容 |
|------|------|
| `.tmp/189_scifi_ch200_baseline.json` | Ch125/150/175/200 的 accepted、budget、CED、overdue、health、gap、halt |
| `.tmp/189_scifi_ch200_at125.json` ... `.tmp/189_scifi_ch200_at200.json` | 从 sci-fi DB 采集的原始 checkpoint 指标 |
| `.tmp/189_scifi_ch200_segment_audit.json` | Ch200 段审计结果 |
| `.tmp/189_scifi_ch200_metrics.md` | T9 / metrics 报告 |
| `tasks/189-ch200-baseline-and-checkpoints-DONE.md` | 结论、命令、路径、对照表、是否入包建议 |

是否把 baseline 纳入 `src/songyan/evals/baselines/` 由执行结果决定；若只是报告级引用，可先留在归档报告，不强行入包。

---

## 验收判据

1. 明确记录 sci-fi Ch200 DB / project_id / run_id，或明确登记 DB 缺失并停止 baseline 冻结。
2. Ch125 / Ch150 / Ch175 / Ch200 四个 checkpoint 均有正式工具输出，并已生成 `.tmp/189_scifi_ch200_baseline.json`。
3. Ch200 T9 复算为 hard clean：meta/artifact=0、duplicate=0、timeline=0，或明确说明与 V7 D1 报告的差异。
4. `segment_audit.py --up-to 200` 输出 critical_orphans 与 halt_would_fire。
5. 形成 V10 使用的 sci-fi Ch200 对照表，字段至少包括：budget peak、CED、overdue、health、accepted、gap、halt、T9。
6. 后续所有非 sci-fi Ch200 five-gate 命令必须显式传入 `--baseline .tmp/189_scifi_ch200_baseline.json`；文档中不得使用默认 Ch100 baseline 跑 Ch125+。
7. 不改五门判定函数；若发现工具不支持 Ch200，应转入 Task 191 或后缀任务处理。
8. 产出 DONE 文档，并更新 `tasks/V10-README.md` 的 Task 189 状态。

---

## 不做

- 不启动 xuanhuan/wuxia/urban Ch200。
- 不调体裁 profile。
- 不改 CED / T9 / five-gate 口径。
- 不引入优秀度信号。
- 不用诊断 DB 或未清洁版本作为终判 baseline。

---

## 风险与路由

| 风险 | 路由 |
|------|------|
| V7 Ch200 DB 缺失 | 先出缺口报告；必要时立恢复/重建子任务，不得伪造重放 |
| V7 报告数值与 V9 工具重放不一致 | 以当前正式工具为准，但必须解释漂移来源 |
| 误用包内 Ch100 baseline 跑 Ch125+ | 立即作废该输出；重新生成并显式传入 `.tmp/189_scifi_ch200_baseline.json` |
| T9 复算非 0 | 先确认是否使用 D1 clean accepted head；不得解释性豁免 |
| segment audit 不支持 Ch200 | 转 Task 191 修工具 I/O，不改判定口径 |

---

## 后续依赖

Task 189 完成后，Task 192/193/194 的 Ch200 五门对照表才能冻结。Task 191 若需要引用 sci-fi baseline 文件，也必须以本任务输出为准。
