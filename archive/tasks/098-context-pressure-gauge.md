# Task 098：上下文压力计 + Craft Card 措辞回调 + Accept 路径字数守卫

> **Phase**: V4.0 Phase B — 验证完成后的系统优化
> **优先级**: P0
> **依赖**: Task 096 完成（Ch2-Ch50 数据在手）
> **预计工作量**: 中（3-4 天）

---

## Goal

在 Task 096 数据基础上，实施三项系统级优化：
1. **上下文压力计**（四信号系统）— 取代硬编码裁剪阈值
2. **Craft Card 1.0.8 → 1.0.9** — 措辞回调，在"写得好的章节更重要"和"严重超标不可接受"之间找中间点
3. **Accept 路径字数守卫** — 超标 > 1.40x 的章节不在 1 轮修订后通过

---

## Context

### Task 096 的三条关键发现

**1. Craft Card 1.0.8 过冲了。** 删除"系统将拒绝并要求重写"后，Writer 从"不敢超"变成了"随便超"。超标率从 19.1% 翻到 29.8%。需要在两个极端之间找到平衡。

**2. 超标章节与修订轮次强相关。** Ch30 (1.757x, 1r)、Ch17 (1.707x, 1r)、Ch42 (1.601x, 1r) — 最严重的超标都只有 1 轮修订。Accept 路径上没有字数检查。

**3. 后期章节信息密度上升。** Ch02-20 达标率 73.7% → Ch36-50 61.5%。Writer 在后期需要整合更多上下文（角色/设定/伏笔），即使生命周期管理在工作，信息密度仍在增加。需要一个有机的信号来控制上下文供给。

### 历史最佳基线

| 指标 | Task 091 (统一1.20x) | Task 096 (动态容差) | 本次目标 |
|------|-------------------|-------------------|---------|
| 达标率 | 74.5% | 70.2% | > 78% |
| 不足率 | 6.4% | 0% | < 3% |
| 超标率 | 19.1% | 29.8% | < 18% |
| 最大超标 | 1.768x | 1.757x | < 1.50x |
| 平均修订 | 2.8轮 | 2.6轮 | < 2.5轮 |

---

## 方案设计

### 1. 上下文压力计（四信号系统）

**核心思路**：让 CreativeDirector 在每章输出四个信号，ContextManager 用它们做动态裁剪。不再使用硬编码的章节数阈值。

#### 1.1 NarrativeFullness — 叙事充满度

CreativeDirector 已经能感知到所有线索的展开程度，只需加一个结构化的输出：

```yaml
# CreativeDirector craft card 新增输出
narrative_fullness: 0.72  # 0.0 (所有线索未展开) ~ 1.0 (所有线索已展开)
```

ContextManager 用它做动态裁剪：

```python
# ContextManager 新增方法
def _dynamic_fullness_factor(self, fullness: float) -> float:
    """叙事充满度越高，上下文包越紧凑，给 Writer 更多空间"""
    return 1.0 - (fullness * 0.5)  # 0.5 ~ 1.0 范围

# 应用到各上限
MAX_CHARACTER_STATES = round(4 * _dynamic_fullness_factor(0.72))  # 4 → 2.6 → 3
MAX_FORESHADOWING = round(8 * _dynamic_fullness_factor(0.72))     # 8 → 5
MAX_SOFT_REFS = round(10 * _dynamic_fullness_factor(0.72))         # 10 → 6
```

信号不是章节数驱动的——一部 80 章的小说可能到 Ch60 才 fullness=0.8，一部 30 章的小说在 Ch20 就已满了。有机性来自于 CreativeDirector 的感知，不是外部阈值。

**改动量**：CreativeDirector craft card +2 行（prompt 中加输出字段说明），CreativeBrief model +1 字段，ContextManager +12 行。

#### 1.2 CharacterFocus — 角色聚光灯

每章选定 2-3 个焦点角色，其余压缩为单行摘要：

```yaml
character_focus:
  - character_id: "jiang_ran"
    detail_level: "full"        # 完整快照（出场角色）
  - character_id: "ai_la"
    detail_level: "full"
  - character_id: "old_ghost"
    detail_level: "compressed"  # 压缩为"名字 + 最后已知状态"
  - character_id: "zhao_ming"
    detail_level: "skip"        # 本章不加载
```

ContextManager 根据 detail_level 加载不同粒度的角色信息。焦点角色保留完整快照，压缩角色只给一行摘要（"艾拉：联邦探员，目前立场倾向于江燃"），skip 角色完全不加载。

**改动量**：CreativeDirector craft card +5 行，CreativeBrief model +1 list field，ContextManager._build_character_snapshots() 加 ~20 行条件分支。

#### 1.3 ForeshadowingUrgency — 伏笔延迟跟踪

不是把所有活跃伏笔都塞给 Writer，而是按紧迫性排序：

