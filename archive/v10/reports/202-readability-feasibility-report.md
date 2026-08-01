# Task 202 Perplexity / 可读性可行性 Spike 报告

> generated_at: `2026-08-01T07:28:46.020139+00:00`
> sample_set: `archive/v10/artifacts/196-excellence-sample-set.json`
> annotations: `archive/v10/artifacts/196-excellence-annotations.json`
> excellence_report: `archive/v10/artifacts/197-198-excellence-signals-report.json`
> style_card_report: `archive/v10/artifacts/199-style-card-report.json`
> voice_anchor_report: `archive/v10/artifacts/200-character-voice-anchor-report.json`
> judge_bias_report: `archive/v10/artifacts/201-judge-bias-report.json`

## 边界

- report-only / observe-only
- does not call LLMs
- does not download or require external language-model weights
- does not modify Writer or CreativeDirector prompts
- does not enter accept/reject gates
- does not change CED, five-gate, segment audit, or T9

## 总览

- sample_chapters: `60`
- chapters_with_any_proxy_hit: `55`
- weak_proxy_coverage: `13/15`
- strong_proxy_false_positive_pressure: `6/6`
- top_flags: `[{'flag': 'dash_pressure', 'count': 44}, {'flag': 'short_paragraph_staccato', 'count': 38}, {'flag': 'ellipsis_pressure', 'count': 11}, {'flag': 'dialogue_sparse', 'count': 11}, {'flag': 'low_info_term_density', 'count': 11}, {'flag': 'low_lexical_variety', 'count': 7}, {'flag': 'top_bigram_repetition', 'count': 2}, {'flag': 'long_sentence_load', 'count': 1}]`

## 候选信号结论

| signal | decision | hit chapters | weak coverage | recommendation |
|--------|----------|-------------:|---------------|----------------|
| sentence_readability | `report-only` | 1 | 1/15 | 展示为章节读感 proxy，不参与排序或 hard gate。 |
| paragraph_readability | `report-only` | 38 | 10/15 | 展示为辅助读感维度，并链接 Task 197 张力/场景证据。 |
| dialogue_ratio | `report-only` | 12 | 3/15 | 展示为 dialogue context，和 Task 200 voice anchors 并列。 |
| punctuation_rhythm | `report-only` | 45 | 11/15 | 仅作为节奏解释项，默认低权重展示。 |
| lexical_repetition_proxy | `report-only` | 18 | 7/15 | 作为 Task 197/198 的补充证据，不单独评分。 |
| perplexity_feasibility | `defer` | - | - | Defer true perplexity to a later offline experiment with pinned local model weights, tokenizer policy, and cost budget; use readability proxies as report-only Task 203 context for V10. |

## Perplexity Feasibility

- decision: `defer`
- reproducible_without_external_model: `False`
- requires_model_weights: `True`
- requires_tokenizer_policy: `True`
- recommendation: Defer true perplexity to a later offline experiment with pinned local model weights, tokenizer policy, and cost budget; use readability proxies as report-only Task 203 context for V10.
- risks:
  - No project-local Chinese language model weights are versioned in the repo.
  - Downloading a model would make the spike non-reproducible in offline CI.
  - Tokenizer choice changes PPL materially for Chinese webnovel names and invented terms.
  - PPL can reward generic fluent prose and punish genre-specific proper nouns.
  - Compute cost is not bounded without a fixed local model and batch policy.

## Sanity Check

- truth_records: `24`
- weak_samples: `15`
- weak_with_proxy_hit: `13`
- strong_samples: `6`
- strong_with_proxy_hit: `6`
- weak_unexplained: xuanhuan Ch17, xuanhuan Ch50

## 决策明细

### sentence_readability

- decision: `report-only`
- definition: 句长均值、长句比例与碎片短句比例。
- sample_summary:
  - chapters_with_signal: `1`
  - sample_chapters: `60`
  - weak_samples: `15`
  - weak_with_signal: `1`
  - decision_basis: `directional proxy over Task 196 sample`
- evidence:
  - scifi Ch134: long_sentence_load
- limitations:
  - 长句或短句密集是风格风险，不等于质量缺陷。
  - 中文网文动作段常天然短句密集。
- Task 203: 展示为章节读感 proxy，不参与排序或 hard gate。

### paragraph_readability

- decision: `report-only`
- definition: 段长均值、超长段比例与连续短段节奏。
- sample_summary:
  - chapters_with_signal: `38`
  - sample_chapters: `60`
  - weak_samples: `15`
  - weak_with_signal: `10`
  - decision_basis: `directional proxy over Task 196 sample`
