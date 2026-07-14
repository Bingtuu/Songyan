# Task 172: 项目模板化与体裁可插拔结构设计

> **状态**: 设计稿（待 review）  
> **日期**: 2026-07-13  
> **对应框架**: V7 阶段 Z 渐进爬坡收尾；为 V8 题材泛化（产品化）奠定工程基础  
> **前置**: Task 172 Ch250 科幻长跑可并行推进；本设计不阻塞 V7 主线  

---

## 1. 背景与目标

### 1.1 现状问题

当前项目已支持 `GenreProfile`（`genres/*.json`）和 `CreativeModeProfile`（`creative_modes/*.json`）的配置化加载，但**项目级别的初始化仍然是硬编码的科幻设定**：

- `scripts/run_158_ch1_ch100.py`、`scripts/run_159_ch1_ch150.py`、`scripts/run_171_ch200.py` 硬编码了 `ProjectSetting` 与 `StoryOutline/ArcPlan/PlotThread`。
- CLI `create_project` 只支持交互式输入，无法一键切换到玄幻、武侠等体裁。
- `evals/seeds/*.json` 虽按体裁保存了种子项目，但格式偏向评测，且未被 CLI/长跑 harness 复用。

这导致：换一个体裁需要手动改脚本、写大纲、重建 DB，无法做到"可插拔"。

### 1.2 目标

建立 **`ProjectTemplate` 模板层**，实现：

1. **B 为主**：每个体裁一个标准模板目录，包含 `ProjectSetting` + 大纲 + 初始角色/设定/数值体系。
2. **C 为补充**：支持轻量继承（`extends`）和变体（`variants/`），但不强制。
3. **兼容现有资产**：保留 `evals/seeds/*.json`，通过转换层复用。
4. **不阻塞 V7 主线**：Task 172 Ch250 科幻长跑继续并行；本任务只在项目初始化层改动。
5. **每子任务后短章测试**：拆分为 172.1–172.5，每个子任务完成后做 Ch1–Ch3/Ch1–Ch5 短章验证。

---

## 2. 总体架构

新增 `ProjectTemplate` 抽象层，位于 `GenreProfile` / `CreativeModeProfile` 之上：

```
project_templates/
├── _schema.json              # 模板 JSON Schema（校验用）
├── scifi/
│   ├── template.yaml         # ProjectSetting + 可选 extends
│   ├── outline.json          # StoryOutline + ArcPlan[] + PlotThread[]
│   └── seed.json             # 初始角色、设定、数值体系
├── xuanhuan/
│   ├── template.yaml
│   ├── outline.json
│   └── seed.json
├── wuxia/
│   ...
└── urban/
    ...
```

运行时核心入口：

```python
from songyan.project_templates import ProjectTemplateLoader, ProjectInitializer

template = ProjectTemplateLoader.load("xuanhuan")
project_id, project = await ProjectInitializer.from_template(template)
```

### 2.1 与现有组件的关系

| 层级 | 现有组件 | 新增组件 |
|---|---|---|
| 体裁规则 | `genres/*.json` + `GenreProfileLoader` | 不变，被模板引用 |
| 创作模式 | `creative_modes/*.json` + `CreativeModeRegistry` | 不变，被模板引用 |
| 项目模板 | — | `project_templates/*/` + `ProjectTemplateLoader` |
| 项目初始化 | CLI 交互式、`run_*` 脚本硬编码 | `ProjectInitializer.from_template()` |
| Prompt 工艺卡 | `prompts/cards/*` | 不变；模板只注入 `genre_rules`/`style_baseline` 等变量 |

---

## 3. 文件格式规范

### 3.1 目录式模板（B 为主）

每个模板目录下包含：

#### `template.yaml`

```yaml
id: xuanhuan                    # 模板 ID，等于目录名
name: 玄幻修仙模板
extends: null                   # 可选：父模板 ID（C 补充）
overwrite: {}                   # 可选：对父模板的字段覆盖

project_setting:
  title: 灵渊纪
  genre_id: xuanhuan
  mode_id: webnovel_intense
  protagonist_name: 陆沉
  protagonist_background: 青岩镇铁匠铺学徒，父母死于十年前的妖兽袭城...
  core_hook: 灵气枯竭时代，少年获得上古灵渊传承，逆天改命
  target_reader_expectation: 热血玄幻升级流，节奏明快，世界观自洽
  target_word_count: 450000
  tone: 热血
  estimated_chapters: 250
  words_per_chapter: 3000
  story_structure: serial
  sub_genre_id: null
  arc_boundaries: [25, 50, 75, 100, 125, 150, 175, 200, 225]
  arc_boundaries_auto: false
```

