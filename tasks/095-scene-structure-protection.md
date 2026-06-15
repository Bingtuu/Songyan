# Task 095: 场景结构保护 + RevisionHandler 增强

> **Phase**: V4.0 Phase B — 修复
> **优先级**: P2
> **依赖**: Task 092（Writer 场景预算已就位）
> **预计工作量**: 中（3 天）

---

## Goal

修复场景结构退化问题：截断时不破坏场景完整性，RevisionHandler 增加"场景合并/拆分"能力。

---

## Context

### 当前问题（Task 091 确认）

| 问题 | 出现章节 | 根因 |
|------|---------|------|
| 单场景章节 | Ch63（初稿 1 场景）、Ch65（初稿 1 场景） | Writer 在上下文过载时倾向"塞进一个场景" |
| 截断后只剩 1 场景 | Ch62（rewrite 截断后 2646 字，1 场景） | `truncated_before_scene_2` 保留 Scene 1，砍掉其余 |
| RevisionHandler 不处理场景数 | 多处 | `segmented_not_enough_scenes` 只报警，不修复 |

**核心矛盾**：
```
Writer 写出 5607 字（3 场景）
    ↓
RuleAuditor：超标！需要截断
    ↓
截断逻辑：从 Scene 3 开始砍，砍到 Scene 2 边界 = 2646 字（1 场景）
    ↓
RuleAuditor：scene_count=1 < min=2，不达标
    ↓
RevisionHandler：只能 patch 段落，不能"创造 Scene 2"
```

---

## In Scope（必须完成）

### 1. 截断时保留最小场景数

修改 `src/songyan/agents/writer.py` 中的截断逻辑：

```python
# 当前
if word_count > max_limit:
    truncated = truncate_before_scene_boundary(content, target=max_limit)
    # 可能只剩 1 个场景

# 修复后
if word_count > max_limit:
    truncated = truncate_before_scene_boundary(
        content, 
        target=max_limit,
        min_scenes=2,           # 新增：至少保留 2 个场景
        scene_splitter=split_by_scene_markers  # 新增：使用场景标记拆分
    )
    # 如果截断后只剩 1 场景，不截断，直接触发 rewrite
    if count_scenes(truncated) < 2:
        logger.warning("truncation_would_destroy_structure")
        return None  # 不返回截断版本，触发 rewrite
```

### 2. Rewrite 时增加"场景拆分"策略

当前 rewrite 只注入字数约束：
```
"字数控制在 2400-4000 之间"
```

修改后 rewrite prompt 增加场景结构约束：
```
"字数控制在 2400-4000 之间"
"必须包含至少 2 个场景，推荐 3 个"
"每个场景字数不得超过总字数的 60%"
```

### 3. RevisionHandler 场景级修复

修改 `src/songyan/agents/revision_handler.py`：

**新增：场景拆分模式**（当 `scenes_count < 2` 时触发）
```python
class RevisionHandler:
    async def handle_scene_shortage(self, content: str, target_scenes: int) -> str:
        """当场景数不足时，将长场景拆分为多个场景."""
        # 1. 识别场景内的情节转折点
        # 2. 在转折点处插入场景分隔标记
        # 3. 为每个新场景生成过渡句
        ...
```

**新增：场景合并模式**（当字数严重超标时触发）
```python
    async def handle_scene_overflow(self, content: str, target_words: int) -> str:
        """当字数严重超标且无法截断时，合并次要场景."""
        # 1. 识别主要场景和次要场景
        # 2. 将次要场景压缩为过渡段落
        # 3. 保留主要场景的完整性
        ...
```

**触发条件**：
```python
if scenes_count < 2:
    strategy = "scene_split"
elif word_count > target * 1.4 and scenes_count > 3:
    strategy = "scene_merge"
else:
    strategy = "segmented_patch"  # 现有逻辑
```

### 4. RuleAuditor 场景数检查增强

修改 `src/songyan/agents/rule_auditor.py`：

```python
# 当前：scene_count 只有布尔检查
scenes_ok = scenes_count >= min_expected

# 修复后：增加警告级别
if scenes_count == 1:
    issues.append(Issue(
        severity="major",
        category="structure",
        description="章节仅有 1 个场景，叙事节奏可能过于集中",
        fix_suggestion="考虑将章节拆分为 2-3 个场景，增加叙事层次"
    ))
elif scenes_count >= 5:
    issues.append(Issue(
        severity="minor",
        category="structure",
        description="章节场景数过多（>5），可能导致碎片化"
    ))
```

---

## Out of Scope（明确不做）

- 修改 Writer 的场景预算逻辑（Task 092 负责）
- 修改 GoalPlanner
- 修改 SettlementExtractor

---

## 接口契约

### Writer 截断函数签名变更

```python
# src/songyan/agents/writer.py

def truncate_content(
    content: str,
    target_word_count: int,
    min_scenes: int = 2,           # 新增
    max_scene_ratio: float = 0.6,  # 新增：单场景不超过总字数 60%
) -> str | None:
    """
    截断内容到目标字数。
    
    Returns:
        str: 截断后的内容（满足 min_scenes）
        None: 截断会破坏结构（场景数 < min_scenes），应触发 rewrite
    """
```

### RevisionHandler 策略枚举

```python
class RevisionStrategy(str, Enum):
    SEGMENTED_PATCH = "segmented_patch"   # 现有：逐段 patch
    SCENE_SPLIT = "scene_split"           # 新增：场景拆分
    SCENE_MERGE = "scene_merge"           # 新增：场景合并
    REWRITE = "rewrite"                   # 现有：整章重写
```

---

## 测试要求

### Layer 2: 模块测试
- [ ] 截断 3 场景内容到目标字数，保留 ≥2 场景
- [ ] 截断后只剩 1 场景时返回 None
- [ ] 场景拆分：将 1 个 3000 字场景拆分为 2 个场景（每个有独立开头和结尾）
- [ ] 场景合并：将 5 个短场景合并为 3 个

### Layer 3: 集成测试
- [ ] Ch1-Ch5 端到端：单场景章节出现率 **< 5%**
- [ ] Ch1-Ch5 端到端：平均场景数 **≥ 2.5**
- [ ] Ch1-Ch5 端到端：`segmented_not_enough_scenes` 触发率 **< 10%**
- [ ] `pytest -x -q` 全量通过

---

## 验收标准（Acceptance Criteria）

- [ ] Writer 截断保留 `min_scenes=2`，截断后 < 2 场景时返回 None
- [ ] Rewrite prompt 增加"至少 2 个场景"约束
- [ ] RevisionHandler 支持 `scene_split` 和 `scene_merge` 策略
- [ ] RuleAuditor 对单场景章节标记 major issue
- [ ] Ch1-Ch10 端到端：单场景章节 **< 2 章**
- [ ] Ch1-Ch10 端到端：平均场景数 **≥ 2.3**
- [ ] `pytest -x -q` 全部通过
- [ ] 生成了 `tasks/095-scene-structure-protection-DONE.md`

---

## 参考

- `src/songyan/agents/writer.py`
- `src/songyan/agents/revision_handler.py`
- `src/songyan/agents/rule_auditor.py`
