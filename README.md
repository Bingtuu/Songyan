<div align="center">
  <img src="docs/icon/logo02.png" alt="Songyan logo" width="160" />

  <h1>Songyan（松烟）</h1>

  <p><strong>用 AI 写长篇中文小说的工程化方案</strong></p>
  <p><em>松烟入墨，字句成锋。</em></p>

  <p>
    <a href="https://www.python.org/"><img src="https://img.shields.io/badge/python-%3E%3D3.11-blue" alt="Python >= 3.11" /></a>
    <a href="LICENSE"><img src="https://img.shields.io/badge/license-AGPL--3.0-blue" alt="License AGPL-3.0" /></a>
    <a href="https://github.com/Bingtuu/Songyan/actions/workflows/ci.yml"><img src="https://github.com/Bingtuu/Songyan/actions/workflows/ci.yml/badge.svg" alt="CI" /></a>
    <a href="https://github.com/astral-sh/ruff"><img src="https://img.shields.io/badge/code%20style-ruff-black" alt="Code style: ruff" /></a>
  </p>
</div>

---

## 目录

- [这是什么？](#这是什么)
- [核心设计](#核心设计)
- [架构概览](#架构概览)
- [当前能力](#当前能力)
- [项目结构](#项目结构)
- [快速开始](#快速开始)
- [常用命令](#常用命令)
- [技术栈](#技术栈)
- [项目状态](#项目状态)
- [体裁与扩展](#体裁与扩展)
- [开发与贡献](#开发与贡献)
- [常见问题](#常见问题)
- [开发文档](#开发文档)
- [许可证](#许可证)

---

## 这是什么？

Songyan 是一套把 AI 写长篇中文小说这件事变得**可持续、可验证、可复现**的工程方案。

它不是一次调用模型生成一章就结束，而是把写作拆成一条流水线：**规划 → 生成 → 审查 → 修订 → 确认 → 记忆**。每一章都要先通过多层质量检查，再被“拆解”成角色状态、世界设定、伏笔线索等事实，存入一个长期事实数据库。这样写到第 200 章时，系统仍然知道第 3 章发生了什么，而不是靠模型自己回忆。

目前已经在以下体裁上完成长窗口验证：

- **科幻**：稳定跑到 220 章；
- **玄幻、武侠、都市**：均完成 200 章长篇爬坡，200/200 accepted，核心质量检查通过。

系统内置科幻、玄幻、武侠、都市等多种体裁模板。新增体裁主要通过配置文件接入，不需要改写核心工作流。

最新验证数据、阶段状态和已知例外见 [`docs/STATUS.md`](docs/STATUS.md)。

### 它解决什么问题？

直接用模型写长篇，通常会遇到三个坑：

1. **写到后面忘了前面**：模型上下文有限，几十章后关键伏笔和角色关系就模糊了。
2. **质量越来越飘**：没有外部约束，文风、设定、角色行为会随机走样。
3. **事实靠不住**：模型会“顺口”改设定、改角色状态，但没法证明这是不是前后一致。

Songyan 的解法是**把“写正文”和“管事实”分开**：正文可以自由发挥，但写入长期事实库的数据必须有正文证据、有校验规则。每一章的事实基础都可追溯、可回放。

---

## 核心设计

### 1. 先写稿，再验事实

大多数 AI 写作工具把模型输出当最终结果。Songyan 把它当**候选材料**：

```
生成正文
    ↓
规则检查 + 语义检查 → 自动修订（最多两轮）
    ↓
人工/自动确认接收
    ↓
从正文中提取并校验：
  - 角色状态变化（旧值必须和数据库当前值对得上）
  - 新设定（必须有正文原文作为证据）
  - 伏笔（记录来源章节，方便后续追踪兑现）
  - 关键数字（公式必须闭合）
    ↓
写入 SQLite 长期事实库
```

一句话：**模型负责创意，系统负责记账和核对。**

### 2. 聪明的上下文压缩

长篇最怕上下文爆炸。Songyan 用四种手段把历史信息控制在合理范围：

| 手段 | 做法 | 效果 |
|------|------|------|
| 分层摘要 | 最近几章保留细节，远期压缩成弧/卷摘要 | 历史信息从线性增长变成对数增长 |
| 角色聚焦 | 主角和当前出场角色保留完整档案，长期不出场的角色逐步降级 | 控制角色池膨胀 |
| 设定归档 | 低置信度、长期未使用的设定自动归档 | 防止设定越积越多 |
| 硬上限保护 | 预算超限时进入紧急模式，只保留不可裁剪的核心约束 | 绝对兜底 |

### 3. 多层把关，不止一个评分

Songyan 不把质量判断交给单一模型，而是分四层：

- **规则层**：用代码做确定性检查——字数、Markdown 泄漏、段落重复、AI 腔特征词等。有就是有，没有就是没有。
- **语义层**：用模型判断角色行为一致性、叙事节奏、信息密度等。关键问题必须附带正文证据。
- **文学诊断**：识别角色工具化、概念空转、过度平滑等文学性问题，只诊断、不阻塞。
- **质量门**：规则层和语义层的结果合并后统一判断——通过则接收，可修复则自动修订，修不好则停下来等人。

### 4. 每个版本都存档

每次生成、修订、重写、人工编辑都会创建一条新记录，**不存在“覆盖”**。这意味着：

- 任何版本都可以回溯；
- 质量下降时可以回退到安全版本；
- 谁在什么时候改了什么，都有审计链。

### 5. 跑长了也能停能续

长篇生成可能跑几个小时。Songyan 支持：

- 中途 kill 后用 `--resume` 从断点继续；
- 自动跳过已接收的章节；
- 单章失败不阻塞整体，失败章被隔离记录；
- 检测到真实质量退化时自动暂停，人工判断后继续。

---

## 架构概览

核心流程可以概括为：

```mermaid
flowchart LR
    Plan["规划"] --> Context["组装上下文"]
    Context --> Draft["生成正文"]
    Draft --> Review["规则/语义审查"]
    Review --> Revise["必要时修订"]
    Revise --> Accept["确认接收"]
    Accept --> Extract["提取事实"]
    Extract --> DB["SQLite 事实库"]
    DB --> Context
```

主要模块：

- `agents/`：规划、写作、审查、修订、事实结算。
- `workflows/`：单章闭环和多章运行控制。
- `db/`：SQLite schema、迁移和 repository。
- `genres/`、`project_templates/`：体裁配置和项目模板。
- `evals/`：质量度量、文本洁净、连续性与段审计工具。

---

## 当前能力

Songyan 已经过科幻 220 章，以及玄幻、武侠、都市各 200 章的长窗口验证。以下能力已在这些验证样本中跑通：

| 能力 | 说明 |
|------|------|
| 长篇连续生成 | 支持数百章连续生成、断点续跑和分段审计 |
| 多体裁可插拔 | 科幻、玄幻、武侠、都市等 7 种体裁共用同一套流程；新增体裁只需写配置文件，不改核心逻辑 |
| 文本洁净 | 已验证样本中无 Markdown 泄漏、无段落重复、无 AI 保护指令混入正文 |
| 事实一致性 | 角色状态、世界设定、关键数值都可追溯到正文证据 |
| 跨体裁一致性审计 | 只统计有正文证据的关键/严重问题，跨体裁公平比较 |
| 跨章连续性 | 孤立设定和遗忘伏笔自动检测；连续性评分全程稳定 |
| 上下文控制 | 智能压缩让 220+ 章生成不溢出上下文窗口 |
| 正文导出 | `songyan export` 从接收版本导出纯净书稿，支持 Markdown/txt 与 flat/arc/volume 分组 |
| 自适应暂停 | 正常波动不误伤，真实质量退化时自动暂停 |
| 叙事骨架 | 全书大纲 → 弧规划 → 章节目标自顶向下派生 |
| 伏笔调度 | 长程伏笔主动兑现，不同体裁可设不同回收窗口 |
| 文学护栏 | 配角目标、主动选择、概念预算等在创作和审查中双重约束 |
| 项目模板化 | 一键从体裁模板创建完整项目骨架 |

> 最新验证数据和进展见 [`docs/STATUS.md`](docs/STATUS.md)。

---

## 项目结构

```text
songyan/
├── src/songyan/
│   ├── agents/              # 写作、审查、修订、事实结算
│   ├── workflows/           # 单章闭环和多章运行
│   ├── db/                  # SQLite schema、repository、迁移
│   ├── evals/               # 质量度量和审计工具
│   ├── genres/              # 体裁配置
│   ├── project_templates/   # 项目模板
│   └── prompts/             # prompt 工艺卡
├── tests/                   # 自动化测试
├── docs/                    # 当前状态和开发文档
└── archive/                 # 历史任务与报告归档
```

---

## 快速开始

> 当前处于 V11 开源可用化收尾阶段。以下路径面向懂命令行、能配置 LLM API key 的技术用户；在 Task 209-215 全部完成前，本项目仍应视为 preview，而不是正式开源可用版本。

### 环境要求

- Python >= 3.11
- DeepSeek API Key（或兼容 OpenAI 接口的 LLM）
- 磁盘空间：100 章数据库约 100MB，200 章约 160MB

### 安装

```powershell
python -m pip install -e ".[dev]"
Copy-Item .env.example .env
```

编辑 `.env`，至少填入 `LLM_API_KEY`。如使用其他兼容 OpenAI 接口的模型服务，同时调整 `LLM_BASE_URL` 和 `LLM_MODEL`。

### 配置

`.env` 关键配置项（完整模板见 [`.env.example`](.env.example)）：

| 变量 | 默认 | 说明 |
|------|------|------|
| `LLM_API_KEY` | — | **必填**。LLM API Key |
| `LLM_BASE_URL` | `https://api.deepseek.com` | 兼容 OpenAI 接口的模型端点 |
| `LLM_MODEL` | `deepseek-chat` | 默认模型 |
| `DATABASE_URL` | `sqlite:///songyan.db` | 事实库路径 |
| `SONGYAN_RUN_COST_BUDGET` | `0` | 单次运行成本预算；0 表示不启用 |

### 创建项目并生成

```powershell
# 检查本地环境、资源和数据库配置；第一次运行建议初始化/迁移 SQLite DB
songyan doctor --init-db

# 从体裁模板创建项目（支持 scifi/xuanhuan/wuxia/urban 等 7 种）
songyan create-project --template xuanhuan

# 记录输出中的 project_id，然后生成第 1-3 章（自动确认模式）
songyan run --project-id <project_id> --chapters 1-3 --auto-confirm

# 记录输出中的 run_id，生成运行报告
songyan report --run-id <run_id>

# 导出已 accepted 的正文
songyan export --project-id <project_id> --chapters 1-3 --format md --output exports/
```

Windows 下长跑建议用硬超时 wrapper。该 wrapper 目前是仓库脚本，不是已安装的 `songyan` 子命令；若当前目录不是仓库根目录，请使用仓库绝对路径调用：

```powershell
# 在仓库根目录下
powershell -File .\scripts\run_with_timeout.ps1 -TimeoutSec 3600 -- songyan run --project-id <project_id> --chapters 1-3 --auto-confirm

# 在任意 cwd 下
$songyanRepo = "C:\path\to\Songyan"
powershell -File "$songyanRepo\scripts\run_with_timeout.ps1" -TimeoutSec 3600 -- songyan run --project-id <project_id> --chapters 1-3 --auto-confirm
```

更完整的 10 章教程、成本预算、日志位置和恢复入口见 [`docs/quickstart.md`](docs/quickstart.md)。故障排查见 [`docs/troubleshooting.md`](docs/troubleshooting.md)。

当前已知限制：

- Task 209 只补齐文档和命令证据，不消耗真实 LLM 预算跑 Ch1-3 成功验收。
- 若 `songyan run` 业务失败，当前进程 exit code 仍可能为 0；请先用 `songyan report --run-id <run_id>` 查看失败原因。该问题路由到 Task 210/212。
- backup/restore、run bundle、profile validate、release checklist 和 wheel smoke 属于 Task 211-215。

---

## 常用命令

| 命令 | 作用 |
|------|------|
| `songyan doctor --init-db` | 检查环境并初始化/迁移 SQLite DB |
| `songyan create-project --template <id>` | 从体裁模板创建项目 |
| `songyan list-projects` | 列出所有项目 |
| `songyan run --project-id <id> --chapters 1-3 --auto-confirm` | 生成 Quickstart 短窗口 |
| `songyan run --project-id <id> --chapters 1-10 --auto-confirm --resume` | 扩展到 10 章并支持断点续跑 |
| `songyan report --run-id <run_id>` | 从运行日志生成报告和成本视图 |
| `songyan export --project-id <id> --chapters 1-3 --format md --output exports/` | 导出 accepted 正文 |
| `songyan index --project-id <id> --chapters 1-10 --rebuild` | 重建 RAG 索引 |
| `songyan metrics` | 质量度量指标 |
| `songyan mark ...` | 管理人工标记 |

完整参数以 `songyan <command> --help` 为准。

---

## 技术栈

| 组件 | 选型 | 选型理由 |
|------|------|----------|
| 语言 | Python 3.11+（async/await） | 适合 IO 密集型 LLM 调用 |
| 工作流 | LangGraph | 把单章闭环建模为状态机，天然支持断点续跑 |
| 数据模型 | Pydantic v2 | 严格校验，类型安全 |
| 事实库 | SQLite + aiosqlite | 零运维、本地可审计、足够支撑 200+ 章 |
| LLM 接入 | LiteLLM | 一端接入，可切多家模型 |
| CLI | Click | 命令行体验稳定 |
| 日志 | structlog | 结构化日志，便于事后重建现场 |
| 测试 | pytest、ruff、mypy | 默认测试 + CLI 测试 + 类型检查 |

---

## 项目状态

| 阶段 | 状态 |
|------|------|
| 长篇稳定性 | 科幻 220 章；玄幻、武侠、都市 Ch200 验证完成 |
| 多体裁运行时 | 已支持按体裁配置上下文预算、质量阈值和伏笔调度 |
| 生产化工具 | CLI、导出、doctor、成本追踪、质量报告、CI 已接入 |
| 当前重点 | V11 开源可用化收尾；Task 209 已补齐 Quickstart 与用户文档闭环 |
| V10 收口报告 | [`archive/v10/reports/207-v10-closure-report.md`](archive/v10/reports/207-v10-closure-report.md) |
| 下一阶段入口 | [`tasks/V11-README.md`](tasks/V11-README.md) |

详细阶段记录见 [`docs/STATUS.md`](docs/STATUS.md) 和 [`tasks/V10-README.md`](tasks/V10-README.md)。

---

## 体裁与扩展

新增体裁主要需要补三类资源：

| 资源 | 位置 | 作用 |
|------|------|------|
| 体裁规则 | `src/songyan/genres/data/` | 写作约束、禁忌、审查关注点 |
| 项目模板 | `src/songyan/project_templates/data/` | 主角设定、核心钩子、种子大纲 |
| 运行时配置 | `genre_runtime_profiles` / registry | 上下文预算、暂停阈值、伏笔窗口 |

推荐流程：

1. 复制一个相近体裁的配置和模板。
2. 用短窗口生成验证文本洁净、预算和一致性。
3. 调整体裁规则或运行时配置。
4. 通过回归后再做长窗口爬坡。

体裁扩展不需要改核心 workflow；除非要改变“写正文”和“管事实”之间的边界。

---

## 开发与贡献

提交代码前请先阅读 [`AGENTS.md`](AGENTS.md)。它记录了项目的工程边界：事实库写入、版本不可覆盖、Agent 职责、审查与修订规则等。

### 验证命令

```bash
# 全量测试
python -m pytest tests/ -q

# CLI 测试
python -m pytest tests/cli -q

# 代码检查
ruff check src/ tests/

# 类型检查
mypy src/
```

如果改动影响体裁配置、上下文组装、prompt 或质量工具，请补充短窗口回归。具体回归口径见 [`AGENTS.md`](AGENTS.md) 和当前阶段任务文档。

---

## 常见问题

**Q: 支持哪些 LLM？**
经 LiteLLM 接入，默认 DeepSeek；任何兼容 OpenAI 接口的端点改 `LLM_BASE_URL` / `LLM_MODEL` 即可，无需改代码。

**Q: 单章生成失败会中断长跑吗？**
不会。isolate 模式下单章失败被隔离记录，后续章节继续；检测到真实质量退化时才自动暂停，人工判断后可 `--resume` 继续。

**Q: Windows 下测试/长跑卡住怎么办？**
用防卡 wrapper 包一层硬超时。当前 wrapper 位于仓库 `scripts/` 目录；非仓库 cwd 下请用绝对路径：

```powershell
powershell -File .\scripts\run_with_timeout.ps1 -TimeoutSec 3600 -- <你的命令>

$songyanRepo = "C:\path\to\Songyan"
powershell -File "$songyanRepo\scripts\run_with_timeout.ps1" -TimeoutSec 3600 -- <你的命令>
```

测试环境下也可以把 `CHECKPOINTER_MODE` 设为 `memory`，减少本地 checkpoint 持久化带来的干扰。

---

## 开发文档

- [`docs/STATUS.md`](docs/STATUS.md) — 当前状态和最新验证证据。
- [`docs/INDEX.md`](docs/INDEX.md) — 文档索引。
- [`docs/quickstart.md`](docs/quickstart.md) — 外部技术用户 Quickstart、10 章教程、成本与日志说明。
- [`docs/troubleshooting.md`](docs/troubleshooting.md) — 故障排查入口和当前限制。
- [`tasks/V10-README.md`](tasks/V10-README.md) — V10 阶段规划和完成入口。
- [`archive/v10/reports/207-v10-closure-report.md`](archive/v10/reports/207-v10-closure-report.md) — V10 收口报告。
- [`tasks/V11-README.md`](tasks/V11-README.md) — V11 开源可用化正式阶段入口。
- [`docs/reports/209-quickstart-evidence.md`](docs/reports/209-quickstart-evidence.md) — Task 209 Quickstart 命令证据。
- [`AGENTS.md`](AGENTS.md) — 开发规范和工程纪律。
- [`archive/`](archive/) — 历史任务、报告和归档资料。

---

## 许可证

AGPL-3.0 — 详见 [`LICENSE`](LICENSE)。
