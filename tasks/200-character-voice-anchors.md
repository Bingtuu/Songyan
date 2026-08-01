# Task 200: 角色声纹锚点

> **阶段**: V10.3 优秀度信号包
> **类型**: 离线 report-only 角色对白观察 / 声纹锚点
> **状态**: ✅ 已完成；DONE: `tasks/200-character-voice-anchors-DONE.md`
> **日期**: 2026-08-01

---

## 任务边界

本任务只从 accepted 正文中抽取角色对白并生成声纹观察报告。它不是运行时 `DialogueStyleCard`，不写回角色档案，不注入 Writer / CreativeDirector prompt，不进入自动 gate，不修改 CED / five-gate / segment audit / T9 口径。

说话人归因必须可解释；无法归因的对白进入 `unknown_attribution`，不得伪造角色声纹。

---

## 输入

| 输入 | 路径 |
|------|------|
| Task 196 样本清单 | `tasks/196-excellence-sample-set.json` |
| Task 196 标注记录 | `tasks/196-excellence-annotations.json` |
| Task 197/198 信号报告 | `tasks/197-198-excellence-signals-report.json` |
| Task 199 style card 报告 | `tasks/199-style-card-report.json` |

---

## 最小 schema

每个角色声纹锚点包含：

1. `character_id / character_name`
2. `evidence_chapters`
3. `sample_lines`
4. `sentence_length_profile`
5. `lexical_markers`
6. `emotional_register`
7. `interaction_pattern`
8. `distinctiveness_score`
9. `drift_or_homogeneity_hits`
10. `limitations`

报告还必须包含 unknown 归因统计。

---

## 输出

| 输出 | 路径 |
|------|------|
| 离线模块 | `src/songyan/evals/voice_anchor_extraction.py` |
| 离线脚本 | `scripts/run_200_voice_anchor_extraction.py` |
| JSON 报告 | `tasks/200-character-voice-anchor-report.json` |
| Markdown 报告 | `docs/reports/200-character-voice-anchor-report.md` |
| 测试 | `tests/evals/test_200_voice_anchor_extraction.py` |

---

## 验收标准

- [x] 任务书与 DONE 文档落盘。
- [x] 角色声纹 JSON + Markdown 报告落盘。
- [x] 每个角色声纹有证据行、适用边界和 unknown 归因说明。
- [x] 明确 report-only，不注入 prompt，不写回角色档案，不污染 hard gate。
- [x] 测试、ruff、git diff --check 通过。

---

## 失败路由

| 条件 | 路由 |
|------|------|
| 说话人归因不足 | 保留 unknown_attribution，记录局限，不伪造角色 |
| 必须写回角色档案 / DialogueStyleCard | 停止并拆后续任务 |
| 弱样本无法由声纹报告解释 | 写负结论，不编造有效性 |
