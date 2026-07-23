# Task 061: Ch2-Ch6 首轮失败根因分析

> **Phase**: V3.0 Layer 2 — 核心验证层（收尾）
> **优先级**: P2
> **依赖**: 058b
> **预计工作量**: 中（调查 ~1 小时）

---

## Goal

追溯 `scripts/run_batched_chapters.py` 中 Ch2-Ch6 连续 5 章首轮全部失败的根因（错误类型："Missing audit results @ done"），如果可复现则修复，否则输出根因分析文档。

## Context

058b 的 `058b_progress.json` 记录了以下异常：

| 章节 | 首轮 | 状态 | 耗时 |
|------|:---:|------|------|
| Ch2 | ❌ | "Missing audit results @ done" | 232s |
| Ch3 | ❌ | 同上 | 158s |
| Ch4 | ❌ | 同上 | 217s |
| Ch5 | ❌ | 同上 | 239s |
| Ch6 | ❌ | 同上 | 248s |
| Ch2-Ch6 (重试) | ✅ | 全部 accepted | ~210s/章 |
| Ch7-Ch30 | ✅ | 全部首轮 accepted | ~237s/章 |

5 连败在 Ch7 之后突然消失——如果问题是 LLM API 不稳定或模型行为随机，不会呈现这种"前 5 章团灭，第 7 章后全通"的模式。

可能的根因假设：

1. **test.db seed 不完整**：独立进程初始化的 test.db 中 Ch1 的 settlement/summary 缺失，导致 Ch2 的 ContextManager 加载失败 → Writer 生成的正文缺少上下文 → LLM Auditor 无法产出有效 review
2. **Ch1 版本链断裂**：Ch1 作为 seed，其 `accepted` 版本的 `version_id` 未正确注册，导致 Ch2 的 `load_recent_summaries()` 等查询返回空
3. **进程间状态泄露**：`run_batched_chapters.py` 的独立进程在 Ch2-Ch6 之间有某种状态污染（如共享的临时文件或环境变量），Ch7 后因为延迟/写入而被自然修复

## In Scope（必须完成）

- [ ] 阅读 `scripts/run_batched_chapters.py` 的完整流程：test.db 创建 → seed 导入 → 单章生成 → 清理
- [ ] 阅读 `evals/runner.py` 的 `import_seed_project()` 和 `import_seed_chapter()` 逻辑
- [ ] 检查 Ch1 seed 导入后的 DB 状态：`chapter_versions`（version_type=accepted）、`settlements`、`chapter_summaries` 是否完整
- [ ] 模拟单进程运行 Ch2，复现 "Missing audit results" 错误
- [ ] 如果能复现：追溯错误在 pipeline 中的精确位置（Writer? LLMAuditor? ReviewMerger?）
- [ ] 如果不能复现：输出根因分析文档，记录调查过程和可能性排序
- [ ] 如果找到 bug：修复并补充回归测试

## Out of Scope（明确不做）

- 不修改 `run_batched_chapters.py` 的整体架构
- 不修改 Agent 代码（除非找到明确 bug）
- 不重跑 Ch2-Ch6 验证
- 不分析 Ch7+ 的 pipeline 行为

## 验收标准

- [ ] 输出 `docs/review/061-ch2-ch6-root-cause.md`（含假设、调查路径、结论/可能性排序）
- [ ] 若找到 bug：补充修复 + 测试 + `tasks/061-ch2-ch6-root-cause-DONE.md`
- [ ] 不违反 AGENTS.md 任何规则
- [ ] 更新了 `docs/STATUS.md`

## 参考文档

- `scripts/run_batched_chapters.py` — 批量运行脚本
- `evals/runner.py` — `import_seed_project()` / `import_seed_chapter()`
- `evals/seeds/scifi_new_weird.json` — 项目 seed
- `evals/seeds/chapters/scifi_new_weird_ch1.md` — Ch1 seed 正文
- `projects/orbital_horror_058b/058b_progress.json` — 运行进度记录
- `docs/review/v30_layer2_runlog.jsonl` — 36 条运行日志