# Task 038 DONE 报告：Writer Prompt 风格注入 + fatigue_words 扩充

> **完成日期**: 2026-06-02
> **执行人**: Kimi Code CLI
> **任务**: Task 038 — Writer Prompt 风格注入（Stage B Phase 5.4）

---

## 交付摘要

将 Task 035~037 的 Genre 模型升级和风格引擎输出注入 Writer Prompt，完成 Phase 5 闭环。同时基于基线报告扩充全 genre 疲劳词库。

---

## 修改清单

### 1. Writer Prompt 升级（`prompts/cards/writer/1.0.5.yaml`）

基于 1.0.4 新增 4 个条件渲染分区：

**风格基线参考** (`{% if style_baseline %}`):
```
- 句式节奏目标：{{ style_baseline.sentence_rhythm }}
- 描写密度目标：{{ style_baseline.description_density }}
- 对话占比目标：{{ style_baseline.dialogue_ratio }}
- 内心独白目标：{{ style_baseline.inner_monologue }}
- 视角深度目标：{{ style_baseline.pov_depth }}
```

**参考作品风格** (`{% if style_samples %}`):
```
- 【{{ sample.work_name }}（{{ sample.author }}）】
  - 代表性段落：{{ sample.excerpt }}
  - 风格特征：{{ sample.analysis }}
```

**当前章节节奏模板** (`{% if pacing_template %}`):
```
- 情感弧线：{{ pacing_template.emotion_arc }}
- 刺激点密度：{{ pacing_template.punch_density }} 个/千字
- 信息释放策略：{{ pacing_template.info_release_strategy }}
```

**感官描写侧重** (`{% if sensory_focus %}`):
```
- 【{{ sense.sense }}】强度目标 {{ sense.intensity_target }}，密度 {{ sense.description_density }} 字/千字
  示例：{{ sense.example_phrases }}
```

### 2. `_render_prompt()` 更新（`src/songyan/agents/writer.py`）

新增提取逻辑：
- `style_baseline`: 从 `ctx.genre_rules.style_baseline` 提取 dict
- `style_samples`: 从 `ctx.soft_references` 过滤 `type="style_sample"`，解析 content 中的 work_name/author/excerpt/analysis
- `pacing_template`: 根据 `goal.chapter_type` 匹配 `genre_rules.pacing_templates`，无匹配则 fallback 到第一个
- `sensory_focus`: 直接从 `genre_rules.sensory_templates` 提取

新增辅助函数 `_extract_field(text, start_marker, end_marker)` 用于解析 style_sample content。

### 3. GenreRules 扩展（`src/songyan/models/context.py` + `src/songyan/agents/context_manager.py`）

`GenreRules` 新增字段：
- `style_baseline: StyleBaseline | None = None`
- `pacing_templates: list[dict] = Field(default_factory=list)`
- `sensory_templates: list[dict] = Field(default_factory=list)`

`_build_genre_rules()` 更新：使用 `model_dump()` 将 Pydantic 模型转换为 dict 传递。

### 4. fatigue_words 扩充

基于基线报告 `orbital_horror_ch2_ch11_assessment.md` 的 7 类重复短语，为全部 7 个 genre 补充覆盖：

| 模式 | 代表词 |
|------|--------|
| 盯着.*看 | 盯着看、死死盯着、目不转睛地看着 |
| 低声说 | 低声说、低声说道 |
| [僵停]住了 | 僵住了、停住了 |
| 呼吸停[滞了] | 呼吸停滞、呼吸一滞 |
| 呼吸[一]?停 | 呼吸一停 |
| 自言自语 | 自言自语 |
| 喃喃自语 | 喃喃自语 |

扩充后数量：

| Genre | 扩充前 | 扩充后 |
|-------|--------|--------|
| scifi | 10 | 22 |
| urban | 10 | 22 |
| urban_fantasy | 15 | 25 |
| post_apocalyptic | 15 | 25 |
| mystery_noir | 12 | 24 |
| wuxia | 15 | 26 |
| xuanhuan | 30 | 40 |

---

## 测试

新增 `tests/test_writer_style_injection.py`（12 个测试）：

**Prompt 渲染测试 (10)**:
- style_baseline 渲染 / 不渲染
- style_samples 渲染 / 不渲染
- pacing_template 匹配章节类型 / fallback / 不渲染
- sensory_focus 渲染 / 不渲染
- scifi 覆盖 7 类疲劳词模式
- 全部 genre 疲劳词 ≥ 10 个

**集成测试 (2)**:
- scifi vs xuanhuan prompt 差异验证（"错落有致" vs "短促有力"）

现有测试更新：
- `test_prompt_loader.py`: writer 版本数 5→6，默认版本 1.0.4→1.0.5

---

## 验证结果

```
tests/test_writer_style_injection.py  — 12 passed
tests/test_writer.py                   — 38 passed
tests/test_prompt_loader.py            — 10 passed
tests/genres/                          — 142 passed
合计: 210 passed
```

ruff: 0 errors

---

## 向后兼容

- `assemble_context_package()` 新增可选参数 `style_samples=None`
- `_render_prompt()` 新增变量均为可选（None/空列表时不渲染）
- prompt loader manifest 默认版本自动升级到 1.0.5
- `GenreRules` 新增字段均有默认值，不影响旧配置加载

---

## Stage B 总结

| Task | 内容 | 新增测试 |
|------|------|---------|
| 035 | GenreProfile 模型升级 | 52 |
| 036 | 新 Genre 配置（4+1） | 43 |
| 037 | 风格模仿引擎 | 17 |
| 038 | Writer Prompt 风格注入 | 12 |
| **合计** | | **124** |

---

## 下一步

**Stage C** — 长程架构调研（Task 039~042）
