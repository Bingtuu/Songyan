# Task 205 FactTrack validity interval spike

> generated_at: `2026-08-01T10:48:54.021098+00:00`
> source_manifest: `archive/v10/artifacts/204-kg-diff-sample-manifest.json`
> source_kg_diff_report: `archive/v10/artifacts/204-kg-diff-spike-report.json`

## 边界

- offline report-only spike
- shadow interval model only
- read-only SQLite access via mode=ro
- does not alter SQLite schema or migrate historical DBs
- does not call LLMs or extract new facts from prose
- does not modify Writer or CreativeDirector prompts
- does not enter accept/reject gates
- does not change CED, five-gate, segment audit, or T9
- does not implement production FactTrack

## Summary

- report_only: `True`
- sample_count: `9`
- positive_samples: `6`
- negative_controls: `3`
- db_backed_samples: `9`
- document_truth_only_samples: `0`
- interval_explained: `6`
- false_positive_count: `0`
- needs_alias_policy_count: `2`
- needs_storyline_tree_count: `3`
- decision: `defer`
- decision_reason: Shadow intervals explain Task 204 signals, but alias policy and storyline semantics are still needed before production use.
- next_route: Task 206 Storyline Tree spike

## Impact Matrix

| issue_type | samples | TP | FP | unclear | explained | reduce FP | reduce FN | alias | storyline |
|------------|--------:|---:|---:|--------:|----------:|----------:|----------:|------:|----------:|
| `critical_orphan` | 1 | 1 | 0 | 0 | 1 | 0 | 1 | 1 | 0 |
| `foreshadowing_unresolved` | 3 | 3 | 0 | 0 | 3 | 0 | 3 | 0 | 3 |
| `negative_control` | 3 | 0 | 0 | 0 | 0 | 3 | 0 | 0 | 0 |
| `setting_tracking_missing_refresh` | 1 | 1 | 0 | 0 | 1 | 0 | 1 | 1 | 0 |
| `stale_continuity_report` | 1 | 1 | 0 | 0 | 1 | 0 | 1 | 0 | 0 |

## Migration Impact

| target | required now | production need | cost | fields | consumers |
|--------|--------------|-----------------|------|--------|-----------|
| `derived_fact_validity_view` | False | Can be generated report-only from existing tables first. | `none` | fact_id, valid_from_chapter, valid_to_chapter, valid_status, interval_rule, confidence | offline evaluators, Task 207 reports |
| `fact_validity_intervals` | False | Optional if intervals become reusable runtime facts. | `medium` | fact_id, fact_type, source_table, source_row_id, valid_from_chapter, valid_to_chapter, valid_status, source_version_id | SettlementExtractor, SummaryWriter, ContextManager, segment_audit |
| `foreshadowings` | False | Trace resolved chapter/version without document truth. | `medium` | resolved_chapter, resolved_version_id, resolved_reason | ContinuityAuditor, five_gate, ContextManager |
| `setting_tracking` | False | Alias-aware validity may need canonical target tracking. | `medium` | valid_from_chapter, valid_to_chapter, alias_group_id | segment_audit, ContextManager |

## Sample Results

| sample | genre | chapter | issue | explained | confidence | FP | alias | storyline |
|--------|-------|--------:|-------|-----------|------------|----|-------|-----------|
| `204-pos-xh-111-foreshadowing-overdue` | xuanhuan | 111 | `foreshadowing_unresolved` | True | `high` | False | False | True |
| `204-pos-xh-150-stale-continuity-report` | xuanhuan | 150 | `stale_continuity_report` | True | `high` | False | False | False |
| `204-pos-wx-117-setting-refresh` | wuxia | 117 | `setting_tracking_missing_refresh` | True | `high` | False | True | False |
| `204-pos-wx-155-critical-orphan` | wuxia | 155 | `critical_orphan` | True | `high` | False | True | False |
| `204-pos-urban-174-foreshadowing-overdue` | urban | 174 | `foreshadowing_unresolved` | True | `high` | False | False | True |
| `204-pos-urban-198-health-streak` | urban | 198 | `foreshadowing_unresolved` | True | `high` | False | False | True |
| `204-neg-xh-200-clean` | xuanhuan | 200 | `negative_control` | False | `none` | False | False | False |
| `204-neg-wx-200-clean` | wuxia | 200 | `negative_control` | False | `none` | False | False | False |
| `204-neg-urban-200-clean` | urban | 200 | `negative_control` | False | `none` | False | False | False |

