# V7 代码审查与架构审计 — 最终汇总报告

> **审计计划**: `archive/superpowers/plans/2026-07-06-v7-code-review-and-architecture-audit-plan.md`
> **审计日期**: 2026-07-06  
> **项目基线**: V7 Task 169 完成后，`2397 passed, 2 skipped, 1 xfailed, 2 warnings`  
> **审计目标**: 在 Ch200 爬坡前确认 V5/V6/V7 核心工程纪律与架构无地基裂缝。

## 1. 执行摘要

### 1.1 总体结论

**无 P0 发现，无事实源污染或流程崩溃风险，可以在完成 P1 修复后进入 Task 170 / Ch200 爬坡。**

V5/V6/V7 的四大铁律在代码层面基本被遵守：
- ✅ `chapter_versions` 正文内容字段未被 `UPDATE` 覆盖。
- ✅ `character_states` 仅 `lifecycle_status` 元数据可 `UPDATE`，状态本身 INSERT-only。
- ✅ Agent 层不直接拿 DB connection，数据访问集中在 repository / service / workflow。
- ✅ LangGraph `Phase1State` 主体为 ID 和标量，未存储完整业务对象；仅有少量小型业务 dict/list 需要复核。

但项目存在明显的**结构性债务**：`_nodes.py`（2,652 行）、`context_manager/__init__.py`（1,136 行）、`revision_handler/__init__.py`（1,029 行）已越过维护拐点；`schema.sql` 表编号混乱、`migrations.py` 累积 971 行。这些 P1 债务若不治理，将在 Ch200+ 长跑中放大维护成本。

### 1.2 发现汇总

| Pass | 名称 | 发现数 | P0 | P1 | P2 |
|------|------|--------|----|----|----|
| 1 | 合规性审查 | 4 | 0 | 1 | 3 |
| 2 | 架构审计 | 6 | 0 | 3 | 3 |
| 3 | 数据/schema 审计 | 4 | 0 | 2 | 2 |
| 4 | 工作流审计 | 5 | 0 | 1 | 4 |
| 5 | Agent 边界审计 | 1 | 0 | 0 | 1 |
| 6 | 质量门审计 | 4 | 0 | 0 | 4 |
| 7 | V7 新子系统审计 | 4 | 0 | 0 | 4 |
| 8 | 测试质量审计 | 4 | 0 | 0 | 4 |
| 9 | Prompt/配置审计 | 3 | 0 | 0 | 3 |
| 10 | 性能/可观测性审计 | 5 | 0 | 0 | 5 |
| 11 | 安全/依赖审计 | 5 | 0 | 0 | 5 |
| 12 | 文档一致性审计 | 3 | 0 | 0 | 3 |
| **合计** | — | **48** | **0** | **7** | **41** |

### 1.3 关键风险热力图

| 维度 | 风险强度 | 主要理由 |
|------|----------|----------|
| **架构（超大文件 / 职责集中）** | █████████ | `_nodes.py` 2652 行、context_manager 1136 行、revision_handler 1029 行 |
| **数据/schema** | ███████ | `schema.sql` 编号混乱、`migrations.py` 971 行 |
| **工作流稳定性** | ██████ | `_nodes.py` 多处裸 `except Exception` 吞掉具体异常 |
| **LangGraph State** | █████ | Phase1State 含少量业务 dict/list，有膨胀趋势 |
| **V7 新子系统** | █████ | re-plan 缺自动 rollback、adaptive halt 默认关闭待 Ch200 验证 |
| **测试效率** | █████ | 全量 520s，慢测试未标记 performance；Embedder 懒加载拖累单元测试 |
| **Prompt/配置** | ████ | revision_handler 有 2 处内联 Prompt |
| **性能/可观测** | █████ | `call_llm` 不返回 token/request_id；Embedder 裸 except |
| **安全/依赖** | ███ | 依赖基本完整；f-string SQL 均为内部常量驱动 |
| **文档一致性** | ████ | V4.0 `code-review-plan.md` 未归档；8 个文件 CRLF 污染 |

---

## 2. P1 级修复清单（必须进入阶段 Z 前完成）

### P1-1 `workflows/_nodes.py` 职责过度集中
- **出处**: Pass 2.2
- **文件**: `src/songyan/workflows/_nodes.py`
- **问题**: 2652 行，承担规划、写作、审查、修订、质量门、结算、评分等 9 类职责，是“上帝文件”。
- **修复建议**: 按职责拆分为 `workflows/nodes/{planning,writing,review,revision,gate,settlement,scoring}.py`；`_nodes.py` 仅保留兼容导出。
- **验证**: `pytest tests/test_108_core_nodes.py tests/test_phase1_graph.py -q`。

