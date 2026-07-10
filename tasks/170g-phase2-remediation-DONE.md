# Task 170g Phase2: 文学质量卡点工艺补丁与小样本复评 — DONE

> **专项**: 文学提质专项（`tasks/170-literary-quality-remediation-README.md`）
> **类型**: 工程补丁 + 小样本验证
> **优先级**: P0（决定 170g 能否从 blocker 改判并重新评估 Ch200 入口）
> **依赖**: Task 170g 改判 blocker 已完成
> **状态**: 🔴 **工艺补丁已落地；小样本复评已完成；结论：未达标，保持 170g blocker，不放行 Task 171 Ch200**
> **负责人**: songyan-agent
> **生成日志**: `.tmp/run_170g_phase2.log`
> **隔离 DB**: `.tmp/task170g_phase2.db`
> **复评报告**: `docs/reports/task-170g-phase2-remediation-reeval-report.md`（已生成）
> **Run ID**: `run-ac99288a`（Ch29–Ch32，因 Ch31 settlement GBK 编码失败手动 accept `v-31-8-ddd9baaa`）

---

## 结论

Task 170g Phase2 在 V7 边界内（不新增 Agent/Workflow 节点）完成了 5 项最小可行工艺补丁：

1. **RuleAuditor exposition 检测升级**：新增 direct_revelation_monologue / protagonist_summary_tell / info_delivery_dialogue 三类模式，堵住模型换壳绕过载体约束的漏洞。
2. **非角色声纹卡补漏**：为建造者/残影/前代钥匙/舰队之手/意识碎片/守门人生成伪 `DialogueStyleCard`，让中段世界观揭示依赖的非人实体声音进入 Writer 声纹约束。
3. **CreativeDirector 世界观揭示正路径模板**：在 `style_constraints` 中强制要求高概念信息通过"锁死的门 / 失效的协议 / 他人代价"三类场景模板呈现，禁止直接说明。
4. **GoalPlanner 信息交付校验**：新增 `information_events` 字段，要求每个信息点必须映射到 `target_events` 中的动作/冲突/失败事件；禁止说明文式目标动词。
5. **RevisionHandler 文学 patch 路径**：把 `exposition_carrier_count` 和 LLMAuditor `dialogue_distinctness` / `info_dump` 低分接入 readability 专精修订，自动生成"讲述→动作承载"patch issue。

所有改动均保持 Agent 边界：Writer 只做初稿、RevisionHandler 只做 patch、LiteraryAuditor 只诊断、GoalPlanner/CreativeDirector 只输出结构化规划。

**Phase2 复评结论**：Ch29–Ch32 隔离 DB 重跑（run `run-ac99288a`）并复评后，**未达 pass 线**：

| 维度 | 窗口均值 | 目标 | 判定 |
|---:|:---:|:---:|:---|
| voice | **1.75** | ≥3.0 | ❌ 塌陷（低于 170b 基线 1.8） |
| exposition | **2.25** | ≥3.0 | ❌ 未达标（较 170g 初评 2.0 微升，但仍偏说明性） |
| pacing | **3.25** | ≥3.0 | ✅ 保持达标 |
| 5 维均值 | **2.55** | ≥3.0 | ❌ 未达标 |
| exposition_carrier_count | **0** | ≤1 | ✅ 达标 |
| T9 硬红线 | **0/0** | 0/0 | ✅ 达标 |
| 机器/LLM 偏差大章数 | **0/4** | <3 分 | ✅ 量具可信 |

因此 **170g 维持 blocker，Task 171 Ch200 继续冻结**。本次 Phase2 证明：在 V7 当前边界内（不新增 Agent/Workflow 节点、不做全自动 LLM 改写闭环）的 5 项最小工艺补丁，能够清除 exposition 载体硬灌形式并稳住 pacing，但**不足以让 voice 和 exposition 本质提升到 pass 线**。下一步必须在"继续迭代更小补丁"与"升级到结构性改写/声源工程方案"之间做选择。

**小样本复评目标**：在 Ch29–Ch32 隔离 DB 重跑并复评，达到 voice ≥3.0、exposition ≥3.0、窗口 5 维均值 ≥3.0、exposition_carrier_count ≤1、T9 0/0。若达标，方可把 170g 改回 observation/pass 并重新评估 Task 171 Ch200 入口；若未达标，保持 blocker，继续迭代或升级到方案 B。

---

## 工程改动清单

### 1. RuleAuditor exposition 检测升级（Task 2）

**Files:**
- `src/songyan/agents/rule_auditor.py`
- `src/songyan/models/review.py`
- `tests/test_rule_auditor.py`

