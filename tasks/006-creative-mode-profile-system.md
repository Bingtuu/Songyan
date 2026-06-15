# Task 006: CreativeModeProfile 系统

> **Phase**: Phase 1
> **优先级**: P0
> **依赖**: Task 002（Pydantic 模型）, Task 004（Repository 层）, Task 005（Genre Profile 系统）
> **预计工作量**: 中

---

## Goal

实现 CreativeModeProfile 的 JSON 配置文件与加载器/注册表，让项目可以通过 `mode_id` 加载创作模式规则，决定各阶段启用的 Agent、审查维度权重、修订策略与容错阈值。

## Context

V1.0 要求每个项目必须关联一个 CreativeModeProfile（通过 `mode_id`）。Task 002 已提供 `CreativeModeProfile` Pydantic 模型，Task 004 已提供 `ProjectRepository` 读取项目 `mode_id`。本 Task 只完成配置和加载层，不实现 Agent 工作流调度或 Prompt 注入。

V1.0 必交付：`webnovel` 完整创作模式配置（默认模式）。
V1.0 预置但不验收：`literary`、`hybrid` 基础创作模式配置。

本 Task 与 Task 005（Genre Profile 系统）高度对称，可参考其实现模式。

## In Scope（必须完成）

- [ ] 新增 `creative_modes/webnovel.json`：完整网文创作模式配置
- [ ] 新增 `creative_modes/literary.json`：基础严肃文学模式配置
- [ ] 新增 `creative_modes/hybrid.json`：基础混合模式配置
- [ ] 新增 `src/songyan/creative_modes/__init__.py`
- [ ] 新增 `src/songyan/creative_modes/registry.py`
  - `load_creative_mode_profile(mode_id: str) -> CreativeModeProfile`
  - `list_creative_mode_profiles() -> list[str]`
  - `CreativeModeProfileLoader` 类封装缓存（可选但推荐）
- [ ] 新增 `tests/creative_modes/test_registry.py`
- [ ] 更新 `docs/STATUS.md`
- [ ] 生成 `tasks/006-creative-mode-profile-system-DONE.md`

## Out of Scope（明确不做）

- 不实现 Agent 工作流调度（哪个阶段调用哪个 Agent）
- 不实现 Writer / RuleAuditor / LLMAuditor 中的 Prompt 注入
- 不新增或修改 `CreativeModeProfile` 模型字段，除非现有模型无法表达任务要求
- 不实现用户自定义创作模式创建 CLI
- 不接入 SQLite 表结构变更

## 接口契约

```python
from pathlib import Path

from songyan.models.creative_mode import CreativeModeProfile


class CreativeModeProfileError(ValueError):
    """CreativeModeProfile 加载或校验失败."""


class CreativeModeProfileNotFoundError(CreativeModeProfileError):
    """请求的 mode_id 不存在."""


def load_creative_mode_profile(mode_id: str) -> CreativeModeProfile:
    """按 mode_id 从 creative_modes/{mode_id}.json 加载创作模式配置."""


def list_creative_mode_profiles() -> list[str]:
    """列出 creative_modes/ 目录下可用的模式 ID，按字母序返回."""


class CreativeModeProfileLoader:
    """带缓存的 CreativeModeProfile 加载器."""

    @classmethod
    def load(cls, mode_id: str) -> CreativeModeProfile: ...

    @classmethod
    def list_modes(cls) -> list[str]: ...

    @classmethod
    def clear_cache(cls) -> None: ...
```

### 路径约定

- JSON 配置放在仓库根目录 `creative_modes/`
- 加载器代码放在 `src/songyan/creative_modes/`
- 默认从仓库根目录的 `creative_modes/` 加载，不从当前工作目录猜测
- 测试中允许通过 monkeypatch 覆盖加载目录

## 数据模型

本 Task 复用现有模型：

