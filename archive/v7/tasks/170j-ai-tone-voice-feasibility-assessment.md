# Task 170j: 路径 B 第三步 — 文学塌陷根因诊断与保守修复

> **专项**: 文学提质专项（`archive/v7/tasks/170-literary-quality-remediation-README.md`）
> **类型**: 根因诊断 / 保守修复 / 路径可行性评估（路径 B 第三步）
> **优先级**: P0（决定路径 B 是否能在 V7 内达标，或需升级/降级方案）
> **依赖**: Task 170i 已完成（结论：未达标，维持 blocker）
> **状态**: 🟡 **待建立文档并 review**
> **负责人**: songyan-agent

---

## 任务边界

Task 170j 是 170i 路径 B 第二步失败后的 **路径 B 第三步**。170i 已经把"认知冲突-误判-代价"模板和"人类角色声纹锚定"落地，但 Ch29–Ch32 复评仍显示：

- **voice 均值 2.00**（目标 ≥3.0）
- **exposition 均值 2.25**（目标 ≥3.0）
- **ai_tone 均值 2.00**（目标 ≥3.0）
- **窗口 5 维均值 2.55**（目标 ≥3.0）

170j 不再追加新的硬性约束或大型机制，而是：
1. **先诊断**：用代码检测 + 人工抽读 + LLM rubric 证据，精确定位 voice/exposition/ai_tone 塌陷的具体文本模式；
2. **做减法/微调**：移除或弱化可能导致模板化的 prompt 元素，调整现有工艺卡的权重与表述，而非新增禁令；
3. **小样本对照**：每个候选改动在 Ch29–Ch32 等效窗口独立跑 1 组样本，快速验证是否有效；
4. **果断决策**：若保守修复无效，诚实判定路径 B 在 V7 内不可行，给出升级/降级方案。

本任务仍守 V7 MVP 边界：不新增 LangGraph 节点、不新增 Agent、不做全自动 LLM 改写闭环。

---

## 核心假设

170i 已证明：

1. **显性 exposition 载体可以被工程约束压住**：`exposition_carrier` 连续多轮保持 0，T9 保持 0/0，pacing 稳定 ≥3.0。
2. **模型会把工程约束"形式化执行"**：它能写出"冲突-误判-代价-修正"结构，但内容仍是冷静、对称、概念堆叠的 AI 腔。
3. **问题可能不是约束不够，而是约束太多、太具体，导致模型只能套模板**：CreativeDirector 的 scene_templates、cognitive_conflict_templates、 DialogueStyleCard、info_release 等层层模板叠加后，Writer 被限制在"填空"而非"创作"。
4. **voice 塌陷与人类角色声纹扁平可能源于：配角缺乏真正的对抗性目标**，而非缺少语言标签。

因此，170j 的核心不是"再列规则"，而是：
- **减少模板重叠**，给 Writer 更多留白；
- **把"对抗性"从句式标签转移到角色目标冲突**；
- **如果上述微调无效，接受路径 B 在当前模型下收益耗尽**。

---

## 目标

1. **诊断优先**：对 170i 的 Ch29–Ch32 正文做结构化缺陷分析，统计：
   - 每章"主角总结式内心独白"出现次数与位置；
   - 每章人类角色对白的目标冲突比例（是否有真正的对抗，还是互相补充信息）；
   - 每章对称/排比/万能过渡句式的密度；
   - 每章高概念信息是否仍由"告知"而非"动作后果"承载。
2. **候选方案 A — 减少模板重叠**：
   - Writer 从 1.2.2 退到更轻量的 1.2.2-lite：保留 exposition_carrier 约束和人类声纹卡，但**移除 cognitive_conflict 五节拍强制模板**，改为"建议冲突结构"；
   - CreativeDirector 保持 1.0.8，但**不再要求每个 information_event 都必须填对立判断/误判/代价/修正**，改为只要求"存在对立判断"和"主角付出代价"两个硬点；
   - 观察模型在约束减少后是否能写出更自然的冲突。
