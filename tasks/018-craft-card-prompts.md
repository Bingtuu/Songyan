# Task 018: Craft Card Prompts — 工艺卡 Prompt 工程系统

## Goal

将现有 7 个扁平 `.md` Prompt 模板升级为**结构化、版本化、可观测的工艺卡系统**（Craft Card System），为每个 Agent 提供可迭代的 Prompt 资产，支持按标签动态加载、版本切换、热重载，并落地到实际写作场景中产生可量化的质量提升。

> **为什么叫"工艺卡"？**
> 
> 传统写作中，编辑会给作者一张"工艺单"："这段对话要体现性格差异""这个场景要激活嗅觉"。Craft Card 就是这个工艺单的系统化版本——它不是 system prompt 的简单堆砌，而是**分层、条件化、可度量**的结构化指令集。

---

## 现状诊断

当前 `prompts/` 目录有 7 个 `.md` 文件（共 462 行），每个 Agent 通过**硬编码路径**加载：

```python
# writer.py
prompt_path = Path(__file__).parents[3] / "prompts" / "writer.md"
```

**问题：**
1. **无版本**：无法对比 v1.0 和 v1.1 哪个写得好
2. **无结构**：所有指令平铺在 markdown 里，无法按条件（如"前三章""高潮章"）动态启用
3. **无观测**：不知道哪个工艺模块被命中、对输出质量的影响是什么
4. **无分层**：system prompt、约束条件、工艺指导、示例混在一起
5. **无动态**：不能按 genre（玄幻/都市）或 mode（网文/严肃）选择不同工艺

---

## Read

- `CLAUDE.md`（约束清单）
- `docs/INDEX.md`
- `docs/STATUS.md`
- `docs/architecture/04-vibe-coding-engineering.md` § Task 011 Writer、§ Task 018
- `src/songyan/agents/*.py` — 现有 Prompt 加载方式（`_load_prompt_template` + Jinja2）
- `prompts/*.md` — 现有 7 个模板
- `src/songyan/models/creative_mode.py` — CreativeModeProfile（模式选择影响工艺卡）
- `src/songyan/models/genre.py` — GenreProfile（题材选择影响工艺卡）

---

## In Scope

### 1. Craft Card Schema 定义（YAML）

每个工艺卡是一个 YAML 文件，结构如下：

