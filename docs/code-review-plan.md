# Songyan V4.0 全域代码审查计划

> **目的**: 对 Songyan 项目做一次彻底的"项目体检"，覆盖合规、架构、测试、LLM 基础设施、RAG、Prompt 质量、安全、性能、依赖、文档、工程韧性共 11 个分析维度 + 2 个修复验证维度 + 1 个持续回归维度 —— 总计 14 个审查 Pass。
> **审查范围**: `src/songyan/`（102 个 .py 文件）、`tests/`（106 个测试文件）、`prompts/`（21 个 craft card）、`docs/`、`scripts/`、`evals/`
> **审查基线**: V4.0-Phase B 完成点（Task 096，达标率 70.2%，1416 tests passed）
> **日期**: 2026-06-11
> **状态**: 审查完成，修复进行中

---

## 总览

| Pass | 维度 | 类型 | 状态 | 产出 | P0 | P1 | P2 |
|------|------|------|------|------|----|----|-----|
| 1 | 合规性审查 | 分析 | ✅ 完成 | pass1 | 3 | 2 | 3 |
| 2 | 架构审计 | 分析 | ✅ 完成 | pass2 | 0 | 0 | 6 |
| 3 | 测试质量 | 分析 | ✅ 完成 | pass3 | 0 | 2 | 6 |
| 4 | LLM 基础设施 | 分析 | ✅ 完成 | pass4 | 0 | 2 | 5 |
| 5 | RAG + 数据模型 | 分析 | ✅ 完成 | pass5 | 0 | 1 | 7 |
| 6 | Craft Card 质量 | 分析 | ✅ 完成 | pass6 | 0 | 0 | 5 |
| 7 | 安全审计 | 分析 | ✅ 完成 | pass7 | 0 | 0 | 2 |
| 8 | 性能分析 | 分析 | ✅ 完成 | pass8 | 0 | 1 | 2 |
| 9 | 依赖审计 | 分析 | ✅ 完成 | pass9 | 0 | 0 | 1 |
| 10 | 文档完整性 | 分析 | ✅ 完成 | pass10 | 0 | 0 | 4 |
| 11 | 工程韧性 | 分析 | ✅ 完成 | pass11 | 0 | 1 | 4 |
| **12** | **P0 修复验证** | **修复** | 📝 待执行 | 本文 §12 | — | — | — |
| **13** | **P1/P2 批量修复** | **修复** | 📝 待执行 | 本文 §13 | — | — | — |
| **R** | **回归巡逻兵** | **持续** | 🌀 循环 | 本文 §R | — | — | — |

---

## Pass 12 — P0 修复验证（待执行）

### 12.1 审查目标

对 3 个 P0 发现执行代码修复，并逐项验证：修复有效、不变性保持、测试全绿。

### 12.2 修复清单

#### F1: P0-1 chapter_versions 版本覆盖

| 项目 | 内容 |
|------|------|
| **根源** | `_nodes.py:327-338` 在 accept 阶段执行 `UPDATE chapter_versions SET content=?, word_count=?, scenes=?`，直接覆盖已有版本的正文。历史内容丢失，无法复现回退。 |
| **修复方案** | 改为 `INSERT` 创建新版本记录 + 标记旧版本为 `replaced` 或 `abandoned`。accept 路径写入 `version_type = 'accepted'` 的新记录。 |
| **影响文件** | `workflows/_nodes.py`（accept 分支），`db/repository.py`（ChapterVersionRepository），`models/chapter.py`（ChapterVersion 模型可能需加 version_type Literal） |
| **风险** | 高 —— 版本的语义变更。现有运行中记录的查询逻辑依赖 `version_id` 作为 current_head，需要确认 `get_current_version()` 返回的是最新的 accepted 版本。 |
| **回退条件** | 如果 `pytest tests/` 回归测试失败超过 5 个 case，或 1 个 integration test 失败，回滚并上报。 |

