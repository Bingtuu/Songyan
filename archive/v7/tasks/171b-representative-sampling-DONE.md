# Task 171b: 代表性样本集 —— DONE（C1/C2/C3 达标）

> **框架**: `docs/reports/v7-literary-framework-review.md` §8 C 组（C1/C2/C3）+ §7.1 R1
> **状态**: ✅ **完成**
> **报告**: `archive/v7/reports/task-171b-representative-sampling-report.md`
> **完成时间**: 2026-07-10

---

## 结论

Task 171b 解决旧框架的**样本不代表性**错误（框架 E-样本环）。用 171a 量具**自身**的对话密度信号（`_VOICE_QUOTE_RE`，与量具章级门同源）对两体裁 + 历史稀疏参照层共 40 章做分层，使 voice **只在能公平测量的对话承载/混合章计分**、稀疏章显式剔除；覆盖 ≥2 体裁；并落地 2×2 归因 checklist。**未改量具、未 live 生成、未阻塞 Ch200、未放宽任何冻结口径。**

一个关键校准发现（诚实入报告）：Task 170 过拟合的 **Ch29–32 并非稀疏**（密度 4.46–12.09），故 170 的 voice≈2.0 低分**不是样本稀疏错配，而是当时量具归因失效**（171a 已修）——把 170 失败精确归到『量具无效』格，而非『模型能力』或『样本稀疏』。

---

## 验收对照（框架 §8 C 组）

| 编号 | 验收项 | 状态 | 证据 |
|---|---|:---:|---|
| C1 | 场景分层采样（voice 只在对话密集章计分） | ✅ | 密度分三层（sparse<3.0 / mixed 3.0–8.0 / dialogue≥8.0，阈值由真实分布校准）；稀疏章 voice_applicable=False。scifi_hist ch1/2/5/16/18（密度 1.47–2.65）被正确剔除 |
| C2 | 多体裁交叉（≥2 体裁） | ✅ | 主结论覆盖 scifi（170p，5 章）+ wuxia（171a-1 live，4 章）；scifi_hist（170i，31 章）作稀疏参照层 |
| C3 | 归因格子正确（2×2 表） | ✅ | 报告 §3：voice/exposition 均落『量具有效 × 样本代表』格（可归因模型能力）；170 旧结论归『量具无效 × 样本单点』格、判为假象 |
| 工程 | 采样脚本可复算 + ruff/pytest | ✅ | `scripts/run_171b_sampling.py` 可复算；`ruff` 通过；`test_171b_sampling.py` 14 passed |

---

## 工程改动清单

### `src/songyan/utils/sampling.py`（新增）
- `dialogue_density(char_count, quote_count)`：成对引号数 / 每千字（char_count≤0 返回 0.0）。
- `classify_dialogue_layer(...)`：按密度返回 (层, 密度)，阈值 `SPARSE_MAX_DENSITY=3.0` / `DIALOGUE_MIN_DENSITY=8.0`（由真实语料分布校准），可覆盖。
- `is_voice_applicable(layer)`：稀疏层 False（对治样本错配）。
- **不改任何检测逻辑**；分层信号与 `rule_auditor._VOICE_QUOTE_RE` 同源，保证「分层口径 = 量具计分口径」。

### `scripts/run_171b_sampling.py`（新增）
- 从两体裁 live DB（scifi 170p + wuxia 171a-1）+ 历史稀疏参照 DB（170i）加载 accepted 正文，逐章分层 + 跑真实 `detect_human_voice_homogeneity` 记录 voice 可计算性。
- 导出样本清单 `.tmp/samples/task171b_sample_manifest.jsonl`（40 行）+ 报告（分层表 + 覆盖统计 + 2×2 归因 checklist + 校准发现）。

### 测试
- `tests/test_171b_sampling.py`（新）：14 用例，覆盖密度计算边界（0/负字数）、三层分类边界（3.0/8.0）、自定义阈值、voice 适用性、以及"稀疏章即使过量具门也剔除"的语义一致性；band 断言用真实语料值（170p ch1/ch4、170i ch5/ch18）。

---

## 分层结果摘要

- **C1 分层**：dialogue 13 章 / mixed 22 章 / sparse 5 章。
- **主语料（scifi+wuxia）9 章全部 dialogue/mixed** → 全部 voice 适用，无稀疏错配；voice 命中：scifi-ch2、wuxia-ch3（各一处声纹趋同，与 171a-1 GT 一致）。
- **稀疏层实例**（voice 不适用）：scifi_hist ch1(2.14)/ch2(2.65)/ch5(1.47)/ch16(2.19)/ch18(2.08)。

---

## 验证清单
- [x] `ruff check src/songyan/utils/sampling.py tests/test_171b_sampling.py scripts/run_171b_sampling.py` 全通过。
- [x] `tests/test_171b_sampling.py` 14 passed；与 `test_rule_auditor*.py`+`test_171a_literary_keyword_wiring.py` 合跑 **108 passed**。
- [x] `scripts/run_171b_sampling.py` 可复算，产出 manifest（40 行）+ 报告。
- [x] 清理临时探针 `.tmp/probe_171b.py`。

---

## 出口与下一步
- **C1/C2/C3 达标**：样本方法论落地，量具+样本"双环"已修，2×2 归因表证明 170 低分是假象。
- **下一步 Task 171c**（spec `archive/v7/tasks/171c-improvement-levers.md`）：在本样本集的**对话承载层**上做杠杆组合验证（后处理/few-shot/解码参数/换模型/人工抽读，带退出判据）——现在"提质有没有效"可被可信量具 + 代表样本客观判读。
- 171b 不阻塞 Ch200；提质结论只在达标格子（量具有效 × 样本代表）内下。
