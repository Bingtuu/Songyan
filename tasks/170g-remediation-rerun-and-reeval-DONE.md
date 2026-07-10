# Task 170g: 提质复评出口（Ch200 放行判定）— DONE（改判 blocker）

> **专项**: 文学提质专项（`tasks/170-literary-quality-remediation-README.md`）
> **类型**: 出口验证（终检）
> **优先级**: P0（决定能否放行 Task 171 Ch200）
> **依赖**: 170c + 170d + 170e + 170f 全部 DONE
> **状态**: 🔴 **blocker（不放行 Task 171 Ch200）**
> **负责人**: songyan-agent
> **复评报告**: `docs/reports/task-170g-remediation-reeval-report.md`
> **生成日志**: `.tmp/run_170g_quick.log`
> **隔离 DB**: `.tmp/task170g_quick.db`（小样本快速验证）
> **Run ID**: `run-8660e9d1`（Ch29–Ch32，4/4 success）

---

## 结论

**170g 复评结论：blocker。**

工程侧约束（`exposition_carrier`）有效减少了明显硬灌模式，pacing 保持达标，量具可信且 T9 不漏报；但 LLM rubric 文学维度整体未较 170f 提升，voice 仍扁平（1.75，低于 170b 基线 1.8）、exposition 仍偏说明性（2.0），窗口均值 2.45 未达 170g 自定 pass 线（≥3.0）。

基于“量具优先 + 真实证据”原则，**残余债构成 Ch200 阻断，不放行 Task 171 Ch200 长跑**。必须先针对 voice/exposition 根因完成工艺补丁，并在 Ch28–Ch40 等效窗口复评达到 pass 标准（voice ≥3.0、exposition ≥3.0、窗口均值 ≥3.0）后，方可重新评估 Ch200 入口。

---

## 改判说明（2026-07-08）

原 170g DONE 文档结论为 `observation` 并放行 Ch200。经重新复核：

1. **170g 自定 pass 线未满足**：voice 1.75 < 3.0、exposition 2.0 < 2.5、窗口均值 2.45 < 3.0。
2. **voice 未较 170b 提升**：从 1.8 降至 1.75，属于“提质无效”，符合 blocker 条件。
3. **残余债不是轻微**：voice 塌陷是 170b 判定 Ch200 blocker 的核心原因之一；exposition 虽载体硬灌减少，但说明性本质未变，模型通过“建造者声音/残影独白/前代钥匙灌输/主角总结”换壳绕过约束。
4. **量具可信 ≠ 质量达标**：T9 不漏报、机器/LLM 偏差 0/4 只能说明量具没失真，不能证明 prose 已够好。
5. **Ch200 是长跑里程碑**：把未解决的 voice/exposition 债带入 100+ 章长跑，只会把中段缺陷放大到后段，后续修复成本更高。

因此将结论修正为 **blocker**，并冻结 Task 171 Ch200 启动。

---

## 验证执行摘要

### 1. 工程改动（已落地）

1. **Writer 工艺卡新增 exposition 载体约束**（`prompts/cards/writer/1.1.0.yaml`、`1.2.0.yaml`）：
   - 禁止信息流/意识触须硬灌。
   - 禁止幻象直接播放关键设定。
   - 限制 FAQ 式全知对话（单次连续解释 ≤50 字，问答必须带摩擦）。
   - 强制动作承载信息。
   - 核心设定留白配额（每章最多完整揭示 1 个）。
   - 禁止同一章内反复使用同一揭示节拍。

2. **RuleAuditor 新增 exposition 载体硬灌检测**（`src/songyan/agents/rule_auditor.py`）：
   - 检测 info_stream / consciousness_tentacle / vision_dump / faq_dialogue /
     repeated_revelation_beat 五种模式。
   - 作为观测指标进入 `RuleAuditResult`，轻量扣分，不直接阻断 accept。
   - 新增单测 7 个（`tests/test_rule_auditor.py`）。