### P1-2 `agents/context_manager/__init__.py` 主函数过大
- **出处**: Pass 2.3
- **文件**: `src/songyan/agents/context_manager/__init__.py`
- **问题**: `assemble_context_package` 约 1000 行，混合分层摘要、角色衰减、设定蒸发、预算硬天花板、RAG chunks 注入。
- **修复建议**: 拆分为 `context_manager/{assemblers,pruner,decay,evaporator,compressor}.py`。
- **验证**: `pytest tests/test_context_manager.py -q`。

### P1-3 `agents/revision_handler/__init__.py` 职责混杂
- **出处**: Pass 2.4
- **文件**: `src/songyan/agents/revision_handler/__init__.py`
- **问题**: 同时承担 issue 筛选、readability 策略、prompt 渲染、patch 执行、输出保存。
- **修复建议**: 拆分为 `revision_handler/{issue_filter,readability,prompt_renderer,patch_engine,output_writer}.py`。
- **验证**: `pytest tests/test_revision_handler.py -q`。

### P1-4 `schema.sql` 表编号混乱
- **出处**: Pass 3.1
- **文件**: `src/songyan/db/schema.sql`
- **问题**: 编号 `4.5` 重复、`13/14` 顺序颠倒、`19` 之后跳到 `23`。
- **修复建议**: 重新整理为连续整数，或改用“V5/V6/V7”阶段前缀。
- **验证**: `grep -nE '^\s*--\s*[0-9]+\.' src/songyan/db/schema.sql` 连续无重复。

### P1-5 `db/migrations.py` 累积 971 行
- **出处**: Pass 3.3
- **文件**: `src/songyan/db/migrations.py`
- **问题**: 35+ 个 `_migrate_*` 函数内联 CREATE/ALTER，维护负担重。
- **修复建议**: 拆分为 `db/migrations/*.py` 按版本独立脚本；长期引入版本化迁移文件。
- **验证**: `pytest tests/db/ -q`。

### P1-6 `Phase1State` 携带少量业务 dict/list
- **出处**: Pass 1.4
- **文件**: `src/songyan/workflows/phase1_graph.py`
- **问题**: `_prev_merged_issues`、`_new_issues_introduced`、`_score_card`、`_best_score_card` 等不是纯标量/ID。
- **修复建议**: 将这类数据通过 ID 指向独立表（如新增 `revision_trace`），state 中只保留 `trace_id`。
- **验证**: `pytest tests/test_phase1_graph.py -q`。

### P1-7 `_nodes.py` 多处裸 `except Exception`
- **出处**: Pass 4.4
- **文件**: `src/songyan/workflows/_nodes.py`
- **问题**: 10 处裸 `except Exception` 吞掉具体异常类型，仅事务回滚处合理。
- **修复建议**: 收窄为具体异常类型（`ValidationError`、`LLMError`、`ValueError` 等），或在顶层统一捕获并记录 traceback。
- **验证**: `ruff check src/songyan/workflows/_nodes.py` + `pytest tests/test_108_core_nodes.py -q`。

---

## 3. P2 级修复清单（建议进入 Ch200 前完成，但不阻塞）

按主题合并后共 30+ 项，下面列出对长跑稳定性影响最大的 15 项：

