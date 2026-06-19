# Task 114: Ch101-Ch150 流式验证 + 决策门 DG-2

> **Phase**: V5.0 Phase 4 — 150 章规模化验证
> **优先级**: P0
> **依赖**: Task 111a-111g 完成；Task 112 前置阻断修复完成；Task 113 Ch101 收敛回滚与 Settlement 阻断修复完成
> **预计工作量**: 2-4 天

---

## Goal

在 Task 111a-111g 修复 Agent/Workflow/Settlement/Context/Report/Performance 契约，由 Task 112 恢复 Ch97 accepted 基线，并由 Task 113 修复 Ch101 收敛回滚与 settlement 阻断后，执行 Ch101-Ch150 流式验证，判断 V5.0 Context Diet 2.0 是否具备支撑 150 章全自动生成的稳定性。

## Context

原 Task 112 是 “Ch101-Ch150 流式验证 + 决策门 DG-2”。进入长跑前的基线检查发现 Ch97 当前 head 为 draft 且 `accepted_version_id=None`，补跑 Ch97 时又暴露 Settlement `setting_key` 非法值阻断，因此正式长跑曾顺延为 Task 113。

Task 113 首次启动长跑时在 Ch101 暴露收敛回滚与 settlement 阻断，故原长跑任务后移为 Task 114。Task 114 不承担前置修复职责，只负责规模化实跑、指标收集、报告生成和决策门判断。

## 执行顺序（必须按序）

1. **前置回归与环境确认**
   - 按 `AGENTS.md` Windows 测试进程防卡协议执行 `pytest tests/ -q`。
   - 若看到完整 `\d+ passed` summary 且无 `failed` / `error` / `errors`，但进程未退出，记录为 `PASS_WITH_TEARDOWN_TIMEOUT` 并清理残留进程。
   - 执行 `ruff check src/ tests/`，区分本 Task 新增 lint 与历史存量 lint；不得把历史存量作为启动长跑的重复阻断。
   - 确认 `git status --short` 干净，避免长跑期间混入未提交代码改动。

2. **接口与报告入口确认**
   - 通过 `songyan run --help` 或源码确认长跑 CLI 参数。
   - 通过 `python scripts/generate_streaming_report.py --help` 或源码确认报告脚本参数。
   - 确认项目 ID 为 `proj-e74ef1e4`，章节范围为 `101-150`，模式为 `webnovel_intense`，并启用 `--auto-confirm`。
   - 确认 DB、`.env`、logs 路径、checkpointer 模式和 JSONL metrics 输出位置。

3. **分段启动 Ch101-Ch150 长跑（必须按段执行，禁止一次性 50 章）**

   采用三段式推进，每段结束后必须检查 JSONL/DB 状态，确认无阻断后再进入下一段：

   - **Phase 1 — Ch102-Ch110（验证修复普适性）**
     ```bash
     songyan run --project-id proj-e74ef1e4 --chapters 102-110 --mode-id webnovel_intense --auto-confirm
     ```
     目标：确认 Task 113 的收敛回滚修复在 Ch101 之外的章节同样有效，无新的 settlement/convergence 阻断。

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

4. **流式监控与熔断条件**

   每段运行期间和结束后检查以下指标，**任一条件触发即熔断停机**：

   | 熔断条件 | 判定标准 | 停机后动作 |
   |----------|----------|-----------|
   | **Convergence + Settlement 双失败** | 任意一章 `convergence_failed=true` 且 `skip_settlement=true` | 停止后续章节，保留 run id、JSONL、DB、stdout/stderr，分析是否为 Task 113 同类问题 |
   | **连续 Settlement 失败** | 连续 3 章 `settlement_success=false`（不含明确的 `human_review` 状态） | 同上，检查是否为系统性 settlement 阻断 |
   | **硬超时** | 单段运行时间超过 4 小时（14400 秒） | 按 `AGENTS.md` 防卡协议判定，以 JSONL/DB 为准，不强制继续 |
   | **事实源污染** | 出现 `accepted_version_id` 指向 abandoned 版本、或 accepted 后无 settlement/summary 且非明确 skip | 立即停止，拆分 P0 修复任务，不继续推进 |
   | **Budget 硬门禁突破** | 任意一章 `budget_used > 1.0` 且未触发 ContextEmergency 阻断 | 记录并分析，若连续出现则停机 |

   **每段结束后的强制检查清单**：
   - [ ] 该段所有章节 JSONL 中 `success` 字段状态正常，或失败原因已记录
   - [ ] `chapter_heads.accepted_version_id` 与 JSONL 一致，无指向 abandoned 版本
   - [ ] 每章 settlement + summary 已写入（或明确标记 skip_settlement 且有 fallback）
   - [ ] `budget_used` 趋势稳定，无异常突增
   - [ ] 无残留 python/pytest/songyan 进程

