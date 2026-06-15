# Task 072: Settlement source_quote 去噪 — 交接报告

> **状态**: ✅ 已完成
> **完成日期**: 2026-06-06
> **耗时**: ~1.5 小时
> **提交**: `TODO`

---

## 做了什么

### 1. 过滤规则实现

新建 `src/songyan/agents/settlement_extractor/_quote_filter.py`：

| 规则 | 参数 | 行为 |
|------|------|------|
| 长度过滤 | `MIN=5`, `MAX=80` | 过短/过长 quote 清空 |
| 存在性验证 | 模糊匹配 (`difflib`, threshold=0.8) | 正文中不存在的 quote 清空 |
| 关键词过滤 | `setting_name` / `character_id` | 不含相关关键词的 quote 清空 |
| 去重过滤 | 同一 `setting_key` | 保留 `source_quote` 最短的一条，其余清空 |

### 2. 集成到 SettlementExtractor 流程

- `extract_settlement` 中在 `_build_state_settlement` 之后、`_validate_settlement` 之前插入 `filter_settlement_source_quotes()`
- `_validate_settlement` 跳过空的 `source_quote`（避免把已过滤的 quote 报告为错误）
- 过滤数量记录 structlog：`settlement.source_quotes_filtered`

### 3. 测试

| 测试文件 | 新增用例 | 结果 |
|---------|---------|------|
| `tests/test_quote_filter.py` | 17 | ✅ 全部通过 |
| `tests/test_settlement_extractor.py` | 45（原有） | ✅ 全部通过 |

### 4. 效果验证

`test_reduces_total_quotes` 模拟 30 条 quote（10 character + 10 setting + 10 numerical）：
- 输入：30 条 quote（50% 噪声）
- 过滤后：15 条保留，15 条清空
- **噪声减少 50%**

---

## 过滤逻辑细节

```python
def filter_settlement_source_quotes(settlement: StateSettlement, content: str) -> int:
    """对 CharacterUpdate / NewSetting / Increment / Decrement 的 source_quote 执行过滤."""
    # 1. CharacterUpdate: 长度 + 存在性 + character_id 关键词
    # 2. NewSetting: 长度 + 存在性 + setting_name 关键词 + 同一 setting_key 去重
    # 3. Increment/Decrement: 长度 + 存在性
    # 无效 quote 被清空为 ""
```

**关键词匹配策略**：
- 精确子串匹配（不区分大小写）
- 或：关键词中至少一半的字出现在 quote 中（中文分字匹配）

---

## 已知限制

- **关键词匹配较严格**：`setting_name` 必须完整或半数字出现在 quote 中，可能导致少量有效 quote 被误过滤
- **不去重 CharacterUpdate**：同一角色的多个更新各自保留，不执行去重
- **不清理历史数据**：只过滤新生成的 settlement，已有数据不变
- **未做 LLM 二次验证**：纯代码规则过滤，无 LLM 成本

---

## 文件变更清单

```
src/songyan/agents/settlement_extractor/_quote_filter.py   # 新建
src/songyan/agents/settlement_extractor/_validate.py        # 跳过空 source_quote
src/songyan/agents/settlement_extractor/__init__.py         # 集成过滤调用
tests/test_quote_filter.py                                   # 新建（17 个测试）
docs/STATUS.md                                               # 更新 072 状态
```

---

## 下一步

- **073**: 截断重写策略
- 端到端验证：运行 Ch31-Ch40，观察 settlement 中 source_quote 数量是否显著减少
