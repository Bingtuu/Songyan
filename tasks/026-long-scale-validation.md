# Task 026: 10章长篇验证 + 长尺度问题修复

## 状态

✅ **已完成** — Ch2~Ch11 全部完成入库（10/10章），Markdown 已导出

## 目标

完成《轨道上的怪谈》10章科幻长篇的真实 LLM 端到端验证，识别并修复长尺度运行中的系统性问题。

## 已完成验证（2026-05-30）

### 入库章节

| 章节 | 字数(v1) | 字数(v2) | 场景数 | 评分 | 耗时 | 状态 |
|------|---------|---------|--------|------|------|------|
| Ch2 | 4632 | 4619 | 2 | 8.46 | 194s | ✅ |
| Ch3 | 3927 | 3974 | 2 | 8.23 | 200s | ✅ |
| Ch4 | 3483 | 3549 | 1 | 8.21 | 214s | ✅ |
| Ch5 | 4458 | 4518 | ? | ? | 207s | ✅ |

### 跨章状态传递验证
- `previous_summary` 正确从 DB 读取并注入每章 GoalPlanner
- Summaries 表记录正常增长（Ch2→Ch5）
- 设定快照从 8 个（种子）→ 17+ 个（Ch4 后）
- 伏笔从 0 → 8+ 个（Ch4 后）

## 已发现的长尺度问题

### P0 — 上下文膨胀
- **现象**: Ch4 出现 `context_manager.prune_start`（预算 8000，实际 10320，超支 2320 tokens）
- **原因**: `summaries` + `setting_snapshots` + `foreshadowings` + `character_states` 随章节线性累积
- **当前缓解**: summary 200字符截断、RECENT_SUMMARY_LIMIT=3
- **需要**: 更强的 prune 策略（setting 去重/合并、character_states 增量 only、foreshadowing 过期清理）

### P1 — Writer 字数与场景控制漂移
- **现象**: 目标 3200，实际 3483~4632（偏差 +9%~+45%）；Ch4 scenes=1（低于预期 2）
- **原因**: 长尺度下 Writer 对字数约束的遵守度下降；场景清单预输出可能失效
- **需要**: 在 prompt 中强化字数硬约束，或增加字数超限的显式惩罚

### P2 — Settlement 精度下降
- **现象**: Ch3 `validation_failed`（source_quote 未在正文找到）；LLM 持续 hallucinate 不存在角色 ID
- **原因**: 随着设定复杂化，LLM 对 source_quote 的引用精度下降；角色 ID 格式混乱
- **当前缓解**: 白名单过滤跳过不存在角色、validation_failed 降级为 needs_human_review
- **需要**: settlement prompt 中增加 source_quote 长度限制（≤100字）、角色 ID 格式示例强化

### P3 — 成本与时间估算
- **单章实际**: ~7-10 LLM calls，~¥0.11，~200s（revision=1 轮）
- **10章预估**: ~¥1.10，~35-50 分钟
- **瓶颈**: Writer（~50s）+ LLMAuditor（~20s）+ Settlement（~15s）

## 明日计划

1. **继续验证 Ch6~Ch11**（使用 `run_batched_chapters.py`，每批 2-3 章）
2. **观察上下文膨胀趋势**: 记录每章的 `budget_used` 和 `prune` 次数
3. **收集完整数据后分析**:
   - setting_snapshots 增长曲线
   - foreshadowings 增长曲线
   - 每章评分变化趋势
   - 字数偏差趋势
4. **根据数据决定修复优先级**

## 运行命令

```bash
# 已完成的 Ch2~Ch5 在数据库 evals/output/multi_chapter_scifi_20260530_233510/test.db
# 项目 ID: proj-bcf431d0

# 继续 Ch6~Ch8
export PYTHONIOENCODING=utf-8
export SONGYAN_MAX_REVISION_ROUNDS=1
PYTHONPATH=. python scripts/run_batched_chapters.py \
  --seed scifi \
  --project-id proj-bcf431d0 \
  --output-dir evals/output/multi_chapter_scifi_20260530_233510 \
  --start 6 --chapters 3

# 然后 Ch9~Ch11
PYTHONPATH=. python scripts/run_batched_chapters.py \
  --seed scifi \
  --project-id proj-bcf431d0 \
  --output-dir evals/output/multi_chapter_scifi_20260530_233510 \
  --start 9 --chapters 3
```

## 环境准备

- `json_repair` 已安装（`pip install json-repair`）
- `SONGYAN_MAX_REVISION_ROUNDS=1` 环境变量已支持（`phase1_graph.py`）
- `run_batched_chapters.py` 脚本已修复编码/属性名 bugs
