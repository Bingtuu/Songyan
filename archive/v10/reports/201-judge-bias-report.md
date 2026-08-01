# Task 201 Judge 偏差对策报告

> generated_at: `2026-08-01T04:53:02.888485+00:00`
> sample_set: `archive/v10/artifacts/196-excellence-sample-set.json`
> annotations: `archive/v10/artifacts/196-excellence-annotations.json`
> excellence_report: `archive/v10/artifacts/197-198-excellence-signals-report.json`
> style_card_report: `archive/v10/artifacts/199-style-card-report.json`
> voice_anchor_report: `archive/v10/artifacts/200-character-voice-anchor-report.json`

## 边界

- report-only / observe-only
- does not call LLM judges
- does not treat prelabel scores as truth
- does not modify Writer or CreativeDirector prompts
- does not enter accept/reject gates
- does not change CED, five-gate, segment audit, or T9

## 总览

- truth_records: `24`
- prelabel_records: `48`
- paired_spotcheck_records: `12`
- major_deltas_ge_2: `24`
- supported_biases: `6`
- prelabel_evidence_fidelity: `0.791`

## Score Delta（prelabel - truth）

| dimension | count | positive | negative | zero | mean_delta | major_delta>=2 |
|-----------|------:|---------:|---------:|-----:|-----------:|---------------:|
| homogeneity | 12 | 10 | 0 | 2 | 1.00 | 2 |
| tension | 12 | 12 | 0 | 0 | 1.58 | 7 |
| ai_tone | 12 | 12 | 0 | 0 | 1.75 | 9 |
| overall | 12 | 12 | 0 | 0 | 1.58 | 6 |

## Evidence Fidelity

| layer | quote_count | verbatim_count | fidelity | examples |
|-------|------------:|---------------:|---------:|----------|
| anchor | 45 | 45 | 1.000 | - |
| prelabel | 134 | 106 | 0.791 | Ch23: 心魔幻境中，唯有亲手斩杀幻象，方能破境。但你不杀，却劈碎虚空——此法从未有人用过。<br>Ch53: “别重蹈你爹娘的覆辙。别把自己填进去。”<br>Ch60: 她把自己变成了第二道屏障。 |
| spotcheck | 48 | 48 | 1.000 | - |

## Bias Findings

### leniency_bias

- status: `supported`
- definition: LLM prelabel scores are systematically higher than agent-deep-read truth.
- statistics:
  - compared_dimensions: `48`
  - positive_delta: `46`
  - negative_delta: `0`
  - major_delta_ge_2: `24`
  - mean_delta: `1.479`
- evidence:
  - xuanhuan Ch17 tension: prelabel=5, truth=3
  - xuanhuan Ch17 ai_tone: prelabel=4, truth=2
  - scifi Ch39 homogeneity: prelabel=4, truth=2
  - scifi Ch39 tension: prelabel=5, truth=3
  - scifi Ch39 ai_tone: prelabel=4, truth=2
  - scifi Ch39 overall: prelabel=4, truth=2
- countermeasures:
  - anchor_example_injection
  - prelabel_downweighting
  - blind_review_protocol

### low_score_blindness

- status: `supported`
- definition: The judge avoids or misses the low-score region proven by deep-read labels.
- statistics:
  - prelabel_low_scores_le_2: `0`
  - truth_low_scores_le_2: `37`
  - truth_records: `24`
  - blind_spot_chapters: `10`
- evidence:
  - xuanhuan Ch50 truth overall=2
  - xuanhuan Ch118 truth overall=2
  - xuanhuan Ch194 truth overall=2
  - scifi Ch32 truth overall=2
  - scifi Ch84 truth overall=2
  - scifi Ch194 truth overall=2
- countermeasures:
  - force_1_2_score_examples
  - require_low_score_checklist_before_scoring

### evidence_drift

- status: `supported`
- definition: Judge evidence quotes may be paraphrased, stitched, or absent from accepted prose.
- statistics:
  - prelabel_quote_count: `134`
  - prelabel_verbatim_count: `106`
  - prelabel_fidelity_ratio: `0.791`
- evidence:
  - Ch23: 心魔幻境中，唯有亲手斩杀幻象，方能破境。但你不杀，却劈碎虚空——此法从未有人用过。
  - Ch53: “别重蹈你爹娘的覆辙。别把自己填进去。”
  - Ch60: 她把自己变成了第二道屏障。
  - Ch61: “石殿里等你的人——是我。”
  - Ch71: 掌心的琥珀色火焰……自主追了上去，沿着气息收缩的轨迹钻进矿石的裂隙里。
  - Ch84: 你身上的那股力量……不是你自己的。
- countermeasures:
  - verbatim_evidence_check
  - reject_or_downweight_non_verbatim_quotes

### engineering_artifact_blindness

