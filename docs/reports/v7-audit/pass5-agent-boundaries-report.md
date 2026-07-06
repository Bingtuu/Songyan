# Pass 5: Agent 边界与职责审计报告

## 执行摘要

- 发现总数: 1
- P0: 0, P1: 0, P2: 1
- 关键结论: 各 Agent 职责边界总体清晰，未发现 Writer/Auditor 越界修改正文或 Settlement 在 accept 外触发的情况。唯一需要关注的是 `settlement_extractor_node` 中 settlement 后长尾处理（RAG/蒸发/摘要/线索/调度/输入侧治理）已超出 SettlementExtractor Agent 本身的职责范围，与 Pass 1/2 的发现一致。

## 检查项与发现

### 5.1 Writer 只做初稿

- **级别**: 通过
- **文件**: `src/songyan/agents/writer.py`
- **方法**: 检查函数签名、返回类型、是否调用修订/结算/审查逻辑
- **结果**:
  - 入口函数 `write_chapter`（`:552`）返回 `ChapterVersion(version_type="draft", ...)`（`:735`）。
  - 未搜索到对 `apply_settlement`、`extract_settlement`、`revision_handler`、`run_llm_audit`、`run_rule_audit` 的调用。
  - 未搜索到对 `chapter_versions.content` 或 `UPDATE chapter_versions` 的修改。
- **结论**: Writer 仅负责生成 `draft` 类型初稿，不越界。

### 5.2 RevisionHandler 只做 patch

- **级别**: 通过
- **文件**: `src/songyan/agents/revision_handler/__init__.py`
- **方法**: 检查 issue 筛选逻辑和 fix_type 处理
- **结果**:
  - `filter_patchable_issues`（`:56`）明确只保留 `fix_type == "patch"` 的 critical/major issue。
  - 搜索 `fix_type="patch"` 共 8 处，未发现 `fix_type="rewrite_scene"` 被允许进入自动修订。
  - `run_revision` 是主入口，内部调用分段修订和 patch 应用。
- **结论**: RevisionHandler 只做局部 patch，不整章重写。

### 5.3 Auditor 不修改正文

- **级别**: 通过
- **文件**: `src/songyan/agents/rule_auditor.py`, `src/songyan/agents/llm_auditor.py`, `src/songyan/agents/literary_auditor.py`
- **方法**: 检查入口函数签名和返回值
- **结果**:
  - `run_rule_audit(content, ...)` 返回 `RuleAuditResult`（`:302`）。
  - `run_llm_audit(content, ...)` 返回 `LLMAuditResult`（`:221`）。
  - `run_literary_audit(content, ...)` 返回 `LiteraryAuditResult`（`:161`）。
  - 均未接收 `ChapterVersion` 对象进行写入，未修改 `chapter_versions.content`。
- **结论**: 审查层只返回审查结果，不修改正文。

### 5.4 SettlementExtractor 只在 accept 后触发

- **级别**: 通过
- **文件**: `src/songyan/workflows/_nodes.py:2256-2410`
- **方法**: 检查 `settlement_extractor_node` 调用点和前置条件
- **结果**:
  - `settlement_extractor_node` 仅在 `human_confirm_router` 的 `accept` 分支后被 LangGraph 调度（`phase1_graph.py:318`）。
  - 节点内部检查 `_qg_passed is False and not _degraded_accept` 时 warning 并仍可继续（ degraded accept 路径）。
  - `_skip_settlement` 为 True 时跳过结算（`:2323`）。
- **结论**: edit/reject/back 不会触发 settlement；accept 是 settlement 的唯一入口。

### 5.5 GoalPlanner / CreativeDirector 不写正文

- **级别**: 通过
- **文件**: `src/songyan/agents/goal_planner.py`, `src/songyan/agents/creative_director/__init__.py`
- **方法**: 检查入口函数签名和返回类型
- **结果**:
  - `define_chapter_goal`（`goal_planner.py:236`）返回 `ChapterGoal`。
  - `generate_creative_brief`（`creative_director/__init__.py:304`）返回 `CreativeBrief`。
  - 两者均未调用 `write_chapter` 或操作 `chapter_versions.content`。
- **结论**: 规划层只输出结构化规划对象。

### 5.6 ContextManager 不做审查判断

- **级别**: 通过
- **文件**: `src/songyan/agents/context_manager/__init__.py`
- **方法**: 搜索是否调用任何 Auditor 或 QualityGate
- **结果**: `rg 'run_rule_audit|run_llm_audit|quality_gate|ScoreAggregator|evaluate_all_gates' src/songyan/agents/context_manager/__init__.py` 无命中。
- **结论**: ContextManager 只负责组装上下文包，不做审查判断。

### 5.7 SettlementExtractor 职责漂移（P2）

- **级别**: P2
- **文件**: `src/songyan/agents/settlement_extractor/__init__.py`, `src/songyan/workflows/_nodes.py:2256-2645`
- **问题描述**: 
  - `settlement_extractor/__init__.py` 的模块 docstring 明确声明“章节 accept 后的结构化状态结算”。
  - 但实际 `settlement_extractor_node` 中，结算核心仅占约 150 行，其余 500+ 行是 RAG 索引、setting 蒸发、分层摘要、plot thread 更新、foreshadowing schedule 推进、输入侧治理。
- **修复建议**: 将非结算逻辑拆出到独立节点或 Service，让 `settlement_extractor_node` 回归“结算提取 + 验证”单一职责（与 Pass 2 建议一致）。

## 通过项

- [x] Writer 只生成 draft，不修改/重写/结算。
- [x] RevisionHandler 只处理 patch 类型 issue。
- [x] Rule/LLM/Literary Auditor 不修改正文。
- [x] Settlement 只在 accept 后触发。
- [x] GoalPlanner / CreativeDirector 不写正文。
- [x] ContextManager 不做审查判断。

## 待修复清单

| ID | 级别 | 问题 | 建议修复文件 | 验证命令 |
|----|------|------|--------------|----------|
| 5.7 | P2 | `settlement_extractor_node` 职责漂移，包含大量非结算后处理 | `src/songyan/workflows/_nodes.py` + 新增 Service/节点 | `pytest tests/test_phase1_graph.py tests/test_settlement_extractor.py -q` |

---

> 下一 Pass: [Pass 6 质量门与审查体系审计](pass6-quality-gates-report.md)
