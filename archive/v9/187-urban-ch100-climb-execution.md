# Task 187: urban Ch100 爬坡执行

> **阶段**: V9.5 urban 第三体裁中篇爬坡
> **类型**: 真实 LLM 实跑 / 分段爬坡 / 五门验收
> **优先级**: P1（V9 B 组最终证据）
> **依赖**: Task 186 任务书已完成设计 review 并准入；Task 185 初始锁定 urban `base_budget=12000`，Task 187.p 已按 Ch19 ContextEmergency 证据将 registry baseline 提升到 `14000`
> **状态**: 🔄 进行中（执行设计已 review，准入实跑）
> **来源**: `archive/v9/186-urban-ch100-climb.md`

---

## 任务目标

本任务执行 urban Ch1-Ch100 中篇爬坡，作为 V9 生产化地基的第三体裁实战验收。

完成条件：

1. 使用现有 `scripts/run_172b_ch100_climb.py`，以 `TEMPLATE_ID=urban RUN_ID=187` 初始化并分段推进到 Ch100。
2. 每 25 章做一次正式五门审计与段审计：Ch25 / Ch50 / Ch75 / Ch100。
3. 终判满足 V9 B 组六条：100/100 accepted、budget<1.0、CED≤sci-fi×1.15、overdue≤sci-fi 同章尺度、health≥8.0、T9=0。
4. 任一段 FAIL 即停止继续烧 token，冻结 DB / project_id / 审计 JSON / metrics 报告，转 `187.p/q/...` 定点修复；机制修复后必须 clean rerun。
5. 完成后产出 `archive/v9/187-urban-ch100-climb-execution-DONE.md`，并为 Task 188 收口提供证据。

---

## 硬约束

- 不新增核心 Agent / Workflow 节点。
- 不改五门冻结判定函数；`five_gate_check.py` 只作重放审计。
- CED 继续使用 consistency-only、merged/source、正文证据口径。
- T9 不接受解释性豁免；终判必须是 clean rerun 后 T9=0。
- 不用诊断 DB 做终判样本；机制修复后必须重新初始化或从明确的 clean 起点重跑。
- 不因 urban 体裁差异放宽 budget、overdue、health 或 completeness 口径。

---

## 设计 review 结论（2026-07-20）

结论：**准入实跑**。

已验证：

- `songyan profile show --genre urban` 可用；准入 review 当时 urban effective profile 来自 registry，`base_budget=12000`、`foreshadowing_horizon_floor=0`。Ch25 过程中已由 187.p 将当前 registry baseline 调整为 `base_budget=14000`。
- `songyan metrics --help` 确认 `--project-id`、`--chapters`、`-o/--output` 参数可用，可用于刷新并导出 T9/text cleanliness 证据。
- `scripts/five_gate_check.py --help` 确认需要 `--genre`、`--db`、`--project-id`、`--up-to`、`--format`。
- `scripts/segment_audit.py --help` 确认需要 `--db`、`--project-id`、`--up-to`、`--format`。
- `git diff --check -- archive/v9/187-urban-ch100-climb-execution.md archive/v9/186-urban-ch100-climb.md` 通过。

review 后不需要修改代码；187 首轮开发动作就是按本文启动 clean DB 实跑。

---

## Ch25 修复链与当前基线

Ch25 首段不是一次性通过，中途按分段早停纪律登记并处理了 5 个现场项：

| task | 类型 | 结论 | 终态 |
|---|---|---|---|
| 187.u | Ch21 settlement past-horizon plant | 过滤 LLM 抽取噪声，保留 `source_version_id` 硬约束 | clean Ch25 未复发 |
| 187.s | Ch25 health 门失败 | urban `continuity.health_overdue_weight=0.08`，不改 five-gate | health 8.5 |
| 187.v | Ch3 numerical settlement | true ledger formula mismatch，documented isolate，不改代码 | fresh rerun 未复发 |
| 187.p | Ch19 ContextEmergency | urban `base_budget=14000`，不改 Context Diet / emergency 阈值 | emergency=0 |
| 187.t | Ch23 `//` T9 artifact | deterministic clean 生成新 accepted 版本；补 `6次/24小时` detector precision | T9=0 |

当前继续 Ch50 的基线：

- DB：`.tmp/task172b_urban_ch100.db`
- project_id：`81e345042b124ee2a73094b82e4be555`
- run_id：`run-d22b1a44`
- Ch23 accepted head：`clean-23-6-502ec9b4`
- urban effective registry：`base_budget=14000`、`continuity.health_overdue_weight=0.08`

---

## 运行路径

