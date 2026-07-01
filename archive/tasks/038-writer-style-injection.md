# Task 038: Writer Prompt 风格注入 + fatigue_words 扩充

> **Phase**: Stage B — Phase 5（Genre 框架增强）
> **优先级**: P0
> **依赖**: Task 036（新 Genre 配置）、Task 037（Style Mimicry Engine）
> **预计工作量**: 小

---

## Goal

将 Genre 模型升级和风格引擎的输出注入 Writer Prompt，并基于基线数据扩充疲劳词库，使 Writer 能根据 Genre 自动调整写作风格。

## Context

B1~B3 完成了 Genre 模型升级、新配置和风格引擎。B4 是最后一环：将 Genre 的 `style_baseline`、StyleSample 的 `analysis`、`pacing_templates` 的条件渲染注入 Writer Prompt，并扩充 `fatigue_words`。

## In Scope

- [ ] **Writer Prompt 新增"风格参考"分区**：
  - `{% if genre_style_baseline %}`: 句式节奏目标、描写密度目标、对话占比目标、内心独白目标、视角深度目标
  - `{% if style_samples %}`: 参考作品风格特征摘要（excerpt + analysis）
  - `{% if pacing_template %}`: 当前章节类型对应的 pacing 模板（emotion_arc / punch_density / info_release_strategy）
  - `{% if sensory_templates %}`: 当前 Genre 的感官描写侧重
  - 条件渲染：仅当字段非空时显示
- [ ] **Writer `_render_prompt()` 更新**：
  - 从 `ctx.genre_rules` 提取 `style_baseline` 相关字段
  - 从 `ctx.soft_references` 提取 type="style_sample" 的参考
  - 从 `ctx.creative_brief` 或 `ctx.mode_rules` 确定当前 pacing_template
  - 传入 prompt 变量
- [ ] **fatigue_words 扩充**：
  - 基于基线报告 `docs/review/orbital_horror_ch2_ch11_assessment.md` 的 7 类重复短语：
    - `盯着.*看`、`低声说`、`[僵停]住了`、`呼吸停[滞了]`、`呼吸[一]?停`、`自言自语`、`喃喃自语`
  - 为每个新 Genre 配置（urban_fantasy / post_apocalyptic / mystery_noir / wuxia）添加 10 个疲劳词
  - `scifi.json` 疲劳词从 10 个扩充到包含上述 7 类模式
- [ ] **跨 genre 验证脚本**（可选，如时间允许）：
  - 同一 seed 用 3 种 genre 生成 3 章，对比风格差异
  - 输出 `evals/output/cross_genre_comparison.json`

## Out of Scope

- 不修改 Writer 的核心生成逻辑（仅修改 prompt 渲染）
- 不修改 RuleAuditor 的检测逻辑（fatigue_words 已自动生效）
- 不重新训练模型或引入外部风格迁移工具

## 接口契约

```python
# Writer prompt 新增变量
style_baseline: dict | None = None  # 来自 genre_rules.style_baseline
style_samples: list[dict] = []      # 来自 soft_references (type="style_sample")
pacing_template: dict | None = None # 当前章节匹配的 pacing template
sensory_focus: list[str] = []       # 当前 genre 的感官侧重

# _render_prompt 中提取逻辑
def _extract_style_info(ctx: ContextPackage) -> dict:
    """从 ContextPackage 提取风格相关信息."""
    ...
```

## 测试要求

### Layer 1: 模型测试
- [ ] Writer prompt 变量可正确渲染

### Layer 2: 模块测试
- [ ] `_render_prompt()` 在有 `style_baseline` 时包含风格分区
- [ ] `_render_prompt()` 在有 `style_samples` 时包含参考作品分区
- [ ] `_render_prompt()` 在无风格数据时不渲染相关区块
- [ ] scifi.json 的 `fatigue_words` 覆盖基线报告的 7 类重复短语

### Layer 3: 集成测试
- [ ] 加载不同 genre 时 Writer prompt 内容有差异

## 验收标准

- [ ] Writer prompt 渲染包含风格分区（style_baseline / style_samples / pacing_template）
- [ ] `scifi.json` 的 `fatigue_words` 覆盖基线报告中的全部 7 类重复短语
- [ ] 跨 genre 加载时 prompt 内容有可测量差异
- [ ] 所有现有测试继续通过
- [ ] 更新了 `docs/STATUS.md`
- [ ] 生成了 `tasks/038-writer-style-injection-DONE.md`

## 参考

- `docs/review/orbital_horror_ch2_ch11_assessment.md` — 基线疲劳词报告
- `prompts/cards/writer/1.0.4.yaml` — Writer Prompt 模板
- `src/songyan/agents/writer.py`
- `src/songyan/agents/rule_auditor.py`
