# V7 代码审查与架构审计 — Pass 13 最终汇总报告

> **审计计划**: 本次审计为 V7 阶段 Z 中期审计，接 2026-07-06 的 pass1-12 审计继续编号。
> **审计日期**: 2026-07-13
> **项目基线**: V7 Task 171w 完成后，`run-e27b763f` Ch201-Ch220 20/20 accepted
> **全量测试**: `2623 passed, 2 skipped, 1 xfailed, 2 warnings in 423.32s`
> **Lint**: `ruff check src/ tests/` — All checks passed
> **类型检查**: `mypy src/` — 失败（>100 errors，详见 Pass 16）
> **审计目标**: 在 Ch250 长跑前确认 V7 新增/硬化代码无结构性裂缝，并评估 pass1-12 中 P1/P2 项的修复情况。

---

## 1. 执行摘要

### 1.1 总体结论

**存在 3 个 P0 级风险，必须在进入 Ch250 长跑前修复；P1 级问题建议在启动 172 前清零；P2 级债务可在 Ch250 爬坡过程中分批治理。**

相比 pass1-12 的审计（当时结论为“无 P0，7 个 P1”），本次审计发现 V7 后期代码在工程纪律上出现了新的 P0 风险，主要集中在：

1. **数据安全**: `db/connection.py` 在 WAL 模式下删除 `-wal`/`-shm` 文件，可能导致数据库损坏。
2. **版本不可变性**: `db/repository.py` 直接 `UPDATE chapter_versions`，违反“每次生成/修订必须创建新记录，禁止覆盖”的铁律。
3. **Agent 边界**: `agents/revision_handler/__init__.py` 对 patchable issue 做整章重写，违反“RevisionHandler 只做 patch，不整章重写”。

这些 P0 问题若不修复，将直接威胁长跑稳定性与事实源可信度。

### 1.2 发现汇总

| Pass | 名称 | 发现数 | P0 | P1 | P2 |
|------|------|--------|----|----|----|
| 13 | V7 后期新增子系统 | 16 | 0 | 3 | 13 |
| 14 | 工作流与 LangGraph | 15 | 1 | 4 | 10 |
| 15 | 数据层与 Schema | 18 | 2 | 9 | 7 |
| 16 | 测试与工程质量 | 13 | 2 | 5 | 6 |
| 17 | Agent 边界与结算 | 9 | 1 | 3 | 5 |
| **合计** | — | **71** | **6** | **24** | **41** |

### 1.3 关键风险热力图

| 维度 | 风险强度 | 主要理由 |
|------|----------|----------|
| **数据/schema 纪律** | ███████████ | P0-2 违反版本不可变性；P0-1 WAL 文件删除可损坏数据库；多个约束缺失 |
| **Agent 边界** | ██████████ | P0-3 RevisionHandler 整章重写；P1 source_quote 空字符串放行 |
| **工作流稳定性** | ████████ | rewrite_node 截断失败导致内存/DB 不一致；裸 except 吞关键异常 |
| **类型与工程质量** | ███████ | mypy strict 失败；全量测试 >7 分钟；CRLF 污染 |
| **可维护性** | ██████ | `_nodes.py` 2695 行、`migrations.py` 1019 行、schema 编号混乱 |
| **可观测性** | ████ | `call_llm` 仍不返回 token/request_id（继承 pass10） |

---

## 2. P0 级修复清单（必须在 Ch250 长跑前完成）

### P0-1 `db/connection.py` 在 WAL 模式下删除 `-wal`/`-shm` 文件

- **出处**: Pass 15.1
- **文件**: `src/songyan/db/connection.py:60-69`
- **问题**: 连接已打开时无条件删除 WAL/SHM 文件，可能截断未 checkpoint 的数据。
- **修复建议**: 删除该段逻辑；WAL 文件由 SQLite 自身在 checkpoint 后回收。若必须处理崩溃残留，应在关闭所有连接后通过 `PRAGMA journal_mode = DELETE` 或备份恢复方式处理。
- **验证**: `python -m pytest tests/db/test_connection.py -q` + `grep -n "unlink" src/songyan/db/connection.py` 无匹配。