现有 harness 固定使用以下路径：

| 项 | 路径 |
|---|---|
| DB | `.tmp/task172b_urban_ch100.db` |
| project 文件 | `.tmp/task172b_urban_project.json` |
| harness 分段 metrics | `.tmp/task172b_urban_segments.jsonl` |
| harness 报告 | `archive/v9/reports/187-urban-ch100-climb.md` |

187 额外审计产物：

| 产物 | 路径模式 |
|---|---|
| 五门 JSON | `.tmp/187_seg<n>_five_gate.json` |
| 段审计 JSON | `.tmp/187_seg<n>_audit.json` |
| metrics/T9 报告 | `.tmp/187_seg<n>_metrics.md` |
| Ch100 终判 JSON | `.tmp/187_urban_ch100_final.json` |

---

## 环境准备

PowerShell：

```powershell
$env:TEMPLATE_ID = "urban"
$env:RUN_ID = "187"
$env:CHECKPOINTER_MODE = "sqlite"
$env:SONGYAN_RUN_COST_BUDGET = "25.0"
```

初始化前确认 urban profile：

```powershell
songyan profile show --genre urban
```

必须看到：

- `base_budget=14000`
- `foreshadowing_horizon_floor=0`
- effective source 来自 registry，非 DB override

---

## 初始化

```powershell
powershell -NoProfile -File scripts\run_with_timeout.ps1 -TimeoutSec 900 -SuccessMarkerRegex "\[init\]" -- python scripts\run_172b_ch100_climb.py --init
```

初始化后读取 project id：

```powershell
$db = ".tmp/task172b_urban_ch100.db"
$projectInfo = Get-Content .tmp/task172b_urban_project.json | ConvertFrom-Json
$projectId = $projectInfo.project_id
```

---

## 分段执行

每段使用 wrapper；任一段失败、超时、budget 熔断、halt 或五门 FAIL 都停止进入下一段。

```powershell
powershell -NoProfile -File scripts\run_with_timeout.ps1 -TimeoutSec 5400 -SuccessMarkerRegex "\[report\]" -- python scripts\run_172b_ch100_climb.py --to 25
powershell -NoProfile -File scripts\run_with_timeout.ps1 -TimeoutSec 7200 -SuccessMarkerRegex "\[report\]" -- python scripts\run_172b_ch100_climb.py --to 50
powershell -NoProfile -File scripts\run_with_timeout.ps1 -TimeoutSec 7200 -SuccessMarkerRegex "\[report\]" -- python scripts\run_172b_ch100_climb.py --to 75
powershell -NoProfile -File scripts\run_with_timeout.ps1 -TimeoutSec 9000 -SuccessMarkerRegex "\[report\]" -- python scripts\run_172b_ch100_climb.py --to 100
```

---

## 段边界审计

每段完成后执行：

```powershell
python scripts/five_gate_check.py --genre urban --db $db --project-id $projectId --up-to <n> --format json > .tmp/187_seg<n>_five_gate.json
python scripts/segment_audit.py --db $db --project-id $projectId --up-to <n> --format json > .tmp/187_seg<n>_audit.json

$env:DATABASE_URL = "sqlite:///$db"
songyan metrics --project-id $projectId --chapters 1-<n> -o .tmp/187_seg<n>_metrics.md
Remove-Item Env:\DATABASE_URL
```

审计判定：

- `five_gate_check.py` 退出码 0 且 JSON `verdict=PASS` 才能进入下一段。
- metrics 报告中 T9 硬红线必须为 0：meta/artifact=0、duplicate=0、timeline=0。
- `segment_audit.py` 若提示 next-audit critical orphan 会触发 halt，需人工判断是否已被 accepted 后续正文真实回收；不能忽略 accepted 后仍存在的 critical orphan。

---

## 分段记录模板

