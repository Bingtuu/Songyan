# Task 170p：修复 seeding gap — SettlementExtractor 新配角自动入库 — DONE

> **专项**: 文学提质专项（`tasks/170-literary-quality-remediation-README.md`）
> **类型**: 数据层根因修复（voice 前置）
> **优先级**: P0
> **依赖**: Task 170o 已完成（voice 量具归因校准，暴露 seeding gap）
> **状态**: ✅ **已完成**
> **负责人**: songyan-agent

---

## 背景与根因

Task 170o 修好 voice 量具（`detect_human_voice_homogeneity`）说话人归因后，真实正文仍恒 0。DB 直查确认根因在**数据层**：

```
characters 表整个 Ch1–Ch32 只有 1 行：('林渊', 1)
SettlementExtractor._apply：if update.character_id not in valid_char_ids → skip（只 UPDATE，从不 INSERT 新配角）
→ 陈薇/老雷等配角永不入库
→ 声纹卡（DialogueStyleCard 只为已存在角色生成）与 voice 量具（需 ≥2 具名人类角色）对配角双双失效
```

即 **voice 量具与 voice 生成质量被同一个 seeding gap 卡住**。170e 只补了主角（`ensure_protagonist_character`），配角缺口未闭合。

## 方案（用户决策）

用户选择 **扩展 settlement 由 LLM 识别新角色**、**每章 accept 后触发**。鉴于此路径触及事务关键写路径且有 hallucination 风险，落地时施加强证据门禁与幂等保护：

1. **模型层**：新增 `NewCharacter`（name / role_type / source_quote / background）+ `StateSettlement.new_characters`。
2. **提取层**：新增 SettlementExtractor 工艺卡 **1.0.3**，指示 LLM 登记"本章首次出场的具名配角/反派"，附 source_quote 证据；`_build_new_character` 解析、`_build_state_settlement` 装配。
3. **证据门禁**（`_validate._filter_new_characters`，与 `new_setting.source_quote` 同纪律，就地剔除、不阻断整章）：
   - name 长度 2–6、非代词/泛称停用词（他/她/对方/众人/声音/投影…）；
   - name 必须在正文中真实出现（LLM 不得凭空捏造）；
   - source_quote 必须能在正文模糊匹配；
   - 去重已存在角色（幂等）；
   - 同一结算内 name 去重。
4. **写入层**（`_apply._apply_core`）：在 `character_updates` 之前**幂等 INSERT** 新配角，**绑定同一事务 conn**（满足 INSERT-only + 事务纪律），新建 ID 加入 `valid_char_ids` / `role_type_by_id`，使**同章** update 也可引用新角色。

## 关键设计约束（守 AGENTS.md）

- **INSERT-only + 事务**：新角色 `CharacterRepository.create(character, conn=c)` 绑定 settlement 事务，随章一起提交/回滚。
- **Agent 边界**：SettlementExtractor 仍只做结算提取与写入，未新增 Agent/节点。
- **证据优先**：无正文/source_quote 证据的候选一律过滤并记 `settlement.new_character_filtered` diagnostic。
- **幂等/可回退**：同名不重复入库；工艺卡 default 1.0.2 → 1.0.3，1.0.2 保留可回退；无 `new_characters` 字段的旧数据行为不变（空数组）。

## 改动清单

| 文件 | 改动 |
|---|---|
| `src/songyan/models/settlement.py` | 新增 `NewCharacter`；`StateSettlement.new_characters` |
| `src/songyan/models/__init__.py` | 导出 `NewCharacter` |
| `src/songyan/agents/settlement_extractor/__init__.py` | `_build_new_character`；`_build_state_settlement` 装配；`_validate_settlement` 传 `existing_character_names` |
| `src/songyan/agents/settlement_extractor/_validate.py` | `_filter_new_characters` 证据门禁 + 停用词表；`_validate_settlement` 新参数 |
| `src/songyan/agents/settlement_extractor/_apply.py` | `_apply_core` 幂等 INSERT 新配角（绑定事务，加入 valid_char_ids） |
| `prompts/cards/settlement_extractor/1.0.3.yaml` | 新卡：new_characters 提取规则 + 示例 |
| `prompts/cards/settlement_extractor/_manifest.yaml` | default_version 1.0.2 → 1.0.3 |
| `tests/test_170p_new_character_seeding.py` | 15 个新单测（解析/门禁/DB INSERT/幂等/validate 集成） |

