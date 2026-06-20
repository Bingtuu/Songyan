# Task 114: Settlement 事实源修复 + Ch101-Ch150 分段流式验证

> **Phase**: V5.0 Phase 4 — 150 章规模化验证
> **优先级**: P0
> **依赖**: Task 111a-111g 完成；Task 112 前置阻断修复完成；Task 113 Ch101 收敛回滚与 Settlement 阻断修复完成
> **当前判定**: Task 114b2 已完成 Ch102/Ch103 QG 收敛阻断处理与 settlement 端到端验证；可按段启动 Task 114c
> **预计工作量**: 3-5 天

---

## Goal

在 Task 111a-111g 修复 Agent/Workflow/Settlement/Context/Report/Performance 契约，由 Task 112 恢复 Ch97 accepted 基线，并由 Task 113 修复 Ch101 收敛回滚与 settlement 阻断后，先修复 Task 114 Phase 1 暴露的 Settlement 事实源契约缺陷，再执行 Ch101-Ch150 分段流式验证，判断 V5.0 Context Diet 2.0 是否具备支撑 150 章全自动生成的稳定性。

## Context

原 Task 112 是 “Ch101-Ch150 流式验证 + 决策门 DG-2”。进入长跑前的基线检查发现 Ch97 当前 head 为 draft 且 `accepted_version_id=None`，补跑 Ch97 时又暴露 Settlement `setting_key` 非法值阻断，因此正式长跑曾顺延为 Task 113。

Task 113 首次启动长跑时在 Ch101 暴露收敛回滚与 settlement 阻断，故原长跑任务后移为 Task 114。Task 113 已通过 Ch101 回放恢复 accepted、settlement 和 summary 基线。

Task 114 Phase 1 首次执行 Ch102-Ch110 时，Ch102 成功，但 Ch103 在 `run-5105e24b` 进入 `settlement_review`，Ch104-Ch110 未继续执行。Review 结论是：这不是 Task 113 的回滚同类问题，而是 V5.0 Settlement 事实源契约缺陷。`SettlementExtractor` 要求 LLM 精确复制长文本 `old_value`，但 Ch103 输出了过期/局部旧值，导致与 Ch102 accepted 后的 DB 当前事实源不一致；同时 `quote_filter` 使用内部 `character_id` 过滤中文正文引用，会放大 settlement 阻断风险。

因此 Task 114 不再是单纯长跑任务，而是拆分为 “P0 修复 + Phase 1 重跑 + Phase 1b 验证窗口 + Phase 2/3 长跑” 的 umbrella 任务。

Task 114a 已完成代码修复与回归测试。Task 114b 实际重跑结果显示：Ch103 回放（`run-385dc3e0`）因 `readability_score:0.473` 触发 QG 收敛失败，Ch102 重跑（`run-452c4f78`）因 `length_score:0.440` 触发 QG 收敛失败；两次均提前 `_skip_settlement=True`，未进入 settlement。因此 114b 未达出口条件，不能直接进入 114c。

Task 114b2 已完成：修复当前版本 lineage 修复计数、QG 合格 best 回滚、rewrite 结构失败后图路由，最终组合窗口 `run-af3ba939` 中 Ch102/Ch103 均完成 accept + settlement + summary，且 run logger 记录 `success=True`。Task 114c 可启动，但必须继续按 Ch111-Ch130、Ch131-Ch150 分段执行。

## Review 判定与拆分方案

### 是否需要拆分

**需要拆分。** 直接推进 Ch111-Ch150 会把 Ch103 暴露的事实源契约缺陷带入后续章节，增加 accepted/settlement/summary 派生状态不一致的风险。

### 子任务边界

