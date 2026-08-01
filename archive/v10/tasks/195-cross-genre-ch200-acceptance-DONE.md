# Task 195 DONE: 跨体裁 Ch200 总验收

> **阶段**: V10.2 跨体裁 Ch200 爬坡收口
> **任务书**: `tasks/195-cross-genre-ch200-acceptance.md`
> **状态**: ✅ 完成
> **完成时间**: 2026-08-01

---

## 结论

V10.2 跨体裁 Ch200 总验收通过。Task 189 sci-fi Ch200 baseline 已作为冻结标尺；xuanhuan / wuxia / urban 三个非 sci-fi 体裁均完成 Ch1-Ch200 accepted，run completed，failed=[]，Ch200 five-gate PASS，segment audit PASS，T9 hard hits=0。

本任务没有改动生成链路、DB、五门、CED、segment audit 或 T9 口径。Task 196 优秀度样本集与校准协议已完成，但不进入本轮 Ch200 hard gate；结构升级 spike 仍留给 Task 204-206。

---

## 冻结标尺

| 项 | sci-fi baseline |
|----|-----------------|
| baseline | `archive/v10/artifacts/189-scifi-ch200-baseline.json` |
| source DB | `.tmp/task171_ch1_ch200.db` |
| project_id | `835afdf11a294b5eac74a5d8998bd9a2` |
| run_id | `run-fb39245c` |
| Ch200 accepted | 200/200 |
| budget_peak | 0.9888 |
| CED/1k | 0.3803 |
| overdue | 352 |
| health | 9.8 |
| T9 | hard clean |

CED 口径继续使用 consistency-only、merged/source、正文证据；不含文学 craft、同质化、AI 腔或 `rule-mr-*` 聚合项。

---

## 三体裁终点复核

| 体裁 | DB | project_id | run_id | Ch200 head | run / failed | cost | five-gate @200 | segment @200 | T9 |
|------|----|------------|--------|------------|--------------|------|----------------|--------------|----|
| xuanhuan | `.tmp/task_v10_xuanhuan_ch200.db` | `d160a55a51de4a2bb82440ebc03ec23a` | `run-v10-xuanhuan-3b4ba8e4` | `v-5659d486` | completed / `[]` | 18.373852 | PASS | PASS：critical=0、total=50、halt=false | hard=0、timeline=0 |
| wuxia | `.tmp/task_v10_wuxia_ch200.db` | `273a8408be8e4caf8cbc1e91954da600` | `run-v10-wuxia-5bbfab3a` | `v-1ecab81e` | completed / `[]` | 17.187324 | PASS | PASS：critical=0、total=52、halt=false | hard=0、timeline=0 |
| urban | `.tmp/task_v10_urban_ch200.db` | `81e345042b124ee2a73094b82e4be555` | `run-v10-urban-743a979a` | `clean-200-t9-194k` | completed / `[]` | 14.91622 | PASS | PASS：critical=0、total=76、halt=false | hard=0、timeline=3 report-only |

T9 hard hits 指 meta/artifact 与重复长段落硬门。urban timeline=3 为 text cleanliness 的 report-only 项，Task 194.k 已将 Ch200 slash artifact deterministic clean 到 `clean-200-t9-194k`，因此不构成 T9 hard gate failure。

---

## Five-Gate 明细

所有命令均显式传入 `--baseline archive/v10/artifacts/189-scifi-ch200-baseline.json`。

| 体裁 | accepted / gap | budget | CED/1k | overdue | health | verdict |
|------|----------------|--------|--------|---------|--------|---------|
| xuanhuan | 200 / 0 | 0.8632 | 0.0416 | 14 | 8.1 @Ch200 | PASS |
| wuxia | 200 / 0 | 0.9646 | 0.1346 | 169 | 9.0 @Ch200 | PASS |
| urban | 200 / 0 | 0.9595 | 0.0660 | 153 | 8.2 @Ch200 | PASS |

Ch200 CED threshold = sci-fi 0.3803 × 1.15 = 0.4373；三体裁均低于阈值。overdue 阈值 = sci-fi Ch200 baseline 352；三体裁均低于阈值。budget 均 < 1.0，且 `halt=null`。

