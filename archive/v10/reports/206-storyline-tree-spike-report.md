# Task 206 Storyline Tree spike

> generated_at: `2026-08-01T11:41:04.635280+00:00`
> source_manifest: `archive/v10/artifacts/204-kg-diff-sample-manifest.json`
> source_kg_diff_report: `archive/v10/artifacts/204-kg-diff-spike-report.json`
> source_facttrack_report: `archive/v10/artifacts/205-facttrack-validity-interval-report.json`

## 边界

- offline report-only spike
- shadow Storyline Tree only
- read-only SQLite access via mode=ro
- does not alter SQLite schema or migrate historical DBs
- does not call LLMs or extract new plot facts from prose
- does not modify Writer or CreativeDirector prompts
- does not enter accept/reject gates
- does not change CED, five-gate, segment audit, or T9
- does not implement production Storyline Tree

## Summary

- report_only: `True`
- sample_count: `9`
- positive_samples: `6`
- negative_controls: `3`
- db_backed_samples: `9`
- document_truth_only_samples: `0`
- needs_storyline_tree_samples: `3`
- tree_explained: `5`
- false_positive_count: `0`
- still_needs_alias_policy_count: `2`
- still_needs_validity_interval_count: `1`
- decision: `defer`
- decision_reason: Storyline Tree explains open-thread samples, but production use still needs alias policy and validity integration.
- next_route: Task 207 V10 closure and archive

## Impact Matrix

| issue_type | samples | TP | FP | unclear | tree | reduce FP | reduce FN | alias | validity |
|------------|--------:|---:|---:|--------:|-----:|----------:|----------:|------:|---------:|
| `critical_orphan` | 1 | 1 | 0 | 0 | 1 | 0 | 1 | 1 | 0 |
| `foreshadowing_unresolved` | 3 | 3 | 0 | 0 | 3 | 0 | 3 | 0 | 0 |
| `negative_control` | 3 | 0 | 0 | 0 | 0 | 3 | 0 | 0 | 0 |
| `setting_tracking_missing_refresh` | 1 | 1 | 0 | 0 | 1 | 0 | 1 | 1 | 0 |
| `stale_continuity_report` | 1 | 0 | 0 | 1 | 0 | 0 | 0 | 0 | 1 |

## Migration Impact

| target | required now | production need | cost | fields | consumers |
|--------|--------------|-----------------|------|--------|-----------|
| `derived_storyline_tree_view` | False | Can be generated report-only from existing facts first. | `none` | storyline_id, parent_id, node_type, chapter_start, chapter_end, status, linked_facts, confidence | Task 207 reports, offline evaluators |
| `storyline_tree_nodes` | False | Optional if tree becomes reusable planning memory. | `medium` | storyline_id, project_id, parent_id, node_type, status, chapter_start, chapter_end | GoalPlanner, CreativeDirector, ContextManager |
| `storyline_fact_links` | False | Needed only if production tree links facts bidirectionally. | `medium` | storyline_id, source_table, source_row_id, confidence | SettlementExtractor, SummaryWriter, segment_audit |

## Sample Results

| sample | genre | chapter | issue | tree | confidence | FP | alias | validity |
|--------|-------|--------:|-------|------|------------|----|-------|----------|
| `204-pos-xh-111-foreshadowing-overdue` | xuanhuan | 111 | `foreshadowing_unresolved` | True | `high` | False | False | False |
| `204-pos-xh-150-stale-continuity-report` | xuanhuan | 150 | `stale_continuity_report` | False | `none` | False | False | True |
| `204-pos-wx-117-setting-refresh` | wuxia | 117 | `setting_tracking_missing_refresh` | True | `medium` | False | True | False |
| `204-pos-wx-155-critical-orphan` | wuxia | 155 | `critical_orphan` | True | `medium` | False | True | False |
| `204-pos-urban-174-foreshadowing-overdue` | urban | 174 | `foreshadowing_unresolved` | True | `high` | False | False | False |
| `204-pos-urban-198-health-streak` | urban | 198 | `foreshadowing_unresolved` | True | `high` | False | False | False |
| `204-neg-xh-200-clean` | xuanhuan | 200 | `negative_control` | False | `none` | False | False | False |
| `204-neg-wx-200-clean` | wuxia | 200 | `negative_control` | False | `none` | False | False | False |
| `204-neg-urban-200-clean` | urban | 200 | `negative_control` | False | `none` | False | False | False |