- evidence:
  - scifi Ch1: short_paragraph_staccato
  - scifi Ch21: short_paragraph_staccato
  - scifi Ch23: short_paragraph_staccato
  - scifi Ch32: short_paragraph_staccato
  - scifi Ch47: short_paragraph_staccato
  - scifi Ch60: short_paragraph_staccato
  - scifi Ch61: short_paragraph_staccato
  - scifi Ch80: short_paragraph_staccato
- limitations:
  - 段落长度受体裁、战斗密度和对话排版影响大。
  - 需要结合 Task 197 tension / scene function 解释。
- Task 203: 展示为辅助读感维度，并链接 Task 197 张力/场景证据。

### dialogue_ratio

- decision: `report-only`
- definition: 对白字符占比、对白行数和对白稀疏 / 过密风险。
- sample_summary:
  - chapters_with_signal: `12`
  - sample_chapters: `60`
  - weak_samples: `15`
  - weak_with_signal: `3`
  - decision_basis: `directional proxy over Task 196 sample`
- evidence:
  - scifi Ch23: dialogue_sparse
  - scifi Ch39: dialogue_sparse
  - scifi Ch71: dialogue_sparse
  - scifi Ch134: dialogue_sparse
  - scifi Ch135: dialogue_sparse
  - scifi Ch148: dialogue_sparse
  - xuanhuan Ch39: dialogue_sparse
  - xuanhuan Ch60: dialogue_heavy
- limitations:
  - 对白稀疏不等于坏章；揭示章和动作章可能需要少对白。
  - 角色声纹质量仍以 Task 200 为主。
- Task 203: 展示为 dialogue context，和 Task 200 voice anchors 并列。

### punctuation_rhythm

- decision: `report-only`
- definition: 问号、叹号、省略号、破折号每千字密度。
- sample_summary:
  - chapters_with_signal: `45`
  - sample_chapters: `60`
  - weak_samples: `15`
  - weak_with_signal: `11`
  - decision_basis: `directional proxy over Task 196 sample`
- evidence:
  - scifi Ch17: dash_pressure
  - scifi Ch21: dash_pressure, ellipsis_pressure
  - scifi Ch23: dash_pressure
  - scifi Ch32: dash_pressure
  - scifi Ch39: dash_pressure
  - scifi Ch47: dash_pressure
  - scifi Ch50: dash_pressure
  - scifi Ch53: dash_pressure
- limitations:
  - 标点密度对中文网文节奏有解释力，但误报率高。
  - 省略号和破折号在悬念章中是正常修辞。
- Task 203: 仅作为节奏解释项，默认低权重展示。

### lexical_repetition_proxy

- decision: `report-only`
- definition: 唯一 bigram 比例、高频 bigram 密度与低信息词密度。
- sample_summary:
  - chapters_with_signal: `18`
  - sample_chapters: `60`
  - weak_samples: `15`
  - weak_with_signal: `7`
  - decision_basis: `directional proxy over Task 196 sample`
- evidence:
  - scifi Ch32: low_info_term_density
  - scifi Ch39: low_info_term_density
  - scifi Ch47: low_lexical_variety
  - scifi Ch61: low_info_term_density
  - scifi Ch84: low_lexical_variety, top_bigram_repetition
  - scifi Ch98: low_lexical_variety
  - scifi Ch105: low_info_term_density
  - scifi Ch145: low_lexical_variety
- limitations:
  - 轻量 ngram 不能理解设定专有名词的必要重复。
  - 与 Task 197/198 重复类信号有重叠，不能重复计分。
- Task 203: 作为 Task 197/198 的补充证据，不单独评分。

### perplexity_feasibility

- decision: `defer`
- definition: 真实 LM perplexity 的可复现性、依赖、成本和中文适配风险。
- sample_summary:
  - requires_model_weights: `True`
  - requires_tokenizer_policy: `True`
  - reproducible_without_external_model: `False`
  - upstream_reports_consumed: `{'task197198_chapters': 60, 'style_cards': 3, 'voice_anchors': 34, 'judge_supported_biases': 6}`
- evidence:
  - No project-local Chinese language model weights are versioned in the repo.
  - Downloading a model would make the spike non-reproducible in offline CI.
  - Tokenizer choice changes PPL materially for Chinese webnovel names and invented terms.
  - PPL can reward generic fluent prose and punish genre-specific proper nouns.
  - Compute cost is not bounded without a fixed local model and batch policy.
