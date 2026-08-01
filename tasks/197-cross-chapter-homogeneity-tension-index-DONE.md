# Task 197 DONE: 跨章同质化 / 多样性 / 叙事张力指数

> **任务书**: `tasks/197-cross-chapter-homogeneity-tension-index.md`
> **状态**: ✅ 完成
> **完成时间**: 2026-08-01

---

## 结论

Task 197 已完成第一批离线结构型优秀度信号。信号覆盖场景功能同质化、桥段节奏重复、张力曲线平直与意象/冲突词复用密度，输出到 Task 197/198 共享 JSON 与 Markdown 报告。

本任务不改变生成链路，不进入任何 gate，不修改 CED / five-gate / segment audit / T9。

---

## 产物

| 产物 | 路径 |
|------|------|
| 共享模块 | `src/songyan/evals/excellence_signals.py` |
| 离线脚本 | `scripts/run_197_198_excellence_signals.py` |
| JSON 报告 | `tasks/197-198-excellence-signals-report.json` |
| Markdown 报告 | `docs/reports/197-198-excellence-signals-report.md` |
| 测试 | `tests/evals/test_197_198_excellence_signals.py` |

---

## 信号结果

Task 197 在 60 章样本中的命中：

| signal | count |
|--------|------:|
| `beat_rhythm_repetition` | 40 |
| `scene_function_homogeneity` | 26 |
| `tension_flatline` | 21 |
| `motif_reuse_density` | 12 |

总计 54/60 章有 Task 197 候选命中，hit 总数 99。

---

## 校准结果

校准真值：Task 196 anchor + spotcheck 共 24 章 agent-deep-read 标注；truth rule 为 `homogeneity<=2 or tension<=2 or overall<=2`。

| evaluated | truth+ | detected+ | TP | FP | FN | precision | recall |
|-----------|--------|-----------|----|----|----|-----------|--------|
| 24 | 10 | 20 | 8 | 12 | 2 | 0.40 | 0.80 |

解读：

- recall=0.80，说明结构型信号能覆盖多数人工低分样本。
- precision=0.40，说明误报仍多，尤其稳定体裁桥段会被 `beat_rhythm_repetition` / `scene_function_homogeneity` 捕捉。
- 因此 Task 197 只能作为 report-only 风险定位，不能作为 gate 或自动修订依据。

---

## 已知误报 / 漏报

| 类型 | 样例 | 说明 |
|------|------|------|
| false positive | scifi Ch1、xuanhuan Ch1 | 强章也可能有稳定场景功能与低张力开场；不等于缺陷 |
| false positive | scifi Ch104 | revelation beat 重复但整体质量高 |
| false negative | scifi Ch39、xuanhuan Ch105 | 人工低分主要来自 AI 腔 / 补丁感，结构型信号不一定捕捉 |

---

## 验证

```powershell
python scripts/run_197_198_excellence_signals.py
python -m pytest tests/evals/test_196_excellence_sampling.py tests/evals/test_197_198_excellence_signals.py tests/utils/test_ai_tells.py -q
python -m pytest tests/ -q
ruff check src/songyan/evals/excellence_signals.py src/songyan/evals/excellence_sampling.py scripts/run_197_198_excellence_signals.py scripts/run_196_rule_pilot.py tests/evals/test_197_198_excellence_signals.py tests/evals/test_196_excellence_sampling.py tests/utils/test_ai_tells.py
ruff check src/ tests/ scripts/run_v10_ch200_climb.py scripts/run_197_198_excellence_signals.py
powershell -File scripts/run_with_timeout.ps1 -TimeoutSec 7200 -- python scripts/run_172a7_genre_validation.py --templates scifi --end 10 --output .tmp/197198_scifi_end10_regression.json
```

结果：

- 聚焦测试：46 passed。
- 全量 pytest：3063 passed, 2 skipped, 1 xfailed。
- ruff：All checks passed。
- scifi end10 回归：10/10 completed，failed=[]，T9=0，overdue=0，budget peak=0.8903，wrapper PASS_NORMAL_EXIT；输出 `.tmp/197198_scifi_end10_regression.json`。

---

## 后续

Task 203 可消费 `tasks/197-198-excellence-signals-report.json`，但展示层必须保留 report-only 与低精度说明。
