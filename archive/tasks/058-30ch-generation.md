# Task 058: 30 章封闭验证生成

> **Phase**: V3.0 Layer 2 — 核心验证层
> **优先级**: P0
> **依赖**: Layer 0 + Layer 1 全部完成
> **预计工作量**: 大（取决于 API 速度，~36-60 小时生成等待 + 1 天分析）

---

## Goal

在全自动 `--auto-confirm` 模式下，从现有基线连续生成到 Ch30，无崩溃、无数据丢失、连续性健康 >= 8/10。

## Context

这是 V3.0 最核心的实验。前面的所有 Layer 0/1 工作都是为它做准备。成功意味着：Songyan 的工程底座已被证明可以支撑长篇小说连续生成。

## In Scope（必须完成）

- [ ] **运行配置**:
  - Seed: scifi, mode: webnovel_intense
  - 复用 `orbital_horror_v2` 或新建 scifi 项目
  - `--auto-confirm`，不设任何 human gate
- [ ] **监控脚本**: 每章生成后自动记录指标到 `docs/review/v30_layer2_runlog.jsonl`
  - draft_words, final_words, version_count, content_preservation_ratio
  - rule_audit_score, budget_used, elapsed_seconds
  - settlement_complete, continuity_score
- [ ] **每 3 章额外检查**: ContinuityAuditor 自动运行，记录 orphaned / forgotten / mismatch
- [ ] **失败处理**:
  - database locked（重试 3 次后仍失败）→ 暂停，记录
  - LLM 超时（重试 3 次后仍失败）→ 暂停，记录
  - RevisionHandler 截断（content < 50%）→ 自动回退到 pre-revision 版本 accept
  - Settlement 部分失败 → 标记 needs_human_review，继续下一章

## Out of Scope（明确不做）

- 不做 Prompt 优化（字数控制、钩子质量提升属于 V3.1）
- 不做人工盲测或质量评分
- 不做多 genre 交叉验证

## 接口契约

```python
# 每章日志结构
class ChapterRunLog(BaseModel):
    chapter: int
    timestamp: str
    status: Literal["accepted", "paused", "failed"]
    metrics: dict[str, float | int | bool]
    warnings: list[str]
```

## 验收标准

- [ ] 30 章全部生成完成，无不可恢复的崩溃
- [ ] 连续性健康分数全程 >= 8/10
- [ ] 每章 settlement 写入完整性 = 100%
- [ ] Content preservation ratio 全程 >= 0.7
- [ ] 生成速度无指数衰减（30 章平均耗时 <= 3 分钟/章）
- [ ] 运行日志完整归档至 `docs/review/v30_layer2_runlog.jsonl`
- [ ] `docs/STATUS.md` 更新
- [ ] 生成 `tasks/058-30ch-generation-DONE.md`

## 参考文档

- `prd/v3.0-stability-closed-loop.md` — 6. Layer 2