- limitations:
  - 本轮不下载模型、不联网、不调用 LLM。
  - PPL 对中文长篇网文和专名密度存在强 tokenizer 偏差。
- Task 203: Defer true perplexity to a later offline experiment with pinned local model weights, tokenizer policy, and cost budget; use readability proxies as report-only Task 203 context for V10.

## 逐章明细

| genre | chapter | flags | sent avg/long | para avg/overlong | dialogue | punct q/!/…/-- | lexical top/density |
|-------|---------|-------|---------------|-------------------|----------|-----------------|---------------------|
| scifi | 1 | short_paragraph_staccato | 18.2/0.06 | 25.1/0.00 | 0.33 | 5.1/0.3/7.7/6.8 | 林渊/0.013 |
| scifi | 17 | dash_pressure | 15.6/0.03 | 36.7/0.00 | 0.27 | 4.1/0.0/0.0/7.2 | 林渊/0.011 |
| scifi | 21 | dash_pressure, ellipsis_pressure, short_paragraph_staccato | 19.0/0.08 | 35.4/0.00 | 0.24 | 2.2/1.7/14.5/9.4 | 方舟/0.011 |
| scifi | 23 | dash_pressure, dialogue_sparse, short_paragraph_staccato | 22.9/0.13 | 41.7/0.00 | 0.01 | 0.7/0.0/2.9/8.4 | 林渊/0.009 |
| scifi | 32 | dash_pressure, low_info_term_density, short_paragraph_staccato | 23.3/0.17 | 41.2/0.00 | 0.34 | 4.3/0.0/2.2/9.8 | 林渊/0.008 |
| scifi | 39 | dash_pressure, dialogue_sparse, low_info_term_density | 23.1/0.14 | 46.4/0.00 | 0.02 | 0.7/0.0/0.0/14.8 | 不是/0.012 |
| scifi | 47 | dash_pressure, low_lexical_variety, short_paragraph_staccato | 15.6/0.02 | 24.7/0.00 | 0.40 | 6.5/0.0/3.4/9.3 | 声音/0.011 |
| scifi | 50 | dash_pressure | 22.6/0.13 | 44.9/0.00 | 0.34 | 3.9/0.2/5.1/10.4 | 林渊/0.012 |
| scifi | 53 | dash_pressure | 20.8/0.16 | 40.3/0.00 | 0.11 | 2.2/0.0/7.2/11.3 | 陈曦/0.012 |
| scifi | 60 | dash_pressure, ellipsis_pressure, short_paragraph_staccato | 19.8/0.08 | 35.6/0.00 | 0.27 | 2.2/0.3/26.2/8.2 | 林渊/0.011 |
| scifi | 61 | dash_pressure, low_info_term_density, short_paragraph_staccato | 23.4/0.16 | 36.5/0.00 | 0.19 | 1.7/0.0/0.8/13.4 | 林渊/0.011 |
| scifi | 71 | dash_pressure, dialogue_sparse | 18.7/0.06 | 43.4/0.00 | 0.03 | 0.6/0.0/2.8/11.2 | 林渊/0.010 |
| scifi | 80 | dash_pressure, short_paragraph_staccato | 15.5/0.05 | 28.6/0.00 | 0.25 | 3.6/1.9/0.7/8.9 | 林渊/0.011 |
| scifi | 84 | dash_pressure, low_lexical_variety, short_paragraph_staccato, top_bigram_repetition | 24.9/0.16 | 37.0/0.00 | 0.08 | 1.1/0.0/6.3/16.3 | 字段/0.020 |
| scifi | 92 | dash_pressure, short_paragraph_staccato | 22.6/0.17 | 43.5/0.00 | 0.31 | 2.4/0.0/5.0/7.7 | 林渊/0.009 |
| scifi | 98 | dash_pressure, low_lexical_variety, short_paragraph_staccato | 16.8/0.03 | 29.8/0.00 | 0.30 | 5.3/0.0/5.3/8.2 | 林渊/0.014 |
| scifi | 104 | dash_pressure | 25.2/0.19 | 37.3/0.00 | 0.12 | 1.1/0.0/2.5/9.5 | 林渊/0.011 |
| scifi | 105 | dash_pressure, low_info_term_density, short_paragraph_staccato | 23.3/0.19 | 37.2/0.00 | 0.20 | 2.6/0.5/2.2/14.4 | 不是/0.011 |
| scifi | 118 | dash_pressure | 20.1/0.06 | 36.2/0.00 | 0.23 | 2.3/0.3/5.4/8.4 | 林渊/0.011 |
| scifi | 120 | dash_pressure | 24.8/0.15 | 50.3/0.00 | 0.06 | 0.2/1.4/0.0/10.3 | 林渊/0.009 |
| scifi | 134 | dash_pressure, dialogue_sparse, long_sentence_load | 29.4/0.28 | 47.0/0.00 | 0.03 | 1.4/0.0/5.8/12.1 | 林渊/0.010 |
| scifi | 135 | dash_pressure, dialogue_sparse, short_paragraph_staccato | 22.8/0.16 | 30.4/0.00 | 0.01 | 0.3/0.0/0.0/11.8 | 林渊/0.013 |
| scifi | 145 | dash_pressure, low_lexical_variety | 21.3/0.10 | 36.5/0.00 | 0.06 | 0.2/0.2/0.0/9.2 | 意识/0.013 |
| scifi | 148 | dash_pressure, dialogue_sparse, low_lexical_variety, short_paragraph_staccato | 21.8/0.19 | 23.6/0.00 | 0.03 | 0.0/0.0/5.4/12.4 | 林渊/0.013 |
| scifi | 162 | dash_pressure | 22.4/0.14 | 56.7/0.00 | 0.28 | 3.3/0.0/0.7/9.1 | 林渊/0.012 |
| scifi | 164 | dash_pressure, low_lexical_variety, short_paragraph_staccato | 21.6/0.10 | 41.0/0.00 | 0.26 | 1.7/1.5/2.9/7.8 | 方舟/0.010 |
| scifi | 169 | dash_pressure, ellipsis_pressure, low_info_term_density | 25.1/0.20 | 59.9/0.00 | 0.12 | 1.2/0.9/12.3/11.1 | 林渊/0.009 |
| scifi | 178 | dash_pressure, short_paragraph_staccato | 19.5/0.10 | 33.1/0.00 | 0.06 | 2.4/2.4/4.4/11.5 | 林渊/0.008 |
| scifi | 194 | dash_pressure, ellipsis_pressure, low_lexical_variety, short_paragraph_staccato, top_bigram_repetition | 21.6/0.15 | 35.7/0.00 | 0.14 | 1.2/0.0/32.5/7.6 | 林渊/0.016 |
| scifi | 199 | dash_pressure, ellipsis_pressure | 21.7/0.14 | 34.4/0.00 | 0.05 | 1.6/0.0/12.6/11.3 | 林渊/0.011 |
| xuanhuan | 1 | short_paragraph_staccato | 20.1/0.10 | 40.3/0.00 | 0.06 | 3.1/1.1/1.7/3.9 | 陆沉/0.010 |
| xuanhuan | 17 | - | 21.7/0.11 | 35.2/0.00 | 0.09 | 2.6/0.5/3.1/5.5 | 陆沉/0.010 |
| xuanhuan | 21 | - | 21.2/0.08 | 32.3/0.00 | 0.09 | 3.6/0.0/4.9/5.5 | 陆沉/0.011 |
| xuanhuan | 23 | short_paragraph_staccato | 20.6/0.08 | 32.9/0.00 | 0.06 | 0.6/0.3/0.8/6.4 | 陆沉/0.011 |
| xuanhuan | 32 | short_paragraph_staccato | 18.5/0.03 | 30.0/0.00 | 0.06 | 1.7/0.0/7.5/4.2 | 陆沉/0.011 |
| xuanhuan | 39 | dialogue_sparse | 24.3/0.15 | 49.8/0.00 | 0.03 | 0.8/0.0/0.0/5.7 | 陆沉/0.009 |
| xuanhuan | 47 | short_paragraph_staccato | 22.2/0.11 | 36.7/0.00 | 0.04 | 3.1/4.5/0.6/3.6 | 陆沉/0.010 |
| xuanhuan | 50 | - | 23.3/0.09 | 43.7/0.00 | 0.09 | 1.7/1.7/0.0/6.1 | 陆沉/0.012 |
| xuanhuan | 53 | dash_pressure, short_paragraph_staccato | 17.3/0.06 | 27.1/0.00 | 0.20 | 0.4/0.7/4.4/9.9 | 陆沉/0.008 |
| xuanhuan | 60 | dialogue_heavy, low_info_term_density, short_paragraph_staccato | 20.2/0.12 | 26.6/0.00 | 0.45 | 5.7/0.0/5.4/6.9 | 灵渊/0.012 |
| xuanhuan | 61 | dash_pressure, low_info_term_density, short_paragraph_staccato | 16.4/0.04 | 21.2/0.00 | 0.23 | 4.5/0.3/5.2/15.6 | 陆沉/0.014 |
| xuanhuan | 71 | dash_pressure, dialogue_sparse, short_paragraph_staccato | 17.3/0.07 | 30.1/0.00 | 0.02 | 2.2/0.3/5.6/7.8 | 妖兽/0.007 |
| xuanhuan | 80 | short_paragraph_staccato | 23.9/0.14 | 39.7/0.00 | 0.04 | 2.7/0.0/4.5/6.1 | 陆沉/0.010 |
| xuanhuan | 84 | dash_pressure, ellipsis_pressure | 16.9/0.03 | 37.1/0.00 | 0.04 | 1.1/0.0/20.0/8.9 | 陆沉/0.013 |
| xuanhuan | 92 | dash_pressure, short_paragraph_staccato | 18.4/0.04 | 23.7/0.00 | 0.05 | 2.5/0.6/1.7/10.8 | 陆沉/0.013 |
| xuanhuan | 98 | dialogue_sparse | 21.4/0.08 | 35.6/0.00 | 0.02 | 0.3/0.0/0.0/6.7 | 陆沉/0.010 |
| xuanhuan | 104 | dash_pressure | 21.0/0.07 | 39.5/0.00 | 0.04 | 1.2/0.0/1.4/8.4 | 陆沉/0.013 |
| xuanhuan | 105 | ellipsis_pressure, low_info_term_density, short_paragraph_staccato | 20.7/0.11 | 27.8/0.00 | 0.11 | 2.1/0.0/10.9/5.4 | 碎片/0.009 |
| xuanhuan | 118 | dash_pressure, dialogue_sparse, low_info_term_density, short_paragraph_staccato | 20.9/0.08 | 27.1/0.00 | 0.02 | 0.4/0.0/2.2/8.3 | 像是/0.011 |
| xuanhuan | 120 | dash_pressure, short_paragraph_staccato | 19.6/0.09 | 39.8/0.00 | 0.24 | 1.3/0.0/3.8/8.8 | 陆沉/0.009 |
| xuanhuan | 134 | dash_pressure, short_paragraph_staccato | 22.8/0.17 | 30.9/0.00 | 0.28 | 2.9/1.0/0.7/8.2 | 母亲/0.009 |
| xuanhuan | 135 | - | 19.2/0.07 | 30.8/0.00 | 0.18 | 0.8/0.0/1.6/6.3 | 陆沉/0.010 |
| xuanhuan | 145 | dash_pressure, dialogue_sparse, low_info_term_density, short_paragraph_staccato | 19.4/0.08 | 26.1/0.00 | 0.03 | 4.2/0.6/5.0/10.8 | 陆沉/0.010 |
| xuanhuan | 148 | dash_pressure, ellipsis_pressure, short_paragraph_staccato | 17.7/0.06 | 28.2/0.00 | 0.29 | 3.9/0.3/22.7/8.8 | 封印/0.010 |
| xuanhuan | 162 | - | 25.7/0.17 | 46.7/0.00 | 0.20 | 2.1/0.0/0.8/6.3 | 陆沉/0.010 |
| xuanhuan | 164 | dash_pressure, ellipsis_pressure, low_info_term_density, short_paragraph_staccato | 17.5/0.07 | 25.9/0.00 | 0.16 | 1.1/0.0/16.7/10.4 | 陆沉/0.012 |
| xuanhuan | 169 | dash_pressure, ellipsis_pressure, short_paragraph_staccato | 17.9/0.09 | 26.8/0.00 | 0.29 | 5.0/0.0/15.1/9.2 | 陆沉/0.010 |
| xuanhuan | 178 | dash_pressure, ellipsis_pressure, short_paragraph_staccato | 21.4/0.10 | 34.6/0.00 | 0.12 | 1.8/2.1/14.1/8.3 | 陆沉/0.009 |
| xuanhuan | 194 | short_paragraph_staccato | 19.8/0.09 | 36.0/0.00 | 0.10 | 0.6/0.0/7.0/5.8 | 陆沉/0.010 |
| xuanhuan | 199 | dash_pressure, short_paragraph_staccato | 21.0/0.05 | 34.6/0.00 | 0.16 | 1.2/0.0/6.2/8.7 | 陆沉/0.012 |

## 局限

- 只覆盖 Task 196 的 xuanhuan + sci-fi 60 章样本。
- 可读性 proxy 只能解释局部读感风险，不能替代人工质量判断。
- 真实 perplexity 未执行；没有稳定本地中文长篇 LM 与 tokenizer 政策。
- 所有结论均为 Task 203 report-only 输入，不进入 hard gate。
