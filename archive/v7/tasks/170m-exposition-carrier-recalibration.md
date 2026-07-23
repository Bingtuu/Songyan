# Task 170m: 量具二次校准（RuleAuditor exposition carrier 动态化 + 人工 ground truth 闭环）

> **专项**: 文学提质专项（`archive/v7/tasks/170-literary-quality-remediation-README.md`）
> **类型**: 量具校准 / 事实基础设施
> **优先级**: P0
> **依赖**: Task 170l 已完成（结论：未达标，维持 blocker；同时暴露 RuleAuditor 引号匹配 bug）
> **状态**: ✅ 已完成
> **负责人**: songyan-agent

---

## 任务边界

Task 170l 小样本复评显示 `exposition_carrier_count=72`（Ch30=27, Ch31=24, Ch32=21），但该计数仍可能失真，因为 RuleAuditor 的 exposition carrier 检测器中存在大量**硬编码关键词、主角名、阈值和世界线特定实体名**。在基于这个计数判断"路径 B 是否到顶"之前，必须先完成一轮量具二次校准：

1. **去硬编码**：把 `_NON_CHARACTER_SPEAKER_KEYWORDS`、`_INFO_DELIVERY_KEYWORDS`、vision_dump 主角名、代价/冲突线索词表等从代码常量改为从项目事实源（DB: `setting_snapshots`、`characters`、`project_settings`）动态抽取。
2. **引入人工 ground truth**：从 170l 生成的 Ch30–Ch32 正文中人工/半人工标注 exposition 硬灌段落，建立第一份可审计的 ground truth。
3. **校准阈值**：基于 ground truth 计算当前检测器的 precision / recall / F1，调整字数阈值、连续句数阈值、引语长度阈值。
4. **接入 reeval 闭环**：在 `run_170l_reeval.py` 中增加"机器检测 vs 人工标注"对比表，输出校准后的 `exposition_carrier_count` 和置信区间。

**本任务不改生成侧代码、不改 Writer/CreativeDirector/RevisionHandler，只动量具和报告脚本。**

---

## 核心目标

1. 让 `exposition_carrier_count` 对任意项目都能基于真实设定/角色名动态计算，而不是依赖代码里写死的科幻关键词。
2. 拿到 170l Ch30–Ch32 的 ground truth 标注和检测器 P/R/F1，明确当前量具是漏报多还是误报多。
3. 输出校准后的 170l 复评报告，作为用户判断"路径 B 是否到顶"的事实基础。

---

## 验收标准

### 工程验收
- `ruff check src/ tests/` 通过。
- 新增/更新单测覆盖动态关键词抽取、引号匹配、阈值边界。
- 无大纲项目 / 新项目 / 主角名变更场景下，检测器能自适应（至少不 crash，最好不依赖硬编码）。
- `run_170m_reeval.py`（或升级 `run_170l_reeval.py`）能输出 ground truth 对比表。

### 量具校准
- 建立 Ch30–Ch32 人工/半人工 ground truth（格式：`chapter | paragraph | carrier_type | start | end | note`）。
- 计算并报告当前检测器在 ground truth 上的 precision / recall / F1（按 carrier_type 拆分）。
- 根据 ground truth 至少调整一项阈值（如 `_NON_CHARACTER_DIALOGUE_WORD_LIMIT`、`_DIRECT_REVELATION_QUOTE_RE` 长度下限、`_INFO_DELIVERY_DIALOGUE_RE` 长度下限等），并给出调整理由。

### 决策交付
- `archive/v7/tasks/170m-exposition-carrier-recalibration-DONE.md` 必须明确给出：
  - 校准后的 Ch30–Ch32 `exposition_carrier_count`；
  - 检测器 P/R/F1；
  - 与 170l 原计数的差异解释；
  - 是否支持"路径 B 到顶"或"仍有升级空间"的判断。

---

## 关键改动清单

### 1. RuleAuditor 动态关键词接口

**Files:**
- `src/songyan/agents/rule_auditor.py`

**要点：**
- 新增可选参数 `project_id` / `setting_keywords` / `character_names`，用于动态注入关键词。
- 保留现有常量作为 fallback（无项目上下文时仍然可用）。
- 把 `_NON_CHARACTER_SPEAKER_KEYWORDS`、`_INFO_DELIVERY_KEYWORDS`、vision_dump 中的主角名改写为函数内根据注入参数合并后的集合。
- `_EARNED_REVELATION_CUES`、`_OPPOSING_JUDGMENT_CUES`、`_COST_CUES` 仍保留为基线词表，但允许外部扩展。

### 2. Repository 辅助查询

**Files:**
- `src/songyan/db/review_repo.py` 或新增 `src/songyan/db/literary_repo.py`

