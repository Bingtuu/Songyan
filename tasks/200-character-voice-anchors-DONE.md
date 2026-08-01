# Task 200 DONE: 角色声纹锚点

> **任务书**: `tasks/200-character-voice-anchors.md`
> **状态**: ✅ 完成
> **完成时间**: 2026-08-01

---

## 结论

Task 200 已完成离线 report-only 角色声纹锚点报告。系统从 Task 196 accepted 样本正文中抽取对白，优先使用源库 `characters` 表做说话人归因；无法安全归因的对白保留为 `unknown_attribution`，不伪造角色声纹。

本任务不是运行时 `DialogueStyleCard`，不写回角色档案，不注入 Writer / CreativeDirector prompt，不进入任何 gate，不修改 CED / five-gate / segment audit / T9。

---

## 产物

| 产物 | 路径 |
|------|------|
| 离线模块 | `src/songyan/evals/voice_anchor_extraction.py` |
| 薄 CLI | `scripts/run_200_voice_anchor_extraction.py` |
| JSON 报告 | `tasks/200-character-voice-anchor-report.json` |
| Markdown 报告 | `docs/reports/200-character-voice-anchor-report.md` |
| 测试 | `tests/evals/test_200_voice_anchor_extraction.py` |

---

## 报告摘要

| scope | anchors | unknown lines | weak explained |
|-------|--------:|--------------:|----------------|
| all | 17 | 1408 | 15/15 |
| genre:scifi | 10 | 752 | 8/8 |
| genre:xuanhuan | 7 | 656 | 7/7 |

unknown ratio 较高（all=0.599，scifi=0.547，xuanhuan=0.671），这是本任务的保守取舍：归因不足时保留 unknown，而不是把对白硬分配给角色。

---

## Schema

每个 `VoiceAnchorObservation` 包含：

| 字段 | 说明 |
|------|------|
| `character_id / character_name / role_type` | 源库角色身份或合成 unknown |
| `evidence_chapters` | 证据章节列表 |
| `sample_lines` | 角色对白证据行，含章节、文本、归因方法、位置 |
| `sentence_length_profile` | quote_count、sentence_count、平均句长、短/长句比例 |
| `lexical_markers` | 角色对白高频词 |
| `emotional_register` | 情绪 / 语气标记 |
| `interaction_pattern` | terse / measured / question-heavy / urgent-imperative / expository |
| `distinctiveness_score` | 与同 scope 其他角色的启发式差异度 |
| `drift_or_homogeneity_hits` | 声纹同质化风险观察 |
| `limitations` | report-only、非 DialogueStyleCard、启发式归因等边界 |

---

## Sanity check

校准真值仍只使用 Task 196 anchor + spotcheck 的 24 章 `agent-deep-read` 标注；prelabel 不作为真值。

| scope | weak samples | weak with voice evidence | weak unexplained |
|-------|-------------:|-------------------------:|------------------|
| all | 15 | 15 | - |
| genre:scifi | 8 | 8 | - |
| genre:xuanhuan | 7 | 7 | - |

解读：

- 弱样本均有可观察 voice evidence 或相邻 197/198 对话风格风险解释。
- 这只是方向性 sanity check，不支持阈值定标，也不能进入 hard gate。

---

## 边界自查

- 未改 `DialogueStyleCard` 模型或 CreativeDirector 生成逻辑。
- 未改 Writer / CreativeDirector prompt。
- 未写回 `characters` / `character_states` / SQLite。
- 未改 gate / CED / five-gate / segment audit / T9。
- 未新增核心 Agent / Workflow 节点。
- unknown 归因保留为报告项，不强行归属。

---

## 验证

```powershell
python scripts/run_200_voice_anchor_extraction.py
python -m pytest tests/evals/test_200_voice_anchor_extraction.py tests/evals/test_199_style_card_extraction.py tests/evals/test_197_198_excellence_signals.py tests/evals/test_196_excellence_sampling.py -q
ruff check src/songyan/evals/voice_anchor_extraction.py scripts/run_200_voice_anchor_extraction.py tests/evals/test_200_voice_anchor_extraction.py
python -m pytest tests/ -q
ruff check src/ tests/ scripts/run_197_198_excellence_signals.py scripts/run_199_style_card_extraction.py scripts/run_200_voice_anchor_extraction.py scripts/run_v10_ch200_climb.py
```

结果：

- Task 200 脚本：成功生成 JSON + Markdown 报告。
- 聚焦测试：27 passed。
- 全量 pytest：3063 passed, 2 skipped, 1 xfailed。
- ruff：All checks passed。

---

## 后续

Task 201 judge 偏差对策可使用本任务的 unknown 归因比例和角色声纹报告，修正 judge 对“谁说话都一个腔”的宽松偏差。Task 203 可消费 `tasks/200-character-voice-anchor-report.json`，但展示时必须保留 report-only 与“不是 DialogueStyleCard”的边界说明。
