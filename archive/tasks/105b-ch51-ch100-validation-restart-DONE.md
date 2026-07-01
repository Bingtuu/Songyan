# Task 105b: Ch51-Ch100 流式验证重启 — DONE

> **完成日期**: 2026-06-16
> **状态**: ✅ 已完成（DG-1 未通过）

---

## 做了什么

Task 105b 是在 Task 105 基础设施和 Task 106-110 修复完成后，对 Ch51-Ch100 进行的完整流式验证重启。

1. **MEMO-001 修复**
   - `VectorStore.load_incremental()` 同步更新 `_embeddings`，确保增量加载后内存缓存与 DB 一致
   - `RAGRetriever` 真正复用缓存的 `VectorStore` 实例，避免每章重建 embedding

2. **清理临时文件**
   - 删除 `_tmp_git_fixup/` 目录及 ~20 个临时脚本
   - 清理 640 个过期 JSONL 日志和 Python 缓存

3. **专用验证 runner**
   - 新增 `scripts/run_task_105b_ch51_ch100.py`
   - 单章超时 10 分钟，全局超时 8 小时，3 连失败自动 halt
   - 写入 JSONL 指标日志，自动生成 markdown 报告

4. **执行 Ch51-Ch100 全自动验证**
   - 项目：`proj-e74ef1e4`（scifi / webnovel_intense）
   - 范围：Ch51–Ch100
   - 模式：`--auto-confirm`，无人工介入

---

## 改了哪些文件

| 文件 | 变更类型 | 说明 |
|------|---------|------|
| `src/songyan/rag/vector_store.py` | 修改 | `load_incremental()` 同步更新 `_embeddings` |
| `src/songyan/rag/retriever.py` | 修改 | 真正复用缓存的 `VectorStore` 实例 |
| `scripts/run_task_105b_ch51_ch100.py` | 新增 | 验证专用 runner |
| `logs/chapter_runs/run-*.jsonl` | 新增 | 50 章指标日志 |
| `logs/reports/task105b-progress-summary.txt` | 新增 | 实时进展摘要 |
| `logs/reports/report-run-7f15965b.md` | 新增 | 流式报告（仅含 Ch100，见下方限制） |

---

## 测试数据

### 实际验证结果（Ch51-Ch100 聚合）

```
覆盖章节: Ch51 ~ Ch100 (50/50)
QG 通过: 29
QG 失败: 21
达标率: 58.0%
Context Emergency: 41/50
平均 budget_used: 0.517
单章平均耗时: 160.8s
总运行时间: 134.0min
```

### 最近 15 章指标

| 章节 | QG | budget | words | rev | dur(s) |
|------|----|--------|-------|-----|--------|
| Ch86 | ✅ | 0.429 | 3728 | 0 | 144.0 |
| Ch87 | ❌ | 0.420 | 3738 | 0 | 113.5 |
| Ch88 | ❌ | 0.390 | 4177 | 1 | 139.6 |
| Ch89 | ❌ | 0.461 | 3817 | 0 | 111.9 |
| Ch90 | ✅ | 0.535 | 3286 | 0 | 180.8 |
| Ch91 | ❌ | 0.389 | 3789 | 1 | 136.4 |
| Ch92 | ❌ | 0.826 | 3779 | 1 | 112.0 |
| Ch93 | ✅ | 0.441 | 3348 | 0 | 140.4 |
| Ch94 | ✅ | 0.384 | 4104 | 0 | 151.2 |
| Ch95 | ❌ | 0.859 | 4197 | 1 | 114.5 |
| Ch96 | ✅ | 0.845 | 2821 | 1 | 155.1 |
| Ch97 | ❌ | 0.874 | 4192 | 1 | 128.7 |
| Ch98 | ❌ | 0.834 | 2940 | 0 | 117.5 |
| Ch99 | ✅ | 0.837 | 4190 | 1 | 179.2 |
| Ch100 | ✅ | 0.789 | 3611 | 2 | 208.1 |

---

## 验证结果

- **ruff 检查**: 无新增 lint 错误
- **稳定性**: 50/50 章全部成功生成，无失败章节，未触发 3-strike halt
- **DG-1 决策门**: ❌ 未通过（达标率 58.0% < 75%）
- **budget 控制**: 平均 0.517，无 `budget_used > 1.0` 章节

---

## 已知限制

1. **DG-1 未达标**: QG 通过率 58.0%，低于 75% 目标。主要失败原因集中在 length_score、coherence_major、readability_score。
2. **后期 budget 爬升**: Ch90 后 `budget_used` 显著上升至 0.8–0.9 区间，Context Emergency 频繁触发，显示活跃信息池仍偏重。
3. **报告生成器限制**: `logs/reports/report-run-7f15965b.md` 只统计了最后一章 Ch100，因为 runner 为每章创建独立 `run_id`，`streaming_report.generate_report` 按 run_id 过滤。完整 50 章数据需通过 JSONL 聚合获取。
4. **Settlement 验证警告**: Ch99-Ch100 出现设定 key 格式不符合 `category.subcategory.name` 规范的 warnings，已过滤但标记为 `needs_human_review`。

---

## 下一步

- 按 DG-1 规则，达标率 < 75% → 启动 Task 108-109 活跃信息池控制（已在代码层面完成，但可能需要针对 Ch90+ 后期 budget 爬升做进一步调优）
- 或推进 Task 110：Ch101-Ch150 流式验证 + 决策门 DG-2，观察 150 章场景下的真实表现
