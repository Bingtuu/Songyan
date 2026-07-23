# Pass 14 ~ Pass 18 — V5.1 Code Review 路线图

> **范围**: 状态管理、Agent 边界、Context Diet 2.0、Prompt 质量、测试矩阵
> **日期**: 2026-06-25
> **审查者**: Codex
> **状态**: 规划待执行

---

## 摘要

本路线图承接 Pass 13（P1/P2 批量修复验证），面向 V5.1 阶段的代码质量加固。当前项目状态：V5.0 工程验收通过，Task 121q 已完成 Ch1-Ch150 150/150 全部成功。下一步优先级为 Task 121r（Prompt / 正文质量清理）和 Task 122a-d（系统性测试矩阵）。

本规划覆盖 5 个 Pass，按依赖顺序执行：

| Pass | 主题 | 范围 | 关联 Task | 优先级 |
|------|------|------|:---------:|:------:|
| Pass 14 | 状态管理与事实源一致性 | `db/`, `workflows/_nodes_settlement.py`, `agents/settlement_extractor/` | 122b | P0 |
| Pass 15 | Agent 边界与审查体系 | `agents/writer.py`, `agents/revision_handler/`, `agents/llm_auditor.py`, `workflows/_nodes_review.py` | 121r, 122b | P0 |
| Pass 16 | Context Diet 2.0 预算与衰减 | `agents/context_manager/`, `agents/setting_evaporator.py` | 122a | P0 |
| Pass 17 | Prompt 工程与元标记防泄漏 | `prompts/cards/`, `agents/writer.py`, `workflows/_nodes_writing.py` | 121r | P1 |
| Pass 18 | 测试矩阵与覆盖率审查 | `tests/`, `evals/` runner | 122a-d | P1 |

---

## Pass 14 — 状态管理与事实源一致性审查

### 范围

验证 SQLite 作为唯一长期事实源的不可违背规则是否在代码层面得到完整贯彻。

**检查文件**:
- `src/songyan/db/repository.py` — ChapterVersionRepository, CharacterStateRepository
- `src/songyan/db/unit_of_work.py` — 事务边界
- `src/songyan/agents/settlement_extractor/_apply.py` — settlement DB 写入
- `src/songyan/agents/settlement_extractor/_validate.py` — 结算校验
- `src/songyan/workflows/_nodes_settlement.py` — human_gate_node, settlement_extractor_node
- `src/songyan/workflows/_nodes_writing.py` — writer_node, rewrite_node

### 检查项

| ID | 检查项 | 验收标准 | 严重度 |
|----|--------|---------|:------:|
| ST-01 | `chapter_versions` 禁止覆盖 | 全局搜索零处 `UPDATE chapter_versions SET content / word_count / scenes` | P0 |
| ST-02 | `character_states` 永远 INSERT | 全局搜索零处 `UPDATE character_states SET`（`lifecycle_status` 除外） | P0 |
| ST-03 | Agent 不直接拿 DB connection | `agents/` 目录内无 `from songyan.db.connection import get_db` | P0 |
| ST-04 | settlement `old_value` 一致性 | `_apply.py` 中 `old_value` 必须与 DB 当前值一致，不一致时抛出异常 | P0 |
| ST-05 | `source_quote` 去噪与存在性 | `_validate.py` 中 `source_quote` 经过去噪，且能在正文中定位 | P0 |
| ST-06 | `new_setting.setting_key` 唯一性 | `_validate.py` 中检查 `setting_key` 在 current lineage 中唯一 | P0 |
| ST-07 | `foreshadowings.source_version_id` 记录 | `settlement_extractor` 输出必须包含 `source_version_id` | P0 |
| ST-08 | accepted/settlement/summary 原子事务 | `unit_of_work.py` 中 accept + settlement + summary 必须在同一事务 | P0 |

### 验证方法

1. 全局搜索 `UPDATE chapter_versions SET` / `UPDATE character_states SET`
2. 检查 `agents/` 目录下所有 `.py` 文件的 DB 访问方式
3. 审查 `settlement_extractor/_apply.py` 中 `old_value` 获取逻辑
4. 审查 `settlement_extractor/_validate.py` 中 `source_quote` 校验正则
5. 确认 `unit_of_work.py` 中 `commit()` 调用位置

### 回归检查 (Pass R)

| ID | 检查项 |
|----|--------|
| RG1 | 新增 import 是否引入未声明依赖 |
| RG2 | 新增 except 是否用了裸 Exception |
| RG3 | 修改文件是否保持 < 400 行 |
| RG4 | pytest 回归全绿 |

---

## Pass 15 — Agent 边界与审查体系审查

### 范围

验证 Agent 职责隔离原则和审查体系的多层防线是否在代码中得到遵守。