---

## 本轮复核命令

### Status

```powershell
python scripts/run_v10_ch200_climb.py --status --genre xuanhuan --format json
python scripts/run_v10_ch200_climb.py --status --genre wuxia --format json
python scripts/run_v10_ch200_climb.py --status --genre urban --format json
```

结果：三体裁 target DB 与 project file 均存在，accepted count=200，run status=`completed`，current_chapter=200。

### Five-Gate

```powershell
python scripts/five_gate_check.py --genre xuanhuan --db .tmp/task_v10_xuanhuan_ch200.db --project-id d160a55a51de4a2bb82440ebc03ec23a --up-to 200 --baseline archive/v10/artifacts/189-scifi-ch200-baseline.json --format json
python scripts/five_gate_check.py --genre wuxia --db .tmp/task_v10_wuxia_ch200.db --project-id 273a8408be8e4caf8cbc1e91954da600 --up-to 200 --baseline archive/v10/artifacts/189-scifi-ch200-baseline.json --format json
python scripts/five_gate_check.py --genre urban --db .tmp/task_v10_urban_ch200.db --project-id 81e345042b124ee2a73094b82e4be555 --up-to 200 --baseline archive/v10/artifacts/189-scifi-ch200-baseline.json --format json
```

结果：三体裁均 PASS，且 `health_report_chapter=200`，不存在 192.aw 型 stale health。

### Segment Audit

```powershell
python scripts/segment_audit.py --db .tmp/task_v10_xuanhuan_ch200.db --project-id d160a55a51de4a2bb82440ebc03ec23a --up-to 200 --genre xuanhuan --format json
python scripts/segment_audit.py --db .tmp/task_v10_wuxia_ch200.db --project-id 273a8408be8e4caf8cbc1e91954da600 --up-to 200 --genre wuxia --format json
python scripts/segment_audit.py --db .tmp/task_v10_urban_ch200.db --project-id 81e345042b124ee2a73094b82e4be555 --up-to 200 --genre urban --format json
```

结果：三体裁 `critical_orphans=0`，`halt_would_fire=false`。

### T9 / failed=[]

使用 accepted head 正文和现有检测器直接复算 meta/artifact、重复长段落与 timeline report-only 项，并查询 `project_runs.completed_chapters` / `failed_chapters`。结果：三体裁 completed=1..200、failed=[]；xuanhuan/wuxia hard=0、timeline=0；urban hard=0、timeline=3 report-only。

---

## 复核说明

曾尝试直接运行 Task 191 harness `--audit --up-to 200`；该路径会串行调用 `songyan metrics --chapters 1-200`，在本轮超过两分钟未返回，已中止。该慢路径与 Task 189 / Task 207 登记的 metrics Ch200 历史库慢路径一致，不作为 hard gate 失败。为避免把报告慢路径误判为质量失败，本任务改用同源的 five-gate、segment audit 和 T9 检测器拆分复核。

---

## 已知限制

- urban Ch199/Ch200 曾因 flash 多次空响应，使用 fallback model `deepseek/deepseek-chat` 完成；该样本可作为 urban Ch200 PASS 终点，但不得记为 flash clean sample。
- 本任务只完成 V10.2 长窗口稳定性验收；优秀度信号包仍按 Task 197-203 继续。
- KG diff / FactTrack validity interval / Storyline Tree 仍是 Task 204-206 spike，不阻塞 Task 195。

---

## 入口文档同步

- `docs/STATUS.md`
- `tasks/V10-README.md`
- `docs/INDEX.md`
- `README.md`
- `AGENTS.md`

---

## 后续路由

V10.2 已完成。下一步进入 V10.3：

1. Task 197：跨章同质化 / 多样性 / 叙事张力指数。
2. Task 198：中文 AI 腔规则包。
3. Task 199-203：style card、角色声纹、judge 偏差、perplexity / 可读性 spike 与优秀度报告整合。

V10.4 结构升级 spike 与 Task 207 收口归档继续按 `tasks/V10-README.md` 执行。