### P0-2 `ChapterVersionRepository` 直接 `UPDATE chapter_versions`

- **出处**: Pass 15.2
- **文件**: `src/songyan/db/repository.py:491-497`, `:505-528`, `:544-559`
- **问题**: `mark_abandoned`、`accept_version`、`update_score_card` 直接修改 `chapter_versions` 表，违反版本不可变原则。
- **修复建议**:
  - `accept_version`: 保持旧版本不变，新增 `version_type='accepted'` 的新版本，并更新 `chapter_heads.accepted_version_id`。
  - `mark_abandoned`: 新增标记版本，或仅在 `chapter_heads` 层做逻辑废弃。
  - `update_score_card`: 新增 `version_type='accepted'` 的 patch 版本，而不是原地更新。
- **验证**: `rg 'UPDATE chapter_versions' src/songyan/ -n` 无匹配；`pytest tests/db/test_repository.py tests/test_settlement_extractor.py tests/test_phase1_graph.py -q` 通过。

### P0-3 RevisionHandler 对 patchable issue 做整章重写

- **出处**: Pass 17.1
- **文件**: `src/songyan/agents/revision_handler/__init__.py:590-636`
- **问题**: `_patch_mandatory_reference_missing` 对 `fix_type="patch"` 的 issue 索要“完整修订后的正文”。
- **修复建议**: 改为局部 patch：定位适合插入设定的段落，生成只包含插入句的 `Patch`，通过 `_apply_patches` 应用。
- **验证**: `pytest tests/test_revision_handler.py tests/test_task138n_mandatory_reference_revision.py -q` 通过；检查该函数不再包含“输出完整修订后的正文”。

### P0-4 mypy strict 模式失败（新增 P0，因 pyproject.toml 声明 strict=true）

- **出处**: Pass 16.1
- **文件**: `src/songyan/` 多处
- **问题**: `mypy src/` 输出 >100 条 error，与 `pyproject.toml` 声明的 `strict = true` 冲突。
- **修复建议**:
  1. 优先修复真实类型不匹配（`review_merger.py`、`rule_auditor.py`、`writer.py`）。
  2. 补全泛型参数。
  3. 处理缺失 stub。
  4. 在 `src/` 根添加 `py.typed`。
- **验证**: `mypy src/` 返回 `Success: no issues found`。

### P0-5 全量 pytest 超过 7 分钟

- **出处**: Pass 16.2
- **文件**: `pyproject.toml`
- **问题**: 全量 2623 个测试耗时 423.32s，影响 CI 和本地开发体验。
- **修复建议**: 将 >5s 的 E2E/长链/压力测试标记为 `@pytest.mark.performance`；默认 CI 跑 `pytest -m "not performance"`。
- **验证**: `pytest -m "not performance" tests/ -q` 在 180s 内完成。

### P0-6 `rewrite_node` 截断失败导致内存/DB 不一致

- **出处**: Pass 14.1
- **文件**: `src/songyan/workflows/_nodes.py:872-931`
- **问题**: 截断后若新版本创建失败，`except Exception` 继续使用已被修改的内存对象。
- **修复建议**: 将截断逻辑放入同一事务/工作单元：先创建新版本对象，再决定是否废弃旧版本。任何写入失败都应回滚到原始版本。
- **验证**: `pytest tests/test_rewrite_node.py tests/test_phase1_graph.py -q` 通过；新增测试覆盖截断失败回滚路径。

---

## 3. P1 级修复清单（建议进入 Ch250 前完成）

