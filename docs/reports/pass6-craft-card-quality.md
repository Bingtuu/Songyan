# Craft Card Prompt 质量评估

> **范围**: prompts/cards/ 目录下 9 个 Agent 的 21 个 craft card 文件
> **视角**: 中文小说创作工具 — 评估 LLM Prompt 对网文生成的指导质量
> **日期**: 2026-06-10
> **审查者**: Codex

---

## 系统概览

Craft Card 是 Songyan 的 LLM Prompt 管理系统 — 每个 Agent 有独立的 YAML 工艺卡，含 Jinja2 模板、weighted sections、版本化 manifest。

```
prompts/cards/
├── writer/                   1.0.5 → 1.0.6 → 1.0.7    (活跃迭代)
├── creative_director/        1.0.0 → 1.0.1 → 1.0.3   (活跃迭代)
├── goal_planner/             1.0.0                    (稳定)
├── llm_auditor/              1.0.0 → 1.0.1 → 1.0.2  (活跃迭代)
├── literary_auditor/         1.0.0 → 1.0.1           (轻度迭代)
├── revision_handler/         1.0.0                    (稳定)
├── settlement_extractor/     1.0.0 → 1.0.1           (轻度迭代)
├── summary_writer/           1.0.0                    (稳定)
├── arc_summary_generator/    1.0.0                    (稳定)
└── volume_summary_generator/ 1.0.0                    (稳定)
```

**9 个 Agent，21 个版本，4 个活跃迭代中。**

---

## 一、系统级优势（从小说创作工具视角）

### 1.1 中文网文领域嵌入极深

Craft Card 中嵌入了大量中文网文的*操作性*知识——不是泛泛的文学理论，而是经过实战检验的具体写法：

**Writer 卡覆盖的网文技法**：
- 认知动词黑名单（13 个：知道、感到、意识到、明白、理解、认为、觉得、想起、记得、发觉、察觉、顿悟、领悟）
- 章末钩子 4 种具体变体（新威胁、秘密揭露、选择压力、时间锁）+ 5 种禁用模式
- 黄金开篇 4 种开局法（动作中、对话冲突、具体悬念、选择压力）
- 感官沉浸 7 种非视觉感官（听觉/触觉/嗅觉/味觉/疼痛/温度/平衡感）
- 信息释放节奏编码（每 500 字 1 新信息 / 每 1500 字 1 旧提醒 / 每章最多 1 误导）
- 段落节奏分布（60% 80-150 字 / 20% < 50 字 / < 10% > 200 字）
- 刺激点感官写作规则（禁止概括性表述，必须通过生理细节呈现）
- 角色语言指纹（语速、用词习惯、句式偏好、口头禅、语气）
- Show Don't Tell 的具体替换示例

**判断**：这是一个读过**大量**网文的系统。Prompt 中的大多数约束不是理论推导出来的，而是从实际网文阅读中提取的模式。这在中文小说 AI 写作工具中是非常罕见的深度。

### 1.2 防御性 Prompt 工程

```yaml
# Writer 卡的多层防御：
系统层: → Jinja2 SandboxedEnvironment（防 Prompt 注入）
模板层: → _escape_jinja2() 递归转义 Jinja2 定界符
输出层: → "禁止输出的元数据格式" 防 metadata 泄漏
内容层: → 段落长度分布硬约束
表现层: → 认知动词黑名单
```

**判断**：防御层级从代码到 prompt 内容都有覆盖。`_escape_jinja2()` 的递归转义是亮点——能防止 `{{` 在用户/LLM 输入中被当作模板指令。

### 1.3 Agent 链的 Prompt 设计合理

```
GoalPlanner:  简单结构化输出（1-3 events + hooks + word_count）
     ↓          → 产出 ChapterGoal（明确、简洁）
CreativeDirector: 丰富结构化输出（tensions + patterns + punch + emotion）
     ↓          → 产出 CreativeBrief（基于 Goal 的创作策略）
Writer:        消费上述所有 + ContextPackage → 生成正文
     ↓
LLM+RuleAuditor: 对照 Writer 的输出做多维度审查
     ↓
RevisionHandler: 只修问题，不整章重写
```

