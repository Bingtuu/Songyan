# Task 170d: LiteraryAuditor 校准（量具可信化）

> **专项**: 文学提质专项（`archive/v7/tasks/170-literary-quality-remediation-README.md`）
> **类型**: 量具修复（先行、独立、低风险）
> **优先级**: P0（量具优先——提质复评依赖可信的文学诊断）
> **依赖**: 170b DONE（提供机器/人工偏差数据）
> **状态**: ◻ 规划中

---

## 问题（170b 实证）

LiteraryAuditor 的机器分与人工/LLM 实读**系统性背离**：

| 章 | 机器 character_autonomy | 人工/LLM voice | 偏差 |
|---|:---:|:---:|:---:|
| 全窗口 13 章 | 6.5–8.5（高分） | 1–2（塌陷） | 5/13 章达 ⚠️ 阈值 |

即：**对白全员同质冷静腔时，机器仍给角色维度高分**。这使机器诊断在角色维度上不可信，若不校准，后续提质复评会假通过。

## 认知修正（查证得到）

**根因是 `character_autonomy_score` 缺锚点评分标准**：

- 工艺卡 `prompts/cards/literary_auditor/1.0.1.yaml`（`_manifest.yaml` default `1.0.1`）**没有为四个分数单独定义 1–10 rubric**，输出格式里只给了示例值（`character_autonomy_score: 8.0` 之类），规则段仅说"评分范围 0-10"。
- 与角色维度相关的观察类型是 `character_tooling`（人物工具化）和 `polyphony_weakness`（声纹薄弱），但它们是**定性观察**，未与 `character_autonomy_score` 的分数锚定。
- 代码侧 `_parse_score`（`literary_auditor.py:130-135`）只做 0-10 clamp，不含标准。

所以模型倾向给中高分——没有"什么样算低分"的明确锚点。

## Goal

1. 给 `character_autonomy_score` 补**锚点 rubric**（明确 1–3 / 4–6 / 7–10 各档的判据），使"对白同质、角色无自主选择"能被打低分。
2. 评估是否新增 **voice / pacing 诊断能力**（决策项，见下）。
3. 用 170b 已有数据**回测**：校准前后同一批正文的分数变化，确认机器分向人工判断收敛。

## 关键决策：是否新增 voice/pacing 维度

有两条路，需在任务执行时依据回测数据决定：

| 方案 | 做法 | 代价 | 适用 |
|------|------|------|------|
| **A（轻，优先尝试）** | 只校准现有 `character_autonomy_score` rubric + 强化 `polyphony_weakness` 观察触发 | 只改工艺卡，不动模型/代码 | 若 voice 问题能被 character_autonomy 充分反映 |
| **B（重）** | 新增独立 voice / pacing 诊断维度 | 需三处同步改：`models/literary.py` 的 `Literal` + `literary_auditor.py` 的 `VALID_OBSERVATION_TYPES` + `1.0.1.yaml`；`LiteraryAuditResult` 加分数字段；DB `literary_observations` 表列 | 若 character_autonomy 无法承载 voice，pacing 完全无诊断 |

> 纪律：**先试 A，回测不足再上 B**。避免过度改模型和 schema。pacing 目前 LiteraryAuditor 无对应维度，若要机器侧量 pacing，倾向放到 170f 的 RuleAuditor 检测（连续独白/说明段落）而非 LiteraryAuditor——分工上 RuleAuditor 管可代码化的节奏信号，LiteraryAuditor 管语义。

## In Scope

- [ ] 在 `1.0.1.yaml`（或新版本 `1.0.2`）为 `character_autonomy_score` 增加分档 rubric，对齐 `character_tooling` / `polyphony_weakness`：
  - 低分（1–3）：对白无法区分身份、角色选择被情节牵着走、全员同质语气。
  - 中分（4–6）：部分角色有区分，但主要角色仍工具化。
  - 高分（7–10）：对白可辨身份、角色有自主选择与抵抗。
- [ ] 若走方案 B：三处枚举同步 + 模型字段 + schema 迁移 + 工艺卡维度说明。
- [ ] 回测脚本：对 170b 的 Ch28–Ch40 正文用校准后工艺卡重新跑 LiteraryAuditor，对比校准前后 `character_autonomy_score`，验证向人工 voice(1–2) 收敛。
- [ ] 单测：构造"对白同质"样本断言校准后 `character_autonomy_score` 落低档；"对白有区分"样本落高档。

## Out of Scope

- 不改 LiteraryAuditor "只诊断、不阻塞 accept" 的边界（AGENTS.md 硬规则）。
- 不把文学分接入 QualityGate（不改 accept 行为）。
- 不做 pacing 的 LiteraryAuditor 维度（倾向归 170f RuleAuditor）——除非回测证明必要。
- 不改生成侧（Writer/CreativeDirector）——那是 170e/170f。

## 与 170b rubric 的对齐

170b 的 5 维 LLM rubric（ai_tone/voice/concept/exposition/pacing）是**评估用的临时 rubric**。170d 校准的是**产品内 LiteraryAuditor**。两者需对齐：校准后 LiteraryAuditor 的 character_autonomy 应与 170b voice 维度同向。170g 复评时以校准后的产品量具为准，170b rubric 作为交叉参照。

## 验证要求

```powershell
python -m pytest tests/test_170d_auditor_calibration.py -q
ruff check src/ tests/
python -m pytest tests/ -q   # 全量回归（注意 test_dialogue_style_card 等相关测试）
# 回测（真实 LLM，隔离）：对 170b 正文重跑校准后 LiteraryAuditor
```

## 验收标准

- [ ] 回测显示：对白同质章的 `character_autonomy_score` 从 6.5–8.5 降到与人工 voice(1–2) 同向的低档。
- [ ] 校准方案（A 或 B）及依据写入 DONE。
- [ ] 单测覆盖同质/有区分两类样本。
- [ ] 全量测试 + ruff 通过。
- [ ] 产出 `tasks/170d-...-DONE.md`。