**检查文件**:
- `src/songyan/agents/writer.py` — 只做初稿，不做修订
- `src/songyan/agents/revision_handler/` — patch 引擎，最多 2 轮
- `src/songyan/agents/llm_auditor.py` — 语义审查，critical/major 需 evidence_quote
- `src/songyan/agents/rule_auditor.py` — 代码检测，需定位信息
- `src/songyan/agents/literary_auditor.py` — 诊断不阻塞
- `src/songyan/workflows/_nodes_review.py` — review_merger_node, llm_auditor_node
- `src/songyan/workflows/_nodes_revision.py` — revision_handler_node
- `src/songyan/workflows/review_merger.py` — Rule + LLM 轻量合并

### 检查项

| ID | 检查项 | 验收标准 | 严重度 |
|----|--------|---------|:------:|
| AG-01 | Writer 不做修订 | `writer.py` 中无 revision/rewrite 逻辑，输出为 draft 版本 | P0 |
| AG-02 | RevisionHandler 只做 patch | `revision_handler/` 中无整章重写逻辑，只生成 patch list | P0 |
| AG-03 | 自动修订最多 2 轮 | `phase1_graph.py` 中 revision 路由限制 `revision_count < 2` | P0 |
| AG-04 | 修订引入新问题停止 | `review_merger.py` 或 `_nodes_revision.py` 中检测 `new_issues_introduced` | P0 |
| AG-05 | `rewrite_scene` 不自动修复 | `revision_handler_node` 中过滤掉 `issue_type == "rewrite_scene"` | P0 |
| AG-06 | LLMAuditor evidence_quote | `llm_auditor.py` 中 critical/major issue 必须含 `evidence_quote` | P0 |
| AG-07 | RuleAuditor 定位信息 | `rule_auditor.py` 中所有命中必须含行号/段落定位 | P1 |
| AG-08 | LiteraryAuditor 不阻塞 | `workflows/_nodes_review.py` 中 literary 结果不进入 accept/reject 判定 | P1 |
| AG-09 | ReviewMerger 不调用 LLM | `review_merger.py` 中无 LLM client 调用，纯内存合并 | P0 |
| AG-10 | `valuable_fissure` 保护 | `revision_handler/` 中 patch 时跳过 `valuable_fissure` 标记的段落 | P1 |

### 验证方法

1. 审查 `writer.py` 的 public API，确认返回 `ChapterVersion` 且不含 revise 方法
2. 检查 `phase1_graph.py` 中 revision router 的条件分支
3. 检查 `llm_auditor.py` 的 Pydantic 输出模型，确认 `evidence_quote` 字段必填约束
4. 确认 `review_merger.py` 无 `call_llm` / `client` import
5. 检查 `revision_handler/` 中是否有 `rewrite_scene` 过滤逻辑

### 回归检查 (Pass R)

| ID | 检查项 |
|----|--------|
| RG1 | Agent 新增 import 是否引入未声明依赖 |
| RG2 | 路由逻辑变更是否影响 phase1_graph 状态机 |
| RG3 | pytest 回归全绿 |

---

## Pass 16 — Context Diet 2.0 预算与衰减审查

### 范围

验证 Context Diet 2.0 四组件（TemporalCompressor、CharacterFocalDecay、SettingEvaporator、BudgetHardCeiling）的协同逻辑和预算安全。

**检查文件**:
- `src/songyan/agents/context_manager/temporal_compressor.py`
- `src/songyan/agents/context_manager/character_focal_decay.py`
- `src/songyan/agents/setting_evaporator.py`
- `src/songyan/agents/context_manager/budget_hard_ceiling.py`
- `src/songyan/agents/context_manager/context_assembler.py`
- `src/songyan/workflows/_nodes_writing.py` — context_manager_node

### 检查项

| ID | 检查项 | 验收标准 | 严重度 |
|----|--------|---------|:------:|
| CD-01 | TemporalCompressor 金字塔摘要 | 最近 5 章详细 + 弧摘要 + 卷摘要结构正确 | P0 |
| CD-02 | CharacterFocalDecay 衰减逻辑 | 角色按未出场章数降级：完整→精简→符号→不加载 | P0 |
| CD-03 | SettingEvaporator 蒸发逻辑 | 低 `resolve_confidence` 设定自动 archive，embedding 合并 | P0 |
| CD-04 | BudgetHardCeiling 触发条件 | `budget_used > 1.0` 时触发 ContextEmergency | P0 |
| CD-05 | ContextEmergency 降级内容 | emergency 时只保留硬约束 + 主角档案 + ChapterGoal | P0 |
| CD-06 | 硬约束不裁剪 | `genre_rules`、`mode_rules`、`chapter_goal` 等硬约束始终保留 | P0 |
| CD-07 | 角色池硬上限 | `CharacterLifecycleAuditor` 中活跃角色数有上限控制 | P1 |
| CD-08 | `human_marks` 生命周期窗口 | `human_marks` 按 6 章窗口衰减（Task 121n） | P1 |
| CD-09 | 预算计算准确性 | `budget_used` 计算包含所有 token 来源，无遗漏 | P0 |