```python
# ContextManager 新增伏笔排序
def _rank_foreshadowings(self, items, current_chapter, delay_history):
    ranked = []
    for item in items:
        urgency = 0.0
        # due_chapter 在 2 章之内 → 高紧迫
        if item.due_chapter and item.due_chapter - current_chapter <= 2:
            urgency += 2.0
        # 已延迟 3 次以上 → 强制加载
        if delay_history.get(item.foreshadowing_id, 0) >= 3:
            urgency += 3.0
        # 与本章出场角色相关 → 中等紧迫
        if any(c in item.related_characters for c in self._focus_characters):
            urgency += 1.0
        ranked.append((item, urgency))
    
    ranked.sort(key=lambda x: -x[1])
    return [item for item, _ in ranked[:MAX_FORESHADOWING]]
```

**改动量**：ForeshadowingItem model +1 field（`delay_count: int = 0`），ContextManager 新增 `_rank_foreshadowings()` ~25 行。

#### 1.4 FocalDistance — 景深随机化

CreativeDirector 掷景深——不由 chapter_type 决定，而是随机：

```yaml
focal_distance: "close"  # close(40%) | mid(40%) | wide(15%) | disruption(5%)
```

| 焦段 | 角色状态 | 场景设定 | 伏笔 | 感官优先级 |
|------|---------|---------|------|-----------|
| Close | 3个完整快照 | 1个 | 0-1个 | 触觉 > 听觉 > 痛觉 |
| Mid | 2个压缩 | 2个 | 2-3个 | 动作 > 对话 > 视觉 |
| Wide | 1行摘要 | 5个活跃场景 | 1个 | 视觉 > 嗅觉 > 温度 |
| Disruption | 随机选择 | 随机 | 随机 | 随机打破感官优先级 |

Wide 的 15% 频率意味着 50 章小说中约 7-8 章是"呼吸型"章节——在密集情节之间给读者喘息空间。Disruption 的 5% 频率约 2-3 章完全打破模式（幻觉/闪回/第二 POV）。

ContextManager 根据焦段调整上下文包配置，Writer Prompt 根据焦段用不同的 system prompt section。

**改动量**：CreativeDirector craft card +6 行，CreativeBrief model +1 field，ContextManager 新增 `_apply_focal_distance()` ~15 行，Writer craft card 新增 4 个焦段 section（~20 行）。

#### 1.5 四信号的协同

```
CreativeDirector (单次 LLM 调用)
  ├── narrative_fullness: 0.72     (信号1: 压力)
  ├── character_focus: [...]       (信号2: 焦点)
  ├── foreshadowing_urgency: [...] (信号3: 时机)
  └── focal_distance: "close"      (信号4: 景深)
       ↓
ContextManager
  ├── 总量: MAX * fullness_factor
  ├── 角色: full / compressed / skip
  ├── 伏笔: urgency ranking
  └── 景深: sensory priority + section injection
       ↓
Writer
  得到一个精炼的、有机的、有随机性的上下文包
```

---

### 2. Craft Card 1.0.8 → 1.0.9

问题：1.0.8 删除了"系统将拒绝并要求重写"，导致超标率翻倍。1.0.9 需要在两者之间找到平衡。

**当前 1.0.8 的问题措辞**：
```
3. 严格遵循字数目标（{{ word_count_target }} 字左右）。**不同章节类型有不同的自然篇幅**...
   **核心原则**：写得好的章节比字数精确的章节更重要——不要为了凑上限而破坏叙事节奏。
```

这太松了。Writer 把它解读为"字数限制只是建议"。

**1.0.9 的替换措辞**：
```
3. 严格遵循字数目标（{{ word_count_target }} 字左右）。**不同章节类型有不同的自然篇幅**...
   - 如果场景需要更多篇幅来充分展开，可以接受适度的超标（1.3x 以内）
   - 但 1.4x 以上的超标会被视为结构缺陷——意味着你在这一章中放了太多内容
   - 如果你发现自己正在接近 1.4x，考虑将部分内容移到下一章
   - **不足 0.8x 同样不可接受**——字数不足意味着情节展开不够
```

这比 1.0.7 的"拒绝重写"更温和，比 1.0.8 的"随便超"更严格。关键在于给出了**具体的数值边界**（1.3x 可以，1.4x 不行），而不是情感性的威胁（"将被拒绝"）。

**改动量**：Writer craft card `1.0.9.yaml` 中修改输出要求第 3 条的文本，~10 行。

---

### 3. Accept 路径字数守卫

当前：Auditor 对字数不负责。如果一个章节除了字数之外没有其他问题，它就会在 1 轮修订后通过。

**修复**：在 `settlement_extractor_node` 的 accept 逻辑中加入字数检查：

```python
# _nodes.py: settlement_extractor_node or human_gate_node
# 在 accept 之前检查
if version.word_count > goal.word_count_target * 1.40:
    if state["revision_round"] < 2:
        # 字数严重超标 + 修订不足 2 轮 → 触发 rewrite
        return {
            "_needs_revision": True,
            "_has_major": True,  # 强制走 revision 路径
            "human_decision": "rewrite_word_count",
            "status": "rule_auditing"
        }
```