每个层级的 Prompt 详细度与职责匹配：
- GoalPlanner 只需要提炼关键点 → 简短
- CreativeDirector 需要策略性思考 → 中等
- Writer 需要融合所有输入 → 最详尽
- Auditor 需要评估质量 → 中等
- RevisionHandler 只需要定位和修改 → 中等

---

## 二、Writer 工艺卡深度评估（1.0.7）

Writer 卡是系统中最关键的 Prompt——它直接影响生成质量。以下从小说创作者视角逐块评估：

### 2.1 好的部分

**字数约束设计**（v1.0.7 新增 scene_budget）
```yaml
# 正确的设计选择：
- 不写死每个场景的字数（让 LLM 灵活分配）
- 总字数 ±10% 是唯一硬约束
- "字数不足必须扩展描写；超标必须删减"
```
这比固定分配的场景字数要合理——LLM 写作时，场景天然地需要不同篇幅。

**Hook 设计**（ending_hook section）
```yaml
# 非常精确的约束：
正确的结尾示例：
- "通讯器里传来一个陌生的声音：'别相信你看到的一切。'"
- "文件上的照片，是他自己。拍摄日期是三天后。"
```
给出了具体可以执行的示例，而不是抽象地说"要有悬念"。

**RAG 段落的使用指引**
```yaml
# 聪明的设计：
"以下段落来自历史章节，经语义检索判定与当前写作内容相关。
这些段落仅供参考，不要求必须引用。如果与当前章节目标冲突，以章节目标为准。"
```
没有把 RAG 结果当作硬性约束——LLM 仍然可以自由选择。这符合"辅助记忆"而不是"强制引用"的设计意图。

### 2.2 问题

#### Q1 — Prompt 总量过大（优先级：中）

Writer 卡的系统 prompt 本身就有 ~200 行 Jinja2 模板。加上最多 15 个 section（每个 3-8 行），再加载所有变量数据的渲染文本：

```
Writer prompt ≈ 系统模板(800-1200 tokens) + 15 sections(300-500 tokens)
               + 变量数据(ChapterGoal + CreativeBrief + character_states + 
                 recent_plot + foreshadowing + genre_rules + mode_rules + 
                 human_instructions + arc_context + volume_context + 
                 style_baseline + style_samples + punch_points + emotion_arc + 
                 rag_results + scene_budget)
               ≈ 3000-5000 tokens (仅 prompt 部分)
```

**影响**：在 Ch70+ 时，ContextPackage 本身已经是 18-25K tokens（V3.x 数据）。如果 Writer prompt 占了 5K+，留给生成的空间就会缩小。

**建议**：考虑把 sections 改为"按章节类型选择性注入"（目前所有 tags 的 section 都被注入），或者通过 Jinja2 的 conditionals 动态裁剪。

#### Q2 — 约束冗余导致优先级混乱（优先级：中）

「至少包含 2 个场景」出现在：
1. 输出要求第 2 条："必须至少包含 2 个场景"
2. golden_opening section："强制要求：全章必须至少包含 2 个场景"

「章末钩子」出现在：
1. 输出要求第 6 条："章末必须包含钩子"
2. ending_hook section（全文展开）

「字数」约束出现在：
1. 输出要求第 3 条（±10%）
2. scene_budget section
3. 变量注入的 word_count_target

**影响**：当这些约束被分散到多个位置时，LLM 的注意力权重会被稀释。如果将来修改了某一条，另一条忘记同步，就会出现矛盾指令。

#### Q3 — 约束冲突无协调指引（优先级：低）

以下约束存在潜在冲突，但 Prompt 中没有优先级指引：

| 约束 A | 约束 B | 冲突场景 |
|--------|--------|---------|
| "字数目标 ±10%" | "必须完成所有目标事件" | 事件太多写不完 |
| "至少 2 个场景" | "严格遵循字数目标" | 2 个场景撑不满字数 |
| "每个场景必须详细描写" | "过渡场景压缩到最低" | 边界模糊 |
| "黄金开篇前 300 字" | "节奏控制" | 开篇太浓可能破坏节奏 |