```yaml
# craft_card.schema.yaml — 工艺卡元结构
metadata:
  agent: "writer"                    # 所属 Agent
  version: "1.0.0"                   # 语义化版本
  name: "网文玄幻标准工艺卡"          # 人类可读名称
  description: "适用于玄幻网文的通用写作工艺"
  tags: ["xuanhuan", "webnovel"]     # 匹配标签
  author: "songyan-team"
  created_at: "2026-05-25"
  updated_at: "2026-05-25"

# System Prompt 层 — Agent 身份定义
system_prompt: |
  你是 Songyan 的小说写作专家...

# 工艺层 — 结构化、条件化的写作指导
sections:
  - id: "golden_opening"
    name: "黄金开篇"
    description: "前 300 字的吸引力法则"
    tags: ["chapter_early"]           # 标签，由调用方决定是否启用
    weight: 1.0                        # 重要性权重（用于排序）
    content: |
      前 300 字必须满足以下至少一条：
      1. 人物处于动作中（跑、打、追、逃）
      2. 出现对话冲突
      3. 抛出具体悬念（不是"悬念"二字，而是一个具体事件）
      4. 主角面临明确的选择压力
      
      禁止：环境描写堆砌、抽象时间流逝、主角"突然想起"

  - id: "paragraph_rhythm"
    name: "段落节奏"
    weight: 1.0
    content: |
      段落长度分布：
      - 80-150 字：60%（叙事主力）
      - < 50 字：20%（对话/短冲击）
      - > 200 字：< 10%（超长段落需有场景切换标记）
      
      连续 3 个单句段落必须被中断（插入一个 80+ 字的段落）。

  - id: "dialogue_craft"
    name: "对话工艺"
    weight: 1.0
    content: |
      对话设计原则：
      1. 每个人物的说话方式必须可区分（语速、用词习惯、句式长短）
      2. 对话中必须有"潜台词"——字面意思 ≠ 真实意图
      3. "说"的替代词使用比例 < 30%（用动作、表情、环境反应替代）
      4. 禁止"解释性对话"（角色不会把已知信息再说一遍）

  - id: "show_dont_tell"
    name: "Show Don't Tell"
    weight: 1.0
    content: |
      禁止直接陈述情绪。以下表达必须转化为感官/动作描写：
      - ❌ "他很生气" → ✅ "他捏碎了茶杯，瓷片刺进掌心"
      - ❌ "她感到害怕" → ✅ "她的指甲掐进了门框的木头里"
      - ❌ "时间过得很慢" → ✅ "水滴从房檐落下，在空中悬停了三次心跳的时间"
      
      例外：极度压缩的过渡段落（< 50 字）可以简要陈述。

  - id: "info_release"
    name: "信息释放"
    weight: 1.0
    content: |
      信息释放节奏（每章）：
      - 新信息（读者不知道）：每 500 字至少 1 个
      - 旧信息提醒（读者可能忘记）：每 1500 字至少 1 个
      - 误导信息（暂时让读者以为 A，实际是 B）：每章最多 1 个
      
      禁止：信息倾倒（连续 300 字以上纯说明）。

  - id: "sensory_immersion"
    name: "感官沉浸"
    weight: 0.8                      # 权重略低，可实验调整
    content: |
      每个新场景必须激活至少 2 种感官：
      - 视觉（默认，不单独计数）
      - 听觉、触觉、嗅觉、味觉、温度、疼痛、平衡感
      
      高价值场景（战斗、告白、死亡）必须激活 3+ 种感官。

  - id: "ending_hook"
    name: "章末钩子"
    weight: 1.0
    content: |
      最后 200 字必须包含以下一种：
      1. 新威胁出现（具体的，不是"危险逼近"）
      2. 秘密揭露（反转一个已有的认知）
      3. 选择压力（主角必须做选择，但本章不给答案）
      4. 时间锁（"三日后大婚""子时前必须到达"）
      
      禁止："明天会怎样呢""他不知道更大的危机在等着他"——这些都是空话。

  - id: "new_setting_mark"
    name: "新设定标记"
    weight: 1.0
    content: |
      首次出现的新设定必须显式标记：
      - 格式：`[[新设定:设定名|类型|关联角色]]`
      - 示例：`[[新设定:玄天剑|法宝|主角]]`
      - 同章后续出现同一设定时，不再标记
      
      类型枚举：法宝、功法、地点、组织、人物、势力、规则

# 变量定义 — 渲染时注入
variables:
  - name: chapter_number
    type: int
    required: true
    description: "当前章节号"
  - name: chapter_type
    type: str
    required: true
    description: "章节类型"
  - name: word_count_target
    type: int
    required: true
  - name: target_events
    type: list[str]
    required: true
  - name: creative_brief
    type: dict
    required: true
    description: "CreativeBrief 对象"
  - name: genre_rules
    type: dict
    required: true
    description: "GenreProfile 规则"

# 示例 — Few-shot 示例（可选）
examples:
  - id: "good_opening"
    description: "好的开篇示例"
    text: |
      李三没有回头。他听到身后传来剑刃破空的声音，身体已经先一步向左翻滚——这个动作他在练武场重复过三千次，肌肉比脑子更快。
    
    why_good: |
      - 人物处于动作中（翻滚）
      - 激活听觉（剑刃破空）+ 触觉（肌肉记忆）
      - 没有环境描写堆砌
      - 主角面临即时威胁（选择压力）

  - id: "bad_opening"
    description: "差的开篇示例"
    text: |
      清晨的阳光洒在青石板路上，鸟儿在枝头歌唱。微风拂过，带来一丝凉意。李三走在路上，心情很好。
    why_bad: |
      - 纯环境描写，无人物动作
      - 无对话、无冲突、无悬念
      - "心情很好"是直接陈述（Show Don't Tell 违规）
```