- status: `supported`
- definition: Judge misses generated/procedural artifacts such as self-reference and residue.
- statistics:
  - truth_low_ai_tone_with_engineering_signal: `7`
  - prelabel_high_despite_engineering_signal: `2`
- evidence:
  - xuanhuan Ch134: setting_patch_segment
  - scifi Ch80: chapter_self_reference, verbatim_sentence_repeat
- countermeasures:
  - mandatory_engineering_artifact_checklist
  - consume_task198_hard_evidence_as_report_context

### style_vs_quality_confusion

- status: `supported`
- definition: Observed style traits and repeated style risks are not equivalent to quality defects.
- statistics:
  - style_cards: `3`
  - strong_truth_records_with_style_risks: `6`
  - report_only: `True`
- evidence:
  - xuanhuan Ch1: template_rhetoric_density
  - xuanhuan Ch104: not_but_template, template_rhetoric_density
  - xuanhuan Ch169: beat_rhythm_repetition, template_rhetoric_density
  - scifi Ch1: beat_rhythm_repetition, template_rhetoric_density, tension_flatline
  - scifi Ch104: beat_rhythm_repetition, scene_function_homogeneity, template_rhetoric_density, tension_flatline
  - scifi Ch199: template_rhetoric_density, tension_flatline
- countermeasures:
  - separate_style_profile_from_quality_score
  - label_style_card_as_observation_only
- limitations:
  - Style card does not produce per-chapter quality truth.

### voice_homogeneity_blindness

- status: `supported`
- definition: Judge under-detects dialogue voice sameness and attribution uncertainty.
- statistics:
  - ai_tone_major_delta_ge_2: `9`
  - voice_anchor_count: `34`
  - unknown_attribution_ratio_all: `0.599`
  - weak_with_voice_evidence: `15`
  - weak_samples: `15`
- evidence:
  - xuanhuan Ch17: ai_tone prelabel=4, truth=2
  - scifi Ch39: ai_tone prelabel=4, truth=2
  - scifi Ch53: ai_tone prelabel=4, truth=2
  - xuanhuan Ch80: ai_tone prelabel=4, truth=2
  - scifi Ch80: ai_tone prelabel=4, truth=2
  - xuanhuan Ch105: ai_tone prelabel=4, truth=2
- countermeasures:
  - voice_homogeneity_checklist
  - unknown_attribution_warning
  - do_not_convert_voice_report_to_dialogue_style_card

## Countermeasure Protocol

### anchor_example_injection: Anchor examples for judge calibration

- status: `recommended`
- applies_to: leniency_bias, low_score_blindness
- steps:
  - Use Task 196 strong/weak anchor examples as rubric references.
  - Include at least one overall=2 and one ai_tone=1 example in offline judge trials.
  - Keep examples outside Writer / CreativeDirector prompts unless separately approved.
- notes:
  - Protocol only; Task 201 does not add or run a new prompt card.

### forced_checklist: Mandatory artifact/style/voice checklist

- status: `recommended`
- applies_to: engineering_artifact_blindness, style_vs_quality_confusion, voice_homogeneity_blindness
- steps:
  - Before scoring ai_tone, check Task 198 engineering artifact classes.
  - Before scoring homogeneity, inspect Task 197 structure risks.
  - Before scoring voice, inspect Task 200 unknown attribution and voice anchors.

### verbatim_evidence_check: Evidence quote verification

- status: `guardrail-only`
- applies_to: evidence_drift
- steps:
  - Every evidence quote must be searched in accepted prose.
  - Non-verbatim evidence is rejected or clearly downweighted.
  - No automatic revision may consume non-verbatim judge evidence.

### prelabel_downweighting: Prelabel is comparison-only

- status: `recommended`
- applies_to: leniency_bias, low_score_blindness
- steps:
  - Do not use prelabel scores as truth labels.
  - Use prelabel only for broad coverage and disagreement discovery.
  - Task 203 should display prelabel as low-confidence context.

### blind_review_protocol: Future multi-judge blind review

- status: `future-experiment`
- applies_to: leniency_bias, low_score_blindness
- steps:
  - Run multiple judge cards on the same anchor + spotcheck set.
  - Hide provenance labels during scoring.
  - Report inter-judge variance and do not convert aggregate score into a gate.
- notes:
  - Not executed in Task 201.

### goodhart_guardrail: Goodhart risk statement

- status: `guardrail-only`
- applies_to: leniency_bias, style_vs_quality_confusion, voice_homogeneity_blindness
- steps:
  - Do not optimize generation directly against judge scores.
  - Separate observation reports from acceptance criteria.
  - Any future gate proposal requires separate calibration and regression.

## 局限

- 本报告只使用 Task 196 的 24 章 agent-deep-read 真值做方向性分析。
- 未调用新 judge，不声明 judge v2 已改善。
- 所有对策均为协议建议；任何接入 prompt 或 gate 的尝试必须另立任务。
