# Task 112: Task 113 前置阻断修复

> **Phase**: V5.0 Phase 4 — 150 章规模化验证前置准备
> **优先级**: P0
> **依赖**: Task 111a-111g 完成
> **预计工作量**: 0.5-1 天

---

## Goal

在正式启动 Ch101-Ch150 长跑前，修复 Task 113 前置检查暴露的 P0 阻断项，恢复 Ch97 的 accepted + settlement + summary 基线，确保 Task 113 的输入状态干净、指标可信、失败可诊断。

## Context

Task 111a-111g 完成后，按计划准备启动 Ch101-Ch150 流式验证。基线检查发现：

- Ch97 当前 `chapter_heads.status=draft`，`accepted_version_id=None`。
- 历史上 Ch97 曾有 accepted 版本，但后续补跑生成了新的 draft head，运行中断后没有完成 accept。
- Ch97 单章补跑时触发 Settlement validation failed，原因是 `new_setting.setting_key` 出现非法值：`e.0.实验室.位置与历史`。
- Task 113 长跑必须依赖 Ch1-Ch100 accepted 基线，不能带着 Ch97 缺口继续。

因此原 Task 112 “Ch101-Ch150 流式验证 + 决策门 DG-2” 顺延为 Task 113；当前 Task 112 只处理前置阻断修复和 Ch97 基线恢复。

## In Scope（必须完成）

- [ ] **确认 Ch97 阻断证据**
  - 记录 Ch97 当前 head 状态、latest run 状态和失败原因
  - 确认失败来自 settlement key validation，而不是正文质量 reject
  - 确认没有残留 Python/pytest/long-run 进程占用 SQLite

- [ ] **修复 QualityGate budget 硬门禁**
  - `ScoreAggregator` 必须从 `_context_metrics.budget_used` 或等效轻量字段读取预算
  - 当 `budget_used > 1.0` 时必须阻塞 accept
  - 不能依赖 LangGraph state 中完整 `context_package`

- [ ] **修复 Settlement `setting_key` 规范化**
  - 对 LLM 输出的非法 key 做统一归一
  - 覆盖中文、数字开头、点号异常、混合路径等输入
  - 归一后仍必须满足数据库唯一性和 schema 校验
  - validation failed 的 settlement 不得落库

- [ ] **恢复 Ch97 accepted 基线**
  - 使用 `proj-e74ef1e4`
  - 补跑 Ch97 单章
  - 确认 `chapter_heads.accepted_version_id` 非空
  - 确认 accepted 后 settlement 和 summary 均存在

- [ ] **同步任务边界**
  - 更新 `docs/STATUS.md`
  - 更新 `README.md`
  - 更新 `docs/INDEX.md`
  - 将正式 Ch101-Ch150 长跑文档后移为 Task 113

## Out of Scope（明确不做）

- 不启动 Ch101-Ch150 正式长跑
- 不做 Prompt 调优
- 不新增 Workflow 节点
- 不手工直接改 DB 来伪造 Ch97 accepted 状态
- 不修复非阻断 P2 清理项或历史文档格式问题

## 接口契约

```bash
songyan run --project-id proj-e74ef1e4 --chapters 97-97 --mode-id webnovel_intense --auto-confirm
```

```bash
python -m pytest <相关测试> -q
```

Windows 下测试必须遵守 `AGENTS.md` 的 “Windows 测试进程防卡协议”，优先使用 PowerShell Job + 硬超时 wrapper，区分测试断言通过和 teardown/后台资源释放卡住。

## 数据模型

不新增业务模型。允许在既有 parser/validator/repository/service 边界内修复 `setting_key` 规范化逻辑和 QG budget 判定逻辑。

## 测试要求

### Layer 1: 单元/契约测试
- [ ] 覆盖 budget 超限必须阻塞 accept
- [ ] 覆盖 `_context_metrics.budget_used` 可在无完整 `context_package` 时生效
- [ ] 覆盖非法 `setting_key` 输入归一化，例如 `e.0.实验室.位置与历史`
- [ ] 覆盖 validation failed settlement 不落库

### Layer 2: 相关回归
- [ ] 使用防卡 wrapper 跑相关测试文件
- [ ] 如执行全量测试，必须按 `AGENTS.md` 防卡协议处理 Windows teardown 卡住

### Layer 3: Ch97 验证
- [ ] Ch97 单章补跑完成
- [ ] Ch97 head `accepted_version_id` 非空
- [ ] Ch97 settlement 存在且 validation passed
- [ ] Ch97 summary 存在

## 验收标准（Acceptance Criteria）

| 指标 | 目标 |
|------|------|
| Ch97 当前状态 | accepted/current head 一致，`accepted_version_id` 非空 |
| Ch97 settlement | validation passed；无非法 `setting_key` 落库 |
| Ch97 summary | accepted 后 100% 存在真实 summary 或 fallback summary |
| Budget QG | `budget_used > 1.0` 必须阻塞 accept |
| State 边界 | 不把完整 `ContextPackage` 放回 LangGraph state |
| Windows 测试执行 | 防卡 wrapper 输出可解释结果，不无限轮询 |

## 决策门

- **Go Task 113**：Ch97 accepted + settlement + summary 全部恢复；相关测试通过；无新增 P0 状态污染。
- **Hold**：Ch97 仍为 draft、settlement 仍失败、summary 缺失，或 budget QG 仍无法阻塞超限 accept。
- **Split Fix**：发现新的 P0 阻断项，拆出独立修复任务，不启动 Task 113 长跑。

## 验收标准（工程流程）

- [ ] 生成 `tasks/112-preflight-blocker-fix-DONE.md`
- [ ] 更新 `docs/STATUS.md`
- [ ] 更新 `README.md`
- [ ] 更新 `docs/INDEX.md`
- [ ] Git commit 包含代码修复、测试、DONE 文档和状态更新

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
- `tasks/113-ch101-ch150-streaming-validation.md` — Ch101-Ch150 流式验证与 DG-2 规划