### 2. 目录结构

```
prompts/
├── archive/                      # 旧 .md 归档（不加载）
│   ├── writer.md
│   ├── goal_planner.md
│   └── ...
├── cards/                        # 工艺卡目录
│   ├── writer/
│   │   ├── _manifest.yaml        # 版本清单 + 默认版本
│   │   ├── v1.0.0.yaml           # 基础版（当前 .md 的结构化升级）
│   │   └── v2.0.0-xuanhuan.yaml  # 玄幻特化版
│   ├── goal_planner/
│   │   ├── _manifest.yaml
│   │   └── v1.0.0.yaml
│   ├── creative_director/
│   │   ├── _manifest.yaml
│   │   └── v1.0.0.yaml
│   ├── llm_auditor/
│   │   ├── _manifest.yaml
│   │   └── v1.0.0.yaml
│   ├── literary_auditor/
│   │   ├── _manifest.yaml
│   │   └── v1.0.0.yaml
│   ├── revision_handler/
│   │   ├── _manifest.yaml
│   │   └── v1.0.0.yaml
│   └── settlement_extractor/
│       ├── _manifest.yaml
│       └── v1.0.0.yaml
└── __init__.py
```

### 3. `_manifest.yaml` 格式

```yaml
# prompts/cards/writer/_manifest.yaml
agent: "writer"
default_version: "1.0.0"

# 版本清单
versions:
  - version: "1.0.0"
    description: "基础网文工艺卡"
    tags: ["webnovel", "xuanhuan", "urban"]
    created_at: "2026-05-25"
  - version: "2.0.0-xuanhuan"
    description: "玄幻特化版，强化修炼体系描述规范"
    tags: ["xuanhuan"]
    created_at: "2026-05-27"
```

### 4. PromptLoader 模块

`src/songyan/prompts/loader.py` — 统一的工艺卡加载器。

```python
class CraftCard(BaseModel):
    metadata: CraftCardMetadata
    system_prompt: str
    sections: list[CraftCardSection]
    variables: list[CraftCardVariable]

class PromptLoader:
    """工艺卡加载器 — 模块级单例，通过 get_prompt_loader() 获取。"""

    def load_card(
        self,
        agent: str,
        version: str | None = None,           # None = 使用 default_version
        tags: list[str] | None = None,        # 标签过滤（如 ["xuanhuan", "chapter_early"]）
    ) -> CraftCard:
        """加载工艺卡。"""

    def list_versions(self, agent: str) -> list[VersionInfo]:
        """列出某 Agent 的所有可用版本。"""

    def render_card(
        self,
        card: CraftCard,
        variables: dict[str, Any],
    ) -> RenderedPrompt:
        """渲染工艺卡为最终 Prompt 字符串。"""
        # 1. 根据 tags 过滤启用的 sections
        # 2. 按 weight 排序（高权重在前）
        # 3. 用 Jinja2 渲染 system_prompt + 每个 section.content
        # 4. 拼接为最终 Prompt
        # 5. 记录渲染日志（哪个 section 被启用）

    def get_active_sections(
        self,
        card: CraftCard,
        tags: list[str] | None = None,
    ) -> list[str]:
        """返回实际启用的 section IDs（用于观测）。"""
```

**关键设计决策：**
- PromptLoader 是**模块级单例**，通过 `get_prompt_loader()` 获取。首次调用扫描 `prompts/cards/` 目录并缓存元数据
- 渲染结果缓存：同一 `(card_version, variables_hash)` 缓存 60 秒
- **无向后兼容 fallback**：Task 018 一次性完成迁移，旧 `.md` 移至 `prompts/archive/`

### 5. Agent 集成改造

**Writer Agent**（重点）：

