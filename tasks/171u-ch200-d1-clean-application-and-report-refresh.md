# Task 171u: Ch200 D1 清洁应用与报告事实源复算

> **框架**: Task 171 Ch200 收口 + 171t 文本洁净量具补强
> **类型**: D1 hard clean 应用层（DB 版本化清洁 + report 事实源一致）
> **优先级**: P0（171v/172 前置）
> **依赖**: 171t；Ch200 run `run-fb39245c`；DB `.tmp/task171_ch1_ch200.db`
> **状态**: ✅ 完成（2026-07-12）

## 结论

171u 承接 171t 的补强量具，目标是把 Ch200 的真实 accepted 结果从“规模跑通”推进到“D1 hard clean pass”。本任务负责两件事：

1. 对 Ch200 accepted 正文中所有 T9 hard issue 创建版本化 deterministic clean，不覆盖旧版本。
2. 复算最终报告事实源，确保 stale continuity report 不再污染当前 D1 判定。

171u 不再承担量具补强，也不做文学护栏。这样出口标准可以保持清楚：**Ch200 DB 当前 accepted head 的 T9 hard issue 全为 0，最终报告只反映最新事实源**。

## 已知输入

来自 171t/20% 抽读复盘的当前待清洁类别：

| 类别 | 样例章节 | 处理方式 |
|---|---|---|
| Markdown 章标题 | Ch1、Ch2、Ch4、Ch47、Ch75 | 删除标题行，保留正文 |
| 保护指令 | Ch84、Ch160 | 删除 `【保护内容 — 请勿修改】` 等非叙事指令 |
| 斜杠拼接痕迹 | Ch41、Ch76、Ch124、Ch164 | 仅清理非单位/非路径/非坐标语境下的拼接 `/` |
| 纯省略号段 | Ch26、Ch32、Ch76、Ch101、Ch174 | 删除独立占位段 |
| prompt/patch 指令 | Ch76 | 删除非叙事写作指令 |
| duplicate=4 | Ch11、Ch84、Ch171 | deterministic dedup，保留首次出现 |
| stale critical orphan report | Ch159、Ch165 | 复算/聚合去 stale，只保留最新事实源 |

实际执行以 171t 输出的清洁清单为准，不以人工样例表为唯一来源。

## 修复边界

### 做

1. 读取当前 Ch200 accepted head，跑 171t final sweep。
2. 对 deterministic-cleanable issue 创建 cleaned version：
   - 每次清洁必须新增 `chapter_versions` 记录；
   - 禁止覆盖旧正文；
   - accepted/current head 写入必须使用事务；
   - 清洁版本需记录来源 version 与清洁原因。
3. 清洁后逐章重跑 RuleAuditor/T9：
   - `meta_tag_leak_count == 0`；
   - `duplicate_paragraph_count == 0`；
   - 新增 artifact hard issue 全为 0。
4. 修复/复算 report 聚合：
   - 同一 `checked_up_to_chapter` 只取最新 continuity report；
   - 或重新生成 Ch159/Ch165 post-171s continuity report；
   - 最终报告不得把 pre-fix stale false positive 当作当前 P1。
5. 重跑 `scripts/run_171_ch200.py --report`，更新 long-run report 与分析报告。

### 不做

- 不修改 171t 量具口径；
- 不降低 T9 阈值；
- 不降低 critical orphan/health 门禁；
- 不做 LLM 整章重写；
- 不为了清洁而改剧情、改设定、改 settlement；
- 不启动 Ch201+ 生成；
- 不处理角色自主性/概念密度/母题疲劳（下放 171v）。

## 工程方案

### 1. 清洁应用流程

```text
accepted head
  -> 171t final sweep
  -> no issue: keep current head
  -> deterministic-cleanable issues:
       create cleaned chapter_version
       run RuleAuditor / T9
       if clean: atomically set accepted/current head
       else: isolate / human review
  -> uncertain issues:
       isolate / human review
```

清洁 helper 必须保持幂等：对已 clean 文本再次运行，不应创建新 version。

### 2. Version 与事务纪律

- 新版本类型建议使用 `revision` 或专门的 `cleaned` 标记（按现有 schema 可用字段决定）；
- `source_version_id` 或 metadata 必须指向被清洁版本；
- accepted/current head/settlement 相关写入必须在同一事务中完成；
- 不改旧 `chapter_versions.content`。

### 3. Report 事实源复算

目标不是掩盖历史，而是区分“历史曾出现 false positive”和“当前最新事实源仍失败”。

聚合策略：

```sql
ROW_NUMBER() OVER (
  PARTITION BY project_id, checked_up_to_chapter
  ORDER BY created_at DESC
) = 1
```