## Interval Evidence

### 204-pos-xh-111-foreshadowing-overdue
- `foreshadowing` / `stale` / `high`: foreshadowing:fs-d160a55a51de4a2bb82440ebc03ec23a-0b5a5f5e Ch58-106 (expected_resolve; foreshadowings:fs-d160a55a51de4a2bb82440ebc03ec23a-0b5a5f5e)
- `foreshadowing` / `stale` / `high`: foreshadowing:fs-d160a55a51de4a2bb82440ebc03ec23a-2448bd9c Ch58-106 (expected_resolve; foreshadowings:fs-d160a55a51de4a2bb82440ebc03ec23a-2448bd9c)
- `foreshadowing` / `stale` / `high`: foreshadowing:fs-d160a55a51de4a2bb82440ebc03ec23a-44315af7 Ch19-67 (expected_resolve; foreshadowings:fs-d160a55a51de4a2bb82440ebc03ec23a-44315af7)
- `foreshadowing` / `stale` / `high`: foreshadowing:fs-d160a55a51de4a2bb82440ebc03ec23a-4dc271e3 Ch49-97 (expected_resolve; foreshadowings:fs-d160a55a51de4a2bb82440ebc03ec23a-4dc271e3)
- `foreshadowing` / `stale` / `high`: foreshadowing:fs-d160a55a51de4a2bb82440ebc03ec23a-5850f886 Ch55-103 (expected_resolve; foreshadowings:fs-d160a55a51de4a2bb82440ebc03ec23a-5850f886)
- `foreshadowing` / `stale` / `high`: foreshadowing:fs-d160a55a51de4a2bb82440ebc03ec23a-652f49a1 Ch48-96 (expected_resolve; foreshadowings:fs-d160a55a51de4a2bb82440ebc03ec23a-652f49a1)
- `foreshadowing` / `stale` / `high`: foreshadowing:fs-d160a55a51de4a2bb82440ebc03ec23a-96471472 Ch58-106 (expected_resolve; foreshadowings:fs-d160a55a51de4a2bb82440ebc03ec23a-96471472)
- `foreshadowing` / `stale` / `high`: foreshadowing:fs-d160a55a51de4a2bb82440ebc03ec23a-c472f027 Ch49-97 (expected_resolve; foreshadowings:fs-d160a55a51de4a2bb82440ebc03ec23a-c472f027)

### 204-pos-xh-150-stale-continuity-report
- `continuity_report` / `superseded` / `high`: continuity_report:cont_9cbf0a62 Ch150-150 (same_chapter_report_order; continuity_reports:cont_9cbf0a62)
- `continuity_report` / `superseded` / `high`: continuity_report:cont_fad57c16 Ch150-150 (same_chapter_report_order; continuity_reports:cont_fad57c16)
- `foreshadowing` / `resolved` / `medium`: foreshadowing:fs-94-1-new-xuanhuan Ch94-142 (expected_resolve; foreshadowings:fs-94-1-new-xuanhuan)
- `foreshadowing` / `resolved` / `medium`: foreshadowing:fs-d160a55a51de4a2bb82440ebc03ec23a-022b12c0 Ch9-57 (expected_resolve; foreshadowings:fs-d160a55a51de4a2bb82440ebc03ec23a-022b12c0)
- `foreshadowing` / `resolved` / `medium`: foreshadowing:fs-d160a55a51de4a2bb82440ebc03ec23a-023bbe84 Ch10-60 (expected_resolve; foreshadowings:fs-d160a55a51de4a2bb82440ebc03ec23a-023bbe84)
- `foreshadowing` / `resolved` / `medium`: foreshadowing:fs-d160a55a51de4a2bb82440ebc03ec23a-02c6381b Ch99-147 (expected_resolve; foreshadowings:fs-d160a55a51de4a2bb82440ebc03ec23a-02c6381b)
- `foreshadowing` / `resolved` / `medium`: foreshadowing:fs-d160a55a51de4a2bb82440ebc03ec23a-03c2a273 Ch80-128 (expected_resolve; foreshadowings:fs-d160a55a51de4a2bb82440ebc03ec23a-03c2a273)
- `foreshadowing` / `resolved` / `medium`: foreshadowing:fs-d160a55a51de4a2bb82440ebc03ec23a-043b3736 Ch86-134 (expected_resolve; foreshadowings:fs-d160a55a51de4a2bb82440ebc03ec23a-043b3736)