**改动：**
- `ExpositionCarrierMatch.carrier_type` 枚举新增：
  - `direct_revelation_monologue`：建造者/残影/前代/碎片/守门人/意识为主语的大段说明性独白。
  - `protagonist_summary_tell`：主角用"他明白了/意识到/知道了/这一切意味着"直接总结世界观。
  - `info_delivery_dialogue`：单次引语内连续 >80 字说明且无动作/疑问打断的设定解释。
- `repeated_revelation_beat` 计数扩展为同一章内出现 2 次及以上相同揭示动作。
- 新增单测 4 个，覆盖三类新模式。

**验证：**
```powershell
python -m pytest tests/test_rule_auditor.py -q  # 57 passed
ruff check src/songyan/agents/rule_auditor.py src/songyan/models/review.py tests/test_rule_auditor.py
```

### 2. 非角色声纹卡补漏（Task 3）

**Files:**
- `src/songyan/workflows/_helpers.py`
- `prompts/cards/writer/1.1.0.yaml`
- `prompts/cards/writer/1.2.0.yaml`
- `tests/test_non_character_voice_cards.py`

**改动：**
- 新增常量 `_NON_CHARACTER_VOICE_NAMES` 与 `_NON_CHARACTER_VOICE_STYLES`，覆盖：建造者、建造者声音、残影、前代钥匙、前六代钥匙、舰队之手、意识碎片、守门人。
- 新增 `_build_non_character_voice_cards(...)`：当最近摘要 `characters_appeared` 中出现上述关键词且该名字不在常规 Character 表时，生成 `DialogueStyleCard` 注入 Writer。
- Writer 1.1.0/1.2.0 `dialogue_style_cards` 说明增加：非人实体声源也必须有可辨语言指纹。
- 新增单测 4 个。

**验证：**
```powershell
python -m pytest tests/test_non_character_voice_cards.py tests/test_context_manager.py -q  # 81 passed
ruff check src/songyan/workflows/_helpers.py tests/test_non_character_voice_cards.py
```

### 3. CreativeDirector 世界观揭示正路径模板（Task 4）

**Files:**
- `prompts/cards/creative_director/1.0.6.yaml`
- `prompts/cards/creative_director/_manifest.yaml`
- `tests/test_prompt_loader.py`

**改动：**
- 在 `style_constraints` 中新增 `【世界观揭示模板】` 要求：
  - **锁死的门**：主角试图打开/通过/破解出口，发现被从另一侧锁死 → 被迫意识到牢笼/规则/代价。
  - **失效的协议**：主角调用系统功能，系统返回错误/异物 → 从失败反馈反推规则。
  - **他人代价**：通过另一角色的失败/损伤/死亡，让主角目睹规则真实运行。
- 要求每个高概念信息必须包含 `concept_name`、`template_id`（locked_door/failed_protocol/others_cost）、`presentation_action`、`failure_or_cost_event`、`environmental_consequence`。
- 禁止只写概念名而不写动作/失败/后果。
- 要求每个 `information_events` 必须对应 `chapter_goal_json` 中 `target_events` 的动作/冲突/失败事件。
- 更新 manifest 描述；新增单测验证 prompt 包含模板关键词。

**验证：**
```powershell
python -m pytest tests/test_prompt_loader.py -q  # 20 passed
```

### 4. GoalPlanner 信息交付校验（Task 5）

**Files:**
- `prompts/cards/goal_planner/1.1.0.yaml`
- `src/songyan/models/chapter.py`
- `src/songyan/db/schema.sql`
- `src/songyan/db/repository.py`
- `src/songyan/db/migrations.py`
- `src/songyan/agents/goal_planner.py`

**改动：**
- Prompt 输出 JSON 新增 `information_events` 字段。
- `target_events` 禁止以"揭示/解释/告诉读者/说明/交代/展现设定/补充世界观/让读者知道"为动词。
- 要求每个 `information_events` 必须映射到 `target_events` 中的动作/冲突/失败事件。
- `ChapterGoal` 模型新增 `information_events: list[str]`。
- `chapter_goals` 表新增 `information_events TEXT DEFAULT '[]'` 列。
- `ChapterGoalRepository` 读写该列；迁移函数 `_migrate_chapter_goal_information_events` 加入 `init_schema` 与 `run_migrations`。
- `_build_chapter_goal` 解析并清洗 `information_events`。

**验证：**
```powershell
python -m pytest tests/test_prompt_loader.py tests/db -q  # 158 passed
ruff check src/songyan/models/chapter.py src/songyan/db/repository.py src/songyan/db/migrations.py src/songyan/agents/goal_planner.py
```

