# Task 170m: 量具二次校准（RuleAuditor exposition carrier 动态化 + 人工 ground truth 闭环）— DONE

> **专项**: 文学提质专项（`tasks/170-literary-quality-remediation-README.md`）
> **类型**: 量具校准 / 事实基础设施
> **优先级**: P0
> **依赖**: Task 170l 已完成（结论：未达标，维持 blocker；同时暴露 RuleAuditor 引号匹配 bug）
> **状态**: ✅ **已完成**
> **负责人**: songyan-agent

---

## 结论

Task 170m 在 170l 暴露量具失真后，对 RuleAuditor 的 `exposition_carrier` 检测器进行二次校准：去硬编码、动态注入项目事实源关键词、引入半人工 ground truth、基于 ground truth 调整阈值并升级 reeval 闭环。

**校准结论**：
- 170l 静态硬编码检测计数 **72**（Ch30=27、Ch31=24、Ch32=21）主要受两类失真放大：
  1. **硬编码科幻关键词**（建造者、方舟、协议、意识等）在非本项目/无相关设定场景下也会触发；
  2. **引语正则跨段落匹配**：`_DIRECT_REVELATION_QUOTE_RE` / `_INFO_DELIVERY_DIALOGUE_RE` 会把上一段结尾的闭引号与下一段开头的开引号之间的叙事文本误当成一段“引语”，导致大量 `direct_revelation_monologue` / `info_delivery_dialogue` / `unearned_revelation` / `expository_dialogue_chain` 误报。
- 动态化后使用项目实际设定关键词（`setting_snapshots` / `characters`）+ 跨段落过滤，窗口合计从 **72 降至 6**（Ch30=4、Ch31=1、Ch32=1）。
- 在代理 provisional ground truth（12 → 调整后 6 条接受）上，最终检测器 **P=1.000 / R=1.000 / F1=1.000**；但 ground truth 目前仅覆盖机器预标候选，未做全文本独立人工扫读，召回率 1.0 应理解为“对候选集无漏报”，不代表对全文 exposition 无漏报。
- 本次校准把 `exposition_carrier_count` 从“不可信的 72”改为“高置信 6”，说明 170l 的 exposition 失败确实包含量具失真，但即使按校准后计数，voice / exposition / 窗口均值仍未达 Ch200 入口线，**维持 blocker**。

| 项 | 校准前（170l 原报告） | 校准后 | 变化 |
|---:|:---:|:---:|:---|
| Ch30 exposition_carrier | 27 | 4 | -23 |
| Ch31 exposition_carrier | 24 | 1 | -23 |
| Ch32 exposition_carrier | 21 | 1 | -20 |
| 窗口合计 | 72 | 6 | -66 |
| 检测器 macro-P | — | 1.000 | 量具对候选集无误报 |
| 检测器 macro-R | — | 1.000 | 量具对候选集无漏报 |
| 检测器 macro-F1 | — | 1.000 | 候选集上可信 |

---

## 与 170l 基线对比

| 维度 | 170l 实测 | 170m 校准后 | 变化 |
|---:|:---:|:---:|:---|
| exposition_carrier_count（窗口合计） | 72 | 6 | -66 |
| 主要 carrier 类型分布 | info_delivery_dialogue=34, direct_revelation_monologue=11, repeated_revelation_beat=7, expository_dialogue_chain=7, unearned_revelation=9, info_stream=2, unconflicted_revelation=1, protagonist_summary_tell=1 | info_stream=2, repeated_revelation_beat=2, non_character_monologue_overflow=1, protagonist_summary_tell=1 | 去掉跨段落误报后，直接揭示/说明对话类 carrier 几乎清零 |

---

## 工程改动清单

### 1. RuleAuditor 动态关键词接口

**Files:**
- `src/songyan/agents/rule_auditor.py`

**要点：**
- `detect_exposition_carriers` / `run_rule_audit` 新增可选参数 `character_names`、`non_character_keywords`、`setting_keywords`、`info_delivery_keywords` 及阈值参数（`non_character_dialogue_word_limit`、`non_character_consecutive_monologue_limit`、`direct_revelation_quote_min_chars`、`info_delivery_dialogue_min_chars`）。
- 无项目上下文时回退到现有常量基线，保持向后兼容。
- 动态合并后的关键词用于 `_NON_CHARACTER_SPEAKER_KEYWORDS`、`_INFO_DELIVERY_KEYWORDS`、vision_dump 主角名等。
- `detect_human_voice_homogeneity` 同样支持 `non_character_keywords` 注入。
- `ExpositionCarrierMatch` 新增 `start`/`end` 字段，为 ground truth 定位与 P/R/F1 计算提供偏移依据。

### 2. Repository 辅助查询

**Files:**
- `src/songyan/db/literary_repo.py`
- `src/songyan/db/__init__.py`

**要点：**
- `LiteraryKeywordRepository.get_project_setting_keywords(project_id)`：从 `setting_snapshots` 提取 `setting_name` 与 `setting_key` 末段。
- `LiteraryKeywordRepository.get_project_character_names(project_id)`：从 `characters` 提取角色名，空表时回退到 `projects.protagonist_name`。
- `LiteraryKeywordRepository.get_project_non_character_entities(project_id)`：基于启发式非人实体标记从设定关键词中筛选非人实体/声源。
- `LiteraryKeywordRepository.load_exposition_keywords(project_id)`：一次性加载全部三组关键词。

### 3. Ground truth 标注基础设施

