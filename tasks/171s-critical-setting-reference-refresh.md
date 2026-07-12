# Task 171s: Ch200 撞墙定点修复 —— critical setting 同义提及刷新

> **框架**: `docs/reports/v7-literary-framework-review.md` §8 D1/D3 + `NNNp` 撞墙修复通道  
> **类型**: 小型撞墙修复（不放宽门禁）  
> **优先级**: P0（当前 Ch200 resume 在 Ch165 被 false critical orphan halt 阻断）  
> **状态**: ✅ **完成（代码 + 回归测试 + 当前 DB 实证刷新）**

## 结论

Ch159/Ch165 两次 halt 都来自同一个 critical setting：

`protagonist.genetic_identity.reaper_maker_consistency`

正文并没有遗忘该设定。Ch160-165 多次写到“基因一致性”“收割者制造者的基因签名”“你的基因就是钥匙”“十七处基因修改”等核心证据，但 `setting_tracking.last_mentioned_chapter` 停在 Ch159，导致 `ContinuityAuditor` 误判为 critical orphan。

因此本 task 不改 `health_low_p1_halt`、不降低 critical orphan 门禁，只修复 **正文证据到 tracking 刷新** 的召回缺口。

## 根因

`settlement_extractor/_apply.py::_detect_setting_references` 已有 deterministic recycle detection，但 `_setting_reference_terms` 主要依赖：

- 完整 `setting_name`
- `setting_name` 按标点/空白拆出的片段
- `setting_key` tail
- 少量手写 canonical cluster

对于“林渊与收割者制造者的基因一致性”这类复合中文设定，正文常用的是同义压缩表达（“基因一致性”“基因签名”“基因修改”），而不是完整 setting_name。现有词面匹配无法覆盖，导致 tracking stale。

## 修复边界

### 做

1. 增强 `_setting_reference_terms` 的中文核心短语召回：
   - 从 `setting_name` 生成连续中文 n-gram（2-6 字）；
   - 过滤低信息停用词与纯角色名片段；
   - 保留高信息技术/设定词组，如“基因一致性”“收割者制造者”“基因签名”等。
2. 增加多 token 命中辅助：
   - 对复合 setting，若正文命中多个高信息短语，可视为引用；
   - 仍保持 deterministic，不调用 LLM。
3. 加回归测试：
   - Ch160 风格文本“基因一致性 / 收割者制造者的基因签名”必须刷新；
   - Ch161 风格文本“你的基因就是钥匙”至少通过高信息 token 命中；
   - 原有“天剑宗”误命中防护仍保持。

### 不做

- 不放宽 `health_low_p1_halt`；
- 不把 critical orphan 降级；
- 不引入 LLM 语义匹配；
- 不修改 Writer/CreativeDirector 生成逻辑。

## 验证

```powershell
python -m pytest tests/test_task137_setting_recycling.py -q
ruff check src/songyan/agents/settlement_extractor/_apply.py tests/test_task137_setting_recycling.py
```

实证：

1. 用修复后的 `_detect_setting_references` 扫 Ch160-165 accepted 正文；
2. 确认该 setting 可被 Ch160/161/164/165 命中；
3. 将当前 DB 的 `last_mentioned_chapter` 刷到 Ch165；
4. resume Ch200 长跑。

## 完成记录

- `tests/test_task137_setting_recycling.py`: 51 passed。
- `ruff check src/songyan/agents/settlement_extractor/_apply.py tests/test_task137_setting_recycling.py`: passed。
- 当前 DB 实证：Ch160/161/162/164/165 均命中
  `protagonist.genetic_identity.reaper_maker_consistency`，已按修复后的 detection
  将 `last_mentioned_chapter` 刷到 Ch165。
