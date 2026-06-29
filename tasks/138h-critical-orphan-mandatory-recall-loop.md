# Task 138h: Critical Orphan Mandatory Recall Loop（critical 设定强制回收闭环）

> **类型**: 架构增强 / Writer 硬约束 / QG 可验证规则
> **状态**: 进行中
> **前置**: Task 138g

## 背景

Task 138g 已证明：继续补单个 alias 无法解决 critical recall 问题。

- `run-715f7d09` 使用已补强的 `surface_material` 窄 alias + CreativeDirector stale critical P1 提示，Ch12 continuity 仍为 `health=3.0`、`orphaned=16`、critical orphan=4。
- `surface_material` 未出现在 Ch12 正文的根本原因是生成波动，而非 alias 失效。
- `team_7` 虽被回收但新增 E-7 critical orphan，说明"增强提示文本"不足以稳定约束 Writer。

核心瓶颈：**critical orphan 从 CreativeDirector 规划到 Writer 正文执行之间缺少稳定闭环**。当前 `active_settings_to_recycle` 是"建议回收"语义，Writer 可以忽略；QG/RuleAuditor 也未对"critical 设定未回收"做专项检测。

本任务将 critical orphan 从"建议"升级为"硬约束"，并在 QG/RuleAuditor 层建立可验证的拦截机制。

## 目标

让 `critical` 级 orphan（`silent >= ORPHANED_THRESHOLDS["critical"]`，即 3 章未提及）从"CreativeDirector 建议回收"变为"Writer 必须回应的硬约束"，且该约束在 QG/RuleAuditor 层可验证。

## 不做的事

- **不新增任何 setting alias**。alias 问题已在 138g 解决，且证明不是瓶颈。
- **不修改 `ContinuityAuditor._compute_health_score()` 公式**。
- **不修改 orphan 分类阈值**（`ORPHANED_THRESHOLDS`）。
- **不动 settlement evidence gate**（已稳定）。
- **不 archive 或降级 critical orphan**。
- **不扩大到 Ch1-Ch20 / default run**（聚焦 Ch10-Ch12 验证收口）。
- **不污染主库**（复跑使用 `.tmp` 副本 DB）。

## 要做的两件事

### 子项 A：Writer 输入硬化（mandatory_references 硬约束块）

**问题**：当前 `_format_active_settings_to_recycle()` 输出的 setting 列表是建议性语义，Writer prompt 中没有专门段落要求 Writer 必须确认这些 setting 已被提及、使用或给出剧情豁免原因。

**改动**：

1. 在 `ContextManager` 或 `CreativeDirector` 的组包逻辑中，从 `active_settings_to_recycle` 里筛选出 `category == "critical"` 且 `silent >= 3` 的项，单独组成 `mandatory_references` 列表。
2. 在 Writer prompt 中新增一个硬约束块（位于 `creative_brief` 或 `hard_constraints` 之后），格式示例：

   ```
   【强制连续性约束 —— 以下设定已沉寂 ≥3 章，本章必须明确提及、使用、
   或给出无法回收的剧情原因（如已损毁、已转移、已被封存）：
   - 巨型遗迹表面材料特性（artifact.mega_ruin.surface_material）：已沉寂 9 章
   - 相位冲刷机制（artifact.ruin.phase_flush_mechanism）：已沉寂 5 章
   】
   ```
3. 该块中的每一项都必须有明确的 `setting_key`、`display_name`、`silent_chapters` 计数。
4. 若本章已因剧情原因明确排除某 setting 的回收（如该 setting 所在场景已物理损毁），Writer 应在正文中给出一句剧情解释；ContinuityAuditor 扫描到该解释后可标记为 `intentionally_dropped`，不计入 orphan。

**验证**：复跑时检查 Writer prompt 中是否包含 `mandatory_references` 块，且块中是否包含当前活跃的 critical orphan。

### 子项 B：QG/RuleAuditor 前置验证（mandatory_reference_missing 检测规则）

**问题**：当前 RuleAuditor 没有专门检测"critical setting 未在正文中回收"的规则。即使 Writer 忽略了 mandatory_references，QG 也可能以其他维度通过。

**改动**：

1. 在 `RuleAuditor` 新增一条规则（或 QG 评分维度）：`mandatory_reference_missing`。
2. 规则逻辑：
   - 从 `chapter_versions` 或 state 中获取本章的 `mandatory_references` 列表（由 CreativeDirector/ContextManager 写入）。
   - 使用已有的 `_setting_reference_terms()` 扫描 accepted 正文，检查每个 mandatory reference 是否有证据命中。
   - 若存在未命中的 mandatory reference，生成 `critical` 级 issue：
     - `rule_id`: `mandatory_reference_missing`
     - `severity`: `critical`
     - `setting_key`: `<key>`
     - `message`: `强制连续性设定 "<name>" 在本章正文中未找到提及证据。该设定已沉寂 <N> 章，属于 mandatory reference，必须在正文中回收或给出剧情豁免原因。`
3. QG 评分影响：每个 `mandatory_reference_missing` issue 扣减 `overall_score` ≥ 1.0（或按 `1.0 * missing_count` 计算），确保即使其他维度全优，只要漏掉一个 mandatory reference，QG 就不会通过。
4. 若 Writer 在正文中给出了剧情豁免原因（如 `"相位冲刷机制因核心损毁已永久失效"`），SettlementExtractor 应能提取该原因并写入 `character_states` 的 `lifecycle_status` 或 setting 的 `intentionally_dropped_chapter`，QG 不再扣分。