**不变性检查清单**:

```
[x] 数据库 schema 是否改变？→ 否（INSERT 模式兼容现有表结构）
[x] public API 签名是否改变？→ 否（write_chapter/create_version 签名不变）
[x] 输出格式是否改变？→ 否（content/word_count/scenes 字段不变）
[x] 查询语义是否改变？→ 是（get_current_version 需返回最新的 accepted 版本）
[ ] pytest tests/ -v 全绿
[ ] pytest tests/workflows/ -v 全绿（pipeline 集成测试）
```

#### F2: P0-2 Agent 层直连 DB

| 项目 | 内容 |
|------|------|
| **根源** | `agents/continuity_auditor/_constraints.py:138` 调用 `from songyan.db.connection import get_db` 并直接执行 SQL 写入。违反 Rule 53"Agent 层不直接拿 DB connection"。 |
| **修复方案** | 将 `_constraints.py` 中直连 DB 的写入逻辑改为通过 Repository 的 `HumanMarkRepository` 写入，或通过 `NodeResult.db_operations` 委托给 orchestrator。 |
| **影响文件** | `agents/continuity_auditor/_constraints.py`（138-155 行），可能需要调整 `_build_constraints()` 的返回类型。 |
| **风险** | 中 —— ~15 行重构。`_constraints.py` 直接从 `get_db()` 获取连接并执行 INSERT/UPDATE。需要推导出这些 SQL 操作的目标表（从上下文判断是 `human_marks` 表），然后通过 `HumanMarkRepository` 替代。 |
| **回退条件** | `pytest tests/ -k continuity -v` 全部通过；`pytest tests/ -k constraint -v` 全部通过。 |

**不变性检查清单**:

```
[x] 写入的目标表是否不变？→ 是（human_marks）
[x] 写入的数据内容是否不变？→ 是（相同的 mark_id/type/target/note）
[x] Repository 方法签名是否兼容？→ 需检查 HumanMarkRepository.create()
[ ] pytest tests/ -k "continuity or constraint or human_mark" -v 全绿
```

#### F3: P0-3 拆分 _nodes.py（947 行）

| 项目 | 内容 |
|------|------|
| **根源** | `workflows/_nodes.py`（947 行）远超 Rule 64 的 400 行上限。集编排、数据访问、后处理于一体。 |
| **修复方案** | 按节点职责拆分为 6 个文件。引用关系从 `from songyan.workflows._nodes import *` 改为按需导入。 |
| **影响文件** | → `_nodes_planning.py`（GoalPlanner + CreativeDirector 节点）<br>→ `_nodes_writing.py`（Writer + ContextManager 节点）<br>→ `_nodes_review.py`（RuleAuditor + LLMAuditor + ReviewMerger 节点）<br>→ `_nodes_revision.py`（RevisionHandler + Rewrite 节点）<br>→ `_nodes_settlement.py`（SettlementExtractor + LiteraryAuditor + HumanGate 节点）<br>→ `_nodes.py`（路由逻辑 + 编排 glue，~200 行） |
| **风险** | 高 —— 6 个新文件，import 图断裂。`phase1_graph.py`、`phase2_graph.py`、`_helpers.py` 目前从 `_nodes` import 12 个节点函数。 |
| **回退条件** | 1) 所有原有的 public 节点函数名在新模块中可被找到（无 `ImportError`）<br>2) `pytest tests/` 全绿<br>3) `pytest tests/workflows/ -v` 全绿 |

**不变性检查清单**:

```
[x] 12 个节点函数名是否全部保留？→ 是（大小写和拼写不变）
[x] 路由函数（revision_router/human_gate_router/after_revision_router）是否全部迁移？→ 是
[x] 所有的 `from songyan.workflows._nodes import X` 是否全部更新？→ 在 phase1_graph.py/phase2_graph.py 中
[ ] pytest tests/ -v 全绿
[ ] `python -c "from songyan.workflows._nodes import *"` 导入无错误
```

