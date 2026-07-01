# Task 020-B: 评测集基础设施（Runner + 种子项目）

> **Phase**: Phase 4 — 评测与优化
> **优先级**: P0
> **依赖**: Task 001 ~ 019（全部完成），Task 020-A（集成测试基线稳定）
> **预计工作量**: 中
> **前置子任务**: 020-A（Mock 端到端集成测试 + Checkpoint 恢复）

---

## Goal

构建可重复运行的评测基础设施：实现 `evals/runner.py` 评测运行器，准备 3 个预置种子项目配置（JSON）和人工种子章节，使外部能够通过一条命令完成"导入项目 → 写入种子 → 生成下一章 → 收集原始结果"的完整流程。

## Context

020-A 已验证工作流各节点链路正确。本 Task 的责任是**让评测可重复、可配置、可扩展**：

- 评测不能依赖人工在 CLI 里一步步创建项目
- 种子项目配置必须版本化、可复用、可分享
- 种子章节（Chapter 1）是触发 Chapter 2 生成的前提
- 评测 runner 是 020-C 收集验收指标的基础设施底座

本 Task **只使用 mock LLM**（和 020-A 相同策略），真实 LLM 评测在 V1.0 验收阶段手动执行。

---

## In Scope（必须完成）

### 1. 评测 Runner 核心实现

- [ ] 创建 `evals/runner.py`
- [ ] 实现 `async def run_seed_project(project_config_path: str, seed_chapter_path: str, output_dir: str) -> EvaluationResult`
  - 步骤 1：读取项目配置 JSON，调用 `ProjectRepository().create()` 导入 SQLite
  - 步骤 2：读取种子章节 Markdown/TXT，包装为 `ChapterVersion(version_type="accepted")` 作为 Chapter 1 写入 DB，并更新 `chapter_heads`
  - 步骤 3：调用 `run_chapter_pipeline(project_id, chapter_number=2, thread_id=...)` 生成 Chapter 2（mock LLM 模式下），流程会在 `human_confirm` 处中断
  - 步骤 3b：调用 `resume_human_confirm(thread_id, "accept")` 自动接受并继续执行 `settlement_extractor` 和 `summary_writer`
  - 步骤 4：收集原始结果（version_id、merged_review_report_id、settlement_id、summary_id、duration）
  - 步骤 5：输出 `EvaluationResult` 并写入 `output_dir/result.json`

- [ ] 实现 `async def import_seed_project(config_path: str) -> str`
  - 解析种子项目 JSON，生成 `project_id`（`uuid.uuid4().hex[:12]` 或 `new_id("proj")`）
  - 创建 `ProjectSetting` → `ProjectRepository().create(project, project_id)`
  - 遍历 `characters`，为每个角色：
    - 创建 `Character` → `CharacterRepository().create(char)`
    - 将 `initial_state` 的每个 field 转为 `CharacterState` 快照写入 `character_states` 表（`source_version_id` 暂用 `"seed"`）
  - 遍历 `initial_settings`，每个转为 `NewSetting` → `SettingSnapshotRepository().create(setting, project_id, setting_id)`
  - 若 `numerical_system` 存在，为每个角色的数值属性创建初始 `NumericalLedger` 记录（`opening_value` 取 `initial_state` 中对应字段，`closing_value` 相同，`increments`/`decrements` 为空）
  - 返回 `project_id`

- [ ] 实现 `async def import_seed_chapter(project_id: str, chapter_path: str, chapter_number: int = 1) -> str`
  - 读取种子章节正文，计算字数，创建 `ChapterVersion(version_type="accepted")` + `ChapterHead`
  - 为种子章节生成/读取 `ChapterSummary` 并写入 `summaries` 表（Chapter 2 的 goal_planner 和 context_manager 依赖此前置摘要）
  - 返回 `version_id`

- [ ] 实现 CLI 入口 `evals/__main__.py`：
  ```bash
  python -m evals --seed-config evals/seeds/xuanhuan_webnovel.json \
                  --seed-chapter evals/seeds/chapters/xuanhuan_ch1.md \
                  --output-dir evals/output/xuanhuan_run_01 \
                  --auto-accept
  ```

### 2. 种子项目配置