### 5. RevisionHandler 文学 patch 路径（Task 6）

**Files:**
- `src/songyan/agents/revision_handler/__init__.py`
- `prompts/cards/revision_handler/1.1.0.yaml`
- `tests/test_revision_handler_literary.py`

**改动：**
- `_readability_driven` 触发条件扩展：
  - `RuleAuditResult.exposition_carrier_count > 0`
  - LLMAuditor `dialogue_distinctness < 5.0` 或 `info_dump < 5.0`
- `_readability_metrics_from_report` 新增 `exposition_carrier_count`、`dialogue_distinctness_score`、`info_dump_score`。
- 新增 `_build_literary_issues(...)`：
  - 从 `exposition_carrier_matches` 前 3 处生成 `SHOW_DONT_TELL` patch issue。
  - 复用 LLMAuditor 已有 `DIALOGUE_DISTINCTNESS` / `INFO_DUMP` / `SHOW_DONT_TELL` issue。
  - 维度分低但无 issue 时生成兜底 issue。
- RevisionHandler 1.1.0 prompt 增加说明文载体、对话声纹塌陷指标与改写示例。
- 新增单测 6 个。

**验证：**
```powershell
python -m pytest tests/test_revision_handler_literary.py tests/test_revision_handler.py -q  # 94 passed
ruff check src/songyan/agents/revision_handler/__init__.py tests/test_revision_handler_literary.py
```

---

## 小样本复评执行摘要（Task 7）

### 生成

- 基线来源：复制 `.tmp/task170g_quick.db` → `.tmp/task170g_phase2.db`（保留 Ch1–Ch28 上下文）。
- 重置 Ch29–Ch32 为 `draft` 并删除旧 accepted head。
- 运行迁移以补齐 `chapter_goals.information_events` 列。
- 命令：
  ```powershell
  DATABASE_URL="sqlite:///.tmp/task170g_phase2.db" `
  START_CHAPTER="29" END_CHAPTER="32" GATE_MODE="observe" `
  python scripts/run_170g_generation.py
  ```

### 复评

- 命令：
  ```powershell
  DATABASE_URL="sqlite:///.tmp/task170g_phase2.db" `
  ASSESS_START="29" ASSESS_END="32" `
  python scripts/run_170g_reeval.py --project-id 6c38c19edb3d4b83ba6963ba78e1e2f0
  ```
- 报告输出：`docs/reports/task-170g-phase2-remediation-reeval-report.md`。

### 结果

| 维度 | Ch29 | Ch30 | Ch31 | Ch32 | 窗口均值 | 目标 |
|---:|:---:|:---:|:---:|:---:|:---:|:---:|
| voice | 3 | 2 | 1 | 1 | **1.75** | ≥3.0 |
| exposition | 2 | 3 | 2 | 2 | **2.25** | ≥3.0 |
| pacing | 3 | 4 | 3 | 3 | **3.25** | ≥3.0 |
| ai_tone | 2 | 3 | 2 | 2 | **2.25** | — |
| concept | 3 | 4 | 3 | 3 | **3.00** | — |
| **均值** | 2.60 | 3.20 | 2.20 | 2.20 | **2.55** | **≥3.0** |

- exposition_carrier_count（合计）：**0**（未检测到 info_stream / consciousness_tentacle / vision_dump / faq_dialogue / repeated_revelation_beat / direct_revelation_monologue / protagonist_summary_tell / info_delivery_dialogue 任一模式）
- T9 硬红线：元标记泄漏 **0**、整段落重复 **0**
- 机器/LLM 偏差大章数：**0 / 4**
- 与 170g 初评对比：voice 1.75→1.75（持平），exposition 2.0→2.25（微升 +0.25），pacing 3.25→3.25（持平），窗口均值 2.45→2.55（微升 +0.10）

### 出口判定

- [ ] 小样本达标 → 扩展 Ch28–Ch40 enforce 复评，全部满足后改判 170g 并重新评估 Ch200。
- [x] **小样本未达标 → 保持 170g blocker，继续迭代或升级到方案 B（结构性改写支持）。**

---

## 为什么 Phase2 补丁未让质量提升到 pass 线

### 观察事实