### 204-pos-wx-117-setting-refresh
- `setting` / `stale` / `high`: setting:track-273a8408be8e4caf8cbc1e91954da600-b622d5ab Ch100-113 (source_version_boundary; setting_tracking:track-273a8408be8e4caf8cbc1e91954da600-b622d5ab)
- `foreshadowing` / `resolved` / `medium`: foreshadowing:fs-273a8408be8e4caf8cbc1e91954da600-02b93ebf Ch10-58 (expected_resolve; foreshadowings:fs-273a8408be8e4caf8cbc1e91954da600-02b93ebf)
- `foreshadowing` / `resolved` / `medium`: foreshadowing:fs-273a8408be8e4caf8cbc1e91954da600-0421b314 Ch1-49 (expected_resolve; foreshadowings:fs-273a8408be8e4caf8cbc1e91954da600-0421b314)
- `foreshadowing` / `resolved` / `medium`: foreshadowing:fs-273a8408be8e4caf8cbc1e91954da600-09f751ff Ch60-108 (expected_resolve; foreshadowings:fs-273a8408be8e4caf8cbc1e91954da600-09f751ff)
- `foreshadowing` / `resolved` / `medium`: foreshadowing:fs-273a8408be8e4caf8cbc1e91954da600-0a38dadf Ch53-101 (expected_resolve; foreshadowings:fs-273a8408be8e4caf8cbc1e91954da600-0a38dadf)
- `foreshadowing` / `resolved` / `medium`: foreshadowing:fs-273a8408be8e4caf8cbc1e91954da600-0a8826da Ch62-110 (expected_resolve; foreshadowings:fs-273a8408be8e4caf8cbc1e91954da600-0a8826da)
- `foreshadowing` / `resolved` / `medium`: foreshadowing:fs-273a8408be8e4caf8cbc1e91954da600-0e6d1584 Ch21-69 (expected_resolve; foreshadowings:fs-273a8408be8e4caf8cbc1e91954da600-0e6d1584)
- `foreshadowing` / `resolved` / `medium`: foreshadowing:fs-273a8408be8e4caf8cbc1e91954da600-0f6c9698 Ch51-99 (expected_resolve; foreshadowings:fs-273a8408be8e4caf8cbc1e91954da600-0f6c9698)

### 204-pos-wx-155-critical-orphan
- `setting` / `stale` / `high`: setting:track-273a8408be8e4caf8cbc1e91954da600-5b381892 Ch152-152 (source_version_boundary; setting_tracking:track-273a8408be8e4caf8cbc1e91954da600-5b381892)
- `setting` / `resolved` / `medium`: setting:track-273a8408be8e4caf8cbc1e91954da600-c77d1a03 Ch127-128 (resolved_marker; setting_tracking:track-273a8408be8e4caf8cbc1e91954da600-c77d1a03)
- `foreshadowing` / `resolved` / `medium`: foreshadowing:fs-273a8408be8e4caf8cbc1e91954da600-01544047 Ch80-128 (expected_resolve; foreshadowings:fs-273a8408be8e4caf8cbc1e91954da600-01544047)
- `foreshadowing` / `resolved` / `medium`: foreshadowing:fs-273a8408be8e4caf8cbc1e91954da600-0155b5e2 Ch81-129 (expected_resolve; foreshadowings:fs-273a8408be8e4caf8cbc1e91954da600-0155b5e2)
- `foreshadowing` / `resolved` / `medium`: foreshadowing:fs-273a8408be8e4caf8cbc1e91954da600-02b93ebf Ch10-58 (expected_resolve; foreshadowings:fs-273a8408be8e4caf8cbc1e91954da600-02b93ebf)
- `foreshadowing` / `resolved` / `medium`: foreshadowing:fs-273a8408be8e4caf8cbc1e91954da600-0421b314 Ch1-49 (expected_resolve; foreshadowings:fs-273a8408be8e4caf8cbc1e91954da600-0421b314)
- `foreshadowing` / `resolved` / `medium`: foreshadowing:fs-273a8408be8e4caf8cbc1e91954da600-09f751ff Ch60-108 (expected_resolve; foreshadowings:fs-273a8408be8e4caf8cbc1e91954da600-09f751ff)
- `foreshadowing` / `resolved` / `medium`: foreshadowing:fs-273a8408be8e4caf8cbc1e91954da600-0a38dadf Ch53-101 (expected_resolve; foreshadowings:fs-273a8408be8e4caf8cbc1e91954da600-0a38dadf)