## Storyline Nodes

### 204-pos-xh-111-foreshadowing-overdue
- `thread` / `stale` / `high`: thread:foreshadowing:fs-d160a55a51de4a2bb82440ebc03ec23a-0b5a5f5e Ch58-106 (foreshadowing_expected_resolve; foreshadowings:fs-d160a55a51de4a2bb82440ebc03ec23a-0b5a5f5e)
- `thread` / `stale` / `high`: thread:foreshadowing:fs-d160a55a51de4a2bb82440ebc03ec23a-2448bd9c Ch58-106 (foreshadowing_expected_resolve; foreshadowings:fs-d160a55a51de4a2bb82440ebc03ec23a-2448bd9c)
- `thread` / `stale` / `high`: thread:foreshadowing:fs-d160a55a51de4a2bb82440ebc03ec23a-44315af7 Ch19-67 (foreshadowing_expected_resolve; foreshadowings:fs-d160a55a51de4a2bb82440ebc03ec23a-44315af7)
- `thread` / `stale` / `high`: thread:foreshadowing:fs-d160a55a51de4a2bb82440ebc03ec23a-4dc271e3 Ch49-97 (foreshadowing_expected_resolve; foreshadowings:fs-d160a55a51de4a2bb82440ebc03ec23a-4dc271e3)
- `thread` / `stale` / `high`: thread:foreshadowing:fs-d160a55a51de4a2bb82440ebc03ec23a-5850f886 Ch55-103 (foreshadowing_expected_resolve; foreshadowings:fs-d160a55a51de4a2bb82440ebc03ec23a-5850f886)
- `thread` / `stale` / `high`: thread:foreshadowing:fs-d160a55a51de4a2bb82440ebc03ec23a-652f49a1 Ch48-96 (foreshadowing_expected_resolve; foreshadowings:fs-d160a55a51de4a2bb82440ebc03ec23a-652f49a1)
- `thread` / `stale` / `high`: thread:foreshadowing:fs-d160a55a51de4a2bb82440ebc03ec23a-96471472 Ch58-106 (foreshadowing_expected_resolve; foreshadowings:fs-d160a55a51de4a2bb82440ebc03ec23a-96471472)
- `thread` / `stale` / `high`: thread:foreshadowing:fs-d160a55a51de4a2bb82440ebc03ec23a-c472f027 Ch49-97 (foreshadowing_expected_resolve; foreshadowings:fs-d160a55a51de4a2bb82440ebc03ec23a-c472f027)
- `thread` / `stale` / `high`: thread:foreshadowing:fs-d160a55a51de4a2bb82440ebc03ec23a-d9b45692 Ch61-109 (foreshadowing_expected_resolve; foreshadowings:fs-d160a55a51de4a2bb82440ebc03ec23a-d9b45692)
- `thread` / `stale` / `high`: thread:foreshadowing:fs-d160a55a51de4a2bb82440ebc03ec23a-f5cc1868 Ch45-93 (foreshadowing_expected_resolve; foreshadowings:fs-d160a55a51de4a2bb82440ebc03ec23a-f5cc1868)

