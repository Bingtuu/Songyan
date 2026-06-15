# Task 094: Health Score 公式修正 + Settlement 去重 — 交接报告

> **状态**: ✅ 已完成
> **完成日期**: 2026-06-09
> **耗时**: ~2 小时
> **提交**: `TODO`

---

## 做了什么

### 1. Health Score 公式修正

**问题**: ContinuityAuditor 的评分公式对长篇小说不公平，所有 orphaned setting 同等扣分（0.5），导致一次性背景设定大量压低分数。

**修复**（`src/songyan/agents/continuity_auditor/__init__.py`）：

| 分类 | 权重 | 说明 |
|------|------|------|
| critical | 2.0 | 核心设定未引用：严重 |
| recurring | 1.0 | 反复设定未引用：中等 |
| background | 0.1 | 背景设定未引用：几乎忽略 |
| technical | 0.05 | 技术设定未引用：忽略 |
| historical | 0.05 | 历史设定未引用：忽略 |

**效果**: 10 个 background orphaned 仅扣分 1.0（原 5.0），critical 仍保持严格。

### 2. Setting 分类体系

**数据库**（`src/songyan/db/schema.sql` + `migrations.py`）：
- `setting_tracking` 表增加 `category` 字段（CHECK: critical/recurring/background/technical/historical）
- 迁移脚本 `_migrate_setting_category` 回填现有数据为 `background`

**自动分类**（`src/songyan/agents/settlement_extractor/_apply.py`）：
- 新增 `_infer_setting_category()` 函数，根据 setting_key/name/description 中的关键词推断分类
- 技术关键词 → `technical`
- 核心关键词（主角、能力、锚等）→ `critical`
- 历史关键词 → `historical`
- 其余 → `background`

### 3. Settlement 去重

**代码层去重**（`src/songyan/agents/settlement_extractor/__init__.py`）：
- LLM 提取后，查询 DB 现有 setting_key
- 重复 key 被 SKIP，不进入 validation
- 记录 `settlement.duplicates_skipped` 日志

**效果**: 消除 `needs_human_review` 中因重复 key 导致的失败。

### 4. Character ID 标准化

**映射层**（`src/songyan/agents/settlement_extractor/__init__.py`）：
- 新增 `_CHARACTER_ID_ALIASES` 字典 + `register_character_aliases()` 函数
- `_build_character_update()` 中自动映射别名 → 标准 ID
- 长期方案应在 `characters` 表中增加 `aliases` 字段

### 5. Settlement 校验增强

**新增校验**（`src/songyan/agents/settlement_extractor/_validate.py`）：
- `setting_key` 格式校验：必须符合 `category.subcategory.name`（正则 `^[a-z_]+\.[a-z_]+\.[a-z_]+$`）
- `foreshadowing.expected_resolve_chapter` 必须在当前章节之后

---

## 测试

| 测试文件 | 结果 |
|---------|------|
| `tests/test_078_foreshadowing_lifecycle.py` | ✅ 12 passed（更新 Health Score 断言 + 新增分类测试） |
| `tests/test_prompt_loader.py` | ✅ passed（版本数 8→3） |
| `tests/test_settlement_extractor.py` | ✅ passed（更新重复 key 测试 + 新增格式校验测试） |
| **全量 pytest** | **✅ 1424 passed, 6 skipped, 0 failed** |

---

## 文件变更清单

```
src/songyan/db/schema.sql                        # setting_tracking 增加 category 字段
src/songyan/db/migrations.py                     # 新增 _migrate_setting_category 迁移
src/songyan/models/continuity.py                 # OrphanedSetting 增加 category 字段
src/songyan/db/continuity_repo.py                # SettingTrackingRepository.create 支持 category
src/songyan/agents/continuity_auditor/_scanners.py   # 读取 category 字段
src/songyan/agents/continuity_auditor/__init__.py    # Health Score 分类加权公式
src/songyan/agents/settlement_extractor/_apply.py    # 自动分类推断 + category 传入
src/songyan/agents/settlement_extractor/__init__.py  # 代码层去重 + Character ID 映射
src/songyan/agents/settlement_extractor/_validate.py # key 格式校验 + foreshadowing 章节校验
prompts/cards/writer/_manifest.yaml                # 版本描述更新
prompts/cards/writer/1.0.0-1.0.4.yaml             # 已删除（只保留最近3版本）
tests/test_078_foreshadowing_lifecycle.py          # 更新断言 + 新增分类测试
tests/test_prompt_loader.py                        # 版本数 8→3
tests/test_settlement_extractor.py                 # 更新重复 key 测试 + 新增格式测试
docs/STATUS.md                                     # 更新 094 状态
```

---

## 已知限制

1. **分类推断是启发式的**：基于关键词匹配，可能误分类。长期应在 SettlementExtractor craft card 中让 LLM 直接输出分类。
2. **Character ID 映射是硬编码的**：`register_character_aliases()` 需要调用方手动注册，不够自动化。
3. **未做端到端验证**：Task 094 的代码改动已通过 pytest，但未运行 Ch1-Ch10 端到端验证 health_score 是否达到 ≥4.0。

---

## 下一步

- **Task 095**（如果继续 Phase B）：场景结构保护
- **扩展验证**：运行 Ch6-Ch20，观察 health_score 和 settlement 失败率改善
