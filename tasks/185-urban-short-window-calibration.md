# Task 185: urban 短窗口标定实跑

> **阶段**: V9.4 urban 标定
> **类型**: 真实 LLM 实跑 / GenreRuntimeProfile 标定 / 短窗口验收
> **优先级**: P1（进入 urban Ch100 前必须消除 end15 预算与 T9 风险）
> **依赖**: 173/174/175/176 长跑可靠性已完成；183 Profile CLI 已完成；184 资源 schema 已完成
> **状态**: 🔄 进行中
> **来源**: `tasks/V9-README.md` Task 185 行；172k urban end15 观察项

---

## 任务边界

本任务目标是完成 urban 体裁的短窗口运行时标定，给 Task 186/187 的 urban Ch100 爬坡提供可靠默认值与证据。

必须完成：

1. 用 Task 183 的 DB override/CLI 路径完成 urban `GenreRuntimeProfile` 候选值实跑，不以手改代码作为迭代手段。
2. 对 urban `base_budget` 候选值执行 end15 短窗口标定：12000 → 13000 → 必要时 15000。
3. 复查 172k urban end15 曾出现的 T9=6（timeline_conflict 4 + meta_tag_leak 2），clean rerun PASS 样本必须 T9=0。
4. 观察 urban 伏笔 resolve 与 overdue 信号；只有实证需要时才调整 `foreshadowing_horizon_floor`。
5. 选定标定值后落入代码注册表，并跑 scifi end10 回归，确认无 Profile 体裁旧行为不变。
6. 证据落盘，更新 V9/STATUS/README/INDEX 并提交。

不做：

- 不启动 urban Ch100 爬坡；那是 Task 187。
- 不写 Task 186 urban Ch100 任务书；那是下一项。
- 不放宽 T9、budget、CED、overdue、health 任一口径。
- 不新增 Agent / Workflow 节点。
- 不改 `load_profile()` 的 registry + DB override 语义。

## 当前事实

172k urban end15（注册表全默认，base_budget=8000）已经证明：

| 指标 | 值 | 结论 |
|---|---:|---|
| accepted | 15/15 | 完成度 PASS |
| budget_used 峰值 | 0.982 | 表面 PASS |
| before_emergency 峰值 | 1.2792 | 贴近 1.3 halt 线 |
| context_emergency_count | 17 次，15 章连续触发 | 未标定，预算起点过低 |
| overdue | 1 | 暂无长窗口 floor 压力 |
| CED/1k | 3.6776 | 短窗口一致性压力低 |
| T9 | 6 | 必须 clean rerun 复查 |

判断：

- urban 与 scifi 的 genre_rules token 同级（约 -1.5%），不需要像 xuanhuan 一样直接假设 15000。
- 172k 的连续 emergency 与 xuanhuan Ch8 同类：溢出发生在不可裁核心，杠杆是抬 `base_budget`，不是调分区权重。
- `foreshadowing_horizon_floor` 不应机械套 xuanhuan/wuxia 的 48；urban end15 overdue=1，先观察 plant/resolve/horizon 分布。

## 关键实现约束

### 1. 标定迭代必须走 DB override，但现有 harness 需要补接线

`scripts/run_172a7_genre_validation.py` 当前在 `run_for_template()` 内部创建随机 temp DB：

```python
tmpdir = tempfile.mkdtemp(prefix=f"task172a7_{safe_id}_")
settings.database_url = f"sqlite:///{tmpdir}/songyan.db"
```

这导致外部命令：

```powershell
songyan profile upsert --genre urban --set base_budget=12000
```

写入的是当前 `DATABASE_URL`，不会进入 harness 随机 temp DB。若不改 harness，所谓“通过 183 CLI 标定”实际不会影响实跑。

Task 185 需要先补一个最小工具接线：

- `run_172a7_genre_validation.py` 增加显式 DB 参数，例如 `--db .tmp/185_urban_base12000.db`。
- 当传入 `--db` 时，使用该 DB，不再创建随机 temp DB。
- 标定流程先设置 `$env:DATABASE_URL` 指向同一 DB，再执行 `songyan profile upsert`，然后运行 harness。
- 默认不传 `--db` 时保留旧 temp DB 行为，避免破坏 V8 历史脚本用途。
- harness 若任一模板产生 `error`，进程必须非零退出；不能仅写出 JSON 后正常返回。