#### `outline.json`

与现有 `load_outline_file()` 解析的格式一致：

```json
{
  "outline": {
    "core_conflict": "人类文明存续与深空黑色结构『方舟』的意志之间的对抗",
    "mainline_synopsis": "...",
    "themes": ["存续与牺牲", "认知的边界"],
    "intended_ending": "..."
  },
  "arc_plans": [
    {
      "arc_index": 0,
      "start_chapter": 1,
      "end_chapter": 25,
      "arc_goal": "发现方舟、确立共鸣者身份",
      "threads_to_open": ["t_ark", "t_resonance", "t_partner"],
      "threads_to_resolve": [],
      "is_mainline": true
    }
  ],
  "plot_threads": [
    {
      "thread_id": "t_ark",
      "title": "方舟",
      "description": "...",
      "is_mainline": true,
      "expected_resolve_arc": 5
    }
  ]
}
```

#### `seed.json`

初始角色、设定、数值体系：

```json
{
  "characters": [
    {
      "name": "陆沉",
      "role": "protagonist",
      "age": 16,
      "description": "...",
      "initial_state": {
        "cultivation_level": "无",
        "spirit_value": 0
      }
    }
  ],
  "initial_settings": [
    {
      "setting_key": "qingyan_town",
      "setting_name": "青岩镇",
      "description": "...",
      "source_quote": ""
    }
  ],
  "numerical_system": {
    "name": "九品灵根修炼体系",
    "levels": ["无", "炼气一层", ...],
    "base_unit": "灵气值",
    "formula_hint": "..."
  }
}
```

### 3.2 单文件种子兼容（evals/seeds/*.json）

现有 `evals/seeds/*.json` 保留，格式兼容。`ProjectTemplateLoader` 内部自动把单文件种子转换为 `ProjectTemplate`：

- `project_name` → `project_setting.title`
- `genre_id` / `mode_id` → 直接映射
- `description` → `project_setting.core_hook`
- `characters` / `initial_settings` / `numerical_system` → `seed.json` 等价内容
- `outline` 字段若不存在，则模板不提供大纲（退化为交互式创建）

### 3.3 轻量继承（C 补充）

允许 `template.yaml` 声明 `extends`：

```yaml
# project_templates/xuanhuan/cultivation/template.yaml
id: xuanhuan_cultivation
name: 玄幻·正统修仙变体
extends: xuanhuan
overwrite:
  project_setting:
    title: 万道独尊
    protagonist_name: 韩立
  seed:
    characters:
      - name: 韩立
        role: protagonist
        ...
```

继承规则：

1. 父模板先加载。
2. `overwrite` 递归合并到父模板；数组字段默认替换（非追加）。
3. 不允许循环继承；检测到循环时抛 `ProjectTemplateError`。
4. `variants/` 子目录中的模板自动注册，ID 为 `<parent>/<variant>`。
5. **文件继承路径**：`template.yaml` 必须从变体目录读取；`outline.json` 和 `seed.json` 优先在变体目录查找，若不存在则继承父模板目录中的文件。`overwrite` 只对 `template.yaml` 中的字段生效，不直接修改继承来的 `outline.json`/`seed.json`。

---

## 4. 数据模型

```python
# src/songyan/models/project_template.py

from __future__ import annotations

from pathlib import Path
from typing import Any

from pydantic import BaseModel, Field

from songyan.models import ProjectSetting
from songyan.models.narrative import ArcPlan, PlotThread, StoryOutline


class TemplateSeedCharacter(BaseModel):
    name: str
    role: str = "supporting"  # protagonist | supporting | antagonist
    age: int | None = None
    description: str = ""
    initial_state: dict[str, Any] = Field(default_factory=dict)


class TemplateSeedSetting(BaseModel):
    setting_key: str
    setting_name: str
    description: str
    source_quote: str = ""


class TemplateSeedNumericalSystem(BaseModel):
    name: str
    levels: list[str] = Field(default_factory=list)
    base_unit: str = ""
    formula_hint: str = ""


class TemplateSeed(BaseModel):
    characters: list[TemplateSeedCharacter] = Field(default_factory=list)
    initial_settings: list[TemplateSeedSetting] = Field(default_factory=list)
    numerical_system: TemplateSeedNumericalSystem | None = None


class ProjectTemplate(BaseModel):
    id: str
    name: str = ""
    extends: str | None = None
    overwrite: dict[str, Any] = Field(default_factory=dict)
    source_dir: Path | None = None  # 加载时回填，指向最终模板目录

    project_setting: ProjectSetting
    seed: TemplateSeed = Field(default_factory=TemplateSeed)
    # outline 字段不在 Pydantic 模型里直接序列化；加载器解析 outline.json 后
    # 通过 outline / arc_plans / plot_threads 三个独立属性暴露。
    _outline: StoryOutline | None = None
    _arc_plans: list[ArcPlan] = Field(default_factory=list)
    _plot_threads: list[PlotThread] = Field(default_factory=list)

    @property
    def has_outline(self) -> bool:
        return self._outline is not None

    @property
    def outline_tuple(self) -> tuple[StoryOutline, list[ArcPlan], list[PlotThread]] | None:
        if self._outline is None:
            return None
        return (self._outline, self._arc_plans, self._plot_threads)
```

