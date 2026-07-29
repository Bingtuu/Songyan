# Task 193: wuxia Ch200 爬坡

> **阶段**: V10.2 跨体裁 Ch200 爬坡
> **类型**: deterministic clean / Ch200 分段长跑 / 段边界审计
> **优先级**: P0
> **依赖**: Task 189 / Task 190 / Task 191；当前 goal 下按编号在 Task 192 之后推进
> **状态**: ◐ 进行中；已到 Ch175 accepted，Ch175 five-gate PASS、T9=0，但 segment audit FAIL，已路由 193.ad 修复
> **预计工作量**: 大

---

## Goal

对 wuxia Ch100 source 的 Ch28 省略号占位段执行 deterministic clean，重跑 T9=0 后使用 Task 191 harness 初始化 V10 Ch200 DB，并推进 Ch101-Ch200 到最终验收。

---

## Context

Task 190 已判定 wuxia 为 `BLOCKED_DIRTY_SAMPLE`：`.tmp/task172b_wuxia_ch100.db` 具备 100/100 accepted、five-gate PASS、segment audit PASS，但 T9=1。唯一已定位问题是 Ch28 的省略号占位段 `……`。V10 守护项规定 T9 是硬红线，不接受解释性豁免。

因此 Task 193 的第一阶段不是长跑，而是清洁 Ch28 并重判 T9=0。清洁必须保留版本链：不得覆盖旧 `chapter_versions.content`，必须创建新版本并事务性切换 accepted/current head。

---

## In Scope（必须完成）

- [ ] 定位 wuxia Ch28 accepted version 和 T9 命中段落，生成清洁前证据。
- [ ] 实现或使用 deterministic clean 路径移除 Ch28 省略号占位段。
- [ ] 清洁写入必须遵守版本规则：
  - 新增 `chapter_versions` 记录；
  - 不 UPDATE 旧正文；
  - 事务性更新 accepted/current head；
  - 保留旧 version 可追溯。
- [ ] 重跑 wuxia Ch100 T9，确认 meta/artifact=0、duplicate=0、timeline=0。
- [ ] 重跑 wuxia Ch100 five-gate 与 segment audit，确认 clean 后仍 PASS。
- [ ] 更新 `.tmp/190_ch100_source_inventory.json` 的 wuxia 记录，且在 DONE 文档中明确从 `BLOCKED_DIRTY_SAMPLE` 提升为可用 source 的证据。
- [ ] 使用 Task 191 harness 初始化 V10 Ch200 target DB：

```powershell
python scripts/run_v10_ch200_climb.py --init-from-source --genre wuxia --format json
```

- [ ] 使用 Task 191 harness 按 Ch125 / Ch150 / Ch175 / Ch200 分段推进：

```powershell
powershell -File scripts/run_with_timeout.ps1 -TimeoutSec <sec> -- python scripts/run_v10_ch200_climb.py --to 125 --genre wuxia
powershell -File scripts/run_with_timeout.ps1 -TimeoutSec <sec> -- python scripts/run_v10_ch200_climb.py --to 150 --genre wuxia
powershell -File scripts/run_with_timeout.ps1 -TimeoutSec <sec> -- python scripts/run_v10_ch200_climb.py --to 175 --genre wuxia
powershell -File scripts/run_with_timeout.ps1 -TimeoutSec <sec> -- python scripts/run_v10_ch200_climb.py --to 200 --genre wuxia
```

- [ ] 每个段边界执行审计，five-gate 必须显式绑定 Task 189 baseline：

```powershell
python scripts/run_v10_ch200_climb.py --audit --genre wuxia --up-to <125|150|175|200> --baseline tasks/189-scifi-ch200-baseline.json
```

- [ ] 产出 `tasks/193-wuxia-ch200-climb-DONE.md`，并同步核心入口文档。

---

## Out of Scope（明确不做）

- 不完整重建 wuxia Ch100，除非 deterministic clean 被 review 判定不可安全执行。
- 不修改 T9 检测器以放过 `……`。
- 不把 Ch28 旧 accepted version 覆盖掉。
- 不修改 wuxia profile，除非另开后缀修复任务并提供回归证据。
- 不在任一段硬门失败后继续跑下一段。

