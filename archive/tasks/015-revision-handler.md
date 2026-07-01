# Task 015: RevisionHandler Agent

> **Phase**: Phase 2 — 修订环节
> **优先级**: P0
> **依赖**: Task 012 (RuleAuditor), Task 013 (LLMAuditor), Task 014 (LiteraryAuditor)
> **预计工作量**: 中

---

## Goal

实现 RevisionHandler Agent —— issue-driven patch 修订，不整章重写。根据 RuleAuditor + LLMAuditor 产出的审查报告，对章节中有问题的部分进行局部修改，创建 revision 版本。

## Context

RevisionHandler 是审查与修订闭环的核心环节，衔接 post_write 审核和重新审查：

```
Writer → RuleAuditor + LLMAuditor → MergedReviewReport
                                      ↓
                              RevisionHandler (本 Task)
                                      ↓
                              创建 revision 版本
                                      ↓
                              [重新审查：RuleAuditor + LLMAuditor]（最多 2 轮）
```

**关键特性**：
- 只修改有问题的部分，保留未修改内容一字不改
- 从后往前应用 patch，避免位置偏移
- 保护 valuable_fissure：不修改 LiteraryAuditor 标记为 preserve 的内容
- 最多 2 轮自动修订（由外部编排器控制轮次）

## In Scope（必须完成）

- [ ] `run_revision()` 主入口 — 筛选 patchable issues → 排除 valuable_fissure → Prompt 渲染 → LLM 调用 → JSON 解析 → Patch 验证 → 代码从后往前应用 → RevisionOutput
- [ ] Prompt 模板：`prompts/revision_handler.md`
- [ ] Patch 应用：`_apply_patches()` 从后往前字符串替换
- [ ] 版本创建：`save_revision_output()` 创建 `version_type="revision"` 的新版本
- [ ] ChapterHead 更新：修订后 `status="under_review"`
- [ ] 保护 valuable_fissure：从 `LiteraryAuditResult` 提取保护内容注入 Prompt
- [ ] 测试：Patch 筛选、保护内容提取、Prompt 渲染、Patch 应用、版本创建

## Out of Scope（明确不做）

- 不做 LangGraph 编排（条件路由、循环逻辑由 Task 019 负责）
- 不做 HumanConfirm 节点
- 不自动触发 RuleAuditor + LLMAuditor 重审（编排器负责）
- 不处理 `fix_type="rewrite_scene"`（整场景重写超出 patch 范围，留待人工）
- 不处理 `fix_type="register_setting"`（设定登记由 SettlementExtractor 负责，Task 016）

## 接口契约

```python
async def run_revision(
    content: str,
    report: MergedReviewReport,
    literary_result: LiteraryAuditResult | None = None,
    temperature: float = 0.3,
) -> tuple[RevisionOutput, str]:
    """运行修订 — 按 issue 局部 patch，不整章重写.

    Args:
        content: 原始章节正文
        report: 合并审查报告（含 patchable_issues）
        literary_result: 可选的 LiteraryAuditor 结果，用于保护 valuable_fissure
        temperature: LLM 温度（默认 0.3，精确修改）

    Returns:
        (RevisionOutput, revised_content)
    """

async def save_revision_output(
    version_db: ChapterVersionRepository,
    head_db: ChapterHeadRepository,
    project_id: str,
    chapter_number: int,
    output: RevisionOutput,
    revised_content: str,
    parent_version: ChapterVersion,
) -> str:
    """保存修订结果 — 创建 revision 版本并更新 ChapterHead.

    Returns:
        新创建的 version_id
    """
```

## 数据模型

复用已有模型：
- `RevisionInput` / `RevisionOutput` / `Patch` — `models/revision.py`
- `MergedReviewReport` / `ReviewIssue` — `models/review.py`
- `ChapterVersion` / `ChapterHead` — `models/chapter.py`
- `LiteraryAuditResult` / `LiteraryObservation` — `models/literary.py`

### Patchable Issues 筛选规则

```python
# 来自 MergedReviewReport.patchable_issues（已有 property）
report.patchable_issues  # severity in ("critical", "major") and fix_type == "patch"
```

### valuable_fissure 保护规则

```python
# 从 LiteraryAuditResult 提取保护内容
protected = [
    obs.evidence_quote for obs in literary_result.observations
    if obs.observation_type == "valuable_fissure" and obs.preserve
]
```

### 版本链规则

| 字段 | 原版本 | 新版本（revision） |
|------|--------|-------------------|
| version_type | draft / revision | revision |
| version_number | N | N + 1 |
| parent_version_id | X | 原版本.version_id |
| content | 原文 | patch 后正文 |

## 测试要求

### Layer 1: Patch 筛选
- [ ] critical/major + fix_type="patch" 被选中
- [ ] minor/info 被排除
- [ ] fix_type="rewrite_scene"/"confirm"/"register_setting" 被排除

### Layer 2: 保护内容提取
- [ ] valuable_fissure + preserve=True 被提取为保护内容
- [ ] non-valuable_fissure 被忽略
- [ ] literary_result=None 时不报错、不保护

### Layer 3: Prompt 渲染
- [ ] 原始正文注入（截断到 MAX_CONTENT_LENGTH）
- [ ] patchable issues 注入
- [ ] 保护内容注入

### Layer 4: Patch 应用
- [ ] 单个 patch 正确替换
- [ ] 多个 patch 从后往前应用（位置不偏移）
- [ ] patch 无匹配时保留原文

### Layer 5: 版本创建
- [ ] 创建 version_type="revision" 的版本
- [ ] version_number = parent + 1
- [ ] parent_version_id 指向原版本
- [ ] ChapterHead.current_version_id 更新
- [ ] ChapterHead.status 更新为 "under_review"

### Layer 6: 集成测试
- [ ] Mock LLM → 完整流程
- [ ] 无 patchable issues 时返回空 patches
- [ ] 无效 JSON → LLMResponseParseError

## 验收标准（Acceptance Criteria）

- [ ] `pytest tests/test_revision_handler.py -v` 全部通过
- [ ] 代码符合 CLAUDE.md 规范（类型标注、单文件 < 400 行等）
- [ ] 不违反任何不可违背规则
- [ ] 全量测试通过，ruff 0 errors
- [ ] 生成了 `tasks/015-revision-handler-DONE.md` 交接文件

## 参考实现

参考以下已有 Agent 的结构：
- `src/songyan/agents/llm_auditor.py` — Prompt 渲染 + LLM 调用 + JSON 解析 + 结果组装
- `src/songyan/agents/writer.py` — ChapterVersion 创建 + ChapterHead 更新
- `tests/test_llm_auditor.py` — 测试结构（Mock LLM、Prompt 验证、结果组装）

### 已有相关文件路径

```
src/songyan/models/revision.py            # RevisionInput, RevisionOutput, Patch
src/songyan/models/review.py              # MergedReviewReport, ReviewIssue, ReviewCategory
src/songyan/models/chapter.py             # ChapterVersion, ChapterHead
src/songyan/models/literary.py            # LiteraryAuditResult, LiteraryObservation
src/songyan/db/repository.py              # ChapterVersionRepository, ChapterHeadRepository
src/songyan/db/review_repo.py             # LiteraryObservationRepository
src/songyan/llm/client.py                 # call_llm()
src/songyan/llm/parsing.py                # parse_llm_response()
```
