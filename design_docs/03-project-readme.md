代码是思想的延伸，架构是协作的契约。
好的产品不是一次做全，而是在正确的时间验证正确的假设。

# NovelForge — 多 Agent AI 小说生产引擎

<p align="center">
  <strong>从一句灵感，到一本完整的小说</strong><br>
  <strong>先验证一章，再验证十章，最后成书</strong>
</p>

<p align="center">
  <a href="#-快速开始">快速开始</a> •
  <a href="#-三阶段路线图">路线图</a> •
  <a href="#-架构设计">架构</a> •
  <a href="#-核心设计">核心设计</a> •
  <a href="#-评测标准">评测</a>
</p>

<p align="center">
  <img src="https://img.shields.io/badge/python-3.11+-blue.svg" alt="Python"/>
  <img src="https://img.shields.io/badge/LangGraph-0.2+-green.svg" alt="LangGraph"/>
  <img src="https://img.shields.io/badge/CLI-first-lightgrey.svg" alt="CLI"/>
  <img src="https://img.shields.io/badge/license-AGPL--3.0-orange.svg" alt="License"/>
</p>

---

## 目录

- [1. 项目定位](#1-项目定位)
- [2. 三阶段路线图](#2-三阶段路线图)
- [3. 快速开始](#3-快速开始)
- [4. 架构设计](#4-架构设计)
- [5. 核心设计](#5-核心设计)
- [6. 评测标准](#6-评测标准)
- [7. 与其他项目对比](#7-与其他项目对比)
- [8. 开发文档](#8-开发文档)
- [9. 参考与致谢](#9-参考与致谢)
- [10. 许可证](#10-许可证)

---

## 1. 项目定位

NovelForge 是一个面向**长篇中文小说创作**的 AI 生产系统，基于 LangGraph 多 Agent 协作架构。

### 核心判断

我们不是在做一个"AI 聊天写小说"的工具，而是在验证一个假设：

> **"AI 能否在足够一致的上下文中，稳定产出质量合格、设定不矛盾的中文小说章节？"**

为此，我们采用**三阶段渐进落地**的策略，而不是一开始就搭建完整工厂。

### 目标用户

| 用户类型 | Phase 1 | Phase 2 | Phase 3 |
|----------|---------|---------|---------|
| **开发者/研究者** | ✅ 验证核心假设 | ✅ 扩展连续性 | ✅ 产品化 |
| **小说新手** | | | ✅ 完整产品 |
| **网文作者** | | ✅ 提速生产 | ✅ 批量生产 |

### 当前阶段

**Phase 1：单章闭环验证（进行中）**

- 4 个核心 Agent
- CLI 界面
- SQLite 单库
- 目标：连续 10 章，审查通过率 > 80%

---

## 2. 三阶段路线图

```
Phase 1: 单章闭环          Phase 2: 卷级连续性        Phase 3: 完整产品
─────────────────          ─────────────────          ────────────
验证：单章质量              验证：跨章连续              目标：产品化
范围：1 章闭环              范围：10 章连续             范围：整本生产
Agent：4 个                 Agent：6 个                Agent：10 个
存储：SQLite                存储：PG + Qdrant           存储：PG+Qdrant+Redis
界面：CLI                   界面：简单 Web              界面：Studio
周期：2-3 周                周期：4-6 周               周期：8-12 周
```

### Phase 1：单章闭环验证

**核心假设**：AI 能否在一致的上下文中，稳定产出质量合格的单章？

**范围**：项目设定 → 章节目标 → 上下文组装 → 生成 → 审查 → 修订 → 确认

**Agent（4 个）**：
- **Planner**：收集设定、制定章节目标、生成摘要
- **Writer**：按场景生成正文
- **Reviewer**：结构化审查（有证据的 issue 列表）
- **ContextManager**：组装"写作上下文包"、版本管理

**存储**：SQLite 单库（唯一的长期事实源）

**界面**：CLI（命令行交互）

**验证标准**：
- 3 个题材各 10 章
- 结构化审查通过率 > 80%
- 人工返工率 < 30%
- 平均质量评分 > 6/10
- 修订不引入新问题

### Phase 2：卷级连续性

**核心假设**：AI 能否在连续 10 章中保持设定和角色的一致性？

**新增 Agent（2 个）**：
- **WorldBuilder**：结构化世界观管理、设定快照
- **CharacterDesigner**：角色弧线追踪、关系图谱

**新增存储**：PostgreSQL + Qdrant（向量检索）

**新增功能**：伏笔追踪、时间线管理、章节摘要索引、简单 Web 界面

**验证标准**：
- 自动连续 10 章无需人工干预
- 跨章设定漂移 < 5%
- 角色行为一致性 > 85%
- 伏笔正确回收率 > 70%

### Phase 3：完整产品化

**目标**：面向新手的完整 AI 小说生产产品

**新增 Agent（4 个）**：
- **PlotPlanner**：宏观大纲、卷战略
- **StyleEngine**：风格提取与一致性
- **LoreKeeper**：RAG 知识库、拆书分析
- **ConflictResolver**：多 Agent 分歧仲裁

**新增基础设施**：Redis、Celery、WebSocket、LangSmith、Studio Web 工作台

---

## 3. 快速开始

### 环境要求

- Python 3.11+
- LLM API Key（DeepSeek / OpenAI 兼容接口）

### 安装（Phase 1）

```bash
# 克隆仓库
git clone https://github.com/yourusername/novel-forge.git
cd novel-forge

# 安装（纯 Python，无 Docker 依赖）
pip install -e ".[dev]"

# 配置环境变量
cp .env.example .env
# 编辑 .env，填入 LLM_API_KEY 和 LLM_BASE_URL

# 运行
novelforge --help
```

### 创建第一篇小说

```bash
# 交互式创建（7 步向导）
novelforge create-project

# 向导会问你：
# 1. 题材？（玄幻/都市/科幻...）
# 2. 核心灵感？（一句话描述）
# 3. 主角设定？（AI 可以建议）
# 4. 读者预期？（爽/燃/甜/虐...）
# 5. 禁忌事项？（可选）
# 6. 目标字数？（可选）
# 7. 书名？（AI 可以建议）

# 开始写作第 1 章
novelforge write --project mynovel --chapter 1

# 系统会：
# 1. 组装上下文包（设定+角色+前文摘要）
# 2. 生成章节初稿
# 3. 自动审查（设定/角色/时间线/质量）
# 4. 如有问题，自动修订（最多 2 轮）
# 5. 输出审查报告
# 6. 等待你确认或修改
```

### 查看结果

```bash
# 查看章节
novelforge show --project mynovel --chapter 1

# 查看审查报告
novelforge review --project mynovel --chapter 1

# 导出为 txt
novelforge export --project mynovel --format txt
```

---

## 4. 架构设计

### Phase 1 架构

```
┌─────────────────────────────────────────────┐
│            Phase 1: 单章闭环                 │
├─────────────────────────────────────────────┤
│                                             │
│  用户 → CLI → LangGraph 工作流               │
│                     │                       │
│         ┌───────────┼───────────┐           │
│         ▼           ▼           ▼           │
│      Planner    Writer    Reviewer          │
│         │           │           │           │
│         └─────┬─────┴─────┬─────┘           │
│               ▼           ▼                 │
│        ContextManager  SQLite               │
│        (上下文包组装)   (唯一事实源)          │
│                                             │
│  4 个 Agent | CLI 界面 | SQLite 单库         │
│                                             │
└─────────────────────────────────────────────┘
```

### 数据事实源

**铁律：SQLite 是唯一的长期事实源。**

| 存储 | 用途 | 持久性 |
|------|------|--------|
| **SQLite** | 所有业务数据（项目、角色、章节版本、审查报告） | ✅ 长期 |
| **Checkpoint** | 仅保存 LangGraph 执行现场（当前节点、状态） | ✅ 仅用于崩溃恢复 |
| **内存** | LLM 上下文窗口、临时计算 | ❌ 重启丢失 |

### 工作流

```
planner ──▶ context_manager ──▶ writer ──▶ reviewer
                                              │
                          ┌───────────────────┘
                          │
                    ┌─────┴─────┐
                    ▼           ▼
                  通过       有问题
                    │           │
                    ▼           ▼
                人工确认    issue-driven patch
                (END)       (最多 2 轮)
                              │
                              ▼
                         再次审查
                              │
                        ┌─────┴─────┐
                        ▼           ▼
                      通过       仍有问题
                        │           │
                        ▼           ▼
                    人工确认    上报人工
                    (END)       (END)
```

---

## 5. 核心设计

### 5.1 四个核心 Agent

| Agent | 职责 | 不做什么 |
|-------|------|----------|
| **Planner** | 收集设定、制定目标、生成摘要 | 不写正文 |
| **Writer** | 按场景生成正文、遵守约束 | 不做审查 |
| **Reviewer** | 结构化审查、输出 issue 列表 | 不直接改正文 |
| **ContextManager** | 组装上下文包、版本管理 | 不做生成/审查判断 |

### 5.2 写作上下文包（Context Package）

Phase 1 的上下文组装不是通用 RAG，而是**小说专用的分区注入结构**：

| 分区 | 内容 | 优先级 |
|------|------|--------|
| **硬约束** | 角色当前状态、已揭示设定、禁忌、本章必须完成的事项 | 必须遵守 |
| **软参考** | 相关世界观设定、角色背景、参考风格 | 建议遵循 |
| **最近剧情** | 前 3 章摘要 + 上一章结尾 500 字 | 高 |
| **角色状态** | 出场角色的完整状态快照 | 高 |
| **伏笔线索** | 已埋下未回收的伏笔、本章应回收的伏笔 | 中 |
| **本章目标** | 必须事件、情感走向、钩子、字数目标 | 高 |

### 5.3 结构化审查

Reviewer 的输出必须是**有证据的、可执行的** issue 列表：

```python
class ReviewIssue:
    category: str           # world_consistency / character_behavior / timeline / quality_*
    severity: str           # critical / major / minor / info
    evidence_quote: str     # 原文片段（必须有！）
    issue_description: str  # 问题描述
    expected: str           # 应该是什么
    actual: str             # 实际是什么
    suggested_fix: str      # 修复建议
    fix_type: str           # patch / rewrite_scene / confirm / register_setting
    confidence: float       # 0-1
```

**铁律**：没有 `evidence_quote` 的 critical/major issue 不进入自动修订。

### 5.4 Issue-Driven 修订

不是整章重写，而是**针对 issue 做局部 patch**：

1. 只修改有 issue 的部分，保留其他内容不变
2. 最多 **2 轮**自动修订
3. 第二轮审查如果引入新问题，立即停止并上报人工
4. `rewrite_scene` 类型的 issue 不自动修复，直接上报人工

### 5.5 版本管理

每次生成和修订都创建新版本，不覆盖旧版本：

```
draft_v1 (初稿)
  └── revision_v1 (第 1 轮修订)
       └── revision_v2 (第 2 轮修订)
            └── accepted (人工确认)
                 └── edited (人工编辑后)
```

### 5.6 新手创建向导

7 步 CLI 引导，让完全不懂写作的新手也能开始：

1. 题材选择 → 2. 核心灵感 → 3. 主角设定 → 4. 读者预期 → 5. 禁忌事项 → 6. 目标字数 → 7. 书名确认

每步 AI 实时生成建议，用户可以随时跳过或修改。

---

## 6. 评测标准

每个 Phase 有明确的完成标准：

### Phase 1 完成标准

| 指标 | 目标 | 测量方式 |
|------|------|----------|
| 结构化审查通过率 | > 80% | 10 章中无 critical/major 的比例 |
| 质量评分 | > 6/10 | Reviewer 的 overall_score 均值 |
| 人工返工率 | < 30% | 需人工大幅修改的章节比例 |
| 修订不引入新问题 | 100% | 第二轮审查新问题数 = 0 |
| 设定一致性 | 100% | critical world_consistency = 0 |
| 角色行为一致性 | > 85% | character_behavior major 以下比例 |

### 评测集

- 3 个题材：玄幻（修仙）、都市（异能）、科幻（星际）
- 每个题材 10 章
- 人工编写前 3 章作为种子，AI 生成第 4-13 章

---

## 7. 与其他项目对比

| 特性 | NovelForge (Phase 1) | AI-Novel-Writing-Assistant | InkOS | Terminal Velocity |
|------|---------------------|---------------------------|-------|-------------------|
| **当前阶段** | 单章闭环验证 | 整本生产（成熟） | 写-审-改循环（成熟） | 完全自主 |
| **Agent 数量** | 4 个（精简） | 10+ 个 | 1 个主循环 | 10 个 |
| **架构策略** | 三阶段渐进 | 终态架构 | 实用工具 | 实验性 |
| **人工参与** | 关键节点门控 | 阶段审核 | 审核门控 | 零人工 |
| **存储** | SQLite 单库 | Postgres + Qdrant | 本地文件 | Git |
| **界面** | CLI | Web + 桌面 | CLI + TUI | 脚本 |
| **审查输出** | 结构化 issue（有证据） | 综合报告 | 综合报告 | 无 |
| **修订策略** | Issue-driven patch（2轮） | 整章重写 | 整章重写 | 无 |
| **版本管理** | 版本链（不覆盖） | 基础 | 基础 | Git |
| **新手引导** | 7 步向导 | 自动导演 | 交互式 | 无 |

**我们的差异点**：
- **假设驱动**：不是一次性做全，而是分阶段验证核心假设
- **精简 Agent**：Phase 1 只有 4 个 Agent，降低编排复杂度
- **结构化审查**：审查结果必须有证据（原文引用），不是抽象评分
- **Issue-Driven 修订**：局部 patch 而非整章重写，避免越修越差
- **版本管理**：每次修订保存新版本，支持回溯

---

## 8. 开发文档

### 完整设计文档

- [完整系统架构设计](docs/01-architecture-design.md) — 三阶段落地架构、数据模型、数据库设计
- [Vibe Coding Prompt 工程](docs/02-vibe-coding-prompts.md) — System Prompt、Agent Prompt、测试 Prompt

### 项目结构

```
novelforge/
├── pyproject.toml
├── .env.example
├── README.md
└── src/novelforge/
    ├── __init__.py
    ├── cli.py              # CLI 入口 + 新手向导
    ├── config.py           # 配置管理
    ├── database.py         # SQLite 操作
    ├── models.py           # Pydantic 模型
    ├── graph.py            # LangGraph 工作流
    ├── agents/
    │   ├── __init__.py
    │   ├── planner.py      # Planner Agent
    │   ├── writer.py       # Writer Agent
    │   ├── reviewer.py     # Reviewer Agent
    │   └── context_manager.py  # ContextManager Agent
    └── utils.py            # 工具函数
```

### 开发环境

```bash
# 安装开发依赖
pip install -e ".[dev]"

# 运行测试
pytest tests/ -v

# 运行评测
python scripts/evaluate.py

# CLI 开发模式
novelforge --debug write --project test --chapter 1
```

---

## 9. 参考与致谢

本项目的设计参考了以下优秀开源项目：

| 项目 | 作者 | 主要参考点 |
|------|------|------------|
| [AI-Novel-Writing-Assistant](https://github.com/ExplosiveCoderflome/AI-Novel-Writing-Assistant) | ExplosiveCoderflome | 导演模式工作流、世界观管理 |
| [InkOS](https://github.com/Narcooo/inkos) | Narcooo | 写-审-改循环、人工门控、TUI |
| [Terminal Velocity](https://github.com/mind-protocol/terminal-velocity) | mind-protocol | 多 Agent 自主协作架构 |
| [Tonade_DSv4-flash_100w_novel_agent](https://github.com/Tonade-sun/Tonade_DSv4-flash_100w_novel_agent) | Tonade-sun | RAG 记忆机制、DeepSeek 集成 |

特别感谢 [LangGraph](https://github.com/langchain-ai/langgraph) 团队。

---

## 10. 许可证

AGPL-3.0

---

> **项目状态**: Phase 1 开发中（单章闭环验证）  
> **欢迎贡献**: 特别是在评测集建设、Prompt 调优、新题材适配方面