| ID | 出处 | 问题 | 修复文件 | 验证命令 |
|---|---|---|---|---|
| P1-1 | Pass 14.2 | 关键路径裸 `except Exception` | `src/songyan/workflows/_nodes.py` | `pytest tests/test_108_core_nodes.py -q` |
| P1-2 | Pass 14.3 | `human_gate_node` 同步编辑器调用阻塞事件循环 | `src/songyan/workflows/_nodes.py` | `pytest tests/test_phase1_graph.py -q` |
| P1-3 | Pass 14.4 | `Phase1State` 携带业务 dict/list | `src/songyan/workflows/phase1_graph.py` + 新增表 | `pytest tests/test_phase1_graph.py -q` |
| P1-4 | Pass 14.5 | re-plan 闭环缺 rollback | `src/songyan/db/replan_repo.py` | `pytest tests/test_166*.py -q` |
| P1-5 | Pass 15.3 | schema.sql 编号混乱 | `src/songyan/db/schema.sql` | `grep -nE '^\s*--\s*[0-9]+\.'` 连续无重复 |
| P1-6 | Pass 15.4 | migrations.py 超过 1000 行 | `src/songyan/db/migrations.py` | `pytest tests/db/test_migrations.py -q` |
| P1-7 | Pass 15.5 | `lifecycle_errors` 表缺失于 schema.sql | `src/songyan/db/schema.sql` | `pytest tests/db/test_schema.py -q` |
| P1-8 | Pass 15.6 | `setting_key` 未加唯一约束 | `src/songyan/db/schema.sql` | `pytest tests/db/test_schema.py -q` |
| P1-9 | Pass 15.7 | `foreshadowings.source_version_id` 允许 NULL | `src/songyan/db/schema.sql` + `settlement_repo.py` | `pytest tests/test_078_foreshadowing_lifecycle.py -q` |
| P1-10 | Pass 15.8 | `numerical_ledgers` 未持久化 formula | `src/songyan/db/schema.sql` + `settlement_repo.py` | `pytest tests/test_settlement_extractor.py -q` |
| P1-11 | Pass 15.9 | 连续性追踪表缺外键 | `src/songyan/db/schema.sql` | `pytest tests/db/test_schema.py -q` |
| P1-12 | Pass 15.10 | `NewSetting.chapter_number` 与 schema 不匹配 | `src/songyan/db/settlement_repo.py` + `models/settlement.py` | `pytest tests/test_settlement_extractor.py -q` |
| P1-13 | Pass 15.11 | `character_update.old_value` 无校验 | `src/songyan/agents/settlement_extractor/_validate.py` | `pytest tests/test_settlement_extractor.py -q` |
| P1-14 | Pass 16.3 | `tests/evals` 与 `tests/cli` 被全局忽略 | `pyproject.toml` | `pytest tests/evals tests/cli -q` |
| P1-15 | Pass 16.4 | mock LLM 未统一 | `tests/conftest.py` | 统计 `patch("songyan.agents.*.call_llm")` 使用次数下降 |
| P1-16 | Pass 16.5 | CRLF 行尾污染 | 多个文件 + `.gitattributes` | `git ls-files --eol` 全为 `w/lf` |
| P1-17 | Pass 16.6 | `review_merger`/`rule_auditor` 类型混用 | `src/songyan/workflows/review_merger.py`, `src/songyan/agents/rule_auditor.py` | `mypy src/` 无相关错误 |
| P1-18 | Pass 17.2 | `_handle_scene_split` 整章重写 | `src/songyan/agents/revision_handler/__init__.py` | `pytest tests/test_revision_handler.py -q` |
| P1-19 | Pass 17.3 | RevisionHandler 内联 Prompt | `src/songyan/agents/revision_handler/` + `prompts/cards/` | `pytest tests/test_revision_handler.py -q` |
| P1-20 | Pass 17.4 | 空 `source_quote` 绕过校验 | `src/songyan/agents/settlement_extractor/_quote_filter.py`, `_validate.py` | `pytest tests/test_settlement_extractor.py -q` |
| P1-21 | Pass 13.3 | `audit_171v_guardrail_persistence` latest brief 选择逻辑脆弱 | `src/songyan/evals/literary_guardrails.py` | `pytest tests/test_171v_literary_guardrails.py -q` |
| P1-22 | Pass 13.2 | `_brief_builder.py` 裸 except | `src/songyan/agents/creative_director/_brief_builder.py` | `pytest tests/test_creative_director.py -q` |
| P1-23 | Pass 13.1 | `generate_dialogue_style_cards` 异常捕获错误 | `src/songyan/agents/creative_director/__init__.py` | `pytest tests/test_creative_director.py -q` |