### 204-pos-xh-150-stale-continuity-report
- `mainline` / `active` / `medium`: mainline:xuanhuan:d160a55a51de4a2bb82440ebc03ec23a Ch1-150 (document_truth; manifest:204-pos-xh-150-stale-continuity-report)
- `arc` / `active` / `medium`: arc:arc-a15e5ea5 Ch126-150 (arc_summary_range; arc_summaries:arc-a15e5ea5)
- `thread` / `open` / `medium`: thread:human_mark:cont-fs-fs-d160a55a51de4a2bb82440ebc03ec23a-09df5487 Ch150-? (human_mark_thread; human_marks:cont-fs-fs-d160a55a51de4a2bb82440ebc03ec23a-09df5487)
- `thread` / `open` / `medium`: thread:human_mark:cont-fs-fs-d160a55a51de4a2bb82440ebc03ec23a-1d544035 Ch150-? (human_mark_thread; human_marks:cont-fs-fs-d160a55a51de4a2bb82440ebc03ec23a-1d544035)
- `thread` / `open` / `medium`: thread:human_mark:cont-fs-fs-d160a55a51de4a2bb82440ebc03ec23a-86aa6a0d Ch150-? (human_mark_thread; human_marks:cont-fs-fs-d160a55a51de4a2bb82440ebc03ec23a-86aa6a0d)
- `thread` / `open` / `medium`: thread:human_mark:cont-fs-fs-d160a55a51de4a2bb82440ebc03ec23a-8d914574 Ch150-? (human_mark_thread; human_marks:cont-fs-fs-d160a55a51de4a2bb82440ebc03ec23a-8d914574)
- `thread` / `open` / `medium`: thread:human_mark:cont-fs-fs-d160a55a51de4a2bb82440ebc03ec23a-ca43c075 Ch72-? (human_mark_thread; human_marks:cont-fs-fs-d160a55a51de4a2bb82440ebc03ec23a-ca43c075)
- `thread` / `open` / `medium`: thread:human_mark:cont-fs-fs-d160a55a51de4a2bb82440ebc03ec23a-da36a39d Ch51-? (human_mark_thread; human_marks:cont-fs-fs-d160a55a51de4a2bb82440ebc03ec23a-da36a39d)
- `thread` / `open` / `medium`: thread:human_mark:cont-fs-fs-d160a55a51de4a2bb82440ebc03ec23a-efd3da00 Ch150-? (human_mark_thread; human_marks:cont-fs-fs-d160a55a51de4a2bb82440ebc03ec23a-efd3da00)
- `thread` / `open` / `medium`: thread:human_mark:cont-fs-fs-d160a55a51de4a2bb82440ebc03ec23a-f6263bc5 Ch150-? (human_mark_thread; human_marks:cont-fs-fs-d160a55a51de4a2bb82440ebc03ec23a-f6263bc5)

### 204-pos-wx-117-setting-refresh
- `subplot` / `active` / `medium`: subplot:setting:track-273a8408be8e4caf8cbc1e91954da600-23e91cb7 Ch69-117 (setting_tracking_thread; setting_tracking:track-273a8408be8e4caf8cbc1e91954da600-23e91cb7)
- `subplot` / `active` / `medium`: subplot:setting:track-273a8408be8e4caf8cbc1e91954da600-3717503b Ch101-117 (setting_tracking_thread; setting_tracking:track-273a8408be8e4caf8cbc1e91954da600-3717503b)
- `subplot` / `active` / `medium`: subplot:setting:track-273a8408be8e4caf8cbc1e91954da600-b622d5ab Ch100-113 (setting_tracking_thread; setting_tracking:track-273a8408be8e4caf8cbc1e91954da600-b622d5ab)
- `subplot` / `active` / `medium`: subplot:setting:track-273a8408be8e4caf8cbc1e91954da600-e303b8f4 Ch62-117 (setting_tracking_thread; setting_tracking:track-273a8408be8e4caf8cbc1e91954da600-e303b8f4)
- `mainline` / `active` / `medium`: mainline:wuxia:273a8408be8e4caf8cbc1e91954da600 Ch1-117 (document_truth; manifest:204-pos-wx-117-setting-refresh)
- `thread` / `open` / `medium`: thread:human_mark:cont-fs-fs-273a8408be8e4caf8cbc1e91954da600-32be7e3a Ch117-? (human_mark_thread; human_marks:cont-fs-fs-273a8408be8e4caf8cbc1e91954da600-32be7e3a)
- `thread` / `open` / `medium`: thread:human_mark:cont-fs-fs-273a8408be8e4caf8cbc1e91954da600-49d766ff Ch117-? (human_mark_thread; human_marks:cont-fs-fs-273a8408be8e4caf8cbc1e91954da600-49d766ff)
- `thread` / `open` / `medium`: thread:human_mark:cont-fs-fs-273a8408be8e4caf8cbc1e91954da600-83d16cbb Ch117-? (human_mark_thread; human_marks:cont-fs-fs-273a8408be8e4caf8cbc1e91954da600-83d16cbb)
- `thread` / `open` / `medium`: thread:human_mark:cont-fs-fs-273a8408be8e4caf8cbc1e91954da600-86ce6726 Ch117-? (human_mark_thread; human_marks:cont-fs-fs-273a8408be8e4caf8cbc1e91954da600-86ce6726)
- `thread` / `open` / `medium`: thread:human_mark:cont-fs-fs-273a8408be8e4caf8cbc1e91954da600-b197365d Ch117-? (human_mark_thread; human_marks:cont-fs-fs-273a8408be8e4caf8cbc1e91954da600-b197365d)