| 子任务 | 名称 | 目标 | 出口条件 |
|--------|------|------|----------|
| **Task 114a** | Settlement 事实源契约修复 | 修复 `old_value` 依赖 LLM 精确复制、`quote_filter` 内部 ID 误杀引用、run logger/post-processing 残留风险 | 聚焦测试通过；Ch103 可完成 settlement + summary 或按明确契约阻断且无事实源污染 |
| **Task 114b** | Phase 1 重跑 Ch102-Ch110 | 验证 Task 114a 修复在短窗口内稳定；补完 Ch104-Ch110 | 已熔断：Ch102/Ch103 因 QG 收敛失败提前跳过 settlement，未达出口条件 |
| **Task 114b2** | QG 收敛阻断处理 + settlement 端到端验证窗口 | 处理 Ch102 length / Ch103 readability 阻断，并让 Ch102/Ch103 至少一个短窗口穿透 accept + settlement + summary | ✅ 已完成：`run-af3ba939` 中 Ch102/Ch103 均成功 |
| **Task 114c** | Phase 2/3 长跑 + DG-2 | 执行 Ch111-Ch130、Ch131-Ch150，生成 DG-2 决策报告 | 达到 DG-2 通过/条件通过标准，或明确拆分后续 P0/P1 修复 |

### 当前推进结论

- **禁止** 在 Task 114a 完成前启动 Ch111-Ch150。
- **允许** 在 Task 114a 完成后先重跑 Ch103 或 Ch102-Ch110。
- Task 114b 已触发 QG 收敛熔断且未穿透 settlement，已归档为熔断复核。
- Task 114b2 已通过，允许进入 Task 114c。

## 执行顺序（必须按序）

1. **Task 114a — Settlement 事实源契约修复**
   - 修复 `SettlementExtractor` 对 `old_value` 的职责边界：已存在 `(character_id, field)` 的 `old_value` 必须由代码从 DB 当前事实源回填或校正，LLM 只负责提取 `new_value` 和证据。
   - 修复 `quote_filter`：CharacterUpdate 不得用内部 `character_id` 作为正文关键词过滤条件；应改用角色名或仅做正文存在性/长度校验。
   - 修复 run logger：失败章节不得因 `_settlement_needs_human_review` 缺省而误记 `settlement_success=True`。
   - 收紧 settlement 后处理：RAG、SettingEvaporator、layered summary 只能由本次 accept + settlement 事务成功触发，不得依赖历史 `version_type in ("accepted", "edited")` 旁路。
   - 增加 Ch103 级回归测试，覆盖：
     - `old_value` 自动校正或回填
     - quote 不因内部角色 ID 被误清空
     - validation failed 不落库、不 accepted、不生成派生状态
     - run logger 正确记录 settlement/summary 状态

2. **Task 114a 验证**
   - 按 `AGENTS.md` Windows 测试进程防卡协议执行 `pytest tests/ -q`。
   - 若看到完整 `\d+ passed` summary 且无 `failed` / `error` / `errors`，但进程未退出，记录为 `PASS_WITH_TEARDOWN_TIMEOUT` 并清理残留进程。
   - 执行 `ruff check src/ tests/`，区分本 Task 新增 lint 与历史存量 lint；不得把历史存量作为启动长跑的重复阻断。
   - 确认 `git status --short` 干净，避免长跑期间混入未提交代码改动。

3. **接口与报告入口确认**
   - 通过 `songyan run --help` 或源码确认长跑 CLI 参数。
   - 通过 `python scripts/generate_streaming_report.py --help` 或源码确认报告脚本参数。
   - 确认项目 ID 为 `proj-e74ef1e4`，章节范围为 `101-150`，模式为 `webnovel_intense`，并启用 `--auto-confirm`。
   - 确认 DB、`.env`、logs 路径、checkpointer 模式和 JSONL metrics 输出位置。

