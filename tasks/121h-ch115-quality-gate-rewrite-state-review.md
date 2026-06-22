# Task 121h: Ch115 Quality Gate / Best-Version Rewrite Contract Fix

> **日期**: 2026-06-22
> **类型**: V5.1 preflight / single-run blocker engineering fix
> **状态**: DONE
> **前置**: Task 121g 已完成 `run-0fd1456e` Ch1-Ch150 single-run 重跑，Ch1-Ch114 成功，Ch115 因 quality gate human review 阻断。

---

## 1. 任务边界

本任务目标是 review 并修复 Task 121g 暴露的 Ch115 quality gate / rewrite 状态生命周期和 best-version 保护问题，为下一次 Ch1-Ch150 single-run 提供可验证的工程闭环。

本任务聚焦：

- 复盘 `run-0fd1456e` 中 Ch115 的状态流和版本流。
- 明确 rewrite 后 `_new_issues_introduced`、`_quality_gate_failures`、`_convergence_failed`、`_settlement_needs_human_review` 的生命周期。
- 确认 quality gate 对当前最终版本的判断不会被旧 revision/rewrite 状态污染。
- 修复高分 best version 被低质量 rewrite / hard truncate 产物覆盖或绕过的问题。
- 复核 rewrite 超长输出、截断版本创建、score card 和 `current_version_id` 的一致性。
- 交付聚焦测试和可供 Task 121i 验证的修复。

不做：

- Prompt 大调优。
- 放宽 QualityGate 阈值。
- 修改 SettlementExtractor 事实校验规则。
- 新增 workflow 节点。
- 将 Task 121g partial 结果包装为 Ch1-Ch150 完成证据。
- 直接启用 ContextEmergency / health_low 硬门禁。
- 直接执行新的 Ch1-Ch150 full single-run；该步骤归 Task 121j。
- 进行全书 Prompt 大调优；该步骤归 Task 121k。

---

## 2. 事实入口

| 类型 | 路径 / ID |
|------|-----------|
| 上一轮任务文档 | `tasks/121g-ch1-ch150-single-run-rerun-ch115-blocker-DONE.md` |
| run_id | `run-0fd1456e` |
| project_id | `7950dbf3b70c468695e5bfe528d66acf` |
| JSONL | `logs/chapter_runs/run-0fd1456e.jsonl` |
| wrapper stdout | `logs/task121g/songyan-task121g-ch1-ch150-full-single-run-20260621-203623.out.log` |
| wrapper stderr | `logs/task121g/songyan-task121g-ch1-ch150-full-single-run-20260621-203623.err.log` |
| wrapper result | `logs/task121g/songyan-task121g-ch1-ch150-full-single-run-20260621-203623.result.txt` |
| 状态文档 | `docs/STATUS.md` |
| V5 事实索引 | `tasks/V5-README.md` |

---

## 3. 上一轮测试结论

Task 121g 的 single-run 结果为 `partial`。

| 项 | 结果 |
|----|------|
| completed_chapters | Ch1-Ch114 |
| failed_chapters | `[115]` |
| 首个失败点 | Ch115 |
| final_status | `partial` |
| wrapper result | `WARN_BUSINESS_DONE_WITH_ERROR` |

已确认越过的历史阻断：

- Ch5 rewrite fallback settlement skip 阻断已解除。
- Ch8 settlement 伏笔同章预计回收阻断已解除。
- Ch18 CreativeDirector stale error 状态污染阻断已解除。

Ch115 失败表象：

```text
success=false
error_stage=human_review_required
settlement_success=false
settlement_needs_human_review=true
summary_id=null
summary_success=false
skip_settlement=false
```

关键判断：

- Ch115 不是 SettlementExtractor 自身校验失败。
- 日志未出现 `settlement_extractor_node.contract_snapshot`、`settlement.validation_failed`、`settlement.applied`。
- 实际阻断发生在 settlement 前，由 quality gate 将状态路由到 `human_review_required`。

---

## 4. Ch115 阻断链路

日志中的核心链路：

```text
Ch115 初稿 3288 字
-> 两轮 revision 后进入 rewrite
-> rewrite 输出 7771 字
-> writer 截断到 6062 字
-> rewrite hard truncate 到 4200 字
-> quality_gate_passed=false
-> convergence_failed=true
-> _new_issues_introduced 非空
-> status=human_review_required
-> 未进入 settlement_extractor
-> run partial
```

Ch115 score card：

```text
overall_score=0.7335
length=0.6
budget=0.7058
coherence=0.85
momentum=0.8
readability=0.6315
critical=0
```

判断：

- `overall_score=0.7335`，质量没有整体崩溃。
- 直接阻断是 quality gate human review，不是 settlement validation。
- 主要工程疑点是 rewrite 后旧 revision 的 `_new_issues_introduced` 可能污染最终版本的质量门判断。
- 主要质量风险是 rewrite 字数失控、硬截断后的结构风险、readability 偏低。