1. **显性硬灌被压住了**：`exposition_carrier_count` 从 170f Stage 2 的多处显著模式 + 170g 初评的 1 处，降至 Phase2 的 **0 处**。RuleAuditor 新增的三类深层模式（direct_revelation_monologue / protagonist_summary_tell / info_delivery_dialogue）也没有触发。
2. **pacing 稳定达标**：3.25，说明 `scene_interaction` 段落约束和动作承载信息的指令被遵守。
3. **voice 没有改善**：1.75，与 170g 初评持平，且低于 170b 基线 1.8。
4. **exposition 本质仍是说明性**：2.25，仅比 170g 初评 2.0 微升 0.25，距 3.0 还差 0.75。
5. **模型学会了换壳**：用"建造者声音 / 前六代残影 / 前代钥匙"等高频非人实体进行大段世界观独白，主角则退化为"听懂了 / 明白了 / 知道了"的总结容器。这不是"载体形式"问题，而是**信息生长方式**问题——高概念设定仍被直接投递，而非从动作、失败、代价中自然长出来。

### 卡点拆解

| 卡点 | 根因 | 为什么 Phase2 补丁没打到 |
|------|------|---------------------------|
| **voice 塌陷** | 非人实体（建造者、残影、前代钥匙、舰队之手、守门人）占中段世界观揭示戏份，但 Writer 的 `dialogue_style_cards` 只覆盖 `characters` 表中的常规角色。 | Task 3 的 `_build_non_character_voice_cards` 已补 8 个非人实体声纹卡，但**只补了声纹约束，没解决戏份分配问题**——非人实体仍然是大段世界观输出的"嘴替"，主角和其他人类角色被边缘化。 |
| **exposition 说明性** | CreativeDirector / GoalPlanner 仍把"揭示设定"作为合法章节目标；模型只要换壳成角色独白或主角总结，就能满足"动作承载信息"的表面要求。 | Task 4/5 的正路径模板 + `information_events` 校验在 prompt 层增加约束，但**没有从章节目标层面删除"世界观揭示"类动词**，也没有要求每个信息点必须对应一次失败或代价。 |
| **RevisionHandler 触达不够** | 自动修订最多 2 轮，且 `exposition_carrier_count=0` 时不会触发文学 patch。 | Task 6 的文学 patch 路径依赖代码检测或 LLMAuditor 低分触发；当模型把 exposition 包装成"合法"对话时，触发器不启动。 |
| **量具已够深但生成目标未改** | RuleAuditor 新增模式能识别独白/总结/信息投递，但本次未命中，说明模型已经**避开这些具体句式，改用更隐性的说明性叙述**。 | 这是 LLM 的对抗性绕过：约束层级停留在"句式黑名单"，未触及"这一章到底要让什么发生"。 |

### 为什么最初会建议 observation / 放行 Ch200

原 170g 初评后，工程侧约束（`exposition_carrier`）确实把显性硬灌从多处压到 1 处，T9 0/0，量具偏差 0/4，pacing 达标。这些信号容易让人误判为"提质有效、残余债轻微"。改判为 blocker 是因为：

- **pass 线是自己定的**：voice ≥3.0 / exposition ≥3.0 / 窗口均值 ≥3.0，170g 初评一项都不满足。
- **voice 没提升反而微降**：从 1.8→1.75，说明核心问题（角色声纹塌陷）没解决。
- **exposition 只是换壳**：载体硬灌减少，但说明性本质未变，不能把"约束生效"等同于"质量达标"。
- **Ch200 是长跑里程碑**：把未解决的 voice/exposition 债带入 100+ 章长跑，缺陷会被放大，后续修复成本更高。

Phase2 的结果进一步验证了这一判断：在 V7 当前边界内追加 5 项补丁后，voice 仍 1.75，exposition 仍远低于 3.0。这说明问题不是"再补一个检测/约束"就能解决，而是需要**结构性升级**。

### 改进路径与工程量评估

在 V7 当前边界内可选的两条路径：

#### 路径 A：继续迭代更细碎的生成侧约束（保守，边际收益递减）

- **进一步收窄 GoalPlanner**：把"揭示/解释/说明/交代/展现设定/补充世界观/让读者知道"等动词加入黑名单，要求每个 `information_events` 必须对应一个 `target_events` 中的失败/代价/冲突，否则重写章节目标。
- **CreativeDirector 强制"失败优先"**：高概念信息必须先写主角尝试某动作并失败，再从失败反馈中让观众/读者推导出设定；禁止先写设定再写动作。
- **Writer 增加"人类角色声纹优先"规则**：限制非人实体单章台词字数 / 独白次数，要求世界观揭示必须由人类角色在冲突中触发。
- **RevisionHandler 降低触发阈值**：把 LLMAuditor `voice` / `exposition` rubric 低分直接接入 readability 路径，不依赖代码检测触发。
- **工程量**：约 1–2 个 Task（GoalPlanner/CreativeDirector prompt 升级 + RevisionHandler 触发条件扩展 + 小样本复评），但基于 Phase2 经验，**预计 voice/exposition 提升幅度有限（可能 +0.2~0.3）**，难以一次性跨过 3.0。

