理解工具的原理，才能真正掌控工具的方向。

# NovelForge — 技术自学参考手册

## 监督 AI Coding 的速查指南

> **版本**: v1.0.0  
> **日期**: 2026-05-16  
> **用途**: 帮助非技术背景的项目负责人理解 NovelForge 使用的技术和框架，从而在 AI Coding 过程中有效监督开发质量  
> **阅读建议**: 先读第 1 章（项目逻辑），再根据兴趣深入各技术章节

---

## 目录

- [1. 项目基本逻辑（必 read）](#1-项目基本逻辑必-read)
  - [1.1 单章闭环流程](#11-单章闭环流程)
  - [1.2 Multi-Agent 协作模型](#12-multi-agent-协作模型)
  - [1.3 数据流向](#13-数据流向)
  - [1.4 监督检查清单](#14-监督检查清单)
- [2. Python 3.11+](#2-python-311)
- [3. Pydantic v2](#3-pydantic-v2)
- [4. LangGraph](#4-langgraph)
- [5. LangChain](#5-langchain)
- [6. litellm](#6-litellm)
- [7. SQLite](#7-sqlite)
- [8. Click](#8-click)
- [9. structlog](#9-structlog)
- [10. pytest + pytest-asyncio](#10-pytest--pytest-asyncio)
- [11. 概念速查表](#11-概念速查表)
- [12. 常见错误与排查](#12-常见错误与排查)

---

## 1. 项目基本逻辑（必 read）

### 1.1 单章闭环流程

这是 NovelForge Phase 1 的核心流程。理解这个流程，就能判断 AI 是否在正确方向上开发。

```
┌─────────────┐    ┌─────────────┐    ┌─────────────┐
│   Planner   │───▶│ ContextManager│───▶│   Writer    │
│  (规划)      │    │  (组装上下文)  │    │  (写初稿)    │
└─────────────┘    └─────────────┘    └──────┬──────┘
                                              │
┌─────────────┐    ┌─────────────┐    ┌─────┴─────┐
│ HumanConfirm│◀───│  Reviewer   │◀───┤  Revision  │
│  (人工确认)  │    │  (审查)      │    │  Handler   │
└─────────────┘    └─────────────┘    │ (自动修订)  │
                                      └─────┬─────┘
                                            │
                                      (最多2轮)
```

**六步流程**（你必须能复述这六步）：

| 步骤 | 谁做 | 做什么 | 产出 |
|------|------|--------|------|
| 1. 规划 | Planner | 收集项目设定，制定章节目标 | ChapterGoal |
| 2. 组装上下文 | ContextManager | 从数据库加载设定、角色、前文，组装成"写作上下文包" | ContextPackage |
| 3. 写初稿 | Writer | 按场景生成章节正文 | ChapterVersion (draft) |
| 4. 审查 | Reviewer | 检查设定一致性、角色行为、时间线、质量 | ReviewReport (issue 列表) |
| 5. 自动修订 | RevisionHandler | 按 issue 局部修改（只改有问题的部分） | ChapterVersion (revision) |
| 6. 人工确认 | HumanConfirm | 你决定：接受/编辑/退回/回退 | ChapterVersion (accepted) |

**关键规则**：
- 步骤 5 最多执行 2 轮，之后必须进入步骤 6
- Writer 只做初稿，RevisionHandler 只做修订，**职责不可混淆**
- 每一步的结果都要保存到 SQLite，不能丢

### 1.2 Multi-Agent 协作模型

NovelForge 使用 **Multi-Agent** 架构——不是一个大 AI 做所有事，而是多个专门的 AI 各做一部分。

**为什么不用一个大 AI？**
- 一个大 AI 容易"分心"：又要写又要审，结果写得时候想着审，审的时候想着写，两边都做不好
- 专门的分工更可靠：Writer 只管写，Reviewer 只管审，互不干扰
- 可替换：如果 Writer 写得不好，可以换 Writer 的 prompt 或模型，不影响 Reviewer

**四个核心 Agent + 两个流程节点**：

| 角色 | 职责 | 监督要点 |
|------|------|----------|
| **Planner** | 规划师。收集你的创意，制定每章目标 | 章节目标是否具体？是否有明确的事件和钩子？ |
| **Writer** | 作家。按场景写正文 | 是否遵守了设定？有没有乱加新设定？章末有钩子吗？ |
| **Reviewer** | 编辑。审查问题 | 是否找出了真正的矛盾？每个问题有原文证据吗？ |
| **ContextManager** | 资料管理员。组装上下文 | 出场角色是否齐全？前文摘要是否正确加载？ |
| **RevisionHandler** | 修理工。按 issue 局部修改 | 是否只改了有问题的部分？其他内容是否保持不变？ |
| **HumanConfirm** | 你的决策入口 | AI 是否给你看了审查结果？是否让你有 accept/edit/reject/back 四个选项？ |

### 1.3 数据流向

理解数据怎么流动，就能判断 AI 是否把东西存到了正确的地方。

```
你的输入（CLI）
    │
    ▼
SQLite 数据库（唯一事实源）
    │
    ├── 项目设定（projects 表）
    ├── 角色卡（characters 表）
    ├── 角色状态（character_states 表）
    ├── 章节版本（chapter_versions 表）
    ├── 审查报告（review_reports 表）
    ├── 章节指针（chapter_heads 表）
    └── 章节摘要（summaries 表）
    │
    ▼
LangGraph 工作流（只存 ID，不存内容）
    │
    ├── project_id
    ├── chapter_number
    ├── current_version_id（指向 chapter_versions）
    ├── review_report_id（指向 review_reports）
    ├── revision_round（0/1/2）
    └── status（当前步骤）
    │
    ▼
LLM（DeepSeek/OpenAI 等）
    │
    └── 只接收和返回文本，不保存任何状态
```

**铁律（你必须检查）**：
1. **SQLite 是唯一的数据库**——如果发现 AI 用了 PostgreSQL、Redis、Qdrant，立即叫停（Phase 1 不需要）
2. **LangGraph 只存 ID**——如果发现 state 里存了完整的章节正文或审查报告，立即纠正
3. **每个节点从 SQLite 加载数据**——如果 Agent 直接从内存里拿数据而不是查数据库，说明有问题

### 1.4 监督检查清单

在 AI Coding 过程中，你可以用以下清单检查每个开发阶段的质量：

**通用检查（任何时候）**：
- [ ] AI 是否只修改了当前 Task 相关的文件？
- [ ] 是否有新的依赖被引入（检查 pyproject.toml）？
- [ ] 是否有测试？测试是否能通过？
- [ ] 代码中是否有 `TODO` 或 `FIXME` 没处理？

**数据结构检查**：
- [ ] Pydantic model 是否有类型标注？
- [ ] 数据库操作是否集中在 repository.py？
- [ ] Agent 是否直接拼 SQL？（应该是 repository 负责）

**流程检查**：
- [ ] Writer 是否只做初稿，不做修订？
- [ ] Reviewer 输出的 issue 是否有 `evidence_quote`？
- [ ] RevisionHandler 是否只改有 issue 的部分？
- [ ] HumanConfirm 是否有 accept/edit/reject/back 四个选项？

---

## 2. Python 3.11+

### 基本概念

Python 是一种编程语言，3.11+ 表示需要 3.11 或更高版本。NovelForge 使用 Python 是因为：
- LangGraph 和 LangChain 都是 Python 生态的框架
- Python 的异步编程（async/await）适合处理 AI 调用这种 I/O 密集型任务

### 项目中用到的关键语法

**异步编程（async/await）**

```python
# async 表示这是一个异步函数，可以"等待"其他操作完成
async def write_chapter(context: ContextPackage) -> ChapterVersion:
    # await 表示"等这个操作完成后再继续"
    # 在等待期间，程序可以做其他事（比如处理另一个请求）
    result = await llm.generate(prompt)  # 等 AI 返回
    return ChapterVersion(content=result)
```

**项目中使用场景**：所有 Agent 的节点函数都是 `async def`，因为调用 LLM 是网络请求，需要时间，异步可以让程序更高效。

**监督要点**：如果 AI 写了普通 `def` 而不是 `async def` 来调用 LLM，说明没理解异步编程。

**类型标注（Type Hints）**

```python
def add(a: int, b: int) -> int:
    # a: int 表示 a 应该是整数
    # -> int 表示返回值是整数
    return a + b

# 可选类型
name: str | None = None  # name 可以是字符串或 None
```

**项目中使用场景**：所有 Pydantic model 的字段都有类型标注，所有函数参数和返回值都有类型标注。

**监督要点**：如果 AI 写的函数没有类型标注，要求补上。类型标注是代码质量的底线。

---

## 3. Pydantic v2

### 基本概念

Pydantic 是 Python 的数据验证库。简单说：**你定义一个数据结构，Pydantic 自动帮你检查数据是否符合要求**。

类比：就像 Excel 表格设置了"这一列只能是数字"，你输入文字就会报错。Pydantic 就是这个功能，但比 Excel 强大得多。

### 项目中使用方式

**定义数据模型**：

```python
from pydantic import BaseModel, Field

class ReviewIssue(BaseModel):
    """审查发现的问题"""
    issue_id: str                    # 必填，字符串
    severity: str                    # 必填，字符串
    evidence_quote: str              # 必填，必须有原文证据
    confidence: float = 1.0          # 可选，默认 1.0
    
    # 自定义验证：critical/major 必须有 evidence_quote
    @field_validator('evidence_quote')
    def check_evidence(cls, v, info):
        if info.data.get('severity') in ('critical', 'major') and not v:
            raise ValueError('critical/major issue 必须有 evidence_quote')
        return v
```

**使用方式**：

```python
# 创建对象（自动验证）
issue = ReviewIssue(
    issue_id="issue-1",
    severity="critical",
    evidence_quote="原文片段",  # 如果这里为空，会报错
)

# 从字典创建（LLM 返回 JSON 时用到）
data = {"issue_id": "1", "severity": "major", "evidence_quote": "xxx"}
issue = ReviewIssue.model_validate(data)  # 自动验证并转换

# 转 JSON（保存到数据库时用到）
json_str = issue.model_dump_json()
```

### 项目中使用场景

| 场景 | 怎么用 | 为什么 |
|------|--------|--------|
| LLM 输出解析 | LLM 返回 JSON → `Model.model_validate(json)` | 确保 LLM 输出格式正确，不会乱 |
| 数据保存 | `model.model_dump_json()` → 存 SQLite | 结构化数据方便查询和验证 |
| API 接口 | FastAPI（Phase 3）自动用 Pydantic 校验请求 | 防止无效数据进入系统 |
| 类型安全 | 所有函数参数用 Pydantic model 而不是裸 dict | 编译时就能发现类型错误 |

### 监督要点

- **所有数据模型必须是 Pydantic BaseModel**，不能用普通 dict 或 dataclass
- **LLM 输出必须经过 Pydantic 验证**——如果 AI 让 LLM 输出自由文本再用字符串解析，这是严重错误
- **版本用 v2 不是 v1**——Pydantic v1 和 v2 语法不兼容，确认 import 的是 `pydantic` 不是 `pydantic.v1`

---

## 4. LangGraph

### 基本概念

LangGraph 是一个**工作流编排框架**。它的作用是：把多个步骤（节点）按照一定规则（边）串联起来，形成一个可执行的流程图。

类比：就像工厂的生产流水线——原料（状态）从入口进入，经过加工站 A（节点 A）、加工站 B（节点 B），最后变成成品（输出）。LangGraph 就是这个流水线的控制系统。

**核心概念**：

| 概念 | 类比 | 说明 |
|------|------|------|
| **Graph** | 流水线整体 | 定义了所有节点和连接关系 |
| **Node** | 加工站 | 一个执行步骤（如 Writer、Reviewer） |
| **Edge** | 传送带 | 节点之间的连接，决定下一步去哪 |
| **State** | 流水线上的物料箱 | 保存当前流程的数据和状态 |
| **Checkpoint** | 快照 | 每隔一步拍个照，崩溃后能从快照恢复 |

### 项目中使用方式

**定义状态**（State）：

```python
from typing import TypedDict

class Phase1State(TypedDict):
    """Phase 1 的状态定义——只存 ID，不存完整对象"""
    project_id: str                    # 项目 ID
    chapter_number: int                # 当前章节号
    current_version_id: str | None     # 当前版本 ID
    review_report_id: str | None       # 审查报告 ID
    revision_round: int                # 修订轮次（0/1/2）
    status: str                        # 当前状态
```

**定义节点**（Node）：

```python
async def writer_node(state: Phase1State) -> Phase1State:
    """Writer 节点——从 state 取 ID，从数据库加载数据，生成草稿"""
    # 1. 从 state 取 ID
    version_id = state["current_version_id"]
    
    # 2. 从 SQLite 加载业务对象（不是从 state！）
    version = await db.get_version(version_id)
    context = await db.get_context(state["project_id"], state["chapter_number"])
    
    # 3. 执行业务逻辑
    new_version = await write_draft(context)
    
    # 4. 保存到 SQLite
    await db.save_version(new_version)
    
    # 5. 更新 state（只更新 ID）
    state["current_version_id"] = new_version.version_id
    state["status"] = "reviewing"
    return state
```

**定义图和路由**（Graph + Edges）：

```python
from langgraph.graph import StateGraph, END

# 创建图
builder = StateGraph(Phase1State)

# 添加节点
builder.add_node("writer", writer_node)
builder.add_node("reviewer", reviewer_node)
builder.add_node("revision_handler", revision_handler_node)
builder.add_node("human_confirm", human_confirm_node)

# 定义连接
builder.add_edge("writer", "reviewer")  # writer -> reviewer

# 条件路由：根据审查结果决定下一步
def review_router(state: Phase1State):
    report = db.get_report(state["review_report_id"])
    if report.has_critical or report.has_major:
        if state["revision_round"] < 2:
            return "revision_handler"  # 还有修订次数，去修订
        return "human_confirm"          # 修订次数用完了，去人工确认
    return "human_confirm"              # 没问题，去人工确认

builder.add_conditional_edges("reviewer", review_router, {
    "revision_handler": "revision_handler",
    "human_confirm": "human_confirm",
})

# 修订后回到 reviewer 重新审查
builder.add_edge("revision_handler", "reviewer")

# 人工确认后结束
builder.add_edge("human_confirm", END)

# 编译
app = builder.compile(checkpointer=sqlite_saver)
```

**运行**：

```python
# 启动流程
result = await app.ainvoke(
    {"project_id": "proj-1", "chapter_number": 1, "revision_round": 0, "status": "idle"},
    config={"configurable": {"thread_id": "proj-1-ch-1"}}
)
```

### 项目中使用场景

| 场景 | 怎么用 | 为什么 |
|------|--------|--------|
| 单章闭环 | 6 个节点串联成图 | 确保流程按正确顺序执行 |
| 修订循环 | reviewer → revision_handler → reviewer | 最多 2 轮的循环控制 |
| 崩溃恢复 | checkpoint 保存执行状态 | 程序崩溃后可从断点恢复 |
| 人工介入 | human_confirm 节点 | 在关键决策点暂停，等用户输入 |

### 监督要点

- **State 只存 ID**——如果 state 里出现了 `content: str`（完整正文），立即纠正
- **每个节点从数据库加载**——如果节点直接从 state 取正文而不是查 SQLite，说明理解有误
- **条件路由要覆盖所有情况**——如果 reviewer 之后可能去 revision 也可能去 human_confirm，两种路径都必须定义
- ** Checkpoint 要配置**——确保编译图时传了 `checkpointer` 参数

---

## 5. LangChain

### 基本概念

LangChain 是一个**大语言模型（LLM）的调用框架**。它提供统一的接口来调用不同厂商的 AI（DeepSeek、OpenAI、Claude 等），并提供一些辅助功能（如 prompt 模板、输出解析等）。

类比：LangChain 就像"万能遥控器"——不管是 DeepSeek 的 API 还是 OpenAI 的 API，都通过 LangChain 统一调用。

### 项目中使用方式

**调用 LLM 生成文本**：

```python
from langchain_openai import ChatOpenAI

# 初始化模型（通过 litellm 支持多种后端）
llm = ChatOpenAI(
    model="deepseek-chat",      # 模型名称
    api_key="sk-xxx",           # API 密钥
    base_url="https://api.deepseek.com",  # API 地址
    temperature=0.7,            # 创造性（0=保守，1=随机）
)

# 调用
response = await llm.ainvoke("写一段玄幻小说的开头")
print(response.content)
```

**结构化输出（与 Pydantic 结合）**：

```python
from langchain_core.output_parsers import PydanticOutputParser

# 定义期望的输出格式
parser = PydanticOutputParser(pydantic_object=ReviewReport)

# 在 prompt 中说明输出格式
prompt = f"""
请审查以下章节。
{parser.get_format_instructions()}

章节内容：{chapter_content}
"""

# 调用 + 自动解析
response = await llm.ainvoke(prompt)
report = parser.parse(response.content)  # 自动转为 ReviewReport 对象
```

### 项目中使用场景

| 场景 | 怎么用 | 为什么 |
|------|--------|--------|
| Writer 生成章节 | `llm.ainvoke(writer_prompt)` | 调用 AI 写小说 |
| Reviewer 审查 | `llm.ainvoke(reviewer_prompt)` + Pydantic 解析 | 让 AI 输出结构化审查报告 |
| Planner 制定目标 | `llm.ainvoke(planner_prompt)` + Pydantic 解析 | 让 AI 输出章节目标 |
| 多模型切换 | 通过 litellm 统一配置 | 以后可以换更好的模型而不改代码 |

### 与 LangGraph 的关系

LangChain 负责"调用 AI 做一件事"，LangGraph 负责"把多件事按顺序串起来"。

```
LangGraph (编排)
    │
    ├── Node 1: Writer
    │       │
    │       └── LangChain (调用 LLM 写章节)
    │
    ├── Node 2: Reviewer
    │       │
    │       └── LangChain (调用 LLM 审查)
    │
    └── Node 3: RevisionHandler
            │
            └── LangChain (调用 LLM 修改)
```

### 监督要点

- **所有 LLM 调用必须通过 LangChain**，不要直接用 `requests` 调 API
- **输出必须结构化**——Reviewer 的输出必须解析成 Pydantic model，不能是自由文本
- **Temperature 设置**：写作（Writer）用 0.7-0.9（有创造性），审查（Reviewer）用 0.3-0.5（更严谨）

---

## 6. litellm
n
### 基本概念

litellm 是一个**多模型路由库**。它提供一个统一的接口来调用 100+ 种不同的 LLM（DeepSeek、OpenAI、Claude、Gemini、本地模型等）。

类比： litellm 就像"国际电话卡"——你拨一个号码格式，它能自动帮你接到 DeepSeek、OpenAI 或任何其他服务商。

### 项目中使用方式

```python
# 配置 litellm（在 .env 或 config.py 中）
import litellm

# 调用 DeepSeek
response = await litellm.acompletion(
    model="deepseek/deepseek-chat",
    messages=[{"role": "user", "content": "写一段小说"}],
    api_key="sk-xxx",
    base_url="https://api.deepseek.com",
)

# 或者调用 OpenAI（只改 model 名，其他代码不变）
response = await litellm.acompletion(
    model="openai/gpt-4",
    messages=[{"role": "user", "content": "写一段小说"}],
    api_key="sk-xxx",
)
```

LangChain 内部可以通过 litellm 调用模型，所以你在代码里主要用 LangChain 的接口，litellm 在底层做路由。

### 项目中使用场景

| 场景 | 怎么用 | 为什么 |
|------|--------|--------|
| 支持多种模型 | 改 model 名即可切换 | 不绑定单一厂商，可换模型 |
| 统一接口 | 一套代码适配所有模型 | 减少维护成本 |
| Phase 1 基础 | 目前用 DeepSeek | 中文能力强，性价比高 |

### 监督要点

- **检查 .env 配置**——确认 `LLM_API_KEY` 和 `LLM_BASE_URL` 已配置
- **确认模型名称格式**——litellm 用 `provider/model` 格式，如 `deepseek/deepseek-chat`

---

## 7. SQLite

### 基本概念

SQLite 是一个**嵌入式数据库**。与 MySQL、PostgreSQL 不同，它不需要单独安装服务器，数据存在单个文件中（如 `novelforge.db`）。

类比：SQLite 就像 Excel 文件——一个文件就是整个数据库，双击就能打开，不需要装任何服务器软件。

### 项目中使用方式

**数据库连接**：

```python
import aiosqlite

# 连接数据库（文件不存在会自动创建）
async with aiosqlite.connect("novelforge.db") as db:
    # 执行 SQL
    await db.execute("INSERT INTO projects (id, title) VALUES (?, ?)", ("1", "我的小说"))
    await db.commit()
    
    # 查询
    async with db.execute("SELECT * FROM projects WHERE id = ?", ("1",)) as cursor:
        row = await cursor.fetchone()
        print(row)
```

**核心表结构**：

| 表名 | 存什么 | 监督要点 |
|------|--------|----------|
| `projects` | 项目设定（题材、主角、核心创意等） | 创建项目后必须有记录 |
| `characters` | 角色卡（名字、性格、背景等） | 每个角色一条记录 |
| `character_states` | 角色状态（每章更新） | 章与章之间状态应变化 |
| `chapter_versions` | 章节版本（draft/revision/accepted/edited） | 每次生成新记录，不覆盖 |
| `chapter_heads` | 章节指针（当前生效版本） | accepted 后必须更新 |
| `review_reports` | 审查报告（issue 列表） | 每章审查后必须有报告 |
| `summaries` | 章节摘要 | 人工确认后生成 |
| `foreshadowings` | 伏笔记录 | 埋下和回收都要记录 |

### 项目中使用场景

| 场景 | 怎么用 | 为什么 |
|------|--------|--------|
| 保存项目设定 | `INSERT INTO projects` | 长期存储 |
| 保存章节版本 | `INSERT INTO chapter_versions` | 版本链追溯 |
| 加载上下文 | `SELECT` 角色状态 + 前文摘要 | ContextManager 组装上下文包 |
| 更新章节指针 | `UPDATE chapter_heads` | 确认 accepted 后更新 |

### 数据事实源铁律

```
SQLite 是唯一长期事实源
    │
    ├── 项目设定 → projects 表
    ├── 角色 → characters 表
    ├── 版本 → chapter_versions 表
    └── 审查 → review_reports 表
    
LangGraph checkpoint 只存执行状态
    │
    ├── project_id
    ├── chapter_number
    ├── current_version_id  (只存 ID！)
    ├── review_report_id    (只存 ID！)
    ├── revision_round      (0/1/2)
    └── status
    
内存 (重启丢失)
    └── LLM 上下文窗口
```

### 监督要点

- **确认用了 SQLite 而不是 PostgreSQL/Qdrant/Redis**——Phase 1 只需要 SQLite
- **确认 repository.py 集中了所有 SQL**——Agent 不直接拼 SQL
- **确认外键约束生效**——schema.sql 里要有 `PRAGMA foreign_keys = ON`
- **确认有数据库初始化逻辑**——程序第一次运行能自动建表

---

## 8. Click

### 基本概念

Click 是 Python 的**命令行界面（CLI）框架**。它让你用装饰器语法快速定义命令行命令。

类比：Click 就像填写表格模板——你定义需要什么字段（选项、参数），Click 自动生成帮助信息、参数校验、错误提示。

### 项目中使用方式

```python
import click

@click.group()  # 命令组（主命令）
def cli():
    """NovelForge CLI"""
    pass

@cli.command()  # 子命令
@click.option("--project", required=True, help="项目 ID")
@click.option("--chapter", type=int, required=True, help="章节号")
def write_chapter(project: str, chapter: int):
    """写一章小说"""
    click.echo(f"正在写项目 {project} 的第 {chapter} 章...")
    # 调用工作流

@cli.command()
def create_project():
    """创建新项目（交互式向导）"""
    genre = click.prompt("题材", type=click.Choice(["玄幻", "都市", "科幻"]))
    title = click.prompt("书名")
    # ...

# 运行：novelforge write-chapter --project abc --chapter 1
```

### 项目中使用场景

| 命令 | 作用 | 什么时候用 |
|------|------|------------|
| `novelforge create-project` | 交互式创建项目 | 开始写新书 |
| `novelforge write-chapter --project X --chapter N` | 写第 N 章 | 日常写作 |
| `novelforge show-version --version ID` | 查看某个版本 | 检查审查结果 |
| `novelforge list-versions --project X --chapter N` | 列出历史版本 | 回退时查看 |

### 监督要点

- **确认有 help 信息**——运行 `novelforge --help` 应显示所有命令
- **确认参数有校验**——`--chapter` 应该是整数，`--project` 应该必填
- **确认交互式向导可用**——`create-project` 应该有 7 步交互

---

## 9. structlog

### 基本概念

structlog 是一个**结构化日志库**。与普通日志不同，它输出的是 JSON 格式，方便机器解析和分析。

普通日志：`2026-05-16 10:00:00 开始写第1章`
结构化日志：`{"timestamp": "2026-05-16T10:00:00", "event": "chapter_writing_started", "chapter": 1, "project": "abc"}`

### 项目中使用方式

```python
import structlog

logger = structlog.get_logger()

# 记录事件（结构化）
logger.info(
    "chapter_writing_started",
    chapter=1,
    project="proj-1",
    version_type="draft",
)

# 输出：
# {"timestamp": "2026-05-16T10:00:00", "event": "chapter_writing_started",
#  "chapter": 1, "project": "proj-1", "version_type": "draft"}
```

### 项目中使用场景

| 场景 | 记录什么 | 为什么 |
|------|----------|--------|
| 章节生成 | chapter, version_type, word_count | 追踪生成过程 |
| 审查 | issue_count, critical_count, major_count | 评估质量 |
| 修订 | patch_count, revision_round | 追踪修订次数 |
| 人工确认 | decision (accept/edit/reject) | 追踪人工干预 |

### 监督要点

- **确认没有 print**——所有日志都用 structlog，不用 `print()`
- **确认日志包含关键字段**——至少要有 `event` 和上下文字段（chapter, project 等）

---

## 10. pytest + pytest-asyncio

### 基本概念

pytest 是 Python 的**测试框架**。测试的作用：自动验证代码是否按预期工作。

类比：测试就像工厂的质量检测——每生产一批产品，自动检查是否符合标准。如果测试不通过，说明代码有问题。

pytest-asyncio 是 pytest 的插件，用于测试异步代码（async/await）。

### 项目中使用方式

```python
import pytest

# 普通测试
class TestReviewIssue:
    def test_critical_must_have_evidence(self):
        """critical issue 必须有 evidence_quote"""
        with pytest.raises(ValueError):
            ReviewIssue(
                issue_id="1",
                severity="critical",
                evidence_quote="",  # 空的，应该报错
            )

# 异步测试
@pytest.mark.asyncio
class TestWriter:
    async def test_generate_draft(self):
        """测试 Writer 能生成草稿"""
        context = create_test_context()
        goal = create_test_goal()
        
        version = await write_draft(context, goal)
        
        assert version.version_type == "draft"
        assert version.word_count > 1000
        assert "###" in version.content  # 有场景分隔
```

### 运行测试

```bash
# 运行所有测试
pytest tests/ -v

# 运行单个测试文件
pytest tests/test_writer.py -v

# 运行单个测试
pytest tests/test_writer.py::TestWriter::test_generate_draft -v

# 带覆盖率报告
pytest tests/ --cov=novelforge --cov-report=term-missing
```

### 项目中使用场景

| 测试文件 | 测试什么 | 为什么重要 |
|----------|----------|------------|
| `test_models.py` | Pydantic model 验证 | 确保数据结构正确 |
| `test_repository.py` | 数据库 CRUD | 确保数据能正确存取 |
| `test_writer.py` | Writer 生成 | 确保能写出章节 |
| `test_reviewer.py` | Reviewer 审查 | 确保能发现问题 |
| `test_revision_handler.py` | Patch 应用 | 确保只改有问题的地方 |
| `test_graph.py` | 端到端流程 | 确保整个闭环能跑通 |

### 监督要点

- **每个核心模块必须有测试**——如果 AI 写了新功能但没写测试，要求补
- **修改 schema 后必须补测试**——这是铁律
- **运行 `pytest` 应该全绿**——如果有测试失败，必须先修复再推进
- **覆盖率 > 60%**——运行 `pytest --cov` 检查

---

## 11. 概念速查表

### 11.1 项目专用术语

| 术语 | 含义 | 你的检查点 |
|------|------|------------|
| **单章闭环** | 一章从规划到确认的完整流程 | 是否六步都走完了？ |
| **Context Package** | 写作上下文包（分区组装） | 硬约束/软参考/前文/角色/伏笔 是否齐全？ |
| **Issue-Driven Patch** | 按问题局部修改 | 是否只改了有问题的部分？ |
| **版本链** | draft → revision → accepted | 每次修订是否创建了新版本？是否可回溯？ |
| **Evidence Quote** | 审查问题的原文证据 | 每个 critical/major 是否有原文引用？ |
| **结构化审查** | 输出固定格式的 issue 列表 | 不是自由文本，是 JSON/ Pydantic |
| **人工金标** | 人工独立打分，与 AI 对比 | 一致率是否 > 70%？ |

### 11.2 技术术语

| 术语 | 含义 | 在 NovelForge 中 |
|------|------|------------------|
| **Agent** | 一个专门的 AI 角色 | Writer、Reviewer 等 4 个核心 Agent |
| **Node** | LangGraph 的工作节点 | 每个 Agent 对应一个 node |
| **State** | 流程状态 | 只存 ID，不存完整对象 |
| **Checkpoint** | 执行快照 | 崩溃后恢复用 |
| **Prompt** | 给 AI 的指令 | 放在 prompts/ 目录 |
| **Schema** | 数据结构定义 | Pydantic model + 数据库表结构 |
| **Repository** | 数据访问层 | 集中所有 SQL，Agent 不直接查数据库 |
| **Async/Await** | 异步编程 | 所有节点函数都是 async |
| **TypedDict** | 类型化的字典 | Phase1State 的定义方式 |
| **Model Validate** | Pydantic 验证 | LLM 输出 → 验证 → 转为对象 |

### 11.3 各技术关系图

```
你（CLI 命令）
    │
    ▼
Click（命令解析）
    │
    ▼
LangGraph（流程编排）
    │
    ├── Node: Planner ──▶ LangChain ──▶ litellm ──▶ DeepSeek API
    ├── Node: Writer  ──▶ LangChain ──▶ litellm ──▶ DeepSeek API
    ├── Node: Reviewer──▶ LangChain ──▶ litellm ──▶ DeepSeek API
    └── ...
    │
    ▼
SQLite（数据存储）
    │
    └── aiosqlite（异步访问）
    
Pydantic v2（数据验证）——贯穿所有环节
structlog（日志记录）——贯穿所有环节
pytest（测试）——开发阶段验证
```

---

## 12. 常见错误与排查

### 12.1 AI 常见错误（你需要叫停的）

| # | 错误 | 为什么错 | 你应该说 |
|---|------|----------|----------|
| 1 | LangGraph state 存了完整正文 | state 应该只存 ID，数据存在 SQLite | "state 里不能有 content 字段，应该从数据库加载" |
| 2 | Writer 既写又改 | Writer 只做初稿，修订是 RevisionHandler 的事 | "Writer 只做 write_draft，不要加 revise 逻辑" |
| 3 | 用 PostgreSQL/Redis/Qdrant | Phase 1 只需要 SQLite | "Phase 1 用 SQLite，不要引入其他数据库" |
| 4 | LLM 输出用字符串解析 | 必须用 Pydantic model_validate | "LLM 输出要用 Pydantic 解析，不要自己 split" |
| 5 | Agent 直接拼 SQL | SQL 必须集中在 repository.py | "数据库操作移到 repository.py" |
| 6 | 没有测试 | 每个模块必须有最小测试 | "补一个测试验证这个功能" |
| 7 | 自动修订超过 2 轮 | 最多 2 轮，之后必须人工确认 | "revision_round 不能超过 2" |
| 8 | 覆盖了旧版本 | 每次修订创建新版本，不覆盖 | "用 INSERT 不是 UPDATE，版本链不能断" |
| 9 | 引入 Phase 2/3 功能 | 当前只做 Phase 1 | "这个功能属于 Phase 2，不要现在做" |
| 10 | 用 print 不用 structlog | 日志必须用 structlog | "换成 logger.info" |

### 12.2 你如何判断开发质量

**好的信号**（说明 AI 在做正确的事）：
- 每次只改 2-5 个文件
- 每个新功能都伴随一个新测试
- 代码里有类型标注
- 数据库操作都在 repository.py
- LangGraph state 里只有 ID 和轻量字段
- 运行 `pytest` 全绿

**坏的信号**（需要立即干预）：
- 一次改了 10+ 个文件
- 写了大量代码但没有测试
- 代码里没有类型标注
- Agent 直接 `import sqlite3` 拼 SQL
- LangGraph state 里有 `content: str` 或 `full_report: dict`
- 运行 `pytest` 有失败但没修复
- pyproject.toml 里出现了 Redis/Qdrant/PostgreSQL 的依赖

### 12.3 关键检查命令

你可以随时运行这些命令来检查项目状态：

```bash
# 检查项目结构
ls -la src/novelforge/

# 检查是否有不应出现的依赖
grep -E "redis|qdrant|postgres" pyproject.toml
# 应该没有任何输出

# 运行测试
pytest tests/ -v
# 应该全部通过

# 检查 LangGraph state 定义
grep -n "content\|full_report\|chapter_content" src/novelforge/workflows/phase1_graph.py
# 不应该匹配到 state 定义中的这些字段

# 检查 Agent 是否直接拼 SQL
grep -rn "sqlite3\|execute.*SELECT\|execute.*INSERT" src/novelforge/agents/
# 应该没有任何输出（SQL 应该在 repository.py）

# 检查是否有 print
grep -rn "print(" src/novelforge/
# 应该很少或没有（用 structlog 替代）

# 检查类型标注
grep -rn "def .*->" src/novelforge/agents/ | wc -l
# 应该有很多（每个函数都有）
```

---

> **本文档的定位**
>
> 这不是编程教程，而是**监督指南**。你不需要学会写代码，但需要理解：
> 1. 项目的基本流程（六步闭环）
> 2. 每个技术的作用（是做什么的）
> 3. 常见的错误信号（什么时候该叫停 AI）
> 4. 关键的检查命令（如何验证开发质量）
>
> 当你发现 AI 的行为与本文档描述不符时，就是干预的时机。