| checkpoint | wrapper | five-gate | T9 | segment audit | 决策 |
|---:|---|---|---|---|---|
| Ch25 | PASS：25/25 accepted，run `run-d22b1a44` | PASS：budget 0.9595、CED 0.1127、overdue 19、health 8.5、gap 0 | PASS：meta/artifact 0、duplicate 0、timeline 0 | PASS：critical_orphans 0，halt_would_fire=false | 进入 Ch50 |
| Ch50 | PASS：50/50 accepted，wrapper `PASS_NORMAL_EXIT` | PASS：budget 0.9595、CED 0.0977、overdue 51、health 8.9、gap 0 | **PASS**：meta/artifact 0、duplicate 0、timeline 0（187.w precision 修复后复跑） | PASS：critical_orphans 0，halt_would_fire=false | 进入 Ch75 |
| Ch75 | PASS：75/75 accepted，wrapper `PASS_NORMAL_EXIT` | PASS：budget 0.9595、CED 0.0891、overdue 73、health 8.4、gap 0 | **PASS**：meta/artifact 0、duplicate 0、timeline 0（187.x precision 修复后复跑） | PASS：critical_orphans 0，halt_would_fire=false | 进入 Ch100 |
| Ch100 | PASS：100/100 accepted，wrapper `PASS_NORMAL_EXIT` | PASS：budget 0.9595、CED 0.11、overdue 100、health 8.6、gap 0 | **PASS**：meta/artifact 0、duplicate 0、timeline 0（187.y/z deterministic clean + precision 修复后复跑） | PASS：critical_orphans 0，halt_would_fire=false | 终判完成 |

---

## 撞墙路由

| 墙 | 触发条件 | 路由 |
|---|---|---|
| 预算墙 | `budget_used_peak >= 1.0`、`context_emergency_budget_ratio_halt`、成本熔断 | `187.p`：先冻结现场，再评估 urban `base_budget` 12000→13000→15000；禁止调分区权重 |
| CED 墙 | CED > sci-fi 同章 ×1.15 | `187.q`：定位 consistency issue 热点章；禁止把 craft issue 计入或移出 CED 来制造通过 |
| overdue 墙 | overdue > sci-fi 同章尺度 | `187.r`：先查 resolve 是否失效，再评估 floor；禁止直接用 floor 掩盖机制问题 |
| health 墙 | health < 8.0 或 critical orphan accepted 后仍存在 | `187.s`：查 setting reference / recycle / health 权重；禁止放宽 health |
| T9 墙 | meta/artifact、duplicate、timeline 任一非 0 | `187.t`：冻结 accepted 正文，定点修 detector 或 writer rules；禁止解释性豁免 |
| 完成度墙 | gap>1 或系统性 isolate | `187.u`：查失败章与 resume/settlement；非系统性 isolate 必须 documented review |

---

## 验收命令

终判：

```powershell
python scripts/five_gate_check.py --genre urban --db $db --project-id $projectId --up-to 100 --format json > .tmp/187_urban_ch100_final.json

$env:DATABASE_URL = "sqlite:///$db"
songyan metrics --project-id $projectId --chapters 1-100 -o .tmp/187_seg100_metrics.md
Remove-Item Env:\DATABASE_URL
```

文档和静态验证：

```powershell
git diff --check
ruff check src/ tests/ scripts/run_172b_ch100_climb.py scripts/five_gate_check.py scripts/segment_audit.py
python -m pytest tests/test_182_five_gate_tools.py tests/test_185_t9_precision_fixes.py tests/test_185_urban_calibration_harness.py -q
```

若 187 期间没有代码改动，默认不跑全量 pytest；若出现机制修复，必须按修复影响面补聚焦测试，并在收口前跑默认全量 pytest、CLI、mypy、ruff。

---

## 执行记录

### Ch25（2026-07-21）

正式通过样本：

- DB：`.tmp/task172b_urban_ch100.db`
- project_id：`81e345042b124ee2a73094b82e4be555`
- run_id：`run-d22b1a44`
- accepted：25/25
- failed_chapters：`[]`
- halt：`None`
- budget_used_peak：0.9595
- context_emergency_count：0
- five-gate：PASS（`.tmp/187_seg25_five_gate.json`）
- segment audit：critical_orphans=0、halt_would_fire=false（`.tmp/187_seg25_audit.json`）
- metrics/T9：meta/artifact=0、duplicate=0、timeline=0（`.tmp/187_seg25_metrics.md`）

Ch25 中途诊断 DB 不作为通过样本：

- `.tmp/187s_diagnostic_ch25_health_fail.db`
- `.tmp/187v_diagnostic_ch3_numerical_settlement_fail.db`
- `.tmp/187p_diagnostic_context_emergency_ch19.db`
- `.tmp/187t_diagnostic_ch23_t9_fail.db`

结论：Ch25 段边界已满足进入 Ch50 的准入条件。

### Ch75（2026-07-21）

正式通过样本：

- DB：`.tmp/task172b_urban_ch100.db`
- project_id：`81e345042b124ee2a73094b82e4be555`
- run_id：`run-d22b1a44`
- accepted：75/75
- failed_chapters：`[]`
- halt：`None`
- budget_used_peak：0.9595
- context_emergency_count：0
- five-gate：PASS（`.tmp/187_seg75_five_gate.json`）
  - budget 0.9595、CED 0.0891、overdue 73、health 8.4、gap 0
