# Task 011: Writer Agent — 完成报告

> **完成日期**: 2026-05-24
> **提交**: (待填写)

---

## 做了什么

实现了 Writer Agent —— 接收 ContextPackage，调用 LLM 生成章节正文，保存为 ChapterVersion，并更新 ChapterHead。

---

## 改了哪些主要文件

### 新增文件

| 文件 | 说明 |
|------|------|
| `src/songyan/agents/writer.py` | Writer Agent：`write_chapter()` 主入口 + Prompt 渲染 + Scene 分割 + 字数统计 + 版本保存 |
| `prompts/writer.md` | Writer Prompt 模板（ContextPackage 全分区注入） |
| `tests/test_writer.py` | Writer 测试（37 个测试） |
| `tasks/011-writer.md` | 本任务规格文档 |

### 修改文件

| 文件 | 修改 |
|------|------|
| `src/songyan/agents/__init__.py` | 导出 `write_chapter` |

---

## 如何运行

```bash
# 运行 Writer 测试
pytest tests/test_writer.py -v

# 运行全量测试
pytest tests/ -v

# 代码检查
ruff check src/ tests/
```

---

## 如何验证

```bash
pytest tests/ -v
# 期望：407 passed

ruff check src/ tests/
# 期望：All checks passed
```

---

## 还没做什么（明确边界）

- 不做审查（RuleAuditor/LLMAuditor 负责，Task 012-014）
- 不做修订（RevisionHandler 负责，Task 015）
- 不做文学性诊断（LiteraryAuditor 负责，Task 014）
- 不做状态结算（SettlementExtractor 负责，Task 016）

---

## 接口使用示例

```python
from songyan.agents.writer import write_chapter
from songyan.db.repository import ChapterVersionRepository, ChapterHeadRepository
from songyan.models import ContextPackage

# 加载上下文包（ContextManager 输出）
ctx = ...  # ContextPackage

version = await write_chapter(
    db_version=ChapterVersionRepository(),
    db_head=ChapterHeadRepository(),
    project_id="proj_123",
    context_package=ctx,
    creative_brief_id="brief_001",
    temperature=0.8,
)

print(version.version_id)      # v-1-1-xxxxxxxx
print(version.word_count)      # 实际字数
print(len(version.scenes))     # 场景数
print(version.content[:200])   # 正文预览
```

---

## 设计要点

- **Prompt 渲染**：将 ContextPackage 7 个分区全部注入模板，缺失内容显示 "（无）"
- **正文提取**：去除 markdown 代码块、首尾说明文字
- **Scene 分割**：按 `### Scene N` 标记分割，无标记时整章为一个场景
- **字数统计**：中文字符 + 英文/数字词
- **版本管理**：自动递增 version_number，更新 ChapterHead.current_version_id
- **generation_metadata**：保存 context_snapshot（tokens/budget/assembled_at）+ prompt_length + scenes_count
- **温度策略**：Writer 0.8（比 GoalPlanner/CreativeDirector 的 0.7 更高，鼓励创造性）