**影响**：LLM 在内部自行权衡，不同模型（DeepSeek vs GPT-4o）可能做出不同选择。对于认证过的 pipeline（DeepSeek），这已通过实际运行验证。如果更换模型，需要重新验证。

#### Q4 — `human_instructions` 变量名不匹配（优先级：低）

Jinja2 模板中：
```jinja2
{% for inst in human_instructions %}
- [{{ inst.action }}] {{ inst.content }}
```

Python 模型（`HumanInstruction`）中：
```python
class HumanInstruction(BaseModel):
    type: str       # ← 实际字段名是 type，不是 action
    content: str
```

两个不匹配。要么 `HumanInstruction` 有一个 `action` 属性（别名），要么渲染时做了格式转换。

**影响**：如果 `HumanInstruction` 确实有 `action` 字段（或别名），则无问题。如果没有，这个 template 会渲染出空值。需要在运行时确认。

---

## 三、Agent 链一致性评估

### 3.1 GoalPlanner → CreativeDirector → Writer：数据契约对齐

| 契约 | GoalPlanner 输出 | CreativeDirector 消费 | Writer 消费 |
|------|-----------------|---------------------|------------|
| target_events | ✅ 1-3 个事件 | ✅ 用于 tensions | ✅ 目标事件 |
| word_count_target | ✅ 2000-5000 | ❌ 未使用 | ✅ 字数目标 |
| hooks | ✅ 信息量钩子 | ❌ 未使用 | ✅ 章末钩子 |
| required_tensions | ❌ 不在范围 | ✅ 生成 | ✅ 张力引导 |
| forbidden_patterns | ❌ 不在范围 | ✅ 生成 | ✅ 禁忌清单 |
| punch_points | ❌ 不在范围 | ✅ 生成（如开启） | ✅ 刺激点执行 |

**评估**：GoalPlanner 和 CreativeDirector 之间有明确的分工 — 前者做规划（事件、字数），后者做策略（张力、风格）。Writer 消费两者的输出。数据契约基本对齐。

**建议**：CreativeDirector 的 JSON 输出中包含了 `mode_id`，但这个字段在 GoalPlanner 中已经存在。可以考虑移除 CreativeDirector 输出中的 `mode_id`（它在模型中已经被传递，不需要每层重复输出）。

### 3.2 Writer → Auditors：评估标准对齐

| Writer 强调的 | LLMAuditor 检查的 | 对齐 |
|---------------|-------------------|------|
| Show Don't Tell | ✅ 语义审查维度之一 | ✅ |
| 章节长度 ±10% | ✅ 字数检查 | ✅ |
| 章末钩子 | ✅ 审查维度之一 | ✅ |
| 段落节奏 | ✅ RuleAuditor 检测 | ✅ |
| 场景数量 | ✅ RuleAuditor 检测 | ✅ |
| 认知动词 | ✅ RuleAuditor 检测 | ✅ |

**评估**：Writer 的输出要求与 Auditor 的评估维度有良好的对应关系。RuleAuditor 负责可编程的检测（AI腔、疲劳词、段落节奏），LLMAuditor 负责语义级别的审查。这套对齐关系是 Songyan 相对于通用 AI 写作工具的核心优势。

### 3.3 Auditor → RevisionHandler：问题修复对齐

| Auditor 输出 | RevisionHandler 输入 | 对齐 |
|-------------|---------------------|------|
| ReviewIssue (severity + evidence_quote) | issues 变量 | ✅ |
| protected_fissures (来自 LiteraryAuditor) | protected_fissures 变量 | ✅ |
| Rewrite-only issues | rewrite_scene 类型不自动修复 | ✅ (Rule 26) |

**评估**：Auditor 的输出结构直接映射到 RevisionHandler 的输入模板。`evidence_quote` 字段是关键的定位信息，确保修订不是盲改。

---

## 四、中文网文特定题材适用性

### 4.1 当前支持的 Tags

```
webnovel, xuanhuan, urban, scifi, 
urban_fantasy, post_apocalyptic, mystery_noir, wuxia
```

