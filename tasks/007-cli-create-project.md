# Task 007: CLI 创建项目

> **Phase**: Phase 1
> **优先级**: P0
> **依赖**: Task 004（Repository 层）, Task 005（Genre Profile 系统）, Task 006（CreativeModeProfile 系统）
> **预计工作量**: 中

---

## Goal

实现 `songyan create-project` 交互式 CLI 向导，让用户可以创建小说项目并保存到 SQLite，同时关联 GenreProfile 和 CreativeModeProfile。

## Context

Phase 1 的基础设施（模型、Schema、Repository、Genre/Mode 配置系统）已全部完成。Task 007 是 Phase 1 的最后一个任务，也是第一个面向用户的交互功能。用户将通过 CLI 向导输入项目信息，系统将其持久化到 SQLite，并为后续 Agent 工作流提供 `genre_id` + `mode_id` 的关联。

## In Scope（必须完成）

- [ ] 修改 `src/songyan/cli/main.py`：新增 `create-project` 命令
  - 交互式 8 步向导（使用 Click 的 `prompt`）
  - 第 1 步：选择创作模式（从 `list_creative_mode_profiles()` 动态加载）
  - 第 2 步：选择题材（从 `list_genre_profiles()` 动态加载）
  - 第 3 步：项目标题
  - 第 4 步：主角姓名（必填）
  - 第 5 步：主角背景（可选，默认空）
  - 第 6 步：核心钩子（可选，默认空）
  - 第 7 步：目标读者预期（可选，默认空）
  - 第 8 步：目标字数（可选，默认 100000）+ 基调（可选，默认 热血）
- [ ] 新增 `list-projects` 命令（简单列出 SQLite 中所有项目）
- [ ] CLI 自动确保 Schema 已初始化（调用 `init_schema()`）
- [ ] 生成 `project_id`（使用 `uuid.uuid4().hex`）
- [ ] 使用 `ProjectRepository.create()` 保存到 SQLite
- [ ] 新增 `tests/cli/test_cli.py`
- [ ] 更新 `docs/STATUS.md`
- [ ] 生成 `tasks/007-cli-create-project-DONE.md`

## Out of Scope（明确不做）

- 不实现 AI 实时建议（调用 LLM 生成推荐）
- 不实现 `edit-project`、`delete-project` 等其他项目管理命令
- 不实现 Writer / Reviewer / Agent 工作流
- 不修改 `ProjectSetting` 模型字段
- 不修改 `projects` 表结构
- 不实现配置文件导入/导出

## 接口契约

```python
# src/songyan/cli/main.py

import click

@click.group()
def cli() -> None:
    """Songyan（松烟）— 多 Agent 中文小说写作系统."""
    ...

@cli.command()
def create_project() -> None:
    """交互式创建小说项目."""
    ...

@cli.command()
def list_projects() -> None:
    """列出所有小说项目."""
    ...
```

### 交互流程

```
$ songyan create-project

? 选择创作模式:
  1. webnovel — 网文模式
  2. literary — 严肃文学模式
  3. hybrid — 混合模式
  > 1

? 选择题材:
  1. xuanhuan — 玄幻
  2. urban — 都市
  3. scifi — 科幻
  > 1

? 项目标题: 我的玄幻小说
? 主角姓名: 林凡
? 主角背景（可选）: 
? 核心钩子（可选）: 
? 目标读者预期（可选）: 
? 目标字数（默认 100000）: 
? 基调（默认 热血）: 

✓ 项目已创建: proj-xxx...
  模式: webnovel
  题材: xuanhuan
  标题: 我的玄幻小说
```

## 数据模型

本 Task 复用现有模型，不新增字段：

```python
class ProjectSetting(BaseModel):
    title: str | None = None
    genre_id: str
    mode_id: str = "webnovel"
    protagonist_name: str
    protagonist_background: str = ""
    core_hook: str = ""
    target_reader_expectation: str = ""
    taboos: list[str] = Field(default_factory=list)
    target_word_count: int = 100_000
    tone: str = "热血"
    reference_works: list[str] = Field(default_factory=list)
```

### Schema 约束

```sql
CREATE TABLE IF NOT EXISTS projects (
    project_id      TEXT PRIMARY KEY,
    title           TEXT,
    genre_id        TEXT NOT NULL,
    mode_id         TEXT DEFAULT 'webnovel',
    protagonist_name TEXT NOT NULL,
    protagonist_background TEXT DEFAULT '',
    core_hook       TEXT DEFAULT '',
    target_reader_expectation TEXT DEFAULT '',
    taboos          TEXT DEFAULT '[]',
    target_word_count INTEGER DEFAULT 100000,
    tone            TEXT DEFAULT '热血',
    reference_works TEXT DEFAULT '[]',
    created_at      TEXT DEFAULT (datetime('now'))
);
```

## 关键实现决策

1. **异步 Repository 的同步调用**：`ProjectRepository.create()` 是 `async` 方法，CLI 命令是同步的。使用 `asyncio.run(_create_project(...))` 包装。
2. **Schema 自动初始化**：CLI 启动时检查/初始化数据库 Schema，避免用户手动执行。
3. **选项列表动态加载**：创作模式和题材列表分别从 `list_creative_mode_profiles()` 和 `list_genre_profiles()` 加载，不硬编码。
4. **无效选择重试**：如果用户输入的序号超出范围，提示重新输入。
5. **project_id 生成**：使用 `uuid.uuid4().hex` 生成唯一 ID。

## 测试要求

