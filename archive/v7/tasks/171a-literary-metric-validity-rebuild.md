# Task 171a: 文学量具效度重建（R0 —— voice/exposition 构念重定义 + 盲标 P/R/F1 + 体裁解耦通电 + voice 归因召回修复）

> **框架**: V7 文学质量框架级复盘（`docs/reports/v7-literary-framework-review.md`），本任务对应框架 §8 **B 组** + §7.1 **R0**
> **类型**: 量具效度重建（R&D 线，"文学结论"的唯一近期硬前置）
> **优先级**: P0（R&D 线起点；未完成则任何"模型写不好"的文学结论无效）
> **依赖**: Task 170 系列已结束（170o/170p 已修 seeding gap，留下 voice 归因召回短板）；不依赖也不阻塞 Task 171 Ch200 主线
> **状态**: ✅ **代码侧完成（B1/B4/B5 达标）**；B2/B3 拆分至 Task 171a-1。DONE：`archive/v7/tasks/171a-literary-metric-validity-rebuild-DONE.md`，报告：`archive/v7/reports/task-171a-metric-validity-report.md`
> **负责人**: songyan-agent

---

## Review 结论（2026-07-10，代码级对齐）

已读 `rule_auditor.py`（voice/exposition 检测器 + `run_rule_audit` 签名）、`literary_repo.py`、`workflows/_nodes.py` 三个 `run_rule_audit` 调用点，确认 spec 判断全部属实：
1. **`load_exposition_keywords` 是死代码**——仅在 `literary_repo.py:150` 定义，全仓零调用点。
2. **`_DEFAULT_CHARACTER_NAMES = {"林渊","宋晚","苏晚"}`**（`rule_auditor.py:296`）作 `detect_exposition_carriers` 的默认值（L442），线上永远 fallback 到写死人名。
3. **`run_rule_audit` 内部管线已完整**：签名已暴露 `character_names`/`setting_keywords`/`non_character_keywords`/`info_delivery_keywords` 等 kwargs（L1076-1083），且已把它们透传给 `detect_exposition_carriers` + `detect_human_voice_homogeneity`（L1150-1167）。**唯一缺口是 3 个调用点（`_nodes.py` L926/L1142/L1751）没传项目关键词**——三处均为 `async`、`state["project_id"]` 在作用域内，可直接注入。
4. **voice 归因**（`detect_human_voice_homogeneity` L785-958）：170o 已支持前置/后置/叙事归因（`X的声音`），但**缺"动作节拍夹引语"（`X皱眉。"…"`）与代词就近实名绑定**，且窗口仅 before30/after40 字符，是召回过低（Ch1 30 引语→8 条）的主因。

**实施顺序微调**：先做"体裁解耦通电 + 删硬编码"（Task #9，改动小、独立、立即消除失真源），再做"voice 归因召回 + 构念重定义"（Task #8，最复杂），最后 ground truth reeval（Task #10）。此调整不改 spec 目标，仅调执行次序。

---

## 任务边界

Task 171a 是新框架 R&D 线的**第一步、也是唯一的近期硬前置**：在做任何 voice/exposition 生成侧提质（171c）之前，先把量具本身修到"可信"。旧框架的致命错误是**拿一把读数恒 0 / 构念建错的尺子做二元放行判决**（框架文档 E2/E3），本任务专门消除这个错误。

**只做量具，不做提质**。本任务不改 Writer/CreativeDirector 的生成行为、不追求提升任何 rubric 分数；只重定义"文学质量怎么量"、把量具修到可信、并证明它可信。提质是 171c 的事，且必须等本任务出口达标后才允许启动。

仍在 V7 MVP 边界内：不新增 LangGraph 节点 / Agent / Workflow；通过重构 `rule_auditor.py` 检测器、接线已有动态注入参数、建立 ground truth 基础设施实现。

---

## 核心问题（复盘认定，本任务对治）