---

## 4. P2 级修复清单（建议 Ch250 爬坡过程中分批治理）

按主题合并后，对长跑稳定性影响较大的 P2 项如下：

| ID | 出处 | 问题 | 修复文件 | 验证命令 |
|---|---|---|---|---|
| P2-01 | Pass 14.6 | `_nodes.py` 职责过度集中（2695 行） | 拆分为 `workflows/nodes/*.py` | `pytest tests/test_108_core_nodes.py tests/test_phase1_graph.py -q` |
| P2-02 | Pass 14.7/8/9 | `Phase1State` 字段缺失/不一致、docstring 位置错误 | `src/songyan/workflows/phase1_graph.py` | `mypy src/` 无错误 |
| P2-03 | Pass 14.10 | `AdaptiveHaltPolicy.min_present_ratio` 未使用 | `src/songyan/evals/adaptive_halt.py` | `pytest tests/test_169a_adaptive_halt_decision_engine.py -q` |
| P2-04 | Pass 15.12 | `text_cleanliness_metrics` 主键索引冗余 | `src/songyan/db/schema.sql` | `pytest tests/db/test_schema.py -q` |
| P2-05 | Pass 15.13 | `connection.py` 未检查 `PRAGMA quick_check` 结果 | `src/songyan/db/connection.py` | `pytest tests/db/test_connection.py -q` |
| P2-06 | Pass 15.14/15 | `run_quality_debt`/`run_db_metrics` 缺外键；schema 头部注释过时 | `src/songyan/db/schema.sql` | `pytest tests/db/test_schema.py -q` |
| P2-07 | Pass 15.16 | `ChapterVersionRepository.get_chain` 递归无深度限制 | `src/songyan/db/repository.py` | `pytest tests/db/test_repository.py -q` |
| P2-08 | Pass 16.7/8/9/10/11 | 慢测试标记、覆盖度、fixture 缺失、xfail、弃用警告 | 多个测试文件 | `pytest tests/ -q` 通过 |
| P2-09 | Pass 17.5/6/7/8 | 裸 except、硬编码主角名、死代码、重复导入 | 多个 agent 文件 | `ruff check src/ tests/` |
| P2-10 | Pass 13.4-11 | rule_auditor 类型标注、死代码、重复计数等 | `src/songyan/agents/rule_auditor.py` | `mypy src/` 无错误 |

---

## 5. 进入 Ch250 的放行条件

建议满足以下条件后再启动 Task 172 Ch250 长跑：

1. **P0 清零**: 完成 §2 中 6 项 P0 修复并通过对应测试。其中 P0-2（版本不可变性）和 P0-1（WAL 删除）是硬阻塞项。
2. **P1 高优先级项完成**: 至少完成 P1-1（裸 except）、P1-3（state 业务对象）、P1-9（source_version_id 非空）、P1-10（formula 持久化）、P1-20（空 source_quote）、P1-21（latest brief 选择逻辑）。
3. **全量回归通过**: `pytest tests/ -q` 保持 `2623 passed, 2 skipped, 1 xfailed, 2 warnings` 或更好。
4. **Lint 通过**: `ruff check src/ tests/` 无新增告警。
5. **类型检查收敛**: `mypy src/` 无 error（P0-4）。
6. **默认测试门禁限时**: `pytest -m "not performance" tests/ -q` 在 180s 内完成（P0-5）。
7. **文档更新**: 本报告已链接到 `docs/INDEX.md` 和 `tasks/V7-README.md`。

