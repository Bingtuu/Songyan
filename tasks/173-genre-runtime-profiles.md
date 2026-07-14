# Task 173: 项目模板与体裁运行时配置（Genre-Aware Runtime Profiles）

> **状态**: 🔄 进行中  
> **负责人**: 待分配  
> **目标窗口**: V7 阶段入口  
> **依赖**: V5/V6 已完成（sci-fi 长距离验证基础）、当前在 `task/173-project-templates` 分支上已修复 xuanhuan Ch3 settlement 数值问题

---

## 一句话目标

把系统从“按 sci-fi/space_opera 标定的单一引擎”改造成“可被不同体裁参数化的引擎”：通过 `GenreRuntimeProfile` 承载 Context Diet 预算、硬门禁阈值、状态压缩规则、伏笔蒸发强度、telemetry 识别等运行时契约，使 xuanhuan、wuxia、urban_fantasy 等体裁也能达到各自的长距离验证窗口。

---

## 背景与根因

V5/V6 的长距离验证（Ch1-Ch150 / Ch200 go/no-go）全部集中在 **sci-fi/space_opera + webnovel_intense + 主角林渊** 这一个项目窗口。`docs/reports/v7-literary-framework-review.md` 已指出这是“验证过拟合到一个点”。

xuanhuan `--end 15` 验证在 **Ch8 触发硬门禁暂停**：

```text
context_emergency_budget_ratio_halt: budget_used_before_emergency=1.4019 >= threshold=1.3
```

这不是 xuanhuan 的局部 bug，而是系统把 sci-fi 的最优参数当成了全局默认。核心差异：

| 维度 | sci-fi | xuanhuan |
|---|---|---|
| 结算状态 | telemetry 读数（短） | 叙事段落（physical_state / knowledge，长） |
| 伏笔 | 短-中周期 | 长周期、密集 |
| 设定增殖 | 稳定（飞船、结构） | 高速（功法、法宝、势力、秘境） |
| genre_rules 长度 | 2531 字符 | 3499 字符（+38%） |
| 上下文预算 | 32K 刚好 | Ch3 起即触 emergency |

---

## 参考方案（外部调研）