1. **构念建错（E3）**：`voice` 现被建模为"同一章内两个说话人对白的逐章同质度"，`exposition` 被建模为"硬编码 SF 关键词的模式计数"。前者导致单人解谜/意识流章天然拿不到 voice 分；后者导致换体裁即失效、且好的功能性长说明被误判。
2. **精度不可信（E2）**：`detect_human_voice_homogeneity` 对真实正文恒返回 0——说话人归因僵化（只认紧邻实名说话人，无法处理"名字+动作节拍+引语""后置提示""代词"句式），170p 验证中 Ch1 的 30 条引语只归因 8 条（召回 ~27%）。
3. **体裁窄化 + 死代码**：`rule_auditor.py` 硬编码 `_DEFAULT_CHARACTER_NAMES={林渊,宋晚,苏晚}` 与整套硬 SF 词表；已写好的动态注入参数（`character_names`/`setting_keywords`/…）在生产 workflow **三个调用点全没接线**，`literary_repo.load_exposition_keywords` 是**无调用点的死代码**。

---

## 目标

1. **voice 构念重定义**：从"逐章同质度"改为 **角色级·跨章·一致性 × 辨识度**——
   - 只在**对话承载章**（对话密度达阈值的章节）计分；单人解谜/意识流章标记为"voice 不适用"，不计入 voice。
   - 一致性：同一角色跨多章的对白特征（句长分布、口头禅、情绪基调）是否稳定。
   - 辨识度：不同角色之间对白特征是否可区分。
2. **exposition 构念重定义**：从"硬编码关键词模式计数"改为 **信息融合度**——信息是否被动作 / 冲突 / 代价承接，而非孤立的说明段/独白灌入。判据与体裁无关。
3. **voice 归因召回修复**：重构 `detect_human_voice_homogeneity` 的说话人归因，支持"名字+动作节拍+引语""后置提示语（"……"他说）""代词指代（就近实名绑定）"三类句式；在配角齐全 DB 上召回率达到本任务精度线。
4. **体裁解耦通电**：把 `rule_auditor.py` 已有的动态注入参数在生产 workflow 真正接线（从 `literary_repo.load_exposition_keywords` 灌入项目实际 `characters`/`setting_snapshots`）；删除 `_DEFAULT_CHARACTER_NAMES` 及硬 SF 词表作为默认值的依赖；消灭 `load_exposition_keywords` 死代码。
5. **盲标 ground truth 基础设施**：建立"遮机器分的人工盲标"流程 + 数据文件，覆盖 ≥2 体裁、含对话密集与稀疏两类场景，用于计算量具 P/R/F1。
6. **reeval 闭环**：用盲标集测量 voice/exposition 量具的 precision/recall/F1，产出效度报告。

---

## 验收标准（对应框架 §8 B 组）

### 工程验收
- `ruff check src/ tests/` 通过。
- 新增/修改单测通过：voice 归因（三类句式）用例、exposition 融合度用例、动态注入接线用例、体裁解耦回退用例。
- 分模块 pytest 全通过（按 AGENTS.md Windows 测试防卡协议：分模块 + 顶层批次）。
- 无大纲/无配角项目能回退旧行为（动态注入为空时有安全 fallback，但**不再 fallback 到写死人名/SF 词表**——改为"该维度对本项目暂不计分"而非误报）。

### 效度验收（B 组硬判据）
- **B1 构念重定义落地**：voice/exposition 的新定义写入量具设计文档 + 代码；旧"逐章同质度""模式计数"废弃或降级为诊断信号（不再作判据）。
- **B2 盲标 ground truth 建立**：盲标集覆盖 **≥2 体裁**、含对话密集 + 稀疏两类场景，样本量足以算 P/R/F1（每维度每类场景 ≥ 一定条数，具体在执行时定并记录）。
- **B3 精度达标**：voice/exposition 量具在盲标集上 **P/R/F1 ≥ 0.8**（阈值可按维度微调，但须在报告中显式声明依据）。
- **B4 体裁解耦通电**：生产 workflow 的 `run_rule_audit` 调用点实际传入项目 `character_names`/`setting_keywords`；`_DEFAULT_CHARACTER_NAMES` 硬编码删除；`load_exposition_keywords` 有调用点 + 测试覆盖（不再是死代码）。
- **B5 voice 归因召回修复**：`detect_human_voice_homogeneity` 在配角齐全 DB（如 `run-bcf3b8f1` 产物）上对真实正文**不再恒 0**；说话人归因召回率达 B3 精度线要求。