- [ ] 创建 `evals/seeds/` 目录结构：
  ```
  evals/seeds/
  ├── xuanhuan_webnovel.json      # 种子 1：玄幻 + 网文（完整配置，主验收）
  ├── urban_hybrid.json           # 种子 2：都市 + 混合（验证跨题材）
  ├── scifi_webnovel.json         # 种子 3：科幻 + 网文（验证跨题材）
  └── chapters/
      ├── xuanhuan_ch1.md         # 人工撰写的 Chapter 1（2000~4000 字）
      ├── urban_ch1.md
      └── scifi_ch1.md
  ```

- [ ] 种子项目 JSON  schema（`SeedProjectConfig`）：
  ```python
  class SeedProjectConfig(BaseModel):
      project_name: str
      genre_id: str          # "xuanhuan" | "urban" | "scifi"
      mode_id: str           # "webnovel" | "hybrid" | "literary"
      description: str
      characters: list[SeedCharacter]
      initial_settings: list[SeedSetting]
      numerical_system: SeedNumericalSystem | None  # 玄幻必填
  ```

- [ ] **P0 — 种子 1（xuanhuan + webnovel）必须包含：**
  - 3~5 个有完整档案的角色（含境界/功法/关系网）
  - 10+ 条世界设定（宗门、地图、修炼体系）
  - 数值体系（境界等级、灵气值公式）
  - 2000~4000 字人工种子 Chapter 1

- [ ] **P1 — 种子 2 / 3（可简化）：**
  - 2~3 个角色
  - 5+ 条世界设定
  - 对应题材特征（都市：职场/异能规则；科幻：科技设定/外星文明）
  - 500~1000 字简化版 Chapter 1（在 020-C 前补齐即可）

### 3. 人工种子章节

- [ ] 每章 2000~4000 字中文正文
- [ ] 包含：场景描写、对话、动作、至少 1 个悬念钩子
- [ ] 格式：Markdown，文件名 `xxx_ch1.md`
- [ ] 内容必须与种子项目配置中的角色和设定一致（不引入未登记的新设定，或正确标记 `[[新设定:描述]]`）

### 4. 评测原始结果持久化

- [ ] `output_dir/result.json`：EvaluationResult 的 JSON 序列化
- [ ] `output_dir/chapter_v2.md`：生成的 Chapter 2 正文
- [ ] `output_dir/review_report.json`：MergedReviewReport 原始数据
- [ ] `output_dir/settlement.json`：StateSettlement 原始数据
- [ ] `output_dir/summary.json`：ChapterSummary 原始数据

---

## Out of Scope（明确不做）

- 真实 LLM 调用跑评测（本 Task 只用 mock，真实 LLM 评测在 V1.0 验收阶段手动执行）
- 验收指标的计算与达标判断（属于 020-C）
- 性能基准测试（属于 020-C）
- 连续多章生成（V1.0 只验证单章闭环）
- Web UI / TUI 展示评测结果
- 种子项目配置的 GUI 编辑器
- PostgreSQL / Redis / Qdrant

---

## 接口契约

```python
# evals/runner.py

class SeedProjectConfig(BaseModel):
    """种子项目配置."""
    project_name: str
    genre_id: str
    mode_id: str
    description: str
    characters: list[SeedCharacter]
    initial_settings: list[SeedSetting]
    numerical_system: SeedNumericalSystem | None = None

class SeedCharacter(BaseModel):
    name: str
    role: str          # "protagonist" | "supporting" | "antagonist"
    age: int | None = None
    description: str
    initial_state: dict[str, str | int | float]

class SeedSetting(BaseModel):
    setting_key: str
    setting_name: str   # 映射到 NewSetting.setting_name / DB setting_snapshots.setting_name
    description: str
    source_quote: str = ""  # 映射到 NewSetting.source_quote（种子章节中引用此设定的原文片段，可空）

class SeedNumericalSystem(BaseModel):
    name: str
    levels: list[str]
    base_unit: str
    formula_hint: str

class EvaluationResult(BaseModel):
    """单次评测原始结果."""
    project_id: str
    project_name: str
    genre_id: str
    mode_id: str
    seed_config_path: str
    seed_chapter_path: str
    success: bool
    chapter_version_id: str
    merged_review_report_id: str
    settlement_id: str
    summary_id: str
    duration_ms: int
    metrics: dict[str, float | int]   # 原始指标（由 020-C 填充具体计算逻辑）
    logs: list[str]
    output_dir: str

async def run_seed_project(
    project_config_path: str,
    seed_chapter_path: str,
    output_dir: str,
    auto_accept: bool = True,
) -> EvaluationResult:
    """运行单个种子项目的评测（mock LLM 模式）.

    1. 导入项目配置到 SQLite
    2. 将种子章节作为 chapter 1 写入 DB（含 summary）
    3. 调用 run_chapter_pipeline 生成 chapter 2（在 human_confirm 中断）
    4. 若 auto_accept=True，调用 resume_human_confirm("accept") 继续 settlement/summary
    5. 收集原始结果并持久化
    6. 返回 EvaluationResult
    """
    ...

async def import_seed_project(config_path: str) -> str:
    """导入种子项目配置，返回 project_id."""
    ...

async def import_seed_chapter(
    project_id: str,
    chapter_path: str,
    chapter_number: int = 1,
) -> str:
    """导入种子章节，返回 version_id."""
    ...
```

