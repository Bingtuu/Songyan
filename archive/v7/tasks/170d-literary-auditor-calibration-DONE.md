# Task 170d: LiteraryAuditor 校准（量具可信化）— DONE

> **专项**: 文学提质专项（`archive/v7/tasks/170-literary-quality-remediation-README.md`）
> **类型**: 量具修复（先行、独立、低风险）
> **状态**: ✅ 完成（2026-07-06）
> **依赖**: 170b DONE（机器/人工偏差数据 + 隔离 DB + 人工 voice 终评分）

---

## 结论一句话

根因 = `character_autonomy_score` 等四个评分**缺锚点 rubric**，模型只能看到 JSON 示例值
（8.0 之类）当锚，系统性给中高分。补**分档锚点 rubric + 遮标签测试 + 高分需证据约束**后，
真实 LLM 回测显示 character_autonomy 均值 **7.69 → 2.46**，**13/13 章向人工 voice(1-2) 收敛**，
**12/13 章触发 polyphony_weakness** 观察。**方案 A（仅改工艺卡）已足够，无需上方案 B。**

## 根因诊断（查证得到）

- 工艺卡 `1.0.1.yaml` 规则 6 仅写"评分范围 0-10"，**四个分数都没有 1-10 分档判据**。
- 唯一的数值锚点是输出格式 JSON 里的示例值（`character_autonomy_score: 8.0`），模型据此锚定中高分。
- 代码侧 `literary_auditor.py::_parse_score` 只做 0-10 clamp，不含标准（正确，不该在代码里塞判据）。
- 相关观察类型 `character_tooling` / `polyphony_weakness` 是**定性观察**，此前**未与分数锚定**——
  即便模型察觉"复调弱化"，也没有规则要求它把 character_autonomy 打低。

所以模型对"对白全员同质冷静腔"仍给 6.5-8.5，与人工 voice(1-2) 系统性背离（170b 5/13 章 ⚠️）。

## 修复（方案 A：仅工艺卡，最小改动）

新建 `prompts/cards/literary_auditor/1.0.2.yaml`（复制 1.0.1 + 校准），
`_manifest.yaml` `default_version` 1.0.1 → 1.0.2。核心新增：

1. **四个评分的分档 rubric**（1-3 / 4-6 / 7-10 各档判据），重点校准 `character_autonomy_score`。
2. **"遮住说话人标签能否分辨谁在说话"测试**：认不出即落 1-3 档。
3. **单人独白/解谜为主、几乎无真实互动**的章也落 1-3 档（对齐 170b pacing/voice 观察）。
4. **规则 9（硬约束）**：character_autonomy 给 7 分以上必须有可辨身份的对白引文证据；
   检测到"对白同质/遮标签认不出"必须落 1-3 档并输出 `polyphony_weakness` 观察。
5. 输出格式示例值下调（8.0→3.0 等）并显式声明"示例仅示意字段类型，不是建议分"，消除示例锚定偏差。

> 为何不改代码/schema（不走方案 B）：回测证明 character_autonomy + polyphony_weakness 已能承载
> voice 塌陷信号，收敛充分。pacing 的机器量化归 170f 的 RuleAuditor（连续独白/说明段落检测），
> 不在 LiteraryAuditor 加维度——避免 `models/literary.py` Literal + `VALID_OBSERVATION_TYPES` +
> yaml + DB 列四处同步的重改动。遵守"先试 A，回测不足再上 B"纪律。

## 回测结果（真实 LLM，隔离 DB）

`scripts/backtest_170d_auditor_calibration.py`：读 1.0.1 落库分为"校准前"，
用 1.0.2 对 Ch28-Ch40 accepted 正文重跑为"校准后"，对照 170b 人工 voice 终评分。

| 指标 | 校准前(1.0.1) | 校准后(1.0.2) |
|------|:---:|:---:|
| character_autonomy 窗口均值 | **7.69** | **2.46** |
| 向人工 voice(×2) 收敛章数 | — | **13/13** |
| 触发 polyphony_weakness 章数 | — | **12/13** |

典型：Ch31 从 7.8 → 2.0（人工 voice×2=2，偏差 0.0 完全命中）；Ch29 从 8.5 → 3.0。
详见 `archive/v7/reports/task-170d-auditor-calibration-backtest.md`。

> Ch33 未触发 polyphony_weakness 但分数仍降到 2.5——因该章是单人独角戏（无对白可比），
> 校准通过"单人独白为主落低档"规则压分，与 170b 判断（Ch33 concept 强但 voice 无）一致。

## 交付物

- 工艺卡：`prompts/cards/literary_auditor/1.0.2.yaml`（新）
- 清单：`prompts/cards/literary_auditor/_manifest.yaml`（default_version → 1.0.2）
- 回测脚本：`scripts/backtest_170d_auditor_calibration.py`
- 回测报告：`archive/v7/reports/task-170d-auditor-calibration-backtest.md`
- 单测：`tests/test_170d_auditor_calibration.py`（7 用例：工艺卡锚点契约 5 + 解析透传 2）

## 验证结果

```
python -m pytest tests/test_170d_auditor_calibration.py -q   → 7 passed
python -m pytest tests/ -q                                   → 2428 passed, 2 skipped, 1 xfailed
ruff check src/ tests/ scripts/                              → All checks passed
真实 LLM 回测                                                 → 均值 7.69→2.46，13/13 收敛
```

## 验收对照

- [x] 对白同质章 character_autonomy 从 6.5-8.5 降到与人工 voice(1-2) 同向低档（回测 13/13 收敛）。
- [x] 校准方案（A）及依据写入本文档。
- [x] 单测覆盖：同质样本落低档如实透传 + 有区分样本高分透传 + 工艺卡锚点契约。
- [x] 全量测试 + ruff 通过。
- [x] 产出本 DONE 文档 + 回测报告。

## 与 170g 的衔接

170g 复评时以校准后 1.0.2 的 LiteraryAuditor 为**产品内主量具**，170b 的 5 维 LLM rubric 作交叉参照。
character_autonomy 现已可信（对同质敏感），可用于判断 170e voice 提质是否真正见效。

## Out of Scope（保持不变）

- 未改 LiteraryAuditor "只诊断、不阻塞 accept" 边界。
- 未把文学分接入 QualityGate。
- 未在 LiteraryAuditor 加 pacing 维度（归 170f RuleAuditor）。
- 未改生成侧（Writer/CreativeDirector）——那是 170e/170f。
- 历史落库的 1.0.1 分数不回改（版本不可变；新评估用 1.0.2 重跑）。
