# Task 171a: 文学量具效度重建报告（R0）

> 生成时间: 2026-07-10
> 对应框架: `docs/reports/v7-literary-framework-review.md` §8 B 组 + §7.1 R0
> 状态: **代码侧（B1/B4/B5）已落地并验证；效度量化（B2/B3 的 ≥2 体裁盲标 P/R/F1）拆分至 171a-1 续做**

---

## 1. 目标回顾（框架 §8 B 组）

| 编号 | 验收项 | 本报告状态 |
|---|---|:---:|
| B1 | voice/exposition 构念重定义落地 | ✅ 已落地 |
| B2 | 盲标 ground truth（≥2 体裁、对话密集+稀疏） | ⏳ 拆分至 171a-1 |
| B3 | voice/exposition 量具 P/R/F1 ≥ 0.8 | ⏳ 拆分至 171a-1 |
| B4 | 体裁解耦通电（动态注入 + 删硬编码 + 消灭死代码） | ✅ 已落地 |
| B5 | voice 归因召回修复（不再恒 0） | ✅ 已落地并实证 |

---

## 2. 已落地改动（代码侧）

### 2.1 B4 体裁解耦通电

- **删除硬编码主角名作默认值**：`rule_auditor.py` 的 `_DEFAULT_CHARACTER_NAMES` 从 `{"林渊","宋晚","苏晚"}` 改为**空集**；旧值保留为 `_LEGACY_SCIFI_CHARACTER_NAMES` 仅供历史参考，不参与检测。未注入角色名时 `vision_dump` 不再误报到写死人名（维度不计分，而非误判）。
- **消灭死代码**：`LiteraryKeywordRepository.load_exposition_keywords`（`literary_repo.py`）此前全仓零调用点。现由 `workflows/_nodes.py` 新增 `_load_literary_keywords(project_id)` 调用，在 **2 个关键 `run_rule_audit` 调用点**（`rule_auditor_node` 主检测 + `revision_handler_node` 复检）注入项目实际 `character_names`/`setting_keywords`/`non_character_keywords`。第 3 处调用点（rewrite 内 hook-only 结构检查）只读 `has_opening_hook`/`has_ending_hook`，不涉及 voice/exposition，故不注入。
- **安全回退**：`_load_literary_keywords` 任何异常都回退空集并 debug 日志，绝不阻断生成管线。

### 2.2 B5 voice 归因召回修复

`detect_human_voice_homogeneity` 说话人归因新增两类句式（补齐 170o 遗留短板）：
1. **动作节拍夹引语**（`_nearest_registry_name`）：`林渊皱眉。"…"` / `"…"林渊转身` 等无 speech-verb 句式，用注册表就近绑定，**before 窗口优先**（引语前的动作主体是说话人），仅 before 无名时回退 after。仅在提供注册表时启用，避免误绑定。
2. **代词就近继承**（`_DIALOGUE_PRONOUN_CUES`）：`"…"他又说` 类纯代词提示，继承上一位具名说话人。
3. 归因窗口 30/40 → **60/60 字符**，覆盖较长动作节拍。

### 2.3 B1 构念重定义

- **voice 仅在"对话承载章"计分**：`detect_human_voice_homogeneity` 新增章级对话密度门（`_VOICE_QUOTE_RE`，`min_chapter_quotes=2`）——全章引语过稀（单人解谜/意识流/纯叙事）直接返回空，视为"voice 不适用"，不把"无对白可比"误判为"声纹同质"。真正的多角色区分度仍由下游"≥2 具名说话人 + 各 ≥2 句"判定。
- exposition 构念（信息融合度）沿用 170i/170m 的 earned/cost/conflict cue 结构信号 + 171a 动态项目关键词（去 SF 硬编码），本次未改判据逻辑、只改关键词来源。

---

## 3. 实证：注入路径在真实 prose 上改变结果

在 **170p 验证 DB**（`.tmp/task170p_validation.db`，seeding gap 修复后 `characters` 表含 4 角色：林渊/老雷/指挥官/赵海）上，对 Ch1–Ch5 accepted 正文对比"注入 vs 不注入"：

| Ch | voice(未注入) | voice(注入) | exposition(未注入) | exposition(注入) |
|---:|:---:|:---:|:---:|:---:|
| 1 | 0 | 0 | 4 | 4 |
| **2** | **0** | **1** | 1 | 2 |
| 3 | 0 | 0 | 1 | 1 |
| 4 | 0 | 0 | 0 | 0 |
| 5 | 0 | 0 | 4 | 4 |

**关键结论**：
1. **Ch2 voice 0→1**：注入项目角色注册表后，此前无法归因的配角对白被检出——证明 171a 的"注入 + 170p seeding"组合让 voice 量具在真实 prose 上从死代码变为可动。
2. **对照 170i DB**（seeding gap 修复前）：`characters` 表仅 1 人（林渊），31 章 accepted，voice 恒 0——正是"量具与生成被同一数据缺口卡死"的实证。171a（注入）+ 170p（seeding）缺一不可。
3. voice 命中在 Ch1–5 仍稀疏（仅 Ch2 翻转）：因开局章动作/设定为主、多角色对白少，符合"voice 仅在对话承载章计分"的构念，非缺陷。

---

## 4. 单测

`tests/test_rule_auditor.py` 新增 4 个 171a 用例（全绿）：
- `test_171a_action_beat_attribution`：动作节拍夹引语归因。
- `test_171a_pronoun_carry_attribution`：代词就近继承。
- `test_171a_action_beat_speaker_is_preceding_actor_not_next`：before 优先（不误取下一位说话人）。
- `test_171a_dialogue_sparse_chapter_not_scored`：对话稀疏章返回空。

`tests/test_rule_auditor_dynamic_keywords.py`：`test_default_character_names_still_work` 改判为 `test_hardcoded_names_not_scored_without_injection`（旧行为是被 171a 消除的失真）。

`ruff check` 通过；`tests/test_rule_auditor.py` + `tests/test_rule_auditor_dynamic_keywords.py` 91 passed。

---

## 5. 未完成部分（诚实拆分至 Task 171a-1）

B2/B3 的**量化效度**需要两项本任务无法即时满足的前置：
1. **≥2 体裁 prose 语料**：磁盘现有真实 prose 全为 scifi（170b/f/h/i/p DB），无第二体裁语料——需小样本 live 生成。
2. **盲标 ground truth**：需遮机器分的人工盲标（agent provisional 标注可先行，但 B3 的可信 P/R/F1 应有人工终审）。

**决定**：不silently 降级 B3。将"≥2 体裁盲标 GT + P/R/F1≥0.8 量化"拆为 **Task 171a-1**，在其中：① 生成第二体裁小样本；② 用 `scripts/run_170m_*` 脚手架扩为体裁无关盲标导出 + reeval；③ 产出 voice/exposition 的 P/R/F1。171a 的代码侧（B1/B4/B5）已达到"量具可动、注入生效、召回句式补齐"，为 171a-1 的量化提供了可信被测对象。

---

## 6. 出口判定

- **171a 代码侧（B1/B4/B5）：达标**——量具体裁解耦通电、voice 归因召回句式补齐、构念重定义落地，并在真实 prose 上实证注入改变结果、消灭死代码与硬编码。
- **171a 效度量化（B2/B3）：转 171a-1**——需第二体裁语料 + 盲标，属数据/人工前置，非代码问题。
- **对 Ch200 主线无影响**：171a 全程不阻塞 Task 171（文学=观测）。