---

## 数据与路径契约

| 项 | 路径 / 口径 |
|----|-------------|
| Ch100 source DB | `.tmp/task172b_wuxia_ch100.db` |
| Ch100 source project_id | `273a8408be8e4caf8cbc1e91954da600` |
| Ch100 source run_id | `run-82968662` |
| dirty chapter | Ch28 |
| dirty issue | 省略号占位段 `……`，T9 meta/artifact=1 |
| V10 Ch200 target DB | `.tmp/task_v10_wuxia_ch200.db` |
| V10 project file | `.tmp/task_v10_wuxia_project.json` |
| V10 segment log | `.tmp/task_v10_wuxia_segments.jsonl` |
| five-gate report | `.tmp/v10_wuxia_seg<checkpoint>_five_gate.json` |
| segment audit report | `.tmp/v10_wuxia_seg<checkpoint>_audit.json` |
| metrics report | `.tmp/v10_wuxia_seg<checkpoint>_metrics.md` |
| final report | `.tmp/v10_wuxia_ch200_final.json` |
| baseline | `tasks/189-scifi-ch200-baseline.json` |

---

## 执行阶段

### 当前执行记录（2026-07-28）

- Ch28 deterministic clean/source 初始化已完成；wuxia V10 target DB 为 `.tmp/task_v10_wuxia_ch200.db`。
- Task 193.p 已完成：旧 Ch100 source 复制出的 V10 target DB 缺 LangGraph checkpoint tables 时，`prune_orphan_checkpoints()` 缺表幂等返回 0。
- Task 193.q 已完成：Ch117 `health_low_p1_halt` P1 target `broken_blade_sect_martial_arts.blood_abyss.reverse_practice` 已通过 accepted patch `fix-117-p1-193q` 修复，continuity/segment/T9 复判通过。
- 193.q 后继续使用 Task 191 harness `--to 125 --genre wuxia`：Ch118 `v-c632abb2`、Ch119 `v-7d9cc930`、Ch120 `v-0b7d1806` accepted。
- 用户要求暂停时，Ch121 已生成并修订至 `rev-121-3-5ee3b52c`，但仍 `under_review`，未 accepted；尚未到 Ch125 段边界，尚未执行 Ch125 five-gate / segment audit / metrics T9。
- run `run-v10-wuxia-5bbfab3a` 已标记 `paused`，`current_chapter=121`，completed_count=120，failed=[]，total_cost=3.159457；DB SHA256 `AEB862EF616761B4AFE5540495674AB5987A01D003E91560993F5AEE08005BF5`；暂停证据 `.tmp/193_wuxia_pause_20260728_0838.json`。

### 当前执行记录（2026-07-29，Ch150 段）

- Ch121→Ch125 resume 已完成（途中成本熔断优雅暂停 `pause_reason='cost_budget'`，提额 6.0 后 completed）；Ch125 段边界审计 five-gate/segment/T9 全 PASS。
- 继续使用 Task 191 harness `--to 150 --genre wuxia --cost-budget 10`（wrapper `run-20260729-183812490`，`PASS_NORMAL_EXIT`）：Ch126→Ch150 全部 accepted，failed=[]，run final_status=completed @150，total_cost=8.035272；Ch150 accepted/current head=`v-a3a9083f`。
- Ch150 段边界审计初判：five-gate PASS（显式绑 `tasks/189-scifi-ch200-baseline.json`），但 segment audit FAIL：`critical_orphans=2`、`halt_would_fire=true`、`next_audit_chapter=153`。
- Task 193.x 已完成：2 条 critical tracking（`blood_abyss.reverse_practice`、`blood_sacrifice.complete_manual`）经 Ch149/Ch150 正文承接证据（天罡正气/血纹/三道弧线符号，逐字验证 6/6）后用 `promote_to_active()` 刷新到 Ch150 `v-a3a9083f`；复判 segment audit PASS（critical_orphans=0、halt=false）。DONE `tasks/193.x-wuxia-ch150-segment-audit-critical-orphans-DONE.md`。
- Task 193.y 已完成：193.x 后 T9 复判发现 Ch145 accepted `v-f581c63b` 第 85 段逐字重复第 30 段（duplicate=1），经 `apply_chapter_text_cleaning()` 版本化 clean 为 `clean-145-6-c534f0e7`；复判 T9=0、five-gate PASS、segment audit PASS。DONE `tasks/193.y-wuxia-ch145-t9-duplicate-clean-DONE.md`。
- 至此 Ch150 段边界审计三项全 PASS；下一步 `--to 175` 后执行 Ch175 段审计。