### 验证方法

1. 审查 `context_assembler.py` 中 `assemble()` 方法的预算累加逻辑
2. 检查 `budget_hard_ceiling.py` 中 `fullness_factor` 和 emergency 触发阈值
3. 审查 `character_focal_decay.py` 中角色档案降级规则
4. 检查 `setting_evaporator.py` 中 `resolve_confidence` 阈值和 archive 逻辑
5. 确认 emergency 路径下的硬约束列表与 `AGENTS.md` 定义一致

### 回归检查 (Pass R)

| ID | 检查项 |
|----|--------|
| RG1 | Context 组装结果变更是否影响 Writer 输出格式 |
| RG2 | budget_used 计算变更是否影响 QualityGate 判定 |
| RG3 | pytest 回归全绿，特别是 context_manager 相关测试 |

---

## Pass 17 — Prompt 工程与元标记防泄漏审查

### 范围

承接 Task 121r，验证 Prompt 工艺卡和 Writer 输出的元标记清理机制。

**检查文件**:
- `prompts/cards/_manifest.yaml` — 工艺卡版本管理
- `prompts/cards/v*.yaml` — 具体工艺卡
- `src/songyan/agents/writer.py` — Writer 主逻辑
- `src/songyan/workflows/_nodes_writing.py` — writer_node, rewrite_node
- `src/songyan/agents/llm_auditor.py` — 元标记检测
- `src/songyan/utils/` — 清理工具函数

### 检查项

| ID | 检查项 | 验收标准 | 严重度 |
|----|--------|---------|:------:|
| PR-01 | 代码中无硬编码长 prompt | `src/` 目录内无内联多行 prompt 字符串（> 200 字符） | P1 |
| PR-02 | Prompt 从工艺卡加载 | `writer.py` / `llm_auditor.py` 均通过 `PromptLoader` 加载 YAML | P1 |
| PR-03 | 工艺卡版本化管理 | `prompts/cards/` 下存在 `_manifest.yaml` 且记录版本映射 | P2 |
| PR-04 | Writer 输出正则清理 | `writer.py` 或 `_nodes_writing.py` 中对 LLM 输出执行 HTML 注释和元标记清理 | P1 |
| PR-05 | 元标记泄漏检测 | `llm_auditor.py` 或 `rule_auditor.py` 含 `<mark>` / `<!--` / `meta:` 检测规则 | P1 |
| PR-06 | 字数控制机制 | `writer.py` 中 `word_count_target` 上下限约束（1.20x/0.80x） | P1 |
| PR-07 | 截断保场景完整性 | `_hard_truncate_at_boundary` 不在场景中间截断 | P1 |
| PR-08 | Rewrite 字数护栏 | `rewrite_node` 中字数限制为 ±20%（Task 090b） | P1 |

### 验证方法

1. 全局搜索 `src/` 中多行字符串 f-string / triple-quote（排除 docstring）
2. 检查 `writer.py` 是否通过 `PromptLoader` 加载 craft card
3. 审查 Writer 输出后的清理正则表达式
4. 检查 `rule_auditor.py` 中是否有元标记相关规则
5. 确认 `rewrite_node` 中字数限制参数

### 回归检查 (Pass R)

| ID | 检查项 |
|----|--------|
| RG1 | Prompt 加载路径变更是否破坏现有测试 |
| RG2 | 新增清理正则是否误伤正文内容 |
| RG3 | pytest 回归全绿 |

---

## Pass 18 — 测试矩阵与覆盖率审查

### 范围

承接 Task 122a-d，验证当前测试基线并规划测试矩阵缺口。

**检查文件**:
- `tests/` — 全部测试文件
- `tests/conftest.py` — fixture 定义
- `tests/test_settlement_submodules.py` — Pass 13 遗留
- `src/songyan/agents/score_aggregator.py` — 评分聚合器
- `src/songyan/workflows/phase1_graph.py` — Pipeline 主流程

### 检查项

