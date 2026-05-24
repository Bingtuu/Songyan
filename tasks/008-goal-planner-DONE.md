# Task 008: GoalPlanner Agent — 完成报告

> **完成日期**: 2026-05-24
> **提交**: (待填写)

---

## 做了什么

实现了 Songyan 第一个 LLM Agent —— GoalPlanner（章节目标制定 Agent），同时建立了最小 LLM Client 基础设施。

---

## 改了哪些主要文件

### 新增文件

| 文件 | 说明 |
|------|------|
| `src/songyan/exceptions.py` | 自定义异常体系：`SongyanError`, `LLMError`, `LLMResponseParseError` |
| `src/songyan/llm/__init__.py` | LLM 模块入口 |
| `src/songyan/llm/retry.py` | 指数退避重试：`retry_with_backoff()`, `async_retry` 装饰器 |
| `src/songyan/llm/client.py` | LLM Client：`get_llm()` (ChatLiteLLM 工厂), `call_llm()` (带重试的调用包装) |
| `src/songyan/agents/__init__.py` | Agents 模块入口 |
| `src/songyan/agents/goal_planner.py` | GoalPlanner Agent：`define_chapter_goal()` 主入口 + Prompt 渲染 + JSON 解析 + 字段修正 |
| `prompts/goal_planner.md` | GoalPlanner Prompt 模板（Jinja2 风格占位符） |
| `tests/test_llm_client.py` | LLM Client 测试（12 个测试） |
| `tests/test_goal_planner.py` | GoalPlanner 测试（20 个测试） |
| `tasks/008-goal-planner.md` | 本任务规格文档 |

### 修改文件

| 文件 | 修改 |
|------|------|
| `pyproject.toml` | 新增 `langchain-litellm` 依赖 |
| `docs/STATUS.md` | 更新项目状态 |

---

## 如何运行

```bash
# 安装依赖
pip install -e ".[dev]"

# 运行 GoalPlanner 测试
pytest tests/test_goal_planner.py -v

# 运行 LLM Client 测试
pytest tests/test_llm_client.py -v

# 运行全量测试
pytest tests/ -v

# 代码检查
ruff check src/ tests/
```

---

## 如何验证

```bash
pytest tests/ -v
# 期望：311 passed

ruff check src/ tests/
# 期望：All checks passed
```

---

## 还没做什么（明确边界）

- 不调用真实 LLM API（测试全部用 Mock）
- 不做状态结算（Task 016 SettlementExtractor）
- 不做摘要生成（后续 task）
- 不做 ContextManager（Task 010）
- 不做 CreativeDirector（Task 009）
- 不做 Writer（Task 011）
- 多模型路由（V1.5+）
- 流式输出（V1.5+）
- Prompt 版本管理（V1.5+）

---

## 接口使用示例

```python
from songyan.agents.goal_planner import define_chapter_goal
from songyan.db.repository import ChapterGoalRepository
from songyan.models import ProjectSetting, GenreProfile, CreativeModeProfile

# 加载项目数据
project = ...  # ProjectSetting
genre = ...    # GenreProfile
mode = ...     # CreativeModeProfile
db = ChapterGoalRepository()

# 制定章节目标
goal = await define_chapter_goal(
    db=db,
    project_id="proj_123",
    project=project,
    genre_profile=genre,
    mode_profile=mode,
    chapter_number=3,
    previous_summary="主角在拍卖会上与反派竞价...",
)

print(goal.target_events)      # ['事件1', '事件2']
print(goal.word_count_target)  # 3000
print(goal.chapter_type)       # '升级'
```