**要点：**
- 提供 `get_project_setting_keywords(project_id)`：从 `setting_snapshots` 提取高频 setting_key / setting_name / alias。
- 提供 `get_project_character_names(project_id)`：从 `characters` 提取角色名（ protagonist + 主要配角）。
- 提供 `get_project_non_character_entities(project_id)`：从 setting_snapshots 中识别非人实体（如织网者、建造者、深渊社等）——可通过 setting_key 前缀/名称模式或 LLM 分类辅助。

### 3. Ground truth 标注基础设施

**Files:**
- `.tmp/ground_truth/task170m_ch30_ch32_ground_truth.jsonl`（人工/半人工标注数据）
- `scripts/run_170m_ground_truth_export.py`：把 170l DB 中 Ch30–Ch32 accepted 正文导出为便于标注的格式（段落 + 机器预标）。

**标注格式：**
```json
{"chapter": 30, "paragraph_index": 11, "paragraph_text": "...", "carrier_type": "info_delivery_dialogue", "start": 120, "end": 340, "annotator": "llm_pre", "note": "角色用长段说明协议规则", "human_verdict": null}
```

**半人工流程：**
1. 机器预标：用当前检测器输出候选。
2. 人工终审：用户对候选做 accept / reject / retype / add-missing。
3. 锁定 ground truth。

### 4. Reeval 闭环升级

**Files:**
- `scripts/run_170l_reeval.py` 或新建 `scripts/run_170m_reeval.py`

**要点：**
- 加载 ground truth。
- 用动态关键词重新跑 `detect_exposition_carriers`。
- 输出：
  - 按 carrier_type 的 precision / recall / F1；
  - 校准前后 `exposition_carrier_count` 对比；
  - 漏报/误报典型案例；
  - 推荐阈值。

### 5. 单测

**Files:**
- `tests/test_rule_auditor.py`

**要点：**
- 动态关键词注入测试。
- 主角名变更后 vision_dump 仍触发。
- 新非人实体名注入后 direct_revelation_monologue 触发。
- 弯引号覆盖测试（已存在，保留）。

---

## 执行顺序

1. 建立本 task 文档（当前步骤）。
2. Review task 文档。
3. 实现 RuleAuditor 动态关键词接口 + repository 辅助查询。
4. 实现 ground truth 导出脚本 + 机器预标。
5. 人工/半人工标注 Ch30–Ch32（用户参与终审）。
6. 基于 ground truth 校准阈值。
7. 升级 reeval 脚本输出对比表。
8. 新增/更新单测并通过。
9. 跑 `ruff check src/ tests/`。
10. 跑校准后的 reeval，生成 `archive/v7/reports/task-170m-exposition-carrier-recalibration-report.md`。
11. 回填 `archive/v7/tasks/170m-exposition-carrier-recalibration-DONE.md`。
12. 更新 `docs/STATUS.md`、`tasks/V7-README.md`、`archive/v7/tasks/170-literary-quality-remediation-README.md`、`README.md`。

---

## 风险与回退

| 风险 | 缓解 |
|------|------|
| 从 setting_snapshots 抽关键词噪音大 | 用 frequency + setting_key 层级过滤，只取出现 ≥2 次且非通用词的设定 |
| 非人实体识别不准 | 先允许硬编码 fallback + 外部注入，后续可接 LLM 分类但不依赖 |
| 人工标注成本高 | 机器预标 + 用户只做终审；如时间有限，先标 1 章做方向性验证 |
| 阈值调整过拟合 ground truth | 只调 1–2 个最敏感阈值，保留基线词表，文档记录调整依据 |

---

## 交付物

- 代码：
  - `src/songyan/agents/rule_auditor.py`
  - `src/songyan/db/review_repo.py` 或 `src/songyan/db/literary_repo.py`
- 脚本：
  - `scripts/run_170m_ground_truth_export.py`
  - `scripts/run_170m_reeval.py`（或升级 `run_170l_reeval.py`）
- 数据：
  - `.tmp/ground_truth/task170m_ch30_ch32_ground_truth.jsonl`
- 单测：
  - `tests/test_rule_auditor.py`
- 报告：
  - `archive/v7/reports/task-170m-exposition-carrier-recalibration-report.md`
- DONE 文档：
  - `archive/v7/tasks/170m-exposition-carrier-recalibration-DONE.md`

---

## 下一步（按路径 B 纪律）

本 task 完成后，根据校准结果决策：
- 若校准后 `exposition_carrier_count` 显著下降且 P/R/F1 可信 → 重新评估 170l 文学失败是否主要是 voice/ai_tone 问题，路径 B 升级方向可聚焦声纹工程。
- 若校准后 `exposition_carrier_count` 仍然很高且检测器召回充分 → 确认 exposition 约束确实失效，路径 B 升级或目标降级。
- 无论哪种结果，都必须在 `archive/v7/tasks/170m-exposition-carrier-recalibration-DONE.md` 中给出量化结论。