## 验证

- `ruff check` src/settlement_extractor + models + 新测试：All checks passed。
- `pytest tests/test_170p_new_character_seeding.py`：**15 passed**（含 DB 集成：`test_apply_settlement_inserts_new_characters` 证明陈薇/老雷入库、role_type 正确；`test_apply_settlement_new_character_idempotent` 证明跨章同名不重复）。
- 回归：`tests/test_settlement_extractor.py test_settlement_extractor_task134.py test_settlement_impact.py test_task137_setting_recycling.py test_task138p_character_id_alias.py test_quote_filter.py test_rule_auditor.py tests/models` → **381 passed, 1 xfailed**。
- 工艺卡加载验证：settlement_extractor default 解析为 **1.0.3**，system_prompt 含 `new_characters`。

### 门禁行为实测（单测断言）

| 候选 | 判定 | 原因 |
|---|:---:|---|
| 陈薇（正文有、有引文） | ✅ 入库 | — |
| 老雷（正文有、有引文） | ✅ 入库 | — |
| 他（代词） | ✂️ 过滤 | name_length_invalid / pronoun |
| 虚构者（不在正文） | ✂️ 过滤 | name_not_in_content |
| 林渊（已存在） | ✂️ 过滤 | already_exists |
| 韩墨×2（同结算重复） | ✂️ 去重 | duplicate_in_settlement |

## 结论与影响

1. **seeding gap 已闭合**：配角在首次具名出场当章即被证据门禁校验后入库，声纹卡与 voice 量具从此有落点。
2. **不改变既有 blocker 结论**：这是数据层修复；voice/exposition 的 LLM rubric 是否真正提升，需在**新的、配角已入库的生成样本**上复评（见下）。
3. **voice 量具（170o）+ 配角入库（170p）现已成对可用**：注册表齐全后，`detect_human_voice_homogeneity` 可对配角对白做同质化检测。

## 后续（建议）

1. **用配角入库后的新样本复评 voice**：跑一段中段窗口（enforce observe），确认 `characters` 表出现配角、DialogueStyleCard 为配角生成、`detect_human_voice_homogeneity` 能出真实分布；再更新 mid-term-review 的 voice 结论（当前"能力边界"判断需用配角齐全的样本重新验证）。
2. **修 170o DONE 中登记的 2 个 pre-existing 测试 collection error**（`test_non_character_voice_cards.py` / `test_revision_handler_literary.py`），恢复分模块 pytest 全量可收集。
3. **观察 new_characters 误报率**：长跑中抽查 `settlement.new_character_created` / `settlement.new_character_filtered` 日志，若 LLM 过度登记临时/无名角色，收紧工艺卡或门禁。

## 交付物

- `src/songyan/models/settlement.py`、`src/songyan/models/__init__.py`
- `src/songyan/agents/settlement_extractor/__init__.py`、`_validate.py`、`_apply.py`
- `prompts/cards/settlement_extractor/1.0.3.yaml`、`_manifest.yaml`
- `tests/test_170p_new_character_seeding.py`
- `tasks/170p-settlement-new-character-seeding-DONE.md`

---

## 附加：修复合并遗留的 2 个 broken 测试（同批次）

用户要求同步修复 170o 附带登记的 2 个 pre-existing collection error。查证结论：合并 `462c494` 把**测试文件**带进来了，但**实现从未入库**（`git log -S` 全历史无该符号定义），且**无任何 pipeline 调用点**——即 170g Phase2 / 170h 的两个 helper 只有测试契约存活，实现与接线都在合并中丢失。按测试契约重建实现：

### 1. `_build_non_character_voice_cards`（`src/songyan/workflows/_helpers.py`）
- 为非角色声源（建造者/残影/守门人/舰队之手 等 `_NON_CHARACTER_VOICE_NAMES`）构造确定性 `DialogueStyleCard`，`character_id="voice-{name}"`。
- 跳过未知名字与已存在角色；填充 `sentence_length_preference="medium"`、`common_openers`、`anger_expression`、`social_role_speech_pattern` 等风格字段。
- 对齐 `tests/test_non_character_voice_cards.py`（4 用例）。