---

## 5. 加载器 API

```python
# src/songyan/project_templates/loader.py

from pathlib import Path

from songyan.models.project_template import ProjectTemplate


class ProjectTemplateError(ValueError):
    """模板加载或校验失败."""


class ProjectTemplateNotFoundError(ProjectTemplateError):
    """模板 ID 不存在."""


class ProjectTemplateLoader:
    def __init__(self, templates_dir: Path | None = None) -> None: ...

    def load(self, template_id: str) -> ProjectTemplate: ...

    def list_templates(self) -> list[str]: ...

    def list_variants(self, template_id: str) -> list[str]: ...
```

### 5.1 加载优先级

1. 先查找 `project_templates/<template_id>/template.yaml`。
2. 若不存在，查找 `evals/seeds/<template_id>.json` 作为兼容路径。
3. 若都不存在，抛 `ProjectTemplateNotFoundError`。

### 5.2 校验

- `template.yaml` 必需字段：`id`、`project_setting`。
- `project_setting.genre_id` 必须对应 `genres/*.json` 中存在的 genre。
- `project_setting.mode_id` 必须对应 `creative_modes/*.json` 中存在的 mode。
- `outline.json` 若存在，必须通过 `load_outline_file()` 的引用校验。
- `seed.json` 中的 `setting_key` 不允许重复。

---

## 6. 项目初始化流程

```python
# src/songyan/project_templates/initializer.py

class ProjectInitializer:
    @staticmethod
    async def from_template(template: ProjectTemplate) -> tuple[str, ProjectSetting]:
        """从模板创建完整项目：
        1. init_schema
        2. ProjectRepository.create(project_setting)
        3. ensure_protagonist_character
        4. 写入 seed characters / initial_settings / numerical_system
           （复用/参考现有 `evals.runner.import_seed_project` 的写入逻辑）
        5. 若存在 outline，NarrativeRepository.import_outline
        6. 返回 (project_id, project_setting)
        """
```

### 6.1 幂等性

- 模板初始化**总是新建项目**（新 `project_id`），不更新已有项目。
- 若 `seed.json` 中的 `numerical_system` 与 `genre.has_numerical_system` 不一致，记录 warning 但不阻断。

---

## 7. CLI / Harness 集成

### 7.1 CLI `create_project`

新增 `--template` 选项：

```bash
# 使用模板一键创建
songyan create-project --template xuanhuan

# 使用变体
songyan create-project --template xuanhuan/cultivation

# 仍支持交互式创建（默认行为不变）
songyan create-project
```

当 `--template` 提供时，CLI 跳过交互式提问，直接使用模板中的 `project_setting`，但仍允许 `--outline-file` 覆盖模板自带大纲。

### 7.2 长跑 harness

改造 `scripts/run_171_ch200.py`，把硬编码的 `_project_setting()` / `_build_outline()` 替换为模板加载：

```python
# run_171_ch200.py 修改后
TEMPLATE_ID = os.getenv("TEMPLATE_ID", "scifi")

async def _init_db() -> str:
    ...
    template = ProjectTemplateLoader().load(TEMPLATE_ID)
    project_id, project = await ProjectInitializer.from_template(template)
    ...
```

新增环境变量：

| 变量 | 默认值 | 说明 |
|---|---|---|
| `TEMPLATE_ID` | `scifi` | 项目模板 ID |
| `START_CHAPTER` | `1` | 起始章 |
| `END_CHAPTER` | `200` | 结束章 |