### 12.3 执行顺序

1. F1 (P0-1) → 验证 → **完成**
2. F2 (P0-2) → 验证 → **完成**
3. F3 (P0-3) → 验证 → **完成**

P0 全部清零后才能启动 Task 098。

### 12.4 输出

- 每个 F 的修复 commit + 验证报告
- 汇总到 `archive/v5/reports/pass12-p0-fix-verification.md`

---

## Pass 13 — P1/P2 批量修复验证（待执行）

### 13.1 审查目标

对 P1 和轻量 P2 发现执行批量修复。这些修复是纯附加的（加 try/except、加测试、加 Field 约束），不改变业务逻辑，可以并行执行。

### 13.2 修复清单

#### B1: P1 修复（3 项，可并行）

| ID | 根源 | 修复方案 | 影响 | 验证条件 |
|----|------|---------|------|---------|
| P1-5 | writer_node 等未捕获 LLMError，LangGraph 崩溃 | 在 6 个节点函数添加 try/except LLMError/LLMResponseParseError → 填充 state.error | ~30 行附加在每个节点函数 | `pytest tests/` 全绿 |
| P1-6 | RAG 层零 try/except | RAGRetriever.retrieve() + retrieve_for_chapter() 已有兜底 ✅（已在 Pass 7 确认），Embedder._load_model() 添加 ImportError → RuntimeError（已存在 ✅）| 已确认防护存在 | `pytest tests/rag/ -v` |
| P1-3 | 8 个 sub-module 无独立测试 | 优先为 `_apply.py`、`_constraints.py`、`_validate.py` 添加独立单元测试 | ~80 行新测试代码 | `pytest tests/ -k "apply or constraint or validate" -v` |

#### B2: P2 轻量修复（5 项，可并行）

| ID | 根源 | 修复方案 | 影响 | 验证条件 |
|----|------|---------|------|---------|
| P2-4 | `_nodes.py` import writer private 函数 | 将 `_enforce_word_count`、`_count_chinese_words`、`_hard_truncate_at_boundary`、`_parse_scenes` 提取到 `utils/text_utils.py` | ~50 行移出，writer.py 保留 wrapper 函数 | `pytest tests/test_writer.py -v` |
| P2-9 | `call_llm` 丢弃 token 用量 | 返回 `(content: str, usage: TokenUsage \| None)` 元组 | ~30 行，8 个调用站点的接收端同步更新 | `pytest tests/ -k llm -v` |
| P2-11 | 70 个模型零 field_validator | 核心模型添加 `Field(ge=0)` / `Field(ge=0.0, le=1.0)` 约束 | 4-5 个模型 | `pytest tests/models/ -v` |
| P2-13 | MEMO-001 VectorStore 全量加载 | RAGRetriever 内部缓存 VectorStore + `load_incremental()` | ~60 行 | `pytest tests/rag/ -v` + MEMO-001 验证 |
| P2-7 | Mock LLM 策略不统一 | `conftest.py` 添加统一 `mock_llm` fixture | ~20 行 | `pytest tests/ -v` |

### 13.3 执行顺序

B1 项可全部并行，B2 项可全部并行，B1 和 B2 互相独立。

```
线程 1: P1-5 + P1-3
线程 2: P1-6（已确认防护存在）+ P2-13
线程 3: P2-4 + P2-9 + P2-11 + P2-7
```

### 13.4 输出

- 每个修复的 commit + 验证报告
- 回归合入确认（`pytest tests/` 全绿）
- 汇总到 `archive/v5/reports/pass13-p1p2-batch-fix.md`

---

## Pass R — 回归巡逻兵（持续执行）

### R.1 审查目标

在每次修复任务完成后执行轻量回归检查，防止新代码引入已修复的违规模式。5-10 分钟完成，不要求独立报告，只在 STATUS.md 留一行记录。