---

## 数据模型

本 Task **新增**以下 Pydantic 模型（放在 `evals/models.py` 或 `evals/runner.py` 顶部）：

```python
class SeedProjectConfig(BaseModel): ...
class SeedCharacter(BaseModel): ...
class SeedSetting(BaseModel): ...
class SeedNumericalSystem(BaseModel): ...
class EvaluationResult(BaseModel): ...
```

**约束**：
- 单文件不超过 400 行，超过则拆为 `evals/models.py`
- 所有字段带类型标注
- JSON 序列化/反序列化通过 Pydantic v2 原生支持

---

## 测试要求

### Layer 1: 导入测试
- [ ] `import_seed_project("evals/seeds/xuanhuan_webnovel.json")` 成功返回 `project_id`
- [ ] 导入后 DB 中角色数量与 JSON 一致
- [ ] 导入后 DB 中设定数量与 JSON 一致
- [ ] 无效 JSON / 缺失必填字段 → 抛出明确异常

### Layer 2: 种子章节导入测试
- [ ] `import_seed_chapter(project_id, "evals/seeds/chapters/xuanhuan_ch1.md")` 成功
- [ ] 导入后 `chapter_heads` 指向该版本，`version_type == "accepted"`
- [ ] 导入后字数统计正确

### Layer 3: Runner 集成测试
- [ ] `run_seed_project()` 在 mock LLM 下完整跑通，返回 `EvaluationResult.success == True`
- [ ] 输出目录包含 `result.json`、`chapter_v2.md`、`review_report.json`、`settlement.json`、`summary.json`
- [ ] 3 个种子配置均可成功导入并跑通
- [ ] runner 可重复执行同一配置（产生不同的 `project_id`，不冲突）

---

## 验收标准（Acceptance Criteria）

- [ ] `pytest tests/test_eval_runner.py -v` 全部通过（≥ 6 个测试用例：导入 2 个 + 种子章节 2 个 + runner 集成 2 个）
- [ ] `python -m evals --help` 可正常显示 CLI 帮助
- [ ] `python -m evals --seed-config evals/seeds/xuanhuan_webnovel.json --seed-chapter evals/seeds/chapters/xuanhuan_ch1.md --output-dir evals/output/test_run` 在 mock 模式下成功执行
- [ ] 3 个种子项目 JSON 均通过 Pydantic validate
- [ ] 代码符合 CLAUDE.md 规范（类型标注、单文件 < 400 行等）
- [ ] 不违反任何不可违背规则
- [ ] 生成了 `tasks/020-B-eval-seed-infrastructure-DONE.md` 交接文件
- [ ] **不更新 docs/STATUS.md**（由 020-C 统一更新）

---

## 参考文档

- `tasks/020-e2e-evaluation.md` — 父任务总纲
- `tasks/020-A-mock-e2e-integration.md` — 上游子任务（集成测试基线）
- `src/songyan/workflows/phase1_graph.py` — `run_chapter_pipeline` 入口
- `src/songyan/db/repository.py` — ProjectRepository / CharacterRepository
- `system_prompt/development-tech-plan-v2.md` — V2 技术方案第 9~10 章
- `docs/architecture/04-vibe-coding-engineering.md` — 工程手册 + 验收指标