4. **Task 114b — 重跑 Phase 1（必须先完成，禁止跳过）**

   Phase 1 首次运行已在 Ch103 停止，因此修复后必须先重跑短窗口，不得直接启动 Phase 2。

   - **优先验证 Ch103**
     ```bash
     songyan run --project-id proj-e74ef1e4 --chapters 103-103 --mode-id webnovel_intense --auto-confirm
     ```
     目标：确认 `run-5105e24b` 暴露的 settlement `old_value` mismatch 不再阻断，且 accepted、settlement、summary 三者一致。

   - **Phase 1 — Ch102-Ch110（验证修复普适性）**
     ```bash
     songyan run --project-id proj-e74ef1e4 --chapters 102-110 --mode-id webnovel_intense --auto-confirm
     ```
     目标：确认 Task 113 的收敛回滚修复和 Task 114a 的 settlement 修复在 Ch101 之外的章节同样有效，无新的 settlement/convergence 阻断。

5. **Task 114b2 — QG 收敛阻断处理 + settlement 端到端验证窗口（已完成）**

   Task 114b 的 Ch103/Ch102 回放没有进入 settlement，因此不能证明 114a 修复在真实长跑链路中端到端生效。进入 Ch111-Ch150 前必须先补齐验证窗口。

   - **处理 Ch102 length 阻断**
     - 目标：避免 `length_score:0.440` / 字数 2514 类失败再次在 settlement 前阻断。
     - 不通过临时放宽 QG 阈值完成；优先检查 Writer/Rewrite 的目标字数执行与 best version 选择。

   - **处理 Ch103 readability 阻断**
     - 目标：避免 `readability_score:0.473` 类失败再次在 settlement 前阻断。
     - 优先检查 RuleAuditor 可读性扣分项、修订耗尽路径和是否可复用 QG 合格版本做 settlement replay。

   - **执行 settlement 端到端验证**
     ```bash
     songyan run --project-id proj-e74ef1e4 --chapters 103-103 --mode-id webnovel_intense --auto-confirm
     songyan run --project-id proj-e74ef1e4 --chapters 102-103 --mode-id webnovel_intense --auto-confirm
     ```
     目标：至少在 Ch102/Ch103 短窗口中看到 accept + settlement + summary 成功，且日志可证明 `old_value` 回填/校正、quote_filter 角色名校验和 run logger 判定均按契约工作。

6. **Task 114c — 分段启动剩余长跑（当前下一步，必须按段执行，禁止一次性 40 章）**

   Task 114b2 已通过，可以继续：

   - **Phase 2 — Ch111-Ch130（中规模窗口）**
     ```bash
     songyan run --project-id proj-e74ef1e4 --chapters 111-130 --mode-id webnovel_intense --auto-confirm
     ```
     目标：验证 20 章连续运行稳定性，收集 QG 通过率和 budget 趋势。

   - **Phase 3 — Ch131-Ch150（收尾窗口）**
     ```bash
     songyan run --project-id proj-e74ef1e4 --chapters 131-150 --mode-id webnovel_intense --auto-confirm
     ```
     目标：完成最后 20 章，确认 150 章端到端达标率。

   **每段通用要求**：
   - 长跑命令必须使用硬超时外层包装（参考 `AGENTS.md` Windows 防卡协议），避免终端在业务完成后卡住。
   - 每段 stdout/stderr 必须落盘到 `logs/task114/` 并按段命名，保留用于事后诊断。
   - 长跑过程中不临时修改评分阈值、Prompt 或 Workflow 节点。