3. **复用工具参数化**（避免覆盖 170b/170f 基线产物）：
   - `scripts/run_170g_generation.py`：隔离 DB `.tmp/task170g_ch1_ch40.db`（默认），本次小样本改用 `.tmp/task170g_quick.db`。
   - `scripts/run_170g_reeval.py`：报告 `docs/reports/task-170g-remediation-reeval-report.md`。

### 2. 中段窗口复评策略

完整 Ch1–Ch40 重生成预计耗时数小时，为快速取得 170g 出口证据，改用 **Ch29–Ch32 小样本快速验证**：

- 基线来源：复制 `.tmp/task170f_stage2_ch1_ch32.db` → `.tmp/task170g_quick.db`。
- 重置 Ch29–Ch32 为 draft 并删除旧 versions。
- 使用 `GATE_MODE=observe`（与 170f Stage 2 可比）重新生成。
- 复评命令：
  ```powershell
  DATABASE_URL="sqlite:///.tmp/task170g_quick.db" `
  ASSESS_START="29" ASSESS_END="32" `
  python scripts/run_170g_reeval.py --project-id 6c38c19edb3d4b83ba6963ba78e1e2f0
  ```

> 说明：小样本用 observe 模式是为了速度和与 170f Stage 2 可比；完整 Ch28–Ch40 enforce 复评仍可作为后续补充，但当前以真实小样本证据作为 170g 出口依据。

### 3. 复评数据（来源：`docs/reports/task-170g-remediation-reeval-report.md`）

#### 5 维 rubric（1–5，LLM 初评）

| Ch | ai_tone | voice | concept | exposition | pacing | 均值 |
|---:|:---:|:---:|:---:|:---:|:---:|:---:|
| 29 | 2 | 1 | 3 | 2 | 3 | 2.20 |
| 30 | 2 | 2 | 3 | 2 | 3 | 2.40 |
| 31 | 3 | 2 | 3 | 2 | 4 | 2.80 |
| 32 | 2 | 2 | 3 | 2 | 3 | 2.40 |
| **窗口均值** | **2.25** | **1.75** | **3.00** | **2.00** | **3.25** | **2.45** |

#### 与 170b / 170f Stage 2 对比

| 维度 | 170b 基线 | 170f Stage 2 | 170g 小样本 | 判定 |
|------|:---:|:---:|:---:|:---|
| voice | 1.8 | 2.25 | 1.75 | 未提升，仍塌陷 |
| pacing | 2.4 | 3.25 ✅ | 3.25 ✅ | 保持达标 |
| exposition | 2.1 | 2.0 ❌ | 2.0 ❌ | 数值未提升 |
| concept | 3.2 | 3.0 | 3.0 | 不回退 |
| ai_tone | 2.2 | 2.0 | 2.25 | 略升 |
| 窗口均值 | 2.34 | 2.50 | 2.45 | 未达 ≥3.0 pass 线 |

#### exposition 载体硬灌（代码检测）

| Ch | exposition_carrier_count | 明细 |
|---:|:---:|:---|
| 29 | 1 | consciousness_tentacle ×1 |
| 30 | 0 | — |
| 31 | 0 | — |
| 32 | 0 | — |
| **合计** | **1** | 较 170f Stage 2 的“意识触须/信息流读取 + 幻象播放 + FAQ 式 NPC 问答”多处硬灌显著减少 |

#### T9 硬红线与量具偏差

- T9 硬红线：元标记泄漏 0、整段落重复 0。
- 机器/LLM 偏差大（⚠️）章数：0 / 4，量具可信。
- continuity_health：Ch30 = 3.0（与 170f Stage 2 同窗口同值，非本次引入）。

### 4. 判定分析

按 170g 规划判定标准：

- **pass 条件**：voice/pacing/exposition 均较基线提升，均值 ≥3，偏差收敛，T9 不漏报。
  - 未满足：voice 未提升、exposition 数值未提升、均值 2.45 < 3。
- **observation 条件**：主要维度提升但仍有轻微债，不影响爬坡；量具已可信。
  - 不满足：voice 未提升且比基线低，exposition 未改善，均值未达 pass 线；残余债非轻微。
- **blocker 条件**：提质无效或量具仍失真或引入新缺陷。
  - 满足：**voice 提质无效**（1.75 < 1.8），说明性 exposition 本质未变；量具虽可信但不足以覆盖非角色声源与深层 exposition 换壳。