### 204-pos-wx-155-critical-orphan
- `subplot` / `active` / `medium`: subplot:setting:track-273a8408be8e4caf8cbc1e91954da600-23e91cb7 Ch69-154 (setting_tracking_thread; setting_tracking:track-273a8408be8e4caf8cbc1e91954da600-23e91cb7)
- `subplot` / `active` / `medium`: subplot:setting:track-273a8408be8e4caf8cbc1e91954da600-2a138162 Ch143-155 (setting_tracking_thread; setting_tracking:track-273a8408be8e4caf8cbc1e91954da600-2a138162)
- `subplot` / `active` / `medium`: subplot:setting:track-273a8408be8e4caf8cbc1e91954da600-3717503b Ch101-153 (setting_tracking_thread; setting_tracking:track-273a8408be8e4caf8cbc1e91954da600-3717503b)
- `subplot` / `active` / `medium`: subplot:setting:track-273a8408be8e4caf8cbc1e91954da600-5b381892 Ch152-152 (setting_tracking_thread; setting_tracking:track-273a8408be8e4caf8cbc1e91954da600-5b381892)
- `subplot` / `active` / `medium`: subplot:setting:track-273a8408be8e4caf8cbc1e91954da600-97f7c5c6 Ch147-153 (setting_tracking_thread; setting_tracking:track-273a8408be8e4caf8cbc1e91954da600-97f7c5c6)
- `subplot` / `active` / `medium`: subplot:setting:track-273a8408be8e4caf8cbc1e91954da600-b622d5ab Ch100-153 (setting_tracking_thread; setting_tracking:track-273a8408be8e4caf8cbc1e91954da600-b622d5ab)
- `subplot` / `active` / `medium`: subplot:setting:track-273a8408be8e4caf8cbc1e91954da600-c77d1a03 Ch127-128 (setting_tracking_thread; setting_tracking:track-273a8408be8e4caf8cbc1e91954da600-c77d1a03)
- `subplot` / `active` / `medium`: subplot:setting:track-273a8408be8e4caf8cbc1e91954da600-e303b8f4 Ch62-154 (setting_tracking_thread; setting_tracking:track-273a8408be8e4caf8cbc1e91954da600-e303b8f4)
- `mainline` / `active` / `medium`: mainline:wuxia:273a8408be8e4caf8cbc1e91954da600 Ch1-155 (document_truth; manifest:204-pos-wx-155-critical-orphan)
- `thread` / `open` / `medium`: thread:human_mark:cont-fs-fs-273a8408be8e4caf8cbc1e91954da600-0bec2ede Ch144-? (human_mark_thread; human_marks:cont-fs-fs-273a8408be8e4caf8cbc1e91954da600-0bec2ede)