```python
class CreativeModeProfile(BaseModel):
    """创作模式配置文件 — 决定 Agent 组合与参数."""

    id: str
    name: str

    enabled_agents: dict[str, list[str]] = Field(default_factory=dict)
    # {
    #   "pre_write": ["goal_planner", "creative_director"],
    #   "write": ["writer"],
    #   "post_write": ["rule_auditor", "llm_auditor", "literary_auditor"],
    #   "revision": ["revision_handler"],
    #   "settlement": ["settlement_extractor"],
    # }

    audit_weights: dict[str, float] = Field(default_factory=dict)
    active_audit_dimensions: list[str] = Field(default_factory=list)
    revision_policy: str = "standard"  # standard | selective | minimal

    tolerance: dict[str, float] = Field(default_factory=dict)
    # {
    #   "max_ai_tells": 2.0,
    #   "max_fatigue_words": 3.0,
    #   "max_cliche_risk": 1.0,
    # }

    context_pruning_strategy: str = "default"  # default | character_focused | theme_focused
    success_metrics: dict[str, float] = Field(default_factory=dict)
```

## JSON 内容要求

每个 `creative_modes/*.json` 必须包含以下字段：

- `id`
- `name`
- `enabled_agents`
- `audit_weights`
- `active_audit_dimensions`
- `revision_policy`
- `tolerance`
- `context_pruning_strategy`
- `success_metrics`

### `active_audit_dimensions` 约束

必须使用 `ReviewCategory` 枚举值字符串，不允许数字或任意标签。允许值：

- `world_consistency`
- `character_behavior`
- `timeline`
- `new_setting_unregistered`
- `narrative_pacing`
- `narrative_hook`
- `info_dump`
- `dialogue_distinctness`
- `dialogue_subtext`
- `description_sensory`
- `show_dont_tell`
- `genre_numerical`

### `enabled_agents` 阶段约定

各阶段的 key 约定如下（value 为 Agent ID 列表）：

- `pre_write`：前置规划阶段
- `write`：写作阶段
- `post_write`：审查阶段
- `revision`：修订阶段
- `settlement`：结算阶段

可选 Agent ID：
`goal_planner`, `creative_director`, `writer`, `rule_auditor`, `llm_auditor`, `literary_auditor`, `revision_handler`, `settlement_extractor`

### `webnovel.json` 最低内容要求

- `enabled_agents` 必须启用全部标准 Agent：
  - `pre_write`: `["goal_planner", "creative_director"]`
  - `write`: `["writer"]`
  - `post_write`: `["rule_auditor", "llm_auditor", "literary_auditor"]`
  - `revision`: `["revision_handler"]`
  - `settlement`: `["settlement_extractor"]`
- `audit_weights` 至少包含 6 个维度的权重（值域 0.0–2.0）
- `active_audit_dimensions` 至少包含 8 个审查维度，必须包含 `narrative_pacing`、`narrative_hook`、`genre_numerical`
- `revision_policy` 必须为 `"standard"`
- `tolerance` 至少包含 `max_ai_tells`、`max_fatigue_words`、`max_cliche_risk`
- `success_metrics` 至少包含 3 个指标

### `literary.json` / `hybrid.json` 最低内容要求

- 配置必须完整、可加载、可通过模型校验
- 可为基础版本，不要求达到 webnovel 配置的完整度
- `literary` 模式的 `enabled_agents` 中 `post_write` 可额外包含 `polyphony_planner`（如果模型支持）
- `hybrid` 模式的 `revision_policy` 可设为 `"selective"`

## 测试要求

### Layer 1: 配置文件测试

- [ ] 三个 JSON 文件都是合法 JSON
- [ ] 三个 JSON 都可实例化为 `CreativeModeProfile`
- [ ] JSON 中的 `id` 与文件名一致
- [ ] 必填字段全部存在
- [ ] `active_audit_dimensions` 全部来自 `ReviewCategory`

### Layer 2: 加载器测试

- [ ] `load_creative_mode_profile("webnovel")` 返回 `CreativeModeProfile`
- [ ] `load_creative_mode_profile("literary")` 返回 `CreativeModeProfile`
- [ ] `load_creative_mode_profile("hybrid")` 返回 `CreativeModeProfile`
- [ ] `list_creative_mode_profiles()` 返回按字母序的可用模式列表
- [ ] 无效 `mode_id` 抛出 `CreativeModeProfileNotFoundError`，错误信息包含可用 mode
- [ ] 非法 JSON 或字段校验失败抛出 `CreativeModeProfileError`
- [ ] 缓存可复用，`clear_cache()` 后可重新加载

### Layer 3: 集成测试