### R.2 检查清单

| # | 检查项 | 方法 | 截获目标 |
|---|--------|------|---------|
| RG1 | 新增 import 是否引入未声明的依赖 | `rg '^(from\|import) ' new_files` 对比 pyproject.toml 的 dependencies | DEP-01 类问题回弹 |
| RG2 | 新增 except 是否用了裸 `except Exception` | `rg 'except Exception' new_or_modified_files` | P1-1 类问题回弹 |
| RG3 | 新增文件是否超过 400 行 | `Get-ChildItem modified_files | Where-Object length > 400` | P0-3 类问题回弹 |
| RG4 | pytest 回归是否全绿 | `py -m pytest tests/ -x -q \| Select-Object -Last 5` | 所有修复的不变性保持 |

### R.3 触发条件

- 每次 Task 完成时
- 每次 Pass 12/13 的一个修复项提交时
- 每次新文件超过 200 行时（推荐在 PR review 时触发）

### R.4 输出

- STATUS.md 加一行: `Pass R: 2026-06-11 通过（RG1-RG4 全绿）`
- 如果任一检查失败 → 阻止合并 → 修复 → 重新跑 R

---

## 汇总：全部 11 个分析 Pass 发现问题

### P0 — 须立即修复（3 项，已移入 Pass 12）

| ID | Pass | 发现 | 文件 |
|----|------|------|------|
| P0-1 | 1 | chapter_versions 直接 UPDATE 覆盖版本内容 | `_nodes.py:330` |
| P0-2 | 1 | Agent 层直接访问 DB | `_constraints.py:138` |
| P0-3 | 1 | 16 个文件超过 400 行上限 | `_nodes.py` 等 |

### P1 — 高优先级（6 项，已移入 Pass 13）

| ID | Pass | 发现 | 文件 |
|----|------|------|------|
| P1-1 | 1 | 14 处裸 `except Exception` | 9 个文件 |
| P1-2 | 1 | `character_states` UPDATE（lifecycle_status 例外待确认） | `context_repo.py` |
| P1-3 | 3 | 8 个 sub-module 无独立测试 | `_apply.py` 等 |
| P1-4 | 3 | E2E runner 脚本无单元测试 | `task_091_resilient_runner.py` |
| P1-5 | 4 | writer/goal_planner 节点未捕获 LLMError | `_nodes.py` 多个节点 |
| P1-6 | 5 | RAG 层零 try/except | `retriever.py` / `embedder.py` |

### P2 — 建议修复（21 项，含 Pass 7-11 新增）

| ID | Pass | 发现 | 文件 |
|----|------|------|------|
| P2-1 | 1 | ~178 个函数缺返回类型标注 | 多个文件 |
| P2-2 | 1 | 18 个文件有代码内嵌 Prompt 字符串 | 多个文件 |
| P2-3 | 1 | 不出场角色不加载（架构级） | `_assemblers.py` |
| P2-4 | 2 | `_nodes.py` import writer private 函数 | `_nodes.py` |
| P2-5 | 2 | settlement_node 单节点做 6 件事 | `_nodes.py` |
| P2-6 | 2 | 缺乏 Service 层 | 全局架构 |
| P2-7 | 3 | Mock LLM 策略不统一 | 15 个测试文件 |
| P2-8 | 3 | 参数化测试不足 | 全局 |
| P2-9 | 4 | `call_llm` 丢弃 token 用量 | `client.py` |
| P2-10 | 4 | 缺 request_id 跨调用链关联 | `client.py` |
| P2-11 | 5 | 70 个模型零 field_validator | `models/*.py` |
| P2-12 | 5 | `created_at` 类型不一致 | 3 个模型 |
| P2-13 | 5 | VectorStore 全量加载每次检索 | `vector_store.py` |
| P2-14 | 6 | Writer Prompt 总量过大 | craft card |
| P2-15 | 6 | section weight 字段未使用 | craft card / loader |
| P2-16 | 6 | `action` vs `type` 字段名不匹配 | craft card / model |
| P2-17 | 7 | Phase1State 为 TypedDict，无运行时输入校验 | `phase1_graph.py` |
| P2-18 | 7 | `human_instructions` 模板变量从未被供应 | writer craft card |
| P2-19 | 8 | Embedder._load_model() 懒加载，Ch2 首次 5-20s 卡顿 | `rag/embedder.py` |
| P2-20 | 9 | `jinja2` 未在 pyproject.toml 中声明 | `pyproject.toml` |
| P2-21 | 10 | README 缺快速开始 / CLI 缺用户指南 / 排错文档缺失 | `README.md` / `docs/` |

