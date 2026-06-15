# Task 036 DONE 报告：5 个新 Genre 配置 + xuanhuan 增强

> **完成日期**: 2026-06-02
> **执行人**: Kimi Code CLI
> **任务**: Task 036 — 新 Genre 配置（Stage B Phase 5.2）

---

## 交付摘要

将 Genre 覆盖面从 3 个扩展到 7 个（4 新增 + 1 增强 + 2 不变），每个配置均使用 Task 035 建立的完整模型结构。

---

## 新增配置

### 1. `genres/urban_fantasy.json` — 都市异能

| 维度 | 内容 |
|------|------|
| chapter_types | opening, daily_disguise, awakening, faction_conflict, power_training, transition |
| punch_density | 0.8 / 2.0 / 2.5（三段式）|
| style_baseline | 短促有力，描写 30%，对话 40%，独白丰富，POV 深 |
| sensory | visual(霓虹) / auditory(地铁) / tactile(雨夜) |
| emotion_arc | 异能觉醒 / 身份撕裂 / 复仇 |
| reference_works | 龙族、全职法师、一世之尊 |

### 2. `genres/post_apocalyptic.json` — 末世生存

| 维度 | 内容 |
|------|------|
| chapter_types | opening, scavenging, faction_conflict, survival, base_building, transition |
| punch_density | 1.0 / 2.0 / 1.5 |
| style_baseline | 短促有力，描写 40%，对话 25%，独白克制，POV 中 |
| sensory | visual(锈蚀) / olfactory(腐烂) / auditory(寂静) |
| emotion_arc | 绝望→希望 / 信任→背叛 / 牺牲→传承 |
| reference_works | 生化危机、流浪地球、末日乐园 |

### 3. `genres/mystery_noir.json` — 悬疑 noir

| 维度 | 内容 |
|------|------|
| chapter_types | opening, clue_gathering, red_herring, confrontation, revelation, transition |
| punch_density | 1.0 / 1.8 / 2.5 |
| style_baseline | 错落有致，描写 35%，对话 35%，独白丰富，POV 深 |
| sensory | visual(暗影) / olfactory(烟味) / tactile(雨水) |
| emotion_arc | 好奇→震惊 / 怀疑→幻灭 / 迷雾→顿悟 |
| reference_works | 白夜行、漫长的告别、福尔摩斯探案集 |

### 4. `genres/wuxia.json` — 武侠

| 维度 | 内容 |
|------|------|
| chapter_types | opening, sect_daily, jianghu_conflict, martial_breakthrough, duel, transition |
| punch_density | 0.6 / 2.0 / 1.5 |
| style_baseline | 短促有力，描写 30%，对话 30%，独白克制，POV 中 |
| sensory | visual(竹林) / gustatory(酒) / pain(血/伤) |
| emotion_arc | 侠义 / 恩怨 / 传承 |
| reference_works | 射雕英雄传、笑傲江湖、陆小凤传奇 |

---

## xuanhuan.json 增强

| 维度 | 变更前 | 变更后 |
|------|--------|--------|
| pacing_templates | 1 个（通用） | 4 个（突破/夺宝/宗门/过渡） |
| emotion_arc_library | 升级突破 / 生死搏杀 / 夺宝探险 | 升级爽点 / 绝境逆袭 / 师徒传承 |
| style_baseline.density | 0.30 | 0.35 |
| sensory_templates | visual / pain / proprioception | proprioception(灵气) / pain(战斗) / gustatory(丹药) |
| fatigue_words | 20 个 | 30 个（新增 10 个） |

---

## 测试

新增 `tests/genres/test_new_genre_configs.py`（43 个测试）：

**Layer 1 — 基础验证 (12)**:
- 4 个新 genre × 3 项（JSON 有效、可实例化、id 匹配文件名、必填字段存在）

**Layer 2 — 完整度验证 (19)**:
- 4 个新 genre × 7 项（pacing_templates 非空、style_baseline 完整、sensory≥3、emotion_arc≥3、reference_works≥1、punch_density 范围、density_sum 有效）
- xuanhuan 增强 6 项（fatigue_words≥25、pacing_templates=4、arcs 包含 4 个类型、style_baseline 更新、sensory 更新、emotion_arc 更新）

**Layer 3 — 集成验证 (6)**:
- list_genre_profiles() 返回 7 个
- 全部 7 个同时加载无冲突
- 每个 genre 的 style_baseline density+ratio ≤ 1.0
- GenreProfileLoader.list_genres() 正确
- xuanhuan 的 max punch_density 为所有 genre 中最高

现有测试更新：
- `test_loader.py`: list 断言从 3 个更新为 7 个
- `test_genre_profile_upgrade.py`: xuanhuan pacing_templates 数量断言放宽

---

## 验证结果

```
tests/genres/test_new_genre_configs.py      — 43 passed
tests/genres/test_genre_profile_upgrade.py  — 45 passed
tests/genres/test_loader.py                 — 36 passed
合计 genres: 142 passed
```

ruff: 0 errors

---

## 已知限制

- `punch_type_defs` 和 `sub_genres` 在所有配置中仍为空列表（B3/B4 视需求填充）
- 新 genre 的 `active_audit_dimensions` 未针对 genre 特点做差异化（全部使用通用维度）
- `has_power_scaling` 对 urban_fantasy 和 wuxia 设为 true，但具体 power 体系仍需项目层定义

---

## 下一步

**Task 037** — 风格模仿引擎（激活 reference_works，提取风格样本注入 ContextPackage.soft_references）