### 2. `_build_literary_issues` + 扩展 `_readability_driven`（`src/songyan/agents/revision_handler/__init__.py`）
- `_build_literary_issues`：把 `exposition_carrier_matches`（最多 3 条，按 carrier_type 映射到 SHOW_DONT_TELL / INFO_DUMP / EXPOSITION / DIALOGUE_DISTINCTNESS）+ LLM 文学维度低分（voice / exposition / dialogue_distinctness / info_dump < 5.0）转成 patch issue。
- `_readability_driven`：新增触发条件 `exposition_carrier_count ≥ 1` 与文学维度低分。
- 对齐 `tests/test_revision_handler_literary.py`（16 用例）。

**验证**：`tests/test_non_character_voice_cards.py tests/test_revision_handler_literary.py` → 20 passed；`ruff` 通过；回归 `tests/test_rule_auditor.py test_revision_handler.py test_170p_new_character_seeding.py` → 197 passed。

> **接线缺口（登记，非本任务修）**：这两个 helper **目前无 pipeline 调用点**（`_build_non_character_voice_cards` 未接入 Writer 上下文组装、`_build_literary_issues` 未接入 RevisionHandler 主流程）。合并丢失了接线；测试只覆盖函数行为。是否接线取决于 170g/h/i 文学 patch 路径是否要在阶段 Z 启用——列后续决策项，不在 170p 擅自接主流程（守"不做全自动 LLM 改写闭环"边界）。

---

## 附加：170p 效果验证（小窗口真实生成）

新增 `scripts/run_170p_validation.py`：Ch1–Ch5 小窗口、observe 门禁、结算走 default 1.0.3，跑完后 `--check` 查 `characters` 表配角入库数 + 逐章用 170o `detect_human_voice_homogeneity`（注册表 gating）验证 voice 量具落点。

> 运行结果回填见下（真实 DeepSeek 生成）。

### 运行结果（`run-bcf3b8f1`，Ch1–Ch5，observe，DeepSeek 真实生成）

**数据层闭环 ✅ 成立**：

| 指标 | 修复前（170i DB） | 170p 后（本次） |
|---|:---:|:---:|
| `characters` 表角色数 | 1（仅林渊） | **4**（林渊 + 老雷/指挥官/赵海） |
| `character_states` 覆盖角色 | 1 | **4** |
| 配角/反派入库数 | 0 | **3** |

- Ch1–Ch5 completed=[1,2,3,4,5]、failed=[]、无 AutoHalt。
- 配角在首次具名出场当章即被证据门禁校验后入库（结算卡 1.0.3 生效）。
- 正文中配角确有对白：Ch1 林渊×25/指挥官×15/老雷×5，Ch2 林渊×23/老雷×13/赵海×10 …（引语邻近含角色名）。**seeding gap 已实证闭合**。

**voice 量具落点 ⚠️ 部分闭合，暴露 170o 检测器新短板**：

- 逐章 `detect_human_voice_homogeneity`（注册表 gating，registry=4）命中均为 **0**。
- 但这**不是**"voice 已区分"的可信结论——诊断发现检测器**自身说话人归因率过低**：Ch1 共 30 条引语，检测器只归因 8 条（post=5 + voice_of=3），**漏 22 条（73%）**。原因：检测器要求"名字+说/道"紧邻引语，而真实正文大量用**动作节拍夹在名字与引语之间**或**跨句归因**，正则抓不到 → 每个合并场景很难凑齐"≥2 说话人×≥2 句" → 0 比较 → 0 命中（假阴性风险仍在）。

**结论**：
1. **170p 目标达成**：配角入库 + 状态快照 + 声纹卡落点，数据层 seeding gap 已闭合并经真实生成验证。
2. **voice 量具仍需再校准**（新增短板，非 170p 引入）：170o 的说话人归因对真实对白格式覆盖不足（紧邻 speech-verb 假设太强），需支持"动作节拍归因""跨句就近实名绑定"，否则即使配角齐全，homogeneity 仍可能假阴性。建议列 **170q**：voice 量具说话人归因二次增强 + 用本 DB（`.tmp/task170p_validation.db`，配角齐全）做召回率回归。
3. **不改变文学 blocker 结论**：这是数据层 + 量具修复，voice 的 LLM rubric 是否真正提升仍需中段窗口大样本人工/LLM 复评。
