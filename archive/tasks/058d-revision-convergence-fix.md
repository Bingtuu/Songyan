# Task 058d: Revision 收敛性修复 + 058c 效果验证

> **Phase**: V3.0 Layer 2 — 核心验证层
> **优先级**: P1
> **依赖**: Task 058c（验证结果分析 + 关键问题修复）
> **预计工作量**: 小（~0.3~0.5 天）

---

## Goal

修复 RevisionHandler 引入新问题不被检测的代码 bug，并用 3 章小规模运行验证 058c 修复（Writer Prompt 威慑 + 字数审计 + 上下文膨胀缓解）的实际效果，为 V3.1 决策提供数据支撑。

---

## Context

058c 已完成 7 项修复，但 Revision 流程本身存在一个**明确的代码 bug**：

```python
# revision_handler/__init__.py
output = _build_revision_output(data, patchable_issues, content, new_version_id="")
# RevisionOutput.new_issues_introduced 被硬编码为 []
```

这意味着 RevisionHandler 修完一轮后，系统**完全不检测**是否引入了新的 AI 腔、疲劳词或结构破坏。这是"越修越烂"恶性循环的技术根因之一。

同时，058c 的 Writer Prompt 字数威慑和上下文膨胀修复的效果**尚未验证**。需要在真实或 mock 场景下跑 3 章，对比 058c 前后的关键指标变化。

本 Task 不做截断重写策略（涉及 workflow 状态机修改，风险高），只做**最小必要修复 + 验证实验**。

---

## In Scope（必须完成）

### P1 — `new_issues_introduced` 检测修复

- [ ] **对比 revision 前后的 RuleAuditResult**
  - 在 `_build_revision_output` 中，读取原始版本和 revision 版本的 RuleAuditResult
  - 对比 `ai_tell_count`、`fatigue_word_count`、`has_opening_hook`、`has_ending_hook` 等指标
  - 如果 revision 后任一指标恶化（增加或从 True 变为 False），生成对应的 `ReviewIssue` 并加入 `new_issues_introduced`

- [ ] **new_issues_introduced 进入第二轮 revision 优先级**
  - 如果 `new_issues_introduced` 非空且当前是 Round 1 → Round 2，将新问题合并到 `patchable_issues` 中
  - 位置：`review_merger.py` 的合并逻辑或 `_nodes.py` 的 `revision_handler_node` 状态流转

- [ ] **新增 `RevisionOutput.new_issues_introduced` 字段**
  - 当前 `RevisionOutput` 模型已有该字段，但 `_build_revision_output` 硬编码为空列表
  - 需要确认 `RevisionOutput` 模型定义，确保字段存在且类型正确

### P1 — 058c 效果验证实验

- [ ] **运行 3 章小规模验证**
  - 使用已有项目 `proj-e74ef1e4`，从 Ch31 开始（或删除 Ch2~Ch30 重新从 Ch2 开始）
  - 运行 3 章，记录：`budget_used`、`revision_rounds`、`word_count`、`rule_audit_score`、`llm_audit_issues`
  - 或者：mock 跑 3 章（使用 mock LLM），只验证 pipeline 链路和指标采集

- [ ] **对比 058b 基线数据**
  - 058b 基线（Ch2~Ch30 平均）：revision_rounds=1.80，budget_used=3.5x~4.3x，word_count CV=17.7%
  - 验证目标：观察 058c 修复后上述指标是否有改善趋势
  - 输出：`docs/review/058d_validation_report.md`

---

## Out of Scope（明确不做）

- 不做截断重写策略（2 轮未收敛时触发整章重写）— 风险高，留待 V3.1 根据 058d 验证结果决策
- 不做大规模重新生成（只跑 3 章验证，不是重跑 30 章）
- 不做 Writer Prompt 重写（058c 已做最小修改）
- 不做 RAG 修复
- 不做 Settlement 数据噪声修复

---

## 接口契约

### 修改点 1：`_build_revision_output` 新增 new_issues_introduced 检测

```python
# src/songyan/agents/revision_handler/__init__.py

def _build_revision_output(
    data: dict[str, Any],
    original_issues: list[ReviewIssue],
    content: str,
    new_version_id: str,
    # 058d 新增：传入原始和修订后的 RuleAuditResult
    original_rule_result: RuleAuditResult | None = None,
    revised_rule_result: RuleAuditResult | None = None,
) -> RevisionOutput:
    """从解析后的字典构建 RevisionOutput.
    
    新增：对比 revision 前后的 RuleAuditResult，检测新问题。
    """
    patches = _parse_patches(data)
    _, applied_patches = _apply_patches(content, patches)
    fixed, remaining = _determine_issues_fixed(applied_patches, original_issues)
    
    # 058d 新增：检测新问题
    new_issues: list[ReviewIssue] = []
    if original_rule_result and revised_rule_result:
        # AI 腔增加
        if revised_rule_result.ai_tell_count > original_rule_result.ai_tell_count:
            new_issues.append(ReviewIssue(...))
        # 疲劳词增加
        if revised_rule_result.fatigue_word_count > original_rule_result.fatigue_word_count:
            new_issues.append(ReviewIssue(...))
        # 钩子丢失
        if original_rule_result.has_opening_hook and not revised_rule_result.has_opening_hook:
            new_issues.append(ReviewIssue(...))
        if original_rule_result.has_ending_hook and not revised_rule_result.has_ending_hook:
            new_issues.append(ReviewIssue(...))
    
    return RevisionOutput(
        new_version_id=new_version_id,
        patches_applied=applied_patches,
        issues_fixed=fixed,
        issues_remaining=remaining,
        new_issues_introduced=new_issues,  # 058d：从 [] 改为实际检测
    )
```