### 2. 成本与防卡纪律

所有真实 LLM 实跑必须使用 Task 176 wrapper 与 Task 175 成本预算：

```powershell
$env:SONGYAN_RUN_COST_BUDGET = "3.0"
powershell -NoProfile -File scripts\run_with_timeout.ps1 -TimeoutSec 5400 -SuccessMarkerRegex '"status": "completed"' -- python scripts\run_172a7_genre_validation.py ...
Remove-Item Env:\SONGYAN_RUN_COST_BUDGET
```

预算值可按实际价格微调，但必须有上限。不得裸跑多轮候选。

### 3. 候选值选择口径

按“最低足够值”选择：

1. 先跑 `base_budget=12000`。
2. 若 end15 无连续 emergency、`budget_used < 1.0`、`before_emergency < 1.0` 或 emergency 非连续且不贴 halt 线，则不继续烧 13000/15000。
3. 若 12000 仍连续 emergency 或 before_emergency 逼近 1.3，跑 13000。
4. 13000 仍不足才跑 15000。

### 4. T9 必须 clean rerun 到 0

172k urban end15 T9=6 不能解释性豁免。处理纪律：

- 若首轮候选 T9=0，直接作为 PASS 候选。
- 若 T9>0，先检查分布与证据；若集中于瞬时 LLM 失误，做同候选 clean rerun。
- 若 clean rerun 仍 T9>0，必须定点修规则/写作侧，不得进入 Task 186。

## 执行方案

### 阶段 A：工具接线

最小改动：

- `scripts/run_172a7_genre_validation.py`
  - 新增 `--db <path>`。
  - 输出 summary 中增加 `db_path`，便于后续审计。
  - 任一模板运行失败时返回非零 exit code，避免 wrapper 被普通退出误导。
  - 保持未传 `--db` 时旧 temp DB 行为。
- 测试：
  - 覆盖传入 `--db` 时 settings 指向指定文件。
  - 覆盖未传 `--db` 时仍使用 temp DB。

### 阶段 B：候选标定

候选一：`base_budget=12000`

```powershell
$db = ".tmp/185_urban_base12000.db"
$env:DATABASE_URL = "sqlite:///$db"
songyan profile upsert --genre urban --set base_budget=12000
$env:SONGYAN_RUN_COST_BUDGET = "3.0"
powershell -NoProfile -File scripts\run_with_timeout.ps1 -TimeoutSec 5400 -SuccessMarkerRegex '"status": "completed"' -- python scripts\run_172a7_genre_validation.py --templates urban --end 15 --db $db --output .tmp/185_urban_base12000_end15.json
Remove-Item Env:\SONGYAN_RUN_COST_BUDGET
Remove-Item Env:\DATABASE_URL
```

候选二/三仅在候选一不达标时执行：

- `.tmp/185_urban_base13000.db` + `.tmp/185_urban_base13000_end15.json`
- `.tmp/185_urban_base15000.db` + `.tmp/185_urban_base15000_end15.json`

### 阶段 C：证据审计

每轮候选至少记录：

- accepted / failed / status
- `budget_used_peak`
- `budget_used_before_emergency_peak`
- `context_emergency_count`
- T9 总数与类型分布
- overdue
- CED/1k
- `foreshadowings` status 分布、expected horizon 分布、resolved 数量

若需要 floor，按实测 plant density 与 expected horizon 决定，不直接复制 48。

### 阶段 D：落注册表与回归

选定候选后：

- 更新 `src/songyan/db/genre_runtime_profile_repo.py` 的 urban 注册表默认值。
- 如选择 floor，同步写入 `foreshadowing_horizon_floor`。
- 用 registry 默认值（不再依赖 DB override）重跑 urban end15 clean 验证，确认最终默认值可独立生效。
- 跑 scifi end10 回归，确认旧行为不漂移：