#### 路径 B：结构性改写支持 / 声源工程（突破 V7 边界，工程量大但可能治本）

- **非人实体戏份重构**：把"建造者/残影/前代钥匙"的大段独白拆成**环境线索 + 人类角色互证 + 主角试错代价**。这需要改写既有中段章节的情节结构，而非只改 prompt。
- **引入"场景-信息"正路径模板库**：CreativeDirector 不再只给约束，而是给 2–3 个具体场景模板（如发现日志残片、两个 NPC 对同一事件给出矛盾说法、主角操作设备触发错误反馈），Writer 必须套用模板。
- **声纹机制工程化升级**：把非人实体的"声音"从单条 style 描述升级为包含情绪节奏、词汇偏好、句法特征的 `DialogueStyleCard`，并在 Writer prompt 中明确要求不同非人实体之间必须可区分。
- **可能触及 V8 边界**：题材泛化 / 全自动 LLM 改写闭环 / 新增 Agent/Workflow 节点。
- **工程量**：约 3–5 个 Task，需要真实 LLM 生成验证 + 人工抽读，预计 1–2 周。

### Phase2 最终出口判定

**保持 170g blocker，不放行 Task 171 Ch200。**

理由：
1. voice 1.75 < 3.0，且未较 170b 基线（1.8）提升；
2. exposition 2.25 < 3.0，仅微升，说明性本质未变；
3. 窗口均值 2.55 < 3.0；
4. 机器/LLM 偏差 0/4、T9 0/0、exposition_carrier_count 0，量具可信，因此问题在**生成侧深层结构**，而非量具失真；
5. V7 边界内的最小工艺补丁已被证明边际收益不足，再追加同类补丁的性价比低。

---

## 验证清单

- [x] `ruff check src/ tests/` 通过。
- [x] `python -m pytest tests/test_rule_auditor.py tests/test_prompt_loader.py -q` 通过。
- [x] `python -m pytest tests/db tests/models tests/genres -q` 通过。
- [x] `python -m pytest tests/rag tests/settlement_extractor tests/creative_modes tests/cli -q` 通过。
- [x] `python -m pytest tests/evals tests/integration -q -k "not test_ch1_20"` 通过。
- [x] `python -m pytest tests/test_*.py -q` 通过。
- [x] Ch29–Ch32 Phase2 重生成完成（run `run-ac99288a`，Ch31 因 settlement 输出编码问题失败后手动 accept `v-31-8-ddd9baaa`，复评使用该版本）。
- [x] Ch29–Ch32 Phase2 复评报告产出：`docs/reports/task-170g-phase2-remediation-reeval-report.md`。
- [x] 出口判定回填：**未达标，保持 blocker**。

---

## 交付物

- 代码：
  - `src/songyan/agents/rule_auditor.py`
  - `src/songyan/models/review.py`
  - `src/songyan/workflows/_helpers.py`
  - `src/songyan/models/chapter.py`
  - `src/songyan/db/schema.sql`
  - `src/songyan/db/repository.py`
  - `src/songyan/db/migrations.py`
  - `src/songyan/agents/goal_planner.py`
  - `src/songyan/agents/revision_handler/__init__.py`
- 工艺卡：
  - `prompts/cards/writer/1.1.0.yaml`
  - `prompts/cards/writer/1.2.0.yaml`
  - `prompts/cards/creative_director/1.0.6.yaml`
  - `prompts/cards/creative_director/_manifest.yaml`
  - `prompts/cards/goal_planner/1.1.0.yaml`
  - `prompts/cards/revision_handler/1.1.0.yaml`
- 脚本修复：
  - `scripts/run_170g_reeval.py`（`ExpositionCarrierMatch` 无 `message` 字段的 bug 修复）
- 单测：
  - `tests/test_rule_auditor.py`
  - `tests/test_non_character_voice_cards.py`
  - `tests/test_prompt_loader.py`
  - `tests/test_revision_handler_literary.py`
- 报告（待生成）：`docs/reports/task-170g-phase2-remediation-reeval-report.md`

---

## 关键纪律

- 未达 voice ≥3.0 / exposition ≥3.0 / 窗口均值 ≥3.0 前，**不放行 Task 171 Ch200**。
- 任何主要维度塌陷（<3.0）不得放行阶段 Z。
- 机器/LLM 偏差 ≥3 分（0–10 尺度）的窗口必须标记为"量具可能失真"。
- T9 文本洁净度保持 0/0 硬红线。
