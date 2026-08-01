# Task 198 DONE: 中文 AI 腔规则包

> **任务书**: `tasks/198-chinese-ai-tone-rule-pack.md`
> **状态**: ✅ 完成
> **完成时间**: 2026-08-01

---

## 结论

Task 198 已完成第一批中文 AI 腔 / 生成事故类离线规则包。规则包从旧 `ai_tells + fatigue_words` 的文风修辞词面，扩展到 Task 196 深读暴露的五类高价值缺陷：逐字复读、自指泄漏、工程残留、设定补丁段、模板修辞 / 说明文腔。

本任务只做 report-only 输出，不影响生成链路、CED、five-gate、segment audit 或 T9。

---

## 产物

| 产物 | 路径 |
|------|------|
| 共享模块 | `src/songyan/evals/excellence_signals.py` |
| 离线脚本 | `scripts/run_197_198_excellence_signals.py` |
| JSON 报告 | `archive/v10/artifacts/197-198-excellence-signals-report.json` |
| Markdown 报告 | `archive/v10/reports/197-198-excellence-signals-report.md` |
| 测试 | `tests/evals/test_197_198_excellence_signals.py` |

---

## 信号结果

Task 198 在 60 章样本中的命中：

| signal | count |
|--------|------:|
| `template_rhetoric_density` | 53 |
| `not_but_template` | 28 |
| `chapter_self_reference` | 13 |
| `engineering_residue` | 12 |
| `verbatim_sentence_repeat` | 5 |
| `legacy_ai_tell` | 2 |
| `cross_chapter_verbatim_repeat` | 2 |
| `setting_patch_segment` | 2 |

总计 57/60 章有 Task 198 候选命中，hit 总数 117。

---

## 校准结果

校准真值：Task 196 anchor + spotcheck 共 24 章 agent-deep-read 标注；truth rule 为 `ai_tone<=2 or overall<=2`。

| evaluated | truth+ | detected+ | TP | FP | FN | precision | recall |
|-----------|--------|-----------|----|----|----|-----------|--------|
| 24 | 15 | 23 | 15 | 8 | 0 | 0.65 | 1.00 |

解读：

- recall=1.00，说明第一批生成事故类规则覆盖了所有 agent 深读低分样本。
- precision=0.65，说明仍有误报，主要来自 `template_rhetoric_density` 与 `not_but_template` 对正常类型文体的宽泛捕捉。
- `chapter_self_reference`、`engineering_residue`、`verbatim_sentence_repeat` 证据更硬，适合作为 Task 203 报告中的高优先级定位项。

---

## 旧规则负结论保留

Task 196 已证明旧 `detect_ai_tells + detect_fatigue_words` 在 60 章样本上区分度为零甚至方向反转。本任务没有把旧规则伪装为有效校准基准；`legacy_ai_tell` 仅作为低权重观察项保留，并要求同章至少两处命中才记录。

---

## 已知误报 / 漏报

| 类型 | 样例 | 说明 |
|------|------|------|
| false positive | scifi Ch1、xuanhuan Ch1 | 强章也可能含“不是 / 像是”等类型常用连接词 |
| false positive | scifi Ch104 | 高质量揭示章也可能有模板连接词密度偏高 |
| false negative | 无 | 本批 agent-deep-read 低分样本均有至少一个 Task 198 命中 |

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

Task 201 judge 偏差对策应把本任务的生成事故类规则纳入 judge v2 强制检查项。Task 203 可消费 `archive/v10/artifacts/197-198-excellence-signals-report.json`，但必须展示 report-only 与误报边界。
