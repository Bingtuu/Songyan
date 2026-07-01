# Task 059: JSONL 监控诊断补全

> **Phase**: V3.0 Layer 2 — 核心验证层（收尾）
> **优先级**: P0
> **依赖**: 058a, 058c
> **预计工作量**: 小（~30 分钟）

---

## Goal

修复 JSONL 运行日志中 `error_stage` 空值和 `continuity_health_score` / `content_preservation_ratio` 全 null 的问题，增加 `_metrics_version` 字段以区分"版本不支持"和"采集失败"。

## Context

058b 的 30 章运行日志暴露了三个监控基建的缺陷：

1. **error_stage 大面积空值**：38 条 error 条目中，31 条的 `error_stage` 为空字符串。`_run_single_chapter` 的 except 分支只捕获异常消息，未记录当前 pipeline 阶段名。
2. **continuity_health_score 全 null**：058c 已将 ContinuityAuditor 移入 `_run_single_chapter`，但 058b 的 runlog 是修复前数据。需要验证当前代码确实能采集到该字段。
3. **content_preservation_ratio 全 null**：同上。
4. **JSONL schema 无版本标识**：后续分析时无法区分"null 因为版本不支持"和"null 因为采集失败"。

## In Scope（必须完成）

- [ ] `_run_single_chapter` 的 except 分支记录当前 pipeline 阶段名（`"writer"`, `"rule_auditor"`, `"llm_auditor"`, `"revision_handler"`, `"settlement"` 等）
- [ ] `ChapterRunLog` 模型增加 `_metrics_version: str = "v1"` 字段
- [ ] `to_jsonl()` 序列化包含 `_metrics_version`
- [ ] 代码审查确认 058c 的 `continuity_health_score` 和 `content_preservation_ratio` 接线正确
- [ ] 新增 5-8 个专项测试

## Out of Scope（明确不做）

- 不改 pipeline 流程逻辑
- 不改 `_run_logger.py` 的指标采集算法
- 不修复 RAG
- 不修复 Settlement 数据噪声

## 接口契约

```python
# ChapterRunLog 新增字段
class ChapterRunLog(BaseModel):
    # ... 现有字段 ...
    _metrics_version: str = Field(default="v1", description="指标采集版本号，用于区分字段释义变化")

# _run_single_chapter except 分支伪代码
async def _run_single_chapter(...) -> ChapterRunLog:
    _stage = "init"
    try:
        _stage = "writer"; ...
        _stage = "rule_auditor"; ...
        # ...
    except Exception as e:
        return _build_error_log(e, stage=_stage)
```

## 数据模型

```python
class ChapterRunLog(BaseModel):
    # 现有字段保持不变
    _metrics_version: str = Field(default="v1")
```

## 测试要求

### Layer 1: 模型测试
- [ ] `ChapterRunLog` 实例化后 `_metrics_version == "v1"`
- [ ] `to_jsonl()` 输出包含 `"_metrics_version":"v1"`
- [ ] 旧版 JSONL（无 `_metrics_version`）反序列化不抛异常

### Layer 2: 模块测试
- [ ] `_run_single_chapter` 在 writer 阶段抛异常时 `error_stage == "writer"`
- [ ] `_run_single_chapter` 在 settlement 阶段抛异常时 `error_stage == "settlement"`
- [ ] `_run_single_chapter` 成功时 `error_stage` 为空（不填）
- [ ] `log_chapter_run` 正确传入 `_metrics_version`

## 验收标准（Acceptance Criteria）

- [ ] `pytest tests/test_run_logger.py -v` 全部通过 + 新增测试通过
- [ ] 代码符合 AGENTS.md 规范
- [ ] 不违反任何不可违背规则
- [ ] 更新了 `docs/STATUS.md`
- [ ] 生成了 `tasks/059-jsonl-diagnostics-DONE.md` 交接文件

## 参考文档

- `src/songyan/models/run_log.py` — ChapterRunLog 模型定义
- `src/songyan/workflows/phase2_graph.py` — `_run_single_chapter` 实现
- `src/songyan/workflows/_run_logger.py` — RunLogger 服务
- `docs/review/v30_layer2_runlog.jsonl` — 058b 运行日志（36 条）