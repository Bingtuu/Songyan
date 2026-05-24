# Task 005: Genre Profile 系统

> **Phase**: Phase 1
> **优先级**: P0
> **依赖**: Task 002（Pydantic 模型）, Task 004（Repository 层）
> **预计工作量**: 中

---

## Goal

实现 Genre Profile 的 JSON 配置文件与加载器，让项目可以通过 `genre_id` 加载题材规则，并为后续 Writer、RuleAuditor、ContextManager 注入题材约束打基础。

## Context

V1.0 要求每个项目必须关联一个 Genre Profile。Task 002 已提供 `GenreProfile` Pydantic 模型，Task 004 已提供 `ProjectRepository` 读取项目 `genre_id`。本 Task 只完成配置和加载层，不把规则注入 Agent 或 Prompt。

V1.0 必交付：`xuanhuan` 完整题材配置。
V1.0 预置但不验收：`urban`、`scifi` 基础题材配置。

## In Scope（必须完成）

- [ ] 新增 `genres/xuanhuan.json`：完整玄幻题材配置
- [ ] 新增 `genres/urban.json`：基础都市题材配置
- [ ] 新增 `genres/scifi.json`：基础科幻题材配置
- [ ] 新增 `src/songyan/genres/__init__.py`
- [ ] 新增 `src/songyan/genres/loader.py`
  - `load_genre_profile(genre_id: str) -> GenreProfile`
  - `list_genre_profiles() -> list[str]`
  - 可选：`GenreProfileLoader` 类封装缓存
- [ ] 新增 `tests/genres/test_loader.py`
- [ ] 更新 `docs/STATUS.md`
- [ ] 生成 `tasks/005-genre-profile-system-DONE.md`

## Out of Scope（明确不做）

- 不实现 Writer Prompt 注入
- 不实现 RuleAuditor 疲劳词检测
- 不实现 ContextManager 上下文组装
- 不新增或修改 `GenreProfile` 模型字段，除非现有模型无法表达任务要求
- 不实现用户自定义题材创建 CLI
- 不接入 SQLite 表结构变更

## 接口契约

```python
from pathlib import Path

from songyan.models.genre import GenreProfile


class GenreProfileError(ValueError):
    """Genre Profile 加载或校验失败."""


class GenreProfileNotFoundError(GenreProfileError):
    """请求的 genre_id 不存在."""


def load_genre_profile(genre_id: str) -> GenreProfile:
    """按 genre_id 从 genres/{genre_id}.json 加载题材配置."""


def list_genre_profiles() -> list[str]:
    """列出 genres/ 目录下可用的题材 ID，按字母序返回."""


class GenreProfileLoader:
    """带缓存的 Genre Profile 加载器."""

    @classmethod
    def load(cls, genre_id: str) -> GenreProfile: ...

    @classmethod
    def list_genres(cls) -> list[str]: ...

    @classmethod
    def clear_cache(cls) -> None: ...
```

### 路径约定

- JSON 配置放在仓库根目录 `genres/`
- 加载器代码放在 `src/songyan/genres/`
- 默认从仓库根目录的 `genres/` 加载，不从当前工作目录猜测
- 测试中允许通过 monkeypatch 覆盖加载目录

## 数据模型

本 Task 复用现有模型：

```python
class GenreProfile(BaseModel):
    id: str
    name: str
    language: str = "zh"
    chapter_types: list[str] = Field(default_factory=list)
    fatigue_words: list[str] = Field(default_factory=list)
    satisfaction_types: list[str] = Field(default_factory=list)
    has_numerical_system: bool = False
    has_power_scaling: bool = False
    pacing_rule: str = ""
    writer_rules: list[str] = Field(default_factory=list)
    reviewer_focus: list[str] = Field(default_factory=list)
    active_audit_dimensions: list[str] = Field(default_factory=list)
    taboos: list[str] = Field(default_factory=list)
```

## JSON 内容要求

每个 `genres/*.json` 必须包含以下字段：

- `id`
- `name`
- `language`
- `chapter_types`
- `fatigue_words`
- `satisfaction_types`
- `has_numerical_system`
- `has_power_scaling`
- `pacing_rule`
- `writer_rules`
- `reviewer_focus`
- `active_audit_dimensions`
- `taboos`

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

### `xuanhuan.json` 最低内容要求

- `has_numerical_system: true`
- `has_power_scaling: true`
- `chapter_types` 至少包含：`opening`、`cultivation_breakthrough`、`combat`、`sect_conflict`、`treasure_hunt`、`transition`
- `satisfaction_types` 至少包含：升级、打脸、夺宝、宗门压迫、师徒/传承、伏笔回收
- `fatigue_words` 至少 20 个中文疲劳词或短语
- `writer_rules` 至少 8 条
- `reviewer_focus` 至少 6 条
- `active_audit_dimensions` 必须包含 `genre_numerical`

### `urban.json` / `scifi.json` 最低内容要求

- 配置必须完整、可加载、可通过模型校验
- 可为基础版本，不要求达到玄幻配置的完整度
- `has_numerical_system` 与 `has_power_scaling` 根据题材设为合理默认值

## 测试要求

### Layer 1: 配置文件测试

