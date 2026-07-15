# Task 172b: xuanhuan Ch100 爬坡验证报告

- 生成时间: 2026-07-15T13:32:03.029262
- 项目: `1e7ce6279b224e7f8e476f6f4e963417`  体裁: `xuanhuan`  目标: Ch100
- Gate: enforce / isolate / resume  Halt: None

## 分段指标（harness 原始观测）

> `CED/1k` 为 harness 旧口径 raw evidence issue 观测值，包含文学 craft issue 与 `rule-mr-*` mandatory-reference 聚合工作项，保留用于趋势追溯；V 维度终判使用下方 `vdim_compare.py` 的 consistency-only 口径。

| up_to | accepted | budget_peak | before_emerg_peak | emerg | overdue | health | CED/1k |
|---:|---:|---:|---:|---:|---:|---:|---:|
| 25 | 25 | 0.9811 | 0.0 | 0 | 0 | 8.8 | 41.5379 |
| 50 | 50 | 0.9811 | 0.0 | 0 | 2 | 9.3 | 20.5428 |
| 75 | 75 | 0.9811 | 0.0 | 0 | 85 | 9.6 | 13.744 |
| 100 | 100 | 0.9811 | 0.0 | 0 | 166 | 9.1 | 10.7489 |

## V 维度终判（2026-07-15）

终判命令：

```powershell
python .tmp/vdim_compare.py 100
```

| gate | xuanhuan Ch100 | sci-fi Ch100 | verdict |
|---|---:|---:|:---:|
| budget_peak | 0.981 | 0.989 | PASS |
| consistency CED/1k | 0.4434（154 issues / 347,290 words） | 0.3976（157 issues / 394,839 words） | PASS（≤ ×1.15 ceiling 0.4573） |
| overdue foreshadowing | 166 | 168 | PASS |
| health | 9.1 | ≥8.0 | PASS |
| completeness | 100/100 accepted | 100/100 | PASS |

CED 终判口径：

- 只计 `critical/major` 且有 evidence 的 consistency 类 issue；
- 每个 accepted head 使用其 review source version，优先 `merged` report，避免 `llm` + `merged` 双计数；
- 排除 `rule-mr-*` mandatory-reference 聚合工作项，因为其 `evidence_quote` 是缺失 setting key 列表，不是正文证据句；真正带正文引用的 `world_consistency` 仍计入。

## 结论

Ch1-Ch100 全 accepted、无 halt；budget / consistency CED / overdue / health / completeness 五门全 PASS。172b 达成 V8 的 V 维度验收条件。