```python
# 改造前
prompt_path = Path(__file__).parents[3] / "prompts" / "writer.md"
template = _load_prompt_template()
prompt = _render_prompt(context_package)

# 改造后
from songyan.prompts import get_prompt_loader

loader = get_prompt_loader()
card = loader.load_card(
    agent="writer",
    tags=[
        context_package.genre_rules.genre_id,
        context_package.creative_mode.mode_id,
        *("chapter_early" if context_package.chapter_goal.chapter_number <= 3 else []),
    ],
)
rendered = loader.render_card(card, {
    "chapter_number": goal.chapter_number,
    "chapter_type": goal.chapter_type,
    "creative_brief": context.creative_brief,
    "genre_rules": context.genre_rules,
    # ...
})
# rendered.system_prompt + rendered.sections_content
```

**其他 Agent**：GoalPlanner、CreativeDirector、LLMAuditor、LiteraryAuditor、RevisionHandler、SettlementExtractor 均改为通过 `PromptLoader` 加载，但结构相对简单（主要是 `system_prompt` + 少量 `sections`）。

### 6. 观测与度量

每次渲染时，PromptLoader 需要记录结构化日志：

```python
structlog.get_logger().info(
    "craft_card_rendered",
    agent="writer",
    version="1.0.0",
    project_id=project_id,
    chapter_number=chapter_number,
    active_sections=["golden_opening", "paragraph_rhythm", ...],
    rendered_length=len(rendered.full_prompt),
)
```

这些日志后续可用于：
- A/B 测试效果归因（哪个 section 的改动带来了什么质量变化）
- Prompt 长度监控（防止工艺卡膨胀导致 token 超支）
- 条件命中分析（"golden_opening" 在前三章的启用率）

### 7. 工艺卡内容编写（Writer 为重点）

**Writer Agent 工艺卡**需要包含以下 8 个工艺模块（从现有 `writer.md` + 工程手册提取）：

| 模块 ID | 名称 | 条件 | 来源 |
|---------|------|------|------|
| `golden_opening` | 黄金开篇 | `chapter_number <= 3` | 工程手册 + hook_checker |
| `paragraph_rhythm` | 段落节奏 | 无条件 | paragraph_rhythm.py 阈值 |
| `dialogue_craft` | 对话工艺 | 无条件 | Writer 现有约束 |
| `show_dont_tell` | Show Don't Tell | 无条件 | 写作通用原则 |
| `info_release` | 信息释放 | 无条件 | 叙事节奏理论 |
| `sensory_immersion` | 感官沉浸 | 无条件 | 沉浸感设计 |
| `ending_hook` | 章末钩子 | 无条件 | hook_checker |
| `new_setting_mark` | 新设定标记 | 无条件 | SettlementExtractor 需求 |

每个模块的 `content` 必须是**可执行**的——不是抽象原则，而是"如果满足 X 则做 Y，否则做 Z"的具体指令。

---

## Out of Scope

- 自动生成工艺卡（AI 自动写 Prompt）— 当前由人工编写
- 多语言工艺卡 — 仅中文
- Prompt 压缩/优化算法 — 仅结构化，不压缩
- 在线 Prompt 编辑 UI — 仅文件系统管理
- Task 019 LangGraph 编排 — 那是下一个任务

---

## Acceptance Criteria

### 基础设施
- [ ] `CraftCard`、`CraftCardSection`、`CraftCardVariable`、`CraftCardExample`、`VersionInfo` Pydantic 模型定义完整
- [ ] `PromptLoader` 实现 `load_card`、`list_versions`、`render_card`、`get_active_sections` 四个方法
- [ ] `_manifest.yaml` 解析正确，支持 `default_version` 和 `versions` 清单
- [ ] `get_prompt_loader()` 返回模块级单例，首次调用扫描目录并缓存
- [ ] 渲染结果缓存：同一 `(card_version, variables_hash)` 缓存 60 秒
- [ ] 单文件不超过 400 行（loader.py 超了则拆分 `renderer.py` + `resolver.py`）

