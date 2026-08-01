# Task 203 优秀度报告整合

> generated_at: `2026-08-01T08:25:21.370306+00:00`

## 边界

- report-only / observe-only
- standalone offline report; not wired into songyan report
- does not call LLMs or regenerate prose
- does not write SQLite
- does not modify Writer or CreativeDirector prompts
- does not enter accept/reject gates
- does not change CED, five-gate, segment audit, or T9
- does not generate an excellence total score, chapter ordering, or binary verdict

## Summary

- report_only: `True`
- source_artifact_count: `7`
- chapter_view_count: `60`
- signal_view_count: `50`
- hard_quality_gate_policy: Ch200 hard gates remain external five-gate / T9 / segment audit facts; this report only references excellence observations.
- no_hard_score_policy: No integrated excellence total score, chapter ordering, or binary verdict is produced.
- next_route: Task 204 KG graph diff spike; CLI integration is deferred to Task 207.

## Source Artifacts

| task | type | report_only | generated_at | path |
|------|------|-------------|--------------|------|
| 196-sample | calibration_data | None | - | `tasks/196-excellence-sample-set.json` |
| 196-annotations | calibration_data | None | - | `tasks/196-excellence-annotations.json` |
| 197/198 | report | True | 2026-08-01T01:41:56.971979+00:00 | `tasks/197-198-excellence-signals-report.json` |
| 199 | report | True | 2026-08-01T03:12:41.994120+00:00 | `tasks/199-style-card-report.json` |
| 200 | report | True | 2026-08-01T04:34:26.522743+00:00 | `tasks/200-character-voice-anchor-report.json` |
| 201 | report | True | 2026-08-01T04:53:02.888485+00:00 | `tasks/201-judge-bias-report.json` |
| 202 | report | True | 2026-08-01T07:28:46.020139+00:00 | `tasks/202-readability-feasibility-report.json` |

## Calibration Truth

- truth_source: Task 196 anchor + spotcheck agent-deep-read
- truth_records: `24`
- anchor_records: `12`
- spotcheck_records: `12`
- prelabel_records: `48`
- prelabel_usage: low-confidence comparison only; never calibration truth

## Signal Layers

| layer | tasks | status | signals | chapters | notes |
|-------|-------|--------|--------:|---------:|-------|
| structure | 197 | `report-only` | 4 | 40 | Task 197 precision=0.40, recall=0.80 |
| ai_tone | 198 | `report-only` | 8 | 53 | Task 198 precision=0.65, recall=1.00 |
| style | 199 | `report-only` | 15 | 60 | style card is observation-only |
| voice | 200 | `report-only` | 2 | 18 | unknown attribution ratio remains material |
| judge_bias | 201 | `report-only` | 6 | 8 | protocol output, not an online judge improvement |
| readability | 202 | `report-only` | 15 | 45 | true perplexity deferred; proxy false positives expected |

## Signal View

