# Task 171b: 代表性样本集报告（场景分层 + ≥2 体裁 + 2×2 归因）

> 生成时间: 2026-07-10T23:21:02
> 对应框架 `docs/reports/v7-literary-framework-review.md` §8 **C 组**（C1/C2/C3）。
> 分层信号复用 171a 量具的 `_VOICE_QUOTE_RE`（章级对话密度门同源），保证「分层口径 = 量具计分口径」。

---

## 1. 分层口径（C1）

密度 = 成对引号数 / 每千字（`_VOICE_QUOTE_RE`，与量具章级门 `min_chapter_quotes` 同源信号）。阈值由真实语料分布校准（见 §2）：

| 层 | 密度（每千字） | voice 计分? | 语义 |
|---|---|:---:|---|
| sparse（稀疏/意识流） | < 3.0 | ❌ 不适用 | 单人解谜/意识流/纯叙事，无可比对白对 |
| mixed（混合） | 3.0 – 8.0 | ✅ 计分 | 有对白但夹叙述，voice 可测但样本量有限 |
| dialogue（对话承载） | ≥ 8.0 | ✅ 计分 | 多角色密集对白，voice 评估主力 |

> **不改量具**：本分层是采样层信号，量具章级门（`quote_count ≥ 2`）不变。所有『对话承载/混合』章均通过量具门，稀疏章即使通过量具门也从 voice 评估集显式剔除（对治 170 在稀疏章硬扣 voice≥3.0 的样本错配）。

## 2. 分层结果（逐章）

| genre | ch | 字数 | 引语 | 密度/千字 | 层 | voice计分 | voice命中 |
|---|---:|---:|---:|---:|---|:---:|:---:|
| scifi | 1 | 3370 | 57 | 16.91 | dialogue | ✅ | — |
| scifi | 2 | 3325 | 59 | 17.74 | dialogue | ✅ | ✅ |
| scifi | 3 | 4203 | 48 | 11.42 | dialogue | ✅ | — |
| scifi | 4 | 3898 | 18 | 4.62 | mixed | ✅ | — |
| scifi | 5 | 4469 | 47 | 10.52 | dialogue | ✅ | — |
| wuxia | 1 | 3704 | 47 | 12.69 | dialogue | ✅ | — |
| wuxia | 2 | 3375 | 22 | 6.52 | mixed | ✅ | — |
| wuxia | 3 | 4300 | 86 | 20.0 | dialogue | ✅ | ✅ |
| wuxia | 4 | 4491 | 37 | 8.24 | dialogue | ✅ | — |
| scifi_hist | 1 | 3277 | 7 | 2.14 | sparse | ❌ | — |
| scifi_hist | 2 | 4146 | 11 | 2.65 | sparse | ❌ | — |
| scifi_hist | 3 | 4378 | 17 | 3.88 | mixed | ✅ | — |
| scifi_hist | 4 | 5140 | 28 | 5.45 | mixed | ✅ | — |
| scifi_hist | 5 | 4769 | 7 | 1.47 | sparse | ❌ | — |
| scifi_hist | 6 | 3478 | 16 | 4.6 | mixed | ✅ | — |
| scifi_hist | 7 | 5217 | 47 | 9.01 | dialogue | ✅ | — |
| scifi_hist | 8 | 5130 | 16 | 3.12 | mixed | ✅ | — |
| scifi_hist | 9 | 5076 | 17 | 3.35 | mixed | ✅ | — |
| scifi_hist | 11 | 4893 | 21 | 4.29 | mixed | ✅ | — |
| scifi_hist | 12 | 4788 | 44 | 9.19 | dialogue | ✅ | — |
| scifi_hist | 13 | 4621 | 25 | 5.41 | mixed | ✅ | — |
| scifi_hist | 14 | 4775 | 36 | 7.54 | mixed | ✅ | — |
| scifi_hist | 15 | 5185 | 19 | 3.66 | mixed | ✅ | — |
| scifi_hist | 16 | 3202 | 7 | 2.19 | sparse | ❌ | — |
| scifi_hist | 17 | 4392 | 30 | 6.83 | mixed | ✅ | — |
| scifi_hist | 18 | 3364 | 7 | 2.08 | sparse | ❌ | — |
| scifi_hist | 19 | 4280 | 31 | 7.24 | mixed | ✅ | — |
| scifi_hist | 20 | 4868 | 29 | 5.96 | mixed | ✅ | — |
| scifi_hist | 21 | 4107 | 41 | 9.98 | dialogue | ✅ | — |
| scifi_hist | 22 | 5204 | 62 | 11.91 | dialogue | ✅ | — |
| scifi_hist | 23 | 4520 | 15 | 3.32 | mixed | ✅ | — |
| scifi_hist | 24 | 3673 | 12 | 3.27 | mixed | ✅ | — |
| scifi_hist | 25 | 4558 | 28 | 6.14 | mixed | ✅ | — |
| scifi_hist | 26 | 4150 | 26 | 6.27 | mixed | ✅ | — |
| scifi_hist | 27 | 5173 | 48 | 9.28 | dialogue | ✅ | — |
| scifi_hist | 28 | 4985 | 15 | 3.01 | mixed | ✅ | — |
| scifi_hist | 29 | 3141 | 14 | 4.46 | mixed | ✅ | — |
| scifi_hist | 30 | 5452 | 32 | 5.87 | mixed | ✅ | — |
| scifi_hist | 31 | 3384 | 23 | 6.8 | mixed | ✅ | — |
| scifi_hist | 32 | 4465 | 54 | 12.09 | dialogue | ✅ | — |