```powershell
$env:SONGYAN_RUN_COST_BUDGET = "2.0"
powershell -NoProfile -File scripts\run_with_timeout.ps1 -TimeoutSec 5400 -SuccessMarkerRegex '"status": "completed"' -- python scripts\run_172a7_genre_validation.py --templates scifi --end 10 --output .tmp/185_scifi_end10_regression.json
Remove-Item Env:\SONGYAN_RUN_COST_BUDGET
```

## TDD / 测试计划

1. `run_172a7_genre_validation.py --db` 指向指定 DB 文件，不再使用随机 temp DB。
2. 未传 `--db` 保持旧 temp DB 行为。
3. harness 内部任一模板失败时返回非零 exit code。
4. `songyan profile upsert --genre urban --set base_budget=<n>` 写入的 DB override 能被同 DB harness 读取。
5. 若修改 urban registry，补注册表单测确认值。
6. 聚焦测试 + CLI 测试 + mypy + ruff。
7. 默认全量 pytest。
8. 真实 urban end15 候选实跑、registry clean rerun 与 scifi end10 回归均使用 wrapper + 成本预算。

## 验收判据

- 至少一个 urban end15 clean rerun 达成：
  - 15/15 accepted；
  - 无 halt；
  - `budget_used_peak < 1.0`；
  - 不再连续触发 ContextEmergency，且 before_emergency 不贴 1.3 halt 线；
  - T9=0；
  - overdue/CED/health 无明显异常。
- 标定值与证据落盘，并写入任务文档执行记录。
- 选定值落入 registry 默认值；后续新项目不依赖手工 DB override。
- registry 默认值下的 urban end15 clean rerun PASS。
- scifi end10 回归 PASS，证明无 Profile 体裁旧行为不变。
- 全量 pytest、CLI pytest、mypy、ruff 全绿。

## 撞墙路由

| 风险 | 触发信号 | 处理 |
|---|---|---|
| 12000 仍连续 emergency | `context_emergency_count` 高、before_emergency 接近 1.3 | 跑 13000；仍不足再跑 15000 |
| T9 clean rerun 仍非 0 | timeline/meta_tag 反复出现 | 冻结样本，定点修 text cleanliness / writer 侧，不进入 186 |
| overdue 异常增长 | end15 overdue 明显高于 172k 或 resolved=0 且 plant 密集 | 先查 resolve 机制，再评估 floor；禁止直接调 floor 掩盖 resolve 失效 |
| profile CLI 未影响 harness | upsert 后 summary 仍显示默认 base_budget 行为 | 修 harness `--db` 接线；用同一 DB 验证 override 生效 |
| 成本超预算 | wrapper 输出 paused / budget exceeded | 停止候选，读成本报告后决定是否提额 resume |
| scifi 回归漂移 | scifi end10 budget/T9/accepted 异常 | 回滚/修正 urban registry 改动，确认未误改 fallback 或 scifi baseline |

## Out of Scope

- urban Ch100 正式爬坡。
- V10 优秀度信号包。
- 稀疏覆盖存储迁移。
- GateConfig 构建时序重构。

---

## 执行记录（2026-07-20）

### 阶段 A：工具接线（含 code review）

- `run_172a7_genre_validation.py` 新增 `--db`、summary `db_path`、模板失败非零退出（checkpoint `9bc831e`）。
- 恢复后先完成 code review（结论 Ready to merge，0 Critical），并按 review 意见补 2 条测试：override 经 `--db` 端到端可读（走 CLI 同款 `upsert_profile_overrides` 路径）、混合结果退出码。聚焦测试 4 passed。

### 阶段 B：候选标定（base_budget=12000，三轮实跑）

| 指标 | run1（override） | run2（override clean rerun） | run3（registry 默认值） |
|---|---:|---:|---:|
| accepted | 14/15（Ch13 结算瞬时失败 isolate） | 15/15 | **15/15** |
| status | partial | completed | completed |
| budget 峰值 | 0.8917 | 0.9396 | 0.9643 |
| before_emergency 峰值 | 0.0 | 0.0 | 0.0 |
| emergency 次数 | 0 | 0 | 0 |
| T9（harness 原值） | 12 | 3 | 3 |
| **T9（修复后检测器复测）** | — | **0** | **0** |
| overdue | 4 | 4 | 3 |
| CED/1k | 6.13 | 3.31 | 5.46 |
| 成本（¥） | 1.594 | 1.489 | 1.733 |