- [ ] 三个 JSON 文件都是合法 JSON
- [ ] 三个 JSON 都可实例化为 `GenreProfile`
- [ ] JSON 中的 `id` 与文件名一致
- [ ] 必填字段全部存在
- [ ] `active_audit_dimensions` 全部来自 `ReviewCategory`

### Layer 2: 加载器测试

- [ ] `load_genre_profile("xuanhuan")` 返回 `GenreProfile`
- [ ] `load_genre_profile("urban")` 返回 `GenreProfile`
- [ ] `load_genre_profile("scifi")` 返回 `GenreProfile`
- [ ] `list_genre_profiles()` 返回 `["scifi", "urban", "xuanhuan"]` 或等价有序列表
- [ ] 无效 `genre_id` 抛出 `GenreProfileNotFoundError`，错误信息包含可用 genre
- [ ] 非法 JSON 或字段校验失败抛出 `GenreProfileError`
- [ ] 缓存可复用，`clear_cache()` 后可重新加载

### Layer 3: 集成测试

- [ ] 创建 `ProjectSetting(genre_id="xuanhuan", ...)` 后，可用该 `genre_id` 加载对应 Genre Profile
- [ ] `xuanhuan` 的 `fatigue_words`、`writer_rules`、`reviewer_focus` 非空

## 验收标准（Acceptance Criteria）

- [ ] `pytest tests/genres/ -v` 全部通过
- [ ] `pytest tests/ -v` 全部通过
- [ ] `ruff check src/songyan/genres/ tests/genres/` 0 errors
- [ ] 三个 JSON 配置文件有效
- [ ] `active_audit_dimensions` 使用 `ReviewCategory` 枚举值字符串
- [ ] `xuanhuan` 配置满足完整度要求
- [ ] 单文件不超过 400 行
- [ ] 不改 `models/genre.py`，除非有明确必要并在 DONE 中说明
- [ ] 更新 `docs/STATUS.md`
- [ ] 生成 `tasks/005-genre-profile-system-DONE.md`
- [ ] git commit + git push

## 参考文档

- `tasks/004-repository-layer-DONE.md` — 上游 Repository 交接
- `src/songyan/models/genre.py` — GenreProfile 模型
- `src/songyan/models/review.py` — ReviewCategory 枚举
- `docs/architecture/04-vibe-coding-engineering.md` — Task 005 原始拆解
- `docs/architecture/05-tech-reference.md` — Genre Profile loader 技术参考
- `system_prompt/development-tech-plan-v2.md` — Genre Profile 在 V1.0 中的位置

---

## 下一步 AI Prompt

```text
你是 Songyan（松烟）项目的协作开发代理。

## 启动协议（必须执行）

请依次阅读：
1. CLAUDE.md
2. docs/INDEX.md
3. docs/STATUS.md
4. tasks/005-genre-profile-system.md — 当前 Task 完整规格（必读）
5. tasks/004-repository-layer-DONE.md — 上游 Task 交接

然后用 5-8 行总结任务边界，确认后再开始写代码。

## 当前代码基线

Git:     main 最新提交应包含 Task 004（Repository 层）
测试:    122 passed（全量）
DB 测试: 51 passed
ruff:    0 errors

## 关键上下文

### 1. GenreProfile 模型已有
位置：src/songyan/models/genre.py

字段包括：
- id, name, language
- chapter_types, fatigue_words, satisfaction_types
- has_numerical_system, has_power_scaling
- pacing_rule, writer_rules, reviewer_focus
- active_audit_dimensions, taboos

除非现有模型无法表达任务要求，不要修改模型。

### 2. ReviewCategory 枚举已有
位置：src/songyan/models/review.py

active_audit_dimensions 必须使用 ReviewCategory 的字符串值，例如：
- world_consistency
- character_behavior
- timeline
- narrative_pacing
- narrative_hook
- genre_numerical

不要使用数字或随意标签。

### 3. 配置目录约定
根目录 genres/ 存放 JSON：
- genres/xuanhuan.json（完整配置）
- genres/urban.json（基础配置）
- genres/scifi.json（基础配置）

代码加载器放在：
- src/songyan/genres/__init__.py
- src/songyan/genres/loader.py

### 4. 本 Task 的核心决策
- JSON 配置是题材规则事实源，不在代码中硬编码题材内容
- load_genre_profile(genre_id) 返回 GenreProfile
- 无效 genre_id 抛明确异常，错误信息包含可用 genre
- xuanhuan 是完整配置，urban/scifi 只预置基础配置
- 不实现 Writer/Reviewer/ContextManager 注入逻辑

## 约束

- 不实现任务外内容（不做 Agent、不做 CLI、不做 Prompt 注入）
- 不改 Repository、Schema、DB connection
- 所有函数带类型标注
- 单文件不超过 400 行
- 错误处理使用明确异常，不写裸 except

## Done When

- [ ] pytest tests/genres/ -v 全部通过
- [ ] pytest tests/ -v 全部通过
- [ ] ruff check src/songyan/genres/ tests/genres/ 0 errors
- [ ] 三个 genres/*.json 可加载为 GenreProfile
- [ ] active_audit_dimensions 全部来自 ReviewCategory
- [ ] 更新 docs/STATUS.md
- [ ] 生成 tasks/005-genre-profile-system-DONE.md
- [ ] git commit + git push
```