### 出口纪律
- **达标出口**：B1–B5 全部满足 → voice/exposition 量具"可信"，171b/171c 可启动。
- **不达标出口（诚实降级，框架 §8.5）**：若 voice 构念重定义后仍无法在盲标集上达到 B3 精度 → 记录"voice 维度暂无可信自动量具"，该维度**永久转人工抽读**、退出一切自动判据；exposition 若达标则单独放行。**不因本任务未完成而回退去阻塞 Ch200 主线。**

---

## 实施要点（非全量设计，执行时细化）

### 1. voice 构念重建
- 新增"对话密度"分层信号（复用/扩展 `_split_scenes`）：按引语字数占比 / 说话人数判定章节是否"对话承载"。
- voice 计分只在对话承载章生效；输出中显式标注"voice 不适用章"。
- 一致性维度需要跨章数据——依赖 `characters` 表配角齐全（170p 已闭合 seeding gap，本任务复用）。

### 2. exposition 融合度重建
- 从"关键词命中计数"改为"揭示句的前后文是否有动作/冲突/代价承接"（复用 170i 引入的 `_EARNED_REVELATION_CUES` / `_COST_CUES` 思路，但去 SF 硬编码、改为体裁无关的结构信号 + 动态项目关键词）。

### 3. 说话人归因重构（`detect_human_voice_homogeneity`）
- 支持三类句式：前置实名（`X说："…"`）、后置提示（`"…"，X说`）、动作节拍夹引语（`X皱眉。"…"`）、代词就近实名绑定。
- 用配角齐全 DB 做召回率回归，回填召回率数据。

### 4. 体裁解耦接线（`workflows/_nodes.py` + `rule_auditor.py` + `literary_repo.py`）
- 3 个 `run_rule_audit` 调用点注入 `LiteraryKeywordRepository.load_exposition_keywords(project_id)` 的结果。
- 删除 `_DEFAULT_CHARACTER_NAMES` 作默认值；空注入时该维度不计分而非误报。

### 5. ground truth 基础设施（`scripts/` + `.tmp/ground_truth/`）
- 复用 170m 的 ground truth 导出/reeval 脚手架（`run_170m_ground_truth_export.py` / `run_170m_reeval.py`）扩成体裁无关、盲标（遮机器分）版本。
- 样本取自 ≥2 体裁的真实生成产物（scifi 已有；第二体裁需小样本生成或复用历史）。

---

## 交付物（预期）
- `src/songyan/agents/rule_auditor.py`（voice/exposition 构念重建 + 归因重构 + 动态注入通电）
- `src/songyan/db/literary_repo.py`（`load_exposition_keywords` 接线，去死代码）
- `src/songyan/workflows/_nodes.py`（3 个调用点注入项目关键词）
- `scripts/run_171a_ground_truth_export.py`、`scripts/run_171a_reeval.py`
- `.tmp/ground_truth/task171a_*_ground_truth.jsonl`（≥2 体裁盲标集）
- `tests/test_171a_*.py`（归因三句式 / 融合度 / 解耦回退）
- `archive/v7/reports/task-171a-metric-validity-report.md`（P/R/F1 效度报告 + 出口判定）
- `archive/v7/tasks/171a-literary-metric-validity-rebuild-DONE.md`

---

## 明确不做
- 不改生成侧行为、不追求提升 rubric 分数（那是 171c）。
- 不阻塞 Task 171 Ch200 主线（本任务是"文学结论"前提，非"Ch200 放行"前提）。
- 不放宽 T9/T10/T5/T6/T12 任何冻结口径。
- 不做全自动 LLM 改写闭环。
