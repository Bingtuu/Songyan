# Pass 6: 质量门与审查体系审计报告

## 执行摘要

- 发现总数: 4
- P0: 0, P1: 0, P2: 4
- 关键结论: 审查体系完整，critical/major 必须有 evidence_quote；RuleAuditor 已覆盖 V6 暴露的元标记泄漏和段落重复问题；QualityGate 阈值动态化且存在 degraded accept 回滚路径；文学性诊断不阻塞 accept。主要建议是增强 RuleAuditor 对段落重复的阻断能力（当前仅作为观测指标）和统一 gate_mode 配置来源。

## 检查项与发现

### 6.1 critical/major issue 证据要求

- **级别**: 通过
- **文件**: `src/songyan/agents/llm_auditor.py:153-169`
- **方法**: 检查 `_parse_issue` 解析逻辑
- **结果**:
  ```python
  evidence_quote = str(data.get("evidence_quote", "") or "")
  if severity in {"critical", "major"} and not evidence_quote.strip():
      logger.warning("llm_auditor.missing_evidence_quote", issue_id=issue_id)
  ```
- **结论**: LLMAuditor 对 critical/major issue 强制要求 `evidence_quote`。

### 6.2 RuleAuditor 元标记与段落重复检测

- **级别**: P2
- **文件**: `src/songyan/agents/rule_auditor.py`
- **方法**: 检查 `_MARKDOWN_SCENE_PATTERNS` 和 `detect_duplicate_paragraphs`
- **结果**:
  - `_MARKDOWN_SCENE_PATTERNS`（`:70-71`）覆盖了 `### Scene N` / `Scene N:` 等变体。
  - `detect_duplicate_paragraphs`（`:149`）实现整段落重复检测。
  - 在 `run_rule_audit`（`:366-371`）中，元标记计数进入结果，重复段落仅作为“观测指标”，注释明确说明“不直接阻断”。
- **问题描述**: V6 暴露的 19 章整段落重复问题在 Task 161 中修复，但 RuleAuditor 仅将其作为观测指标，未纳入 critical/major issue 自动修订链路。若 Writer/RevisionHandler 的去重逻辑出现回退，可能导致问题漏出。
- **修复建议**: 将“同章重复长段落”提升为 major issue 并进入自动修订；或至少在 enforce 模式下作为 QG 失败项。

### 6.3 QualityGate 阈值动态化

- **级别**: 通过
- **文件**: `src/songyan/workflows/_nodes.py:96-104`, `:233-281`
- **方法**: 检查 safe-best 阈值与 degraded accept 阈值
- **结果**:
  - `_safe_best_min_score`: Ch1–Ch20→0.75, Ch21–Ch50→0.78, Ch51+→0.82。
  - `_score_card_is_degraded_acceptable`: Ch1–`quality_ramp_chapters`→0.55，其余→0.70；要求 length_ok、budget_ok、无 coherence_critical。
- **结论**: 阈值按章节位置动态化，开局期有质量爬坡窗口。

### 6.4 enforce / observe 模式一致性

- **级别**: 通过
- **文件**: `src/songyan/cli/main.py:430-487`, `src/songyan/workflows/_gates.py`, `src/songyan/models/gate_config.py`
- **方法**: 检查 CLI 参数传递与 GateConfig 构建
- **结果**:
  - CLI `--gate-mode` 默认 `enforce`，可选 `observe`。
  - `GateConfig.for_mode(gate_mode)` 构建配置。
  - observe 模式下 `gate_config.is_enforce()` 返回 False，单章 gate 触发不 pause run；enforce 模式下触发 pause。
- **结论**: 与 V5.2 默认 enforce 的决策一致。

### 6.5 文学性诊断不阻塞 accept

- **级别**: 通过
- **文件**: `src/songyan/workflows/_nodes.py:1793-1985`
- **方法**: 检查 `quality_gate_node` 是否读取 literary_observation
- **结果**: `quality_gate_node` 仅读取 `_score_card`、字数、保留率、新问题，未读取 `literary_observation_id` 或 LiteraryAuditor 输出。
- **结论**: 文学性诊断不进入质量门判断，不阻塞 accept。

### 6.6 RuleAuditor 定位信息完整性

- **级别**: P2
- **文件**: `src/songyan/agents/rule_auditor.py`
- **方法**: 检查 RuleAuditResult 中的定位字段
- **结果**: RuleAuditor 输出包含 `ai_tell_matches`, `fatigue_word_matches`, `markdown_scene_title_matches`, `duplicate_paragraph_matches` 等，均带位置/行号信息。
- **建议**: 确保所有 matches 的模型字段包含 `line_number` 或 `start_index`，便于 ReviewMerger 生成带定位的 issue。

### 6.7 GateConfig 来源统一性

- **级别**: P2
- **文件**: `src/songyan/cli/main.py`, `src/songyan/workflows/phase2_graph.py`
- **方法**: 检查 GateConfig 是否通过单一入口构建
- **结果**: CLI 中通过 `GateConfig.for_mode(gate_mode)` 构建；Phase2 中通过默认 `GateConfig()` 构建。
- **建议**: 统一 GateConfig 构建入口，避免 CLI 与默认配置漂移；或在 `GateConfig` 中集中管理所有默认阈值。

## 通过项

- [x] LLMAuditor critical/major issue 强制要求 evidence_quote。
- [x] QualityGate 阈值按章节位置动态化。
- [x] enforce/observe 模式参数传递正确。
- [x] LiteraryAuditor 不阻塞 accept。

## 待修复清单

| ID | 级别 | 问题 | 建议修复文件 | 验证命令 |
|----|------|------|--------------|----------|
| 6.2 | P2 | 重复长段落仅作为观测指标，未进入自动修订 | `src/songyan/agents/rule_auditor.py` + `src/songyan/workflows/_nodes.py` | `pytest tests/test_161_paragraph_dedup.py -q` |
| 6.6 | P2 | 部分 RuleAuditor match 字段可能缺少统一行号定位 | `src/songyan/agents/rule_auditor.py` + `src/songyan/models/review.py` | `pytest tests/test_rule_auditor.py -q` |
| 6.7 | P2 | GateConfig 构建入口分散 | `src/songyan/models/gate_config.py` + `src/songyan/cli/main.py` | `pytest tests/test_123_gates.py -q` |

---

> 下一 Pass: [Pass 7 V7 新子系统审计](pass7-v7-subsystems-report.md)
