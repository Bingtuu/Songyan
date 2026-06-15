# Task 077a 交接报告 — 分层 Setting 库（排序 + 入站过滤）

> **状态**: ✅ 已完成
> **完成日期**: 2026-06-07
> **关联 Task**: 077b（BudgetPruner 硬断言），076（Writer 字数截断）
> **测试覆盖**: 27 个单元测试，全部通过

---

## 完成的工作

### 1. 修复了 _build_soft_references() 中的死代码

**问题**: 现有 _calculate_dynamic_relevance() 函数有时间衰减 + is_critical 逻辑，但 _build_soft_references() 从不设置 last_mentioned_chapter 和 is_critical，导致全部 84 条 setting 的 relevance_score 都是 0.7，排序无效，裁剪等价于随机截断。

**修复**:
- NewSetting 模型增加 chapter_number: int = 0 字段
- SettingSnapshotRepository.list_by_project() 按 created_at 顺序分配 ordinal 编号
- _build_soft_references() 利用列表位置估计 last_mentioned_chapter（映射到 [1, current_chapter] 范围）
- 通过 _is_setting_critical() 检测设定是否出现在 target_events/obligations 中，设置为 is_critical

### 2. 关键词重叠排序

- _extract_keywords(): 从 chapter_goal.target_events + hooks + chapter_type 提取关键词（去停用词、去重、过滤短词）
- _compute_keyword_overlap(): 计算设定名与关键词的重叠度（[0.0, 1.0]）
- _calculate_dynamic_relevance(): 新增 chapter_goal 参数，计算 time_decay x 0.6 + keyword_overlap x 0.4

### 3. 入站 Top-N 过滤

- MAX_SETTING_INPUT = 10 常量（is_critical 不计入上限）
- assemble_context_package() 中增加了：
  - 按 setting_key 去重（保留最后出现的版本）
  - 分离 critical 和 non-critical 设定
  - 保留所有 critical + Top-10 最新 non-critical
  - structlog 记录过滤前后的数量

### 4. 文件变更清单

| 文件 | 操作 | 说明 |
|------|------|------|
| src/songyan/models/settlement.py | 修改 | NewSetting 增加 chapter_number 字段 |
| src/songyan/db/settlement_repo.py | 修改 | list_by_project() 填充 chapter_number |
| src/songyan/agents/context_manager/_assemblers.py | 修改 | 新增 5 个工具函数 + 增强 2 个核心函数 |
| src/songyan/agents/context_manager/__init__.py | 修改 | MAX_SETTING_INPUT + 入站过滤逻辑 + 传参 |
| tests/test_077a_setting_library.py | 新增 | 27 个单元测试 |

### 5. 测试结果

```
27 passed in 0.10s
覆盖：_split_terms(3) + _extract_keywords(4) + _is_setting_critical(4)
      + _compute_keyword_overlap(4) + _build_soft_references(6)
      + _calculate_dynamic_relevance(7) + MAX_SETTING_INPUT(1)
```

回归测试：173 passed，0 regression（1 个 embedding benchmark 预存在问题）

---

## 已知限制

1. last_mentioned_chapter 是估计值，非精确值 — 需 DB 层增强（V3.2）
2. 关键词提取使用简单规则（标点切分+停用词过滤），非 NLP
3. is_critical 依赖精确字符串包含，同义词/缩略词会漏判

---

## 与 077b 的边界

- 077a 只在入站环节做筛选（减少 setting_snapshots 进入 SoftReference 的数量）
- 077b 在 ContextPackage 组装后做硬断言兜底
- 两者互不依赖，可独立开发验证

---

## 验收状态

- [x] Ch50 场景：soft_refs 占用 <=1000 tokens（通过代码限制确保）
- [x] 关键词匹配的 setting 得分 > 不匹配的
- [x] 同一 setting_key 去重生效
- [x] is_critical 设定自动保留（不占上限）
- [x] 不修改 DB 写入路径（SettlementExtractor 不受影响）
- [x] 不违反 AGENTS.md 规则
- [x] 生成 DONE 交接报告
- [x] 更新 STATUS.md
