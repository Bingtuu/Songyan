# Pass 1: 合规性审查报告

## 执行摘要

- 发现总数: 4
- P0: 0, P1: 1, P2: 3
- 关键结论: V5/V6/V7 的核心不可违背规则在代码中基本被遵守，但 Phase1State 中出现了少量小型业务集合/字典，虽未违反“state 只存 ID”的严格字面解释，仍建议复核；`settlement_extractor_node` 承载了远超出“状态结算”职责的后处理长尾，存在职责漂移风险。

## 检查项与发现

### 1.1 版本不可覆盖检查

- **级别**: 通过
- **方法**: `rg 'UPDATE chapter_versions' src/songyan/ -n -C 2`
- **结果**:
  - `src/songyan/db/repository.py:494` — `UPDATE chapter_versions SET is_abandoned = 1`（元数据标记，OK）
  - `src/songyan/db/repository.py:513` — `UPDATE chapter_versions SET version_type = 'accepted'`（元数据标记，OK）
  - `src/songyan/db/repository.py:550` — `UPDATE chapter_versions SET score_card = ?`（元数据标记，OK）
- **结论**: 未发现对 `content` / `word_count` / `scenes` 等正文字段的 `UPDATE`，版本不可覆盖规则成立。

### 1.2 character_states INSERT-only 检查

- **级别**: 通过
- **方法**: `rg 'UPDATE character_states' src/songyan/ -n -C 2`
- **结果**:
  - `src/songyan/db/context_repo.py:273` / `:335` / `:451` / `:538` — 均只更新 `lifecycle_status` 字段（dormant / archived）。
- **结论**: 与 `AGENTS.md` “`character_states` 快照表永远 INSERT，禁止 UPDATE（`lifecycle_status` 元数据除外）”一致。

### 1.3 Agent 层不直接拿 DB connection

- **级别**: 通过
- **方法**: `rg 'from songyan.db.connection import get_db' src/songyan/agents/ -n -C 2`
- **结果**: 命令返回 exit code 1，无命中。
- **结论**: Agent 包内部没有直接导入 `get_db`；数据访问集中在 repository / service / workflow 层。

### 1.4 LangGraph state 只存 ID

- **级别**: P1
- **文件**: `src/songyan/workflows/phase1_graph.py:49-114`
- **问题描述**: `Phase1State` 主体为 ID 和标量控制字段，符合铁律。但存在少量小型集合/字典字段，虽未存储完整业务对象，却携带了业务细节：
  - `_context_metrics: dict`（Task 111b 注释说明“ContextPackage 不入 state，仅保留轻量指标”，可接受）
  - `_deferred_constraints: list[str]`
  - `_prev_merged_issues: list[dict] | None`
  - `_new_issues_introduced: list[dict] | None`
  - `_best_score_card: dict | None`
  - `_score_card: dict | None`
- **证据**:
  ```python
  # phase1_graph.py:99-114
  _context_metrics: dict
  _deferred_constraints: list[str]
  _continuity_budget_exhausted: bool
  _score_card: dict | None
  _prev_merged_issues: list[dict] | None
  ```
- **潜在影响**: 这些字段目前体积可控，但随着 V7/V8 继续堆叠状态，state 可能膨胀，LangGraph checkpoint 序列化/反序列化成本上升，且业务逻辑与路由状态耦合加深。
- **修复建议**: 将 `_prev_merged_issues`、`_new_issues_introduced`、`_score_card` 等通过 ID 指向独立表（如 `review_reports` 或新增 `revision_trace` 表），state 中只保留 `report_id` 或 `trace_id`。
- **验证方式**: 检查 `phase1_graph.py` 是否只剩标量/ID；运行 `pytest tests/test_phase1_graph.py -q`。

### 1.5 结算证据校验检查