补充质量复盘结论：

```text
v-115-1      3288 字 overall=0.8422
rev-115-2    3224 字 overall=0.8468
rev-115-3    3493 字 overall=0.8776  <- 高分 best 候选
rewrite      7771 字
截断         6062 字
hard truncate 4200 字 overall=0.7335 <- 最终阻断版本
```

因此，Ch115 不是“没有可用版本”。它在 `rev-115-3` 已产生高分、字数健康的 best 候选，随后进入整章 rewrite，rewrite 超长并经截断后显著劣化。Task 121h 必须同时处理状态污染和 best-version 保护，不能只清理 `_new_issues_introduced`。

---

## 5. Review 问题清单

### 5.1 P1：rewrite 后状态污染

需要确认：

- `rewrite_node` 成功生成新版本后，是否清理旧 `_new_issues_introduced`。
- hard truncate 创建新版本后，旧 `_quality_gate_failures` 是否仍然保留。
- 最终版本重新审查后，`_new_issues_introduced` 是否只代表当前版本相对上一轮审查真正新增的问题。
- `review_merger_node` 已覆盖的 stale state 清理契约，是否同样覆盖 rewrite 后路径。

预期契约：

- 当前最终版本无新引入问题时，`_new_issues_introduced` 必须为空列表或 `None`。
- 旧 revision 的 new issues 不得跨版本污染 rewrite 后的 final quality gate。
- 若最终版本确实引入新问题，必须保留 evidence 并进入 `human_review_required`。

### 5.2 P1：quality gate 版本一致性

需要确认：

- `current_version_id`、`_score_card`、`_best_version_id`、`_best_score_card` 是否指向同一判定语境。
- hard truncate 新建版本后，score card 是否对应截断后的版本，而不是被截断前的版本。
- `quality_gate_node` 中 `has_new_issues` 的判断是否仅针对当前版本。
- `quality_gate_router` 对 `human_review_required` 的 blocked 路由是否仍符合 Task 111d 契约。

预期契约：

- quality gate 的所有失败原因都应能追溯到当前 `current_version_id`。
- 当前版本可安全结算且没有当前版本 new issues 时，不应因 stale state 阻断 settlement。

### 5.3 P2：rewrite 字数失控与硬截断风险

需要确认：

- rewrite prompt 已注入 `2800 ~ 4200` 字硬约束，但 Writer 仍输出 7771 字的原因。
- writer 截断到 6062 后，rewrite hard truncate 到 4200 是否可能破坏结构完整性。
- hard truncate 后的 scene count、opening hook、ending hook 是否被重新校验。
- Ch115 的 4200 字版本是否存在段落碎片化、语义断裂或钩子损伤。

预期契约：

- 超长 rewrite 不应直接污染 accepted head。
- 截断版本必须作为新版本记录，不能覆盖原版本。
- 截断后必须经过结构完整性和 quality gate 检查。
- 截断版本质量低于 active best 时，必须回滚到 best，而不是继续使用截断版本进入最终质量门。

### 5.4 P1：高分 best-version 保护

需要确认：

- `rev-115-3` 这类高分 best 候选在进入 rewrite 前是否被正确记录为 `_best_version_id` 和 `_best_score_card`。
- 2 轮 revision 后仍有 major issue 时，是否应该无条件进入整章 rewrite。
- rewrite 产物低于 best 明显阈值时，是否自动废弃 rewrite 并恢复 best。
- best 版本未完全 QG pass 但具备安全结算条件时，是否应走 `human_confirm -> settlement`，而不是继续高风险 rewrite。

预期契约：

- 若 active best 满足 `overall >= 0.82`、`length_ok=true`、`budget_ok=true`、无 critical issue，整章 rewrite 不得覆盖该 best。
- 若 rewrite / hard truncate 版本比 best 低超过 `0.08`，自动 abandon rewrite 并恢复 best。
- 如果 best 仍有 non-critical major issue，允许记录 `_convergence_failed=True`，但在 `skip_settlement=false` 且事实源安全时继续 settlement。
- rewrite 是救灾手段，不是覆盖高分 best 的默认路径。

### 5.5 P2：中后段质量退化信号

需要纳入 review，但不作为本任务首要修复项：

- Ch114 readability 已降到 `0.484`，但章节仍完成 settlement 和 summary。
- Ch115 readability 为 `0.6315`，接近质量风险区间。
- Ch111-Ch115 附近存在 convergence_failed 和 QG false 但仍可 settlement 的情况。
- 前序抽查发现正文元标记泄漏和机械化场景标题风险。

预期处理：