- **Recursive Summarization for Long-Term Dialogue Memory** ([arXiv:2308.15022](https://arxiv.org/abs/2308.15022))：用递归摘要维护长期记忆，对应本任务的“状态字段压缩”。
- **SCORE: Story Coherence and Retrieval Enhancement** ([arXiv:2503.23512](https://arxiv.org/abs/2503.23512))：通过 episode-level summaries + key item tracking + RAG 维持叙事一致性，对应本任务的“分层摘要 + 设定追踪”。
- **ComoRAG: Cognitive-Inspired Memory-Organized RAG** ([arXiv:2508.10419](https://arxiv.org/abs/2508.10419))：动态 memory workspace + 迭代检索，对应本任务的“ContextManager 按体裁动态加载”。

共同启示：**长叙事一致性不能靠 brute-force context stuffing，要靠分层摘要、动态内存、按体裁调整保留策略**。

---

## 设计原则

1. **共享引擎，参数化配置**：LangGraph、Agent、Repository、Settlement 核心框架不动。
2. **B 为主，C 为补充**：主要用 per-genre 配置（B），只在必要时加体裁插件钩子（C），如 xuanhuan 的寿命读数解析。
3. **默认保持 sci-fi 行为**：提取常量时，默认值保持当前 sci-fi 验证通过的数值，避免退化。
4. **分体裁标定，不追求统一 Ch250**：每套体裁有自己的目标窗口和验收标准。

---

## 四层体裁复杂度

| 层级 | 体裁 | 风险 | 目标窗口 | 主要工作 |
|---|---|---|---|---|
| A 轻量适配 | urban、post_apocalyptic、mystery_noir | 低 | Ch20-Ch30 | genre_rules + 轻微 budget 调参 |
| B 中度适配 | urban_fantasy、wuxia、灵异、新怪谈 | 中 | Ch15-Ch30 | + telemetry 别名 + 状态压缩 + 伏笔蒸发 |
| C 重度适配 | xuanhuan、穿越/系统流 | 高 | Ch20-Ch50 | + 深度状态摘要 + 独立门禁阈值 + 长周期伏笔管理 |
| D 不同产品 | literary | — | Ch3-Ch5 | 换 `literary` 模式，目标不是 250 章连载 |

---

## 子任务拆分

### 173a: 现状审计与常量提取

**目标**：把 context_manager、setting_evaporator、continuity_auditor、settlement_extractor 中所有 sci-fi 标定的硬编码常量找出来，提取到 `GenreRuntimeProfile`。

**涉及文件**：
- `src/songyan/agents/context_manager/__init__.py`
- `src/songyan/agents/context_manager/_budget.py`（如存在）
- `src/songyan/agents/settlement_extractor/_validate.py`
- `src/songyan/agents/setting_evaporator.py`
- `src/songyan/agents/continuity_auditor.py`
- `src/songyan/models/project_template.py`
- 新建 `src/songyan/models/genre_runtime_profile.py`

**输出**：
- `GenreRuntimeProfile` Pydantic 模型，字段至少覆盖：
  - `context_budget_config`: 各分区比例、emergency 阈值、halt 阈值
  - `state_compression_config`: 各字段摘要阈值、摘要策略
  - `foreshadowing_config`: resolve_confidence 阈值、长周期 archive 窗口、逾期降级策略
  - `telemetry_config`: 体裁 telemetry 属性别名列表
  - `revision_config`: 字数偏差容忍度、动态 safe-best 阈值
- `ProjectTemplate` 支持携带 `runtime_profile` 字段。
- 默认 profile 与当前 sci-fi 行为完全一致。

**验证**：
- 单元测试：`tests/models/test_genre_runtime_profile.py`
- scifi Ch1-Ch10 回归：`python scripts/run_173_short_window.py --templates scifi --end 10`

---

### 173b: xuanhuan 运行时配置

**目标**：为 xuanhuan 定义第一版 `GenreRuntimeProfile`，解决 Ch8 硬门禁暂停问题。

**关键参数（初稿，需实验标定）**：

```yaml
context_budget:
  character_states_ratio: 0.30      # 保持
  recent_plot_ratio: 0.15           # 从 0.20 下调，给 foreshadowing/soft_refs 腾空间
  foreshadowing_ratio: 0.08         # 从 0.10 下调
  soft_references_ratio: 0.12       # 保持
  hard_constraints_ratio: 0.35      # 上浮，genre_rules 更长
  emergency_halt_threshold: 1.5     # 从 1.3 上调（或按体裁独立）
  
state_compression:
  physical_state_threshold: 80      # 超过 80 token 自动摘要
  knowledge_threshold: 100          # 超过 100 token 自动摘要
  emotional_state_dedup: true       # 去重合并相近情绪词
  
foreshadowing:
  resolve_confidence_threshold: 0.7 # 提高 archive 门槛
  long_range_archive_window: 15     # expected_resolve > current + 15 时 archive
  overdue_demote: true              # 逾期伏笔降级，不常驻 context
  
telemetry_aliases:
  - ["lifespan", "remaining_lifespan_days", "寿元", "余寿", "剩余寿命", "寿命"]
  - ["cultivation_level", "修为", "境界", "炼气", "筑基"]
  - ["time_limit_days", "倒计时", "时限", "期限"]
```

**涉及文件**：
- `project_templates/xuanhuan/template.yaml`
- 新建 `project_templates/xuanhuan/runtime_profile.yaml`
- `src/songyan/project_templates/loader.py`：加载 runtime profile

**验证**：
- xuanhuan `--end 15` 不触发硬门禁
- ContextEmergency 频率下降或稳定在可接受范围
- 连续性审计 mismatch 不随章节线性恶化

---

### 173c: 状态字段自动压缩

**目标**：实现 physical_state / knowledge_* / emotional_state 的自动摘要，context 中只加载摘要，DB 保留原文。

**策略**：
- **physical_state**：提取“部位+状态+变化”三元组，如“左臂黑色纹路蔓延至锁骨，金色纹路反噬”→“左臂暗纹失控，金色力量反噬”。
- **knowledge_of_***：提取关键事实列表，去掉场景描写。
- **emotional_state**：情绪词去重合并，限制为最多 3-4 个核心情绪。

**涉及文件**：
- 新建 `src/songyan/agents/state_compressor.py`
- 修改 `src/songyan/agents/context_manager/__init__.py`：加载状态时先压缩
- 修改 `src/songyan/db/repository/character_state_repository.py`（如需要）：提供摘要读取接口

**验证**：
- 单元测试：`tests/test_state_compressor.py`
- xuanhuan `--end 10` 验证 context 中 character_states token 下降

---

### 173d: 伏笔蒸发策略调参

**目标**：让 foreshadowing 的 archive/evaporation 可配置，减少逾期伏笔常驻 context。

**策略**：
- 按体裁配置 `resolve_confidence` 阈值。
- 对 `expected_resolve_chapter` 远期的伏笔直接 archive。
- 对逾期伏笔降低 context 权重，仅在相关章节召回。

**涉及文件**：
- `src/songyan/agents/setting_evaporator.py` 或相关 foreshadowing 蒸发逻辑
- `src/songyan/models/genre_runtime_profile.py`

**验证**：
- 单元测试：`tests/test_foreshadowing_evaporation.py`
- xuanhuan `--end 15` 中 foreshadowing token 占比下降

---

### 173e: 体裁 telemetry 注册表

**目标**：把 `_validate.py` 中硬编码的 telemetry 关键词/别名改为按体裁配置。

**涉及文件**：
- `src/songyan/agents/settlement_extractor/_validate.py`
- 新建 `src/songyan/genres/telemetry_registry.py`
- 各 `genres/*.json` 增加 `telemetry_aliases` 字段（或新建 `project_templates/{genre}/telemetry.yaml`）

**验证**：
- 单元测试：`tests/test_telemetry_registry.py`
- xuanhuan + wuxia Ch1-Ch5 settlement 不报错

---

### 173f: 中度/轻量体裁配置

**目标**：为 wuxia、urban_fantasy、urban、mystery_noir、post_apocalyptic 定义初始 runtime profile。

**优先级**：
1. wuxia（和 xuanhuan 最接近，验证中度配置模板是否可复用）
2. urban_fantasy（异能/魔力 telemetry）
3. urban / mystery_noir / post_apocalyptic（轻量，验证默认参数是否足够）

**涉及文件**：
- `project_templates/{genre}/template.yaml` 或 `project_templates/{genre}/runtime_profile.yaml`

**验证**：
- 各体裁 `--end 15`（中度）或 `--end 10`（轻量）无硬门禁暂停

---

### 173g: 验证脚本与回归

**目标**：更新 `run_173_short_window.py`，支持按体裁 profile 验证；完成 sci-fi 回归。

**涉及文件**：
- `scripts/run_173_short_window.py`
- 新建 `scripts/run_173_genre_sweep.py`：批量跑多体裁目标窗口

**验证**：
- scifi `--end 50` 无退化（Ch1-Ch50 全部 accept，ContextEmergency 频率与基线一致）
- xuanhuan `--end 20`（或 Ch15 起）
- wuxia / urban_fantasy `--end 15`

---

## 与 V5/V6 sci-fi 经验的继承

| V5/V6 已验证的能力 | 本任务如何复用 |
|---|---|
| Context Diet 2.0 硬约束 + 分区预算框架 | 保持，但把比例/阈值变成可配置 |
| `setting_evaporator` + `human_marks` 蒸发机制 | 保持，调参即可 |
| `ContinuityAuditor` + `mandatory_references` 闭环 | 保持，压缩后的状态仍要参与审计 |
| safe-best 动态阈值（Ch1-20/21-50/51+） | 把阈值写入 `revision_config`，按体裁可配 |
| `--gate-mode enforce` 与硬门禁框架 | 把 `emergency_halt_threshold` 等阈值写入 profile |

**唯一需要修正的认知**：之前把 sci-fi 的最优参数当成了“全局默认”，现在要把它降级为“sci-fi profile 的默认值”。

---

## 验收判定

### P0（必须）
- [ ] `GenreRuntimeProfile` 模型落地，能被 `ProjectTemplate` 加载。
- [ ] scifi `--end 50` 回归：150/150 accept 等价（无退化）。
- [ ] xuanhuan `--end 15` 不再触发 `context_emergency_budget_ratio_halt`。

### P1
- [ ] xuanhuan `--end 20` 通过。
- [ ] wuxia / urban_fantasy `--end 15` 通过。
- [ ] 状态压缩单元测试覆盖 physical_state / knowledge / emotional_state。

### P2
- [ ] urban / mystery_noir / post_apocalyptic `--end 10` 通过。
- [ ] 体裁 telemetry 注册表覆盖 xuanhuan + wuxia + urban_fantasy。

---

## 风险与依赖

1. **API 成本**：xuanhuan Ch20 验证需要多次 LLM 调用，建议用保留数据库的脚本复跑，避免重复创建项目。
2. **状态压缩可能损失细节**：需要保证压缩后的摘要仍能满足 `ContinuityAuditor` 的校验需求。
3. **默认配置变更风险**：提取常量时必须保持 sci-fi 默认值，否则 V5/V6 的 Ch150 证据会失效。
4. **多 worktree 状态**：当前在 `task/173-project-templates` 分支，完成后需合回 main。

---

## 下一步

1. review 本任务拆分（当前文档）。
2. 确认 173a 的 `GenreRuntimeProfile` 字段集合。
3. 开工 173a：先审计硬编码常量，再提取模型。