保持向后兼容：不设置 `TEMPLATE_ID` 时，默认仍跑科幻，与现有 Task 171 行为一致。

### 7.3 小窗口验证命令示例

```powershell
# 玄幻 Ch1-Ch5 小窗口
$env:TEMPLATE_ID = "xuanhuan"
$env:END_CHAPTER = "5"
python scripts/run_171_ch200.py --init
python scripts/run_171_ch200.py

# 武侠 Ch1-Ch3
$env:TEMPLATE_ID = "wuxia"
$env:END_CHAPTER = "3"
python scripts/run_171_ch200.py --init
python scripts/run_171_ch200.py
```

---

## 8. 任务拆分与短章测试

Task 172 拆分为 5 个子任务，每个子任务完成后做短章测试。

| 子任务 | 目标 | 短章测试 |
|---|---|---|
| **172.1** | 定义 `ProjectTemplate` 数据模型 + JSON/YAML Schema | `tests/test_project_template_models.py`：7 个 genre 的模板样例能过 Pydantic 校验 |
| **172.2** | 实现 `ProjectTemplateLoader`：目录式模板 + 兼容 `evals/seeds/*.json` | `tests/test_project_template_loader.py`：加载所有已有 genre 模板/种子，校验通过 |
| **172.3** | 实现 `ProjectInitializer.from_template()` | `tests/test_project_template_initializer.py`：从模板初始化项目后，DB 中 project/characters/settings/outline 正确 |
| **172.4** | 改造 `run_171_ch200.py` 和 CLI `create_project` 支持 `--template` | 对每个 genre 跑 `TEMPLATE_ID=<id> END_CHAPTER=3 python scripts/run_171_ch200.py`，要求 completed=3、T9=0 |
| **172.5** | 轻量继承/变体：`extends` 和 `variants/` | 创建一个 `xuanhuan/cultivation` 变体，跑 Ch1–Ch3 验证覆盖合并正确 |

### 8.1 短章测试通过标准

每个体裁的小窗口测试必须满足：

1. `completed == target_chapters`（默认无失败）。
2. `T9 hard issue == 0`（无 meta/artifact/duplicate）。
3. 每章字数在 `word_range` 内。
4. 不触发 AutoHalt（若触发，必须证明是真实退化并进入 172.p 修复）。

### 8.2 测试策略

- 单元测试覆盖 loader / initializer / model 校验。
- 小窗口实跑测试作为**集成测试**，标记为 `@pytest.mark.slow` 或手动在 harness 中执行，避免 CI 超时。
- 由于涉及 LLM 调用，小窗口测试默认跳过；提供 `scripts/run_172_short_window.py` 统一入口。

---

## 9. 风险与边界

### 9.1 明确不做

- **不改 Prompt 工艺卡结构**：Prompt 仍走 `prompts/cards/*`，模板只负责注入 `genre_rules`/`style_baseline` 等已有变量。
- **不改 Agent 编排**：不新增玄幻/武侠专属 agent；`CreativeModeProfile.enabled_agents` 已足够。
- **不替代 V7 科幻主线**：Task 172 Ch250 仍默认跑 `scifi` 模板。
- **不做全自动大纲生成**：模板中的 `outline.json` 由人编写；后续可考虑模板辅助生成，但不在 172 范围内。

### 9.2 已知风险

| 风险 | 缓解 |
|---|---|
| 新体裁小窗口触发 gate / health 退化 | 先标记为 `172.p-*` 撞墙修复，不临时放宽阈值 |
| 模板格式漂移 | 提供 `_schema.json` 和单测强制校验 |
| `evals/seeds/*.json` 与新版模板字段冲突 | 转换层做字段映射，旧文件只读不改 |
| 继承合并语义歧义 | `overwrite` 数组字段默认替换，文档明确 |

---

## 10. 附录：与现有 `evals/seeds/*.json` 的兼容策略

| 现有种子字段 | 映射到 `ProjectTemplate` |
|---|---|
| `project_name` | `project_setting.title` |
| `genre_id` | `project_setting.genre_id` |
| `mode_id` | `project_setting.mode_id` |
| `description` | `project_setting.core_hook` |
| `characters` | `seed.characters` |
| `initial_settings` | `seed.initial_settings` |
| `numerical_system` | `seed.numerical_system` |
| `outline`（若新增） | `outline` |

转换层只读现有种子，不修改原文件。后续若种子需要大纲，可逐步在种子 JSON 中增加 `outline` 字段。

---

> **松烟入墨，字句成锋。**