### 204-pos-urban-174-foreshadowing-overdue
- `foreshadowing` / `stale` / `high`: foreshadowing:fs-81e345042b124ee2a73094b82e4be555-04318c3f Ch97-100 (expected_resolve; foreshadowings:fs-81e345042b124ee2a73094b82e4be555-04318c3f)
- `foreshadowing` / `stale` / `high`: foreshadowing:fs-81e345042b124ee2a73094b82e4be555-06b6ab33 Ch10-14 (expected_resolve; foreshadowings:fs-81e345042b124ee2a73094b82e4be555-06b6ab33)
- `foreshadowing` / `stale` / `high`: foreshadowing:fs-81e345042b124ee2a73094b82e4be555-07f28d27 Ch151-155 (expected_resolve; foreshadowings:fs-81e345042b124ee2a73094b82e4be555-07f28d27)
- `foreshadowing` / `stale` / `high`: foreshadowing:fs-81e345042b124ee2a73094b82e4be555-0853c834 Ch38-39 (expected_resolve; foreshadowings:fs-81e345042b124ee2a73094b82e4be555-0853c834)
- `foreshadowing` / `stale` / `high`: foreshadowing:fs-81e345042b124ee2a73094b82e4be555-0d93f0fa Ch108-120 (expected_resolve; foreshadowings:fs-81e345042b124ee2a73094b82e4be555-0d93f0fa)
- `foreshadowing` / `stale` / `high`: foreshadowing:fs-81e345042b124ee2a73094b82e4be555-131f5ce9 Ch93-94 (expected_resolve; foreshadowings:fs-81e345042b124ee2a73094b82e4be555-131f5ce9)
- `foreshadowing` / `stale` / `high`: foreshadowing:fs-81e345042b124ee2a73094b82e4be555-19e28032 Ch20-21 (expected_resolve; foreshadowings:fs-81e345042b124ee2a73094b82e4be555-19e28032)
- `foreshadowing` / `stale` / `high`: foreshadowing:fs-81e345042b124ee2a73094b82e4be555-1b0bab01 Ch155-162 (expected_resolve; foreshadowings:fs-81e345042b124ee2a73094b82e4be555-1b0bab01)

