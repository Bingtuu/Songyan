技术不是越复杂越好，而是越够用越好。
墨只需要烟和胶，不需要金银。

# Songyan（松烟）— 技术参考手册

## V2.0 版

> **版本**: V2.0.0
> **日期**: 2026-05-24
> **目标读者**: 协作开发的 AI 编程助手、技术决策者
> **用途**: 技术选型说明、工具约束、调试参考
> **变更**: 基于 v2 review——CreativeModeProfile、CreativeDirector、双层审查(RuleAuditor+LLMAuditor)、LiteraryAuditor、SettlementExtractor

---

## 目录

- [1. 技术栈总览](#1-技术栈总览)
- [2. 技术选型理由](#2-技术选型理由)
- [3. 工具约束与负面清单](#3-工具约束与负面清单)
- [4. Agent 调用关系图](#4-agent-调用关系图)
- [5. 数据流图](#5-数据流图)
- [6. 数据事实源规则](#6-数据事实源规则)
- [7. 上下文 Token 预算管理](#7-上下文-token-预算管理)
- [8. CreativeModeProfile 技术实现](#8-creativemodeprofile-技术实现)
- [9. Genre Profile 技术实现](#9-genre-profile-技术实现)
- [10. 双层审查技术细节](#10-双层审查技术细节)
- [11. LiteraryAuditor 技术细节](#11-literaryauditor-技术细节)
- [12. 状态结算技术细节](#12-状态结算技术细节)
- [13. 错误处理策略](#13-错误处理策略)
- [14. 性能监控](#14-性能监控)
- [15. 多 LLM 支持说明](#15-多-llm-支持说明)
- [16. 技术债务与升级路径](#16-技术债务与升级路径)
- [17. 调试指南](#17-调试指南)

---

## 1. 技术栈总览

| 组件 | 选型 | 版本 | 用途 |
|------|------|------|------|
| **Python** | 3.11+ | 3.11 | 运行环境，async/await |
| **Pydantic** | v2 | >=2.0 | 数据模型、类型校验 |
| **LangGraph** | >=0.2 | >=0.2 | 工作流编排 |
| **LangChain** | >=0.3 | >=0.3 | LLM 接口 |
| **litellm** | latest | latest | 多模型统一接口 |
| **SQLite** | 内置 | 3.x | 唯一事实源 |
| **Click** | latest | latest | CLI 框架 |
| **structlog** | latest | latest | 结构化日志 |
| **tiktoken** | latest | latest | Token 计数 |
| **pytest** | +pytest-asyncio | >=7 | 测试框架 |

---

## 2. 技术选型理由

### 2.1 为什么不用 vLLM/Ollama 本地模型

**答案**：V1.0 阶段不需要。

- V1.0 验证的是"在足够一致的上下文中能否产出合格章节"
- 这个假设验证不依赖模型是否本地
- 使用兼容 OpenAI API 的远程模型（DeepSeek、GPT-4o 等）即可
- litellm 提供统一接口，后续切换到本地模型不需要改业务代码

**升级路径**：V2.0 再考虑 vLLM + 微调，通过 litellm 切换。

### 2.2 为什么不用 Mem0/PostgreSQL/Qdrant

**答案**：V1.0 用不到。

| 组件 | 为什么不需要 | 什么时候需要 |
|------|-------------|-------------|
| **Mem0** | V1.0 单章闭环，不需要长期记忆管理 | V1.5 连续章节 |
| **PostgreSQL** | SQLite 在单用户场景下性能足够 | V2.0 多用户并发 |
| **Qdrant** | V1.0 通过最近章节摘要 + 硬约束获取上下文，不需要语义检索 | V2.0 长篇跨章上下文 |
| **Redis** | V1.0 无并发、无缓存需求 | V1.5+ 状态缓存 |

**升级路径**：V1.5 引入 Mem0 + Redis（可选），V2.0 引入 Qdrant 做跨章语义检索。

### 2.3 为什么不用 Celery/ARQ

**答案**：V1.0 不需要任务队列。

- V1.0 是单用户、单章、串行流程
- LangGraph 本身就是异步编排框架
- 不需要分布式任务处理

**升级路径**：V2.0 需要批量生产时引入 Celery。

### 2.4 为什么 litellm 是统一 LLM 接口

**理由**：
- 兼容 OpenAI API 格式
- 支持多提供商（OpenAI、DeepSeek、Anthropic、本地 vLLM）
- 统一接口切换模型不需要改业务代码
- 支持 temperature、max_tokens 等参数透传

### 2.5 为什么 Pydantic v2（不是 v1）

- V2 性能更好（Rust 核心）
- V2 API 更一致
- 所有现代 Python 生态都已迁移到 v2
- V1 已被官方标记为 deprecated

### 2.6 为什么需要 CreativeModeProfile ⭐

**问题**：同一个系统如何同时服务网文作者和严肃文学创作者？

**答案**：不是两套代码，而是同一套"管线 + 插件"架构，通过 CreativeModeProfile 配置：

- 网文模式：节奏/爽点/钩子权重高，容忍一定套路
- 严肃文学：人物自治/概念落地/裂隙保留权重高，零容忍套路
- 混合模式：平衡两者

**技术实现**：JSON 配置文件 + Registry 注册表，新增模式只需新增 JSON。

### 2.7 为什么 Reviewer 要双层化 ⭐

**问题**：15 个维度全用 LLM 判断，又慢又贵。

**答案**：拆分为 RuleAuditor（代码）+ LLMAuditor（LLM）：

| 维度 | 适合 | 方式 | 耗时 | 成本 |
|------|------|------|------|------|
| AI 腔/疲劳词/段落/首屏/字数 | 代码规则 | RuleAuditor | < 200ms | 零 |
| 角色行为/节奏/对话/设定一致性 | 语义理解 | LLMAuditor | ~30s | LLM 费用 |

- RuleAuditor 先跑（< 200ms），LLMAuditor 后跑（~30s）
- 如果 RuleAuditor 发现大量 critical，可以跳过 LLMAuditor（快速失败）
- 合并为 MergedReviewReport，统一输出格式

---

## 3. 工具约束与负面清单

### 绝对禁止（V1.0）

| 禁止项 | 原因 | 替代方案 |
|--------|------|----------|
| **React Web UI** | V1.0 只做 CLI | 不用，V2.0 再说 |
| **PostgreSQL** | V1.0 单库够了 | SQLite |
| **Qdrant** | V1.0 不需要向量检索 | 最近章节摘要 |
| **Redis** | V1.0 无并发/缓存需求 | 内存 |
| **Celery** | V1.0 单章串行 | LangGraph 原生 |
| **ARQ** | V1.0 不需要任务队列 | LangGraph 原生 |
| **Mem0** | V1.0 单章闭环 | SQLite + 摘要 |
| **模板市场** | V1.0 不做 | 内置 3 题材 + 3 模式 |
| **多租户** | V1.0 不做 | 单用户 |
| **复杂权限** | V1.0 不做 | 无权限 |
| **vLLM** | V1.0 用远程模型 | litellm |
| **Ollama** | V1.0 用远程模型 | litellm |

### 可选但非必须

| 可选项 | 什么时候需要 | 说明 |
|--------|-------------|------|
| **Click 装饰器模式** | V1.0 可选 | 可以用，但不强求 |
| **Jinja2 模板** | V1.0 可选 | Prompt 直接 Python 字符串拼接 |
| **rich 库** | V1.0 可选 | CLI 美化，但不强求 |

---

## 4. Agent 调用关系图

### 4.1 修正后的拓扑（基于 v2 review）⭐

```
┌─────────────────────────────────────────────────────────────────┐
│                  Songyan V1.0 Agent 拓扑（修正后）                │
├─────────────────────────────────────────────────────────────────┤
│                                                                  │
│  ┌──────────────┐                                               │
│  │     CLI      │                                               │
│  │  (Click)     │                                               │
│  └──────┬───────┘                                               │
│         │                                                        │
│         ▼                                                        │
│  ┌──────────────────────────────────────────────────┐           │
│  │            LangGraph 工作流（修正顺序）             │           │
│  │                                                  │           │
│  │  ┌─────────────────┐                            │           │
│  │  │  goal_planner    │ 制定 ChapterGoal           │           │
│  │  │                 │ 项目设定收集                │           │
│  │  └────────┬────────┘                            │           │
│  │           │                                      │           │
│  │           ▼                                      │           │
│  │  ┌─────────────────┐                            │           │
│  │  │ creative_director│ 生成 CreativeBrief         │           │
│  │  │                 │ 创作意图+张力地图            │           │
│  │  │                 │ 温度 0.7                   │           │
│  │  └────────┬────────┘                            │           │
│  │           │                                      │           │
│  │           ▼                                      │           │
│  │  ┌─────────────────┐                            │           │
│  │  │ context_manager  │ 加载 Genre + Mode Profile  │           │
│  │  │                 │ 组装 ContextPackage          │           │
│  │  │                 │ Token 预算管理               │           │
│  │  │                 │ 保存 snapshot               │           │
│  │  └────────┬────────┘                            │           │
│  │           │                                      │           │
│  │           ▼                                      │           │
│  │  ┌─────────────────┐                            │           │
│  │  │     writer       │ 按场景生成正文              │           │
│  │  │                 │ 输入: ContextPackage        │           │
│  │  │                 │        + CreativeBrief      │           │
│  │  │                 │        + Craft Card         │           │
│  │  │                 │ 温度 0.7                   │           │
│  │  └────────┬────────┘                            │           │
│  │           │                                      │           │
│  │           ▼                                      │           │
│  │  ┌─────────────────┐    ┌─────────────────────┐ │           │
│  │  │  rule_auditor    │    │  Quality Utils      │ │           │
│  │  │                 │    │                     │ │           │
│  │  │  代码层规则检测   │───▶│  - ai_tells.py      │ │           │
│  │  │  - AI 腔         │    │  - fatigue_words.py │ │           │
│  │  │  - 疲劳词        │    │  - hook_checker.py  │ │           │
│  │  │  - 段落节奏       │    │  - paragraph_rhythm │ │           │
│  │  │  - 首屏/章末钩子  │    │  - token_counter.py │ │           │
│  │  │  耗时 < 200ms   │    └─────────────────────┘ │           │
│  │  └────────┬────────┘                            │           │
│  │           │                                      │           │
│  │           ▼                                      │           │
│  │  ┌─────────────────┐                            │           │
│  │  │  llm_auditor     │ 语义审查（LLM调用）         │           │
│  │  │                 │ 12维度                      │           │
│  │  │  - 角色行为       │ 温度 0.3                   │           │
│  │  │  - 叙事节奏       │                            │           │
│  │  │  - 对话区分度     │                            │           │
│  │  │  - 设定一致性     │                            │           │
│  │  │  耗时 ~30s      │                            │           │
│  │  └────────┬────────┘                            │           │
│  │           │                                      │           │
│  │           ▼                                      │           │
│  │  ┌─────────────────┐                            │           │
│  │  │  review_merger   │ 合并 Rule + LLM 结果       │           │
│  │  │                 │ 输出 MergedReviewReport     │           │
│  │  └────────┬────────┘                            │           │
│  │           │                                      │           │
│  │           ▼                                      │           │
│  │  ┌─────────────────┐                            │           │
│  │  │ literary_auditor │ 文学性诊断（LLM调用）       │           │
│  │  │                 │ 不阻塞流程                  │           │
│  │  │  - 人物工具化     │ 温度 0.3                   │           │
│  │  │  - 概念空转       │                            │           │
│  │  │  - 有价值裂隙     │                            │           │
│  │  │  耗时 ~10s      │                            │           │
│  │  └────────┬────────┘                            │           │
│  │           │                                      │           │
│  │           ▼                                      │           │
│  │  ┌─────────────────┐                            │           │
│  │  │ revision_handler │ issue-driven patch 修订    │           │
│  │  │                 │ 保护 valuable_fissure      │           │
│  │  │                 │ 最多 2 轮                   │           │
│  │  └────────┬────────┘                            │           │
│  │           │                                      │           │
│  │           ▼                                      │           │
│  │  ┌─────────────────┐                            │           │
│  │  │ human_confirm    │                            │           │
│  │  │                 │                            │           │
│  │  │  - accept       │ ──→ settlement_extractor   │           │
│  │  │  - edit         │ ──→ 编辑器修改 ──→ accept  │           │
│  │  │  - reject       │ ──→ goal_planner（重新规划）│           │
│  │  │  - back         │ ──→ 指定版本               │           │
│  │  └─────────────────┘                            │           │
│  │                                                  │           │
│  │  ┌──────────────────────────────────────────┐   │           │
│  │  │          settlement_extractor             │   │           │
│  │  │  - 角色状态变更 INSERT                    │   │           │
│  │  │  - 新设定登记（setting_key）              │   │           │
│  │  │  - 伏笔操作（source_version_id）          │   │           │
│  │  │  - 数值变更验证                          │   │           │
│  │  └──────────────────────────────────────────┘   │           │
│  └──────────────────────────────────────────────────┘           │
│                                                                  │
│  ┌──────────────────────────────────────────────────┐           │
│  │              SQLite 单库（唯一事实源）              │           │
│  │  projects / characters / character_states(INSERT) │           │
│  │  chapter_versions(UNIQUE) / review_reports        │           │
│  │  literary_observations / creative_briefs          │           │
│  │  setting_snapshots(setting_key) / foreshadowings  │           │
│  │  numerical_ledgers / summaries / chapter_heads    │           │
│  └──────────────────────────────────────────────────┘           │
│                                                                  │
│  ┌──────────────────────────────────────────────────┐           │
│  │              Genre Profile 配置库                   │           │
│  │  genres/xuanhuan.json                            │           │
│  │  genres/urban.json                               │           │
│  │  genres/scifi.json                               │           │
│  └──────────────────────────────────────────────────┘           │
│                                                                  │
│  ┌──────────────────────────────────────────────────┐           │
│  │           CreativeModeProfile 配置库               │           │
│  │  creative_modes/webnovel.json                    │           │
│  │  creative_modes/literary.json                    │           │
│  │  creative_modes/hybrid.json                      │           │
│  └──────────────────────────────────────────────────┘           │
│                                                                  │
│  ┌──────────────────────────────────────────────────┐           │
│  │              Prompt 模板库                         │           │
│  │  prompts/writer.md                               │           │
│  │  prompts/craft_card.md  ← 写作工艺层               │           │
│  │  prompts/creative_director.md ← 创作导演           │           │
│  │  prompts/goal_planner.md                         │           │
│  │  prompts/rule_auditor.md ← 规则检测               │           │
│  │  prompts/llm_auditor.md ← 语义审查                │           │
│  │  prompts/literary_auditor.md ← 文学审计           │           │
│  │  prompts/settlement_extractor.md                  │           │
│  └──────────────────────────────────────────────────┘           │
└─────────────────────────────────────────────────────────────────┘
```

---

## 5. 数据流图

### 5.1 核心数据流（修正后）⭐

```
用户 CLI 命令
    |
    ▼
┌──────────────────────────────────────────────────────────┐
│                    GoalPlanner                            │
│  输入: project_id, chapter_number                         │
│  输出: ChapterGoal                                        │
└──────────────────┬───────────────────────────────────────┘
                   |
                   ▼
┌──────────────────────────────────────────────────────────┐
│                    CreativeDirector                       │
│  输入: ChapterGoal + Genre Profile + 角色状态              │
│  输出: CreativeBrief（创作意图+张力地图+禁忌清单）          │
│  保存: INSERT creative_briefs                             │
└──────────────────┬───────────────────────────────────────┘
                   |
                   ▼
┌──────────────────────────────────────────────────────────┐
│                    ContextManager                         │
│  输入: project_id, chapter_number, CreativeBrief          │
│  加载: Genre Profile → CreativeModeProfile → SQLite 数据  │
│  组装: ContextPackage（含 CreativeBrief 注入）             │
│  预算: tiktoken 估算 → 裁剪 → snapshot 保存               │
│  输出: ContextPackage (含 genre_rules + mode_rules)       │
└──────────────────┬───────────────────────────────────────┘
                   |
                   ▼
┌──────────────────────────────────────────────────────────┐
│                    Writer                                 │
│  输入: ContextPackage + ChapterGoal + CreativeBrief       │
│  处理: 加载 craft_card.md → 组装 Prompt → LLM 调用        │
│  输出: ChapterVersion (type=draft, 含 creative_brief_id)  │
│  保存: INSERT chapter_versions (含 context_snapshot)      │
└──────────────────┬───────────────────────────────────────┘
                   |
                   ▼
┌──────────────────────────────────────────────────────────┐
│                    RuleAuditor                            │
│  输入: chapter_version_id                                 │
│  处理: 加载正文 → 代码规则检测（< 200ms）                  │
│  输出: RuleAuditResult（ai_tell_count, fatigue_count...） │
│  保存: 不保存（运行时计算）                                │
└──────────────────┬───────────────────────────────────────┘
                   |
                   ▼
┌──────────────────────────────────────────────────────────┐
│                    LLMAuditor                             │
│  输入: chapter_version_id + context_snapshot              │
│  处理: 加载正文 → 12 维度语义审查 → LLM 调用              │
│  输出: LLMAuditResult（issues + dimension_scores）        │
│  保存: INSERT review_reports (含 rule + llm 结果)         │
└──────────────────┬───────────────────────────────────────┘
                   |
                   ▼
┌──────────────────────────────────────────────────────────┐
│                    ReviewMerger                           │
│  输入: RuleAuditResult + LLMAuditResult                   │
│  处理: 合并为 MergedReviewReport                          │
│  输出: MergedReviewReport（统一 issue 列表）               │
│  更新: UPDATE review_reports (merged 结果)                │
└──────────────────┬───────────────────────────────────────┘
                   |
                   ▼
┌──────────────────────────────────────────────────────────┐
│                    LiteraryAuditor                        │
│  输入: chapter_version_id + MergedReviewReport            │
│  处理: LLM 调用 → 文学性诊断                              │
│  输出: LiteraryAuditResult（observations，不阻塞）        │
│  保存: INSERT literary_observations                       │
│  注意: 不阻塞流程，无论结果如何继续                        │
└──────────────────┬───────────────────────────────────────┘
                   |
           ┌───────┴────────┐
           ▼                ▼
      无 critical/     有 critical/major
       major           |
           |           ▼
           |    ┌──────────────────┐
           |    │ RevisionHandler  │
           |    │ - 筛选 patchable │
           |    │ - 排除 fissure   │
           |    │ - 从后往前 patch │
           |    │ - 新版本 revision│
           |    └────────┬─────────┘
           |              |
           |              ▼
           |         RuleAuditor（重新检测）
           |              |
           |              ▼
           |         LLMAuditor（重新审查）
           |              |
           |         ┌────┴────┐
           |      通过      仍有 issues
           |         |         |
           |         |    第 2 轮？
           |         |    Y → patch
           |         |    N → human_confirm
           |         |
           └────┬────┘
                ▼
        ┌──────────────────┐
        │  HumanConfirm     │
        │  - accept → settlement_extractor
        │  - edit → 编辑器 → accept
        │  - reject → goal_planner
        │  - back → 指定版本
        └────────┬─────────┘
                 ▼
        ┌──────────────────┐
        │ SettlementExtractor│ ⭐
        │ 输入: accepted 正文 + DB 当前状态
        │ 处理: LLM 提取 → 代码验证 → INSERT 新快照
        │ 验证: old_value, source_quote, setting_key, closing_value
        │ 失败: needs_human_review
        └────────┬─────────┘
                 ▼
        ┌──────────────────┐
        │  摘要生成         │
        │  UPDATE chapter_heads
        └──────────────────┘
```

---

## 6. 数据事实源规则

### 铁律

**SQLite 是 V1.0 唯一长期事实源。**

### LangGraph state 中允许存什么

```python
class Phase1State(TypedDict):
    """LangGraph state 中只允许存这些字段"""
    project_id: str
    chapter_number: int
    mode_id: str                          # 创作模式 ID ⭐
    current_version_id: str | None        # chapter_versions.id
    review_report_id: str | None          # review_reports.id
    creative_brief_id: str | None         # creative_briefs.id ⭐
    literary_observation_id: str | None   # literary_observations.id ⭐
    revision_round: int                   # 0, 1, 2
    status: str                           # 状态机状态
```

### LangGraph state 中禁止存什么

- 完整章节正文
- 完整上下文包（ContextPackage）
- 完整审查报告（MergedReviewReport）
- 完整文学审计（LiteraryAuditResult）
- 完整角色档案
- Genre Profile 内容
- CreativeModeProfile 内容
- CreativeBrief 内容
- Prompt 文本

### 各节点如何获取数据

| 节点 | 数据来源 | 说明 |
|------|----------|------|
| goal_planner | SQLite (projects, characters, chapter_versions) | 制定目标时 |
| creative_director | SQLite (projects, characters) + ChapterGoal | 生成创作意图 |
| context_manager | SQLite (projects, characters, summaries, foreshadowings) + genres/*.json + creative_modes/*.json | 实时组装 ⭐ |
| writer | ContextPackage (内存) | 从 context_manager 传入 |
| rule_auditor | chapter_versions.content (内存) | 代码检测，不查 DB |
| llm_auditor | SQLite (chapter_versions) + context_snapshot | 加载正文 + snapshot |
| literary_auditor | SQLite (chapter_versions) + MergedReviewReport | 加载正文 + 审查结果 ⭐ |
| review_merger | RuleAuditResult + LLMAuditResult (内存) | 内存合并 |
| revision_handler | SQLite (chapter_versions) + patchable_issues | 加载原始版本 |
| human_confirm | SQLite (chapter_versions, review_reports, literary_observations) | 显示 + 确认 ⭐ |
| settlement_extractor | SQLite (所有状态表) + accepted 正文 | 结算 + 更新 |

---

## 7. 上下文 Token 预算管理

### 默认预算分配

```python
@dataclass
class ContextBudget:
    total_budget: int = 32_000           # 总预算
    generation_reserve: int = 8_000      # 预留生成空间
    available: int = 24_000              # 实际可用
    
    # 分区预算上限
    hard_constraints_max: int = 6_000
    character_states_max: int = 5_000
    recent_plot_max: int = 6_000
    foreshadowing_max: int = 2_000
    soft_references_max: int = 3_000
    chapter_goal_max: int = 2_000
    creative_brief_max: int = 1_500      # ⭐ 新增：CreativeBrief 预算
    mode_rules_max: int = 500            # ⭐ 新增：ModeRules 预算（很小）
```

### 裁剪策略（优先级从高到低）⭐

```
1. soft_references 减少到 1000 tokens
2. soft_references 完全移除
3. creative_brief 描述压缩（保留核心约束，压缩张力描述）⭐
4. recent_plot 从 3 章减到 2 章
5. character_states 只保留核心字段（去掉 backstory）
6. foreshadowing 只保留 planted 和 due
7. mode_rules 不裁剪（很小，500 tokens）⭐
8. 报错：上下文不足
```

### Token 计数方式

```python
import tiktoken

def estimate_tokens(text: str, model: str = "gpt-4") -> int:
    encoder = tiktoken.encoding_for_model(model)
    return len(encoder.encode(text))
```

---

## 8. CreativeModeProfile 技术实现

### 8.1 注册表

```python
# songyan/creative_modes/registry.py
import json
from pathlib import Path
from songyan.models.creative_mode import CreativeModeProfile

MODES_DIR = Path(__file__).parent.parent.parent / "creative_modes"

class CreativeModeRegistry:
    _cache: dict[str, CreativeModeProfile] = {}
    
    @classmethod
    def register(cls, mode: CreativeModeProfile) -> None:
        cls._cache[mode.id] = mode
    
    @classmethod
    def get(cls, mode_id: str) -> CreativeModeProfile:
        if mode_id in cls._cache:
            return cls._cache[mode_id]
        
        path = MODES_DIR / f"{mode_id}.json"
        if not path.exists():
            raise ValueError(f"未知创作模式: {mode_id}，可用: {cls.list_modes()}")
        
        data = json.loads(path.read_text(encoding="utf-8"))
        profile = CreativeModeProfile(**data)
        cls._cache[mode_id] = profile
        return profile
    
    @classmethod
    def list_modes(cls) -> list[str]:
        return [p.stem for p in MODES_DIR.glob("*.json")]
    
    @classmethod
    def load_all(cls) -> None:
        """启动时加载所有模式"""
        for path in MODES_DIR.glob("*.json"):
            mode_id = path.stem
            cls.get(mode_id)
```

### 8.2 在 ContextManager 中的注入

```python
# agents/context_manager.py
from songyan.creative_modes.registry import CreativeModeRegistry

def assemble_context_package(...) -> ContextPackage:
    # ... 加载 Genre Profile ...
    
    # 加载 CreativeModeProfile ⭐
    mode = CreativeModeRegistry.load(project.mode_id)
    
    # 注入 ModeRules
    mode_rules = ModeRules(
        mode_id=mode.id,
        revision_policy=mode.revision_policy,
        tolerance_max_ai_tells=mode.tolerance.get("max_ai_tells", 2.0),
        tolerance_max_fatigue_words=mode.tolerance.get("max_fatigue_words", 3.0),
        tolerance_max_cliche_risk=mode.tolerance.get("max_cliche_risk", 2.0),
        context_pruning_strategy=mode.context_pruning_strategy,
    )
    
    # 组装 ContextPackage
    context = ContextPackage(
        # ...
        mode_rules=mode_rules,
        # ...
    )
    
    # Token 预算检查（含 CreativeBrief）
    estimated = estimate_context_tokens(context)
    if estimated > budget.available:
        context = prune_context(context, budget)
    
    return context
```

---

## 9. Genre Profile 技术实现

### 9.1 加载器（不变）

```python
# songyan/genres/loader.py
import json
from pathlib import Path
from songyan.models.genre import GenreProfile

GENRES_DIR = Path(__file__).parent.parent.parent / "genres"

class GenreProfileLoader:
    _cache: dict[str, GenreProfile] = {}
    
    @classmethod
    def load(cls, genre_id: str) -> GenreProfile:
        if genre_id in cls._cache:
            return cls._cache[genre_id]
        
        path = GENRES_DIR / f"{genre_id}.json"
        if not path.exists():
            raise ValueError(f"未知题材: {genre_id}，可用: {cls.list_genres()}")
        
        data = json.loads(path.read_text(encoding="utf-8"))
        profile = GenreProfile(**data)
        cls._cache[genre_id] = profile
        return profile
    
    @classmethod
    def list_genres(cls) -> list[str]:
        return [p.stem for p in GENRES_DIR.glob("*.json")]
```

### 9.2 在 Writer 中的注入（不变）

见 V1.0 文档。

### 9.3 在 RuleAuditor 中的注入 ⭐

```python
# agents/rule_auditor.py
from songyan.genres.loader import GenreProfileLoader
from songyan.utils.fatigue_words import detect_fatigue_words

def audit_fatigue_words(chapter_content: str, genre_id: str) -> list[FatigueWordMatch]:
    genre = GenreProfileLoader.load(genre_id)
    return detect_fatigue_words(chapter_content, genre.fatigue_words)
```

---

## 10. 双层审查技术细节

### 10.1 RuleAuditor 实现 ⭐

```python
# agents/rule_auditor.py
import time
from songyan.utils.ai_tells import detect_ai_tells
from songyan.utils.fatigue_words import detect_fatigue_words
from songyan.utils.hook_checker import check_opening_hook, check_ending_hook
from songyan.utils.paragraph_rhythm import analyze_paragraph_rhythm
from songyan.utils.numerical_validator import validate_numerical_formulas

async def audit_rules(
    chapter_content: str,
    word_count_target: int,
    genre_id: str | None = None,
    numerical_context: NumericalContext | None = None,
) -> RuleAuditResult:
    """代码层规则检测——全部代码执行，不调用 LLM"""
    start = time.monotonic()
    
    # 并行执行所有检测
    ai_tells = detect_ai_tells(chapter_content)
    fatigue = detect_fatigue_words(chapter_content, genre_id)
    opening_hook = check_opening_hook(chapter_content)
    ending_hook = check_ending_hook(chapter_content)
    rhythm = analyze_paragraph_rhythm(chapter_content)
    word_count = len(chapter_content)
    
    # 数值验证（仅玄幻）
    numerical_issues = []
    if numerical_context:
        numerical_issues = validate_numerical_formulas(chapter_content, numerical_context)
    
    duration_ms = int((time.monotonic() - start) * 1000)
    
    return RuleAuditResult(
        ai_tell_matches=ai_tells,
        ai_tell_count=len(ai_tells),
        fatigue_word_matches=fatigue,
        fatigue_word_count=sum(f.count for f in fatigue),
        has_opening_hook=opening_hook,
        has_ending_hook=ending_hook,
        paragraph_rhythm_score=rhythm.score,
        rhythm_issues=rhythm.issues,
        word_count=word_count,
        word_count_target=word_count_target,
        word_count_ok=word_count_target * 0.8 <= word_count <= word_count_target * 1.3,
        numerical_issues=numerical_issues,
        duration_ms=duration_ms,
    )
```

**性能目标**：所有检测 < 200ms。

### 10.2 LLMAuditor 实现 ⭐

```python
# agents/llm_auditor.py
from langchain_community.chat_models import ChatLiteLLM

async def audit_semantics(
    chapter_content: str,
    hard_constraints: list[HardConstraint],
    character_states: list[CharacterStateSnapshot],
    chapter_goal: ChapterGoal,
    creative_brief: CreativeBrief | None,
    reviewer_focus: list[str],
) -> LLMAuditResult:
    """LLM 语义审查——调用 LLM，需要语义理解"""
    
    llm = ChatLiteLLM(
        model=os.getenv("LLM_MODEL", "deepseek-chat"),
        temperature=0.3,  # 低温度，精确
    )
    
    # 构建 prompt（含 CreativeBrief）
    prompt = build_llm_auditor_prompt(
        chapter_content=chapter_content,
        hard_constraints=hard_constraints,
        character_states=character_states,
        chapter_goal=chapter_goal,
        creative_brief=creative_brief,
        reviewer_focus=reviewer_focus,
    )
    
    response = await llm.ainvoke(prompt)
    
    # 解析为 LLMAuditResult
    result = parse_llm_audit_response(response.content)
    return result
```

**性能目标**：单次调用 ~30s（取决于模型和章节长度）。

### 10.3 ReviewMerger 实现 ⭐

```python
# agents/review_merger.py（可内联为轻量函数）

def merge_audit_reports(
    rule_audit: RuleAuditResult | None,
    llm_audit: LLMAuditResult | None,
    chapter_version_id: str,
) -> MergedReviewReport:
    """合并 RuleAuditor 和 LLMAuditor 的结果"""
    
    # 从 RuleAuditor 转换 issues
    rule_issues = _convert_rule_to_issues(rule_audit) if rule_audit else []
    
    # 从 LLMAuditor 获取 issues
    llm_issues = llm_audit.issues if llm_audit else []
    
    # 合并（去重：同一位置的同一类型 issue 合并）
    merged_issues = _deduplicate_issues(rule_issues + llm_issues)
    
    # 计算 overall_score（加权平均）
    dimension_scores = {}
    if llm_audit:
        dimension_scores.update(llm_audit.dimension_scores)
    if rule_audit:
        dimension_scores["style_ai_tells"] = max(0, 10 - rule_audit.ai_tell_count * 2)
        dimension_scores["style_fatigue_words"] = max(0, 10 - rule_audit.fatigue_word_count * 1.5)
        dimension_scores["style_paragraph_rhythm"] = rule_audit.paragraph_rhythm_score
    
    overall_score = sum(dimension_scores.values()) / len(dimension_scores) if dimension_scores else 0
    
    return MergedReviewReport(
        chapter_version_id=chapter_version_id,
        rule_audit=rule_audit,
        llm_audit=llm_audit,
        issues=merged_issues,
        overall_score=overall_score,
        ai_tell_count=rule_audit.ai_tell_count if rule_audit else 0,
        fatigue_word_count=rule_audit.fatigue_word_count if rule_audit else 0,
        has_opening_hook=rule_audit.has_opening_hook if rule_audit else False,
        has_ending_hook=rule_audit.has_ending_hook if rule_audit else False,
        dimension_scores=dimension_scores,
        summary=_generate_summary(merged_issues, dimension_scores),
    )
```

---

## 11. LiteraryAuditor 技术细节

### 11.1 实现 ⭐

```python
# agents/literary_auditor.py

async def diagnose_literary_quality(
    chapter_content: str,
    creative_brief: CreativeBrief | None,
    llm_audit_result: LLMAuditResult | None,
    mode_id: str,
) -> LiteraryAuditResult:
    """
    文学性诊断——LLM 调用，诊断不阻塞。
    
    核心原则：
    - 不阻塞入库
    - valuable_fissure 不是缺陷
    - 不输出 fix，只输出 observation
    """
    
    llm = ChatLiteLLM(
        model=os.getenv("LLM_MODEL", "deepseek-chat"),
        temperature=0.3,
    )
    
    prompt = build_literary_auditor_prompt(
        chapter_content=chapter_content,
        creative_brief=creative_brief,
        llm_audit_result=llm_audit_result,
        mode_id=mode_id,
    )
    
    response = await llm.ainvoke(prompt)
    
    result = parse_literary_audit_response(response.content)
    
    # 强制设置：不阻塞
    result.blocking = False
    
    return result
```

### 11.2 保护 valuable_fissure

```python
# 在 RevisionHandler 中
def filter_patchable_issues(
    issues: list[ReviewIssue],
    literary_observations: list[LiteraryObservation],
) -> list[ReviewIssue]:
    """
    过滤可 patch 的 issues：
    - 只保留 severity 为 critical/major 的
    - 只保留 fix_type 为 patch 的
    - **排除 LiteraryAuditor 标记为 valuable_fissure 的位置**
    """
    # 获取被保护的位置
    protected_locations = set()
    for obs in literary_observations:
        if obs.observation_type == "valuable_fissure" and obs.preserve:
            if obs.evidence_quote:
                protected_locations.add(obs.evidence_quote[:50])  # 前50字作为标识
    
    patchable = []
    for issue in issues:
        if issue.severity not in ("critical", "major"):
            continue
        if issue.fix_type != "patch":
            continue
        # 检查是否在被保护的位置
        if issue.evidence_quote and any(
            loc in issue.evidence_quote for loc in protected_locations
        ):
            continue  # 跳过被保护的裂隙
        patchable.append(issue)
    
    return patchable
```

---

## 12. 状态结算技术细节

### 12.1 结算流程（更新）⭐

```python
# agents/settlement_extractor.py

async def extract_settlement(
    db: Repository,
    version_id: str,
    project_id: str,
    chapter_number: int,
) -> StateSettlement:
    """执行状态结算——INSERT 新快照，不 UPDATE 旧记录"""
    
    # 1. 加载数据
    version = await db.chapter_versions.get(version_id)
    current_states = await db.character_states.list_latest(project_id)
    current_settings = await db.setting_snapshots.list_by_project(project_id)
    
    # 2. LLM 提取
    settlement = await llm_extract_settlement(
        content=version.content,
        current_states=current_states,
        current_settings=current_settings,
        genre_rules=GenreProfileLoader.load(project.genre_id),
    )
    
    # 3. 代码层验证
    errors = validate_settlement(settlement, current_states, current_settings)
    if errors:
        settlement.validation_status = "needs_human_review"
        settlement.validation_errors = errors
        return settlement
    
    # 4. 更新 SQLite（永远 INSERT，不 UPDATE）⭐
    await apply_settlement(db, settlement, project_id, chapter_number, version_id)
    settlement.validation_status = "valid"
    return settlement

async def apply_settlement(
    db: Repository,
    settlement: StateSettlement,
    project_id: str,
    chapter_number: int,
    version_id: str,
):
    """将结算结果应用到数据库——INSERT 新快照"""
    
    for update in settlement.character_updates:
        # INSERT 新状态快照，不是 UPDATE ⭐
        await db.character_states.insert_snapshot(
            character_id=update.character_id,
            project_id=project_id,
            chapter_number=chapter_number,
            field=update.field,
            new_value=update.new_value,
            source_version_id=version_id,
        )
    
    for setting in settlement.new_settings:
        # 检查 setting_key 是否已存在
        existing = await db.setting_snapshots.get_by_key(project_id, setting.setting_key)
        if existing:
            # 更新描述（设定演变）
            await db.setting_snapshots.update_description(existing.id, setting.description)
        else:
            # 新建设定
            await db.setting_snapshots.create(
                project_id=project_id,
                chapter_number=chapter_number,
                setting_key=setting.setting_key,
                setting_name=setting.setting_name,
                description=setting.description,
                source_quote=setting.source_quote,
            )
    
    for fs in settlement.foreshadowing_updates:
        await db.foreshadowings.update_status(
            fs.foreshadowing_id,
            fs.operation,
            source_version_id=version_id,  # ⭐
        )
    
    for num in settlement.numerical_updates:
        await db.numerical_ledgers.create(num)
```

### 12.2 验证逻辑（更新）⭐

```python
def validate_settlement(
    settlement: StateSettlement,
    current_states: list[CharacterState],
    current_settings: list[SettingSnapshot],
) -> list[str]:
    """验证结算结果，返回错误列表"""
    errors = []
    
    # 验证 character_update.old_value
    for update in settlement.character_updates:
        state = find_state(current_states, update.character_id)
        if state and getattr(state, update.field) != update.old_value:
            errors.append(
                f"角色 {update.character_id} 的 {update.field} "
                f"当前值为 {getattr(state, update.field)}，"
                f"但结算声称 old_value={update.old_value}"
            )
    
    # 验证 numerical_update.closing_value
    for num in settlement.numerical_updates:
        expected = num.opening_value + sum(i.amount for i in num.increments) - sum(d.amount for d in num.decrements)
        if abs(num.closing_value - expected) > 0.001:
            errors.append(
                f"数值 {num.attribute_name} 的 closing_value={num.closing_value} "
                f"不等于公式值 {expected}"
            )
    
    # 验证 new_setting.setting_key 唯一性 ⭐
    seen_keys = set()
    for setting in settlement.new_settings:
        if setting.setting_key in seen_keys:
            errors.append(f"设定 key {setting.setting_key} 重复")
        seen_keys.add(setting.setting_key)
        # 检查是否与已有设定冲突
        existing = find_setting_by_key(current_settings, setting.setting_key)
        if existing and existing.description != setting.description:
            # 允许描述更新（设定演变），不报错
            pass
    
    # source_quote 存在性（在正文中搜索）
    for setting in settlement.new_settings:
        if setting.source_quote and setting.source_quote not in accepted_content:
            errors.append(f"设定 {setting.setting_name} 的 source_quote 不在正文中")
    
    return errors
```

---

## 13. 错误处理策略

### 错误分类

| 错误类型 | 处理方式 | 是否重试 |
|----------|----------|----------|
| **LLM API 错误** | 记录日志，重试 3 次（指数退避） | 是 |
| **LLM 输出解析失败** | 记录原始输出，返回空结果 | 否 |
| **Pydantic 验证失败** | 记录详细错误，不上报人工 | 否 |
| **StateSettlement 验证失败** | 标记 needs_human_review | 否 |
| **数据库连接失败** | 重试 3 次，然后报错退出 | 是 |
| **Token 预算超限** | 按裁剪策略减少上下文 | 否 |
| **内存不足** | 记录，清理缓存，重试 1 次 | 是 |
| **RuleAuditor 超时** | 跳过代码检测，只保留 LLMAuditor | 否 ⭐ |

### 自定义异常

```python
class SongyanError(Exception):
    """基础异常"""
    pass

class SettlementValidationError(SongyanError):
    """状态结算验证失败"""
    pass

class GenreNotFoundError(SongyanError):
    """题材配置不存在"""
    pass

class ModeNotFoundError(SongyanError):          # ⭐ 新增
    """创作模式配置不存在"""
    pass

class TokenBudgetExceededError(SongyanError):
    """Token 预算超限"""
    pass

class ContextAssemblyError(SongyanError):
    """上下文组装失败"""
    pass

class RuleAuditTimeoutError(SongyanError):      # ⭐ 新增
    """RuleAuditor 超时"""
    pass

class LiteraryAuditNonBlockingError(SongyanError):  # ⭐ 新增
    """LiteraryAuditor 诊断失败（不阻塞）"""
    pass
```

---

## 14. 性能监控

### 关键指标（更新）⭐

| 指标 | 目标 | 监控方式 |
|------|------|----------|
| GoalPlanner 调用时间 | < 30s | structlog 记录 |
| CreativeDirector 调用时间 | < 30s | structlog 记录 |
| 上下文组装时间 | < 5s | structlog 记录 |
| 单章生成时间 | < 60s | structlog 记录 |
| **RuleAuditor 检测时间** | **< 200ms** | structlog 记录 ⭐ |
| **LLMAuditor 审查时间** | **< 45s** | structlog 记录 ⭐ |
| **LiteraryAuditor 诊断时间** | **< 15s** | structlog 记录 ⭐ |
| 合并报告时间 | < 10ms | structlog 记录 ⭐ |
| 修订时间 | < 30s | structlog 记录 |
| 状态结算时间 | < 15s | structlog 记录 |
| LLM 调用次数 | 每章 < 12 次 | 计数器 ⭐ |
| Token 使用量 | < 32K/次 | tiktoken 计数 |
| 数据库查询次数 | 每节点 < 10 次 | SQL 日志 |

### 日志格式（更新）⭐

```python
import structlog

logger = structlog.get_logger()

# 双层审查日志
logger.info(
    "dual_audit_completed",
    version_id=version_id,
    rule_duration_ms=150,           # ⭐
    llm_duration_ms=28000,          # ⭐
    total_issues=5,
    critical=0,
    major=2,
    minor=3,
    ai_tell_count=1,
    fatigue_word_count=0,
    overall_score=7.2,
)

# 文学审计日志
logger.info(
    "literary_audit_completed",
    version_id=version_id,
    observations=3,
    valuable_fissures=1,            # ⭐
    character_autonomy_score=6.5,   # ⭐
    conceptual_idling_score=7.0,    # ⭐
    duration_ms=8000,
    blocking=False,                 # ⭐
)

# 结算日志
logger.info(
    "settlement_completed",
    version_id=version_id,
    status="valid",
    character_updates=2,
    new_settings=1,
    setting_keys=["xuanhuan.spirit_stone"],  # ⭐
    numerical_updates=1,
    validation_errors=[],
    duration_ms=8000,
)
```

---

## 15. 多 LLM 支持说明

### 15.1 litellm 统一接口

```python
from langchain_community.chat_models import ChatLiteLLM

def get_llm(temperature: float = 0.7):
    return ChatLiteLLM(
        model=os.getenv("LLM_MODEL", "deepseek-chat"),
        api_key=os.getenv("LLM_API_KEY"),
        base_url=os.getenv("LLM_BASE_URL"),
        temperature=temperature,
        max_tokens=4096,
    )

# 写作用高温度（创造性）
writer_llm = get_llm(temperature=0.7)

# 审查用低温度（精确性）
llm_auditor_llm = get_llm(temperature=0.3)

# 文学诊断用低温度（精确性）
literary_auditor_llm = get_llm(temperature=0.3)

# 目标规划用高温度（创造性）
goal_planner_llm = get_llm(temperature=0.7)

# 创作导演用高温度（创造性）
creative_director_llm = get_llm(temperature=0.7)

# 结算用低温度（精确提取）
settlement_llm = get_llm(temperature=0.3)

# 修订用低温度（精确修改）
revision_llm = get_llm(temperature=0.3)
```

### 15.2 温度策略（更新）⭐

| Agent | 温度 | 理由 |
|-------|------|------|
| Writer | 0.7 | 需要创造性 |
| GoalPlanner | 0.7 | 需要创造性规划 |
| CreativeDirector | 0.7 | 需要创造性意图 ⭐ |
| LLMAuditor | 0.3 | 需要精确和一致 ⭐ |
| LiteraryAuditor | 0.3 | 需要精确诊断 ⭐ |
| RevisionHandler | 0.3 | 需要精确修改 |
| SettlementExtractor | 0.3 | 需要精确提取 |

---

## 16. 技术债务与升级路径

### V1.0 → V1.5

| 当前（V1.0） | 问题 | 升级（V1.5） |
|-------------|------|-------------|
| SQLite 单库 | 查询性能 | 增加索引优化 |
| 最近章节摘要 | 上下文有限 | 引入 Mem0 管理长期记忆 |
| 单章闭环 | 无法验证连续 | 连续 5-10 章生成 |
| 硬编码预算 | 不够灵活 | 根据题材动态调整预算 |
| 正则检测 AI 腔 | 有漏网之鱼 | LLM 二次确认 |
| CreativeDirector 轻量 | 意图不够深 | 引入 PolyphonyPlanner |
| LiteraryAuditor 轻量 | 诊断维度有限 | 增加 CharacterAutonomyAuditor |

### V1.5 → V2.0

| 当前（V1.5） | 问题 | 升级（V2.0） |
|-------------|------|-------------|
| 摘要检索 | 信息丢失 | Qdrant 向量检索 |
| 无 Web UI | 不友好 | React Studio |
| 单模型 | 无法分工 | 多模型路由（强模型写，快模型审） |
| 无风格控制 | 风格单一 | 风格迁移（RAG/微调） |

---

## 17. 调试指南

### 常见问题（更新）⭐

#### Q: RuleAuditor 检测太慢（> 200ms）

**排查步骤**：
1. 检查 ai_tells.py 的正则模式数量（不超过 15 个）
2. 检查 fatigue_words.py 的疲劳词数量（不超过 50 个）
3. 检查 hook_checker.py 是否使用了简单规则而非 LLM
4. 使用 `cProfile` 分析哪个检测耗时最长
5. 考虑将 numerical_validator 移到异步线程

#### Q: LLMAuditor 输出无法解析

**排查步骤**：
1. 检查 LLMAuditor prompt 中的 JSON 格式示例是否清晰
2. 检查 temperature 是否为 0.3（不是 0.7）
3. 检查 max_tokens 是否足够（至少 4096）
4. 手动运行 LLMAuditor prompt，查看原始输出
5. 增加 Pydantic 解析的错误日志

#### Q: LiteraryAuditor 标记了太多 valuable_fissure

**排查步骤**：
1. 检查 LiteraryAuditor prompt 中对 valuable_fissure 的定义是否清晰
2. 调整 LiteraryAuditor 的 temperature（从 0.3 调到 0.2）
3. 检查 CreativeBrief 的 forbidden_patterns 是否太模糊
4. 在 webnovel 模式下降低 valuable_fissure 的敏感度

#### Q: CreativeBrief 没有被正确注入 Writer Prompt

**排查步骤**：
1. 检查 context_manager.py 是否正确加载 CreativeBrief
2. 检查 ContextPackage 是否包含 creative_brief 字段
3. 检查 writer.py 的 build_writer_prompt 是否调用了 build_creative_brief_section
4. 检查 generation_metadata 是否保存了 creative_brief_id
5. 查看 creative_briefs 表中是否有记录

#### Q: SettlementExtractor 验证失败（setting_key 冲突）⭐

**排查步骤**：
1. 检查 setting_snapshots 表中是否已有相同 setting_key
2. 检查 settlement.new_settings 中是否有重复 setting_key
3. 确认 setting_key 的命名规则是否一致（建议用 "genre.category.name" 格式）
4. 如果是设定演变（描述更新而非新建），检查是否正确处理了

#### Q: 状态结算后 character_states 被 UPDATE 而不是 INSERT ⭐

**排查步骤**：
1. 检查 repository.py 的 update_state 方法是否改为 insert_snapshot
2. 检查 schema.sql 中 character_states 表的注释是否说明为快照表
3. 检查 settlement_extractor.py 的 apply_settlement 是否调用 INSERT
4. 查询数据库确认：每个角色每章应该有多个状态记录

#### Q: 上下文 Token 超限

**排查步骤**：
1. 检查 ContextBudget.available 是否 > 0
2. 检查各分区预算使用情况（特别是 creative_brief_max）
3. 检查是否加载了过多角色（出场角色检测是否正确）
4. 检查 CreativeBrief 是否过长（应 < 1500 tokens）
5. 手动调整 total_budget 到 48K 或 64K

### 调试命令

```bash
# 查看项目信息（含创作模式）
songyan show-project --project <id>

# 查看章节版本链
songyan list-versions --project <id> --chapter <n>

# 查看审查报告（含双层审查结果）
songyan review --version <version_id>

# 查看文学性诊断
songyan literary-audit --version <version_id> ⭐

# 查看 CreativeBrief
songyan show-brief --version <version_id> ⭐

# 查看角色状态快照链
songyan show-character-states --project <id> --character <char_id> ⭐

# 手动运行 RuleAuditor（调试）
songyan debug rule-audit --version <version_id> ⭐

# 性能分析
python -m cProfile -o profile.stats -m songyan.cli.main write --project test --chapter 1
```
