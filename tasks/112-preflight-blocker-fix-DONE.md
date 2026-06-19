# Task 112 DONE: Task 113 前置阻断修复

> **完成日期**: 2026-06-19
> **Phase**: V5.0 Phase 4 — 150 章规模化验证前置准备
> **结果**: ✅ 完成，Task 113 可进入 Ch101-Ch150 流式验证准备

---

## 做了什么

1. 修复 QualityGate budget 硬门禁。
   - `ScoreAggregator.flags.budget_ok` 改为以 `budget_used <= 1.0` 为硬门禁。
   - 保留 budget score 作为排序/加权指标，不再用 `budget_score >= 0.5` 误判 hard ceiling。
   - 覆盖 `_context_metrics.budget_used` 在无完整 `ContextPackage` 时仍可驱动 QG。

2. 修复 Settlement `setting_key` 规范化阻断。
   - 将 `setting_key` 规范化提前到 settlement validation 之前。
   - 支持中文、数字开头、点号异常、混合路径等非法 key 的稳定 ASCII 三段式归一。
   - `_validate_settlement` 复用统一 `_is_valid_setting_key`，避免 validate/apply 两套规则不一致。
   - Ch97 阻断样例 `e.0.实验室.位置与历史` 归一为 `e_0.s_4ae2c4c7.n_ad166662`。

3. 恢复 Ch97 accepted 基线。
   - 补跑命令：

```bash
songyan run --project-id proj-e74ef1e4 --chapters 97-97 --mode-id webnovel_intense --auto-confirm
```

   - 新 run: `run-8c20d4f1`
   - 新 accepted version: `v-97-18-993f1a7a`
   - `chapter_heads.accepted_version_id` 已恢复为 `v-97-18-993f1a7a`
   - run 状态: `completed`
   - Ch97 summary: `sum-proj-e74ef1e4-97-33461899`
   - 本次补跑新落库 6 条 setting，非法 `setting_key` 数为 0。

4. 同步 Task 112/113 边界。
   - Task 112 固化为前置阻断修复。
   - Ch101-Ch150 流式验证顺延为 Task 113。
   - 更新 `STATUS.md`、`README.md`、`docs/INDEX.md`。

## 改动文件

- `AGENTS.md`
- `README.md`
- `docs/INDEX.md`
- `docs/STATUS.md`
- `src/songyan/evals/score_aggregator.py`
- `src/songyan/agents/settlement_extractor/__init__.py`
- `src/songyan/agents/settlement_extractor/_setting_quality.py`
- `src/songyan/agents/settlement_extractor/_validate.py`
- `tests/test_106_scoring_system.py`
- `tests/test_phase1_graph.py`
- `tests/settlement_extractor/test_setting_quality.py`
- `tests/test_settlement_extractor.py`
- `tasks/112-preflight-blocker-fix.md`
- `tasks/113-ch101-ch150-streaming-validation.md`
- `tasks/112-preflight-blocker-fix-DONE.md`

## 验证结果

### 窄测试

```bash
python -m pytest tests/test_106_scoring_system.py tests/test_phase1_graph.py tests/settlement_extractor/test_setting_quality.py tests/test_settlement_extractor.py -q
```

结果：

```text
150 passed, 1 xfailed
WRAPPER_RESULT=PASS_WITH_TEARDOWN_TIMEOUT
TEST_ASSERTIONS=PASSED
PROCESS_EXIT=TIMEOUT_AFTER_SUMMARY
```

### 单元测试

```bash
python -m pytest tests/ -v
```

结果：

```text
1658 passed, 4 skipped, 2 xfailed, 3 xpassed, 10 warnings
WRAPPER_RESULT=PASS_NORMAL_EXIT
```

### 全量回归

```bash
python -m pytest tests/ -q
```

结果：

```text
1658 passed, 4 skipped, 2 xfailed, 3 xpassed, 10 warnings
WRAPPER_RESULT=PASS_NORMAL_EXIT
```

### 代码检查

```bash
ruff check src/songyan/evals/score_aggregator.py src/songyan/agents/settlement_extractor/__init__.py src/songyan/agents/settlement_extractor/_setting_quality.py src/songyan/agents/settlement_extractor/_validate.py tests/test_106_scoring_system.py tests/test_phase1_graph.py tests/settlement_extractor/test_setting_quality.py tests/test_settlement_extractor.py
```

结果：

```text
All checks passed!
```

全量 ruff：

```bash
ruff check src/ tests/
```

结果：失败，均为历史 lint 存量，集中在未改动测试文件中的 `E501`、`F841` 等；本次改动文件定向 ruff 通过。

## 已知限制

- `proj-e74ef1e4` 历史数据中仍存在旧 run 遗留的非法 `setting_key`，统计为 447 条；本次 Ch97 补跑新落库 setting 无非法 key。该历史数据清理不纳入 Task 112，建议如 Task 113 前仍需“全库 setting_key 规范率 100%”，单独拆数据迁移/归档任务。
- Windows 下窄测试仍出现 pytest summary 已完成但进程 teardown 不退出的情况，已按 `AGENTS.md` 防卡协议处理。

## 下一步

进入 `tasks/113-ch101-ch150-streaming-validation.md`：Ch101-Ch150 流式验证 + 决策门 DG-2。
