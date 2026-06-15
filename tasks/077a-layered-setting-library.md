# Task 077a: 分层 Setting 库 — 排序 + 入站过滤

> **Phase**: V3.1 100章架构改造 — Phase A 止血
> **优先级**: P0
> **依赖**: 无（与 077b 互不依赖，可并行）
> **预计工作量**: 小-中（0.5-1 天）

---

## Goal

两件事：一是修复现有死代码，让 time-decay + is_critical 实际生效；二是增加关键词重叠排序，在 **入站环节** 就限制 setting_snapshots 转 SoftReference 的数量。

最终目标：Ch50 场景 soft_refs 占用从 ~3000 tokens 降到 <=1000 tokens。

## Context

V3.1 验证报告 **4.1.1**（Token 预算不可恢复超支）的根因之一是 setting_snapshots 线性增长。到 Ch50 有 84 条 setting，全部以 relevance_score=0.7（无区分度）进入 SoftReference。

现有 _calculate_dynamic_relevance() 函数看上去有时间衰减 + is_critical 逻辑，但实际上**从未执行过**。因为 _build_soft_references() 不设置 last_mentioned_chapter 和 is_critical。全部84条的 relevance_score 都是 0.7，排序无效，裁剪等价于随机截断。

验证报告中 Ch50 数据：
- setting_snapshots: 84 条
- Ch100 预估: ~184 条
- soft_refs 当前占用: ~3000 tokens
- 目标: <=1000 tokens

## In Scope

### 1. 修复 _build_soft_references() 死代码

- [ ] NewSetting 模型增加 chapter_number: int = 0 字段
  - 文件: src/songyan/models/settlement.py
  - 不修改 DB schema（DB 已有 created_at，读取端推导）
- [ ] SettingSnapshotRepository.list_by_project() 返回时填充 chapter_number
  - 文件: src/songyan/db/settlement_repo.py
  - 利用 Python 层枚举（ORDER BY created_at 后按位置编号）
- [ ] _build_soft_references() 传递 last_mentioned_chapter 到 SoftReference
  - 文件: src/songyan/agents/context_manager/_assemblers.py
  - 使 time-decay 逻辑正式生效
- [ ] 同 setting_key 去重：只保留最后出现的版本，减少冗余

### 2. 关键词重叠排序

- [ ] 从 chapter_goal.target_events + chapter_goal.hooks + chapter_goal.chapter_type 提取关键词
  - 简单实现：分词 + 中文停用词过滤
- [ ] 增强 _calculate_dynamic_relevance()：增加关键词重叠维度
  - 重叠比例 → relevance boost（+0..+0.3）
  - 设定名出现在 target_events/obligations 中时 → is_critical 标记
- [ ] 加权融合：time_decay x 0.6 + keyword_overlap x 0.4

### 3. 入站 Top-N 过滤

- [ ] 在 assemble_context_package() 中，调用 _build_soft_references() 前：
  - 去重（setting_key）
  - 排序（relevance desc）
  - 截断到 Top-10
  - is_critical 不占上限
- [ ] 新增模块级常量：MAX_SETTING_INPUT: int = 10
- [ ] 调整 _prune_soft_references() 与入站上限保持一致

### 4. 测试

- [ ] 关键词重叠：target_events 匹配的 setting 得分 > 不匹配的
- [ ] 时间衰减：久未提及的 setting 得分 < 最近提及的
- [ ] is_critical 标记：出现在 target_events/obligations 中的 setting >= 0.9
- [ ] 入站截断：84 条 setting → 最多 10 条 SoftReference
- [ ] 去重：同 setting_key 重复记录只保留最后一条
- [ ] 集成验证：Ch50 场景 soft_refs 占用 <=1000 tokens
- [ ] pytest 通过

## Out of Scope

- 不修改 DB schema（仅增强读取端）
- 不做 setting 聚类/聚合（V3.2）
- 不修改 Writer prompt
- BudgetPruner 硬断言 → 077b

## 接口契约

```python
# NewSetting 仅新增可选字段
class NewSetting(BaseModel):
    setting_name: str
    description: str
    source_quote: str
    setting_key: str = ""
    chapter_number: int = 0  # 新增：创建时的章节编号


# 增强后的动态相关性计算
def _calculate_dynamic_relevance(
    soft_ref: SoftReference,
    current_chapter: int,
    recent_chapters: list[int],
    chapter_goal: ChapterGoal | None = None,
) -> float:
    """动态相关性 = time_decay x 0.6 + keyword_overlap x 0.4.
    time_decay: 基于 last_mentioned_chapter 的距离衰减
    keyword_overlap: 与 chapter_goal 目标事件 + 钩子的关键词重叠度
    is_critical 设定始终 >= 0.9
    """

# 新增入站常量
MAX_SETTING_INPUT: int = 10  # setting_snapshots -> SoftReference 硬上限
```

## 验收标准

- [ ] Ch50 场景：soft_refs 占用 <=1000 tokens（当前 ~3000）
- [ ] 关键词匹配的 setting 得分 > 不匹配的，recent > 老旧
- [ ] 同一 setting_key 去重生效
- [ ] is_critical 设定自动保留（不占上限）
- [ ] 不修改 DB 写入路径（SettlementExtractor 不受影响）
- [ ] 不违反 AGENTS.md 规则
- [ ] 生成 DONE 交接报告 + 更新 STATUS.md