- 预算结论：base12000 两轮 budget 峰值 ≤0.9643、emergency=0、before_emergency=0，172k 的 17 次连续 emergency 完全消除。按"最低足够值"口径定为 **12000**，不再烧 13000/15000。
- 落盘：`.tmp/185_urban_base12000_end15.json`（run1）、`.tmp/185_urban_base12000_end15_r2.json`（run2）、`.tmp/185_urban_registry_end15.json`（run3，含复测标注）、`.tmp/185_t9_recompute_note.json`（复测证据）。

### 阶段 C：T9 定点修（检测器精度 8 项 + 写作侧 1 项）

T9 命中逐条核对后定性：无一条真时间线矛盾；slash_splice 真阳性仅 run1 的 `//` 注释体（写作侧）。修复均有守护测试（真拼接/真回跳/换措辞真回跳仍命中）：

- R1（run1/run2 证据）：slash 安全上下文补中文时间单位（`47次/分钟`）；闪回/档案标记 +年前/时间戳/签署/发起时间/timestamp；新增作息日程标记（到站/发车/班次/末班/检票/午休/下班/打卡）；倒计时配对加同计时器量级约束（>4× 视为独立计时器）。
- R2（run3 证据）：倒计时配对加语义锚点（匹配点 ±12 字符 CJK bigram，两侧非空且不相交判独立截止期限）；标记 +去年/前年/距今/修改时间；管道分隔日志行排除；**无年份日期与完整日期不可比**（归一化缺陷：`MM-DD`=month*31+day vs ordinal）。
- 写作侧：urban `writer_rules` +1（电子设备/系统消息用引号或【】，禁 `//` 代码注释体）；run3 正文 `//` 零出现。
- 复测口径说明：T9 为离线推导指标，检测器修复不重生成正文；对 run3（最终 prompt 下生成的 clean 样本）accepted 正文以终态检测器复测，T9=0，替代 run4（省 ¥1.7）。测试 `tests/test_185_t9_precision_fixes.py` 18 条。

### 阶段 D：registry 落值与回归

- registry：urban `base_budget` 8000→**12000**（`genre_runtime_profile_repo.py`，注释含 172k/185 证据链）；`foreshadowing_horizon_floor` 保持 0（end15 overdue=3，无长窗口压力，留待 Ch100 观察）。
- run3 即 registry 默认值 clean rerun（fresh DB、无 override，`profile show` 证实 source=registry）：15/15 + T9=0 + budget 0.9643，PASS 候选成立。
- scifi end10 回归（`.tmp/185_scifi_end10_regression.json`）：**10/10 accepted、0 halt、T9=0**、overdue=0、budget 峰值 0.7662、before_emergency 1.2352 未贴 halt 线。T9 由 175 运行的诊断残留 1（countdown_increase，同类假阳性）归 0，为检测器精度修复的预期后果；scifi 的 profile 与上下文路径本次未改动，Ch1 预算 legacy 公式不变。
- 验证：默认全量 pytest **2952 passed, 2 skipped, 1 xfailed**；CLI **35 passed**；mypy 176 files 0 errors；ruff 全绿。

### 验收结论（2026-07-20）

**PASS**：base_budget=**12000** 落入 registry；run3（registry 默认值、无 DB override）urban end15 clean rerun 达成 15/15 accepted、0 halt、budget 0.9643、emergency 0、T9=0（修复后检测器复测 accepted 正文）；overdue 3、CED 5.46 与 sci-fi 同量级；`foreshadowing_horizon_floor` 维持 0（短窗口无压力，留 Ch100 观察）；scifi end10 回归无漂移。总实跑成本约 ¥4.8（复测替代 run4 省 ¥1.7）。
