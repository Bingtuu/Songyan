# Task 072: Settlement source_quote 去噪

> **Phase**: V3.1 — 质量跃迁
> **优先级**: P2
> **依赖**: 无
> **预计工作量**: 中（~6 小时）

---

## Goal

解决 SettlementExtractor 产生的 `source_quote` 噪声问题（20-40 条/章），提高结算数据的可用性和准确性。

## Context

058b 数据：
- 每章 settlement 包含 20-40 条 `source_quote`
- 大量 source_quote 是**无效引用**：
  - 引用的是叙述性句子而非关键设定
  - 引用长度超过 100 字，缺乏精确性
  - 同一设定被多次重复引用
  - 引用内容在正文中不存在（幻觉引用）

影响：
- 结算数据臃肿，查询性能下降
- 人类 review 时难以快速定位关键设定
- 跨章一致性审计时噪声干扰判断

## In Scope（必须完成）

- [ ] 分析 058b 的 settlement 数据，统计 source_quote 的类型分布（有效 vs 噪声）
- [ ] 设计过滤规则：
  - 长度过滤：`source_quote` 超过 80 字视为噪声
  - 去重过滤：同一 `setting_key` 的多个 quote 只保留最短的 1 条
  - 存在性验证：`source_quote` 必须在正文中存在（模糊匹配）
  - 类型过滤：排除纯叙述句，只保留包含**设定关键词**的引用
- [ ] 在 `SettlementExtractor` 的 `_validate_source_quote()` 中实现过滤逻辑
- [ ] 修改 `NewSetting.source_quote` 的验证逻辑
- [ ] 补充单元测试：各种噪声场景的过滤效果
- [ ] 补充回归测试：`pytest tests/ -x -q` 全部通过

## Out of Scope（明确不做）

- 不修改 SettlementExtractor 的整体架构
- 不做 LLM 二次验证 source_quote（成本过高）
- 不清理历史数据（只过滤新生成的 settlement）
- 不修改 `source_quote` 的数据模型结构

## 过滤规则

```python
MAX_QUOTE_LENGTH = 80
MIN_QUOTE_LENGTH = 5

def filter_source_quotes(
    quotes: list[str],
    content: str,
    setting_key: str,
) -> list[str]:
    """过滤 source_quote 噪声.
    
    规则：
    1. 长度必须在 [5, 80] 字之间
    2. 必须在正文中存在（模糊匹配，允许前后 3 字偏移）
    3. 同一 setting_key 只保留最短的一条
    4. 必须包含 setting_key 或其同义词
    """
    ...
```

## 测试要求

- [ ] 超过 80 字的 quote 被过滤
- [ ] 正文中不存在的 quote 被过滤
- [ ] 同一 setting_key 的多个 quote 只保留最短的一条
- [ ] 不包含 setting_key 的 quote 被过滤
- [ ] 有效 quote（短、存在、含关键词）保留

## 验收标准

- [ ] `pytest tests/test_settlement_extractor.py -v` 全部通过 + 新增测试通过
- [ ] 模拟 settlement 生成后，source_quote 数量从 30 条降至 <= 10 条
- [ ] `docs/STATUS.md` 更新
- [ ] 生成 `tasks/072-settlement-source-quote-denoising-DONE.md`

## 参考文档

- `src/songyan/agents/settlement_extractor/__init__.py` — SettlementExtractor
- `src/songyan/agents/settlement_extractor/_apply.py` — 结算应用逻辑
- `src/songyan/models/settlement.py` — `NewSetting` 模型