| layer | signal | task | status | chapters | evidence | calibration / notes |
|-------|--------|------|--------|---------:|---------:|---------------------|
| ai_tone | `chapter_self_reference` | 198 | `report-only` | 4 | 13 | truth_rule=ai_tone<=2 or overall<=2, evaluated=24, precision=0.652, recall=1.0 |
| ai_tone | `cross_chapter_verbatim_repeat` | 198 | `report-only` | 2 | 2 | truth_rule=ai_tone<=2 or overall<=2, evaluated=24, precision=0.652, recall=1.0 |
| ai_tone | `engineering_residue` | 198 | `report-only` | 5 | 12 | truth_rule=ai_tone<=2 or overall<=2, evaluated=24, precision=0.652, recall=1.0 |
| ai_tone | `legacy_ai_tell` | 198 | `report-only` | 1 | 2 | truth_rule=ai_tone<=2 or overall<=2, evaluated=24, precision=0.652, recall=1.0 |
| ai_tone | `not_but_template` | 198 | `report-only` | 28 | 28 | truth_rule=ai_tone<=2 or overall<=2, evaluated=24, precision=0.652, recall=1.0 |
| ai_tone | `setting_patch_segment` | 198 | `report-only` | 2 | 2 | truth_rule=ai_tone<=2 or overall<=2, evaluated=24, precision=0.652, recall=1.0 |
| ai_tone | `template_rhetoric_density` | 198 | `report-only` | 53 | 53 | truth_rule=ai_tone<=2 or overall<=2, evaluated=24, precision=0.652, recall=1.0 |
| ai_tone | `verbatim_sentence_repeat` | 198 | `report-only` | 4 | 5 | truth_rule=ai_tone<=2 or overall<=2, evaluated=24, precision=0.652, recall=1.0 |
| judge_bias | `engineering_artifact_blindness` | 201 | `report-only` | 2 | 2 | truth_low_ai_tone_with_engineering_signal=7, prelabel_high_despite_engineering_signal=2 |
| judge_bias | `evidence_drift` | 201 | `report-only` | 0 | 8 | prelabel_quote_count=134, prelabel_verbatim_count=106, prelabel_fidelity_ratio=0.791 |
| judge_bias | `leniency_bias` | 201 | `report-only` | 4 | 8 | compared_dimensions=48, positive_delta=46, negative_delta=0, major_delta_ge_2=24 |
| judge_bias | `low_score_blindness` | 201 | `report-only` | 8 | 8 | prelabel_low_scores_le_2=0, truth_low_scores_le_2=37, truth_records=24, blind_spot_chapters=10 |
| judge_bias | `style_vs_quality_confusion` | 201 | `report-only` | 6 | 6 | style_cards=3, strong_truth_records_with_style_risks=6, report_only=True |
| judge_bias | `voice_homogeneity_blindness` | 201 | `report-only` | 8 | 8 | ai_tone_major_delta_ge_2=9, voice_anchor_count=34, unknown_attribution_ratio_all=0.599, weak_with_voice_evidence=15 |
| readability | `dialogue_ratio` | 202 | `report-only` | 12 | 12 | chapters_with_signal=12, sample_chapters=60, weak_samples=15, weak_with_signal=3 |
| readability | `flag:dash_pressure` | 202 | `report-only` | 44 | 44 | readability proxy flag; not a quality defect by itself |
| readability | `flag:dialogue_heavy` | 202 | `report-only` | 1 | 1 | readability proxy flag; not a quality defect by itself |
| readability | `flag:dialogue_sparse` | 202 | `report-only` | 11 | 11 | readability proxy flag; not a quality defect by itself |
| readability | `flag:ellipsis_pressure` | 202 | `report-only` | 11 | 11 | readability proxy flag; not a quality defect by itself |
| readability | `flag:long_sentence_load` | 202 | `report-only` | 1 | 1 | readability proxy flag; not a quality defect by itself |
| readability | `flag:low_info_term_density` | 202 | `report-only` | 11 | 11 | readability proxy flag; not a quality defect by itself |
| readability | `flag:low_lexical_variety` | 202 | `report-only` | 7 | 7 | readability proxy flag; not a quality defect by itself |
| readability | `flag:short_paragraph_staccato` | 202 | `report-only` | 38 | 38 | readability proxy flag; not a quality defect by itself |
| readability | `flag:top_bigram_repetition` | 202 | `report-only` | 2 | 2 | readability proxy flag; not a quality defect by itself |
| readability | `lexical_repetition_proxy` | 202 | `report-only` | 18 | 18 | chapters_with_signal=18, sample_chapters=60, weak_samples=15, weak_with_signal=7 |
| readability | `paragraph_readability` | 202 | `report-only` | 38 | 38 | chapters_with_signal=38, sample_chapters=60, weak_samples=15, weak_with_signal=10 |
| readability | `perplexity_feasibility` | 202 | `defer` | 0 | 0 | requires_model_weights=True, requires_tokenizer_policy=True, reproducible_without_external_model=False |
| readability | `punctuation_rhythm` | 202 | `report-only` | 45 | 45 | chapters_with_signal=45, sample_chapters=60, weak_samples=15, weak_with_signal=11 |
| readability | `sentence_readability` | 202 | `report-only` | 1 | 1 | chapters_with_signal=1, sample_chapters=60, weak_samples=15, weak_with_signal=1 |
| structure | `beat_rhythm_repetition` | 197 | `report-only` | 40 | 40 | truth_rule=homogeneity<=2 or tension<=2 or overall<=2, evaluated=24, precision=0.4, recall=0.8 |
| structure | `motif_reuse_density` | 197 | `report-only` | 12 | 12 | truth_rule=homogeneity<=2 or tension<=2 or overall<=2, evaluated=24, precision=0.4, recall=0.8 |
| structure | `scene_function_homogeneity` | 197 | `report-only` | 26 | 26 | truth_rule=homogeneity<=2 or tension<=2 or overall<=2, evaluated=24, precision=0.4, recall=0.8 |
| structure | `tension_flatline` | 197 | `report-only` | 21 | 21 | truth_rule=homogeneity<=2 or tension<=2 or overall<=2, evaluated=24, precision=0.4, recall=0.8 |
| style | `anti_pattern:beat_rhythm_repetition` | 199 | `report-only` | 40 | 80 | anti-patterns are aggregated from Task 197/198 hits |
| style | `anti_pattern:chapter_self_reference` | 199 | `report-only` | 13 | 26 | anti-patterns are aggregated from Task 197/198 hits |
| style | `anti_pattern:cross_chapter_verbatim_repeat` | 199 | `report-only` | 2 | 4 | anti-patterns are aggregated from Task 197/198 hits |
| style | `anti_pattern:engineering_residue` | 199 | `report-only` | 12 | 24 | anti-patterns are aggregated from Task 197/198 hits |
| style | `anti_pattern:legacy_ai_tell` | 199 | `report-only` | 2 | 4 | anti-patterns are aggregated from Task 197/198 hits |
| style | `anti_pattern:motif_reuse_density` | 199 | `report-only` | 12 | 24 | anti-patterns are aggregated from Task 197/198 hits |
| style | `anti_pattern:not_but_template` | 199 | `report-only` | 28 | 56 | anti-patterns are aggregated from Task 197/198 hits |
| style | `anti_pattern:scene_function_homogeneity` | 199 | `report-only` | 26 | 52 | anti-patterns are aggregated from Task 197/198 hits |
| style | `anti_pattern:setting_patch_segment` | 199 | `report-only` | 2 | 4 | anti-patterns are aggregated from Task 197/198 hits |
| style | `anti_pattern:template_rhetoric_density` | 199 | `report-only` | 53 | 106 | anti-patterns are aggregated from Task 197/198 hits |
| style | `anti_pattern:tension_flatline` | 199 | `report-only` | 21 | 42 | anti-patterns are aggregated from Task 197/198 hits |
| style | `anti_pattern:verbatim_sentence_repeat` | 199 | `report-only` | 5 | 10 | anti-patterns are aggregated from Task 197/198 hits |
| style | `style_card:all` | 199 | `report-only` | 60 | 12 | style card is an observed profile, not a prompt constraint; strong samples may still contain style risks |
| style | `style_card:genre:scifi` | 199 | `report-only` | 30 | 10 | style card is an observed profile, not a prompt constraint; strong samples may still contain style risks |
| style | `style_card:genre:xuanhuan` | 199 | `report-only` | 30 | 9 | style card is an observed profile, not a prompt constraint; strong samples may still contain style risks |
| voice | `unknown_attribution` | 200 | `report-only` | 1 | 1408 | ratio=0.599 |
| voice | `voice_anchor` | 200 | `report-only` | 18 | 226 | speaker attribution is heuristic; not DialogueStyleCard and not written back to character profiles |

