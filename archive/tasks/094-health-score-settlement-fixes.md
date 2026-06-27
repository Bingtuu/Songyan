# Task 094: Health Score 公式修正 + Settlement 去重修复

> **Phase**: V4.0 Phase B — 修复
> **优先级**: P1
> **依赖**: Task 091（验证数据确认问题）
> **预计工作量**: 中（3 天）

---

## Goal

修复两个独立但相关的问题：
1. **Health Score 虚假低迷**：ContinuityAuditor 的评分公式对长篇小说不公平，将一次性背景 setting 标记为缺陷
2. **Settlement 提取质量退化**：重复 setting key 和 character ID 不匹配

---

## Context

### Health Score 问题（Task 091 确认）

| 指标 | 数值 | 根因 |
|------|------|------|
| 平均 health_score | 2.0（目标 ≥3.0） | orphaned settings 公式性压低 |
| Ch60 orphaned | 317 | 10 章窗口内未引用的 setting |
| Ch70 active settings | 91 | 其中估计只有 20-30 个是"需要持续追踪"的 |

**问题本质**：
```
当前公式：health_score = 10 - orphaned_count * penalty

缺陷：
- "联邦星舰跃迁引擎型号"（一次性背景）= 未引用 = 严重扣分
- "主角的常数锚能力"（核心设定）= 未引用 = 同样扣分
- 长篇小说中 60-70% 的 setting 是背景铺垫，天然不会反复引用
```

### Settlement 问题（Task 091 确认）

| 问题 | 出现章节 | 影响 |
|------|---------|------|
| 重复 setting key | Ch62 (`technology.emergency_jump_drive.description`) | `needs_human_review` |
| Character ID 不匹配 | Ch70 (`char_001` vs `char_jiang_ran`) | 角色状态未更新 |
| Setting key 冲突 | 随着总量增长增加 | 结算失败率上升 |

---

## In Scope（必须完成）

### 1. Setting 分类标签体系

在 `src/songyan/models/settings.py` 中增加 `setting_category`：

```python
class SettingCategory(str, Enum):
    CRITICAL = "critical"       # 核心设定：主角能力、主线道具、世界观基石
    RECURRING = "recurring"     # 反复出现：重要地点、组织、角色关系
    BACKGROUND = "background"   # 一次性背景：某艘飞船型号、某个NPC名字
    TECHNICAL = "technical"     # 技术细节：引擎参数、科学原理解释
    HISTORICAL = "historical"   # 历史设定：过去事件、年代背景
```

**分类规则**（SettlementExtractor 自动打标）：
- 与主角直接相关 → `critical`
- 在 3+ 章中被引用 → `recurring`
- 纯技术参数/型号 → `technical`
- 其余 → `background`

### 2. Health Score 公式修正

修改 `src/songyan/agents/continuity_auditor.py`：

```python
# 当前（问题）
health_score = max(0, 10 - orphaned_count * 0.5)

# 修复后
health_score = max(0, 10 - (
    orphaned_critical * 2.0 +    # 核心设定未引用：严重
    orphaned_recurring * 1.0 +   # 反复设定未引用：中等
    orphaned_background * 0.1 +  # 背景设定未引用：几乎忽略
    orphaned_technical * 0.05 +  # 技术设定未引用：忽略
    overdue_foreshadowings * 1.0 # 逾期未回收伏笔：中等
))
```

**阈值调整**：
- `threshold=7.0`（不变）
- 但 health_score < 3.0 才触发 warning（当前是 < 7.0）

### 3. SettlementExtractor Setting Key 去重

在 `src/songyan/agents/settlement_extractor.py` 中：

**当前流程**（有问题）：
```
LLM 提取 new_settings → 直接 INSERT
                    ↓ 如果 key 冲突 → SQL 报错 → needs_human_review
```

**修复后流程**：
```
LLM 提取 new_settings → 代码层去重（按 setting_key）
                    → 查询 DB 是否已存在
                    → 存在：SKIP（不插入）
                    → 不存在：INSERT
                    → 所有 INSERT 成功后 → validation_passed
```