3. **候选方案 B — 角色目标冲突前置**：
   - 不增加声纹标签，而是让 CreativeDirector 1.0.8 输出每个主要人类角色在本章的**对抗性目标**（想要什么、害怕什么、与主角目标的冲突点）；
   - Writer 1.2.2 接收对抗性目标而非详细声纹卡，让人类角色的对白从"目标冲突"中自然生长；
   - 观察 voice 是否因真实对抗而提升。
4. **候选方案 C — 混合精简版**：
   - 保留 170i 的 exposition_carrier 约束；
   - 用方案 A 的轻量冲突模板 + 方案 B 的对抗性目标；
   - 移除部分声纹卡字段，只保留"情绪基调 + 一句话口头禅/禁忌"，避免过度标签化。
5. **路径可行性评估**：
   - 若任一候选方案在 Ch29–Ch32 达到 voice≥3.0 / exposition≥3.0 / 窗口均值≥3.0 / T9 0/0 / carrier≤1，则进入全量 Ch1–Ch40 复评；
   - 若均未达标但与 170i 相比有明显提升（窗口均值 ≥2.8 且无维度退化），可追加一轮微调；
   - 若均未达标且提升不明显，判定路径 B 在 V7 内不可行，给出升级/降级方案。

---

## 验收标准

### 工程验收
- `ruff check src/ tests/` 通过。
- 新增诊断脚本与单测通过。
- 无大纲项目能回退旧行为（CreativeDirector default_version 保持 1.0.5，Writer default_version 保持 1.1.0）。

### 诊断交付
- `docs/reports/task-170j-diagnosis-report.md` 必须包含：
  - Ch29–Ch32 每章的"主角总结式独白"统计；
  - 人类角色对白的"目标冲突" vs "信息互补"比例；
  - AI 腔句式密度（对称/排比/万能过渡）；
  - 明确指出的 1–3 个最可修复的具体模式。

### 小样本对照实验
- 每个候选方案在 Ch29–Ch32 独立跑 1 个隔离 DB（与 170i 相同大纲）。
- 评估指标：voice / exposition / pacing / concept / ai_tone，窗口 5 维均值，T9 硬红线，`exposition_carrier_count`，机器/LLM 偏差。
- 达标线：
  - voice ≥ 3.0
  - exposition ≥ 3.0
  - pacing ≥ 3.0
  - 窗口 5 维均值 ≥ 3.0
  - `exposition_carrier_count` ≤ 1
  - T9 硬红线 0/0
  - 机器/LLM 偏差 < 3 分

### 决策交付
- `archive/v7/tasks/170j-ai-tone-voice-feasibility-assessment-DONE.md` 必须明确给出：
  - 诊断结论；
  - A/B/C 各方案实验数据对照表；
  - 推荐方案或"不可行"判定；
  - 下一步工程清单或升级/降级方案。

---

## 关键改动清单

### 1. 诊断脚本：`scripts/run_170j_diagnose.py`

**Files:**
- `scripts/run_170j_diagnose.py`（新增）
- `tests/test_170j_diagnose.py`（新增）

**改动：**
- 读取 170i 隔离 DB `.tmp/task170i_ch1_ch32.db` 的 Ch29–Ch32 accepted 正文。
- 输出诊断报告 `docs/reports/task-170j-diagnosis-report.md`，包含：
  - `protagonist_summary_tell_count`：主角"明白/意识到/知道了/终于懂了/这一切都意味着"等总结句出现次数与位置；
  - `opposing_goal_ratio`：人类角色对白中体现目标冲突 vs 信息互补的比例（用启发式规则 + 可选 LLM 抽样标注）；
  - `ai_tone_density`：对称/排比/万能过渡/清单式说明句的密度；
  - `revelation_carrier`：高概念信息由"动作后果"承载 vs 由"直接告知"承载的比例。
- 不修改生成逻辑，只读不写，风险为零。

