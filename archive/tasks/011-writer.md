# Task 011: Writer Agent

> **Phase**: Phase 2 — 写前管线 → 写作
> **优先级**: P0
> **依赖**: Task 008 (GoalPlanner), Task 009 (CreativeDirector), Task 010 (ContextManager)
> **预计工作量**: 中

---

## Goal

实现 Writer Agent —— 接收 ContextPackage，调用 LLM 生成章节正文，保存为 ChapterVersion，并更新 ChapterHead。

## Context

Writer 是写前管线的最终环节，也是写作阶段的起点。它接收 ContextManager 组装的 ContextPackage（含 ChapterGoal + CreativeBrief + 角色状态 + 剧情摘要 + 伏笔 + 规则），通过 Prompt 驱动 LLM 生成本章正文。

## In Scope（必须完成）

- [ ] `Writer` Agent：`write_chapter()` 主入口
- [ ] Prompt 渲染：将 ContextPackage 渲染为 Writer Prompt
- [ ] LLM 调用：复用 `call_llm()` 生成正文
- [ ] 输出解析：提取正文内容 + 字数统计
- [ ] Scene 分割：按标记（`### Scene`）或空行分割场景
- [ ] 版本保存：创建 ChapterVersion 并写入 DB
- [ ] 章节头更新：更新 ChapterHead 指向当前版本
- [ ] Prompt 模板：`prompts/writer.md`
- [ ] 测试：Prompt 渲染、输出解析、版本保存、集成测试

## Out of Scope（明确不做）

- 不做审查（RuleAuditor/LLMAuditor 负责，Task 012-014）
- 不做修订（RevisionHandler 负责，Task 015）
- 不做文学性诊断（LiteraryAuditor 负责，Task 014）
- 不做状态结算（SettlementExtractor 负责，Task 016）

## 接口契约

```python
async def write_chapter(
    db_version: ChapterVersionRepository,
    db_head: ChapterHeadRepository,
    project_id: str,
    context_package: ContextPackage,
    creative_brief_id: str | None = None,
    temperature: float = 0.8,
) -> ChapterVersion:
    """生成章节正文并保存为 ChapterVersion.

    Args:
        db_version: ChapterVersion 仓库
        db_head: ChapterHead 仓库
        project_id: 项目 ID
        context_package: 上下文包（来自 ContextManager）
        creative_brief_id: CreativeBrief ID（写入版本外键）
        temperature: LLM 温度（默认 0.8，比规划 Agent 更高）

    Returns:
        新创建的 ChapterVersion
    """
```

## 数据模型

复用已有模型：
- `ContextPackage` — Writer 输入
- `ChapterVersion` — Writer 输出
- `ChapterHead` — 章节头更新

## 测试要求

### Layer 1: Prompt 渲染
- [ ] ContextPackage 正确渲染到 Prompt
- [ ] 各分区内容正确注入

### Layer 2: 输出解析
- [ ] 正文提取
- [ ] Scene 分割
- [ ] 字数统计

### Layer 3: 版本管理
- [ ] 首章创建：version_number=1, 新建 ChapterHead
- [ ] 后续章节：version_number 递增
- [ ] ChapterHead 更新

### Layer 4: 集成测试
- [ ] Mock LLM → 完整流程 → DB 验证

## 验收标准（Acceptance Criteria）

- [ ] `pytest tests/test_writer.py -v` 全部通过
- [ ] 代码符合 CLAUDE.md 规范（类型标注、单文件 < 400 行等）
- [ ] 不违反任何不可违背规则
- [ ] 全量测试通过，ruff 0 errors
- [ ] 生成了 tasks/011-writer-DONE.md 交接文件