### 当前执行记录（2026-07-29，Ch155 blocker / 193.z）

- 使用 Task 191 harness 从 Ch150 继续执行 `--to 175 --genre wuxia --cost-budget 14`（wrapper `run-20260729-213157512`，显式 `LLM_MODEL=deepseek/deepseek-v4-flash`）。
- Ch151、Ch152、Ch153、Ch154 均 accepted；Ch153 曾触发 rewrite，最终 accepted settlement version `v-142b4ce3`。
- Ch155 二轮修订版本 `rev-155-3-9ac1de69` 的 RuleAuditor 已清洁且 mandatory reference PASS，但 LLMAuditor 返回空内容，JSON 标准解析与 repair 均失败：

```text
llm_auditor_node.audit_failed chapter_number=155 error='LLM 返回内容无法解析为 JSON（标准解析和 repair 均失败）' version_id=rev-155-3-9ac1de69
project_pipeline.chapter_failed chapter_number=155 error='LLM audit failed: LLM 返回内容无法解析为 JSON（标准解析和 repair 均失败）'
```

- pipeline isolate 继续进入 Ch156 前置；为避免扩大 gap 与继续消耗成本，已人工中止外部进程，并用 `ProjectRunRepository.update()` 将 run 冻结为 `status=paused`、`pause_reason=user_requested`、`current_chapter=155`、`failed_chapters=[155]`。
- 冻结后状态：accepted_count=154，run total_cost=8.796384；冻结目录 `.tmp/backups/193z_wuxia_ch155_llm_auditor_json_parse_20260729-220836/`。
- 已创建 blocker 任务书：`tasks/193.z-wuxia-ch155-llm-auditor-json-parse.md`；修复前不得继续 Ch156+。

### 当前执行记录（2026-07-29，Ch155 修复完成 / 193.z + 193.aa）

- Task 193.z 已完成：使用单章 resume 脚本 `.tmp/run_193z_ch155_resume.py` 重跑 Ch155，wrapper `run-20260729-221336654` `PASS_NORMAL_EXIT`；pipeline `completed=[155]`、`failed=[]`、`final_status=completed`，final accepted settlement version `v-3af05880`。
- 单章 runner 结束后，已用 `ProjectRunRepository.update()` 将 `project_runs.completed_chapters` 恢复为 1..155、`failed=[]`、`status=completed`、`current_chapter=155`。
- post-fix five-gate @155 PASS，但 segment audit @155 初判 `critical_orphans=1`、`halt_would_fire=true`，目标为 `broken_blade_sect_location_cave_altar.blood_lock.tie_bloodline`；已冻结现场 `.tmp/backups/193aa_wuxia_ch155_segment_critical_orphan_20260729-2230/` 并路由 193.aa。
- Task 193.aa 已完成：创建 Ch155 accepted continuity patch `fix-155-segment-193aa`（parent `v-3af05880`），补回“义庄地下洞窟祭坛 / 白骨 / 铁氏嫡系血脉锁 / 密室裂缝”正文承接，并通过 `SettingTrackingRepository.promote_to_active()` 刷新目标 tracking 到 Ch155。
- 最终状态：Ch155 accepted/current head=`fix-155-segment-193aa`；run `run-v10-wuxia-5bbfab3a` completed @155、failed=[]、total_cost=9.05207；five-gate @155 PASS、segment audit @155 PASS（critical_orphans=0、halt=false）、T9=0。
- 下一步继续使用 Task 191 harness 从 Ch156 推进到 Ch175；真实 `--to` 必须带 `--cost-budget` 或 `SONGYAN_RUN_COST_BUDGET`，到 Ch175 后先审计再继续。