**终判：blocker。** 理由：

1. **工程侧约束部分有效但未触及根因**：`exposition_carrier` 约束 + 代码检测使显性硬灌模式从 170f 多处降至 1 处，但模型换壳为“建造者/残影独白/前代钥匙灌输/主角总结”，深层 exposition 仍偏说明性。
2. **voice 塌陷未改善**：非角色声源（建造者、残影、前代钥匙、舰队之手）未进入声纹约束，主角以外的对白仍同质化。
3. **pacing 保持 3.25 达标**：170f 的 `scene_interaction` 约束效果稳定，但这不能覆盖 voice/exposition 失败。
4. **量具可信但不够深**：机器 literary_quality 与 LLM rubric 归一后无大偏差（0 / 4），T9 不漏报；但 RuleAuditor 当前检测不到“非角色声音独白”和“主角总结式 tell”等深层问题。
5. **继续阻塞 Ch200 是务实选择**：在 voice/exposition 未达 pass 线前放行，会把中段文学债带入长跑；先完成工艺补丁并复评，边际收益远高于带病爬坡。

---

## 验证清单

- [x] `python -m pytest tests/test_rule_auditor.py tests/test_prompt_loader.py -q` 通过（72 passed）。
- [x] `ruff check src/ tests/` 通过。
- [x] 分模块 pytest 通过：
  - `tests/db tests/models tests/genres`：357 passed
  - `tests/rag tests/settlement_extractor tests/creative_modes tests/cli`：133 passed
  - `tests/evals tests/integration`：76 passed, 4 skipped
- [x] 顶层 `pytest tests/test_*.py -q` 通过：1862 passed, 1 xfailed。
- [x] Ch29–Ch32 小样本重生成完成：`run-8660e9d1`，4/4 success，failed=[]，Halt: None。
- [x] Ch29–Ch32 复评报告产出：`docs/reports/task-170g-remediation-reeval-report.md`。
- [x] 用户复核终判：**blocker**。
- [x] **明确结论：不放行 Task 171 Ch200；170g Phase2 小样本复评仍未达标，继续冻结阶段 Z 入口。**

---

## 后续步骤

1. **不启动 Task 171 Ch200 长跑**。阶段 Z 入口冻结，直到 170g 复评达到 pass 标准。
2. **执行 170g Phase 2 工艺补丁**（见 `tasks/170g-remediation-rerun-and-reeval-DONE.md` 改判说明与 `docs/STATUS.md` 当前优先级）：
   - 非角色声源声纹补漏（`_helpers.py` + Writer 1.2.0）。
   - exposition 检测升级（RuleAuditor 新增 direct_revelation_monologue / protagonist_summary_tell / info_delivery_dialogue）。
   - CreativeDirector 世界观揭示场景正路径模板。
   - GoalPlanner 信息交付校验。
   - RevisionHandler 文学 patch 路径。
3. **小样本复评**：在 Ch29–Ch32 隔离 DB 重跑并复评，目标 voice ≥3.0、exposition ≥3.0、窗口均值 ≥3.0。
4. **若小样本达标**：扩展到 Ch28–Ch40 enforce 复评，全部满足第 5 节标准后，方可把 170g 改回 observation/pass 并放行 Ch200。
5. **若小样本仍不达标**：保持 blocker，升级到结构性改写方案（方案 B）或继续迭代。

---

## Phase2 复评结果（2026-07-08）

按本节第 5 条，执行了 170g Phase2 工艺补丁与小样本复评，详见 `tasks/170g-phase2-remediation-DONE.md`。

### 复评数据

| 维度 | Ch29 | Ch30 | Ch31 | Ch32 | 窗口均值 | 目标 |
|---:|:---:|:---:|:---:|:---:|:---:|:---:|
| ai_tone | 2 | 3 | 2 | 2 | 2.25 | — |
| voice | 3 | 2 | 1 | 1 | **1.75** | ≥3.0 |
| concept | 3 | 4 | 3 | 3 | 3.00 | — |
| exposition | 2 | 3 | 2 | 2 | **2.25** | ≥3.0 |
| pacing | 3 | 4 | 3 | 3 | **3.25** | ≥3.0 |
| **均值** | 2.60 | 3.20 | 2.20 | 2.20 | **2.55** | **≥3.0** |