### 2. 候选方案 A — 轻量冲突模板

**Files:**
- `prompts/cards/creative_director/1.0.8-lite.yaml`（新增）
- `prompts/cards/writer/1.2.2-lite.yaml`（新增）
- `prompts/cards/creative_director/_manifest.yaml`（新增版本条目）
- `prompts/cards/writer/_manifest.yaml`（新增版本条目）
- 相关单测

**改动：**
- CreativeDirector 1.0.8-lite：
  - 保留 `cognitive_conflict_templates` 字段，但只要求 `opposing_judgment` 和 `cost_event` 两个子字段；
  - 移除 `misjudgment_idx` / `correction_idx` 的强制对应；
  - 把"五节拍"表述从"必须"改为"建议结构"。
- Writer 1.2.2-lite：
  - 保留 exposition_carrier 约束和人类声纹卡；
  - 把"认知冲突五节拍必须执行"改为"优先通过动作和代价呈现信息，允许自然留白"；
  - 移除"主角连续内心独白不超过两句"的硬限制，改为"避免用连续独白总结世界观"。

### 3. 候选方案 B — 角色目标冲突前置

**Files:**
- `prompts/cards/creative_director/1.0.9-goals.yaml`（新增）
- `prompts/cards/writer/1.2.3-goals.yaml`（新增）
- `src/songyan/models/creative_mode.py`（`CreativeBrief` 新增 `character_conflict_goals` 字段）
- `src/songyan/agents/creative_director/_brief_builder.py`（解析 `character_conflict_goals`）
- 相关单测

**改动：**
- CreativeDirector 1.0.9-goals：
  - 新增 `character_conflict_goals` 字段，为每个主要人类角色输出：
    - `what_they_want`：本章想达成的具体目标；
    - `what_they_fear`：本章害怕发生的具体后果；
    - `conflict_with_protagonist`：与主角目标的直接冲突点（一句话）。
  - 不再输出详细的 `cognitive_conflict_templates`。
- Writer 1.2.3-goals：
  - 接收 `character_conflict_goals`，要求每个出场人类角色的对白必须体现其目标/恐惧/冲突点；
  - 不强制 DetailedDialogueStyleCard，只保留"情绪基调 + 一句话口头禅/禁忌"；
  - 保留 exposition_carrier 约束。

### 4. 候选方案 C — 混合精简版

**Files:**
- `prompts/cards/creative_director/1.0.10-mixed.yaml`（新增）
- `prompts/cards/writer/1.2.4-mixed.yaml`（新增）
- 相关单测

**改动：**
- 保留 170i 的 exposition_carrier 约束；
- 用方案 A 的轻量冲突模板（只要求 opposing_judgment + cost_event）；
- 叠加方案 B 的 character_conflict_goals，但只给 2–3 个核心人类角色；
- 声纹卡极简：只保留"情绪基调"和"一句话口头禅/禁忌"，其余字段删除。

### 5. 实验 harness：`scripts/run_170j_experiment.py`

**Files:**
- `scripts/run_170j_experiment.py`（新增）
- `scripts/run_170j_reeval.py`（新增，复用 170i 逻辑但支持多方案对比）

**改动：**
- 参数化实验条件：`--approach {A,B,C}`、`--start 29 --end 32`、`--db .tmp/task170j_<approach>.db`。
- `--init` 创建干净 DB 并导入与 170i 相同的大纲/弧/线索。
- 根据 `--approach` 切换 CreativeDirector / Writer 版本：
  - A：CreativeDirector 1.0.8-lite + Writer 1.2.2-lite
  - B：CreativeDirector 1.0.9-goals + Writer 1.2.3-goals
  - C：CreativeDirector 1.0.10-mixed + Writer 1.2.4-mixed
- 所有路径使用 `GATE_MODE=observe`（基于 170i 经验，enforce 对早期章节过度敏感）。
- 生成后自动调用 `scripts/run_170j_reeval.py --approach <X>` 出报告。

