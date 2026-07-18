# Task 172d DONE — 文学护栏跨体裁化

> **完成时间**: 2026-07-15  
> **归属**: V8.3 / GenreProfile 层 3  
> **结论**: ✅ 完成。既有文学护栏已从科幻主角名与科幻 lexicon 中解耦，scifi 保持回退等价，xuanhuan/wuxia/urban 可使用各自 GenreProfile lexicon。

## 已交付

1. `literary_guardrail_observe.py` 的主动选择 / 配角目标 observe 路径从项目解析主角名与体裁 lexicon，不再依赖 `"林渊"` 默认值。
2. `GenreProfile` 支持跨体裁 lexicon；xuanhuan / wuxia / urban 已配置各自主动动词、代价词、配角动作词与后果词。
3. scifi / 无 profile 场景保持科幻默认 lexicon 回退。
4. `review_merger.py` 的 show-dont-tell 认知豁免移除科幻主角专名短语，改为体裁中性的认知动词触发；新增玄幻主角回归测试。

## 验证

```powershell
python -m pytest tests/test_review_merger.py tests/test_171w_text_guardrail_observe.py tests/test_172d_cross_genre_guardrails.py -q
```

结果：`35 passed`

```powershell
rg 林渊 src\songyan\evals src\songyan\workflows -n
```

结果：仅剩 `literary_guardrail_observe.py` 中说明“替代硬编码”的注释，无运行时代码硬编码主角名。

## 影响

172d 作为 172a.7 的硬前置已闭合；V8 的多体裁质量报告与后续 Ch100 爬坡不再受科幻专名 / 科幻 lexicon 假失败影响。
