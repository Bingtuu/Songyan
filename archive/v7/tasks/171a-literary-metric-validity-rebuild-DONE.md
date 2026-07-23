# Task 171a: 文学量具效度重建 —— DONE（代码侧达标，B2/B3 拆分至 171a-1）

> **框架**: `docs/reports/v7-literary-framework-review.md` §8 B 组 + §7.1 R0
> **状态**: ✅ **代码侧完成（B1/B4/B5 达标）**；B2/B3（≥2 体裁盲标 P/R/F1）拆分至 **Task 171a-1**
> **报告**: `archive/v7/reports/task-171a-metric-validity-report.md`
> **完成时间**: 2026-07-10

---

## 结论

Task 171a 重建了文学量具的**效度基础**——消除旧框架 E2/E3（量具读数不可信 + 构念建错）与体裁窄化。代码侧三项（B1 构念重定义 / B4 体裁解耦通电 / B5 voice 归因召回）已落地并在真实 prose 上实证；量化效度（B2/B3 的 ≥2 体裁盲标 P/R/F1）因需第二体裁语料 + 盲标，诚实拆分至 Task 171a-1。**全程未阻塞 Ch200 主线，未放宽任何冻结口径。**

---

## 验收对照（框架 §8 B 组）

| 编号 | 验收项 | 状态 | 证据 |
|---|---|:---:|---|
| B1 | voice/exposition 构念重定义 | ✅ | voice 仅在"对话承载章"计分（章级密度门）；exposition 沿用结构信号 + 动态关键词去 SF 硬编码 |
| B2 | ≥2 体裁盲标 ground truth | ⏳→171a-1 | 现有真实 prose 全为 scifi，需第二体裁 live 生成 |
| B3 | voice/exposition P/R/F1 ≥ 0.8 | ⏳→171a-1 | 依赖 B2 语料 + 盲标 |
| B4 | 体裁解耦通电（注入 + 删硬编码 + 消灭死代码） | ✅ | `_DEFAULT_CHARACTER_NAMES` 清空；`load_exposition_keywords` 接线到 2 个调用点；死代码消除 |
| B5 | voice 归因召回修复（不再恒 0） | ✅ | 动作节拍 + 代词继承 + 窗口加宽；170p DB Ch2 voice 0→1 实证 |

---

## 工程改动清单

### `src/songyan/agents/rule_auditor.py`
- `_DEFAULT_CHARACTER_NAMES` 从 `{林渊,宋晚,苏晚}` 改为空集（`_LEGACY_SCIFI_CHARACTER_NAMES` 仅存历史值，不参与检测）。
- 新增 `_DIALOGUE_PRONOUN_CUES`（代词提示语集）、`_VOICE_QUOTE_RE`（章级对话密度门）。
- 新增 `_nearest_registry_name(before, after, registry)`：动作节拍归因，before 窗口优先。
- `detect_human_voice_homogeneity`：新增 `min_chapter_quotes` 参数 + 章级密度门（对话稀疏章返回空）；归因窗口 30/40→60/60；新增动作节拍归因（步骤 4）+ 代词就近继承（步骤 5）。

### `src/songyan/workflows/_nodes.py`
- 新增 `_load_literary_keywords(project_id)`：安全加载项目关键词，异常回退空集、不阻断管线。
- `rule_auditor_node`（主检测）+ `revision_handler_node`（复检）两个 `run_rule_audit` 调用点注入 `character_names`/`setting_keywords`/`non_character_keywords`。
- 第 3 处调用点（rewrite 内 hook-only 结构检查）不注入（只读 hook，不涉 voice/exposition）。
- 新增 `from songyan.db.literary_repo import LiteraryKeywordRepository`。

### 测试
- `tests/test_rule_auditor.py`：新增 4 个 171a 用例（动作节拍 / 代词继承 / before 优先 / 对话稀疏返回空）。
- `tests/test_rule_auditor_dynamic_keywords.py`：`test_default_character_names_still_work` 改判为 `test_hardcoded_names_not_scored_without_injection`（旧行为是被消除的失真）。
- `tests/test_171a_literary_keyword_wiring.py`（新）：`_load_literary_keywords` 安全回退契约 2 用例。

---

## 实证（真实 prose）

170p 验证 DB（seeding 修复后 `characters`=4：林渊/老雷/指挥官/赵海）Ch1–5：**Ch2 voice 0→1（注入后）**，证明"171a 注入 + 170p seeding"组合让 voice 量具从死代码变为可动。对照 170i DB（seeding 前 characters=1）voice 恒 0——两者缺一不可。详见报告 §3。

---

## 验证清单
- [x] `ruff check src/ tests/` 全通过。
- [x] `tests/test_rule_auditor.py` + `test_rule_auditor_dynamic_keywords.py` + `test_non_character_voice_cards.py` + `test_revision_handler_literary.py` + `test_171a_literary_keyword_wiring.py` + `test_170p_new_character_seeding.py`：128 passed。
- [x] `tests/test_108_core_nodes.py` + `test_rewrite_node.py`：28 passed（`_nodes.py` 改动无回归）。
- [x] 真实 prose 集成验证（170p DB Ch1–5，注入 vs 不注入对比）。
- [x] 报告 `archive/v7/reports/task-171a-metric-validity-report.md` 产出。

---

## 出口与下一步
- **171a 代码侧达标**：量具可动、注入生效、召回句式补齐、体裁解耦通电。
- **下一步 Task 171a-1**（已建 spec `archive/v7/tasks/171a-1-metric-validity-quantification.md`）：生成第二体裁小样本 + 盲标 GT + 计算 voice/exposition P/R/F1，补齐 B2/B3。
- 171a 不阻塞 Ch200；171c 提质须待 171a-1 各维度 P/R/F1 达标后，才在达标维度上启动。