### 204-pos-urban-174-foreshadowing-overdue
- `thread` / `stale` / `high`: thread:foreshadowing:fs-81e345042b124ee2a73094b82e4be555-04318c3f Ch97-100 (foreshadowing_expected_resolve; foreshadowings:fs-81e345042b124ee2a73094b82e4be555-04318c3f)
- `thread` / `stale` / `high`: thread:foreshadowing:fs-81e345042b124ee2a73094b82e4be555-06b6ab33 Ch10-14 (foreshadowing_expected_resolve; foreshadowings:fs-81e345042b124ee2a73094b82e4be555-06b6ab33)
- `thread` / `stale` / `high`: thread:foreshadowing:fs-81e345042b124ee2a73094b82e4be555-07f28d27 Ch151-155 (foreshadowing_expected_resolve; foreshadowings:fs-81e345042b124ee2a73094b82e4be555-07f28d27)
- `thread` / `stale` / `high`: thread:foreshadowing:fs-81e345042b124ee2a73094b82e4be555-0853c834 Ch38-39 (foreshadowing_expected_resolve; foreshadowings:fs-81e345042b124ee2a73094b82e4be555-0853c834)
- `thread` / `stale` / `high`: thread:foreshadowing:fs-81e345042b124ee2a73094b82e4be555-0d93f0fa Ch108-120 (foreshadowing_expected_resolve; foreshadowings:fs-81e345042b124ee2a73094b82e4be555-0d93f0fa)
- `thread` / `stale` / `high`: thread:foreshadowing:fs-81e345042b124ee2a73094b82e4be555-131f5ce9 Ch93-94 (foreshadowing_expected_resolve; foreshadowings:fs-81e345042b124ee2a73094b82e4be555-131f5ce9)
- `thread` / `stale` / `high`: thread:foreshadowing:fs-81e345042b124ee2a73094b82e4be555-19e28032 Ch20-21 (foreshadowing_expected_resolve; foreshadowings:fs-81e345042b124ee2a73094b82e4be555-19e28032)
- `thread` / `stale` / `high`: thread:foreshadowing:fs-81e345042b124ee2a73094b82e4be555-1b0bab01 Ch155-162 (foreshadowing_expected_resolve; foreshadowings:fs-81e345042b124ee2a73094b82e4be555-1b0bab01)
- `thread` / `stale` / `high`: thread:foreshadowing:fs-81e345042b124ee2a73094b82e4be555-1c5091da Ch106-120 (foreshadowing_expected_resolve; foreshadowings:fs-81e345042b124ee2a73094b82e4be555-1c5091da)
- `thread` / `stale` / `high`: thread:foreshadowing:fs-81e345042b124ee2a73094b82e4be555-1e433daa Ch92-97 (foreshadowing_expected_resolve; foreshadowings:fs-81e345042b124ee2a73094b82e4be555-1e433daa)

### 204-pos-urban-198-health-streak
- `thread` / `stale` / `high`: thread:foreshadowing:fs-81e345042b124ee2a73094b82e4be555-04318c3f Ch97-100 (foreshadowing_expected_resolve; foreshadowings:fs-81e345042b124ee2a73094b82e4be555-04318c3f)
- `thread` / `stale` / `high`: thread:foreshadowing:fs-81e345042b124ee2a73094b82e4be555-06b6ab33 Ch10-14 (foreshadowing_expected_resolve; foreshadowings:fs-81e345042b124ee2a73094b82e4be555-06b6ab33)
- `thread` / `stale` / `high`: thread:foreshadowing:fs-81e345042b124ee2a73094b82e4be555-07f28d27 Ch151-155 (foreshadowing_expected_resolve; foreshadowings:fs-81e345042b124ee2a73094b82e4be555-07f28d27)
- `thread` / `stale` / `high`: thread:foreshadowing:fs-81e345042b124ee2a73094b82e4be555-0853c834 Ch38-39 (foreshadowing_expected_resolve; foreshadowings:fs-81e345042b124ee2a73094b82e4be555-0853c834)
- `thread` / `stale` / `high`: thread:foreshadowing:fs-81e345042b124ee2a73094b82e4be555-0d93f0fa Ch108-120 (foreshadowing_expected_resolve; foreshadowings:fs-81e345042b124ee2a73094b82e4be555-0d93f0fa)
- `thread` / `stale` / `high`: thread:foreshadowing:fs-81e345042b124ee2a73094b82e4be555-131f5ce9 Ch93-94 (foreshadowing_expected_resolve; foreshadowings:fs-81e345042b124ee2a73094b82e4be555-131f5ce9)
- `thread` / `stale` / `high`: thread:foreshadowing:fs-81e345042b124ee2a73094b82e4be555-169dc311 Ch186-192 (foreshadowing_expected_resolve; foreshadowings:fs-81e345042b124ee2a73094b82e4be555-169dc311)
- `thread` / `stale` / `high`: thread:foreshadowing:fs-81e345042b124ee2a73094b82e4be555-19e28032 Ch20-21 (foreshadowing_expected_resolve; foreshadowings:fs-81e345042b124ee2a73094b82e4be555-19e28032)
- `thread` / `stale` / `high`: thread:foreshadowing:fs-81e345042b124ee2a73094b82e4be555-1b0bab01 Ch155-162 (foreshadowing_expected_resolve; foreshadowings:fs-81e345042b124ee2a73094b82e4be555-1b0bab01)
- `thread` / `stale` / `high`: thread:foreshadowing:fs-81e345042b124ee2a73094b82e4be555-1c5091da Ch106-120 (foreshadowing_expected_resolve; foreshadowings:fs-81e345042b124ee2a73094b82e4be555-1c5091da)

