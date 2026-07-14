# Task 172a: 体裁运行时画像（Genre Runtime Profiles）

> **阶段**: V8 多体裁可插拔支撑  
> **类型**: 架构/基础设施（Context Diet 2.0 运行时解耦）  
> **优先级**: P0  
> **依赖**: 172a.1 现状审计完成  
> **状态**: 拆分完成，待 172a.1 开工

## 背景

xuanhuan `--end 15` 在 Ch8 被硬门禁暂停：

```text
context_emergency_budget_ratio_halt: budget_used_before_emergency=1.4019 >= threshold=1.3
```

关键观测（Ch1-Ch8）：

| 指标 | 数值 | 说明 |
|---|---|---|
| ContextEmergency 触发 | 8/8 | 每章都触发紧急裁剪 |
| budget_used 峰值 | 1.40 | 超出默认 32K 预算 40% |
| genre_rules 长度 | 3499 字符 | scifi 仅 2531 字符，长 38% |
| Ch8 伏笔状态 | 10 planted / 3 due / 13 overdue | 回收链已崩 |
| 连续性审计 mismatch | Ch3=1, Ch6=2 | 随章节数恶化 |

V5–V7 的 Ch150/Ch200 验证全部集中在 `scifi/space_opera + webnovel_intense`，系统是按科幻的状态动力学调优的：角色少、设定集中、状态变化慢。xuanhuan 状态膨胀曲线完全不同——功法、境界、势力、法宝、地图等离散状态项多，导致 Context Diet 2.0 默认参数直接溢出。

这不是 xuanhuan 个例，而是**系统性过拟合**：默认运行时是科幻体裁的隐式画像。

## 目标

把 Context Diet 2.0 的运行时契约从科幻默认值中解耦，建立**体裁运行时画像（GenreRuntimeProfile）**机制，使不同体裁可拥有独立的：

1. Token 预算分配（genre_rules / mode_rules / character / setting / foreshadowing 权重）；
2. 硬门禁阈值（context_emergency_budget_ratio_halt、chapter_health_low 等）；
3. 状态压缩策略（出场角色衰减窗口、设定蒸发曲线、伏笔置信度衰减）；
4. 连续性审计敏感度（mismatch 容忍度、角色未出场阈值）。

首批覆盖体裁：xuanhuan、wuxia、urban、scifi。无画像体裁必须能回退旧行为（AGENTS.md 硬性兼容要求）。

## 根因分析

1. **常量硬编码**：ContextManager 中 budget、衰减参数、halt 阈值多为全局常量或环境变量，未与体裁关联。
2. **genre_rules 一刀切**：xuanhuan genre_rules 本身比 scifi 长 38%，仍占用相同 token 预算池，挤占角色/设定/伏笔空间。
3. **状态项密度假设错误**：科幻角色状态变化慢，默认角色衰减窗口对玄幻不适用；功法/境界等设定项增长快，默认蒸发曲线 archive 过早。
4. **验证覆盖单一**：过去 Ch200 长跑只证明 sci-fi 可行，未覆盖其他体裁的状态动力学。

## 外部调研

完整长调研报告见 `docs/reports/v8-literature-and-landscape-review.md`。本节只摘录对 172a 设计有直接影响的结论。

### 关键结论

1. **体裁差异是状态动力学差异**：xuanhuan 的功法/境界/势力/法宝/地图等高状态密度不是“prompt 风格”问题，而是导致上下文预算溢出的结构性问题（CreAgentive、DOME、ConStory-Bench 共同支持）。
2. **没有单一上下文策略能覆盖所有体裁**：外部最佳实践（AI Dungeon Memory/Lorebook、DOME hierarchical outline、StoryWriter 动态压缩）都强调按体裁调整运行时上下文策略。
3. **一致性评估需要专用密度指标**：ConStory-Bench 的 Consistency Error Density (CED) 可跨体裁公平比较，V8 验收应纳入。
4. **状态跟踪可升级方向**：FactTrack 的 pre-facts/post-facts + validity interval、CHIRON 的角色表 + 验证模块，可作为 V9 结构升级储备。