```python
# 新增去重逻辑（SettlementExtractor 内部）
existing_keys = await repo.get_setting_keys(project_id)
new_settings = [s for s in llm_output.new_settings 
                if s.setting_key not in existing_keys]
duplicates = [s for s in llm_output.new_settings 
              if s.setting_key in existing_keys]
if duplicates:
    logger.info(f"Skipped {len(duplicates)} duplicate settings")
```

### 4. Character ID 标准化

在 `src/songyan/agents/settlement_extractor.py` 中：

```python
# 新增 ID 映射层
CHARACTER_ALIASES = {
    # Settlement 可能返回的 ID → DB canonical ID
    "char_001": "char_jiang_ran",
    "char_002": "char_lin_yuan",
    "char_jr": "char_jiang_ran",
    "char_ly": "char_lin_yuan",
    "jiang_ran": "char_jiang_ran",
    "lin_yuan": "char_lin_yuan",
}

# 规范化流程
canonical_id = CHARACTER_ALIASES.get(
    raw_character_id, 
    raw_character_id  # 未匹配的保持原样
)
```

**长期方案**：在数据库 `characters` 表中增加 `aliases` 字段（JSON 数组），由 SettlementExtractor 查询匹配。

### 5. 增加 Settlement 校验覆盖率

当前仅校验 `setting_key` 唯一性，增加：
- `source_quote` 必须在正文中存在（已有，但阈值过宽）
- `new_setting.setting_key` 格式校验（`category.subcategory.name`）
- `foreshadowing.target_chapter` 必须在当前章节之后

---

## Out of Scope（明确不做）

- 修改 Writer / GoalPlanner / RevisionHandler（Task 092/094 负责）
- 修改 ContextManager
- 废弃现有的 continuity_auditor 评分逻辑（保留兼容，新逻辑通过配置开关切换）

---

## 接口契约

### SettingSnapshot 模型扩展

```python
class SettingSnapshot(BaseModel):
    """扩展示例（向后兼容，category 默认为 background）."""
    setting_id: str
    project_id: str
    chapter_number: int
    setting_key: str
    setting_name: str
    description: str
    source_quote: str
    category: SettingCategory = SettingCategory.BACKGROUND  # 新增
    created_at: datetime
```

### ContinuityAuditor 输出扩展

```python
class ContinuityReport(BaseModel):
    report_id: str
    version_id: str
    health_score: float
    orphaned_count: int
    orphaned_critical: int   # 新增
    orphaned_recurring: int  # 新增
    orphaned_background: int # 新增
    orphaned_technical: int  # 新增
    overdue_foreshadowings: int
    constraints: list[ContinuityConstraint]
```

---

## 测试要求

### Layer 2: 模块测试
- [ ] Setting 分类器正确分类 `critical` / `recurring` / `background`
- [ ] Health Score 公式：10 个 background orphaned = 扣分 1.0；10 个 critical orphaned = 扣分 20.0
- [ ] Settlement 去重：重复 key 被 SKIP，不报错
- [ ] Character ID 映射：`char_001` → `char_jiang_ran`

### Layer 3: 集成测试
- [ ] Ch1-Ch5 端到端跑通，health_score **≥ 4.0**（当前 2.0）
- [ ] Settlement 无 `needs_human_review`（当前 ~5%）
- [ ] `pytest -x -q` 全量通过

### 数据迁移
- [ ] 现有 `setting_snapshots` 表的 `category` 字段回填（默认 `background`）
- [ ] 迁移脚本可重复执行

---

## 验收标准（Acceptance Criteria）

- [ ] `setting_snapshots` 表增加 `category` 字段，已有数据回填
- [ ] ContinuityAuditor 使用新评分公式，health_score **≥ 4.0**（Ch1-Ch10）
- [ ] SettlementExtractor 代码层去重，无重复 key 报错
- [ ] Character ID 标准化映射生效
- [ ] Ch1-Ch10 端到端：Settlement 失败率 **< 2%**
- [ ] `pytest -x -q` 全部通过
- [ ] 生成了 `tasks/094-health-score-settlement-fixes-DONE.md`

---

## 参考

- `evals/output/task_091_scifi_webnovel/report.md` — Task 091 验证数据
- `src/songyan/agents/continuity_auditor.py`
- `src/songyan/agents/settlement_extractor.py`
- `src/songyan/models/settings.py`
