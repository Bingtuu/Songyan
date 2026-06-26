# Task 121m: QG False 硬拦截与元标记泄漏清理 — DONE

- **状态**: DONE
- **完成日期**: 2026-06-22（文档归档 2026-06-26）
- **类型**: V5.1 preflight / 工程阻断

## 目标摘要

阻断两类劣质数据进入下游上下文池：
1. `quality_gate_passed=False` 的章节不再执行 settlement 提取、状态写入、RAG 索引和生命周期清理。
2. Writer 输出中不再出现 `<!-- 新设定:... -->` 等 HTML 元标记，保持叙事正文纯净。

## 关键改动 / 交付物

- `src/songyan/workflows/_nodes.py`
  - `settlement_extractor_node` 在调用 `extract_settlement` 前增加 `_quality_gate_passed=False` 硬拦截，返回 `status="settlement_review"`，`_settlement_needs_human_review=True`，阻止劣质上下文污染。
- `src/songyan/agents/writer.py`
  - 后处理 `_extract_body` 改为强制清理所有 HTML 注释 `<!--...-->`，并保留对旧版 `[[新设定:...]]` 可见标记的兜底清理。
- `prompts/cards/writer/1.0.9.yaml`
  - `new_setting_mark` section 重写为：新设定由 SettlementExtractor 自动识别，正文禁止任何元数据标记（HTML 注释、`[[新设定:...]]` 及内部工作标记）。
- `tests/test_108_core_nodes.py`
  - 新增 `TestSettlementExtractorNodeQGFalseBlock`：验证 QG false 时不提取、不应用 settlement，不生成 summary，进入 settlement_review。
- `tests/test_writer.py`
  - 新增 `test_strips_html_comments`、`test_strips_multiline_html_comments`、`test_strips_legacy_bracket_settings`：验证 HTML 注释与旧版标记被彻底移除。

## 验证证据

- 任务原文档记录：`pytest tests/ -q` **1729 passed**，`ruff check src/ tests/` 通过。
- `docs/STATUS.md` 记录：Task 121m **已完成**，项目测试 **1731 passed**。
- 核心单测覆盖：
  - `tests/test_108_core_nodes.py::TestSettlementExtractorNodeQGFalseBlock::test_qg_false_blocks_settlement_and_returns_review`
  - `tests/test_writer.py::TestWriterPostprocess::test_strips_html_comments`
  - `tests/test_writer.py::TestWriterPostprocess::test_strips_multiline_html_comments`
  - `tests/test_writer.py::TestWriterPostprocess::test_strips_legacy_bracket_settings`
- 后续 `run-4ff41095`（Task 121o）验证 Ch1-Ch18 成功、ContextEmergency 0 次、AutoHalt 0 次。

## 遗留 / 后续

- 无本任务直接遗留项。
- 已按计划在 Task 121o 中确认 QG false 版本不再进入 settlement、正文无元标记泄漏，并稳定越过 Ch13 / Ch18。