### GitHub 开源项目

- **[Novelgen](https://github.com/kirinonakar/Novelgen)**：使用**分层上下文 + 弧线管理**。长小说（13 章以上）仅保留当前 part 与相邻 part 的详细大纲，远端章节降维为标题+摘要；同时维护 Current Arc / Closed Arcs 两层结构，已闭合弧线用摘要代替原文。其 Context Management 明确区分了不同体裁的推荐上下文长度（短 outline 16k-24k，一般长篇 32k）。
  - 启示：GenreRuntimeProfile 应包含**弧线摘要策略**与**大纲降维策略**。

- **[Novel-OS](https://github.com/mrigankad/Novel-OS)**：使用**持久化中心状态 + 确定性连续性引擎**。所有 Agent 输出被解析并合并到 `story_state.json`，连续性引擎在 LLM Guardian 之前运行，检查 dormant_thread、overdue_thread、unresolved_foreshadowing 等。关键设计是**状态更新契约（OUTPUT CONTRACT）**让各 Agent 以结构化块输出。
  - 启示：不同体裁应能注册不同的连续性检查规则（如玄幻更关注境界/功法一致性，科幻更关注时间线/物理规则）。

- **[narrative-state-engine](https://github.com/daviburg/narrative-state-engine)**：TRPG 长战役的**结构化知识提取与状态跟踪**。核心原则：原始记录不可变、派生状态可重现、Catalog-first context。每个实体携带 `first_seen_turn` / `last_updated_turn` 来源，按回合构建聚焦实体上下文。
  - 启示：Profile 可引入**来源追踪**与**按章节构建聚焦上下文**策略，替换当前全局衰减。

### 学术论文

- **CreAgentive**（arXiv:2509.26461）：genre-agnostic Story Prototype + 多体裁三阶段 Agent workflow。
- **DOME**（arXiv:2412.13575）：Dynamic Hierarchical Outlining + temporal knowledge graph memory。
- **ConStory-Bench**（arXiv:2603.05890）：长故事一致性基准，提出 CED / GRR 指标。
- **FactTrack**（arXiv:2407.16347）：time-aware world state tracking with validity intervals。
- **CHIRON**（arXiv:2406.10190）：rich character sheet + validation module。

## 技术方案：GenreRuntimeProfile

引入 `GenreRuntimeProfile` Pydantic 模型，作为 Context Diet 2.0 的运行时契约。每个体裁可注册一个 Profile；系统启动时按项目 `genre` 加载对应 Profile；无 Profile 时回退到当前默认值（即 sci-fi 行为）。

### 数据模型（Pydantic v2）

```python
class GenreRuntimeProfile(BaseModel):
    genre: str
    version: str

    # 上下文预算
    context_budget_total: int = 32768
    context_budget_weights: dict[str, float] = {
        "genre_rules": 0.10,
        "mode_rules": 0.05,
        "chapter_goal": 0.10,
        "creative_brief": 0.05,
        "protagonist_profile": 0.10,
        "character_profiles": 0.25,
        "setting": 0.15,
        "foreshadowing": 0.08,
        "recent_chapters": 0.08,
        "summary": 0.04,
    }

    # 角色/设定/伏笔状态压缩
    character_decay_chapters: int = 5
    setting_evaporation_profile: SettingEvaporationProfile
    foreshadowing_evaporation_profile: ForeshadowingEvaporationProfile

    # 门禁阈值
    emergency_halt_threshold: float = 1.3
    chapter_health_low_threshold: float = 6.5
    continuity_mismatch_tolerance: dict[str, int] = {
        "critical": 0,
        "major": 1,
        "minor": 3,
    }

    # 高级策略开关
    arc_summarization_enabled: bool = False
    outline_dimming_enabled: bool = False
```

### 核心原则

1. **可插拔**：新增体裁只需新增一个 Profile 文件/记录，不修改核心逻辑。
2. **可回退**：无画像项目 100% 保持旧行为。
3. **可观测**：每个 Profile 字段必须进入 telemetry 表，便于审计不同体裁的运行时差异。
4. **MVP 边界**：172a 不新增 Agent/Workflow 节点，只做运行时参数解耦与注册表。

### 加载机制

```
project.genre -> lookup genre_runtime_profiles table
                -> if found: load and cache
                -> if not found: fallback to code-level default registry (scifi profile)
```

- 数据库优先：允许运行时调参后无需改代码即可生效。
- 代码默认注册表兜底：保证新环境/测试可立即运行。
- Project 记录 `runtime_profile_id` + `runtime_profile_snapshot`，确保每次生成可审计。

### 注入点

- `ContextManager.assemble_context()`：预算权重与总预算。
- `ContextEmergency`：halt 阈值与总预算。
- `HaltService` / `HealthGate`：health_low_threshold。
- `ContinuityAuditor`：mismatch 容忍度。
- `SettingEvaporator` / `ForeshadowingScheduleRepo`：蒸发曲线。
- `CharacterStateRepo`：衰减窗口。

## 子任务拆分

### 172a.1: 现状审计与常量提取

**目标**：把当前 Context Diet 2.0 中所有与体裁相关的硬编码常量/环境变量枚举出来，形成审计清单；并把当前 sci-fi 默认行为显式固化为 `GenreRuntimeProfile` 的 `scifi` profile。

**做**：

1. 在 `src/songyan/context/`、`src/songyan/agents/context_manager/`、`src/songyan/services/` 中扫描与 token budget、衰减、halt 阈值相关的常量。
2. 输出审计报告到 `docs/reports/172a.1-context-diet-constants-audit.md`，字段包括：常量名、当前值、所在文件、是否体裁敏感、建议归属 Profile 字段。
3. 识别哪些字段已被环境变量覆盖，哪些完全硬编码。
4. 基于当前默认值，先生成 `scifi` profile 的完整字段快照，作为后续所有体裁调参的 baseline；该快照写入 `docs/reports/172a.1-scifi-baseline-profile.json` 并登记到 `genre_runtime_profiles` 表。

**不做**：

- 不修改任何常量值；
- 不引入新抽象。

**验收**：

- 审计报告覆盖 ContextManager、ContextEmergency、ChapterGoal 装配、伏笔蒸发、角色衰减等模块；报告通过 code review。
- `scifi` baseline profile 完整字段快照与当前默认行为等价，可被后续回归验证。

---

### 172a.2: GenreRuntimeProfile 数据模型 + 数据库表

**目标**：建立 `GenreRuntimeProfile` Pydantic v2 模型与数据库表。

**做**：

1. 新增 `src/songyan/models/genre_runtime_profile.py`，定义 `GenreRuntimeProfile`。
2. 字段覆盖：
   - `context_budget_total`: int（默认 32768）
   - `context_budget_weights`: dict[str, float]
   - `character_decay_chapters`: int
   - `setting_evaporation_profile`: dict（resolve_confidence 阈值与蒸发速率）
   - `foreshadowing_evaporation_profile`: dict（due 窗口、overdue 阈值）
   - `emergency_halt_threshold`: float
   - `chapter_health_low_threshold`: float
   - `continuity_mismatch_tolerance`: dict
   - `arc_summarization_enabled`: bool
   - `outline_dimming_enabled`: bool
3. 新增 migration 在 SQLite 创建 `genre_runtime_profiles` 表；`genre` 字段唯一。
4. 注册默认 Profile（即当前 sci-fi 行为），保证回退。

**不做**：

- 不把所有 Prompt 都参数化；只参数化运行时契约。

**验收**：

- 模型通过 Pydantic validation；
- migration 可上下迁移；
- 默认 Profile 能正确加载。

**测试**：

```python
# tests/models/test_genre_runtime_profile.py
def test_default_profile_is_sci_fi_fallback():
    profile = load_profile("scifi")
    assert profile.context_budget_total == 32768

def test_xuanhuan_profile_has_higher_budget():
    profile = load_profile("xuanhuan")
    assert profile.context_budget_weights["setting"] > load_profile("scifi").context_budget_weights["setting"]
```

---

### 172a.3: 按体裁加载 Profile

**目标**：项目初始化时根据 `genre` 加载对应 Profile；无匹配时回退默认。

**做**：

1. 在 `src/songyan/services/project_service.py`（或类似入口）新增 `get_runtime_profile(genre: str)`。
2. 优先从数据库 `genre_runtime_profiles` 加载；数据库无记录则 fallback 到代码内默认注册表。
3. 将 Profile 注入 `ContextManager`、`ContextEmergency`、`ContinuityAuditor` 等依赖。
4. 在 `Project` 模型/状态中添加 `runtime_profile_id` 或 `runtime_profile_snapshot`，确保每次生成可审计当时使用的 Profile。

**不做**：

- 不在 Agent 节点中动态切换 Profile；每个项目运行期 Profile 固定。

**验收**：

- sci-fi 项目行为不变；
- xuanhuan 项目能加载 xuanhuan Profile；
- 未知体裁回退默认。

---

### 172a.4: Context Diet 预算分配按体裁

**目标**：让 `ContextManager` 按 Profile 的权重和总预算组装上下文包。

**做**：

1. 修改 `ContextManager.assemble_context()`，将硬编码的预算分配替换为 `profile.context_budget_weights`。
2. `ContextEmergency` 触发逻辑改用 `profile.context_budget_total` 与 `profile.emergency_halt_threshold`。
3. 对 xuanhuan Profile 初步调参：提高 setting 权重、降低部分 genre_rules 挤占；确保 Ch8 budget_used 峰值 < 1.0（不触发 emergency）。

**不做**：

- 不调整 Prompt 内容本身；只调整装配预算。

**验收**：

- xuanhuan `--end 15` 不再因 budget_used > 1.3 被 halt；
- scifi `--end 10` regression 通过。

---

### 172a.5: 硬门禁阈值按体裁

**目标**：把 halt/health 等硬门禁阈值从全局常量迁移到 Profile。

**做**：

1. 修改 `src/songyan/services/halt_service.py`（或对应门禁服务），从 Profile 读取阈值。
2. 修改 health/orphan/T12 等 gate 的判定阈值来源。
3. 对 xuanhuan 调整：`context_emergency_budget_ratio_halt` 可适度提高（如 1.5），但同步要求 ContextManager 把 budget_used 压到 < 1.0；health_low_threshold 保持不变。

**不做**：

- 不放宽 T9/T10/T12 冻结口径。

**验收**：

- 门禁阈值来源可通过 telemetry 查询；
- xuanhuan `--end 15` 不被 budget halt 阻塞。

---

### 172a.6: 状态压缩与伏笔蒸发按体裁

**目标**：角色衰减、设定蒸发、伏笔回收策略按体裁定制。

**做**：

1. 修改角色档案衰减逻辑，使用 `profile.character_decay_chapters`。
2. 修改设定/伏笔蒸发逻辑，使用 `profile.setting_evaporation_profile` / `profile.foreshadowing_evaporation_profile`。
3. 对 xuanhuan：
   - 角色衰减窗口缩短（玄幻角色出场密度高）；
   - 设定蒸发放慢（功法/境界需长期保持）；
   - 伏笔 due 窗口拉长并区分 major/minor。
4. 若启用 `arc_summarization_enabled`，对已闭合 arc 的章节摘要做二级压缩。

**不做**：

- 不引入全新的大纲摘要 Agent；只启用已有 SummaryWriter 输出的 arc 级摘要。

**验收**：

- xuanhuan Ch8 overdue foreshadowing 数量下降；
- 角色档案加载 token 可控。

---

### 172a.7: 多体裁验证窗口与回归

**目标**：建立多体裁短窗口验证 harness，确保改动不破坏 sci-fi，同时让 xuanhuan 通过 end 15/20。

**做**：

1. 新增/复用 `scripts/run_172a_short_window_preserve.py`，支持 `--templates xuanhuan|wuxia|urban|scifi --end N`。
2. 每个子任务完成后跑：
   - scifi `--end 10`（回归）；
   - xuanhuan `--end 15`；
   - xuanhuan `--end 20`（最终）；
   - wuxia `--end 10`；
   - urban `--end 10`。
3. 输出指标：ContextEmergency 频率、budget_used 峰值、连续性审计 mismatch 数、伏笔 planted/due/overdue、accepted 率、CED。
4. 将结果写入 `docs/reports/172a.7-genre-short-window-validation.md`。

**不做**：

- 不在 172a 内做 Ch100+ 长跑；只验证短窗口。

**验收**：

- xuanhuan `--end 15` 100% accepted，无 budget halt；
- scifi `--end 10` 维持原口径；
- wuxia/urban `--end 10` 不出现 budget halt。

## 验证指标

| 面 | 判据 |
|---|---|
| 架构 | GenreRuntimeProfile 可插拔，无画像回退旧行为 |
| 数据 | `genre_runtime_profiles` 表存在，默认 sci-fi 记录与当前行为等价 |
| 基线 | `scifi` profile 快照完整，可通过 `--end 10` 回归验证行为等价 |
| xuanhuan end 15 | 8/8 accepted，无 context_emergency_budget_ratio_halt |
| xuanhuan end 20 | 20/20 accepted，或 gaps 有明确 isolate 记录 |
| scifi regression | `--end 10` 100% accepted，指标不劣化 |
| wuxia/urban | `--end 10` 无 budget halt |
| 一致性 | xuanhuan Ch8 overdue foreshadowing < 5（基线 13） |
| 密度 | 引入 Consistency Error Density (CED)：`(critical + major issues with evidence_quote) / chapter_words`，各体裁 CED ≤ sci-fi 同级 |
| 测试 | pytest 全绿，ruff 无新增错误 |

## 出口标准

Task 172a 完成后需产出：

1. `tasks/172a-v8-genre-runtime-profiles-DONE.md` 记录最终参数与验证结果；
2. `docs/reports/172a.1-context-diet-constants-audit.md` 与 `docs/reports/172a.1-scifi-baseline-profile.json`；
3. `docs/reports/172a.7-genre-short-window-validation.md` 多体裁短窗口报告；
4. 将 xuanhuan/wuxia/urban Profile 登记到 `docs/STATUS.md` 的 V8 阶段事实；
5. 明确 Task 172b（Ch100+ 多体裁长跑验证）的触发条件。

## 验证命令

```powershell
# 默认回归
python -m pytest tests/ -q
ruff check src/ tests/

# 多体裁短窗口验证
python scripts/run_172a_short_window_preserve.py --templates xuanhuan --end 15 --output .tmp/task172a_xuanhuan_end15.json
python scripts/run_172a_short_window_preserve.py --templates xuanhuan --end 20 --output .tmp/task172a_xuanhuan_end20.json
python scripts/run_172a_short_window_preserve.py --templates scifi    --end 10 --output .tmp/task172a_scifi_end10.json
python scripts/run_172a_short_window_preserve.py --templates wuxia    --end 10 --output .tmp/task172a_wuxia_end10.json
python scripts/run_172a_short_window_preserve.py --templates urban    --end 10 --output .tmp/task172a_urban_end10.json
```

## 撞墙路由

如 172a.4/172a.5 调参后仍无法压下 xuanhuan budget_used，说明仅调整预算分配不够，需要提前启动 **弧线摘要/大纲降维**（172a.6 子集），或拆出 `172a.p-context-summarization-pilot` 进行 Prompt 级摘要实验，不在 172a 内无限放宽阈值。