逻辑：
- 超标 > 1.40x AND 修订 < 2 轮 → 自动触发 rewrite
- 超标 > 1.20x AND 修订 < 1 轮 → 自动增加 1 轮 revision
- 超标 < 1.20x OR 已有 2+ 轮修订 → 正常通过

这不是 "reject"——是"多给你一轮修订"。和 Craft Card 1.0.9 的措辞呼应：1.4x 被视为结构缺陷。

**改动量**：`_nodes.py` `settlement_extractor_node` 或 `human_gate_node` 加 ~20 行。

---

### 4. 删除 min_scenes=2 截断保护

当前：`enforce_word_count` 中 `min_scenes=2` 阻止了对 1-scene 章节的截断。Task 096 的数据证明了 1-scene 章节可以是好章节（Ch39 1.12x, Ch41 1.22x）。

**改为字数保护**：不管场景数，统一用字数超标来触发截断。

```python
# truncation.py: 删除 min_scenes 检查
# 旧:
if len(scenes) < min_scenes:
    return content, scenes, current_word_count, False, "_disallowed_by_scene_structure"

# 新:
# 直接进入截断逻辑，不按场景数判断
# 如果截断后只剩 1 个场景但字数达标，允许
```

**改动量**：`truncation.py` 删除 ~4 行。

---

## In Scope

### 代码改动

| 文件 | 改动类型 | 行数 |
|------|---------|------|
| `agents/creative_director/__init__.py` | craft card 新增 4 个信号输出 | ~5 |
| `models/creative_mode.py` (CreativeBrief) | 新增 4 个字段 | ~10 |
| `agents/context_manager/__init__.py` | 新增 `_dynamic_fullness_factor()`、`_rank_foreshadowings()`、`_apply_focal_distance()` | ~60 |
| `agents/context_manager/_assemblers.py` | `_build_character_snapshots()` 支持 compressed/skip | ~25 |
| `utils/truncation.py` | 删除 `min_scenes` 截断保护 | -4 |
| `workflows/_nodes.py` | Accept 路径字数检查 | ~20 |

### Prompt 改动

| 文件 | 改动 |
|------|------|
| `prompts/cards/creative_director/1.0.4.yaml` | 新增 4 个信号输出字段 |
| `prompts/cards/writer/1.0.9.yaml` | 措辞回调：1.3x 可以，1.4x 不行 |
| `prompts/cards/writer/_manifest.yaml` | 新增 1.0.9 版本记录 |

### 测试

| 文件 | 内容 |
|------|------|
| `tests/test_context_manager.py` | 测试 fullness_factor 计算、foreshadowing ranking |
| `tests/test_creative_director.py` | 测试 4 个信号输出 |
| `tests/test_phase1_graph.py` | 测试 accept 路径字数守卫 |
| `tests/test_truncation.py` | 测试删除 min_scenes 后的 1-scene 截断行为 |

---

## Out of Scope

- RAG 检索优化（Phase C 范围）
- ContextService 架构改造（Phase C 范围，Task 104-106）
- Health Score 公式优化
- 多模型路由

---

## 验收条件

### 功能

- [ ] CreativeDirector 输出 `narrative_fullness`、`character_focus`、`foreshadowing_urgency`、`focal_distance` 四个字段
- [ ] ContextManager 根据 fullness 动态调整上下文包上限
- [ ] ContextManager 根据 character_focus 加载不同粒度的角色快照
- [ ] ContextManager 根据 foreshadowing_urgency 排序伏笔加载优先级
- [ ] ContextManager 根据 focal_distance 切换上下文包配置
- [ ] Writer prompt 根据 focal_distance 注入不同的 system prompt section
- [ ] Accept 路径上超标 > 1.40x 且修订 < 2 轮时触发 rewrite
- [ ] 1-scene 章节可以被截断（min_scenes 保护已移除）
- [ ] Craft Card 1.0.9 的 1.4x 警告清晰传达

### 测试

- [ ] 全部测试通过 `1416+ passed`
- [ ] 新增上下文压力计测试通过
- [ ] Accept 路径字数守卫测试通过

### 验证

- [ ] Ch2-Ch50 回归验证：达标率 > 78%，超标率 < 18%，最大超标 < 1.50x
- [ ] 四信号分布的随机性验证：50 章中 Wide 出现 5-10 次，Disruption 出现 1-4 次
- [ ] 1-scene 章节的字数达标率改善

---

## 风险

1. **CreativeDirector 的 4 个信号质量**：LLM 生成的结构化字段可能有偏差，需要验证输出格式的稳定性
2. **过度优化**：四个信号同时作用可能互相干扰，需要分阶段验证
3. **Craft Card 1.0.9 的措辞**：1.4x 警告的强度需要通过实际运行验证——太强会回到 1.0.7 的恐惧，太弱会和 1.0.8 一样无效