7. **流式监控与熔断条件**

   每段运行期间和结束后检查以下指标，**任一条件触发即熔断停机**：

   | 熔断条件 | 判定标准 | 停机后动作 |
   |----------|----------|-----------|
   | **Convergence + Settlement 双失败** | 任意一章 `convergence_failed=true` 且 `skip_settlement=true` | 停止后续章节，保留 run id、JSONL、DB、stdout/stderr，分析是否为 Task 113 同类问题 |
   | **Settlement 事实源失败复发** | 任意一章出现 `old_value` mismatch、quote_filter 大量清空 CharacterUpdate quote、或 `settlement.validation_failed` | 停止后续章节，回到 Task 114a 修复，不得扩大长跑 |
   | **连续 Settlement 失败** | 连续 2 章 `settlement_success=false`（不含明确且预期的人审状态） | 同上，检查是否为系统性 settlement 阻断 |
   | **硬超时** | 单段运行时间超过 4 小时（14400 秒） | 按 `AGENTS.md` 防卡协议判定，以 JSONL/DB 为准，不强制继续 |
   | **事实源污染** | 出现 `accepted_version_id` 指向 abandoned 版本、或 accepted 后无 settlement/summary 且非明确 skip | 立即停止，拆分 P0 修复任务，不继续推进 |
   | **Budget 硬门禁突破** | 任意一章 `budget_used > 1.0` 且未触发 ContextEmergency 阻断 | 记录并分析，若连续出现则停机 |

   **每段结束后的强制检查清单**：
   - [ ] 该段所有章节 JSONL 中 `success` 字段状态正常，或失败原因已记录
   - [ ] `chapter_heads.accepted_version_id` 与 JSONL 一致，无指向 abandoned 版本
   - [ ] 每章 settlement + summary 已写入（或明确标记 skip_settlement 且有 fallback）
   - [ ] `budget_used` 趋势稳定，无异常突增
   - [ ] 无残留 python/pytest/songyan 进程

8. **报告与收口**
   - 生成 DG-2 报告，对比 Task 105b、110d、110e 基线。
   - 生成 `tasks/114-ch101-ch150-streaming-validation-DONE.md`。
   - 更新 `docs/STATUS.md`、`README.md` 和必要索引。
   - 提交包含报告、DONE 文档和状态更新的 git commit。

## In Scope（必须完成）

- [ ] **准备验证基线**
  - 确认 Task 111a-111g 的 DONE 文档和回归测试结果
  - 确认 Task 112 已恢复 Ch97 accepted + settlement + summary
  - 确认当前 DB、`.env`、logs 路径、checkpointer 模式和项目 ID
  - 记录 Ch80-Ch96 / Ch51-Ch100 的最新对比基线

- [ ] **Task 114a: Settlement 事实源契约修复**
  - `old_value` 由代码事实源回填或校正，不再依赖 LLM 精确复制长字符串
  - `quote_filter` 不再用内部 `character_id` 误杀 CharacterUpdate 中文引用
  - run logger 准确记录失败章节的 settlement/summary 状态
  - accepted 后处理只在本次 settlement + accept 事务成功后触发
  - 增加 Ch103 regression case，覆盖 `run-5105e24b` 同类问题

- [ ] **Task 114b: Phase 1 重跑**
  - 先重跑 Ch103，验证 `old_value mismatch` 不再阻断
  - 再重跑 Phase 1: Ch102-Ch110（验证修复普适性）
  - 补完 Ch104-Ch110 的实际运行记录
  - Phase 1 结束后执行强制检查清单，确认无阻断后再启动 Phase 2

- [x] **Task 114b2: QG 收敛阻断处理 + settlement 端到端验证窗口**
  - 已修复 Ch102/Ch103 新回放继承历史 revision/rewrite 次数的问题
  - 已修复 QG 合格 best 不能解除 `_skip_settlement` 的问题
  - 已修复 rewrite 结构失败后固定进入审查链路的问题
  - 已用 `run-af3ba939` 验证 Ch102/Ch103 短窗口真实穿透 settlement

- [ ] **Task 114c: 剩余长跑与 DG-2**
  - Phase 2: Ch111-Ch130（中规模稳定性）
  - Phase 3: Ch131-Ch150（收尾与达标率）
  - 每段结束后执行强制检查清单，确认无阻断后再启动下一段
  - 使用 scifi + webnovel_intense
  - 使用 `--auto-confirm`
  - 保留 JSONL chapter run metrics
  - 出现连续失败时按本 Task 熔断条件停机分析