## Chapter View

| genre | chapter | calibration | layers | notes |
|-------|---------|-------------|--------|-------|
| scifi | 1 | anchor | structure:2, ai_tone:1, style:2, voice:2, judge_bias:1, readability:1 | calibration truth from agent-deep-read |
| scifi | 17 | spotcheck | structure:1, ai_tone:1, style:2, voice:1, readability:1 | calibration truth from agent-deep-read |
| scifi | 21 | - | ai_tone:2, style:2, voice:1, readability:3 | - |
| scifi | 23 | - | structure:1, ai_tone:1, style:2, readability:3 | - |
| scifi | 32 | anchor | structure:3, ai_tone:1, style:2, judge_bias:1, readability:3 | calibration truth from agent-deep-read |
| scifi | 39 | spotcheck | ai_tone:1, style:2, judge_bias:2, readability:3 | calibration truth from agent-deep-read |
| scifi | 47 | - | structure:4, ai_tone:1, style:2, voice:1, readability:3 | - |
| scifi | 50 | - | structure:2, ai_tone:2, style:2, voice:1, readability:1 | - |
| scifi | 53 | spotcheck | structure:2, ai_tone:2, style:2, judge_bias:2, readability:1 | calibration truth from agent-deep-read |
| scifi | 60 | - | structure:2, ai_tone:3, style:2, readability:3 | - |
| scifi | 61 | - | structure:2, ai_tone:1, style:2, readability:3 | - |
| scifi | 71 | - | structure:3, ai_tone:1, style:2, voice:1, readability:2 | - |
| scifi | 80 | spotcheck | structure:3, ai_tone:3, style:2, judge_bias:2, readability:2 | calibration truth from agent-deep-read |
| scifi | 84 | anchor | structure:3, ai_tone:5, style:2, voice:1, judge_bias:1, readability:4 | calibration truth from agent-deep-read |
| scifi | 92 | - | structure:2, ai_tone:3, style:2, voice:1, readability:2 | - |
| scifi | 98 | - | structure:3, ai_tone:2, style:2, readability:3 | - |
| scifi | 104 | anchor | structure:3, ai_tone:1, style:2, voice:1, judge_bias:1, readability:1 | calibration truth from agent-deep-read |
| scifi | 105 | spotcheck | structure:3, ai_tone:1, style:2, judge_bias:1, readability:3 | calibration truth from agent-deep-read |
| scifi | 118 | - | structure:1, ai_tone:2, style:2, voice:1, readability:1 | - |
| scifi | 120 | - | structure:1, ai_tone:2, style:2, readability:1 | - |
| scifi | 134 | spotcheck | structure:1, ai_tone:2, style:2, readability:3 | calibration truth from agent-deep-read |
| scifi | 135 | - | structure:1, ai_tone:2, style:2, readability:3 | - |
| scifi | 145 | - | structure:2, ai_tone:1, style:2, voice:1, readability:2 | - |
| scifi | 148 | - | structure:2, ai_tone:2, style:2, readability:4 | - |
| scifi | 162 | - | structure:2, ai_tone:2, style:2, readability:1 | - |
| scifi | 164 | - | structure:3, ai_tone:2, style:2, readability:3 | - |
| scifi | 169 | - | structure:1, ai_tone:2, style:2, readability:3 | - |
| scifi | 178 | - | structure:1, ai_tone:1, style:2, voice:1, readability:2 | - |
| scifi | 194 | anchor | structure:2, ai_tone:2, style:2, judge_bias:1, readability:5 | calibration truth from agent-deep-read |
| scifi | 199 | anchor | structure:1, ai_tone:1, style:2, judge_bias:1, readability:2 | calibration truth from agent-deep-read |
| xuanhuan | 1 | anchor | ai_tone:1, style:2, voice:2, judge_bias:1, readability:1 | calibration truth from agent-deep-read |
| xuanhuan | 17 | spotcheck | structure:1, ai_tone:1, style:2, voice:1, judge_bias:2 | calibration truth from agent-deep-read |
| xuanhuan | 21 | - | structure:1, style:2 | - |
| xuanhuan | 23 | - | structure:1, ai_tone:2, style:2, readability:1 | - |
| xuanhuan | 32 | spotcheck | structure:2, ai_tone:1, style:2, readability:1 | calibration truth from agent-deep-read |
| xuanhuan | 39 | - | structure:1, ai_tone:1, style:2, readability:1 | - |
| xuanhuan | 47 | - | structure:1, style:2, readability:1 | - |
| xuanhuan | 50 | anchor | structure:2, ai_tone:3, style:2, judge_bias:1 | calibration truth from agent-deep-read |
| xuanhuan | 53 | spotcheck | structure:2, style:2, voice:1, judge_bias:1, readability:2 | calibration truth from agent-deep-read |
| xuanhuan | 60 | - | structure:3, ai_tone:2, style:2, readability:3 | - |
| xuanhuan | 61 | - | structure:4, ai_tone:1, style:2, readability:3 | - |
| xuanhuan | 71 | - | structure:2, ai_tone:2, style:2, readability:3 | - |
| xuanhuan | 80 | spotcheck | structure:2, ai_tone:2, style:2, judge_bias:1, readability:1 | calibration truth from agent-deep-read |
| xuanhuan | 84 | - | structure:2, ai_tone:1, style:2, readability:2 | - |
| xuanhuan | 92 | - | structure:3, ai_tone:1, style:2, readability:2 | - |
| xuanhuan | 98 | - | structure:2, ai_tone:1, style:2, readability:1 | - |
| xuanhuan | 104 | anchor | ai_tone:2, style:2, voice:1, judge_bias:1, readability:1 | calibration truth from agent-deep-read |
| xuanhuan | 105 | spotcheck | ai_tone:2, style:2, judge_bias:2, readability:3 | calibration truth from agent-deep-read |
| xuanhuan | 118 | anchor | structure:1, ai_tone:2, style:2, judge_bias:1, readability:4 | calibration truth from agent-deep-read |
| xuanhuan | 120 | - | structure:1, ai_tone:2, style:2, readability:2 | - |
| xuanhuan | 134 | spotcheck | structure:1, ai_tone:3, style:2, judge_bias:3, readability:2 | calibration truth from agent-deep-read |
| xuanhuan | 135 | - | ai_tone:1, style:2 | - |
| xuanhuan | 145 | - | structure:1, ai_tone:2, style:2, readability:4 | - |
| xuanhuan | 148 | - | structure:2, ai_tone:2, style:2, readability:3 | - |
| xuanhuan | 162 | - | structure:1, ai_tone:2, style:2 | - |
| xuanhuan | 164 | - | structure:1, ai_tone:2, style:2, readability:4 | - |
| xuanhuan | 169 | anchor | structure:1, ai_tone:1, style:2, judge_bias:1, readability:3 | calibration truth from agent-deep-read |
| xuanhuan | 178 | - | structure:1, ai_tone:2, style:2, voice:1, readability:3 | - |
| xuanhuan | 194 | anchor | structure:1, ai_tone:2, style:2, voice:1, judge_bias:1, readability:1 | calibration truth from agent-deep-read |
| xuanhuan | 199 | - | structure:2, ai_tone:2, style:2, readability:2 | - |

## Confidence Notes

- **197 / structure**: precision=0.4, recall=0.8; truth_rule=homogeneity<=2 or tension<=2 or overall<=2
- **198 / ai_tone**: precision=0.652, recall=1.0; truth_rule=ai_tone<=2 or overall<=2
- **200 / voice**: unknown attribution ratio=0.599; do not fabricate speakers
- **202 / readability**: true perplexity is deferred; readability proxies have 6/6 strong-sample hit pressure
- **201 / judge_bias**: prelabel is comparison-only and must not become truth

## 后续路由

- Task 204: KG 图 diff spike。
- Task 207: 决定是否把本独立报告入口收编到 CLI / `songyan report`。
- 本报告保持 report-only，不成为任何 hard gate 输入。