---

## 6. 与 pass1-12 审计的对比

| 维度 | pass1-12 (2026-07-06) | pass13 (2026-07-13) |
|---|---|---|
| 基线 | Task 169 完成 | Task 171w 完成 |
| 全量测试 | 2397 passed | 2623 passed |
| P0 数量 | 0 | 6 |
| P1 数量 | 7 | 24 |
| 主要新增风险 | 无 | WAL 删除、版本 UPDATE、RevisionHandler 整章重写、mypy 失败、测试超时 |
| 已修复项 | — | 未观察到 pass1-12 中 P1 问题被系统修复；`_nodes.py`、context_manager、revision_handler、schema、migrations 等债务依然存在 |

**说明**: P0 数量从 0 上升到 6，并非代码质量恶化，而是因为本次审计更深入地触达了数据层和 Agent 边界的核心纪律，且 mypy/测试时间等问题在 pass1-12 中未被标为 P0。建议立即组织一轮 P0/P1 修复专项。

---

## 7. 建议新增 Task

| 建议 Task 编号 | 任务 | 范围 | 目标 |
|---|---|---|---|
| 172p-1 | 数据层纪律修复 | `connection.py`, `repository.py`, `schema.sql`, `settlement_repo.py` | P0-1/P0-2/P1-8/9/10/11/12/13/20 清零 |
| 172p-2 | RevisionHandler 守界修复 | `src/songyan/agents/revision_handler/` | P0-3/P1-18/19 清零 |
| 172p-3 | 工作流状态与异常治理 | `src/songyan/workflows/_nodes.py`, `phase1_graph.py`, `phase2_graph.py` | P0-6/P1-1/2/3 + P2-01/02 清零 |
| 172p-4 | 类型与工程质量收敛 | 全 `src/`、测试配置 | P0-4/P0-5/P1-14/15/16/17 清零 |
| 172p-5 | schema 与迁移重构 | `schema.sql`, `migrations.py` | P1-5/6/7 + P2-04/05/06/07 清零 |

---

## 8. 验证命令速查

```powershell
# 全量测试
python -m pytest tests/ -q

# Lint
ruff check src/ tests/

# 类型检查
mypy src/

# 非 performance 测试限时
python -m pytest -m "not performance" tests/ -q

# DB 测试
python -m pytest tests/db/ -q

# 超大文件
find src/songyan -name '*.py' -exec wc -l {} + | sort -rn | head -30

# 版本覆盖风险
rg 'UPDATE chapter_versions' src/songyan/ -n

# 裸 except
rg 'except Exception' src/songyan/workflows/_nodes.py -n

# 慢测试
pytest tests/ --durations=30 -q

# git 行尾
git ls-files --eol | grep 'w/crlf'
```

---

## 9. 报告索引

| 报告 | 路径 |
|------|------|
| Pass 13 V7 后期新增子系统 | `docs/reports/v7-audit/pass13-v7-late-subsystems-report.md` |
| Pass 14 工作流与 LangGraph | `docs/reports/v7-audit/pass14-workflow-langgraph-report.md` |
| Pass 15 数据层与 Schema | `docs/reports/v7-audit/pass15-data-schema-report.md` |
| Pass 16 测试与工程质量 | `docs/reports/v7-audit/pass16-test-quality-report.md` |
| Pass 17 Agent 边界与结算 | `docs/reports/v7-audit/pass17-agent-settlement-report.md` |
| **Pass 13 最终汇总（本文件）** | `docs/reports/v7-audit/pass13-final-audit-report.md` |

---

> **松烟入墨，字句成锋。**
> 本审计结论：V7 阶段 Z 代码在功能上已支撑 Ch200+，但在数据层纪律、Agent 边界、类型与工程效率上存在必须清零的 P0/P1 风险。完成 §2 与 §3 高优先级项后，方可放心迈向 Ch250。