### 当前执行记录（2026-07-29，Ch162 修复完成 / 193.ab + 193.ac）

- 继续使用 Task 191 harness 从 Ch155 执行 `--to 175 --genre wuxia --cost-budget 15`（wrapper `run-20260729-223717368`，显式 `LLM_MODEL=deepseek/deepseek-v4-flash`）。
- Ch156-Ch162 accepted；Ch156/157 曾进入 rewrite 才通过，Ch158-Ch161 accepted 后继续，Ch162 accepted/current 初始 head=`v-b786a6f6`。
- Ch162 结算与 continuity audit 后触发 `health_low_p1_halt: P1_count=1 (critical orphaned setting)`，run 自动暂停，accepted_count=162、failed=[]、pause_reason=`auto_halt:chapter_gate`、total_cost=10.29487。
- Task 193.ab 已完成：创建 direct P1 patch `fix-162-p1-193ab`（parent `v-b786a6f6`），补回《血祭刀诀》完整秘录、血祭三转、天罡正气与血脉为桥承接，刷新 `blood_sacrifice.complete_manual` 到 Ch162。post-fix segment audit 仍发现 `blood_abyss.reverse_practice` critical orphan。
- Task 193.ac 已完成：创建 segment patch `fix-162-segment-193ac`（parent `fix-162-p1-193ab`），将“反练”明确为“血引归墟反练”，刷新 `blood_abyss.reverse_practice` 到 Ch162。
- 最终状态：Ch162 accepted/current head=`fix-162-segment-193ac`；run completed @162、failed=[]、total_cost=10.29487；five-gate @162 PASS、segment audit @162 PASS（critical_orphans=0、halt=false）、T9=0。
- 下一步继续 Task 191 harness 从 Ch163 推进到 Ch175；真实 `--to` 必须带 `--cost-budget` 或 `SONGYAN_RUN_COST_BUDGET`，到 Ch175 后先审计再继续。

### 当前执行记录（2026-07-30，Ch175 segment audit blocker / 193.ad）

- 使用 Task 191 harness 从 Ch162 执行 `--to 175 --genre wuxia --cost-budget 16`（wrapper `run-20260729-234725258`，显式 `LLM_MODEL=deepseek/deepseek-v4-flash`）。
- Ch163-Ch175 全部 accepted；run `run-v10-wuxia-5bbfab3a` completed @175、failed=[]、total_cost=12.781521；Ch175 accepted/current head=`v-6b82012e`。
- Ch175 checkpoint audit 显式绑定 `tasks/189-scifi-ch200-baseline.json`：five-gate PASS（budget=0.9646、CED/1k=0.1553、overdue=143、health=9.1、accepted=175/gap=0），metrics/T9=0。
- Segment audit @175 FAIL：`critical_orphans=1`、`total_orphans=49`、`halt_would_fire=true`、`next_audit_chapter=177`。
- 唯一 critical target：`broken_blade_sect_location_cave_altar.blood_lock.tie_bloodline`（`洞窟祭坛血纹·铁氏血脉锁`），tracking_id=`track-273a8408be8e4caf8cbc1e91954da600-5b381892`，last_mentioned=Ch173。
- 已冻结现场：`.tmp/backups/193ad_wuxia_ch175_segment_critical_orphan_20260730-0140/`；任务书 `tasks/193.ad-wuxia-ch175-segment-critical-orphan.md`。
- 修复完成前禁止继续 Ch176+。

### A. Ch28 deterministic clean

1. 只读查询 Ch28 accepted version、正文 hash、命中段落。
2. 生成清洁候选正文：只移除占位段，不改写整章，不改变叙事内容。
3. 通过 service / repository / UnitOfWork 或受控脚本创建新 `chapter_versions`，事务性更新 `chapter_heads.accepted_version_id` 和 `current_version_id`。
4. 记录旧 version_id、新 version_id、正文 hash diff、命中段落前后对照。

### B. Ch100 clean 复核

必须重跑：

- T9 meta/artifact、duplicate、timeline；
- five-gate `--up-to 100`；
- segment audit `--up-to 100`；
- profile show/diff，确认无意外 override。