8 个题材标签，覆盖了主要网文类型。

### 4.2 题材适配深度评估

Writer 卡的约束设计**明显以 webnovel 和 xuanhuan 为核心**（节奏要快、爽点密集、钩子驱动），其他题材的适配取决于 genre profile 提供的差异化配置。

以 scifi 为例：
- scifi 的核心需求（世界构建的逻辑自洽、科幻概念的内部一致性、基于规则的推理）在 Writer 卡的通用约束中部分覆盖
- 但专门为 scifi 设计的约束不多（没有"新科技引入必须基于已有科技树"之类的规则）
- CreativeDirector 的 `style_constraints` 可以通过 genre profile 注入 scifi 特定约束

**评估**：Writer 卡是一套**偏网文风格的通用模板**，题材差异主要通过 genre profile 的差异化配置来实现。对于 webnovel 和 xuanhuan，这是优势；对于 literary mode，部分约束（如信息释放节奏的 500/1500 字指标）可能过于机械化。

### 4.3 Literary Mode 适配

当前 craft card 系统中没有 literary_style 或纯文学模式的专用 section。Writer 卡的所有约束（段落节奏、信息释放、感官沉浸）都偏向网文的快节奏。

如果需要在 V4.1 支持 literary mode，Writer 卡需要添加：
- 允许更长的环境描写段落
- 降低信息释放节奏
- 允许更多内心独白和内心活动
- 支持更复杂的句式结构
- 减少"刺激点"类约束

---

## 五、版本管理评估

### 5.1 版本策略

```
Writer:     1.0.5 (风格参考) → 1.0.6 (RAG) → 1.0.7 (场景预算)
CreativeDirector: 1.0.0 → 1.0.1 → 1.0.2 → 1.0.3 (设定连续性)
```

**好**: 
- 每个版本的 changelog 语义明确（"新增"、"修复"、"收紧"）
- `default_version` 指针可以平滑切换
- tags 跨版本保持一致
- `_manifest.yaml` 标记了**所有兼容的题材**（8 个），而不是只标记当前验证的

**可改进**:
- 没有版本回退的自动机制（如果 1.0.7 导致质量下降，不能自动切回 1.0.6）
- 没有 A/B 测试框架来比较不同版本的效果
- CreativeDirector 跳过了 1.0.2（从 1.0.1 直接到 1.0.3），中间版本未公开

### 5.2 Section 系统的演化

v1.0.7 新增了 `scene_budget` section 和变量。但 section 的权重（weight）字段没有在模板渲染中使用：

```yaml
# section 定义中有 weight 字段
- id: "golden_opening"
  weight: 1.0

# 但 loader.py 中没有使用 weight 做任何事：
# 当前行为：所有匹配 tags 的 section 都按顺序添加
# 预期的行为：weight 高的 section 应该优先保留（在 token 裁剪时）
```

**建议**：weight 字段目前是"声明式"的（存在于 YAML 中但代码不使用）。要么利用它做预算裁剪时的 section 优先级排序，要么移除这个字段。

---

## 六、修复建议

| # | 问题 | 影响 | 建议 |
|---|------|------|------|
| C1 | Prompt 总量过大 | Ch70+ 时 5K+ tokens | 按 chapter_type 选择性注入 sections；或 ContextManager 裁剪时对 craft card 做 token 估算 |
| C2 | 约束冗余 | 修改不同步风险 | 每季度做一次约束去重（删掉在输出要求和 section 中重复的约束） |
| C3 | section weight 未使用 | 声明未执行 | 在 loader.py 的裁剪逻辑中使用 weight 字段排序 |
| C4 | `action` vs `type` 不匹配 | 模板渲染可能出空值 | 确认 HumanInstruction 是否有 action 字段；如果使用别名，更新文档 |
| C5 | 无版本回退机制 | 新版本质量问题 | 在 manifest 中添加 `fallback_version` 字段，当渲染异常时自动回退 |

---

> **松烟入墨，字句成锋。**
> Craft Card 是 Songyan 与通用 AI 写作工具之间的核心差异优势 — 
> 每一行 prompt 都是对网文创作实操经验的一种编码。