### 6. 评估与决策文档

**Files:**
- `archive/v7/tasks/170j-ai-tone-voice-feasibility-assessment-DONE.md`（新增）

**改动：**
- 汇总诊断报告与 A/B/C 实验数据；
- 按验收标准给出 go/no-go；
- 若不可行，给出明确升级/降级方案。

---

## 执行顺序

1. **建立并 review 本 task 文档**（当前步骤）。
2. **运行诊断脚本**：
   - 实现 `scripts/run_170j_diagnose.py`；
   - 生成 `docs/reports/task-170j-diagnosis-report.md`；
   - 根据诊断结果微调候选方案重点。
3. **实现候选方案 A/B/C 工艺卡**：
   - 新增 6 个 prompt 卡；
   - 更新 `_manifest.yaml`；
   - 新增/调整解析代码；
   - 新增单测。
4. **搭建实验 harness**：
   - 实现 `scripts/run_170j_experiment.py` 与 `scripts/run_170j_reeval.py`；
   - 新增单测。
5. **小样本对照实验**：
   - 跑 A/B/C 各一组 Ch29–Ch32；
   - 出三份复评报告。
6. **路径可行性评估与决策**：
   - 汇总数据；
   - 回填 `archive/v7/tasks/170j-ai-tone-voice-feasibility-assessment-DONE.md`。
7. **状态更新**：
   - 更新 `docs/STATUS.md`、`tasks/V7-README.md`、`README.md`、`archive/v7/tasks/170-literary-quality-remediation-README.md`。

---

## 风险与回退

| 风险 | 缓解 |
|------|------|
| 减少约束后 exposition_carrier 回升 | 保留 exposition_carrier 硬约束，只减少冲突模板和声纹卡的细节 |
| 角色目标冲突前置导致剧情过度戏剧化 | 要求冲突点必须基于已有角色关系，禁止凭空制造反派 |
| 混合方案 prompt 仍过长 | C 方案声纹卡极简，只保留 2 个字段 |
| 所有保守方案均无效 | 在 DONE 文档中明确判定路径 B 不可行，提出升级/降级方案，不继续空转 |
| 无大纲项目行为改变 | 所有新 Writer/CreativeDirector 版本只对有骨架项目生效，default_version 不变 |

---

## 交付物

- 诊断：
  - `scripts/run_170j_diagnose.py`
  - `docs/reports/task-170j-diagnosis-report.md`
- 工艺卡：
  - `prompts/cards/creative_director/1.0.8-lite.yaml`
  - `prompts/cards/writer/1.2.2-lite.yaml`
  - `prompts/cards/creative_director/1.0.9-goals.yaml`
  - `prompts/cards/writer/1.2.3-goals.yaml`
  - `prompts/cards/creative_director/1.0.10-mixed.yaml`
  - `prompts/cards/writer/1.2.4-mixed.yaml`
- 代码：
  - `src/songyan/agents/creative_director/_brief_builder.py`
  - `src/songyan/models/creative_mode.py`
  - `src/songyan/agents/writer.py`（渲染轻量冲突/目标冲突）
  - `scripts/run_170j_experiment.py`
  - `scripts/run_170j_reeval.py`
- 单测：
  - `tests/test_170j_diagnose.py`
  - `tests/test_prompt_loader.py`（验证新增卡可加载）
  - `tests/test_creative_director.py`（解析新字段）
- 报告与状态：
  - `docs/reports/task-170j-approachA-reeval-report.md`
  - `docs/reports/task-170j-approachB-reeval-report.md`
  - `docs/reports/task-170j-approachC-reeval-report.md`
  - `archive/v7/tasks/170j-ai-tone-voice-feasibility-assessment-DONE.md`

---

## 下一步

1. review 本 task 文档。
2. 确认后先跑诊断脚本，拿到 170i 正文的精确缺陷数据，再决定 A/B/C 是否都要实现。