- T9 硬红线：元标记泄漏 0、整段落重复 0。
- exposition_carrier_count（代码检测）：0 处。
- 机器/LLM 偏差大章数：0 / 4，量具可信。
- 与 170g 初评对比：voice 持平（1.75），exposition 微升（2.0→2.25），pacing 持平（3.25），窗口均值微升（2.45→2.55）。

### Phase2 判定

**仍未达标，170g 维持 blocker，不放行 Task 171 Ch200。**

理由：
1. voice 1.75 仍塌陷，且未较 170b 基线 1.8 提升；
2. exposition 2.25 距 3.0 pass 线仍有 0.75 差距；
3. 窗口均值 2.55 < 3.0；
4. 量具可信（偏差 0/4、T9 0/0、exposition_carrier 0），问题在生成侧深层结构；
5. V7 边界内的最小工艺补丁边际收益已验证不足，再追加同类约束性价比低。

### Phase2 认知更新

- **补丁有效但不够**：5 项工艺补丁成功把显性 exposition 载体硬灌压到 0，pacing 保持达标，T9 不漏报；但未解决"非人实体独白 + 主角总结容器"的换壳模式。
- **voice 塌陷的根因是戏份分配**：非人实体占据中段世界观揭示的核心戏份，主角和人类角色被边缘化；单纯补声纹卡无法挽回 voice。
- **exposition 说明性的根因是信息生长方式**：设定仍被直接投递，而非从失败/代价/冲突中推导出来。
- **下一步必须选择**：路径 A（继续 GoalPlanner/CreativeDirector/RevisionHandler 细粒度约束，预计边际收益有限）或路径 B（结构性改写 / 声源工程，工程量大但可能治本）。

---

## 验证清单

| 债项 | 严重程度 | 根因 | 跟踪方式 |
|------|:---:|:---|:---|
| voice 扁平 | P0 | 非角色声源（建造者/残影/前代钥匙/舰队之手）无 `dialogue_style_card`，Writer 声纹约束未覆盖 | Task 170g Phase 2 声纹补洞 + 小样本复评 |
| exposition 说明性仍强 | P0 | 约束只禁了“载体形式”，模型换壳为角色独白/主角总结直接投递信息 | Task 170g Phase 2 RuleAuditor 升级 + CreativeDirector 正路径模板 + RevisionHandler 文学 patch |
| continuity_health 偶发 3.0 | P2 | Ch30 health=3.0，与 170f 同窗口同值，非本次退化 | 已有自适应门禁监控，Ch200 长跑中观察（但当前不放行） |

---

## 交付物

- 生成脚本：`scripts/run_170g_generation.py`
- 复评脚本：`scripts/run_170g_reeval.py`
- 工艺卡更新：`prompts/cards/writer/1.1.0.yaml`、`prompts/cards/writer/1.2.0.yaml`
- 代码检测：`src/songyan/agents/rule_auditor.py`、`src/songyan/models/review.py`、`src/songyan/models/__init__.py`
- 单测：`tests/test_rule_auditor.py`、`tests/test_prompt_loader.py`
- 复评报告：`docs/reports/task-170g-remediation-reeval-report.md`
- 生成日志：`.tmp/run_170g_quick.log`
- 隔离 DB：`.tmp/task170g_quick.db`
- 状态更新：`docs/STATUS.md`、`tasks/V7-README.md`、`README.md`、`tasks/170-literary-quality-remediation-README.md`、`AGENTS.md`

---

## 关键判定记录

> **170g 复评结论：blocker。不放行 Task 171 Ch200 长跑。**
>
> 本判定基于 Ch29–Ch32 小样本真实生成 + LLM rubric 初筛 + 代码检测 + T9 硬红线 + 用户复核终评，量具可信；但 voice/exposition 未达 170g pass 线，必须先完成工艺补丁并复评通过。