或等价 Python 去重。最终报告可保留历史说明，但 D1 判定必须只依据最新事实源。

## 测试

建议新增/扩展：

1. `tests/test_171u_d1_clean_application.py`
   - clean issue 会创建新 version；
   - clean 文本二次运行不创建重复 version；
   - unresolved hard issue 不会被 accept；
   - accepted/current head 写入事务一致。
2. `tests/test_145_stage_a_metrics.py` 或相关 report 测试：
   - 同一 chapter 多条 continuity report 只取最新；
   - Ch159/Ch165 pre-fix stale P1 不污染当前 P1 peak。
3. 回归：
   - 171t final sweep 测试；
   - 171q duplicate 样本；
   - 171s setting refresh 样本。

## 验证命令

```powershell
python -m pytest tests/test_171t_text_cleanliness_final_sweep.py tests/test_171u_d1_clean_application.py tests/test_161_paragraph_dedup.py tests/test_task137_setting_recycling.py tests/test_145_stage_a_metrics.py -q
ruff check src/songyan/ tests/
```

报告复算：

```powershell
$env:DATABASE_URL = "sqlite:///.tmp/task171_ch1_ch200.db"
python scripts/run_171_ch200.py --report
```

## 出口标准

| 项 | 标准 |
|---|---|
| accepted | 200/200 |
| gaps | 0 |
| Halt | None |
| T9 duplicate | 0 |
| T9 meta/artifact | 0 |
| stale critical orphan | 不参与当前 D1 判定；报告只取最新事实源 |
| health median | >= 8.5 |
| version discipline | 清洁均创建新 `chapter_versions`，不覆盖旧内容 |
| report | `task-171-ch200-long-run-report.md` 与 DB 当前事实一致 |
| analysis | `task-171-ch200-analysis-and-next-step-report.md` 更新为 hard clean pass/remaining risk |

## 实施结果（2026-07-12）

已完成 171u 开发与 Ch200 DB 收口：

1. 新增 `src/songyan/services/text_cleanliness_cleaner.py`：
   - `clean_chapter_text`：deterministic 清理 171t hard issue；
   - `apply_chapter_text_cleaning`：创建新的 accepted clean version，并在同一事务内更新 `chapter_heads.current_version_id` / `accepted_version_id`；
   - `apply_project_text_cleaning`：按章节范围执行清洁，幂等跳过 clean 文本。
2. `scripts/run_171_ch200.py` 新增 `--clean-d1`：
   - 对当前 accepted head 执行 deterministic D1 清洁；
   - 自动重算 `task-171-ch200-long-run-report.md`。
3. `ContinuityReportRepository.list_by_chapter_range` 改为同章只返回最新 report。
4. `collect_orphan_metrics` 增加 current tracking 过滤：
   - 若旧 report 的 orphan 当前已被后续章节提及，或 tracking 已进入终态，则不再计入当前 D1/T6b 判定；
   - Ch159/Ch165 pre-fix stale critical orphan 不再污染最终报告。
5. 实际 Ch200 DB 已追加 20 个 clean accepted versions：
   - Ch1、2、4、11、26、32、41、47、75、76、84、97、101、124、148、159、160、164、171、174。
   - 旧版本均保留，clean version 的 `parent_version_id` 指向原 accepted version，`generation_metadata.task="171u"`。
6. 清洁前已备份 DB：`.tmp/task171_ch1_ch200_pre171u.db`。

最终事实源审计：

| 项 | 结果 |
|---|---:|
| accepted heads | 200/200 |
| clean versions | 20 |
| remaining hard issues | 0 |
| text_metrics rows | 200 |
| T9 meta/artifact | 0 |
| T9 duplicate | 0 |
| timeline conflicts | 14（report-only） |
| T6b critical orphan peak | 0 |

验证：

```powershell
python -m pytest tests/test_171u_d1_clean_application.py tests/test_145_stage_a_metrics.py tests/test_164_text_cleanliness.py tests/test_171t_text_cleanliness_final_sweep.py -q
# 33 passed

ruff check src/songyan/evals/db_metrics.py src/songyan/db/continuity_repo.py src/songyan/services/text_cleanliness_cleaner.py tests/test_171u_d1_clean_application.py
# All checks passed

python -m pytest tests/ -q
# 2595 passed, 2 skipped, 1 xfailed, 2 warnings

ruff check src/ tests/
# All checks passed
```

## 与后续关系

171u 完成后，Task 171 才能判为 **Ch200 D1 hard clean pass**。随后进入 171v 文学可读性护栏；171v 完成并通过 Ch201-Ch220 小窗口后，才启动 Task 172 Ch250 过渡验证。