- **级别**: 通过（含一处 P2 建议）
- **文件**: `src/songyan/agents/settlement_extractor/_validate.py`
- **结果**:
  - `character_update.old_value` 由 DB 当前值回填（`_validate.py:560-578`）。
  - `source_quote` 使用模糊匹配验证在正文中存在（`_validate.py:589-602`）。
  - `setting_key` 三段式格式校验（`_validate.py:605-620`）。
  - `numerical_update.closing_value` 公式闭合校验，并支持 telemetry snapshot 规范化（`_validate.py:624-647`）。
  - `foreshadowing_update.source_version_id` 非空校验，`plant` 操作 `expected_resolve_chapter` 边界回填（`_validate.py:650-674`）。
- **P2 建议**: `_quote_in_content` 对空 quote 直接返回 `True`（`_validate.py:190`），若上游未过滤空 quote，可能让无证据设定通过。建议增加显式日志并在调用处强制非空。

### 1.6 自动修订最多 2 轮

- **级别**: 通过
- **文件**: `src/songyan/workflows/phase1_graph.py:39, 122-175`
- **结果**:
  - 默认 `_MAX_REVISION_ROUNDS = int(os.environ.get("SONGYAN_MAX_REVISION_ROUNDS", "2"))`。
  - `revision_router` 在 `rround >= max_r` 时路由到 `rewrite`。
  - 存在 `_total_revision_count` 跨 rewrite 累计计数。
- **结论**: 自动修订轮次上限机制成立。

### 1.7 settlement_extractor_node 职责漂移（P2）

- **级别**: P2
- **文件**: `src/songyan/workflows/_nodes.py:2256-2645`
- **问题描述**: `settlement_extractor_node` 除了执行 SettlementExtractor 核心结算外，还顺序执行了 RAG 索引、setting 蒸发、分层摘要、plot thread 更新、foreshadowing schedule 推进、输入侧降级/回升/resolve 等 6 项后处理。虽然每项都有 try/except 非阻塞隔离，但节点已成为“accept 后所有长尾任务”的中央枢纽。
- **证据**:
  ```text
  2256  async def settlement_extractor_node(...)
  2440  RAG 索引
  2465  SettingEvaporator
  2490  分层摘要 (arc/volume)
  2510  PlotThread 更新
  2540  ForeshadowingSchedule 生命周期
  2580  输入侧治理 (demote/promote/resolve)
  ```
- **潜在影响**: 单节点职责过重，任一后处理失败虽被捕获，但增加测试复杂度；与架构原则中“SettlementExtractor 只做结算提取和验证”存在漂移。
- **修复建议**: 将 RAG/蒸发/摘要/线索/调度/输入侧治理拆分为独立节点或 Service 方法，由 Phase1 图在 settlement 后按需顺序调用，每个职责独立测试。

## 通过项

- [x] `chapter_versions` 内容字段未被 UPDATE 覆盖。
- [x] `character_states` 仅 `lifecycle_status` 元数据被 UPDATE。
- [x] Agent 层无直接 DB connection 导入。
- [x] Settlement 证据校验（old_value / source_quote / setting_key / numerical formula / foreshadowing source_version_id）均存在。
- [x] 自动修订轮次上限为 2 并正确路由。

## 待修复清单

| ID | 级别 | 问题 | 建议修复文件 | 验证命令 |
|----|------|------|--------------|----------|
| 1.4 | P1 | Phase1State 携带少量业务 dict/list，state 存在轻微膨胀和耦合 | `src/songyan/workflows/phase1_graph.py`, 可能新增 revision trace 表 | `pytest tests/test_phase1_graph.py -q` |
| 1.5a | P2 | `_quote_in_content` 对空 quote 直接返回 True，可能让无证据设定通过 | `src/songyan/agents/settlement_extractor/_validate.py:184-214` | `pytest tests/test_settlement_extractor.py -q` |
| 1.7 | P2 | `settlement_extractor_node` 承担 accept 后 6 项长尾后处理，职责漂移 | `src/songyan/workflows/_nodes.py`, 拆分为独立节点/Service | `pytest tests/test_phase1_graph.py tests/test_settlement_extractor.py -q` |

---

> 下一 Pass: [Pass 2 架构审计](pass2-architecture-report.md)