### 修改点 2：`revision_handler_node` 传入 RuleAuditResult

```python
# src/songyan/workflows/_nodes.py

async def revision_handler_node(state: dict[str, Any]) -> dict[str, Any]:
    # ... 现有逻辑 ...
    
    # 058d 新增：获取原始 RuleAuditResult
    original_rule_report = await ReviewReportRepository().get_by_version(
        version.version_id, audit_type="rule"
    )
    original_rule_result = original_rule_report.rule_audit if original_rule_report else None
    
    output, revised_content = await run_revision(
        content=version.content,
        report=report,
        literary_result=literary_result,
    )
    
    # 058d 新增：对 revision 后的内容运行 RuleAudit，获取修订后的 RuleAuditResult
    # （可选：如果性能敏感，可以延迟到 _build_revision_output 中）
    
    # ... 截断检测 ...
    
    new_version_id = await save_revision_output(...)
    
    # 058d 新增：获取修订后的 RuleAuditResult
    revised_rule_report = await ReviewReportRepository().get_by_version(
        new_version_id, audit_type="rule"
    )
    revised_rule_result = revised_rule_report.rule_audit if revised_rule_report else None
    
    # 重新构建 RevisionOutput，传入前后 RuleAuditResult
    output = _build_revision_output(
        data=parse_llm_response(...),
        original_issues=report.patchable_issues,
        content=version.content,
        new_version_id=new_version_id,
        original_rule_result=original_rule_result,
        revised_rule_result=revised_rule_result,
    )
    
    return {
        "current_version_id": new_version_id,
        "revision_round": state["revision_round"] + 1,
        "_content_preservation_ratio": ratio,
        "_new_issues_introduced": [i.issue_id for i in output.new_issues_introduced],
        "status": "rule_auditing",
    }
```

---

## 数据模型

本 Task 主要复用现有模型，确认 `RevisionOutput` 字段：

```python
class RevisionOutput(BaseModel):
    """修订输出."""
    new_version_id: str
    patches_applied: list[Patch]
    issues_fixed: list[ReviewIssue]
    issues_remaining: list[ReviewIssue]
    new_issues_introduced: list[ReviewIssue] = Field(default_factory=list)  # 已有字段，当前被硬编码为 []
    content_preservation_ratio: float = 1.0
```

---

## 测试要求

### Layer 1: 模型测试
- [ ] `RevisionOutput` 带 `new_issues_introduced` 可正确实例化

### Layer 2: 模块测试
- [ ] `_build_revision_output` 在 revision 后 ai_tell_count 增加时正确检测新问题
- [ ] `_build_revision_output` 在 revision 后无恶化时返回空 `new_issues_introduced`
- [ ] `revision_handler_node` 返回的 state 包含 `_new_issues_introduced`

### Layer 3: 集成测试
- [ ] Mock 跑 1 章完整流程（含 revision），验证 `_new_issues_introduced` 被正确采集到 `ChapterRunLog`

---

## 验收标准

- [ ] `new_issues_introduced` 检测逻辑完成，revision 引入新问题被正确记录
- [ ] 3 章验证实验完成，报告写入 `docs/review/058d_validation_report.md`
- [ ] `pytest tests/ --ignore=tests/integration -q` 基线通过（≥1087 passed）
- [ ] 不违反 AGENTS.md 任何规则（尤其 #15 RevisionHandler 只做 patch，不整章重写）
- [ ] 更新了 `docs/STATUS.md`
- [ ] 生成了 `tasks/058d-revision-convergence-fix-DONE.md`

### 关键阈值

| 指标 | 修复前 | 修复后目标 |
|------|--------|-----------|
| `new_issues_introduced` 检测覆盖率 | 0%（硬编码为 `[]`） | 100%（实际检测） |
| 058c 验证实验 | 无 | 3 章对比数据 |

---

## 参考文档

- `tasks/058c-analysis-and-fixes-DONE.md` — 058c 交接报告
- `src/songyan/agents/revision_handler/__init__.py` — RevisionHandler 实现
- `src/songyan/workflows/_nodes.py` — revision_handler_node
- `src/songyan/workflows/review_merger.py` — ReviewMerger 合并逻辑
- `src/songyan/models/revision.py` — RevisionOutput 模型
- `docs/review/058c_issue_type_distribution.md` — Issues 分布分析
