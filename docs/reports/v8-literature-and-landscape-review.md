# V8 长篇生成外部调研：跨体裁、记忆管理与一致性

> 调研目标：在重新审视 V8 规划之前，系统梳理外部项目与学术论文对“跨体裁长篇生成”的解决方案，确认 Songyan 当前问题在学术/工程上的定位，并为 `GenreRuntimeProfile` 的设计与 V8 验收标准提供外部依据。
>
> 调研日期：2026-07-14
> 覆盖范围：GitHub 开源项目、arXiv 2023–2026 年长文本/故事生成论文、AI 叙事产品公开文档

---

## 1. 调研问题

1. 跨体裁长篇生成的公开项目如何组织体裁差异？
2. 长文本一致性与记忆管理的最新方法有哪些？
3. sci-fi / fantasy / wuxia / urban 在叙事结构、状态密度、伏笔模式上有什么差异？
4. 运行时参数化 / genre-aware context management 有哪些工程实践？
5. 跨体裁长篇生成的评估方法论是什么？

---

## 2. 关键项目与论文速览

### 2.1 跨体裁/长篇生成框架

| 项目/论文 | 核心思想 | 与 Songyan 的相关性 |
|-----------|----------|---------------------|
| **CreAgentive** (Cheng et al., arXiv:2509.26461) | 提出 **Story Prototype**：用 genre-agnostic 知识图谱（角色/事件/环境三元组）把“故事逻辑”与“风格实现”解耦；三阶段 Agent 工作流可在多个体裁稳定生成数千章，$<\$1 / 100 章。 | 最高层参考：长期可把“叙事骨架”做成体裁无关的 Story Prototype，但 V8 只取“解耦”原则，先解耦运行时常量/阈值。 |
| **DOME** (Hu et al., NAACL 2025, arXiv:2412.13575) | **Dynamic Hierarchical Outlining + Memory-Enhancement**：把小说写作理论融入大纲规划，用基于时序知识图的记忆模块减少上下文冲突。 | 支撑 V6 骨架方向：outline 与 memory 必须协同；Context Diet 2.0 的弧线摘要可借鉴其 hierarchical outline 思想。 |
| **StoryWriter** (Xia et al., arXiv:2506.16445) | 多智能体框架：outline agent（事件级大纲）→ planning agent（分章）→ writing agent（动态压缩历史）。 | 与 Songyan 现有 workflow 结构类似，可作为验证“outline-plan-write + 动态压缩”路线的外部佐证。 |
| **Multigenre AI-powered Story Composition** (de Lima et al., arXiv:2405.06685) | 用 **genre patterns**（comedy / romance / tragedy / satire / mystery）引导交互式叙事，保证主题一致性。 | 说明体裁差异不仅是风格，更是叙事结构；V8 当前只调工程参数，未来可引入更上层的 genre-specific narrative patterns。 |

### 2.2 一致性与记忆管理

| 项目/论文 | 核心思想 | 与 Songyan 的相关性 |
|-----------|----------|---------------------|
| **ConStory-Bench** (Li et al., arXiv:2603.05890) | 长故事一致性基准：2,000 prompts、4 场景、5 大类 19 子类错误；发现**事实/时间类错误最常见**，且多出现在叙事**中段**；提出 CED / GRR 指标。 | 直接把 Songyan 的 T9/T10/T12/连续性审计放进更大评估框架；建议 V8 引入“错误密度”指标。 |
| **FactTrack** (Lyu et al., arXiv:2407.16347) | **Time-aware world state tracking**：把事件分解为 pre-facts / post-facts，维护每个原子事实的 validity interval，检测时间区间重叠的矛盾。 | 与 Songyan settlement_extractor 高度相关：当前状态更新是点式的，可升级成带 validity interval 的时序世界状态。 |
| **CHIRON** (Gurung & Lapata, EMNLP Findings 2024, arXiv:2406.10190) | **角色表（character sheet）**：Dialogue / Physical-Personality / Knowledge / Goals 四类，生成+验证模块过滤不一致描述；提出 `density` 指标衡量角色中心度。 | Songyan `character_states` 快照可借鉴其结构化和验证思路；density 可用于量化不同体裁的角色状态膨胀。 |
| **Story-Bench** (clchinkc, GitHub) | 三源验证：程序化指标 + LLM judge + ensemble；可复现 YAML、A/B 对比、增量执行。 | V8 多体裁回归可借鉴其“head-to-head comparison + statistical breakdown”。 |
| **AI Dungeon / NovelAI / SillyTavern** | **Memory + Lorebook + Author's Note**：用触发词把知识库条目注入上下文，本质上是用户可维护的 RAG-like 记忆系统。 | Songyan 的 Context Diet 2.0 已在做类似事情；可学习其“条目级来源追踪”与“触发式注入”。 |
| **CORRPUS / COTTAGE** (Dong et al., UPenn) | 用代码表示做神经符号状态跟踪，维护 text adventure 的 world model。 | 说明状态跟踪可以结构化、可验证；V8 的状态压缩/蒸发策略可更明确化。 |

