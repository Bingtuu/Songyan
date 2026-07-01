# Task 058a: 监控与韧性基础设施

> **Phase**: V3.0 Layer 2 — 核心验证层
> **优先级**: P0
> **依赖**: Layer 0 + Layer 1 全部完成（052~057）
> **预计工作量**: 1-2 天

---

## Goal

建立可支撑 30 章连续生成的监控和失败处理机制，使 058b 的 30 章运行无需人工干预即可自愈常见故障。

## Context

已有基础设施：
- `phase2_graph.py` 的 `run_project_pipeline` 支持 `auto_confirm=True`
- 每 3 章自动运行 `ContinuityAuditor`（阈值 hardcode 为 7.0）
- `scripts/run_batched_chapters.py` 有 progress.json + LLM 调用统计
- 053 已修复 database locked（WAL + 指数退避重试）

缺失：
- 每章详细指标未持久化到结构化日志
- RevisionHandler 截断无自动回退
- Settlement 部分失败会阻塞流程

## In Scope

- [ ] **`ChapterRunLog` 模型**: `src/songyan/models/chapter_run_log.py`
  - 字段: chapter, timestamp, status, metrics(dict), warnings(list[str])
  - metrics 包含: draft_words, final_words, version_count, content_preservation_ratio, rule_audit_score, budget_used, elapsed_seconds, settlement_complete
- [ ] **`RunLogger` 服务**: `src/songyan/evals/run_logger.py`
  - 写入 `docs/review/v30_layer2_runlog.jsonl`（追加模式，每章一行 JSON）
  - 提供 `log_chapter(log: ChapterRunLog)` 和 `close()` 方法
- [ ] **`phase2_graph.py` 指标注入**:
  - 在 `_run_single_chapter` 中收集本章指标
  - 调用 `RunLogger.log_chapter()` 持久化
- [ ] **失败处理增强**:
  - RevisionHandler content < 50% → 自动 accept pre-revision 版本
  - Settlement `needs_human_review` → 记录警告，继续下一章
- [ ] **ContinuityAuditor 阈值可配置**: `health_score_threshold` 参数化（默认 7.0）
- [ ] **监控脚本增强**: `scripts/run_batched_chapters.py` 接入 `RunLogger`

## Out of Scope

- 不修改任何 Agent Prompt
- 不启动实际 30 章生成
- 不做人眼质量评估

## 测试要求

- [ ] `pytest tests/ --ignore=tests/integration -x -q` 全部通过
- [ ] mock 运行 3 章，验证 JSONL 输出格式正确
- [ ] RevisionHandler 截断回退路径有单元测试

## 验收标准

- [ ] `ChapterRunLog` 模型完整定义
- [ ] mock/短程运行下 JSONL 日志能正确记录所有指标
- [ ] 失败处理路径有单元测试覆盖
- [ ] `docs/STATUS.md` 更新
- [ ] 生成 `tasks/058a-monitoring-infrastructure-DONE.md`

## 参考文档

- `tasks/058-30ch-generation.md` — 父 Task 规格
- `scripts/run_batched_chapters.py` — 现有运行脚本
- `src/songyan/workflows/phase2_graph.py` — 多章编排层