### 204-neg-xh-200-clean
- `mainline` / `active` / `medium`: mainline:xuanhuan:d160a55a51de4a2bb82440ebc03ec23a Ch1-200 (document_truth; manifest:204-neg-xh-200-clean)
- `arc` / `active` / `medium`: arc:arc-6ca67094 Ch176-200 (arc_summary_range; arc_summaries:arc-6ca67094)
- `thread` / `open` / `medium`: thread:human_mark:cont-fs-fs-d160a55a51de4a2bb82440ebc03ec23a-05d9ea23 Ch200-? (human_mark_thread; human_marks:cont-fs-fs-d160a55a51de4a2bb82440ebc03ec23a-05d9ea23)
- `thread` / `open` / `medium`: thread:human_mark:cont-fs-fs-d160a55a51de4a2bb82440ebc03ec23a-35b70634 Ch200-? (human_mark_thread; human_marks:cont-fs-fs-d160a55a51de4a2bb82440ebc03ec23a-35b70634)
- `thread` / `open` / `medium`: thread:human_mark:cont-fs-fs-d160a55a51de4a2bb82440ebc03ec23a-5610b52f Ch200-? (human_mark_thread; human_marks:cont-fs-fs-d160a55a51de4a2bb82440ebc03ec23a-5610b52f)
- `thread` / `open` / `medium`: thread:human_mark:cont-fs-fs-d160a55a51de4a2bb82440ebc03ec23a-7c53f049 Ch200-? (human_mark_thread; human_marks:cont-fs-fs-d160a55a51de4a2bb82440ebc03ec23a-7c53f049)
- `thread` / `open` / `medium`: thread:human_mark:cont-fs-fs-d160a55a51de4a2bb82440ebc03ec23a-8adc0bfe Ch174-? (human_mark_thread; human_marks:cont-fs-fs-d160a55a51de4a2bb82440ebc03ec23a-8adc0bfe)
- `thread` / `open` / `medium`: thread:human_mark:cont-fs-fs-d160a55a51de4a2bb82440ebc03ec23a-8cdde9d9 Ch200-? (human_mark_thread; human_marks:cont-fs-fs-d160a55a51de4a2bb82440ebc03ec23a-8cdde9d9)
- `thread` / `open` / `medium`: thread:human_mark:cont-fs-fs-d160a55a51de4a2bb82440ebc03ec23a-905e6485 Ch200-? (human_mark_thread; human_marks:cont-fs-fs-d160a55a51de4a2bb82440ebc03ec23a-905e6485)
- `thread` / `open` / `medium`: thread:human_mark:cont-fs-fs-d160a55a51de4a2bb82440ebc03ec23a-b16c8d5b Ch200-? (human_mark_thread; human_marks:cont-fs-fs-d160a55a51de4a2bb82440ebc03ec23a-b16c8d5b)

### 204-neg-wx-200-clean
- `mainline` / `active` / `medium`: mainline:wuxia:273a8408be8e4caf8cbc1e91954da600 Ch1-200 (document_truth; manifest:204-neg-wx-200-clean)
- `arc` / `active` / `medium`: arc:arc-ceafd43a Ch176-200 (arc_summary_range; arc_summaries:arc-ceafd43a)
- `thread` / `open` / `medium`: thread:human_mark:cont-fs-fs-273a8408be8e4caf8cbc1e91954da600-0bec2ede Ch144-? (human_mark_thread; human_marks:cont-fs-fs-273a8408be8e4caf8cbc1e91954da600-0bec2ede)
- `thread` / `open` / `medium`: thread:human_mark:cont-fs-fs-273a8408be8e4caf8cbc1e91954da600-10a94141 Ch135-? (human_mark_thread; human_marks:cont-fs-fs-273a8408be8e4caf8cbc1e91954da600-10a94141)
- `thread` / `open` / `medium`: thread:human_mark:cont-fs-fs-273a8408be8e4caf8cbc1e91954da600-10e2d6c7 Ch189-? (human_mark_thread; human_marks:cont-fs-fs-273a8408be8e4caf8cbc1e91954da600-10e2d6c7)
- `thread` / `open` / `medium`: thread:human_mark:cont-fs-fs-273a8408be8e4caf8cbc1e91954da600-11350e41 Ch156-? (human_mark_thread; human_marks:cont-fs-fs-273a8408be8e4caf8cbc1e91954da600-11350e41)
- `thread` / `open` / `medium`: thread:human_mark:cont-fs-fs-273a8408be8e4caf8cbc1e91954da600-168d64fc Ch141-? (human_mark_thread; human_marks:cont-fs-fs-273a8408be8e4caf8cbc1e91954da600-168d64fc)
- `thread` / `open` / `medium`: thread:human_mark:cont-fs-fs-273a8408be8e4caf8cbc1e91954da600-186fef1f Ch141-? (human_mark_thread; human_marks:cont-fs-fs-273a8408be8e4caf8cbc1e91954da600-186fef1f)
- `thread` / `open` / `medium`: thread:human_mark:cont-fs-fs-273a8408be8e4caf8cbc1e91954da600-197f2b24 Ch168-? (human_mark_thread; human_marks:cont-fs-fs-273a8408be8e4caf8cbc1e91954da600-197f2b24)
- `thread` / `open` / `medium`: thread:human_mark:cont-fs-fs-273a8408be8e4caf8cbc1e91954da600-1bac529c Ch156-? (human_mark_thread; human_marks:cont-fs-fs-273a8408be8e4caf8cbc1e91954da600-1bac529c)