### Layer 1: CLI 命令注册测试

- [ ] `songyan create-project` 命令可被引用（help 文本正确）
- [ ] `songyan list-projects` 命令可被引用（help 文本正确）

### Layer 2: create-project 交互测试

- [ ] 使用 Click `CliRunner` + `input` 模拟完整交互流程，项目成功保存到 DB
- [ ] 保存后可通过 `ProjectRepository.get()` 读取到正确的 `ProjectSetting`
- [ ] 保存的项目 `genre_id` 与输入一致
- [ ] 保存的项目 `mode_id` 与输入一致
- [ ] 保存的项目 `project_id` 不为空且唯一

### Layer 3: list-projects 测试

- [ ] 空数据库时 `list-projects` 输出提示信息
- [ ] 创建项目后 `list-projects` 显示项目信息

### 异常测试

- [ ] 数据库初始化失败时 CLI 给出明确错误信息
- [ ] 重复 project_id 不抛出裸异常（理论上 UUID 不会重复，但需处理）

## 验收标准（Acceptance Criteria）

- [ ] `pytest tests/cli/ -v` 全部通过
- [ ] `pytest tests/ -v` 全部通过
- [ ] `ruff check src/songyan/cli/ tests/cli/` 0 errors
- [ ] `songyan create-project --help` 显示正确帮助信息
- [ ] `songyan list-projects --help` 显示正确帮助信息
- [ ] 交互向导可完整运行并保存项目到 SQLite
- [ ] 创作模式和题材列表从 JSON 配置动态加载
- [ ] 单文件不超过 400 行（如 CLI 逻辑复杂可拆分为 `src/songyan/cli/commands.py`）
- [ ] 所有函数带类型标注
- [ ] 错误处理使用明确异常，不写裸 except
- [ ] 更新 `docs/STATUS.md`
- [ ] 生成 `tasks/007-cli-create-project-DONE.md`
- [ ] git commit + git push

## 参考文档

- `tasks/006-creative-mode-profile-system-DONE.md` — 上游 CreativeModeProfile 交接
- `tasks/005-genre-profile-system-DONE.md` — 上游 Genre Profile 交接
- `src/songyan/cli/main.py` — 现有 CLI 入口
- `src/songyan/db/repository.py` — ProjectRepository
- `src/songyan/db/migrations.py` — init_schema
- `src/songyan/models/project.py` — ProjectSetting 模型
- `src/songyan/genres/loader.py` — Genre Profile 加载器
- `src/songyan/creative_modes/registry.py` — CreativeModeProfile 注册表
- `docs/architecture/04-vibe-coding-engineering.md` — Task 007 原始拆解

---

## 下一步 AI Prompt

```text
你是 Songyan（松烟）项目的协作开发代理。

## 启动协议（必须执行）

请依次阅读：
1. CLAUDE.md
2. docs/INDEX.md
3. docs/STATUS.md
4. tasks/007-cli-create-project.md — 当前 Task 完整规格（必读）
5. tasks/006-creative-mode-profile-system-DONE.md — 上游 Task 交接

然后用 5-8 行总结任务边界，确认后再开始写代码。

## 当前代码基线

Git:     main 最新提交应包含 Task 006（CreativeModeProfile 系统）
测试:    196 passed（全量）
DB 测试: 51 passed
ruff:    0 errors

## 关键上下文

### 1. CLI 入口已有
位置：src/songyan/cli/main.py

当前只有一个空的 Click group：

@click.group()
def cli() -> None:
    """Songyan（松烟）— 多 Agent 中文小说写作系统."""
    pass

pyproject.toml 中已配置入口点：
songyan = "songyan.cli.main:cli"

### 2. ProjectRepository 已有
位置：src/songyan/db/repository.py

async def create(self, project: ProjectSetting, project_id: str) -> None
async def get(self, project_id: str) -> ProjectSetting | None

注意：create 是 async 方法，CLI 命令是同步的，需用 asyncio.run() 包装。

### 3. Schema 初始化已有
位置：src/songyan/db/migrations.py

async def init_schema(db_path=None) -> None

CLI 应在首次使用前自动调用 init_schema()。

### 4. Genre / Mode 加载器已有
位置：
- src/songyan/genres/loader.py — load_genre_profile(), list_genre_profiles()
- src/songyan/creative_modes/registry.py — load_creative_mode_profile(), list_creative_mode_profiles()

创作模式选择应从 list_creative_mode_profiles() 动态加载。
题材选择应从 list_genre_profiles() 动态加载。

### 5. ProjectSetting 模型已有
位置：src/songyan/models/project.py

必填字段：genre_id, protagonist_name
默认值字段：mode_id="webnovel", target_word_count=100000, tone="热血"

## 约束

- 不实现任务外内容（不做 Agent、不做 LLM 调用）
- 不改 Repository、Schema、DB connection、ProjectSetting 模型
- 所有函数带类型标注
- 单文件不超过 400 行
- 错误处理使用明确异常，不写裸 except

## Done When

- [ ] pytest tests/cli/ -v 全部通过
- [ ] pytest tests/ -v 全部通过
- [ ] ruff check src/songyan/cli/ tests/cli/ 0 errors
- [ ] songyan create-project 交互向导可完整运行
- [ ] songyan list-projects 可列出项目
- [ ] 项目成功保存到 SQLite
- [ ] 更新 docs/STATUS.md
- [ ] 生成 tasks/007-cli-create-project-DONE.md
- [ ] git commit + git push
```