- 作为 V5.1 Prompt 调优输入，不在 Task 121h 中扩展为大范围 Prompt 重写。

---

## 6. 代码 Review 入口

优先 review：

| 文件 | 关注点 |
|------|--------|
| `src/songyan/workflows/_nodes.py` | `rewrite_node`、`review_merger_node`、`quality_gate_node`、`human_gate_node` |
| `src/songyan/workflows/phase1_graph.py` | `quality_gate_router`、`rewrite_router` |
| `src/songyan/workflows/phase2_graph.py` | 单章终态判定、error/stale state 处理 |
| `src/songyan/workflows/_run_logger.py` | `convergence_failed`、`skip_settlement`、`settlement_success` 日志口径 |
| `src/songyan/services/revision_handler.py` | `_detect_new_issues` 当前版本语义 |
| `src/songyan/services/review_merger.py` | previous new issues 合并与清理语义 |

优先测试入口：

| 文件 | 关注点 |
|------|--------|
| `tests/test_108_core_nodes.py` | stale state 清理、best rollback、core node 契约 |
| `tests/test_rewrite_node.py` | rewrite 字数约束、hard truncate、avoid list |
| `tests/test_phase1_graph.py` | quality gate / rewrite / blocked 路由 |
| `tests/test_107_convergence_guardrail.py` | convergence failed、fallback settlement 契约 |
| `tests/test_revision_handler.py` | new issues detection |
| `tests/test_review_merger.py` | previous new issues merge |

---

## 7. 执行步骤

### Step 1：证据复盘

从 `run-0fd1456e` 提取 Ch111-Ch115 状态变化：

- 每章 `success`、`quality_gate_passed`、`convergence_failed`、`skip_settlement`。
- Ch115 各版本的 `version_id`、`version_number`、`word_count`、`score_card`。
- Ch115 revision/rewrite 后 `_new_issues_introduced` 的来源、内容和对应版本。
- Ch115 是否存在可回滚的 active best version。

输出：

- Ch115 状态流表。
- Ch115 版本流表。
- 明确判断：阻断由当前版本真实 new issues 引起，还是 stale state 污染引起。

### Step 2：代码路径 review

按以下路径审查状态传递：

```text
revision_handler
-> review_merger_node
-> quality_gate_node
-> rewrite_node
-> rule_auditor / llm_auditor
-> review_merger_node
-> quality_gate_node
-> quality_gate_router
-> human_gate_node / settlement_extractor_node
```

重点确认：

- rewrite 成功后是否重置 revision-only 状态。
- review merger 是否在 best rollback 时清理 stale QG 状态。
- quality gate 对 `_new_issues_introduced` 的处理是否有版本归属。
- human gate 是否可能把 stale `_settlement_needs_human_review=True` 透传到 run logger。

### Step 3：最小工程修复

修复原则：

- 保持 Task 111d 契约：真实 new issues 必须阻断自动化并上报人工。
- 保持 Task 121c 契约：`_skip_settlement` 只表示没有可安全结算正文。
- 不通过放宽 QG 或忽略 new issues 来跑通。
- 不覆盖旧版本，所有 rewrite/truncate 结果必须创建新 `chapter_versions` 记录。

候选修复方向：

- rewrite 成功生成当前版本后，清理旧 `_new_issues_introduced`、旧 `_quality_gate_failures`、旧 `_settlement_needs_human_review`。
- hard truncate 新版本创建后，确保后续审查和 score card 均绑定新版本。
- quality gate 检查 new issues 时增加版本语义，避免跨版本 stale issues。
- 增加 best-version 保护：高分 best 存在时，rewrite 结果不得覆盖更优 best。
- 增加 rewrite 降级回滚：rewrite / hard truncate 分数显著低于 best 时，废弃 rewrite 并恢复 best。
- 在 run logger 或节点日志中增加可观测字段，暴露 new issues 来源版本。

### Step 4：聚焦测试

至少补充或更新测试：

- rewrite 成功后不会继承旧 `_new_issues_introduced`。
- hard truncate 后新版本不会继承旧 quality gate failures。
- 当前版本无 new issues 时，quality gate 不会因 stale state 进入 `human_review_required`。
- 当前版本确有 new issues 时，仍进入 `human_review_required`，且不执行 settlement。
- rollback 到 QG passed best version 时，清理 stale settlement review 标记。
- 高分 best 存在时，低分 rewrite / hard truncate 产物不得覆盖 best。
- `overall >= 0.82`、无 critical、事实源安全的 best 版本可进入 human_confirm / settlement，并保留 `_convergence_failed` 诊断。

建议先跑：

