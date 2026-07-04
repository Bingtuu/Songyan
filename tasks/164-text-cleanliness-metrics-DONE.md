# Task 164 DONE: 文本洁净度度量入库 + T9 harness

> **Phase**: V7 阶段 W（篇章级质量修复）
> **完成时间**: 2026-07-04
> **结论**: 完成。已新增文本洁净度逐章入库、`songyan metrics` 展示段，并将 T9 作为三态 harness 接入验收框架。

---

## 目标回放

Task 164 要把 Task 160-162 的三类篇章级缺陷信号汇聚为可查、可复核、可判定的指标：

- 元标记泄漏；
- 重复长段落；
- 跨章时间线矛盾；
- T9 三态判据。

## 已完成改动

| 模块 | 改动 |
|------|------|
| `src/songyan/db/schema.sql` / `src/songyan/db/migrations.py` | 新增 `text_cleanliness_metrics` 表，主键 `(project_id, chapter_number)`，记录 accepted version 的三类洁净度计数与 details JSON。 |
| `src/songyan/db/text_cleanliness_repo.py` | 新增 `TextCleanlinessMetricRepository` 与 `TextCleanlinessMetricRow`，支持 upsert、按项目/章节范围回读。 |
| `src/songyan/evals/text_cleanliness.py` | 新增 accepted 正文洁净度采集：调用 160 的元标记检测、161 的重复长段落检测、162 的时间线冲突诊断；支持 derive-and-upsert、只读采集、report 段渲染。 |
| `src/songyan/evals/db_metrics.py` | `render_stage_a_metrics` 新增“文本洁净度（T9 harness 数据源）”段；每次 metrics 渲染会刷新并入库洁净度指标。 |
| `src/songyan/evals/v6_acceptance.py` | 新增 `check_t9`，并接入 `evaluate_v6_acceptance` 三态结果列表。 |
| `tests/test_164_text_cleanliness.py` | 新增专项测试，覆盖入库/回读、report 渲染、T9 pass/fail/undecided、时间线红线开关、验收框架接入。 |

## T9 口径

默认口径：

- `meta_tag_leak_count == 0` 为硬红线；
- `duplicate_paragraph_count == 0` 为硬红线；
- `timeline_conflict_count` 默认 **report-only**，不计入硬红线。

`check_t9(..., include_timeline_in_redline=True)` 已提供参数化开关，供 Task 165 基于 Ch150 修复后实测决定是否冻结为硬红线。

## 入库设计

表：`text_cleanliness_metrics`

| 字段 | 含义 |
|------|------|
| `project_id` / `chapter_number` | 项目与章节 |
| `version_id` | 当前 accepted version |
| `meta_tag_leak_count` | `detect_meta_tag_leaks` + `detect_markdown_scene_titles` |
| `duplicate_paragraph_count` | `detect_duplicate_paragraphs` |
| `timeline_conflict_count` | 当前章作为 conflict current_chapter 的冲突数 |
| `details_json` | 三类检测的原始定位详情 |

## 验收点

- `collect_text_cleanliness_metrics(..., persist=True)` 可从 accepted 正文复算并 upsert。
- `TextCleanlinessMetricRepository.list_by_project` 可回读完整曲线。
- `render_stage_a_metrics` 输出文本洁净度段。
- `check_t9`：
  - 全零 → pass；
  - 元标记/重复长段落 >0 → fail；
  - accepted 样本不足 → undecided；
  - 时间线冲突默认 report-only，开启参数后可 fail。

## 验证

```powershell
python -m pytest tests/test_164_text_cleanliness.py tests/test_157_v6_acceptance.py tests/test_145_stage_a_metrics.py -q
```

结果：`48 passed`

```powershell
python -m pytest tests/ -q
```

结果：`2317 passed, 2 skipped, 1 xfailed, 2 warnings`

```powershell
ruff check src/ tests/
```

结果：`All checks passed!`

## 边界

- 本 Task 不冻结 T9/T10；T9 时间线是否纳入硬红线留 Task 165。
- 本 Task 不新增门禁，不改变 accept 行为。
- 本 Task 只消费 160-162 检测信号，不修改检测器逻辑。
- 未执行 Ch150 真实复跑；真实样本清零验证留 Task 165。

## 下一步

进入 Task 165：阶段 W 出口 — Ch1-Ch150 复跑验证 + T9/T10 标定冻结。
