# Task 001: 初始化项目结构

> **Phase**: Phase 1 — 基础设施
> **优先级**: P0
> **依赖**: 无
> **预计工作量**: 小

---

## Goal

创建项目骨架，配置 pyproject.toml、.env.example、完整目录结构，确保 `pip install` 成功且项目可 import。

## Context

这是第一个 Task，所有后续开发的基础。需要先搭好项目结构，再开始写业务代码。

## In Scope（必须完成）

- [ ] `pyproject.toml` — 项目配置（依赖、脚本、pytest/ruff/mypy 配置）
- [ ] `.env.example` — 环境变量模板（已创建，确认内容正确）
- [ ] `.gitignore` — 忽略规则（已创建，确认内容正确）
- [ ] 完整目录结构（`src/songyan/` 下所有子目录和 `__init__.py`）
- [ ] `src/songyan/__init__.py` — 版本号
- [ ] `src/songyan/config.py` — Pydantic Settings 配置加载（已创建，确认内容正确）
- [ ] `src/songyan/cli/main.py` — CLI 入口（空实现，Click 框架）
- [ ] `tests/__init__.py`
- [ ] `tests/test_init.py` — 验证 import 成功
- [ ] `README.md` — 项目说明（可简化，后续扩充）
- [ ] `genres/` 目录（空，留给 Task 005）
- [ ] `creative_modes/` 目录（空，留给 Task 006）
- [ ] `prompts/` 目录（空，留给后续 Task）

## Out of Scope（明确不做）

- 任何业务代码（models、agents、db 等）
- 数据库 schema
- CLI 具体命令实现
- Genre Profile 配置文件（Task 005）
- CreativeModeProfile 配置文件（Task 006）
- 完整 README（先写骨架，后续补充）

## 接口契约

```python
# src/songyan/__init__.py
__version__ = "0.1.0"

# src/songyan/config.py
class Settings(BaseSettings):
    llm_api_key: str
    llm_base_url: str = "https://api.deepseek.com"
    llm_model: str = "deepseek-chat"
    llm_temperature: float = 0.7
    context_total_budget: int = 32_000
    context_generation_reserve: int = 8_000
    log_level: str = "INFO"
    database_url: str = "sqlite:///songyan.db"

# src/songyan/cli/main.py
@click.group()
def cli(): ...
```

## 数据模型

无新增模型。

## 测试要求

### Layer 1: 模型测试
- 无

### Layer 2: 模块测试
- [ ] `test_import_songyan` — `import songyan` 成功，`__version__` 存在
- [ ] `test_settings_load` — `Settings()` 可从 `.env` 加载配置
- [ ] `test_cli_exists` — `songyan.cli.main:cli` 可被引用

### Layer 3: 集成测试
- 无

## 验收标准（Acceptance Criteria）

- [ ] `pip install -e ".[dev]"` 成功
- [ ] `python -c "import songyan; print(songyan.__version__)"` 输出 `0.1.0`
- [ ] `pytest tests/test_init.py -v` 全部通过
- [ ] 目录结构与规范一致（`src/songyan/cli/`、`src/songyan/db/`、`src/songyan/models/`、`src/songyan/agents/`、`src/songyan/workflows/`、`src/songyan/utils/`、`src/songyan/creative_modes/`）
- [ ] `ruff check src/` 无错误（如已配置 ruff）
- [ ] 更新了 docs/STATUS.md（标记 Task 001 完成）
- [ ] 生成了 tasks/001-init-project-DONE.md 交接文件

## 参考文档

- `docs/architecture/04-vibe-coding-engineering.md` — Task 001 原始规格
- `system_prompt/development-tech-plan-v2.md` — 第 6 节项目结构
- `CLAUDE.md` — 代码规范（第 3.11 节）