```powershell
python -m pytest tests/test_108_core_nodes.py tests/test_rewrite_node.py tests/test_phase1_graph.py tests/test_107_convergence_guardrail.py -q
ruff check src/songyan/workflows/_nodes.py src/songyan/workflows/phase1_graph.py tests/test_108_core_nodes.py tests/test_rewrite_node.py tests/test_phase1_graph.py tests/test_107_convergence_guardrail.py
```

通过后再跑：

```powershell
python -m pytest tests/ -q
ruff check src/ tests/
```

### Step 5：交付给 Task 121i

本任务不直接承担 full single-run。完成后交付：

- 代码修复。
- 聚焦测试结果。
- Ch115 版本选择 / 状态生命周期复盘结论。
- Task 121i 所需的验证命令和预期结果。

---

## 8. 验收标准

本任务完成需满足：

- Ch115 根因有证据结论：真实当前版本 new issues 或 stale state 污染，二者必须明确区分。
- 相关代码修复有聚焦测试覆盖。
- 聚焦测试通过。
- 全量 `pytest` 和 `ruff` 通过，或明确记录非本任务引入的已知 xfail/环境限制。
- 明确证明高分 best 不会被低质量 rewrite / hard truncate 覆盖。
- 产出 Task 121i 的 Ch115 聚焦验证入口。
- 更新 `docs/STATUS.md`、`tasks/V5-README.md`，并在完成后将本文状态改为 DONE 或新增 `121h-...-DONE.md`。

---

## 8.1 完成记录

Task 121h 已完成工程修复和验证。

代码修复：

- `rewrite_node` 成功生成 rewrite / hard truncate 当前版本后，统一清理旧 `_new_issues_introduced`、`_quality_gate_failures`、`_settlement_needs_human_review`、`_skip_settlement`、`_convergence_failed` 和旧 `_score_card`。
- `revision_handler_node` 为 `_new_issues_introduced` 增加 `_new_issues_version_id` / `version_id` 归属。
- `review_merger_node` 和 `quality_gate_node` 只消费当前版本的 new issues，避免旧 revision/rewrite 状态污染当前最终版本。
- 增加低质量 rewrite 保护：当 active best 满足 `overall >= 0.82`、`length_ok=true`、`budget_ok=true`、无 critical issue，且 rewrite / hard truncate 分数低于 best 超过 `0.08` 时，自动 abandon 当前 rewrite 并恢复 best。
- `Phase1State` 增加 `_new_issues_version_id`，让状态归属可观测。

测试覆盖：

- rewrite 成功后不继承旧 revision/QG/settlement 状态。
- stale versioned new issues 不再触发当前版本 quality gate human review。
- 高分 safe best 不会被低质量 rewrite 覆盖，即使 rewrite 当前无 major issue。
- 既有 best rollback、结构失败回滚、quality gate 路由契约保持通过。

验证结果：

```powershell
python -m pytest tests/test_108_core_nodes.py tests/test_rewrite_node.py tests/test_107_convergence_guardrail.py tests/test_phase1_graph.py -q
# 82 passed

ruff check src/songyan/workflows/_nodes.py src/songyan/workflows/phase1_graph.py tests/test_108_core_nodes.py tests/test_rewrite_node.py tests/test_107_convergence_guardrail.py tests/test_phase1_graph.py
# All checks passed!

python -m pytest tests/ -q
# 1724 passed, 1 xfailed, 1 xpassed, 14 warnings

ruff check src/ tests/
# All checks passed!
```

交付给 Task 121i 的预期：

- Ch115 若再次出现 `rev-115-3` 级别 safe best，低质量 rewrite / hard truncate 不应覆盖该 best。
- 若当前最终版本没有当前版本 new issues，不应因 stale `_new_issues_introduced` 进入 `human_review_required`。
- 若当前版本真实引入 new issues，仍应保留 evidence 并阻断自动化。

---

## 9. 风险与非目标

### 风险

- 若 Ch115 确实存在当前版本新问题，而非 stale state，修复状态生命周期后仍可能被质量门阻断。
- rewrite 字数失控可能是 Prompt 层问题，Task 121h 只处理工程契约，不保证一次修复叙事质量。
- hard truncate 虽可控字数，但可能造成结构或语义损伤，需要通过 QG 和人工抽查确认。

### 非目标

- 不把所有 `convergence_failed=true` 视为章节失败；只要存在可安全结算版本，仍允许 settlement。
- 不把 ContextEmergency 作为本任务阻断条件。
- 不处理全书 Prompt 风格问题，相关内容后置到 V5.1 Prompt 调优任务。

---

## 10. 预期后续

Task 121h 完成后进入以下任务链：

1. Task 121i：Ch115 聚焦验证与 Ch111-Ch115 质量窗口复核。
2. Task 121j：修复后新的 Ch1-Ch150 full single-run。
3. Task 121k：Prompt / 正文质量清洗，处理机械场景标题、元标记泄漏、短段落碎片化和说明文堆叠。