通过后，更新 source inventory 中 wuxia verdict 为可初始化状态，并记录 clean 证据。

### C. Ch200 初始化与分段推进

1. 使用 `scripts/run_v10_ch200_climb.py --init-from-source --genre wuxia` 初始化 V10 DB。
2. 依次推进 Ch125、Ch150、Ch175、Ch200。
3. 每段结束先审计再继续。

### D. 收口

DONE 文档至少记录：

- Ch28 clean 前后证据；
- 新旧 `chapter_versions` 和 head 切换记录；
- Ch100 clean 复核；
- Ch200 每段 accepted、budget、CED、overdue、health、T9、segment audit；
- 成本、wrapper 结果、run_id；
- 是否有后缀修复任务。

---

## 失败路由

| 失败点 | 处理 |
|--------|------|
| Ch28 命中不止已知占位段 | 暂停 deterministic clean，开 `193.p` 诊断 |
| clean 后 T9 仍 > 0 | 冻结 clean 版本，定位新增命中，不进入 Ch200 |
| clean 后 five-gate 或 segment audit 失败 | 回查是否 clean 破坏正文/状态；必要时开后缀修复 |
| `--init-from-source` 拒绝 source | 修复 source inventory / genre / T9 / accepted head，不绕过 harness |
| Ch125/150/175/200 任一五门失败 | 冻结现场，开 `193.<suffix>` 修复，不推进下一段 |
| wrapper 超时或成本熔断 | 记录 `WRAPPER_RESULT`、成本状态和 resume 命令，低频监控后继续 |

---

## Review 要求

完成前必须自查：

- 是否创建新 `chapter_versions` 而非覆盖旧正文；
- 是否只做局部 deterministic clean，没有整章重写；
- 是否 clean 后 T9=0 是真实复算结果；
- 是否 source inventory 与 DONE 文档一致；
- 是否所有 Ch125+ five-gate 都显式传入 Task 189 baseline；
- 是否没有为了过关修改 T9/CED/five-gate 口径。

---

## 测试与验证要求

若新增 clean 工具或写路径，必须补测试覆盖：

- 新版本创建，不覆盖旧 version；
- head 切换事务一致；
- T9 dirty -> clean；
- 错误 project_id / chapter / missing accepted version 拒绝。

常规代码改动必须执行：

```powershell
powershell -File scripts/run_with_timeout.ps1 -TimeoutSec 2400 -- python -m pytest tests/ -q
ruff check src/ tests/
git diff --check
```

长跑段边界至少执行：

```powershell
python scripts/run_v10_ch200_climb.py --audit --genre wuxia --up-to <checkpoint> --baseline tasks/189-scifi-ch200-baseline.json
```

影响 harness、five-gate、segment audit 或 Ch200 口径时，必须重放 Task 189 Ch125/150/175/200 baseline。

---

## 验收标准

- [ ] Ch28 dirty sample 已用版本化方式 clean，旧版本可追溯。
- [ ] wuxia Ch100 source 复核 T9=0，five-gate PASS，segment audit PASS。
- [ ] `.tmp/190_ch100_source_inventory.json` 与 DONE 文档同步登记 wuxia 可用 source。
- [ ] `.tmp/task_v10_wuxia_ch200.db` 初始化自 clean Ch100 source，且 V10 `project_runs` 独立。
- [ ] Ch1-Ch200 全 accepted。
- [ ] Ch125 / Ch150 / Ch175 / Ch200 four checkpoints 五门 PASS。
- [ ] Ch200 T9=0；segment audit PASS。
- [ ] DONE 文档和核心入口已更新。
- [ ] 验证命令通过，提交一次，不 push。

---

## 参考文档

- `tasks/189-ch200-baseline-and-checkpoints-DONE.md`
- `tasks/189-scifi-ch200-baseline.json`
- `tasks/190-ch100-terminal-source-inventory-DONE.md`
- `tasks/191-ch200-harness-preparation-DONE.md`
- `archive/v8/tasks/172c-wuxia-ch100-clean-rerun-DONE.md`
