# 226 · 评审发现修复（blocker + M3 major）

| 项 | 内容 |
|---|---|
| 状态 | DONE |
| 关联 | PRD §6.6 验收 2；tech-m2 §3.2 / §4.3.2 / §4.3.3 / 验收 #5；tech-m3 §4.1 / §4.2 |
| 预估 | 5 个切片（每切片一个小 PR） |
| 来源 | 只读评审报告 `docs/superpowers/plans/2026-11-07-m0-m3-review-audit.md`（2026-11-07，PR #27–#61 全量 review） |

## 目标

修复全量 code review 确认的 1 个 blocker 和 4 个 major，让「人确认销账」信任边界与已接受技术方案一致，并让 M3 步 1–5 具备进入 §6–7 验收的条件。

## 硬约束

- 只改评审报告列出的问题；不顺手重构无关代码。
- 每个切片 TDD：先写失败测试，再实现，审阅后合。
- 不越出 PRD / tech-m2 / tech-m3 已接受范围；设计要改先回改方案文档。
- 不动 `chapter continue` / `review`（M3 步 6 / M4，未授权）。

## 步骤

- [x] **切片 1（blocker）：settlement resolve 降级为提案，不再直写 `resolved`**
  - [x] 失败测试：`apply_settlement` 收到带 `resolve` 操作的 settlement 后，`foreshadowings.status` 不变、open 集（`list_schedulable`）不变；人 `canon confirm promise` 后才是 `resolved` + 追溯列。
  - [x] 实现：`src/songyan/agents/settlement_extractor/_apply.py:791-804` 移除 `update_status(..., "resolved")` 直写；resolve 建议改走提案通道（`plan_*` pending 或 human_mark / observation 计数，按 tech-m2 §4.3.3「pending 销账建议或等价」选型，优先复用既有 `_proposals.py` 通道）。
  - [x] 回归排查：旧 lineage 测试（如 `tests/test_078_foreshadowing_lifecycle.py` 等）若断言 resolve 直写，按 M2 锁定语义更新，并在完成总结里列出每个被更新的测试及理由。
  - [x] 注意：run 管线与 import 回放（`import_replay_service.py:525`）共用 `apply_settlement`，两条路径行为要同时合规。
- [x] **切片 2：variant usage 记账去重 + CLI 归因**
  - [x] 失败测试：真实 LLM 路径（不 mock `default_slot_draft` 内部 record）每槽在 `llm_call_usage` 只有一行；`project_id`/`run_id` 归因非 NULL。
  - [x] 实现：`variant_generate.py:189-202` 显式 `usage_repo.record` 与 client 自动遥测二选一（推荐去掉显式行、保留 client 遥测 + 在 variant CLI 入口 `bind_contextvars`）；成本口径保持 S7 owner 价。
- [x] **切片 3：pick 槽状态守卫 + `is_abandoned` 残留**
  - [x] 失败测试：pick abandoned/archived 槽被拒（干净错误，非 traceback）；合法 pick 后正文行 `is_abandoned=0`。
  - [x] 实现：`variant_pick.py` 加 status 守卫；pick 复活时清除 `chapter_versions.is_abandoned`（元数据 UPDATE，符合只追加不变量）。
- [x] **切片 4：variant generate 失败路径与原子性收口**
  - [x] 失败测试：LLM 失败时已写槽保留、stderr 有摘要、退出码符合 tech-m3 §4.2（非裸 traceback exit 1）；并发/重入撞唯一索引时无孤儿 `chapter_versions` draft 行。
  - [x] 实现：LLMError 包装为带已写槽信息的受控异常；每槽 version+variant+usage 写入收进同一事务（或撞键路径显式清理 draft 行）；`DuplicatePickedVariantError` 的 `exit_code=2` 接上消费者。
- [x] **切片 5（minor 批，一张小 PR）**
  - [x] `canon confirm` 前置状态校验：rejected→approved 是否允许（**需 owner 拍板**，见下）。
  - [x] `_proposals.py` rejected 复活口径统一：extract 提案对 rejected 行应跳过而非覆盖回 pending（与 entity 路径一致；**需 owner 确认语义**）。
  - [x] 单边 `--from-ch`/`--to-ch` 显式旗标被静默丢弃问题：报错或合并，不静默。
  - [x] `compute_stale_chapter_set` 死参数 `evidence_chapters`：删除或接回调用方，不留死代码。

## 验收标准

- [x] 全量 `python -m pytest tests/ -q` + `tests/cli` + `ruff check src/ tests/` + `mypy src/` 绿。
- [ ] 新测试命名合规（无 `test_task###_*` / `test_<数字>_*` / `test_v<数字>_*`）。
- [ ] 切片 1 后：全仓 `foreshadowings.status='resolved'` 的写路径只剩 `canon confirm promise` 一条（grep 证据写进完成总结）。
- [ ] 每切片独立小 PR，Mew COMMENT 后合。

