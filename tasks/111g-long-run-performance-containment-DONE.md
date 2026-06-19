# Task 111g DONE: 长跑性能缺陷收敛

> **完成日期**: 2026-06-19
> **状态**: ✅ 已完成
> **提交范围**: Context 复用防回归 / LiteraryAuditor 缓存 / Settlement prompt 限流 / Setting merge 分桶 / ProjectRunState O(1) 写入

---

## 完成内容

1. **ContextPackage 重复组装收敛**
   - 复用 Task 111f 的 `context_snapshot_id` 路径。
   - Writer、LLMAuditor、LiteraryAuditor 不再自行重新组装完整 ContextPackage。
   - 保留 snapshot 复用测试，覆盖 Auditor 使用同一上下文快照。

2. **LiteraryAuditor 同版本缓存**
   - `LiteraryObservationRepository` 新增 `get_latest_id_by_version()`。
   - `literary_auditor_node()` 对已有 observation 的 `version_id` 跳过 LLM。
   - cache hit 仍返回 `revision_routing`，不设置 `_needs_revision`，保持 LiteraryAuditor 非阻断职责。

3. **SettlementExtractor prompt 事实源限流**
   - 新增角色状态、设定、伏笔 prompt-only selector。
   - prompt 输入限制为正文命中、due/recent 或 top-N。
   - 校验仍使用 SQLite 加载的完整事实源，不影响 `old_value`、setting uniqueness、`source_quote` 和 `source_version_id` 校验。

4. **SettingEvaporator merge 默认路径优化**
   - merge 扫描按 category / setting_key bucket 缩小候选集。
   - 仅让最近新增/提及的 settings 主动探测重复项。
   - 保留同名设定合并语义，合并顺序按 `created_at, setting_key` 稳定排序。

5. **ProjectRunState accumulated_summary 写放大收敛**
   - 每章持久化到 `project_runs.accumulated_summary` 的内容改为最近单章摘要。
   - `ProjectRunResult.accumulated_summary` 仍在最终返回时一次性拼接完整内存列表，保持调用方兼容。

---

## 修改文件

- `src/songyan/agents/setting_evaporator/__init__.py`
- `src/songyan/agents/settlement_extractor/__init__.py`
- `src/songyan/db/review_repo.py`
- `src/songyan/workflows/_nodes.py`
- `src/songyan/workflows/phase2_graph.py`
- `tests/db/test_review_settlement_repository.py`
- `tests/test_108_core_nodes.py`
- `tests/test_phase2_graph.py`
- `tests/test_setting_evaporator.py`
- `tests/test_settlement_extractor.py`
- `docs/STATUS.md`
- `tasks/111g-long-run-performance-containment-DONE.md`

---

## 验证结果

```bash
python -m pytest tests/test_phase1_graph.py tests/test_context_manager.py tests/test_settlement_extractor.py -q
```

结果：`169 passed, 1 xfailed`

```bash
python -m pytest tests/test_setting_evaporator.py tests/test_eval_runner.py -q
```

结果：`25 passed, 4 xpassed, 1 warning`

```bash
python -m pytest tests/test_setting_evaporator.py tests/test_settlement_extractor.py tests/test_108_core_nodes.py tests/db/test_review_settlement_repository.py tests/test_phase2_graph.py tests/models/test_project_run.py -q
```

结果：`102 passed, 1 xfailed`

```bash
python -m pytest tests/ -v
```

结果：`1653 passed, 4 skipped, 1 xfailed, 4 xpassed, 10 warnings`

```bash
python -m pytest tests/ -q
```

结果：`1653 passed, 4 skipped, 1 xfailed, 4 xpassed, 10 warnings`

```bash
ruff check src/songyan/agents/setting_evaporator/__init__.py src/songyan/agents/settlement_extractor/__init__.py src/songyan/db/review_repo.py src/songyan/workflows/_nodes.py src/songyan/workflows/phase2_graph.py tests/test_phase2_graph.py tests/test_setting_evaporator.py tests/test_settlement_extractor.py tests/test_108_core_nodes.py tests/db/test_review_settlement_repository.py
```

结果：`All checks passed!`

```bash
ruff check src/ tests/
```

结果：失败，仍为历史 lint 存量 `113 errors`，集中在未触及测试文件的 E501/F841；本 Task touched files 的 ruff 已通过。

---

## 已知限制

- 本 Task 不执行 Ch101-Ch150 正式长跑；Task 112 负责正式流式验证。
- Settlement prompt 限流只影响 LLM 输入，不减少验证阶段读取完整事实源的 DB 成本。
- 全量 ruff 仍存在历史存量 `113 errors`，touched files 已通过 ruff。

---

## 下一步

进入 **Task 112: Ch101-Ch150 流式验证 + 决策门 DG-2**。