| ID | 出处 | 问题 | 修复文件 | 验证命令 |
|----|------|------|----------|----------|
| P2-01 | 1.7 / 2.6 / 5.7 | `settlement_extractor_node` 承担 6 项非结算后处理 | `src/songyan/workflows/_nodes.py` + 新增 Service | `pytest tests/test_phase1_graph.py tests/test_settlement_extractor.py -q` |
| P2-02 | 4.7 / 2.7a | `phase2_graph.py` 单章与 run 级编排耦合 | 拆出 `workflows/single_chapter_runner.py` + Service | `pytest tests/test_phase2_graph.py -q` |
| P2-03 | 8.1 | 测试未复用统一 `mock_llm` fixture | 各测试文件 | `rg 'patch\("songyan\.agents\..*\.call_llm"' tests/ -c` 下降 |
| P2-04 | 8.2 | 慢测试未标记 `performance` | 集成/E2E 测试 + `pyproject.toml` | `pytest tests/ -m "not performance" -q` <120s |
| P2-05 | 8.3 | 内部工具模块缺独立测试 | `tests/settlement_extractor/`, `tests/agents/` | 新增测试全绿 |
| P2-06 | 8.4 | Embedder 懒加载拖累单元测试 | `tests/conftest.py` + 相关测试 | 慢测试列表下降 |
| P2-07 | 9.1 | `revision_handler` 有 2 处内联 Prompt | `src/songyan/agents/revision_handler/` + `prompts/cards/revision_handler/` | `pytest tests/test_revision_handler.py -q` |
| P2-08 | 10.2 | Embedder 裸 `except Exception` 返回零向量 | `src/songyan/rag/embedder.py` | `pytest tests/rag/ -q` |
| P2-09 | 10.3 / 11.5 | `call_llm` 不返回 token 用量 / request_id | `src/songyan/llm/client.py` + 调用方 | `pytest tests/ -k llm -q` |
| P2-10 | 11.1 | `json_repair` 未声明依赖 | `pyproject.toml` | 干净 venv `python -c "import json_repair"` |
| P2-11 | 11.2 | `lifecycle_scheduler.transition` 表名未白名单 | `src/songyan/db/lifecycle_scheduler.py` | 新增单测 |
| P2-12 | 6.2 | 重复长段落仅作为观测指标 | `src/songyan/agents/rule_auditor.py` + `_nodes.py` | `pytest tests/test_161_paragraph_dedup.py -q` |
| P2-13 | 7.1 | re-plan 无自动 rollback 方法 | `src/songyan/services/replan_application.py` | `pytest tests/test_166*.py -q` |
| P2-14 | 12.1 | V4.0 `code-review-plan.md` 未归档/未指向 V7 | `docs/code-review-plan.md` | 文件顶部含 V7 指向 |
| P2-15 | 12.2 | 8 个 Python 文件 CRLF 行尾污染 | 8 个文件 + `.gitattributes` | `git ls-files --eol` 全为 `w/lf` |

完整 P2 清单见各 Pass 报告的“待修复清单”：
- [Pass 1](pass1-compliance-report.md)
- [Pass 2](pass2-architecture-report.md)
- [Pass 3](pass3-data-and-schema-report.md)
- [Pass 4](pass4-workflow-report.md)
- [Pass 5](pass5-agent-boundaries-report.md)
- [Pass 6](pass6-quality-gates-report.md)
- [Pass 7](pass7-v7-subsystems-report.md)
- [Pass 8](pass8-testing-report.md)
- [Pass 9](pass9-prompts-config-report.md)
- [Pass 10](pass10-performance-observability-report.md)
- [Pass 11](pass11-security-dependencies-report.md)
- [Pass 12](pass12-docs-consistency-report.md)

---

## 4. 各 Pass 关键结论速查

| Pass | 核心结论 |
|------|----------|
| **Pass 1 合规性** | 四大铁律基本成立；Phase1State 有少量业务 dict/list；settlement_extractor_node 职责漂移。 |
| **Pass 2 架构** | 分层清晰但 3 个文件越过维护拐点；Service 层覆盖不足，大量编排逻辑在 `_nodes.py`。 |
| **Pass 3 数据/schema** | 关键写入使用事务；V7 新表索引合理；schema 编号与 migrations 累积是主要维护负担。 |
| **Pass 4 工作流** | Phase1 路由无死胡同；Phase2 resume 以 accepted head 为事实源；adaptive halt 默认关闭；裸 except 过多。 |
| **Pass 5 Agent 边界** | Writer/Auditor/RevisionHandler/GoalPlanner/ContextManager 边界清晰；settlement 后处理超出 Agent 职责。 |
| **Pass 6 质量门** | critical/major 必须有 evidence_quote；阈值动态化；文学性不阻塞 accept；重复段落未进入自动修订。 |
| **Pass 7 V7 新子系统** | re-plan、伏笔调度、adaptive gate/halt 架构合理；58 个测试通过；re-plan 缺自动 rollback。 |
| **Pass 8 测试质量** | 2397 全绿；E2E 覆盖主路径；mock 分散、慢测试未标记、部分内部模块缺独立测试。 |
| **Pass 9 Prompt/配置** | 工艺卡版本管理体系成熟；revision_handler 有 2 处内联 Prompt；Jinja2 沙箱防护到位。 |
| **Pass 10 性能/可观测** | RAG 增量加载、LLM 重试/预算熔断、DB 遥测均落地；`call_llm` 缺少 token/request_id。 |
| **Pass 11 安全/依赖** | 无注入漏洞；`json_repair` 未声明；lifecycle_scheduler 表名接口可白名单化。 |
| **Pass 12 文档一致性** | STATUS/V7-README 一致；旧 code-review-plan 未归档；8 个文件 CRLF 污染。 |