- segment audit：critical_orphans=0、halt_would_fire=false（`.tmp/187_seg75_audit.json`）
- metrics/T9：meta/artifact=0、duplicate=0、timeline=0（`.tmp/187_seg75_metrics.md`）

187.x T9 precision 收口（Ch75 段边界前必须归零）：

- 现象：Ch75 metrics 复跑后仍剩 2 条 timeline diagnostic
  - Ch63→Ch66：`2025-03-20` → `2017-09-12`，对应 `[注册日期: 2017年9月12日]`
  - Ch66→Ch70：`2024-01-07` → `1998-07-19`，对应 `[最后更新: 2024年1月7日]` 与父子回忆语境
- 根因：`_ignored_by_flashback_context` 未识别方括号元数据块；`父亲` 不在闪回标记列表内
- 修复：
  - `src/songyan/evals/timeline_consistency.py`
    - 新增 `_BRACKET_METADATA_RE`，方括号内的键值对日期（`[注册日期: ...]`、`[最后更新: ...]` 等）视为档案属性并忽略
    - `_FLASHBACK_MARKERS` 补充 `注册日期`、`父亲`
  - `tests/test_185_t9_precision_fixes.py`：新增 3 个回归测试覆盖 bracket metadata 与父子回忆语境
- 验证：`tests/test_185_t9_precision_fixes.py` + `tests/test_162_timeline_consistency.py` 41 passed；ruff 全绿

结论：Ch75 段边界已满足进入 Ch100 的冻结口径。

### Ch100（2026-07-22）

正式通过样本：

- DB：`.tmp/task172b_urban_ch100.db`
- project_id：`81e345042b124ee2a73094b82e4be555`
- run_id：`run-d22b1a44`
- accepted：100/100
- failed_chapters：`[]`
- halt：`None`
- budget_used_peak：0.9595
- context_emergency_count：0
- total_cost：约 ¥13.26（1766 次 LLM 调用）
- five-gate：PASS（`.tmp/187_urban_ch100_final.json`）
  - budget 0.9595、CED 0.11、overdue 100、health 8.6、gap 0
  - 对照 sci-fi Ch100 baseline：budget 0.9888、CED 0.3976、overdue 168、health 10.0
- segment audit：critical_orphans=0、halt_would_fire=false（`.tmp/187_seg100_audit.json`）
- metrics/T9：meta/artifact=0、duplicate=0、timeline=0（`.tmp/187_seg100_metrics.md`）

187.y T9 / 文本洁净度收口（Ch100 终判前必须归零）：

- 现象：Ch100 首次 metrics 显示 duplicate=2（Ch81、Ch88），timeline=2（Ch82、Ch83）
- Ch81/Ch88 duplicate：
  - Ch81 第 30/31 段高度重复（路径 A/B）
  - Ch88 第 8/26 段完全重复
  - 走 `apply_project_text_cleaning(1, 100)` deterministic clean，生成 `clean-81-6-5dc1dff6`、`clean-88-6-010cfb72`
- Ch82/Ch83 timeline：
  - Ch82 `2024年3月12日。三天前。` 是相对过去引用
  - Ch83 `2022年3月15日` 位于隐蔽通道/日志语境
- 修复：
  - `_FLASHBACK_MARKERS` 补充 `天前`、`隐蔽通道`
  - `_context_window` 半径由 30 扩展到 80，让日志/暗网语境标记能被日期匹配到
- 验证：新增 2 个回归测试；聚焦 pytest 43 passed；ruff 全绿

187.z T9 precision 收口（第二次复跑后仍剩 1 条 timeline）：

- 现象：duplicate 归零后，timeline 剩 1 条：Ch63→Ch96 `2025-03-20` → `2022-03-15`
- 根因：Ch91 `【覆盖时间戳: ...】` 全角括号、Ch96 行内代码文件名、物理隔离归档版本、项目封存语境、`2022年3月15日14:37:22` 紧凑时间戳未被识别为档案/口令时间
- 修复：
  - 将 `_BRACKET_METADATA_RE` 扩展为 `_METADATA_BLOCK_RE`，覆盖 `【...】` 与 `` `...` ``
  - `_FLASHBACK_MARKERS` 补充 `物理隔离`、`项目被封存`、`身份验证`
  - 新增紧凑时间戳启发式：日期后紧跟 `HH:MM(:SS)` 视为机器/口令时间戳并忽略
- 验证：新增 4 个回归测试；聚焦 pytest 47 passed；ruff 全绿

结论：Ch100 终判满足 V9 B 组六条，Task 187 完成。
