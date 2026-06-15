# Task 009: CreativeDirector Agent — 完成报告

> **完成日期**: 2026-05-24
> **提交**: (待填写)

---

## 做了什么

实现了创作导演 Agent —— 基于 GoalPlanner 输出的 ChapterGoal，生成本章的 CreativeBrief（创作意图 + 张力地图 + 禁忌清单 + 允许裂隙）。

---

## 改了哪些主要文件

### 新增文件

| 文件 | 说明 |
|------|------|
| `src/songyan/agents/creative_director.py` | CreativeDirector Agent：`generate_creative_brief()` 主入口 + Prompt 渲染 + JSON 解析 + 张力验证 + forbidden_patterns 保底 |
| `prompts/creative_director.md` | CreativeDirector Prompt 模板（Jinja2 风格占位符） |
| `tests/test_creative_director.py` | CreativeDirector 测试（23 个测试） |
| `tasks/009-creative-director.md` | 本任务规格文档 |

### 修改文件

| 文件 | 修改 |
|------|------|
| `src/songyan/agents/__init__.py` | 导出 `generate_creative_brief` |
| `docs/STATUS.md` | 更新项目状态 |

---

## 如何运行

```bash
# 运行 CreativeDirector 测试
pytest tests/test_creative_director.py -v

# 运行全量测试
pytest tests/ -v

# 代码检查
ruff check src/ tests/
```

---

## 如何验证

```bash
pytest tests/ -v
# 期望：334 passed

ruff check src/ tests/
# 期望：All checks passed
```

---

## 还没做什么（明确边界）

- 不写正文（Writer 负责，Task 011）
- 不做审查（RuleAuditor/LLMAuditor 负责，Task 012-013）
- 不做修订（RevisionHandler 负责，Task 015）
- 不做状态结算（SettlementExtractor 负责，Task 016）
- ContextManager（Task 010）

---

## 接口使用示例

```python
from songyan.agents.creative_director import generate_creative_brief
from songyan.db.review_repo import CreativeBriefRepository
from songyan.models import ChapterGoal, GenreProfile, CreativeModeProfile, Character

# 加载数据（GoalPlanner 输出 + 项目数据）
chapter_goal = ...  # ChapterGoal
genre = ...         # GenreProfile
mode = ...          # CreativeModeProfile
characters = [...]  # list[Character]
db = CreativeBriefRepository()

# 生成创作导演简报
brief = await generate_creative_brief(
    db=db,
    project_id="proj_123",
    chapter_goal=chapter_goal,
    genre_profile=genre,
    mode_profile=mode,
    characters=characters,
    previous_summary="主角在拍卖会上与反派竞价...",
)

print(brief.creative_intent)       # "让读者感受到主角在绝境中爆发的爽感"
print(len(brief.required_tensions))  # 1-3
print(brief.forbidden_patterns)     # ["不要使用'冷笑'", ...]
print(brief.reader_contract)        # "读完本章，读者应该为主角的逆袭感到振奋"
```
