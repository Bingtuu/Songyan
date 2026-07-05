# Task 168a DONE: 自适应门禁信号快照模型

> **完成时间**: 2026-07-05
> **阶段**: V7 阶段 Y（enforce 可生产化）
> **结论**: 完成。系统现在具备 `adaptive_gate_signal_snapshots` SQLite 事实源，可持久化单章/审计点级别的自适应门禁输入信号。

---

## 交付内容

- 新增模型：
  - `AdaptiveGateSignalSnapshot`
  - `AdaptiveGateContinuitySignals`
  - `AdaptiveGateQualitySignals`
  - `AdaptiveGateLiterarySignals`
  - `AdaptiveGateCleanlinessSignals`
  - `AdaptiveGateContextSignals`
  - `AdaptiveGateNarrativeSignals`
  - `AdaptiveGateSignalSourceStatus`
- 新增 SQLite 表：
  - `adaptive_gate_signal_snapshots`
- 新增 repository：
  - `AdaptiveGateSignalRepository.upsert(...)`
  - `get(...)`
  - `list_range(...)`
  - `delete_range(...)`
- 新增纯构造器：
  - `build_adaptive_gate_signal_snapshot(...)`

## 关键实现

- `run_id=None` 在 repository 层归一化为空字符串，保证 `(project_id, run_id, chapter_number)` 可稳定 upsert。
- 所有信号域用 typed Pydantic model 表达，避免后续 169 直接拼 dict。
- `source_status` 对所有域显式记录 `present/missing/insufficient/observation`。
- 缺失来源默认写入 `missing`，不作为失败。
- 168a 不读取正文，不调用 LLM，不修改 workflow，不调用 `_gates.py`。

## 边界确认

- 不做窗口聚合。
- 不做 spike/anomaly 判定。
- 不改变 `GateConfig`。
- 不改变 enforce / AutoHalt 行为。
- 不新增 workflow 节点。
- 不启动 Ch200。

## 验证结果

```powershell
python -m pytest tests/test_168a_adaptive_gate_signal_snapshot.py -q
# 8 passed

python -m pytest tests/test_168a_adaptive_gate_signal_snapshot.py tests/db/test_migrations.py tests/db/test_schema.py -q
# 29 passed

python -m pytest tests/test_167a_foreshadowing_schedule.py tests/test_167b_schedule_injection.py tests/test_168a_adaptive_gate_signal_snapshot.py -q
# 24 passed

python -m pytest tests/ -q
# 2376 passed, 2 skipped, 1 xfailed, 2 warnings

ruff check src/ tests/
# All checks passed
```

## 后续

进入 Task 168b：自适应门禁窗口聚合与报告出口。168b 应只依赖 `AdaptiveGateSignalRepository.list_range(...)` 读取快照，计算窗口级 trend / hit rate / missed rate / pressure 指标，并追加到 `songyan metrics`。