- [ ] 创建 `ProjectSetting(mode_id="webnovel", ...)` 后，可用该 `mode_id` 加载对应 CreativeModeProfile
- [ ] `webnovel` 的 `enabled_agents`、`audit_weights`、`tolerance` 非空
- [ ] `webnovel` 的 `enabled_agents["post_write"]` 包含 `literary_auditor`

## 验收标准（Acceptance Criteria）

- [ ] `pytest tests/creative_modes/ -v` 全部通过
- [ ] `pytest tests/ -v` 全部通过
- [ ] `ruff check src/songyan/creative_modes/ tests/creative_modes/` 0 errors
- [ ] 三个 JSON 配置文件有效
- [ ] `active_audit_dimensions` 使用 `ReviewCategory` 枚举值字符串
- [ ] `webnovel` 配置满足完整度要求
- [ ] 单文件不超过 400 行
- [ ] 不改 `models/creative_mode.py`，除非有明确必要并在 DONE 中说明
- [ ] 更新 `docs/STATUS.md`
- [ ] 生成 `tasks/006-creative-mode-profile-system-DONE.md`
- [ ] git commit + git push

## 参考文档

- `tasks/005-genre-profile-system.md` — 对称任务（Genre Profile 系统）
- `tasks/005-genre-profile-system-DONE.md` — Genre Profile 交接报告
- `src/songyan/models/creative_mode.py` — CreativeModeProfile 模型
- `src/songyan/models/review.py` — ReviewCategory 枚举
- `docs/architecture/04-vibe-coding-engineering.md` — Task 006 原始拆解
- `system_prompt/development-tech-plan-v2.md` — CreativeModeProfile 在 V1.0 中的位置

---

## 下一步 AI Prompt

```text
你是 Songyan（松烟）项目的协作开发代理。

## 启动协议（必须执行）

请依次阅读：
1. CLAUDE.md
2. docs/INDEX.md
3. docs/STATUS.md
4. tasks/006-creative-mode-profile-system.md — 当前 Task 完整规格（必读）
5. tasks/005-genre-profile-system-DONE.md — 对称参考任务交接

然后用 5-8 行总结任务边界，确认后再开始写代码。

## 当前代码基线

Git:     main 最新提交应包含 Task 005（Genre Profile 系统）
测试:    158 passed（全量）
DB 测试: 51 passed
ruff:    0 errors

## 关键上下文

### 1. CreativeModeProfile 模型已有
位置：src/songyan/models/creative_mode.py

字段包括：
- id, name
- enabled_agents（阶段 → Agent 列表）
- audit_weights（维度 → 权重）
- active_audit_dimensions
- revision_policy
- tolerance（容错阈值）
- context_pruning_strategy
- success_metrics

除非现有模型无法表达任务要求，不要修改模型。

### 2. ReviewCategory 枚举已有
位置：src/songyan/models/review.py

active_audit_dimensions 必须使用 ReviewCategory 的字符串值。

### 3. 配置目录约定
根目录 creative_modes/ 存放 JSON：
- creative_modes/webnovel.json（完整配置）
- creative_modes/literary.json（基础配置）
- creative_modes/hybrid.json（基础配置）

代码加载器放在：
- src/songyan/creative_modes/__init__.py
- src/songyan/creative_modes/registry.py

### 4. 本 Task 的核心决策
- JSON 配置是创作模式规则事实源，不在代码中硬编码模式内容
- load_creative_mode_profile(mode_id) 返回 CreativeModeProfile
- 无效 mode_id 抛明确异常，错误信息包含可用 mode
- webnovel 是完整配置，literary/hybrid 只预置基础配置
- 不实现 Agent 工作流调度或 Prompt 注入

## 约束

- 不实现任务外内容（不做 Agent、不做 CLI、不做 Prompt 注入）
- 不改 Repository、Schema、DB connection
- 所有函数带类型标注
- 单文件不超过 400 行
- 错误处理使用明确异常，不写裸 except

## Done When

- [ ] pytest tests/creative_modes/ -v 全部通过
- [ ] pytest tests/ -v 全部通过
- [ ] ruff check src/songyan/creative_modes/ tests/creative_modes/ 0 errors
- [ ] 三个 creative_modes/*.json 可加载为 CreativeModeProfile
- [ ] active_audit_dimensions 全部来自 ReviewCategory
- [ ] 更新 docs/STATUS.md
- [ ] 生成 tasks/006-creative-mode-profile-system-DONE.md
- [ ] git commit + git push
```
