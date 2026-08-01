# Task 198: 中文 AI 腔规则包

> **阶段**: V10.3 优秀度信号包
> **类型**: 离线 report-only 规则信号
> **状态**: ✅ 已完成；DONE: `tasks/198-chinese-ai-tone-rule-pack-DONE.md`
> **日期**: 2026-08-01

---

## 任务边界

本任务只扩充中文 AI 腔 / 生成事故类离线检测规则，不进入 Writer / CreativeDirector prompt，不进入自动 accept/reject gate，不修改 CED / five-gate / segment audit / T9 口径。

Task 196 已证明旧 `ai_tells + fatigue_words` 规则集对优秀度校准无效；本任务按 Task 196 §4.3 的缺陷主类补充规则，但仍只作为 report-only 观察信号。

---

## 输入

| 输入 | 路径 |
|------|------|
| 样本清单 | `archive/v10/artifacts/196-excellence-sample-set.json` |
| 标注记录 | `archive/v10/artifacts/196-excellence-annotations.json` |
| 校准报告 | `tasks/196-excellence-calibration-report.md` |

---

## 规则包范围

Task 198 最小规则包：

1. `verbatim_sentence_repeat` / `verbatim_paragraph_repeat`：章内逐字复读。
2. `cross_chapter_verbatim_repeat`：同体裁样本跨章逐字复用句子。
3. `chapter_self_reference`：正文中出现“第 N 章”式章节号自指。
4. `engineering_residue`：Markdown heading、占位符、保护指令、舞台指示、ASCII 工程残留。
5. `setting_patch_segment`：解释性连接词与设定词密度过高的说明文补丁段。
6. `template_rhetoric_density` / `not_but_template`：模板修辞和说明文腔密度偏高。
7. `legacy_ai_tell`：旧规则命中保留为低权重观察项，仅当同章至少两处命中才记录。

---

## 输出

| 输出 | 路径 |
|------|------|
| 共享模块 | `src/songyan/evals/excellence_signals.py` |
| 离线脚本 | `scripts/run_197_198_excellence_signals.py` |
| 结构化报告 | `archive/v10/artifacts/197-198-excellence-signals-report.json` |
| Markdown 报告 | `archive/v10/reports/197-198-excellence-signals-report.md` |
| 聚焦测试 | `tests/evals/test_197_198_excellence_signals.py` |

---

## 验收标准

- [x] 每类规则均输出章节、位置、证据片段与 signal_id。
- [x] 规则结果可与 Task 196 agent-deep-read 真值对照。
- [x] prelabel 不作为真值。
- [x] 旧规则试点负结论保留，不伪装为有效指标。
- [x] 报告显式标注 report-only，不污染 CED / hard gate。
- [x] 聚焦测试和 ruff 通过。

---

## 校准结论

Task 198 在 24 章 agent-deep-read 真值上的结果：

| evaluated | truth+ | detected+ | TP | FP | FN | precision | recall |
|-----------|--------|-----------|----|----|----|-----------|--------|
| 24 | 15 | 23 | 15 | 8 | 0 | 0.65 | 1.00 |

结论：Task 198 第一批规则包相对旧规则显著改善召回，能覆盖 Task 196 人工深读标注中的 AI 腔 / 生成事故低分样本；但模板修辞类信号仍偏宽，不能进入 gate。

---

## 失败路由

若后续希望将任何规则转入 prompt 或 gate，必须另立任务，扩大样本校准，完成 scifi 短窗口回归；影响 Ch200 口径时还必须重放 Task 189 baseline。

---

## 后续

Task 203 可整合本任务 JSON；Task 201 judge 偏差对策应复用本任务命中的生成事故类信号作为 judge v2 强制检查项。