- [ ] **收集 DG-2 指标**
  - 成功章节数
  - QG 通过率
  - `budget_used`
  - ContextEmergency 次数
  - coherence/readability/momentum/length 各维失败原因
  - revision/rewrite 次数
  - settlement validation 状态
  - summary / lifecycle / RAG / evaporator 后置维护结果

- [ ] **生成一键报告**
  - 输出 DG-2 报告
  - 对比 Task 105b、110d、110e 基线
  - 标明是否进入 V5.1 或继续 P0 修复

## Out of Scope（明确不做）

- 不在长跑中临时改评分阈值
- 不用 Prompt 调优替代事实源契约修复
- 不新增 Workflow 节点
- 不修复非阻断 P2 清理项
- 不在 Task 114a 完成前启动 Ch111-Ch150

## 接口契约

```bash
songyan run --project-id <project_id> --chapters 101-150 --mode-id webnovel_intense --auto-confirm
```

```bash
python scripts/generate_streaming_report.py --run-id <run_id>
```

实际命令以当前 CLI 和脚本参数为准；执行前必须通过 `--help` 或源码确认。

## 数据模型

不新增模型。复用现有 chapter run JSONL、project run metrics、score card、settlement 和 summary 数据。

## 测试要求

### Layer 1: Task 114a 聚焦测试
- [ ] SettlementExtractor：已有 `(character_id, field)` 的 `old_value` 被 DB 当前值回填或校正
- [ ] QuoteFilter：CharacterUpdate 的中文原文引用不会因为不包含内部 `character_id` 被清空
- [ ] Settlement 边界：validation failed 不落库、不 accepted、不生成 settlement 后处理副作用
- [ ] RunLogger：失败章节不会默认记录为 `settlement_success=True`

### Layer 2: 前置回归
- [ ] `pytest tests/ -q` 按 `AGENTS.md` 防卡协议执行并通过；允许记录 `PASS_WITH_TEARDOWN_TIMEOUT`
- [ ] `ruff check src/ tests/` 无本 Task 新增 lint 错误；历史存量 lint 必须在 DONE 文档中记录

### Layer 3: 长跑验证（分段验收）
- [ ] Ch103 单章回放完成，accepted/settlement/summary 状态一致，或按明确契约阻断且无事实源污染
- [ ] Phase 1 (Ch102-Ch110) 完成且无熔断触发，或熔断后已诊断并修复
- [x] Task 114b2 完成：Ch102/Ch103 短窗口穿透 accept + settlement + summary，或明确诊断并修复新的阻断
- [ ] Phase 2 (Ch111-Ch130) 完成且无熔断触发
- [ ] Phase 3 (Ch131-Ch150) 完成且无熔断触发
- [ ] 每章都有 chapter run metrics
- [ ] 每个 accepted 章节都有 settlement + summary，除非明确 skip_settlement 且有 fallback summary
- [ ] 每段结束后执行强制检查清单并通过

### Layer 4: 报告验证
- [ ] DG-2 报告可复现统计数据
- [ ] 报告中标明失败章节、失败原因和是否可自动恢复

## 验收标准（Acceptance Criteria）

### 分段验收指标

| 指标 | Task 114a | Task 114b / Phase 1 (Ch102-Ch110) | Task 114b2 / 验证窗口 | Task 114c / Phase 2 (Ch111-Ch130) | Task 114c / Phase 3 (Ch131-Ch150) | 整体 |
|------|-----------|-------------------------------------|--------------------------|--------------------------------------|--------------------------------------|------|
| 出口条件 | Ch103 类 settlement mismatch 已修复 | 已熔断，需进入 114b2 | ✅ Ch102/Ch103 `run-af3ba939` 短窗口穿透 settlement | 完成率 >= 90% | 完成率 >= 90% | >= 95%，或失败可按熔断策略诊断恢复 |
| QG 通过率 | 不作为 114a 指标 | 未达标 | 短窗口不再在 settlement 前阻断 | >= 65% | >= 70% | >= 70% |
| `budget_used` | 不回归 | 每章 <= 1.0 | 每章 <= 1.0 | 每章 <= 1.0 | 每章 <= 1.0 | 每章 <= 1.0 |
| 熔断触发 | 0 个未解释事实源污染 | 已触发 QG 收敛熔断 | 0 次未解释熔断 | 0 次 | 0 次 | 累计 <= 2 次且均已修复 |