---

## 5. 进入 Ch200 的放行条件

建议满足以下条件后再启动阶段 Z（Ch200 / Ch250 / Ch300）长跑：

1. **P1 清零**: 完成 §2 中 7 项 P1 修复并通过对应测试。
2. **P2 优先级项完成**: 至少完成 P2-01、P2-02、P2-09、P2-13（settlement 职责拆分、Phase2 编排解耦、LLM token/request_id、re-plan rollback）。
3. **全量回归通过**: `pytest tests/ -q` 保持 `2397 passed, 2 skipped, 1 xfailed, 2 warnings` 或更好。
4. **Lint 通过**: `ruff check src/ tests/` 无新增告警。
5. **文档更新**: `docs/INDEX.md` 已指向本报告；`docs/code-review-plan.md` 已归档 V4.0 并指向 V7 审计计划。
6. **行尾统一**: 工作区 `git status` 干净，无 CRLF 污染导致的“无可见 diff modified”。

---

## 6. 后续任务建议

针对本次审计发现，建议新开以下 Task（编号接 Task 170 之后）：

| 建议 Task 编号 | 任务 | 范围 | 目标 |
|---------------|------|------|------|
| 171a | 超大文件拆分与 Service 层下沉 | `_nodes.py`, `context_manager`, `revision_handler`, `phase2_graph` | P1 清零，降低维护拐点 |
| 171b | Schema 与迁移重构 | `schema.sql`, `migrations.py` | 编号连续化、迁移脚本独立化 |
| 171c | LangGraph State  diet | `phase1_graph.py` | state 只存 ID，业务数据入表 |
| 171d | 异常处理与可观测补强 | `_nodes.py`, `llm/client.py`, `rag/embedder.py` | 收窄裸 except、返回 token/request_id |
| 171e | 测试工程效率 | `tests/conftest.py`, 慢测试 | 统一 mock、performance 标记、Embedder mock |
| 171f | 文档与行尾清理 | `docs/code-review-plan.md`, `.gitattributes`, 8 个 CRLF 文件 | 文档一致性、工作区干净 |

---

## 7. 验证命令速查

```bash
# 全量测试
pytest tests/ -q

# Lint
ruff check src/ tests/

# 超大文件
find src/songyan -name '*.py' -exec wc -l {} + | sort -rn | head -30

# 版本覆盖风险
rg 'UPDATE chapter_versions' src/songyan/ -n

# 裸 except
rg 'except Exception' src/songyan/workflows/_nodes.py -n

# 慢测试
pytest tests/ --durations=20 -q

# git 行尾
git ls-files --eol | grep 'w/crlf'
```

---

## 8. 附录：报告索引

| 报告 | 路径 |
|------|------|
| Pass 1 合规性 | `docs/reports/v7-audit/pass1-compliance-report.md` |
| Pass 2 架构 | `docs/reports/v7-audit/pass2-architecture-report.md` |
| Pass 3 数据/schema | `docs/reports/v7-audit/pass3-data-and-schema-report.md` |
| Pass 4 工作流 | `docs/reports/v7-audit/pass4-workflow-report.md` |
| Pass 5 Agent 边界 | `docs/reports/v7-audit/pass5-agent-boundaries-report.md` |
| Pass 6 质量门 | `docs/reports/v7-audit/pass6-quality-gates-report.md` |
| Pass 7 V7 新子系统 | `docs/reports/v7-audit/pass7-v7-subsystems-report.md` |
| Pass 8 测试质量 | `docs/reports/v7-audit/pass8-testing-report.md` |
| Pass 9 Prompt/配置 | `docs/reports/v7-audit/pass9-prompts-config-report.md` |
| Pass 10 性能/可观测 | `docs/reports/v7-audit/pass10-performance-observability-report.md` |
| Pass 11 安全/依赖 | `docs/reports/v7-audit/pass11-security-dependencies-report.md` |
| Pass 12 文档一致性 | `docs/reports/v7-audit/pass12-docs-consistency-report.md` |
| **最终汇总（本文件）** | `docs/reports/v7-audit/final-audit-report.md` |

---

> **松烟入墨，字句成锋。**
> 本审计确认：150 章之后的地基没有结构性裂缝，但屋顶需要加固。完成 P1 与关键 P2 项后，可放心迈向 Ch200。
