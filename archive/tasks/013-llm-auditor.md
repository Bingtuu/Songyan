# Task 013: LLMAuditor Agent

> **Phase**: Phase 2 — 审查环节
> **优先级**: P0
> **依赖**: Task 011 (Writer Agent), Task 012 (RuleAuditor)
> **预计工作量**: 中

---

## Goal

实现 LLMAuditor Agent —— 调用 LLM 对章节进行语义层面的深度审查，覆盖 12 个维度（一致性、叙事质量、对话质量、描写质量、题材专项），输出结构化的 LLMAuditResult。

## Context

LLMAuditor 是审查环节的第二个 Agent，与 RuleAuditor 互补：
- RuleAuditor：纯代码，检测表层模式（AI 腔、疲劳词、钩子、节奏）
- LLMAuditor：调用 LLM，检测深层语义问题（设定一致性、人物行为逻辑、叙事节奏、对话质量、描写质量等）

LLMAuditor 的输入是章节正文 + ContextPackage（提供背景上下文），输出 LLMAuditResult，最终与 RuleAuditor 结果合并为 MergedReviewReport。

## In Scope（必须完成）

- [ ] `run_llm_audit()` 主入口 — Prompt 渲染 → LLM 调用 → JSON 解析 → LLMAuditResult
- [ ] Prompt 模板：`prompts/llm_auditor.md`
- [ ] 12 维度审查说明注入 Prompt
- [ ] JSON 解析：复用 `llm/parsing.py` 的 `extract_json` + `parse_llm_response`
- [ ] 结果组装：`LLMAuditResult`（issues + dimension_scores + 文学性评分）
- [ ] 保存集成：`save_llm_audit()` 写入 `review_reports`
- [ ] 测试：JSON 解析、结果组装、边界条件、集成测试

## Out of Scope（明确不做）

- 不做规则检测（RuleAuditor 负责，Task 012）
- 不做文学性诊断（LiteraryAuditor 负责，Task 014）
- 不做合并报告逻辑（RevisionHandler 或编排层负责）

## 接口契约

```python
async def run_llm_audit(
    content: str,
    context_package: ContextPackage | None = None,
    temperature: float = 0.3,
) -> LLMAuditResult:
    """运行 LLM 语义审查.

    Args:
        content: 章节正文
        context_package: 上下文包（提供角色状态、剧情背景等）
        temperature: LLM 温度（默认 0.3，要求稳定输出）

    Returns:
        LLMAuditResult
    """

async def save_llm_audit(
    db: ReviewReportRepository,
    version_id: str,
    result: LLMAuditResult,
    report_id: str | None = None,
) -> None:
    """保存 LLMAuditResult 到 review_reports 表."""
```

## 数据模型

复用已有模型：
- `LLMAuditResult` — 审查结果
- `ReviewIssue` — 具体问题
- `ReviewCategory` — 12 个审查维度

## 测试要求

### Layer 1: JSON 解析
- [ ] 正常 JSON 解析
- [ ] markdown 代码块包裹的 JSON
- [ ] 无效 JSON → LLMResponseParseError

### Layer 2: 结果组装
- [ ] issues 正确解析
- [ ] dimension_scores 正确解析
- [ ] 文学性评分正确解析
- [ ] 无效 category 过滤
- [ ] 无效 severity 回退

### Layer 3: 保存验证
- [ ] Mock DB 保存调用

### Layer 4: 集成测试
- [ ] Mock LLM → 完整流程

## 验收标准（Acceptance Criteria）

- [ ] `pytest tests/test_llm_auditor.py -v` 全部通过
- [ ] 代码符合 CLAUDE.md 规范
- [ ] 全量测试通过，ruff 0 errors
- [ ] 生成了 tasks/013-llm-auditor-DONE.md 交接文件
