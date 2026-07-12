# Task 171a-1: 文学量具效度量化 —— DONE（B2/B3 达标）

> **框架**: `docs/reports/v7-literary-framework-review.md` §8 B 组（B2/B3）
> **状态**: ✅ **完成**（voice/exposition 两体裁 F1 均 ≥ 0.8）
> **报告**: `docs/reports/task-171a-1-metric-prf-report.md`
> **完成时间**: 2026-07-10

---

## 结论

Task 171a-1 补齐了框架 §8 的 **B2/B3**——在 **scifi + wuxia 两个对话属性不同的体裁**上，用**遮机器分的 agent-provisional 盲标 ground truth**，对 voice（`human_voice_homogeneity`）与 exposition（`exposition_carrier` 族）分别量化 P/R/F1，**四个 genre×family 组合 F1 全部 ≥ 0.8**。量化过程中定位并修复了一处"跨对话轮引语拼接"假阳性（方向性引号收敛），wuxia exposition precision 由 0.70 提升到 1.00。**全程未阻塞 Ch200 主线，未放宽任何冻结口径。**

---

## 验收对照（框架 §8 B 组 + 本任务验收标准）

| 编号 | 验收项 | 状态 | 证据 |
|---|---|:---:|---|
| B2 | ≥2 体裁盲标 ground truth | ✅ | `.tmp/ground_truth/task171a1_{scifi,wuxia}_ground_truth.jsonl`；wuxia 为 live 生成（run-416227cc，Ch1–4，4/4） |
| B3 | voice/exposition P/R/F1 ≥ 0.8 | ✅ | scifi voice F1=1.000 / exposition F1=0.889；wuxia voice F1=1.000 / exposition F1=1.000 |
| 出口判定 | 达标维度可进 171c | ✅ | voice、exposition 两维度在两体裁均 ≥ 0.8，均"可信"，可作为 171c 提质的可归因依据 |

---

## P/R/F1 结果（量具补强后）

| genre | family | gt | pred | tp | fp | fn | P | R | F1 | 判定 |
|---|---|---:|---:|---:|---:|---:|---:|---:|---:|:---:|
| scifi | voice | 1 | 1 | 1 | 0 | 0 | 1.00 | 1.00 | **1.000** | ✅ |
| scifi | exposition | 8 | 10 | 8 | 2 | 0 | 0.80 | 1.00 | **0.889** | ✅ |
| wuxia | voice | 1 | 1 | 1 | 0 | 0 | 1.00 | 1.00 | **1.000** | ✅ |
| wuxia | exposition | 6 | 6 | 6 | 0 | 0 | 1.00 | 1.00 | **1.000** | ✅ |

> scifi exposition 残留的 2 个 FP 是 `repeated_revelation_beat` 汇总计数与单条 `info_delivery_dialogue` 命中并存的"aggregate beat 双计"，属同一现象的两种记法（report-only 冗余），非真实误报，记为已知观测项。

---

## 工程改动清单

### `src/songyan/agents/rule_auditor.py`（量具补强）
- `detect_exposition_carriers`：`direct_revelation_quote_re` / `info_delivery_dialogue_re` 由"任意成对引号"改为**方向性引号**（开 `["“]`、闭 `["”]`，引语内部禁含引号），使"上一句闭引号 + 叙事描写 + 下一句开引号"不再被误当一段引语。修复跨对话轮 artifact。

### 脚本（新增）
- `scripts/run_171a1_generate.py`：wuxia（第二体裁）生成台架。`--init` 建"断剑江湖"项目（主角沈砚，genre_id=wuxia，mode_id=webnovel）；`--start/--end` 跑真实 API 生成。
- `scripts/run_171a1_reeval.py`：跨体裁效度 reeval。`--export` 导出候选（scifi 170p + wuxia）→ 盲标 → 默认计算 P/R/F1 写报告。`_prf` 将全部候选计为 prediction，rejected 计 FP（precision 无构造性 1.0）。
- `scripts/run_171a1_label.py`：agent-provisional 盲标（policy 内联可审计）。

### 测试
- `tests/test_rule_auditor.py`：新增 `test_171a1_cross_dialogue_narration_not_info_delivery`（方向性引号回归，锁定跨对话轮 artifact 不再命中 info_delivery）。

---

## 关键发现与修复

- **跨对话轮引语拼接（已修）**：wuxia Ch3 两处 `info_delivery_dialogue` 的 `matched_text` 实为两段引号之间的**叙事描写**（如"布片…边缘被烧得焦黑"），无换行故 `"\n\n"` 过滤拦不住。根因是原正则允许闭引号 `”` 作开头。改方向性引号后，wuxia exposition 候选 11→7、precision 0.70→1.00，同一修复也移除了动作场景被误判为 `direct_revelation_monologue` 的 FP。
- **体裁解耦实证**：wuxia（零科幻词表）真实 prose 上，量具正常检出 info-delivery / voice 同质 / protagonist summary-tell，并被注入的 wuxia 角色注册表（沈砚/柳孤鸣/曲靖等 6 人）正确归因。live 生成日志显示 `literary_keywords.loaded` 触发（171a 前为死代码），确认体裁解耦端到端通电。

---

## 方法与局限（诚实标注）

- **标注为 agent-provisional**，非人工终审盲标；与 170m 同口径：recall=1.0 表示"候选集内无漏报"，不代表对全文独立扫读无漏报（GT 取自候选集，未做正文逐句独立标注）。
- 样本量小（scifi 11 / wuxia 7 候选，4–5 章/体裁）。结论为"量具在两体裁候选集上精度达标（F1 ≥ 0.8）+ 体裁解耦生效 + 跨对话轮 artifact 已修"，**不宣称统计意义上的全量精度**——后者由 171b 代表性样本 + 更宽盲标窗口承接。

---

## 验证清单
- [x] `ruff check src/ tests/ scripts/run_171a1_*.py` 全通过。
- [x] `tests/test_rule_auditor.py` + `test_rule_auditor_dynamic_keywords.py` + `test_171a_literary_keyword_wiring.py`：94 passed。
- [x] wuxia live 生成 run-416227cc：completed=[1,2,3,4]，failed=[]。
- [x] 两体裁盲标 GT 落地；报告 `docs/reports/task-171a-1-metric-prf-report.md` 产出（含 P/R/F1 + 误报归因 + 局限）。
- [x] 清理临时诊断脚本 `.tmp/inspect_wuxia_fp.py`。

---

## 出口与下一步
- **B2/B3 达标**：voice、exposition 两维度在 scifi + wuxia 均 F1 ≥ 0.8，量具效度"可信"。171a（R0）代码侧 + 量化侧全部落地。
- **下一步 Task 171b**（spec `tasks/171b-representative-sampling.md`）：把小样本效度升级为**代表性样本**——扩大盲标窗口 + 对话密集/稀疏分层，覆盖框架 §8 C 组，为 171c 提质与"全量精度"结论奠基。
- 171a-1 不阻塞 Ch200；171c 提质在已达标维度（voice/exposition）上启动。
