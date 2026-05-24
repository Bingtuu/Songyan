松烟入墨，字句成锋。

# Songyan（松烟）— 多 Agent 中文小说写作系统

<p align="center">
  <strong>从一句灵感，到一章精彩</strong><br>
  <strong>先验证一章，再验证十丈，最后成书</strong>
</p>

<p align="center">
  <a href="#-快速开始">快速开始</a> •
  <a href="#-核心特性">核心特性</a> •
  <a href="#-架构设计">架构</a> •
  <a href="#-评测标准">评测</a> •
  <a href="#-演进路线">路线图</a>
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
- [2. 核心特性](#2-核心特性)
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

Songyan（松烟）是一个面向**长篇中文小说创作**的 AI 生产系统，基于 LangGraph 多 Agent 协作架构。

松烟取意古法制墨——松木燃烧，烟灰凝墨。以 AI 为烟，以规则为胶，凝练成可用之墨。

### 核心判断

我们不是在做一个"AI 聊天写小说"的工具，而是在验证一个假设：

> **"每生成一章，系统都知道它为什么这么写、哪里可能错、改了什么、状态发生了什么变化、下一章应该继承什么。"**

为此，我们采用**渐进落地**的策略：先验证一章，再验证十丈，最后成书。

### 目标用户

| 用户类型 | V1.0 | V1.5 | V2.0 |
|----------|------|------|------|
| **开发者/研究者** | 验证核心假设 | 扩展连续性 | 产品化 |
| **网文作者** | | 提速生产 | 批量生产 |
| **小说新手** | | | 完整产品 |
| **严肃文学创作者** | | 轻量辅助 | 深度协作 |

### 当前阶段

**V1.0：单章闭环验证（进行中）**

- GoalPlanner + CreativeDirector + ContextManager + Writer
- **双层审查**：RuleAuditor（代码）+ LLMAuditor（语义）
- **LiteraryAuditor** 文学性诊断
- **CreativeModeProfile** 创作模式系统（网文/严肃文学/混合）
- Genre Profile 题材规则系统
- 15+ 维度结构化审查（含 AI 腔/疲劳词/首屏钩子）
- 写作工艺层 Prompt 架构
- 状态结算机制
- CLI 界面
- SQLite 单库

---

## 2. 核心特性

### 六层质量防线

Songyan 不是让 Writer 一个人写好，而是六层防线的共同结果：

```
第一层：CreativeModeProfile（创作模式选择）    — 网文还是严肃文学？
第二层：CreativeDirector（创作意图与张力地图） — 本章要制造什么张力
第三层：Genre Profile（题材规则约束）           — 玄幻有玄幻的规矩
第四层：写作工艺层 Prompt（文学质量约束）       — 怎么写比写什么更重要
第五层：Writer Agent（创作执行）                — AI 动笔
第六层：Reviewer 双层审查                       — AI 编辑把关
  - RuleAuditor（代码检测）：AI 腔/疲劳词/段落/首屏/字数  — 快、稳、便宜
  - LLMAuditor（语义审查）：角色/节奏/对话/设定一致性    — 准、深、语义理解
第七层：LiteraryAuditor（文学性诊断）           — 防止"流畅但平庸"
第八层：人工确认（最终门控）                    — 你说了算
```

### CreativeModeProfile 创作模式系统 ⭐

同一个系统，不同模式，服务不同创作场景：

| 模式 | 目标 | 特色 Agent | 审查侧重 |
|------|------|-----------|----------|
| **网文** | 节奏、爽点、连载 | CreativeDirector + 钩子审查 | 节奏/爽点/数值一致性 |
| **严肃文学** | 人物自治、裂隙保留 | CreativeDirector + PolyphonyPlanner | 人物自治/概念落地/裂隙保护 |
| **混合** | 两者兼顾 | 全部启用 | 平衡权重 |

新增创作模式只需一个 JSON 配置文件，无需修改 Agent 代码。

### Genre Profile 题材规则系统

不同题材有不同的规矩。玄幻不能战力吃书，都市不能节奏拖沓，科幻不能设定矛盾。

```json
{
  "id": "xuanhuan",
  "fatigue_words": ["冷笑", "蝼蚁", "倒吸凉气", "瞳孔骤缩"],
  "pacing_rule": "三章内必有明确反馈",
  "writer_rules": ["设定不可吃书", "金手指四维约束"],
  "satisfaction_types": ["打脸", "升级突破", "收益兑现"]
}
```

Writer 按规则写，RuleAuditor 按规则检测。

### 双层审查体系 ⭐

Reviewer 拆分为 **RuleAuditor（代码检测）** 和 **LLMAuditor（语义审查）**：

```
章节正文
    |
    ├──▶ RuleAuditor（代码，<200ms，稳定，便宜）
    |       • AI 腔检测（正则）
    |       • 疲劳词检测（字符串匹配）
    |       • 段落节奏分析（统计）
    |       • 首屏/章末钩子检查（规则）
    |       • 字数统计
    |       • 数值公式验证
    |
    └──▶ LLMAuditor（LLM，语义理解）
            • 设定一致性
            • 角色行为一致性
            • 叙事节奏
            • 对话区分度
            • 信息倾倒
            • ShowDon'tTell
            |
            ▼
    MergedReviewReport（合并输出）
```

### LiteraryAuditor 文学性诊断 ⭐

Reviewer 之后，人工之前——专门诊断"流畅但平庸"的问题：

- **人物工具化**：人物只是推动剧情的工具？
- **概念空转**：抽象概念多、身体感少？
- **过度平滑**：所有矛盾都被过早解决？
- **有价值裂隙**：标记"可能 valuable 的异常"，建议人工保留

**不阻塞入库，只提供诊断。**

### 写作工艺层

Prompt 分四层：约束层（动态）+ 工艺层（固定）+ 题材层（Genre Profile）+ **创作意图层（CreativeBrief）**⭐

工艺层包含经过验证的写作指导：
- **黄金开篇纪律**：前 300 字必须有冲突/意外/危险/情感冲击
- **Show, Don't Tell**：不写"他很愤怒"，写"他攥紧了拳头，指节泛白"
- **对话工艺**：每句对话推动剧情，潜台词丰富
- **感官沉浸**：激活听觉/触觉/嗅觉，不只视觉
- **章末钩子**：最后一段必须留下有效悬念

### CreativeDirector 创作导演 ⭐

Writer 动笔之前，CreativeDirector 先制定"创作意图与张力地图"：

- 本章要制造什么张力
- 人物之间的价值冲突是什么
- 哪些地方允许保留裂隙
- 哪些套路必须避开
- 本章对读者的"承诺"是什么

**输出结构化 CreativeBrief，入 Writer Prompt——不写正文。**

### 状态结算机制

写完一章不只是生成摘要，而是完成一次**完整的状态结算**：

- 角色境界突破了？→ INSERT 新 character_states 快照
- 引入了新设定？→ 加入 setting_snapshots（带 setting_key 追踪演变）
- 埋下了新伏笔？→ 加入 foreshadowings（带 source_version_id）
- 战力数值变了？→ 记账 numerical_ledgers
- 代码层验证：old_value 匹配、closing_value 公式正确

确保下一章的上下文是准确的。

### Issue-Driven 修订

发现问题不是整章重写，而是**精准 patch**：

1. RuleAuditor + LLMAuditor 定位到具体句子（evidence_quote）
2. RevisionHandler 只替换有问题的部分
3. **保护 LiteraryAuditor 标记的有价值裂隙**
4. 保留其他内容完全不变
5. 最多 2 轮自动修订
6. 修订后再次双层审查，确保没引入新问题

---

## 3. 快速开始

### 环境要求

- Python 3.11+
- LLM API Key（DeepSeek / OpenAI 兼容接口）

### 安装

```bash
# 克隆仓库
git clone https://github.com/yourusername/songyan.git
cd songyan

# 安装（纯 Python，无 Docker 依赖）
pip install -e ".[dev]"

# 配置环境变量
cp .env.example .env
# 编辑 .env，填入 LLM_API_KEY 和 LLM_BASE_URL

# 运行
songyan --help
```

### 创建第一篇小说

```bash
# 交互式创建（8 步向导）
songyan create-project

# 向导会问你：
# 1. 创作模式？（网文/严肃文学/混合）⭐
# 2. 题材？（玄幻/都市/科幻）
# 3. 核心灵感？（一句话描述）
# 4. 主角设定？（AI 可以建议）
# 5. 读者预期？（爽/燃/甜/虐...）
# 6. 禁忌事项？（可选）
# 7. 目标字数？（可选）
# 8. 书名？（AI 可以建议）

# 开始写作第 1 章
songyan write --project mynovel --chapter 1

# 系统会：
# 1. GoalPlanner 制定章节目标
# 2. CreativeDirector 生成创作意图+张力地图 ⭐
# 3. 加载 Genre Profile + CreativeModeProfile（题材规则）
# 4. 组装上下文包（约束层 + 工艺层 + 题材层 + 创作意图层）
# 5. 生成章节初稿
# 6. RuleAuditor 代码层规则检测（AI腔/疲劳词/段落）⭐
# 7. LLMAuditor 语义审查（角色/节奏/对话/设定一致性）⭐
# 8. 合并为 MergedReviewReport
# 9. LiteraryAuditor 文学性诊断（不阻塞）⭐
# 10. 如有问题，自动修订（最多 2 轮，局部 patch）
# 11. 状态结算（角色/设定/伏笔/数值更新）
# 12. 等待你确认或修改
```

### 查看结果

```bash
# 查看章节
songyan show --project mynovel --chapter 1

# 查看审查报告（含双层审查结果）
songyan review --project mynovel --chapter 1

# 查看文学性诊断
songyan literary-audit --project mynovel --chapter 1

# 查看版本历史
songyan list-versions --project mynovel --chapter 1

# 导出为 txt
songyan export --project mynovel --format txt
```

---

## 4. 架构设计

### V1.0 架构

```
用户 → CLI → LangGraph 工作流
                 |
     ┌───────────┼───────────┬───────────────┐
     ▼           ▼           ▼               ▼
  GoalPlanner  Creative   Context        Writer
  (目标制定)   Director   Manager
     |       (创作意图)    (上下文)
     |          |            |
     |          ▼            ▼
     └────▶ CreativeBrief + ContextPackage → Writer
                                              |
                                              ▼
                                    ┌──────────────────┐
                                    │   RuleAuditor    │ 代码检测
                                    │   LLMAuditor     │ 语义审查
                                    └────────┬────────┘
                                             │
                                    MergedReviewReport
                                             │
                                             ▼
                                    LiteraryAuditor ⭐
                                    (文学性诊断，不阻塞)
                                             |
                              ┌──────────────┴──────────────┐
                              ▼                              ▼
                         Revision                     HumanConfirm
                         Handler                       accept → SettlementExtractor
                         (patch)                       edit / reject / back
                              |
                              ▼
                    ┌──────────────────┐
                    │  Settlement      │ ⭐
                    │  Extractor       │
                    │  (状态结算)      │
                    └────────┬─────────┘
                             ▼
                          SQLite
```

### 数据事实源

**铁律：SQLite 是唯一的长期事实源。**

| 存储 | 用途 | 持久性 |
|------|------|--------|
| **SQLite** | 所有业务数据（项目、角色、章节版本、审查报告、文学审计、数值账本） | 长期 |
| **Checkpoint** | 仅保存 LangGraph 执行现场 | 仅用于崩溃恢复 |
| **内存** | LLM 上下文窗口、临时计算 | 重启丢失 |

### 工作流（修正后的顺序）⭐

```
goal_planner ──▶ creative_director ──▶ context_manager ──▶ writer
                                                              |
                    ┌─────────────────────────────────────────┘
                    |
                    ▼
          ┌───────────────────┐
          │   RuleAuditor     │ 代码检测（AI腔/疲劳词/段落/字数）
          │   LLMAuditor      │ 语义审查（角色/节奏/对话/设定）
          └─────────┬─────────┘
                    │
          MergedReviewReport
                    |
                    ▼
          LiteraryAuditor ⭐
          （文学性诊断，不阻塞）
                    |
         ┌──────────┴──────────┐
         ▼                     ▼
   Revision              HumanConfirm
   （patch 2轮）          accept → settlement → SQLite → done
                         reject → goal_planner
                         back → writer
```

---

## 5. 核心设计

### 5.1 Agent 总览

| Agent | 职责 | 不做什么 |
|-------|------|----------|
| **GoalPlanner** | 项目设定收集、章节目标制定 | 不写正文、不做结算 |
| **CreativeDirector** | 写前生成创作意图+张力地图+禁忌清单 | 不直接写正文 |
| **ContextManager** | 加载 Genre Profile、按 Token 预算组装上下文包 | 不做生成、不做审查 |
| **Writer** | 按场景生成正文（受 Genre + 工艺层 + CreativeBrief 约束） | 不做审查 |
| **RuleAuditor** | 代码层规则检测（AI 腔/疲劳词/段落/首屏/字数） | 不做语义判断 |
| **LLMAuditor** | LLM 语义审查（角色/节奏/对话/设定一致性） | 不做代码检测 |
| **LiteraryAuditor** | 文学性诊断（人物工具化/概念空转/裂隙） | 不阻塞流程、不修改正文 |
| **RevisionHandler** | 按 issue 局部 patch 修订 | 不整章重写 |
| **SettlementExtractor** | 状态结算提取+代码验证+更新 DB | 不写摘要 |

### 5.2 CreativeModeProfile ⭐

创作模式配置系统——"管线 + 插件"架构：

```python
# 网文模式
mode = CreativeModeProfile(
    id="webnovel",
    enabled_agents={
        "pre_write": ["goal_planner", "creative_director"],
        "write": ["writer"],
        "post_write": ["rule_auditor", "narrative_reviewer", "literary_auditor"],
        "revision": ["revision_handler"],
        "settlement": ["settlement_extractor"]
    },
    audit_weights={"narrative_pacing": 1.2, "character_autonomy": 0.6},
    revision_policy="standard"
)

# 严肃文学模式
mode = CreativeModeProfile(
    id="literary",
    enabled_agents={
        "pre_write": ["goal_planner", "creative_director", "polyphony_planner"],
        "write": ["writer"],
        "post_write": ["literary_auditor", "character_autonomy_auditor"],
        "revision": ["selective_revision_handler"],
        "settlement": ["settlement_extractor"]
    },
    audit_weights={"character_autonomy": 1.5, "cliche_risk": 1.5},
    revision_policy="selective"  # 保护裂隙
)
```

### 5.3 写作上下文包（Context Package）

小说专用的分区上下文注入结构：

| 分区 | 内容 | 优先级 |
|------|------|--------|
| **硬约束** | 角色当前状态、已揭示设定、禁忌、本章义务 | 必须遵守 |
| **角色状态** | 出场角色的完整状态快照 | 高 |
| **最近剧情** | 前 N 章摘要 + 上一章结尾 500 字 | 高 |
| **伏笔线索** | 已埋下未回收、本章应回收 | 中 |
| **题材规则** | Genre Profile 的 writer_rules | 高 |
| **工艺层** | 黄金开篇、段落节奏、对话工艺 | 高 |
| **创作意图层** | CreativeBrief 的张力地图+禁忌清单 | 高 ⭐ |
| **软参考** | 世界观设定、风格样本 | 低（超预算先裁剪） |

### 5.4 双层审查体系

```python
# RuleAuditor —— 代码检测，快速稳定
rule_result = RuleAuditor.check(
    ai_tells=True,           # "不禁意识到"等 AI 高频句式
    fatigue_words=True,      # "冷笑""蝼蚁"等疲劳词
    paragraph_rhythm=True,   # 段落长度分布
    opening_hook=True,       # 前 300 字吸引力
    ending_hook=True,        # 后 200 字悬念
    word_count=True,         # 字数统计
    numerical_formulas=True  # 玄幻数值公式验证
)

# LLMAuditor —— LLM 语义审查
llm_result = LLMAuditor.review(
    world_consistency=True,      # 设定一致性
    character_behavior=True,     # 角色行为
    narrative_pacing=True,       # 叙事节奏
    dialogue_distinctness=True,  # 对话区分度
    info_dump=True,              # 信息倾倒
    show_dont_tell=True,         # Show Don't Tell
    conceptual_idling=True       # 概念空转 ⭐
)

# 合并
merged = MergedReviewReport.merge(rule_result, llm_result)
```

### 5.5 LiteraryAuditor（文学性诊断）

Reviewer 之后的额外诊断层——**不阻塞入库**：

```python
literary_result = LiteraryAuditor.diagnose(
    character_tooling=True,      # 人物工具化
    conceptual_idling=True,      # 概念空转
    excessive_smoothing=True,    # 过度平滑
    valuable_fissure=True,       # 有价值裂隙（标记保护）
    cliche_risk=True,            # 套路化风险
    polyphony_weakness=True      # 复调不足
)
```

### 5.6 状态结算

每章 accept 后自动执行：

1. SettlementExtractor 从 accepted 正文中提取变更
2. **代码层验证**：
   - character_update.old_value == DB 当前值
   - new_setting.source_quote 在正文中存在
   - new_setting.setting_key 唯一
   - numerical closing_value == opening + 增量 - 消耗
3. 验证通过 → **INSERT 新快照**（永远 INSERT，不 UPDATE）
4. 验证失败 → 标记 `needs_human_review`
5. 结算完成后 → 生成人类可读摘要

### 5.7 Issue-Driven 修订

不是整章重写，而是**针对 issue 做局部 patch**：

1. RuleAuditor + LLMAuditor 定位到具体句子（evidence_quote）
2. RevisionHandler 只替换有问题的部分
3. **保护 LiteraryAuditor 标记的 valuable_fissure** ⭐
4. 保留其他内容完全不变
5. 最多 **2 轮**自动修订
6. 第二轮引入新问题 → 立即停止并上报人工

### 5.8 版本管理

每次生成和修订都创建新版本，不覆盖旧版本：

```
draft_v1 (初稿)
  └── revision_v1 (第 1 轮修订)
       └── revision_v2 (第 2 轮修订)
            └── accepted (人工确认)
                 └── edited (人工编辑后)
```

### 5.9 新手创建向导

8 步 CLI 引导，让完全不懂写作的新手也能开始：

1. 创作模式选择 → 2. 题材选择 → 3. 核心灵感 → 4. 主角设定 → 5. 读者预期 → 6. 禁忌事项 → 7. 目标字数 → 8. 书名确认

每步 AI 实时生成建议，用户可以随时跳过或修改。

---

## 6. 评测标准

### V1.0 完成标准（修正为客观指标）⭐

| 指标 | 目标 | 测量方式 |
|------|------|----------|
| 设定硬错误数 | 0 | critical world_consistency = 0 |
| 人工大改比例 | < 30% | 需人工大幅修改的章节比例 |
| 审查漏检率 | < 20% | 人工发现但 AI 没发现的问题比例 |
| 修订后新问题数 | 0 | 第二轮审查新问题数 = 0 |
| AI 腔规则命中数 | < 2 处/章 | RuleAuditor 检测数 |
| 疲劳词命中数 | < 3 处/章 | RuleAuditor 检测数 |
| 首屏钩子达标率 | 100% | 前 300 字有吸引力事件 |
| 章末钩子达标率 | 100% | 最后 200 字有有效悬念 |
| 状态结算字段准确率 | > 90% | old_value 与 DB 一致率 |
| 概念空转段落数 | 0 | LiteraryAuditor 检测数 |
| 人物语言区分度 | > 70% | 人工评分>7 的章节比例 |
| AI 与人工金标一致率 | > 70% | critical/major 重叠率 |

**移除指标**：overall_score > 6.5/10（太主观，容易自欺）。

### 评测集

- 3 个题材：玄幻（修仙）、都市（异能）、科幻（星际）
- 2 种创作模式：网文、严肃文学
- 每个组合 3 章
- 人工编写第 1 章作为种子，AI 生成第 2-4 章
- 人工金标对比（RuleAuditor + LLMAuditor vs 人工审查重叠率 > 70%）

---

## 7. 与其他项目对比

| 特性 | Songyan (V1.0) | InkOS | AI-Novel-Writing-Assistant |
|------|---------------|-------|---------------------------|
| **当前阶段** | 单章闭环验证 | 写-审-改循环（成熟） | 整本生产（成熟） |
| **创作模式** | ✅ CreativeModeProfile ⭐ | ❌ 无 | ❌ 无 |
| **创作导演** | ✅ CreativeDirector ⭐ | ❌ 无 | ⚠️ 导演模式 |
| **题材规则** | ✅ Genre Profile JSON | ✅ YAML Profile | ❌ 无 |
| **双层审查** | ✅ RuleAuditor + LLMAuditor ⭐ | ✅ 33 维（单一 LLM） | ⚠️ 综合报告 |
| **文学性诊断** | ✅ LiteraryAuditor ⭐ | ❌ 无 | ❌ 无 |
| **写作工艺** | ✅ 四层 Prompt 架构 ⭐ | ✅ 模块化 Prompt | ⚠️ 基础 |
| **状态结算** | ✅ 结构化结算（快照表）⭐ | ✅ Observer+Reflector | ❌ 摘要 |
| **上下文预算** | ✅ Token 预算管理 | ✅ 硬编码预算 | ❌ 无 |
| **Issue-Driven 修订** | ✅ 局部 patch（2轮） | ✅ 整章重写 | ⚠️ 重写 |
| **有价值裂隙保护** | ✅ LiteraryAuditor 标记 ⭐ | ❌ 无 | ❌ 无 |
| **版本管理** | ✅ 版本链（不覆盖） | ✅ JSON truth files | ⚠️ 基础 |
| **Agent 数量** | 9 个（4 写前 + 1 写 + 3 审查 + 1 结算） | 10 级流水线 | 10+ |
| **界面** | CLI | CLI + Studio | Web + 桌面 |
| **存储** | SQLite | SQLite + JSON | Postgres + Qdrant |

**Songyan 的差异化设计**：
- **CreativeModeProfile**：同一套系统，网文/严肃文学/混合三种模式
- **CreativeDirector**：写前制定创作意图+张力地图，不是让 AI "随便写"
- **双层审查**：RuleAuditor（代码快）+ LLMAuditor（语义准），又快又准
- **LiteraryAuditor**：防止"流畅但平庸"，标记有价值裂隙保护创意
- **有价值裂隙保护**：不是所有"异常"都是 bug，有些裂隙可能是文学性的火花
- **四层 Prompt**：约束层 + 工艺层 + 题材层 + **创作意图层**
- **状态结算快照表**：character_states 永远 INSERT 不 UPDATE，完整可追溯

---

## 8. 开发文档

### 完整设计文档

- [完整系统架构设计](docs/01-architecture-design.md) — V1.0 架构、数据模型、数据库设计
- [Prompt 工程文档](docs/02-vibe-coding-prompts.md) — 所有 Agent Prompt、写作工艺层
- [Vibe Coding 工程手册](docs/04-vibe-coding-engineering.md) — 开发规范、Task 拆解
- [技术参考手册](docs/05-tech-reference.md) — 技术栈说明、Agent 调用关系

### 项目结构

```
songyan/
├── pyproject.toml
├── .env.example
├── README.md
├── CLAUDE.md                           # 不可违背规则清单
├── creative_modes/                     # ⭐ 创作模式配置
│   ├── webnovel.json
│   ├── literary.json
│   └── hybrid.json
├── genres/                             # 题材配置文件
│   ├── xuanhuan.json
│   ├── urban.json
│   └── scifi.json
├── docs/
│   ├── 01-architecture-design.md
│   ├── 02-vibe-coding-prompts.md
│   ├── 04-vibe-coding-engineering.md
│   └── 05-tech-reference.md
├── prompts/
│   ├── writer.md
│   ├── craft_card.md                   # 写作工艺层
│   ├── creative_director.md            # ⭐ 创作导演
│   ├── goal_planner.md                 # ⭐ 目标规划
│   ├── rule_auditor.md                 # ⭐ 规则检测
│   ├── llm_auditor.md                  # ⭐ 语义审查
│   ├── literary_auditor.md             # ⭐ 文学审计
│   └── settlement_extractor.md         # ⭐ 状态结算
├── src/songyan/
│   ├── __init__.py
│   ├── config.py
│   ├── cli/
│   │   └── main.py
│   ├── db/
│   │   ├── schema.sql
│   │   ├── repository.py
│   │   └── connection.py
│   ├── models/
│   │   ├── __init__.py
│   │   ├── project.py
│   │   ├── character.py
│   │   ├── chapter.py
│   │   ├── context.py
│   │   ├── review.py                   # ⭐ RuleAuditResult, LLMAuditResult
│   │   ├── revision.py
│   │   ├── settlement.py
│   │   ├── genre.py
│   │   ├── creative_mode.py            # ⭐ CreativeModeProfile, CreativeBrief
│   │   └── literary.py                 # ⭐ LiteraryObservation
│   ├── agents/
│   │   ├── __init__.py
│   │   ├── goal_planner.py             # ⭐ 拆分自 planner
│   │   ├── creative_director.py        # ⭐ 新增
│   │   ├── context_manager.py
│   │   ├── writer.py
│   │   ├── rule_auditor.py             # ⭐ 新增
│   │   ├── llm_auditor.py              # ⭐ 新增
│   │   ├── literary_auditor.py         # ⭐ 新增
│   │   ├── revision_handler.py
│   │   └── settlement_extractor.py     # ⭐ 拆分自 planner
│   ├── workflows/
│   │   └── phase1_graph.py             # ⭐ 修正流程顺序
│   └── utils/
│       ├── ai_tells.py                 # AI 腔检测
│       ├── fatigue_words.py            # 疲劳词检测
│       ├── hook_checker.py             # 钩子检测
│       ├── paragraph_rhythm.py         # 段落节奏
│       └── token_counter.py
├── tests/
│   ├── __init__.py
│   ├── test_models.py
│   ├── test_repository.py
│   ├── test_context_package.py
│   ├── test_writer.py
│   ├── test_goal_planner.py            # ⭐
│   ├── test_creative_director.py       # ⭐
│   ├── test_rule_auditor.py            # ⭐
│   ├── test_llm_auditor.py             # ⭐
│   ├── test_literary_auditor.py        # ⭐
│   ├── test_revision_handler.py
│   ├── test_settlement_extractor.py    # ⭐
│   ├── test_graph.py
│   └── test_genre_profile.py
└── evals/
    └── runner.py
```

### 开发环境

```bash
# 安装开发依赖
pip install -e ".[dev]"

# 运行测试
pytest tests/ -v

# 运行评测
python evals/runner.py

# CLI 开发模式
songyan --debug write --project test --chapter 1
```

---

## 9. 参考与致谢

本项目的设计参考了以下优秀开源项目：

| 项目 | 作者 | 主要参考点 |
|------|------|------------|
| [InkOS](https://github.com/Narcooo/inkos) | Narcooo | 写-审-改循环、33 维审计、Hook 生命周期、状态结算 |
| [AI-Novel-Writing-Assistant](https://github.com/ExplosiveCoderflome/AI-Novel-Writing-Assistant) | ExplosiveCoderflome | 导演模式工作流、世界观管理 |
| [Terminal Velocity](https://github.com/mind-protocol/terminal-velocity) | mind-protocol | 多 Agent 自主协作架构 |

特别感谢 [LangGraph](https://github.com/langchain-ai/langgraph) 团队。

---

## 10. 许可证

AGPL-3.0

---

> **Songyan（松烟）**
>
> 松烟入墨，字句成锋。
>
> 项目状态: V1.0 开发中（单章闭环验证）
> 核心设计: 管线 + 插件架构，同一套系统服务网文与严肃文学
> 欢迎贡献: 特别是在题材配置、Prompt 调优、评测集建设、创作模式设计方面