5. **报告与收口**
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

- [ ] **执行 Ch101-Ch150 流式验证（三段式）**
  - Phase 1: Ch102-Ch110（验证修复普适性）
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
- 不做 Prompt 调优
- 不新增 Workflow 节点
- 不修复非阻断 P2 清理项

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

### Layer 1: 前置回归
- [ ] `pytest tests/ -q` 按 `AGENTS.md` 防卡协议执行并通过；允许记录 `PASS_WITH_TEARDOWN_TIMEOUT`
- [ ] `ruff check src/ tests/` 无本 Task 新增 lint 错误；历史存量 lint 必须在 DONE 文档中记录

### Layer 2: 长跑验证（分段验收）
- [ ] Phase 1 (Ch102-Ch110) 完成且无熔断触发，或熔断后已诊断并修复
- [ ] Phase 2 (Ch111-Ch130) 完成且无熔断触发
- [ ] Phase 3 (Ch131-Ch150) 完成且无熔断触发
- [ ] 每章都有 chapter run metrics
- [ ] 每个 accepted 章节都有 settlement + summary，除非明确 skip_settlement 且有 fallback summary
- [ ] 每段结束后执行强制检查清单并通过

### Layer 3: 报告验证
- [ ] DG-2 报告可复现统计数据
- [ ] 报告中标明失败章节、失败原因和是否可自动恢复

## 验收标准（Acceptance Criteria）

### 分段验收指标

| 指标 | Phase 1 (Ch102-Ch110) | Phase 2 (Ch111-Ch130) | Phase 3 (Ch131-Ch150) | 整体 (Ch101-Ch150) |
|------|----------------------|----------------------|----------------------|-------------------|
| 完成率 | >= 80% | >= 90% | >= 90% | >= 95%，或失败可按熔断策略诊断恢复 |
| QG 通过率 | >= 60% | >= 65% | >= 70% | >= 70% |
| `budget_used` | 每章 <= 1.0 | 每章 <= 1.0 | 每章 <= 1.0 | 每章 <= 1.0 |
| 熔断触发 | 0 次（允许 1 次诊断后修复） | 0 次 | 0 次 | 累计 <= 2 次且均已修复 |

### 整体验收指标

| 指标 | 目标 |
|------|------|
| Ch101-Ch150 运行完成率 | >= 95%，或失败可按熔断策略诊断恢复 |
| QG 通过率 | >= 70% |
| `budget_used` | 每章 <= 1.0；如超出必须触发并记录 emergency |
| ContextEmergency | 目标 0；若出现需说明触发分区和后续影响 |
| settlement validation failed | 0 个自动落库 |
| accepted 后 summary | 100% 有真实 summary 或 fallback summary |
| 无事实源污染 | `accepted_version_id` 无指向 abandoned 版本 |
| DG-2 报告 | 已生成并写入任务 DONE 文档 |

## 决策门 DG-2

- **通过**：QG 通过率 >= 70%，无 P0 状态污染，budget 稳定，进入 V5.1 文学质量与 Prompt 层优化。
- **条件通过**：QG 通过率 60%-70%，无 P0 状态污染，可进入局部 P1 修复后重跑失败窗口。
- **不通过**：QG 通过率 < 60%，或出现 accepted/settlement/summary 长期事实源污染，停止长跑并拆分 P0 修复任务。

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
