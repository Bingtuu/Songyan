# Task 036: 5 个新 Genre 配置 + xuanhuan 增强

> **Phase**: Stage B — Phase 5（Genre 框架增强）
> **优先级**: P0
> **依赖**: Task 035（GenreProfile 模型升级）
> **预计工作量**: 中（内容工作为主）

---

## Goal

将 Genre 覆盖面从 3 个扩展到 8 个（含增强），使系统支持多种类型小说的差异化生成。每个新配置使用 B1 的完整模型。

## Context

Task 035 完成 GenreProfile 模型升级后，需要填充实际的 Genre 配置。新增配置涵盖：都市异能、末世生存、悬疑 noir、武侠；同时增强玄幻配置（修炼体系 + 爽点模板 + 境界系统）。

## In Scope

- [ ] 新增 `genres/urban_fantasy.json`（都市异能）：
  - 现代背景 + 超自然元素
  - pacing_templates：日常伪装章 / 异能觉醒章 / 势力冲突章
  - sensory_templates：城市感官（霓虹、地铁、雨夜）
  - emotion_arc_library：觉醒弧线 / 身份撕裂弧线 / 复仇弧线
  - style_baseline：对话占比 40%，描写密度 0.3，内心独白丰富
- [ ] 新增 `genres/post_apocalyptic.json`（末世生存）：
  - 资源稀缺 + 人性考验
  - pacing_templates：资源搜寻章 / 阵营冲突章 / 人性抉择章
  - sensory_templates：废墟感官（锈蚀、腐烂、寂静）
  - emotion_arc_library：绝望→希望 / 信任→背叛 / 牺牲→传承
  - style_baseline：短句为主，描写密度 0.4，对话克制
- [ ] 新增 `genres/mystery_noir.json`（悬疑 noir）：
  - 信息差 + 不可靠叙述
  - pacing_templates：线索搜集章 / 误导反转章 / 真相揭露章
  - sensory_templates：暗影感官（雨、霓虹反光、烟味）
  - emotion_arc_library：好奇→困惑→震惊 / 怀疑→确信→幻灭
  - style_baseline：错落有致，描写密度 0.35，对话占比 35%
- [ ] 新增 `genres/wuxia.json`（武侠）：
  - 江湖规则 + 门派体系
  - pacing_templates：门派日常章 / 江湖恩怨章 / 武学突破章
  - sensory_templates：古风感官（竹、酒、 blood）
  - emotion_arc_library：侠义弧线 / 恩怨弧线 / 传承弧线
  - style_baseline：短促有力，描写密度 0.3，对话占比 30%
- [ ] 增强 `genres/xuanhuan.json`：
  - 新增完整 `pacing_templates`（突破章 / 夺宝章 / 宗门冲突章 / 过渡章）
  - 新增 `emotion_arc_library`（升级爽点弧线 / 绝境逆袭弧线 / 师徒传承弧线）
  - 新增 `style_baseline`（对话占比 25%，描写密度 0.35，内心独白克制）
  - 新增 `sensory_templates`（灵气感知、战斗痛觉、丹药味觉）
  - 保留并扩展 `fatigue_words`（新增 10 个玄幻疲劳词）
- [ ] 每个配置包含完整字段：pacing_templates / punch_type_defs / sensory_templates / emotion_arc_library / style_baseline / reference_works

## Out of Scope

- 不修改 scifi.json / urban.json 的核心结构（仅迁移 pacing_rule → pacing_templates）
- 不引入 LLM 自动生成配置内容（用 LLM 生成草案后人工审阅）
- 不修改 GenreLoader 逻辑（B1 已完成）

## 测试要求

### Layer 1: 模型测试
- [ ] 5 个新配置可被 `GenreLoader` 加载
- [ ] Pydantic 验证通过，无缺失必填字段

### Layer 2: 模块测试
- [ ] 每个新配置的 `pacing_templates` 非空
- [ ] 每个新配置的 `style_baseline` 完整
- [ ] `xuanhuan.json` 增强后 `fatigue_words` >= 25 个

### Layer 3: 集成测试
- [ ] 8 个配置（3 旧 + 4 新 + 1 增强）同时加载不冲突
- [ ] `list_genre_profiles()` 返回 8 个 genre_id

## 验收标准

- [ ] 5 个配置能被 `GenreLoader` 加载
- [ ] Pydantic 验证通过，无缺失必填字段
- [ ] 与现有 scifi/urban/xuanhuan 不冲突
- [ ] 所有现有测试继续通过
- [ ] 更新了 `docs/STATUS.md`
- [ ] 生成了 `tasks/036-new-genre-configs-DONE.md`

## 参考

- `docs/architecture/roadmap_v2_phases.md` — Phase 5.2
- `genres/scifi.json` — 参考模板
- `genres/xuanhuan.json` — 增强目标
- `src/songyan/genres/loader.py`