### 204-pos-urban-198-health-streak
- `foreshadowing` / `stale` / `high`: foreshadowing:fs-81e345042b124ee2a73094b82e4be555-04318c3f Ch97-100 (expected_resolve; foreshadowings:fs-81e345042b124ee2a73094b82e4be555-04318c3f)
- `foreshadowing` / `stale` / `high`: foreshadowing:fs-81e345042b124ee2a73094b82e4be555-06b6ab33 Ch10-14 (expected_resolve; foreshadowings:fs-81e345042b124ee2a73094b82e4be555-06b6ab33)
- `foreshadowing` / `stale` / `high`: foreshadowing:fs-81e345042b124ee2a73094b82e4be555-07f28d27 Ch151-155 (expected_resolve; foreshadowings:fs-81e345042b124ee2a73094b82e4be555-07f28d27)
- `foreshadowing` / `stale` / `high`: foreshadowing:fs-81e345042b124ee2a73094b82e4be555-0853c834 Ch38-39 (expected_resolve; foreshadowings:fs-81e345042b124ee2a73094b82e4be555-0853c834)
- `foreshadowing` / `stale` / `high`: foreshadowing:fs-81e345042b124ee2a73094b82e4be555-0d93f0fa Ch108-120 (expected_resolve; foreshadowings:fs-81e345042b124ee2a73094b82e4be555-0d93f0fa)
- `foreshadowing` / `stale` / `high`: foreshadowing:fs-81e345042b124ee2a73094b82e4be555-131f5ce9 Ch93-94 (expected_resolve; foreshadowings:fs-81e345042b124ee2a73094b82e4be555-131f5ce9)
- `foreshadowing` / `stale` / `high`: foreshadowing:fs-81e345042b124ee2a73094b82e4be555-169dc311 Ch186-192 (expected_resolve; foreshadowings:fs-81e345042b124ee2a73094b82e4be555-169dc311)
- `foreshadowing` / `stale` / `high`: foreshadowing:fs-81e345042b124ee2a73094b82e4be555-19e28032 Ch20-21 (expected_resolve; foreshadowings:fs-81e345042b124ee2a73094b82e4be555-19e28032)

### 204-neg-xh-200-clean
- `setting` / `resolved` / `medium`: setting:track-d160a55a51de4a2bb82440ebc03ec23a-630031ce Ch53-60 (resolved_marker; setting_tracking:track-d160a55a51de4a2bb82440ebc03ec23a-630031ce)
- `setting` / `resolved` / `medium`: setting:track-d160a55a51de4a2bb82440ebc03ec23a-66d01dae Ch61-102 (resolved_marker; setting_tracking:track-d160a55a51de4a2bb82440ebc03ec23a-66d01dae)
- `setting` / `resolved` / `medium`: setting:track-d160a55a51de4a2bb82440ebc03ec23a-b41a1907 Ch1-110 (resolved_marker; setting_tracking:track-d160a55a51de4a2bb82440ebc03ec23a-b41a1907)
- `foreshadowing` / `resolved` / `low`: foreshadowing:fs-94-1-new-xuanhuan Ch94-142 (expected_resolve; foreshadowings:fs-94-1-new-xuanhuan)
- `foreshadowing` / `resolved` / `low`: foreshadowing:fs-d160a55a51de4a2bb82440ebc03ec23a-00120257 Ch127-175 (expected_resolve; foreshadowings:fs-d160a55a51de4a2bb82440ebc03ec23a-00120257)
- `foreshadowing` / `resolved` / `low`: foreshadowing:fs-d160a55a51de4a2bb82440ebc03ec23a-0161dc8a Ch109-157 (expected_resolve; foreshadowings:fs-d160a55a51de4a2bb82440ebc03ec23a-0161dc8a)
- `foreshadowing` / `resolved` / `low`: foreshadowing:fs-d160a55a51de4a2bb82440ebc03ec23a-01647bcb Ch141-189 (expected_resolve; foreshadowings:fs-d160a55a51de4a2bb82440ebc03ec23a-01647bcb)
- `foreshadowing` / `resolved` / `low`: foreshadowing:fs-d160a55a51de4a2bb82440ebc03ec23a-022b12c0 Ch9-57 (expected_resolve; foreshadowings:fs-d160a55a51de4a2bb82440ebc03ec23a-022b12c0)

