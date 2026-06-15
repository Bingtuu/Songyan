# Task 058a: 监控与韧性基础设施（已完成）

> **Phase**: V3.0 Layer 2 — 核心验证层
> **优先级**: P0
> **依赖**: Layer 0 + Layer 1 全部完成（052~057）
> **完成日期**: 2026-06-04
> **执行者**: AI Agent

---

## 完成项

- [x] **`ChapterRunLog` 模型**: `src/songyan/models/run_log.py`
  - 字段: log_id, run_id, project_id, chapter_number, started_at, finished_at
  - 结果字段: success, error, error_stage
  - 质量指标: word_count, rule_violations, rule_audit_score, llm_audit_issues, llm_audit_critical, revision_rounds, content_preservation_ratio
  - 连续性: continuity_health_score
  - Settlement: settlement_success, settlement_needs_human_review
  - 资源: duration_sec
  - 序列化: `to_jsonl()` 输出单行 JSON
- [x] **`RunLogger` 服务**: `src/songyan/workflows/_run_logger.py`
  - `collect_chapter_metrics()` — 从数据库异步查询版本/审查指标
  - `build_chapter_run_log()` — 组装日志对象
  - `write_run_log()` — 追加写入 `logs/chapter_runs/{run_id}.jsonl`
  - `log_chapter_run()` — 一站式记录（收集 → 构建 → 写入）
  - 写入失败 graceful degradation（记录 warning，不抛异常）
- [x] **`phase2_graph.py` 指标注入**:
  - `_run_single_chapter()` 内记录 started_at / finished_at / duration_sec
  - 成功/失败均调用 `log_chapter_run()` 持久化
  - 传递 `final_state`（含 revision_rounds, content_preservation_ratio）和 `final_version_id`
- [x] **失败处理增强 — RevisionHandler 截断回退**:
  - `revision_handler_node()` 检查 `output.content_preservation_ratio < 0.5`
  - 截断时跳过 `save_revision_output()`，直接返回原始 version_id
  - 在 state 中记录 `_content_preservation_ratio` 供监控采集
- [x] **失败处理增强 — Settlement 部分失败标记继续**:
  - `settlement_extractor_node()` 捕获 `LLMError` / `LLMResponseParseError`
  - 不返回 `"status": "error"`，而是标记 `_settlement_needs_human_review: True`
  - summary 和 RAG 继续执行（非阻塞）
  - 返回 `"status": "done"`，流程不中断
- [x] **ContinuityAuditor 阈值可配置**:
  - `run_project_pipeline()` 新增 `continuity_health_threshold: float = 7.0` 参数
  - 替换原 hardcode 的 `7.0` 比较逻辑
- [x] **测试**: `tests/test_run_logger.py` — 13 passed
  - `_compute_rule_score` 完美/违规/None 三种场景
  - `collect_chapter_metrics` 有数据/无版本/无 report 三种场景
  - `build_chapter_run_log` 成功/失败场景
  - `write_run_log` 创建/追加/写入失败三种场景
  - `ChapterRunLog.to_jsonl()` 序列化验证
- [x] **现有测试兼容**: `tests/test_phase2_graph.py` 添加 `log_chapter_run` mock

---

## 关键决策

### 指标收集在 phase2_graph 层面而非 Phase1State
遵守"LangGraph state 只存 ID"铁律，`_content_preservation_ratio` 作为轻量标量临时存入 state 供上层采集，不存完整业务对象。`ChapterRunLog` 的指标从数据库（version + review_reports）+ state 标量联合查询，不依赖 state 膨胀。

### Settlement 部分失败不阻塞
`settlement_extractor_node` 中 LLM 提取 settlement 失败时，流程继续到 summary 和 RAG，最终返回 `done`。这是基于" settlement 可人工补录，但中断整批生成的代价更高"的权衡。

### JSONL 而非 SQLite 存储日志
监控日志是高频追加、只读分析的场景，JSONL 更适合后续用 jq/pandas 做离线分析，避免给 SQLite 增加写入压力。

---

## 基线验证

| 指标 | 目标 | 实际 |
|------|------|------|
| 全量测试通过 | ≥ 1020 passed | **1025 passed**（排除 integration + 4 个遗留 eval_runner pydantic 失败）|
| 新测试覆盖 | 13 个 | **13 passed** |
| 无文件系统泄漏 | JSONL 写入可控 | 写入 `logs/chapter_runs/` 目录，测试使用临时目录 |

---

## 交付物

- `src/songyan/models/run_log.py` — `ChapterRunLog` Pydantic 模型
- `src/songyan/workflows/_run_logger.py` — 指标收集 + JSONL 写入服务
- `src/songyan/workflows/phase2_graph.py` — `_run_single_chapter` 计时/日志注入 + `continuity_health_threshold` 参数
- `src/songyan/workflows/_nodes.py` — `revision_handler_node` 截断回退 + `settlement_extractor_node` 部分失败标记
- `src/songyan/models/__init__.py` — `ChapterRunLog` 导出
- `tests/test_run_logger.py` — 13 个单元测试
- `tests/test_phase2_graph.py` — mock `log_chapter_run` 兼容更新
- `docs/STATUS.md` — Task 状态更新

---

## 遗留风险

| 风险 | 严重度 | 说明 |
|------|--------|------|
| `TestGraphStructure` 超时 | 中 | `test_phase1_graph.py::TestGraphStructure` 在部分环境下 LangGraph 编译超时，与 058a 修改无关 |
| eval_runner 4 个 pydantic 失败 | 低 | 遗留问题（`merged_review_report_id=None`），与 058a 无关 |
| `scripts/run_batched_chapters.py` 未显式接入 | 低 | 脚本调用 `run_project_pipeline`，日志已自动采集；无需额外修改 |

---

## 下一步

**Task 058b: 30 章实际封闭验证生成**
- 使用 `run_project_pipeline(auto_confirm=True)` 生成 30 章
- 观察 JSONL 日志中的指标趋势，识别异常章节
- 验证失败处理增强在真实场景下的自愈效果

**Task 058c: 验证结果分析 + 问题修复**
- 分析 30 章 JSONL 日志，统计失败率、平均 revision 轮数、content_preservation_ratio 分布
- 修复 058b 中发现的任何问题
