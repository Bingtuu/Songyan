# Task 035: GenreProfile 模型升级

> **Phase**: Stage B — Phase 5（Genre 框架增强）
> **优先级**: P0
> **依赖**: Task 034（遗留验证补齐）
> **预计工作量**: 中

---

## Goal

将 Genre 配置从"单字符串"升级为结构化多维度框架，支撑风格多样化。`pacing_rule` 从 `str` 扩展为 `list[PacingTemplate]`，新增子类型、感官模板、情感弧线库、风格基线等维度。

## Context

当前 `GenreProfile` 的 `pacing_rule` 是单字符串（如 scifi 的"科技揭示与叙事推进交替进行..."），无法支撑多风格差异化生成。Phase 5 需要让系统能根据 Genre 自动调整：章节类型分布、情感弧线模板、刺激点密度策略、感官描写侧重、句式节奏目标。

## In Scope

- [ ] **Pydantic 模型扩展**：
  - 新增 `PacingTemplate`：`chapter_types` / `emotion_arc` / `punch_density` / `info_release_strategy`
  - 新增 `SubGenre`：`sub_genre_id` / `name` / `parent_genre_id` / `differentiation_rules`
  - 新增 `PunchTypeDef`：`punch_type_id` / `description` / `genre_suitability` / `sensory_requirements`
  - 新增 `SensoryTemplate`：`sense` / `intensity_target` / `description_density` / `example_phrases`
  - 新增 `EmotionArc`：`arc_name` / `phases`（list of `from→to`）/ `typical_length_words` / `suitable_chapter_types`
  - 新增 `StyleBaseline`：`sentence_rhythm` / `description_density` / `dialogue_ratio` / `inner_monologue` / `pov_depth`
  - `GenreProfile` 扩展：`pacing_templates` / `sub_genres` / `punch_type_defs` / `sensory_templates` / `emotion_arc_library` / `style_baseline` / `reference_works`
- [ ] `pacing_rule` 保留但标记为 deprecated（向后兼容）
- [ ] `GenreLoader` 更新：加载新字段，验证 `active_audit_dimensions` 保持不变
- [ ] `genres/scifi.json` / `genres/xuanhuan.json` / `genres/urban.json` 迁移：
  - `pacing_rule` 字符串 → 单元素 `pacing_templates` 列表
  - 新增基础 `style_baseline`（基于现有 writer_rules 推断）
  - 新增基础 `sensory_templates`（3 个感官类型）
  - 新增基础 `emotion_arc_library`（3 条情感弧线）
- [ ] 向后兼容：旧 JSON 加载不报错（`extra="ignore"` 已就位，`pacing_rule` 保留）

## Out of Scope

- 不修改 `GenreProfile` 的 `id` / `name` / `language` 等核心字段
- 不删除 `fatigue_words` / `taboos` / `writer_rules` 等现有字段
- 不在本 Task 中写新的 Genre 配置（B2 负责）
- 不修改 Writer Prompt 注入逻辑（B4 负责）

## 接口契约

```python
class PacingTemplate(BaseModel):
    chapter_types: list[str]
    emotion_arc: str  # 引用 emotion_arc_library 中的 arc_name
    punch_density: float  # 每千字刺激点数
    info_release_strategy: str

class SubGenre(BaseModel):
    sub_genre_id: str
    name: str
    parent_genre_id: str
    differentiation_rules: list[str]

class PunchTypeDef(BaseModel):
    punch_type_id: str
    description: str
    genre_suitability: dict[str, float]  # genre_id -> 0.0~1.0
    sensory_requirements: list[str]

class SensoryTemplate(BaseModel):
    sense: Literal["visual", "auditory", "tactile", "pain", "proprioception", "olfactory", "gustatory"]
    intensity_target: float  # 0.0~1.0
    description_density: float  # 每千字描写字数
    example_phrases: list[str]

class EmotionArc(BaseModel):
    arc_name: str
    phases: list[dict[str, str]]  # [{"from": "紧张", "to": "震惊"}, ...]
    typical_length_words: int
    suitable_chapter_types: list[str]

class StyleBaseline(BaseModel):
    sentence_rhythm: str  # "短促有力" / "绵长舒缓" / "错落有致"
    description_density: float  # 0.0~1.0，描写占全文比例
    dialogue_ratio: float  # 0.0~1.0，对话占全文比例
    inner_monologue: str  # "丰富" / "克制" / "几乎没有"
    pov_depth: str  # "深" / "中" / "浅"

class GenreProfile(BaseModel):
    # ... 现有字段保留 ...
    pacing_rule: str = ""  # deprecated，向后兼容
    pacing_templates: list[PacingTemplate] = Field(default_factory=list)
    sub_genres: list[SubGenre] = Field(default_factory=list)
    punch_type_defs: list[PunchTypeDef] = Field(default_factory=list)
    sensory_templates: list[SensoryTemplate] = Field(default_factory=list)
    emotion_arc_library: list[EmotionArc] = Field(default_factory=list)
    style_baseline: StyleBaseline | None = None
    reference_works: list[str] = Field(default_factory=list)
```

## 测试要求

### Layer 1: 模型测试
- [ ] 新模型可正确实例化
- [ ] 旧 JSON（无新字段）加载不报错
- [ ] 新 JSON（完整字段）加载正确

### Layer 2: 模块测试
- [ ] `GenreLoader` 加载升级后的 scifi.json / xuanhuan.json / urban.json
- [ ] `PacingTemplate` 验证：punch_density 在 0.0~5.0 范围内
- [ ] `StyleBaseline` 验证：description_density + dialogue_ratio <= 1.0

### Layer 3: 集成测试
- [ ] 加载旧配置 → 新字段为默认值
- [ ] 加载迁移后的配置 → 新字段有有效数据

## 验收标准

- [ ] Pydantic 模型通过验证
- [ ] 旧配置加载不报错（`extra="ignore"`）
- [ ] 新配置字段完整，`GenreLoader` 正确解析
- [ ] `scifi.json` / `xuanhuan.json` / `urban.json` 迁移完成
- [ ] 所有现有测试继续通过
- [ ] 更新了 `docs/STATUS.md`
- [ ] 生成了 `tasks/035-genre-profile-upgrade-DONE.md`

## 参考

- `docs/architecture/roadmap_v2_phases.md` — Phase 5.1
- `src/songyan/models/genre.py`
- `src/songyan/genres/loader.py`
- `genres/scifi.json`