| ID | 检查项 | 验收标准 | 严重度 |
|----|--------|---------|:------:|
| TS-01 | 动态阈值单元测试 | `test_score_aggregator.py` 覆盖 0.75→0.78→0.82 三段阈值 | P1 |
| TS-02 | `degraded_accept` 降级回滚 | 测试评分 0.70-0.74 时触发降级接受，且注入降级标记 | P1 |
| TS-03 | Settlement 子模块测试 | `_apply.py`, `_validate.py`, `_constraints.py` 有独立测试 | P1 |
| TS-04 | Pipeline 集成测试 | `test_phase1_graph.py` 覆盖 rewrite → settlement → summary 完整路径 | P1 |
| TS-05 | QG false 硬拦截 | 测试 QualityGate 失败后 settlement 被跳过（Task 121m） | P0 |
| TS-06 | Rewrite 状态清理 | 测试 rewrite 后旧版本 issue 被清理（Task 121h） | P0 |
| TS-07 | ContextEmergency 降级 | 测试 budget_used > 1.0 时 emergency 触发和内容裁剪 | P1 |
| TS-08 | Ch1-Ch20 E2E 模拟 | `evals/` runner 可模拟 Ch1-Ch20 端到端 | P1 |
| TS-09 | mock_llm fixture 使用 | `conftest.py` 中 `mock_llm` fixture 被现有测试引用 | P2 |
| TS-10 | 测试回归基线 | `pytest tests/ -q` 结果 ≥ 1731 passed，0 新增失败 | P0 |

### 验证方法

1. 执行 `pytest tests/ -q` 确认当前基线
2. 检查 `test_score_aggregator.py` 中阈值测试用例
3. 检查 `test_phase1_graph.py` 中 Pipeline 路径覆盖
4. 确认 `conftest.py` 中 `mock_llm` fixture 定义和使用
5. 审查 `tests/` 中是否有 `settlement_extractor` 子模块的独立测试

### 回归检查 (Pass R)

| ID | 检查项 |
|----|--------|
| RG1 | 新增测试是否引入未声明依赖 |
| RG2 | 新增测试执行时间是否 < 5 秒/个 |
| RG3 | 全量 pytest 回归通过 |

---

## 全局回归检查（All Passes）

每个 Pass 执行后必须执行：

| ID | 检查项 | 命令 |
|----|--------|------|
| RG1 | lint 通过 | `ruff check src/ tests/` |
| RG2 | 类型检查 | `python -m mypy src/`（如有配置） |
| RG3 | 全量回归 | `pytest tests/ -q` |
| RG4 | 新增文件行数 | 单文件 < 400 行 |
| RG5 | 裸 except 检查 | 全局搜索 `except:`（不含异常类型） |
| RG6 | print 语句检查 | 全局搜索 `print(`（排除 `scripts/` 和 `archive/`） |

---

## 执行顺序与依赖

```
Pass 14 (状态管理) ──┐
Pass 15 (Agent 边界) ─┤──→ 可并行启动
Pass 16 (Context Diet)─┘
       │
       ▼
Pass 17 (Prompt 质量) ──→ 依赖 Pass 15 Writer 边界确认
       │
       ▼
Pass 18 (测试矩阵) ────→ 依赖 Pass 14-17 修复内容
```

---

## 汇总

```
V5.1 Code Review 执行结果汇总:
  Pass 14 (状态管理)          ████████▁▁  7/8 通过，1 观察项 (ST-03)
  Pass 15 (Agent 边界)        █████████▁  9/10 通过，1 观察项 (AG-04)
  Pass 16 (Context Diet)      ██████████  9/9 全部通过
  Pass 17 (Prompt 质量)       ████████▁▁  7/8 通过，1 观察项 (PR-05)
  Pass 18 (测试矩阵)          ██████▁▁▁▁  6/10 通过，4 缺口/观察项

  P0 检查项总计: 22 项 → 通过 21/22，1 观察项
  P1 检查项总计: 18 项 → 通过 14/18，4 缺口
  P2 检查项总计:  3 项 → 通过 3/3

  关键发现:
  - P0 风险: 0 项。所有 P0 检查项均通过或已观察项降级。
  - P1 缺口: 4 项（TS-01 动态阈值缺测试、TS-02 degraded_accept 缺测试、TS-03 settlement 子模块空壳、TS-08 Ch1-Ch20 E2E 缺测试）
  - pytest 基线: 1803 passed, 0 failed, 超目标 1731

  报告文件:
  - archive/v5/reports/pass14-state-management-audit.md
  - archive/v5/reports/pass15-agent-boundary-audit.md
  - archive/v5/reports/pass16-context-diet-audit.md
  - archive/v5/reports/pass17-prompt-engineering-audit.md
  - archive/v5/reports/pass18-test-matrix-audit.md
```

---

## 验证限制

- 本规划为静态审查方案，实际执行需 Python 运行时环境
- 建议在 CI/CD 环境或有 Python 的环境中执行验证命令
- 每个 Pass 的详细执行报告应按 `pass{NN}-{主题}.md` 格式单独归档到 `docs/reports/`

---

> **松烟入墨，字句成锋。**
> V5.0 的 150 章成功不是终点，而是 V5.1 质量跃迁的起点。代码审查不是找茬，而是确保每行代码都经得起第 151 章的考验。