### 工艺卡内容
- [ ] Writer 工艺卡 `v1.0.0.yaml` 包含全部 8 个模块，每个模块内容 >= 3 条可执行指令
- [ ] 至少 2 个模块带有 `tags`（如 `golden_opening: ["chapter_early"]`）
- [ ] 至少 1 个示例（few-shot）包含 `why_good` / `why_bad` 分析
- [ ] 其他 6 个 Agent（GoalPlanner/CreativeDirector/LLMAuditor/LiteraryAuditor/RevisionHandler/SettlementExtractor）各有一个基础工艺卡 `v1.0.0.yaml`

### Agent 集成
- [ ] Writer Agent 使用 `PromptLoader` 加载工艺卡，替代硬编码 `prompts/writer.md`
- [ ] 至少 3 个其他 Agent 使用 `PromptLoader`（优先 Writer、LLMAuditor、RevisionHandler）
- [ ] 集成后各 Agent 原有测试全部通过（向后兼容）

### 观测
- [ ] 每次 `render_card` 输出 `craft_card_rendered` 结构化日志
- [ ] 日志包含 `agent`、`version`、`active_sections`、`ab_variant`、`rendered_length`
- [ ] `get_active_sections` 可独立调用，返回本次渲染实际启用的 section IDs

### 测试
- [ ] PromptLoader 独立测试 >= 15 个（加载、渲染、A/B、缓存、fallback、条件过滤）
- [ ] 每个 Agent 至少 1 个集成测试验证"工艺卡内容确实出现在最终 Prompt 中"
- [ ] 标签过滤测试：传入 `["chapter_early"]` 时启用 golden_opening，不传时不启用
- [ ] 版本切换测试：手动切换 `default_version` 后加载到不同内容
- [ ] 缓存测试：第二次相同调用命中缓存
- [ ] `pytest` 全量通过，ruff 0 errors

---

## Dependencies

- Phase 1 全部完成（GenreProfile、CreativeModeProfile、Repository）
- Phase 2 全部完成（所有 Agent 已实现，现有 Prompt 模板存在）
- `jinja2` 已作为依赖（现有 Agent 已使用）
- `pyyaml` 需要确认是否已安装（如果没有，添加到 `pyproject.toml`）

---

## 落地场景示例

### 场景 1：开篇质量提升实验

> **问题**：玄幻新书前 3 章 AI 腔检测平均命中 4.2 个，用户反馈"像 AI 写的"。

**操作**：
1. 复制 `writer/v1.0.0.yaml` → `writer/v1.1.0.yaml`
2. 在 `golden_opening` 模块中新增 3 条更严格的约束
3. 修改 `_manifest.yaml` 的 `default_version` 为 `"1.1.0"`
4. 跑 10 章评测集对比 `ai_tell_count`

**预期**：如果 AI 腔 < 2，保留 v1.1.0 为 default_version；否则回退。

### 场景 2：按题材动态加载

> **问题**：都市文和玄幻文的"信息释放"节奏不同，共用同一套 Prompt 导致都市文节奏拖沓。

**操作**：
1. 创建 `writer/v1.0.0-urban.yaml`，将 `info_release` 的间隔从 500 字调整为 300 字
2. 在 `_manifest.yaml` 中配置 `tags: ["urban"]`
3. `load_card(agent="writer", genre="urban")` 自动匹配

### 场景 3：新 Agent 快速接入

> **问题**：新增 "StyleAuditor" Agent，需要快速获得一套可迭代的 Prompt。

**操作**：
1. 创建 `prompts/cards/style_auditor/_manifest.yaml`
2. 创建 `prompts/cards/style_auditor/v1.0.0.yaml`
3. StyleAuditor 代码中 `get_prompt_loader().load_card("style_auditor")`
4. 无需改 PromptLoader 代码

---

## Notes

- **工艺卡不是银弹**：它的价值在于"结构化"和"可观测"，而非内容本身有多精妙。内容可以通过 A/B 测试持续迭代。
- **避免过度工程**：初始版本不要追求每个模块都完美，先建立框架，再填充内容。
- **与 Task 019 的衔接**：Task 019 的 LangGraph 节点会调用 `PromptLoader.render_card()`，但 PromptLoader 本身不感知 LangGraph 存在。