### 整体验收指标

| 指标 | 目标 |
|------|------|
| Task 114a 修复 | `old_value` 不再依赖 LLM 精确复制；quote_filter 不再因内部 ID 清空有效 CharacterUpdate quote |
| Ch103 回放 | accepted、settlement、summary 一致，或明确阻断且无半提交 |
| Ch101-Ch150 运行完成率 | >= 95%，或失败可按熔断策略诊断恢复 |
| QG 通过率 | >= 70% |
| `budget_used` | 每章 <= 1.0；如超出必须触发并记录 emergency |
| ContextEmergency | 目标 0；若出现需说明触发分区和后续影响 |
| settlement validation failed | 0 个自动落库；任意复发必须回到 Task 114a |
| accepted 后 summary | 100% 有真实 summary 或 fallback summary |
| 无事实源污染 | `accepted_version_id` 无指向 abandoned 版本 |
| DG-2 报告 | 已生成并写入任务 DONE 文档 |

## 决策门 DG-2

- **通过**：QG 通过率 >= 70%，无 P0 状态污染，budget 稳定，进入 V5.1 文学质量与 Prompt 层优化。
- **条件通过**：QG 通过率 60%-70%，无 P0 状态污染，可进入局部 P1 修复后重跑失败窗口。
- **不通过**：QG 通过率 < 60%，或出现 accepted/settlement/summary 长期事实源污染，停止长跑并拆分 P0 修复任务。
- **DG-2 前置否决**：Task 114a 未完成、Ch103 回放未通过、Phase 1 未补完、或 Task 114b2 未完成时，不进入 DG-2 判定。当前 Task 114b2 已完成，后续 DG-2 仍需等待 Task 114c 分段长跑结果。

## 验收标准（工程流程）

- [ ] 生成 `tasks/114-ch101-ch150-streaming-validation-DONE.md`
- [ ] 更新 `docs/STATUS.md`
- [ ] 更新 `README.md`
- [ ] Git commit 包含验证报告、DONE 文档和状态更新

## 参考文档

- `tasks/105-ch51-ch100-streaming-validation-DONE.md` — 流式验证基础设施
- `tasks/105b-ch51-ch100-validation-restart-DONE.md` — Ch51-Ch100 重启验证基线
- `tasks/110e-coherence-major-fix-DONE.md` — Ch80-Ch96 最新成功基线
- `tasks/111a-workflow-decision-contract-fix.md` — 工作流决策契约前置修复
- `tasks/111b-settlement-state-integrity-fix.md` — Settlement 事实源前置修复
- `tasks/111c-context-prompt-consistency-fix.md` — Context/Prompt 一致性前置修复
- `tasks/111d-quality-gate-settlement-blockers-fix.md` — QualityGate 与 Settlement 阻断项修复
- `tasks/111e-task112-reporting-dg2-gate-fix.md` — Task 112 报告与 DG-2 Gate 完整性修复
- `tasks/111f-context-snapshot-prompt-metadata-fix.md` — Context Snapshot、Prompt 与 Metadata 一致性修复
- `tasks/111g-long-run-performance-containment.md` — 长跑性能缺陷收敛
- `tasks/112-preflight-blocker-fix.md` — Task 112 前置阻断修复
- `tasks/113-ch101-convergence-settlement-blocker-fix.md` — Task 113 Ch101 收敛回滚与 Settlement 阻断修复