### 2.3 开源清单汇总

- [Picrew/awesome-llm-story-generation](https://github.com/Picrew/awesome-llm-story-generation)：288 项、10 个分类的精选列表，是持续跟踪该领域的最佳入口。
- [ConStory-Bench](https://github.com/Picrew/ConStory-Bench)：一致性评估 pipeline，可直接参考其错误分类。
- [FSM-LLM-Narrative](https://github.com/rosasun51/FSM-LLM-Narrative)：基于 FSM 的动态叙事处理，适合游戏化叙事参考。
- [story-bench](https://github.com/clchinkc/story-bench)：生产化评估平台设计。

---

## 3. 核心发现

### 3.1 体裁差异本质上是“状态动力学”差异

外部文献一致表明：不同体裁的差异不仅是 prompt 风格，而是**状态密度、变化速率、伏笔结构、角色出场模式**的差异。

| 体裁 | 状态密度 | 状态变化特征 | 伏笔/回收模式 | 对 Context 的压力 |
|------|----------|--------------|---------------|-------------------|
| **sci-fi / space_opera** | 中 | 设定集中，物理/时间规则变化慢 | 长程、机制型 | 中，角色少 |
| **xuanhuan（玄幻）** | **极高** | 功法、境界、势力、法宝、地图快速膨胀 | 密集、等级跃迁驱动 | **高**，默认预算易溢出 |
| **wuxia（武侠）** | 中高 | 武功、门派、兵器、恩怨关系变化 | 事件驱动、仇杀/传承 | 中高 |
| **urban（都市）** | 中 | 现代社会背景稳定，人际关系/商业线变化 | 生活流、情感线 | 中，但对话/关系密集 |
| **mystery / noir** | 中 | 事实/线索状态逐步揭露 | 谜面-谜底强约束 | 高，对事实一致性敏感 |

> 关键结论：**不存在一个“万能上下文策略”能同时最优覆盖这些差异。** 这与 Songyan xuanhuan `--end 15` 在 Ch8 因 budget_used 1.40 触发 halt 的观测完全一致。

### 3.2 上下文管理需要三层解耦

外部项目的最佳实践可归纳为三层：

1. **叙事逻辑层（story logic）**：体裁无关的骨架（Story Prototype / 知识图谱 / outline）。
2. **运行时参数层（runtime profile）**：按体裁定制的预算、阈值、压缩策略。
3. **风格实现层（style realization）**：genre/mode 特定的 prompt、语料、韵律。

Songyan 目前：**第 3 层较完善（genres/、creative_modes/），第 1 层刚起步（V6 骨架），第 2 层缺失（Context Diet 2.0 常量仍是 sci-fi 隐式画像）**。这正是 V8 的抓手。

### 3.3 记忆/状态跟踪需要“时序有效性”

FactTrack 的 pre-fact / post-fact / validity interval 表明：长篇一致性不能只靠“当前状态快照”，而需要知道**事实在什么时间区间有效**。Songyan 当前的 `character_states` 是 INSERT-only 快照，`foreshadowings` 有 `source_version_id`，但设定项尚未显式维护 validity interval。这是 V9 或更晚可升级的方向。

### 3.4 角色表示需要结构化 + 验证

CHIRON 证明：简单 summary 在角色一致性任务上不如结构化 character sheet，且 LLM 生成的角色描述有 **32.6% 不一致**。Songyan 的 `character_states` 已有快照机制，但可进一步：

- 把角色信息按 Dialogue / Physical / Knowledge / Goals 分类；
- 增加 entailment/验证步骤，防止 settlement 把幻觉写入长期事实源；
- 用 density 指标监控不同体裁的角色状态膨胀。

### 3.5 评估必须包含“一致性专用”指标

ConStory-Bench 把一致性错误分为 5 类 19 子类，并发现：

- **事实/时间错误最常见**；
- 错误集中在叙事**中段**；
- 高 token 熵段落更易出错。

Songyan 当前已有 T9/T10/T12、连续性审计、health、orphan 等指标，但缺乏像 **Consistency Error Density (CED)** 这样跨体裁可比的密度指标。建议 V8 引入 CED-like 汇总指标。

---

## 4. 对 Songyan 当前问题的映射

### 4.1 问题诊断

- **系统性过拟合 sci-fi**：V5–V7 的 200 章长跑证明的是“sci-fi 状态动力学下的系统可用”，而非“通用长篇生成系统”。
- **运行时契约未解耦**：Context Diet 2.0 的预算、阈值、衰减参数与 genre 无关，导致 xuanhuan 这类高状态密度体裁直接溢出。
- **缺乏体裁级回归**：没有为 xuanhuan/wuxia/urban 建立 end 10/15/20 的短窗口基准，无法提前发现过拟合。

### 4.2 GenreRuntimeProfile 的学术/工程支撑

`GenreRuntimeProfile` 的方向与外部证据高度一致：

- **CreAgentive** 的 genre-agnostic Story Prototype + style realization 解耦，支持“同一大纲、不同体裁”的可插拔思想。
- **AI Dungeon / NovelAI / SillyTavern** 的 Memory/Lorebook 机制说明：用户/系统需要按场景定制上下文注入策略。
- **DOME / StoryWriter** 说明：大纲层级、记忆增强、动态压缩必须在运行时根据体裁状态密度调整。
- **ConStory-Bench** 说明：不同体裁的一致性错误分布不同，审计敏感度也应可调。

因此，V8 的 `GenreRuntimeProfile` 不是临时补丁，而是把 Songyan 从“单一体裁优化”升级为“体裁可插拔平台”的必经工程。

### 4.3 可直接借鉴的具体技术

| Songyan 现有模块 | 可借鉴的外部技术 | 落地优先级 |
|------------------|------------------|------------|
| `ContextManager` 预算分配 | DOME 的 hierarchical outline + memory weights；AI Dungeon 的 Lorebook 触发注入 | **V8 核心** |
| `ContextEmergency` | 运行时 threshold profile；避免单一 budget ratio halt | **V8 核心** |
| `character_states` | CHIRON 结构 + 验证模块 | V8.2 或 V9 |
| `settlement_extractor` | FactTrack 的 pre/post-facts + validity interval | V9 |
| `continuity_auditor` | ConStory-Checker 的三阶段 pipeline + 错误分类 | V8 可部分引入 |
| 评估 harness | Story-Bench 的 A/B 对比 + ensemble judge | V8.1 短窗口回归 |

---

## 5. 对 V8 规划的建议

### 5.1 认可当前 V8 方向

当前 `tasks/V8-README.md` 与 `tasks/172a-v8-genre-runtime-profiles.md` 的方向是正确的：

- 把 Context Diet 2.0 的运行时契约从 sci-fi 隐式画像解耦；
- 用短窗口（end 10/15/20）快速验证多体裁质量同标；
- 明确不做新 Agent/Workflow，只做运行时参数化。

这与外部文献的共识一致：**没有单一上下文策略能覆盖所有体裁，必须在运行时根据体裁状态动力学调整。**

### 5.2 建议补充四点

#### （1）sci-fi baseline 必须显式化

V7 的 sci-fi 成功依赖于一组**未文档化的默认参数**。建议：

- 把当前默认值固化为 `GenreRuntimeProfile` 中的 `scifi` profile；
- 明确记录 sci-fi 的 budget weights、decay 参数、halt 阈值；
- 任何 V8 改动必须以“sci-fi `--end 10` 回归等效”为硬性门槛。

> 理由：CreAgentive 等系统都会显式保存 baseline profile，否则无法证明新体裁改动没有回退旧行为。

#### （2）把 xuanhuan 的验证作为“压力测试”而不仅是“目标体裁”

xuanhuan 的高状态密度使其成为 Context Diet 2.0 的极端压力测试。建议：

- 在 172a.1 审计中把 xuanhuan Ch8 的 `budget_used=1.4019` 作为关键 case study；
- 172a.4 的目标不应只是“不触发 halt”，而是“budget_used 峰值 < 1.0 且不连续触发 ContextEmergency”。

#### （3）引入 CED-like 一致性密度指标

参考 ConStory-Bench，建议 V8 增加跨体裁可比的 **Consistency Error Density (CED)**：

```text
CED = (critical + major issues with evidence_quote) / total_chapter_words
```

这样可以在不同体裁之间公平比较，而不是只看 accepted 率。

#### （4）建立多体裁短窗口回归 harness

建议把以下命令纳入 CI/验证清单：

```powershell
python scripts/run_172a_short_window_preserve.py --templates scifi    --end 10
python scripts/run_172a_short_window_preserve.py --templates xuanhuan --end 15
python scripts/run_172a_short_window_preserve.py --templates wuxia    --end 10
python scripts/run_172a_short_window_preserve.py --templates urban    --end 10
```

并记录：ContextEmergency 频率、budget_used 峰值、CED、overdue foreshadowing 数。

### 5.3 对 sci-fi 是否需要在 V8 做“对齐迭代”的判断

建议：**在 V8.1 内做一次 sci-fi profile 显式化验证，但不重新做文学性专项。**

- 把当前 sci-fi 默认参数写成 profile；
- 跑 `--end 10` 验证行为等价；
- 若等价，则 sci-fi 不需要再做额外迭代；若发现默认参数本身有隐藏问题，则定点修复。

这样既保证底盘不回退，又避免重复 V7 的文学性工程。

---

## 6. 结论

外部调研支持 V8 的核心判断：

1. **体裁差异是状态动力学差异**，不是 prompt 风格差异；xuanhuan 的预算溢出是系统对 sci-fi 过拟合的必然结果。
2. **GenreRuntimeProfile 是正确方向**，与 CreAgentive、DOME、AI Dungeon/NovelAI 等外部最佳实践一致。
3. **V8 的边界合理**：先做运行时参数解耦，再做状态结构升级（CHIRON/FactTrack 留到 V9）。
4. **验收标准应包含一致性密度指标**，而不仅是 accepted 率。

建议按现有 172a.1–172a.7 子任务推进，同时补充 sci-fi profile 显式化与 CED 指标。

---

## 附录：主要参考文献

1. Cheng, Y., Cai, L., Peng, C., Xu, Y., Bie, R., & Zhao, Y. (2025). *CreAgentive: An Agent Workflow Driven Multi-Category Creative Generation Engine*. arXiv:2509.26461.
2. Hu, J., et al. (2024). *Generating Long-form Story Using Dynamic Hierarchical Outlining with Memory-Enhancement*. NAACL 2025. arXiv:2412.13575.
3. Xia, H., et al. (2025). *A Multi-Agent Framework for Long Story Generation*. arXiv:2506.16445.
4. Li, J., et al. (2026). *Consistency Bugs in Long Story Generation by LLMs*. arXiv:2603.05890.
5. Lyu, Z., Yang, K., Kong, L., & Klein, D. (2024). *FactTrack: Time-Aware World State Tracking in Story Outlines*. arXiv:2407.16347.
6. Gurung, A., & Lapata, M. (2024). *CHIRON: Rich Character Representations in Long-Form Narratives*. EMNLP Findings 2024. arXiv:2406.10190.
7. de Lima, E. S., Neggers, M. M. E., & Furtado, A. L. (2024). *Multigenre AI-powered Story Composition*. arXiv:2405.06685.
8. Dong, R.-Y. (2023). *COTTAGE: Coherent Text Adventure Games Generation*. Master's Thesis, University of Pennsylvania.
9. AI Dungeon. *The Memory System*. https://help.aidungeon.com/faq/the-memory-system
10. Picrew. *awesome-llm-story-generation*. https://github.com/Picrew/awesome-llm-story-generation
11. clchinkc. *story-bench*. https://github.com/clchinkc/story-bench