### 204-neg-urban-200-clean
- `mainline` / `active` / `medium`: mainline:urban:81e345042b124ee2a73094b82e4be555 Ch1-200 (document_truth; manifest:204-neg-urban-200-clean)
- `arc` / `active` / `medium`: arc:arc-096e8a7d Ch176-200 (arc_summary_range; arc_summaries:arc-096e8a7d)
- `thread` / `open` / `medium`: thread:human_mark:cont-fs-fs-81e345042b124ee2a73094b82e4be555-04318c3f Ch105-? (human_mark_thread; human_marks:cont-fs-fs-81e345042b124ee2a73094b82e4be555-04318c3f)
- `thread` / `open` / `medium`: thread:human_mark:cont-fs-fs-81e345042b124ee2a73094b82e4be555-06b6ab33 Ch99-? (human_mark_thread; human_marks:cont-fs-fs-81e345042b124ee2a73094b82e4be555-06b6ab33)
- `thread` / `open` / `medium`: thread:human_mark:cont-fs-fs-81e345042b124ee2a73094b82e4be555-07f28d27 Ch159-? (human_mark_thread; human_marks:cont-fs-fs-81e345042b124ee2a73094b82e4be555-07f28d27)
- `thread` / `open` / `medium`: thread:human_mark:cont-fs-fs-81e345042b124ee2a73094b82e4be555-169dc311 Ch195-? (human_mark_thread; human_marks:cont-fs-fs-81e345042b124ee2a73094b82e4be555-169dc311)
- `thread` / `open` / `medium`: thread:human_mark:cont-fs-fs-81e345042b124ee2a73094b82e4be555-1b0bab01 Ch165-? (human_mark_thread; human_marks:cont-fs-fs-81e345042b124ee2a73094b82e4be555-1b0bab01)
- `thread` / `open` / `medium`: thread:human_mark:cont-fs-fs-81e345042b124ee2a73094b82e4be555-1e433daa Ch102-? (human_mark_thread; human_marks:cont-fs-fs-81e345042b124ee2a73094b82e4be555-1e433daa)
- `thread` / `open` / `medium`: thread:human_mark:cont-fs-fs-81e345042b124ee2a73094b82e4be555-1f6f7b92 Ch153-? (human_mark_thread; human_marks:cont-fs-fs-81e345042b124ee2a73094b82e4be555-1f6f7b92)
- `thread` / `open` / `medium`: thread:human_mark:cont-fs-fs-81e345042b124ee2a73094b82e4be555-21f82532 Ch102-? (human_mark_thread; human_marks:cont-fs-fs-81e345042b124ee2a73094b82e4be555-21f82532)

## 后续路由

- Task 207: V10 收口与归档；登记 Storyline Tree 的生产化建议，不在本任务接 runtime。
- 若后续生产化，优先从 derived report-only view 开始，不直接改变 Ch200 hard gate。
- Task 206 输出保持 report-only，不进入 hard gate。