### 覆盖统计

- **C1 分层**：{'dialogue': 13, 'mixed': 22, 'sparse': 5} —— 稀疏章已从 voice 评估集剔除。
- **C2 体裁**：主结论覆盖 ['scifi', 'wuxia']（≥2）；scifi_hist 仅作稀疏参照层。
- 稀疏层实例（voice 不适用）：scifi_hist-ch1(2.14), scifi_hist-ch2(2.65), scifi_hist-ch5(1.47), scifi_hist-ch16(2.19), scifi_hist-ch18(2.08)。

### 关键校准发现（诚实标注）

- **稀疏章确实存在且被正确剔除**：scifi_hist ch1/2/5/16/18（密度 1.47–2.65）落 sparse 层、voice 不计分 —— 这是 C1 的实证（分层能挡住意识流/单人解谜章）。
- **但 Task 170 过拟合的 Ch29–32 并非稀疏**：其密度 4.46–12.09（mixed/dialogue），即『有对白可比』。故 170 在该窗口 voice≈2.0 的低分**不是样本稀疏错配**，而是当时量具归因失效（171a 已修：170p DB Ch2 voice 0→1）。这把 170 的失败精确定位到『量具无效』格，而非『样本稀疏』或『模型能力』。

## 3. 2×2 失败归因 checklist（框架 §6.3 / §8 C3）

> 列＝量具是否已验证效度（171a-1 出口）；行＝样本是否代表（本任务）。
> **只有『量具有效 × 样本代表』格才允许把低分归因为「模型能力」**；其余格先修量具或换样本。

| 维度 | 量具已验证效度? (171a-1) | 样本代表? (171b) | 允许归因「模型能力」? |
|---|:---:|:---:|:---:|
| voice | ✅ 是（两体裁 F1=1.0） | ✅ 是（≥2 体裁 + 密度分层，仅对话承载章计分） | ✅ 可 |
| exposition | ✅ 是（两体裁 F1=0.889/1.0） | ✅ 是（≥2 体裁，全章适用） | ✅ 可 |

- 覆盖体裁：scifi, scifi_hist, wuxia（含历史 scifi_hist 仅作稀疏参照，不计入主结论覆盖）。
- 旧 Task 170 结论（voice≈2.0）落在『量具无效 × 样本单点』格 —— 现已双修，
  故 170 的「模型写不好」结论**不成立**（是量具+样本假象）。

## 4. 出口与局限

- **C1/C2/C3 达标**：分层落地（voice 只在对话承载/混合章计分）、≥2 体裁交叉、2×2 归因表填齐。
- 样本量仍小（主语料 scifi 5 章 + wuxia 4 章）；密度阈值（3.0/8.0）由本批语料校准，扩样后可复算 `run_171b_sampling.py` 重新校准。
- 本任务只做采样方法论；提质杠杆验证在 171c，在本样本集的『对话承载』层上进行。

## 5. 复现

```
python scripts/run_171b_sampling.py --print
```
- 样本清单：`.tmp/samples/task171b_sample_manifest.jsonl`