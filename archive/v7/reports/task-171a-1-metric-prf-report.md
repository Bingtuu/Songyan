# Task 171a-1: 跨体裁量具效度量化报告（voice / exposition P/R/F1）

> 生成时间: 2026-07-10
> 对应框架: `docs/reports/v7-literary-framework-review.md` §8 **B2/B3**
> 数据: scifi（170p DB `run-bcf3b8f1`，Ch1–5）+ wuxia（171a-1 新生成 `run-416227cc`，Ch1–4）
> 量具: 171a 重建后的 `detect_exposition_carriers` + `detect_human_voice_homogeneity`，均注入项目实际角色/设定关键词（体裁解耦通电）
> 注: `scripts/run_171a1_reeval.py` 会生成同名简版表格；本文件为含归因/局限的终版，二者数字一致。

---

## 1. 结论

- **voice 量具（`human_voice_homogeneity`）：F1 = 1.000（scifi + wuxia 双体裁）✅ ≥ 0.8**。
- **exposition 量具：F1 = 0.889（scifi）/ 1.000（wuxia）✅ ≥ 0.8**。
- **量具补强（171a-1 执行中定位并修复）**："跨对话轮引语拼接"假阳性——`direct_revelation_quote_re` / `info_delivery_dialogue_re` 改为**方向性引号**（开 `["“]`、闭 `["”]`，内部禁含引号），使"上一句闭引号 + 叙事 + 下一句开引号"不再被误当一段引语。wuxia exposition precision **0.70 → 1.00**，候选 11 → 7。
- **体裁解耦实证成立**：wuxia（非科幻）真实 prose 上，量具在**零科幻词表**下正常检出 info-delivery / voice 同质 / protagonist summary-tell，并被注入的 wuxia 角色注册表（沈砚/柳孤鸣/曲靖等 6 人）正确归因。
- **B2/B3 达标**：voice 与 exposition 在两体裁 F1 均 ≥ 0.8。scifi exposition 残留 2 个"aggregate beat 双计"是 report-only 冗余（同一 info_delivery 既单条命中又计入 `repeated_revelation_beat` 计数），非真实误报，记为已知观测项。

---

## 2. P/R/F1 结果（量具补强后）

| genre | family | gt | pred | tp | fp | fn | P | R | F1 | 判定 |
|---|---|---:|---:|---:|---:|---:|---:|---:|---:|:---:|
| scifi | voice | 1 | 1 | 1 | 0 | 0 | 1.00 | 1.00 | **1.000** | ✅ |
| scifi | exposition | 8 | 10 | 8 | 2 | 0 | 0.80 | 1.00 | **0.889** | ✅ |
| wuxia | voice | 1 | 1 | 1 | 0 | 0 | 1.00 | 1.00 | **1.000** | ✅ |
| wuxia | exposition | 6 | 6 | 6 | 0 | 0 | 1.00 | 1.00 | **1.000** | ✅ |

> family 定义：voice = `human_voice_homogeneity`；exposition = 其余 carrier 类型（info_delivery_dialogue / direct_revelation_monologue / protagonist_summary_tell / repeated_revelation_beat 等）。补强前 wuxia exposition 为 P=0.70/F1=0.824（3 个跨对话轮 artifact），修复后清零。

---

## 3. 假阳性归因与修复

- **跨对话轮引语拼接（已修）**：wuxia Ch3 两处 `info_delivery_dialogue` 的 `matched_text` 实为两段引号之间的**叙事描写**（"布片…边缘被烧得焦黑"、"字迹很工整…信笺泛黄"），无换行故 `"\n\n"` 过滤拦不住。根因是原正则允许**闭引号 `”` 作开头**。改方向性引号后清零。同一修复也移除了 wuxia Ch3 把动作场景（掷茶碗碎片）误判为 `direct_revelation_monologue` 的 FP。
- **aggregate beat 双计（scifi 残留 2，report-only）**：`repeated_revelation_beat` 汇总计数与单条 `info_delivery_dialogue` 命中并存，属同一现象的两种记法，不构成真实误报，保留为观测冗余。

---

## 4. 方法与局限（诚实标注）

- **标注为 agent-provisional**（`scripts/run_171a1_label.py`，policy 内联可审计），非人工终审盲标。与 170m 同口径：recall=1.0 表示**候选集内无漏报**，不代表对全文独立扫读无漏报（GT 取自候选集，未做正文逐句独立标注）。
- 样本量小（scifi 11 / wuxia 7 候选、4–5 章）。结论为"量具在两体裁候选集上精度达标（F1 ≥ 0.8）+ 体裁解耦生效 + 跨对话轮 artifact 已修"，不宣称统计意义上的全量精度。
- 若需更强证据，可扩大盲标窗口 + 人工终审覆盖 agent-provisional。

---

## 5. 复现

```
python scripts/run_171a1_generate.py --init          # 建 wuxia 项目 + 大纲
python scripts/run_171a1_generate.py --start 1 --end 4   # 真实 API 生成（run-416227cc，4/4）
python scripts/run_171a1_reeval.py --export          # 导出候选（scifi 170p + wuxia）
python scripts/run_171a1_label.py                    # agent-provisional 盲标
python scripts/run_171a1_reeval.py                   # 计算 P/R/F1
```

- 候选/标注：`.tmp/ground_truth/task171a1_{scifi,wuxia}_ground_truth.jsonl`
- wuxia 生成 DB：`.tmp/task171a1_wuxia.db`（run-416227cc，Ch1–4 4/4 completed，failed=[]）