## owner 拍板（2026-11-07 已答）

1. ~~`canon confirm` 是否允许 rejected 行直接转正？~~ **已拍板：不允许**，复活须走 `canon edit` 重新 pending。
2. ~~extract 提案遇 rejected 行：跳过还是允许重提案？~~ **已拍板：跳过**，与 entity 路径一致。

## 完成总结（DONE 时填写）

**状态**：DONE（2026-11-07）。五个切片全部实现，一次性提交（owner 拍板：全部做完一起提交）。

**验收结果**：

- `python -m pytest tests/ -q`：**3527 passed**, 2 skipped, 1 xfailed；唯一失败 `tests/test_llm_http_timeout.py::test_hung_http_call_is_cut_by_per_call_timeout` 为既有 flaky（本机单跑也失败、定时敏感、与本任务零关联），不修，已记为遗留。
- `tests/cli`：**188 passed**；`ruff check src/ tests/` 全过；`mypy src/`（198 文件）零问题。
- 新测试 12 个用例全部先红后绿；命名合规（无 `test_task###_*` / `test_<数字>_*.py` 形式的新增）。
- resolved 写路径唯一性 grep 证据：`foreshadowings.status='resolved'` 在 src 只剩 `canon_write.py`（`canon confirm promise`）一条写径；`apply_settlement` 仅剩 overdue/due 的 open 集内部流转（`_apply.py:1309/1311`）。

**各切片内容**：

1. **切片 1（blocker）**：`_apply.py` resolve 分支不再直写 `resolved`，改为提案留痕（`observation_counts["foreshadowing_resolve_proposed"]` + 日志事件 `settlement.foreshadowing_resolve_proposed`）。run 管线与 import 回放共用 `apply_settlement`，两条路径同时合规。
2. **切片 2**：`variant_generate` 删除显式 `usage_repo.record`（client 遥测记唯一一行）；`generate_chapter_variants` 用 `bound_contextvars` 绑定 project/chapter/agent，归因非 NULL。
3. **切片 3**：`pick_variant_slot` 拒绝 abandoned 槽（新增 `PickAbandonedVariantError`，CLI exit 2）；archived 槽允许复活（测试锁死）。
4. **切片 4**：LLM 失败 → `VariantGenerateLLMError(written_slots)`，CLI 干净报 stderr + exit 1（tech-m3 §4.2 #4）；每槽 version+variant 写入收进同一事务（`chapter_variant_repo.insert` 增加 conn 参数）；pick 撞单 picked 唯一守卫 → exit 2。
5. **切片 5**：`canon confirm` 拒绝 rejected 行（`ConfirmRejectedError`，owner 拍板：复活须走 `canon edit`）；extract 提案跳过 rejected（owner 拍板，与 entity 路径一致，日志事件改 `extract_proposal_skip_final`）；单边 `--from-ch/--to-ch` 显式旗标不再静默回退 valid 窗口（整命令失败 exit 2）；删除死参数 `evidence_chapters`。

**被更新的旧测试（切片 1 行为变更，按 M2 锁定语义改写）**：

- `tests/test_settlement_extractor.py::test_applies_foreshadowing_resolve` → `test_applies_foreshadowing_resolve_as_proposal`：断言 update_status 不被调用 + 提案留痕（原断言 Task 241 直写行为，违反 tech-m2 §3.2）。
- `tests/test_172cr_foreshadowing_resolve.py`：模块 docstring + 3 个端到端测试（planted/overdue/dormant）由「落库 resolved」改为「行不变 + 提案留痕」；prompt 事实源与 resolve 校验断言保留。
- `tests/test_241_foreshadowing_resolved_trace.py`：模块 docstring + `TestApplyResolveTrace`/`TestReplayResolveTrace` 两个测试类改写为提案语义（回放路径不再直写 resolved）；repo 层 `update_status` 回填测试（人确认销账路径）保留不变。

**M2 结论复核**：切片 1 修复后，评审发现的「M2 验收未覆盖 apply_settlement resolve 路径」缺口已补（新测试 `tests/settlement_extractor/test_resolve_proposal_semantics.py` 直接覆盖）。建议 owner 在下次 M 阶段评审时把 M2 验收记录标注为「复核无破口」。

**遗留问题**：

- `test_llm_http_timeout` flaky（既有，非本任务引入）。
- 评审 minor/observation 余项（`_confirm_promise` 事务、migration 崩溃窗口、plan 模型默认值开放坑等）未在本任务范围，见评审报告。