**验证**：
- 单测：模拟 Writer 正文包含/不包含 mandatory reference 的场景，验证 RuleAuditor 是否正确生成 issue。
- 单测：模拟剧情豁免原因被提取的场景，验证 QG 不扣分。
- 复跑：若 Writer 未回收 critical setting，QG 应拦截并打回修订；修订后应成功回收。

## 实施顺序

1. 先实现子项 A（Writer 输入硬化），复跑一次，观察 Writer 是否能在 prompt 约束下稳定回收 critical setting。
2. 若子项 A 单独复跑即达标（critical orphan ≤1, health ≥5.0），子项 B 可作为加固兜底合并提交。
3. 若子项 A 单独复跑未达标，再实现子项 B（QG 拦截），形成"提示 + 拦截"双层闭环，再次复跑验证。

## 验收标准

### 代码层

- 新增/修改的代码通过 `ruff check src/ tests/`。
- 新增单测覆盖子项 A（`mandatory_references` 组包逻辑）和子项 B（`mandatory_reference_missing` 检测规则）。
- 目标测试：`pytest tests/test_task137_setting_recycling.py tests/test_task135_continuity_governance.py tests/test_continuity_health_governance.py -q` -> `70+ passed`。
- 全量 pytest 不引入 regression。

### 实跑层

- 使用新的 `.tmp` 副本 DB 复跑 Ch10-Ch12（至少两次，使用不同随机种子或不同 `_internal_run_id`）。
- Ch11/Ch12 settlement、summary、QG 全部通过。
- Ch12 continuity 生成。
- **单次复跑出口**：critical orphan ≤ 1，health ≥ 5.0。
- **连续两次复跑出口**：两次均 critical orphan ≤ 1 且 health ≥ 5.0，证明闭环稳定。
- 若 Writer 给出了剧情豁免原因（如 E-7 节点已损毁），SettlementExtractor 应正确提取，continuity 不将其计为 orphan。

### 文档层

- 本文件更新实施记录和结论。
- `STATUS.md`、`V5-README.md`、`docs/INDEX.md` 同步更新。

## 技术细节备忘

- `mandatory_references` 的来源：ContinuityAuditor 的 `classify_report()` 已输出 orphan 分类，CreativeDirector 的 `_load_active_settings_to_recycle()` 已加载 stale setting。可在 ContextManager 组装 context pack 时，从 `active_settings_to_recycle` 中按 `category == "critical"` 和 `silent >= 3` 筛选。
- 正文扫描复用：`_setting_reference_terms()` 和 `_detect_setting_references()` 已具备扫描能力，子项 B 可直接复用。
- 剧情豁免标记：可在 `settings` 表中新增 `intentionally_dropped_chapter` 字段（或复用 `lifecycle_status`），由 SettlementExtractor 在提取到明确豁免语句时写入。本任务若涉及 schema 变更，需评估最小影响；优先尝试复用现有字段（如 `human_marks` 或 `notes`）。
- 随机种子隔离：复跑使用 `.tmp/task138h_ch10_focus_<timestamp>.db`，运行前确认无残留进程。

---

## 实施记录

### 子项 A（Writer 输入硬化）

- **完成时间**: 2026-06-29
- **修改文件**:
  - `src/songyan/models/context.py`: ContextPackage 新增 `mandatory_references` 字段
  - `src/songyan/agents/context_manager/__init__.py`: `assemble_context_package` 接收并传递 `mandatory_references`
  - `src/songyan/workflows/_helpers.py`: 新增 `_load_critical_mandatory_references()` 查询 critical orphan
  - `src/songyan/agents/writer.py`: `_render_prompt` 渲染 `mandatory_references_text`
  - `prompts/cards/writer/1.1.0.yaml` + `1.2.0.yaml`: 新增 mandatory_references 段落
  - `tests/test_task137_setting_recycling.py`: 追加 4 个测试
- **复跑结果** (`run-a225b713`): Ch12 health=3.0, orphaned=14。Writer 初稿对 5/7 mandatory_references 零提及。子项 A 单独不足。

### 子项 B（RuleAuditor 检测 + review_merger 转化）

- **完成时间**: 2026-06-29
- **修改文件**:
  - `src/songyan/models/review.py`: RuleAuditResult 新增 `mandatory_reference_issues` + `mandatory_reference_check_passed`
  - `src/songyan/agents/rule_auditor.py`: 新增 `_check_mandatory_references()` 检测逻辑
  - `src/songyan/workflows/_nodes.py`: rule_auditor_node / revision_handler_node 传入 `mandatory_references`
  - `src/songyan/workflows/review_merger.py`: `_convert_rule_to_issues` 将缺失项转化为 critical issue
  - `tests/test_task137_setting_recycling.py`: 追加 4 个测试
  - `tests/test_review_merger.py`: 追加 2 个测试
- **复跑结果** (`run-a225b713`): RuleAuditor 检出 5 个缺失，但 RevisionHandler patch 无法补救（rev-12-2 仍有 5 个缺失且被 abandoned）。
- **review_merger bug 修复**: 发现 cap=5 会截断 mandatory_reference issues，已修复为将 mandatory_reference 放在 issues 列表最前面。

### 结论

子项 A+B 建立了"注入 + 检测"双层闭环，但 RevisionHandler 只做 patch 无法修复"初稿完全缺失设定"的问题。后续通过 Task 138i（措辞硬化）和 Task 138j（回收提示）在源头提升 Writer 回收率。
