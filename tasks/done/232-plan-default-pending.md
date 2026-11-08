# 232 · plan 模型 approval_status 默认值改 pending（P0-3 拍板方案 A）

| 项 | 内容 |
|---|---|
| 状态 | DONE（2026-11-08） |
| 关联 | 搁置记录 `tasks/done/229-plan-default-pending-deferred.md`（owner 2026-11-07 书面拍板方案 A） |
| 预估 | 小切片（模型 5 处默认值 + 测试机械修复） |

## 背景

五个 plan 模型（`PlanEntity` / `PlanAttribute` / `PlanEvent` / `PlanTimeAnchor` / `PlanClue`）的 `approval_status` 默认 `"approved"`。不显式传状态构造卡片即直写 Canon，绕过 pending 队列，与「确认才入典」核心边界相悖。

拍板前评估（已核实）：

- 生产写入方全部显式传值：`canon_write.py`（pending）、`_proposals.py`（pending）、`plan_fact_repo.py` row→model 映射（DB 读回）。
- 两个种子夹具 JSON 已显式写 `"approved"`（pydantic 解析走 JSON 值），夹具零改动。
- 依赖默认值的是测试代码：约 50+ 处构造点未传 `approval_status`，改默认后这些卡变 pending，gate/checker 测试会失败。

## 范围

- [x] 建任务
- [x] TDD：模型级测试「不显式传 approval_status 即 pending」先红
- [x] 五模型默认值 `"approved"` → `"pending"`（`src/songyan/models/plan_facts.py`）
- [x] 修复依赖默认值的测试：夹具语义卡显式传 `"approved"`
- [x] 全量回归（重点 `tests/db/test_plan_fact_cards.py`、`tests/plan_checks/`、M0–M2 CLI 测试）
- [x] 只读 review → 归档 → 同步 STATUS/HANDOFF → 本地提交

## 验收标准

- [x] 五模型不显式传状态时 `approval_status == "pending"`（模型级测试锁死）。
- [x] 显式传 `"approved"` / `"rejected"` 行为不变。
- [x] 种子夹具加载后 approved 卡仍进 Canon（gate 可见）。
- [x] `pytest tests/` 全绿（允许既有 `test_llm_http_timeout` 环境失败）；ruff / `mypy src/` 过。

## 完成总结

**状态**：DONE（2026-11-08）。

**做了什么**：

1. `src/songyan/models/plan_facts.py` 五模型 `approval_status` 默认值 `"approved"` → `"pending"`，模块 docstring 补记默认语义（不显式传状态即入 pending 队列，绝不静默进 Canon）。
2. 新增 `tests/models/test_plan_facts_defaults.py`：锁死五模型默认 `pending` + 显式 `approved`/`rejected` 不被默认值覆盖（TDD 先红后绿）。
3. 测试侧 26 处构造点显式补 `approval_status="approved"`（夹具语义卡）：`test_plan_fact_cards.py`（3）、`test_plan_attribute_source_extract.py`（1）、`test_claim_check.py`（1）、`test_must_mention.py`（1）、`test_observe_review_inputs.py`（11）、`test_plan_fact_gate.py`（3）、`test_typed_attributes.py`（4）、`test_variant_fingerprint.py`（5，按 5 模型各一计）。
4. 有意保留不显式传状态的用例：`test_plan_fact_cards.py` 中 4 个 repo round-trip / 校验拒绝测试（状态无关，现顺带覆盖 pending 行序列化）。

**review**：无 blocker / major；minor 2 条（round-trip 用例现只过 pending 行，可补不补；任务流程项）均记录不修。

**记录不修（新增环境项）**：`tests/test_191_ch200_harness.py` 在本机确定性失败——测试以 `text=True` 起子进程，子进程输出 UTF-8 中文而父进程按 cp936 解码（`UnicodeDecodeError`）。与本次改动无关（stash 掉改动后于 HEAD 复现）；`PYTHONUTF8=1` 下该文件 11/11 通过。属环境编码项，连同 `test_llm_http_timeout` 一起留维护者调查。后续本机全量回归建议带 `PYTHONUTF8=1`。

**验证**：新增模型测试先红后绿；重点套件（`tests/models` + `tests/db` + `tests/plan_checks` + variant fingerprint）271 passed；全量 `pytest tests/`（带 `PYTHONUTF8=1`）终验；ruff / `mypy src/`（198 文件）全绿。