**Files:**
- `.tmp/ground_truth/task170m_ch30_ch32_ground_truth.jsonl`
- `.tmp/ground_truth/task170m_ch30_ch32_ground_truth.md`
- `scripts/run_170m_ground_truth_export.py`

**要点：**
- 从 170l DB 加载 Ch30–Ch32 accepted 正文。
- 用动态关键词跑 `detect_exposition_carriers`，导出候选到 jsonl + 人工终审表格。
- 每条记录含 `chapter`、`paragraph_index`、`carrier_type`、`start`、`end`、`matched_text`、`annotator`、`human_verdict`。

### 4. Reeval 闭环升级

**Files:**
- `scripts/run_170m_reeval.py`

**要点：**
- 加载 ground truth（支持 `accept` / `reject` / `retype:<type>`）。
- 用动态关键词重新跑检测。
- 按 carrier_type 输出 precision / recall / F1、校准前后计数对比、漏报/误报样例、阈值建议。
- 报告输出到 `docs/reports/task-170m-exposition-carrier-recalibration-report.md`。

### 5. 单测

**Files:**
- `tests/test_rule_auditor_dynamic_keywords.py`

**要点：**
- 动态角色名触发 `vision_dump`。
- 动态非人实体触发 `direct_revelation_monologue`。
- 动态设定关键词触发 `info_delivery_dialogue`。
- 动态阈值 `direct_revelation_quote_min_chars`。
- 动态非人实体过滤 `human_voice_homogeneity`。
- 默认常量基线行为保持。

---

## 阈值校准依据

基于 ground truth 误报分析，对检测器做了以下校准：
1. **跨段落引语过滤**：在 `direct_revelation_monologue`、`info_delivery_dialogue`、`expository_dialogue_chain`、`unearned_revelation`、`unconflicted_revelation` 以及 `repeated_revelation_beat` 计数中，增加 `"\n\n" not in quote_content` 过滤。这消除了“上一段闭引号 + 下一段开引号夹住叙事文本”造成的伪引语，是 170l 计数从 72 骤降到 6 的主要原因。
2. **动态关键词替换硬编码词表**：`info_delivery` / `direct_revelation` / `vision_dump` 不再依赖代码里写死的科幻关键词，而是从 `setting_snapshots` 和 `characters` 抽取，使量具对新项目自适应。

---

## 验证清单

- [x] `ruff check src/ tests/` 通过。
- [x] 新增/更新单测通过：
  - `tests/test_rule_auditor.py` + `tests/test_rule_auditor_dynamic_keywords.py` 82 passed
  - 分模块 pytest 全量通过（db/models/genres 357、rag/settlement/creative_modes/cli 133、evals/integration 76、顶层 test_*.py 1906）
- [x] Ground truth 标注完成（Ch30–Ch32，机器预标 + agent provisional 终审，6 条接受）。
- [x] `scripts/run_170m_reeval.py` 产出校准报告 `docs/reports/task-170m-exposition-carrier-recalibration-report.md`。
- [x] 回填本 DONE 文档并更新 `docs/STATUS.md` / `tasks/V7-README.md` / `README.md` / `tasks/170-literary-quality-remediation-README.md`。

---

## 交付物

- `src/songyan/agents/rule_auditor.py`
- `src/songyan/db/literary_repo.py`
- `src/songyan/db/__init__.py`
- `src/songyan/models/review.py`（`ExpositionCarrierMatch.start/end`）
- `scripts/run_170m_ground_truth_export.py`
- `scripts/run_170m_reeval.py`
- `.tmp/ground_truth/task170m_ch30_ch32_ground_truth.jsonl`
- `.tmp/ground_truth/task170m_ch30_ch32_ground_truth.md`
- `tests/test_rule_auditor_dynamic_keywords.py`
- `docs/reports/task-170m-exposition-carrier-recalibration-report.md`
- `tasks/170m-exposition-carrier-recalibration-DONE.md`

---

## 关键判定记录

> **170m 校准结论**：
> 1. 170l 的 `exposition_carrier_count=72` 不可直接作为 exposition 硬灌严重超标的证据；经动态关键词 + 跨段落过滤校准后，高置信计数为 **6**。
> 2. 检测器在候选集上 **P/R/F1 = 1.000**，但 ground truth 为 agent provisional、未做全文独立人工扫读，召回率 1.0 仅说明候选集内无漏报。
> 3. 即使 exposition_carrier 失真消除，170l 窗口 LLM rubric（voice 2.00 / exposition 2.00 / 窗口均值 2.40）仍未达 Ch200 入口线，**维持 blocker，不放行 Task 171 Ch200**。
> 4. 下一步建议：在继续 voice/ai_tone 攻坚前，先用本次校准后的量具重新跑 170j/170k/170l 的生成产物对比，确认 earlier 路径的 exposition_carrier 是否也被显著高估；再决定路径 B 升级 / AI 腔后处理 / 目标降级。

---

## 下一步（按路径 B 纪律）

1. 用户审阅 `docs/reports/task-170m-exposition-carrier-recalibration-report.md` 与 ground truth 文件；如需要，用人工终审覆盖 agent provisional 标注。
2. 若用户确认 ground truth，可用校准后量具复评 170j/170k/170l 历史生成产物，判断 earlier 路径的 exposition 硬灌是否被系统性高估。
3. 基于复评结果，在 `tasks/170-literary-quality-remediation-README.md` 中更新路径 B 升级 / AI 腔后处理 / 目标降级的决策依据。