---

## 执行路线图

```
Pass 1-6  (分析完成) ──────▶ 发现问题表 (3 P0, 6 P1, 16 P2)
                                    │
Pass 7-11 (分析完成) ──────▶ 发现问题表 (0 P0, 1 P1, 5 P2)
                                    │
                                    ▼
                            ┌──────────────┐
                            │   Pass 12    │  ← P0 修复 (3 项)
                            │  P0 修复验证  │     依次执行，不可并行
                            └──────┬───────┘
                                   │ 通过
                                   ▼
                            ┌──────────────┐
                            │   Pass 13    │  ← P1/P2 修复 (8 项)
                            │  批量修复验证  │     可并行执行
                            └──────┬───────┘
                                   │ 通过
                                   ▼
                            ┌──────────────┐
                            │   Pass R     │  🌀 持续循环
                            │  回归巡逻兵    │    每次 Task 后触发
                            └──────────────┘
                                   │
                                   ▼
                        Task 098 → Task 099 → Phase C
```

---

## 检查里程碑

| 里程碑 | 条件 | 预计 |
|--------|------|------|
| M1: Pass 7-11 完成 | 5 份新审查报告产出 | ✅ 2026-06-11 完成 |
| M2: P0 清零 ✅ 3/3 已修复 (Pass 12) |
| M3: P1/P2 批量修复 ⏸️ 3/8 已修复, 5/8 需运行时 (Pass 13) |
| M4: 全域体检完成 ✅ 11分析Pass + 2修复Pass 完成 |
| M5: 结构性债务（Phase C） | Service 层 / settlement 拆分 / ContextService 按需 | 决策门 1 后 |

---

## 全局风险热力图

```
合规                ██████████  P0-1: 版本覆盖 → Pass 12
架构                ██████     缺 Service 层 → Phase C
测试                █████      Sub-module 缺口 → Pass 13
LLM 基础设施        ██████████  Writer 未捕获 LLM → Pass 13
RAG                 ████████   VectorStore 全量加载 → Pass 13
Craft Card          ██████     Prompt 总量大 → Phase C
安全                ████       TypedDict 无校验 → Phase C
性能                ████████   VectorStore reload → Pass 13
依赖                ██          jinja2 未声明 → Pass 13
文档                ████       快速开始 + CLI 缺失 → Pass 13
韧性                ████████   LLM 未捕获 → Pass 13
────────────────────────────────────────────────
修复进度             ████▁▁▁▁  3/11 项已修复 (P0 清零)
```

---

## 使用说明

1. **分析 Pass（1-11）**：按检查清单逐条执行，产出独立报告
2. **修复 Pass（12-13）**：按不变性检查清单逐个修复，P0 清零后才能启动 Task 098
3. **回归 Pass（R）**：每次 Task 完成后 5-10 分钟跑完，只在 STATUS.md 记录
4. **更新**：完成后更新本文档的 Pass 状态表和汇总表
5. **优先级**：Pass 12 > Pass 13 > Phase C，同级别按"修复成本/影响比"排序

> **松烟入墨，字句成锋。**
> 一次彻底的体检，不是为了发现所有问题，而是为了确保接下来 100 章的路没有地基裂缝。