### 204-neg-wx-200-clean
- `setting` / `resolved` / `medium`: setting:track-273a8408be8e4caf8cbc1e91954da600-c77d1a03 Ch127-128 (resolved_marker; setting_tracking:track-273a8408be8e4caf8cbc1e91954da600-c77d1a03)
- `foreshadowing` / `resolved` / `low`: foreshadowing:fs-273a8408be8e4caf8cbc1e91954da600-0033bb28 Ch130-178 (expected_resolve; foreshadowings:fs-273a8408be8e4caf8cbc1e91954da600-0033bb28)
- `foreshadowing` / `active` / `low`: foreshadowing:fs-273a8408be8e4caf8cbc1e91954da600-00396909 Ch192-240 (expected_resolve; foreshadowings:fs-273a8408be8e4caf8cbc1e91954da600-00396909)
- `foreshadowing` / `resolved` / `low`: foreshadowing:fs-273a8408be8e4caf8cbc1e91954da600-01544047 Ch80-128 (expected_resolve; foreshadowings:fs-273a8408be8e4caf8cbc1e91954da600-01544047)
- `foreshadowing` / `resolved` / `low`: foreshadowing:fs-273a8408be8e4caf8cbc1e91954da600-0155b5e2 Ch81-129 (expected_resolve; foreshadowings:fs-273a8408be8e4caf8cbc1e91954da600-0155b5e2)
- `foreshadowing` / `resolved` / `low`: foreshadowing:fs-273a8408be8e4caf8cbc1e91954da600-02b93ebf Ch10-58 (expected_resolve; foreshadowings:fs-273a8408be8e4caf8cbc1e91954da600-02b93ebf)
- `foreshadowing` / `stale` / `low`: foreshadowing:fs-273a8408be8e4caf8cbc1e91954da600-03122986 Ch68-116 (expected_resolve; foreshadowings:fs-273a8408be8e4caf8cbc1e91954da600-03122986)
- `foreshadowing` / `resolved` / `low`: foreshadowing:fs-273a8408be8e4caf8cbc1e91954da600-0421b314 Ch1-49 (expected_resolve; foreshadowings:fs-273a8408be8e4caf8cbc1e91954da600-0421b314)

### 204-neg-urban-200-clean
- `setting` / `resolved` / `medium`: setting:track-81e345042b124ee2a73094b82e4be555-53f1e665 Ch35-200 (resolved_marker; setting_tracking:track-81e345042b124ee2a73094b82e4be555-53f1e665)
- `foreshadowing` / `stale` / `low`: foreshadowing:fs-81e345042b124ee2a73094b82e4be555-04318c3f Ch97-100 (expected_resolve; foreshadowings:fs-81e345042b124ee2a73094b82e4be555-04318c3f)
- `foreshadowing` / `resolved` / `low`: foreshadowing:fs-81e345042b124ee2a73094b82e4be555-04d43c57 Ch165-170 (expected_resolve; foreshadowings:fs-81e345042b124ee2a73094b82e4be555-04d43c57)
- `foreshadowing` / `active` / `low`: foreshadowing:fs-81e345042b124ee2a73094b82e4be555-050992a9 Ch13-? (expected_resolve; foreshadowings:fs-81e345042b124ee2a73094b82e4be555-050992a9)
- `foreshadowing` / `resolved` / `low`: foreshadowing:fs-81e345042b124ee2a73094b82e4be555-0637afbc Ch63-68 (expected_resolve; foreshadowings:fs-81e345042b124ee2a73094b82e4be555-0637afbc)
- `foreshadowing` / `resolved` / `low`: foreshadowing:fs-81e345042b124ee2a73094b82e4be555-065c8e17 Ch171-180 (expected_resolve; foreshadowings:fs-81e345042b124ee2a73094b82e4be555-065c8e17)
- `foreshadowing` / `stale` / `low`: foreshadowing:fs-81e345042b124ee2a73094b82e4be555-06b6ab33 Ch10-14 (expected_resolve; foreshadowings:fs-81e345042b124ee2a73094b82e4be555-06b6ab33)
- `foreshadowing` / `resolved` / `low`: foreshadowing:fs-81e345042b124ee2a73094b82e4be555-0705124f Ch120-125 (expected_resolve; foreshadowings:fs-81e345042b124ee2a73094b82e4be555-0705124f)

## 后续路由

- Task 206: Storyline Tree spike，用于验证 open thread 与已兑现伏笔的主线/支线归属。
- Task 207: 若 V10 收口时登记生产化，优先以 derived view / report-only 方式进入，不直接迁移历史库。
- Task 205 输出保持 report-only，不进入 hard gate。
