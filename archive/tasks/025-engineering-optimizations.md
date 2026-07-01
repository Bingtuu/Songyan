# Task 025: 工程优化（patch 匹配 / 成本估算 / 上下文膨胀）

> **Phase**: Phase 4（工程收尾）
> **优先级**: P2（V1.1 体验优化）
> **依赖**: Task 024（Prompt 打磨完成）
> **预计工作量**: 小

---

## Goal

修复 3 个工程层面的体验问题，降低运行成本、提升修订成功率。

## Context

这些是 Round 2/3 真实评测中观察到的工程问题，不影响核心功能，但长期累积会影响用户体验和成本。

## In Scope（必须完成）

- [ ] **Revision Handler patch 匹配率提升**：
  - Round 2 v2：1/8 patch 未找到原文
  - Round 3 v3：1/6 patch 未找到原文
  - 方案：增加模糊匹配（Levenshtein 距离 ≤ 10%）或段落级匹配回退
- [ ] **LLM 调用成本估算公式修正**：
  - 预估 ¥0.5-3，实际 ¥0.13-0.15
  - 更新 `evals/runner.py` 或相关模块的成本估算公式
- [ ] **Multi-turn 上下文膨胀控制**：
  - 3 轮 revision 后 LLMAuditor prompt 字符数从 8393→8598→9448 持续增长
  - 方案：对历史 review 做摘要压缩，或只保留最近 2 轮的 review context

## Out of Scope（明确不做）

- 重写 Revision Handler 架构
- 更换 LLM 提供商
- 缓存层实现

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
    """基于实际 DeepSeek API 定价的精确估算."""
    ...

# 上下文压缩
async def _compress_review_history(reviews: list[ReviewReport]) -> str:
    """将多轮 review 压缩为摘要，控制 token 增长."""
    ...
```

## 测试要求

### Layer 1: 无需新增模型

### Layer 2: 模块测试
- [ ] 模糊匹配：100% 匹配、90% 匹配（应找到）、70% 匹配（应失败）
- [ ] 成本估算：与实际账单误差 ≤ 20%
- [ ] 上下文压缩：3 轮 review → 压缩后长度 ≤ 1.5 轮原长度

### Layer 3: 集成测试
- [ ] Revision Handler 在模糊匹配辅助下 patch 成功率 ≥ 95%

## 验收标准（Acceptance Criteria）

- [ ] patch 匹配失败率从 ~15% 降到 ≤ 5%
- [ ] 成本估算误差 ≤ 20%
- [ ] 3 轮 revision 后 LLMAuditor prompt 字符数增长 ≤ 10%（vs 当前 ~12%）
- [ ] 所有现有测试继续通过
- [ ] 更新了 `docs/STATUS.md`
- [ ] 生成了 `tasks/025-engineering-optimizations-DONE.md` 交接文件

## 参考文档

- `src/songyan/agents/revision_handler.py`
- `src/songyan/agents/llm_auditor.py`
- `evals/runner.py`
- `evals/output/ROUND2_ANALYSIS_REPORT.md`
- `evals/output/ROUND3_ANALYSIS_REPORT.md`
