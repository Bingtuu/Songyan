# Task 015: RevisionHandler Agent — 完成报告

> **完成日期**: 2026-05-25
> **提交**: (待填写)

---

## 做了什么

实现了 RevisionHandler Agent —— issue-driven patch 修订，不整章重写。根据 RuleAuditor + LLMAuditor 产出的合并审查报告，对章节中有问题的部分进行局部修改，创建 `version_type="revision"` 的新版本。

---

## 改了哪些主要文件

### 新增文件

| 文件 | 说明 |
|------|------|
| `src/songyan/agents/revision_handler.py` | RevisionHandler：`run_revision()` 筛选 patchable issues → 排除 valuable_fissure → Prompt 渲染 → LLM 调用 → JSON 解析 → Patch 验证 → 代码从后往前应用 → `(RevisionOutput, revised_content)` + `save_revision_output()` 创建 revision 版本并更新 ChapterHead |
| `prompts/revision_handler.md` | RevisionHandler Prompt 模板（局部修改原则 + 保护内容 + JSON 输出格式） |
| `tests/test_revision_handler.py` | RevisionHandler 测试（38 个测试） |
| `tasks/015-revision-handler.md` | 本任务规格文档 |

### 修改文件

| 文件 | 修改 |
|------|------|
| `src/songyan/agents/__init__.py` | 导出 `run_revision`, `save_revision_output` |

---

## 如何运行

```bash
# 运行 RevisionHandler 测试
pytest tests/test_revision_handler.py -v

# 运行全量测试
pytest tests/ -v

# 代码检查
ruff check src/ tests/
```

---

## 如何验证

```bash
pytest tests/ -v
# 期望：536 passed

ruff check src/ tests/
# 期望：All checks passed
```

---

## 还没做什么（明确边界）

- 不做 LangGraph 编排循环（条件路由、最多 2 轮由 Task 019 负责）
- 不做 HumanConfirm 节点
- 不处理 `fix_type="rewrite_scene"`（整场景重写超出 patch 范围，留待人工）
- 不处理 `fix_type="register_setting"`（设定登记由 SettlementExtractor 负责，Task 016）
- 不自动触发 RuleAuditor + LLMAuditor 重审（编排器负责）

---

## 接口使用示例

```python
from songyan.agents.revision_handler import run_revision, save_revision_output
from songyan.db.repository import ChapterHeadRepository, ChapterVersionRepository
from songyan.models import MergedReviewReport, LiteraryAuditResult

# 运行修订
output, revised_content = await run_revision(
    content=chapter_version.content,
    report=merged_review_report,
    literary_result=literary_audit_result,  # 可选，用于保护 valuable_fissure
    temperature=0.3,
)

print(len(output.patches_applied))   # 应用的 patch 数
print(output.issues_fixed)            # 已修复的 issue_id 列表
print(output.issues_remaining)        # 未修复的 issue_id 列表

# 保存 revision 版本
new_version_id = await save_revision_output(
    version_db=ChapterVersionRepository(),
    head_db=ChapterHeadRepository(),
    project_id=project_id,
    chapter_number=chapter_number,
    output=output,
    revised_content=revised_content,
    parent_version=chapter_version,
)
```

---

## 设计要点

- **Patch 筛选**：使用 `MergedReviewReport.patchable_issues`（critical/major + fix_type="patch"），自动排除 minor/info 和非 patch 类型
- **valuable_fissure 保护**：从 `LiteraryAuditResult` 提取 `observation_type="valuable_fissure"` 且 `preserve=True` 的 `evidence_quote`，注入 Prompt 作为保护内容
- **从后往前应用 patch**：按 `original_text` 在 content 中最后出现的位置倒序排序，避免位置偏移
- **双来源正文**：LLM 返回的 `content` 字段 + 代码层 `_apply_patches()` 结果。若 patches 成功应用且结果与原文不同，优先使用代码层结果（确定性更高）
- **版本链**：revision 版本 `version_number = parent + 1`，`parent_version_id` 指向原版本，`version_type="revision"`
- **ChapterHead 状态**：修订后 `status="under_review"`，表示需要重新审查
- **温度策略**：0.3（精确修改）
