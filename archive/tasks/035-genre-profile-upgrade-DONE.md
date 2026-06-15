# Task 035 DONE 报告：GenreProfile 模型升级

> **完成日期**: 2026-06-02
> **执行人**: Kimi Code CLI
> **任务**: Task 035 — GenreProfile 模型升级（Stage B Phase 5.1）

---

## 交付摘要

将 `GenreProfile` 从单字符串配置升级为结构化多维度框架，支撑 Phase 5 风格多样化目标。

---

## 修改清单

### 1. 模型层 (`src/songyan/models/genre.py`)

新增 6 个 Pydantic 模型：

| 模型 | 核心字段 | 验证规则 |
|------|---------|---------|
| `PacingTemplate` | chapter_types, emotion_arc, punch_density, info_release_strategy | punch_density ∈ [0.0, 5.0] |
| `SubGenre` | sub_genre_id, name, parent_genre_id, differentiation_rules | — |
| `PunchTypeDef` | punch_type_id, description, genre_suitability, sensory_requirements | — |
| `SensoryTemplate` | sense(Literal 7 种), intensity_target, description_density, example_phrases | intensity_target ∈ [0.0, 1.0] |
| `EmotionArc` | arc_name, phases, typical_length_words, suitable_chapter_types | typical_length_words ≥ 0 |
| `StyleBaseline` | sentence_rhythm, description_density, dialogue_ratio, inner_monologue, pov_depth | density + ratio ≤ 1.0 |

`GenreProfile` 扩展字段：
- `pacing_templates: list[PacingTemplate]`
- `sub_genres: list[SubGenre]`
- `punch_type_defs: list[PunchTypeDef]`
- `sensory_templates: list[SensoryTemplate]`
- `emotion_arc_library: list[EmotionArc]`
- `style_baseline: StyleBaseline | None`
- `reference_works: list[str]`

向后兼容：
- `pacing_rule: str` 保留（deprecated 标记）
- `model_config = {"extra": "ignore"}` 确保旧 JSON 加载不报错
- 所有新字段均有 `default_factory=list` 或 `None` 默认值

### 2. 配置文件迁移

3 个 Genre JSON 均新增：

| Genre | punch_density | style_baseline 特点 | sensory 侧重 | reference_works |
|-------|--------------|---------------------|-------------|-----------------|
| scifi | 1.2 | 错落有致，克制独白 | visual / auditory / tactile | 三体、银河帝国 |
| urban | 1.5 | 短促有力，丰富独白 | visual / auditory / olfactory | 全职高手、大医凌然 |
| xuanhuan | 2.5 | 短促有力，克制独白 | visual / pain / proprioception | 斗破苍穹、凡人修仙传 |

每个配置包含：1 个 pacing_template + 1 个 style_baseline + 3 个 sensory_templates + 3 个 emotion_arc + reference_works。

### 3. 导出更新 (`src/songyan/models/__init__.py`)

`__init__.py` 新增导出 6 个新模型。

### 4. 测试 (`tests/genres/test_genre_profile_upgrade.py`)

52 个新测试，覆盖三层：

**Layer 1 — 模型测试 (20)**:
- PacingTemplate: 实例化、边界值、punch_density 范围
- StyleBaseline: density+ratio 验证、越界检测
- SensoryTemplate: 合法/非法 sense 值
- EmotionArc / SubGenre / PunchTypeDef: 基础实例化
- GenreProfile: 旧 dict 向后兼容、完整 dict 全字段加载

**Layer 2 — Loader 测试 (15)**:
- 3 个 genre × 5 项验证（加载成功、punch_density 有效、style_baseline 有效、sensory≥3、emotion_arc≥3、reference_works≥1）
- pacing_rule 保留验证、migrated 验证

**Layer 3 — 集成测试 (5)**:
- 旧配置 → 新字段默认值
- 迁移后配置 → 新字段有有效数据
- GenreProfileLoader 类封装
- xuanhuan punch_density > urban > scifi

---

## 测试验证

```
tests/genres/test_genre_profile_upgrade.py  — 52 passed
tests/genres/test_loader.py               — 47 passed
tests/models/test_batch1_foundation.py    —  8 passed
tests/test_validation_gapfill.py          — 12 passed
tests/test_layered_context.py             — 19 passed
合计 genres + models 相关: 99 passed
```

ruff: 0 errors（genre.py / test_genre_profile_upgrade.py）

---

## 向后兼容声明

- 旧 `pacing_rule` 字符串保留在 JSON 中，Python 模型字段保留
- `extra="ignore"` 确保未来新增字段不会导致旧代码崩溃
- `GenreLoader` 逻辑未变，仅依赖 `GenreProfile.from_dict()`

---

## 已知限制

- `punch_type_defs` 和 `sub_genres` 在 JSON 中为空列表（本 Task 只搭建模型，B2 填充内容）
- `StyleBaseline` 的验证为静态约束，实际写作风格仍需 Writer 层面配合（B4）
- `reference_works` 尚未被风格模仿引擎消费（B3）

---

## 下一步

**Task 036** — 新 Genre 配置（urban_fantasy / post_apocalyptic / mystery_noir / wuxia），复用本 Task 建立的模型框架。
