# Task 033: 工程优化三项收尾（Revision 模糊匹配 / 成本估算 / 上下文压缩）

> **Phase**: Stage A（还债与封锁解除）
> **优先级**: P1
> **依赖**: Task 032（DONE 报告补齐）
> **预计工作量**: 中

---

## Goal

完成 V1.x 遗留的三项工程优化，降低运行成本、提升修订成功率。

## Context

Task 025 规格已定义但未执行。三项问题来自 Round 2/3 真实评测：patch 匹配失败率 ~15%、成本估算严重偏高（预估 ¥0.5-3，实际 ¥0.13-0.15）、3 轮 revision 后 LLMAuditor prompt 字符数持续增长（8393→8598→9448）。

## In Scope

- [ ] **Revision Handler 模糊匹配**：
  - 实现 `_find_text_fuzzy(text, target, max_distance_ratio=0.1)`
  - Levenshtein 距离 ≤ 10% 时回退匹配
  - 集成到 `RevisionHandler.apply_patch()` 的查找逻辑中
  - 将 patch 匹配失败率从 ~15% 降到 ≤ 5%
- [ ] **成本估算修正**：
  - 实现 `estimate_cost(prompt_tokens, completion_tokens, model) -> float`
  - 基于实际 DeepSeek API 定价（输入/输出单价）
  - 替换 `evals/runner.py` 或相关模块中的估算逻辑
  - 误差 ≤ 20%
- [ ] **上下文压缩**：
  - 实现 `_compress_review_history(reviews: list[ReviewReport]) -> str`
  - 多轮 review 压缩为摘要，控制 token 增长
  - 3 轮 review 压缩后长度 ≤ 1.5 轮原长度
  - LLMAuditor prompt 字符数增长 ≤ 10%（当前 ~12%）

## Out of Scope

- 重写 Revision Handler 架构
- 更换 LLM 提供商或模型
- 缓存层实现
- 不修改 RuleAuditor / LiteraryAuditor 的 review 历史处理

## 接口契约

```python
# Revision Handler 模糊匹配
async def _find_text_fuzzy(
    text: str,
    target: str,
    max_distance_ratio: float = 0.1,
) -> tuple[int, int] | None:
    """在 text 中模糊查找 target，返回 (start, end) 或 None."""
    ...

# 成本估算修正
def estimate_cost(prompt_tokens: int, completion_tokens: int, model: str) -> float:
    """基于实际 DeepSeek API 定价的精确估算（单位：RMB）."""
    ...

# 上下文压缩
async def _compress_review_history(reviews: list[ReviewReport]) -> str:
    """将多轮 review 压缩为摘要，控制 token 增长."""
    ...
```

## 测试要求

### Layer 1: 模型测试
- [ ] `estimate_cost` 边界：0 tokens → 0 cost

### Layer 2: 模块测试
- [ ] 模糊匹配：100% 匹配（应找到）/ 90% 匹配（应找到）/ 70% 匹配（应失败）
- [ ] 成本估算：与实际账单误差 ≤ 20%（基于已知账单数据点）
- [ ] 上下文压缩：3 轮 review → 压缩后长度 ≤ 1.5 轮原长度
- [ ] 压缩后关键信息不丢失（issue count / severity 保留）

### Layer 3: 集成测试
- [ ] Revision Handler 在模糊匹配辅助下 patch 成功率 ≥ 95%
- [ ] LLMAuditor 在 3 轮 revision 后 prompt 字符数增长 ≤ 10%

## 验收标准

- [ ] patch 匹配失败率从 ~15% 降到 ≤ 5%
- [ ] 成本估算与实际账单误差 ≤ 20%
- [ ] 3 轮 revision 后 LLMAuditor prompt 字符数增长 ≤ 10%
- [ ] 所有现有测试继续通过（pytest 全绿）
- [ ] 代码符合 CLAUDE.md 规范
- [ ] 更新了 `docs/STATUS.md`
- [ ] 生成了 `tasks/033-engineering-cleanup-DONE.md` 交接文件

## 参考

- `tasks/025-engineering-optimizations.md` — V1.x 原始规格
- `src/songyan/agents/revision_handler.py`
- `src/songyan/agents/llm_auditor.py`
- `evals/runner.py`
- `evals/output/ROUND2_ANALYSIS_REPORT.md`
- `evals/output/ROUND3_ANALYSIS_REPORT.md`
