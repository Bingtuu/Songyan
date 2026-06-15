# Task 075: Checkpointer 抽象层重构

> **Phase**: V3.1 基建加固
> **优先级**: P1
> **依赖**: Task 073（截断重写策略已稳定）
> **预计工作量**: 小

---

## Goal

将 `AsyncSqliteSaver` 的硬编码依赖重构为可配置抽象层，根治 Windows 下 WAL 文件锁竞争导致的卡死/内存暴涨问题，并确保测试环境自动使用 `MemorySaver` 隔离。

## Context

Ch41-Ch50 验证过程中，Windows 环境下 `AsyncSqliteSaver` + `aiosqlite` + WAL 模式的高频 checkpoint 写入引发后台线程死锁，导致：
- 系统卡死无响应（误判为"内存挤爆"）
- 强制重启后 SQLite schema 损坏
- 残留 8 个僵尸 Python 进程（6 个 500MB+）

根本原因是**基础设施没有为测试/Windows 环境提供 Checkpointer 隔离层**，只能依赖人肉注释提醒（`test_ch41_50_validation.py` 注释写了用 MemorySaver 实际没用）。

本 Task 属于 V3.1 验证阶段的基建加固，不改任何业务工作流逻辑。

## In Scope（必须完成）

- [ ] 新增 `src/songyan/workflows/checkpointer.py` — Checkpointer 工厂 + 统一入口
- [ ] `settings.checkpointer_mode: Literal["memory", "sqlite"] = "sqlite"` 配置项
- [ ] 重构 `phase1_graph._get_checkpointer()` — 委托工厂，不改返回类型签名
- [ ] 重构 `phase1_graph.reset_checkpointer()` — 强化资源清理（gc.collect + 线程释放）
- [ ] `tests/conftest.py` — `test_db` fixture 自动设置 `checkpointer_mode = "memory"`
- [ ] 移除 `test_ch41_50_validation.py` 中对 `_get_checkpointer` 的临时 patch
- [ ] 新增 `tests/workflows/test_checkpointer.py` — 工厂模式 + 资源清理 + 配置切换测试
- [ ] `.env.example` 追加 `CHECKPOINTER_MODE=sqlite`

## Out of Scope（明确不做）

- 不引入 PostgreSQL / Redis 等外部 checkpointer
- 不改 `Phase1State` 定义
- 不改 `run_chapter_pipeline` / `run_project_pipeline` 等公共 API 签名
- 不做 LangGraph 版本升级

## 接口契约

```python
# src/songyan/workflows/checkpointer.py
from langgraph.checkpoint.base import BaseCheckpointSaver

async def get_checkpointer() -> BaseCheckpointSaver:
    """根据 settings.checkpointer_mode 返回对应实现.

    - "memory" → MemorySaver（测试/Windows 验证环境）
    - "sqlite" → AsyncSqliteSaver（生产环境）
    """
    ...

async def reset_checkpointer_instance(cp: BaseCheckpointSaver | None) -> None:
    """彻底释放 checkpointer 资源（关闭连接、清理线程引用、gc.collect）."""
    ...
```

```python
# src/songyan/config.py 新增字段
checkpointer_mode: Literal["memory", "sqlite"] = "sqlite"
```

## 数据模型

无新增 Pydantic 模型。

## 测试要求

### Layer 1: 模型/配置测试
- [ ] `CheckpointerMode` 枚举/配置可正确解析 `"memory"` 和 `"sqlite"`
- [ ] 非法值抛出 `ValidationError`

### Layer 2: 模块测试
- [ ] `get_checkpointer()` 在 `"memory"` 模式下返回 `MemorySaver` 实例
- [ ] `get_checkpointer()` 在 `"sqlite"` 模式下返回 `AsyncSqliteSaver` 实例
- [ ] `reset_checkpointer_instance()` 关闭连接后，`.conn` 不可用
- [ ] 连续两次 `get_checkpointer()` 在 sqlite 模式下返回同一单例（保持现有行为）

### Layer 3: 集成测试
- [ ] `test_db` fixture 自动切换后，`run_chapter_pipeline` 不产生 sqlite 文件锁
- [ ] `test_ch41_50_validation.py` 在不 patch `_get_checkpointer` 的情况下仍通过

## 验收标准（Acceptance Criteria）

- [ ] `pytest tests/workflows/test_checkpointer.py -v` 全部通过
- [ ] `pytest tests/integration/test_ch41_50_validation.py -v` 在不使用 `patch("_get_checkpointer")` 的情况下通过
- [ ] `pytest -v` 全量 1252 测试通过
- [ ] 代码符合 CLAUDE.md 规范（类型标注、单文件 < 400 行等）
- [ ] 不违反任何不可违背规则
- [ ] 更新了 `docs/STATUS.md`
- [ ] 生成了 `tasks/075-checkpointer-abstraction-DONE.md` 交接文件

## 参考文档

- `AGENTS.md` — 不可违背规则（不改公共 API 签名、不新增功能）
- `docs/STATUS.md` — V3.1 路线图
- `system_prompt/development-tech-plan-v3.md` — 技术栈约束
