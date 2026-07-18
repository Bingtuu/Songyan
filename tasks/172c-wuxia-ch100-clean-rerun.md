# Task 172c — wuxia Ch100 修复后干净重跑

> **状态**: ✅ 完成（Ch1-Ch100 clean rerun 100/100 accepted；五门 PASS）  
> **归属**: V8.2 / 172c 主线续跑（V8-pass 后续增强）  
> **编号说明**: 本文件不新增 `172c.s`；它是 `tasks/172c-wuxia-ch100-climb.md` 在 172c.r 完成后的执行页。  
> **硬前置**: 172c.r ✅（resolve 四层根因全修、health 口径对齐、scifi end10 + wuxia end15 实跑回归通过）  
> **目标体裁**: wuxia  
> **终判基线**: sci-fi Ch1-100 冻结基线（同 172b / `.tmp/scifi_ch100_baseline.json`）

---

## 1. 目标

从干净 DB 重新运行 wuxia Ch1-Ch100，获得完全出自 172c.r 修复后机制的终判数据，闭合 172c 第二非 sci-fi 体裁中篇爬坡验证。

本任务回答的问题只有一个：**修复后的伏笔 resolve + continuity health 机制，能否支撑 wuxia 在 Ch100 尺度达到 sci-fi 同级质量水位。**

172c.r 前的 Ch1-Ch75 数据只保留为事故证据，不进入 172c 终判。V8 五维验收已由 xuanhuan Ch100 闭合，本任务失败不回溯推翻 V8-pass。

## 2. 背景

172c 初次爬坡已完成 Ch75 accepted，但段 3 暴露三门失败：

| gate | Ch75 结果 | 判断 |
|---|---:|---|
| budget | PASS | 无需优先处理 |
| completeness | PASS | 75/75 accepted |
| CED | FAIL | 需在修复后重跑中复核 |
| overdue | FAIL（203 vs sci-fi 117/136 尺度） | 原因已定位到 resolve 机制失效 |
| health | FAIL（5.6） | 原因已定位到 overdue 漏计与口径割裂 |

172c.r 已完成四层根因修复：

1. settlement prompt card 1.0.4 补 `foreshadowing_updates.resolve` 契约。
2. `resolved_hooks` 明确为叙事摘要，不可替代 DB resolve 操作。
3. settlement 事实源纳入 overdue 伏笔，使逾期伏笔仍可被 LLM 回收。
4. `_update_continuity_tracking` 5.3 跳过本单已 resolve id，避免同事务陈旧读把 resolved 翻回 overdue。

短窗口实跑已证明机制恢复：scifi end10 有 8 次 `foreshadowing_resolved`，wuxia end15 有 9 次 `foreshadowing_resolved`，0 failed。下一步必须重跑长窗口，因为原 Ch75 DB 的前 75 章生成于修复前，无法作为干净终判样本。

## 3. In Scope

- [x] 备份旧 wuxia Ch75 DB、project file、segments metrics 和报告产物（如存在）。
- [x] 清理旧 `.tmp/task172b_wuxia_segments.jsonl`，避免新分段指标被旧 Ch75 数据污染。
- [x] 使用 `scripts/run_172b_ch100_climb.py --init` 重新初始化 wuxia 项目。
- [x] 从 Ch1 分段运行到 Ch100：25 / 50 / 75 / 100 四个边界均做 early-warning。
- [x] 每个边界记录五门：budget、consistency CED、overdue、health、completeness。
- [x] 每个边界额外记录 resolve 健康度：resolved 数量、due/overdue 可见性、是否出现 resolve 后翻回 overdue。
- [x] Ch100 产出 `docs/reports/172c-wuxia-ch100-climb.md` 终判报告。
- [x] 完成后同步 `docs/STATUS.md`、`tasks/V8-README.md`、`README.md` 的 172c 状态。

## 4. Out of Scope

- 不新增 Agent / workflow 节点。
- 不修改 CED 口径；继续使用 consistency-only、merged/source、正文证据口径。
- 不把文学 craft issue 或 `rule-mr-*` 聚合项计入 CED。
- 不在无长窗口证据前调整 wuxia `foreshadowing_horizon_floor`。
- 不为了让 overdue 过线而调 floor 掩盖 resolve 机制问题。
- 不启动 urban Ch100 或跨体裁 Ch200；这些划归 V9 或后续任务。
- 不回填旧 Ch75 DB 作为终判数据。

## 5. 启动前检查

| 检查项 | 要求 |
|---|---|
| 代码状态 | 172c.r 修复已在当前分支；若之后有 settlement / continuity / profile 改动，先跑相关测试 |
| LLM 配置 | `.env` 中 API key 可用；Windows 长跑建议 `CHECKPOINTER_MODE=memory` |
| 旧数据备份 | 备份 `.tmp/task172b_wuxia_ch100.db`、`.tmp/task172b_wuxia_project.json`、`.tmp/task172b_wuxia_segments.jsonl` |
| 判定器 | `.tmp/vdim_compare.py` 与 `.tmp/scifi_ch100_baseline.json` 在位 |
| 旧行为回归 | 如 172c.r 后又改过运行时契约，先跑 scifi `--end 10` |
| 成本窗口 | 确认 API 低价时段足够覆盖 100 章长跑或至少一个 25 章段 |

备份示例：

```powershell
New-Item -ItemType Directory -Force .tmp\backups | Out-Null
$stamp = Get-Date -Format "yyyyMMdd_HHmmss"
Copy-Item .tmp\task172b_wuxia_ch100.db ".tmp\backups\task172c_prefill_ch75_$stamp.db" -ErrorAction SilentlyContinue
Copy-Item .tmp\task172b_wuxia_project.json ".tmp\backups\task172c_prefill_project_$stamp.json" -ErrorAction SilentlyContinue
Copy-Item .tmp\task172b_wuxia_segments.jsonl ".tmp\backups\task172c_prefill_segments_$stamp.jsonl" -ErrorAction SilentlyContinue
```

> 注意：当前 harness 内部按 `TEMPLATE_ID` 固定 DB 路径为 `.tmp/task172b_wuxia_ch100.db`，不要依赖外部 `DATABASE_URL` 切换路径。`--init` 会删除同名 DB / WAL / SHM 后重建，因此必须先备份。
> `--init` 不会清理 `.tmp/task172b_wuxia_segments.jsonl`；备份后必须手动删除旧 metrics 文件。

## 6. 执行步骤

### 6.1 初始化

```powershell
$env:TEMPLATE_ID = "wuxia"
$env:RUN_ID = "172c"
$env:CHECKPOINTER_MODE = "memory"
Remove-Item .tmp\task172b_wuxia_segments.jsonl -Force -ErrorAction SilentlyContinue
python scripts/run_172b_ch100_climb.py --init
```

初始化后确认：

- project genre = `wuxia`
- skeleton 导入成功（9 arcs / 3 threads）
- runtime profile snapshot 中 `base_budget=10500`、`max_character_states=8`、`character_decay.focal_gaps={full:8, compact:20, symbol:60}`、`foreshadowing_horizon_floor=48`（172c.s 后）

### 6.2 分段运行

```powershell
python scripts/run_172b_ch100_climb.py --to 25
python .tmp/vdim_compare.py 25

python scripts/run_172b_ch100_climb.py --to 50
python .tmp/vdim_compare.py 50

python scripts/run_172b_ch100_climb.py --to 75
python .tmp/vdim_compare.py 75

python scripts/run_172b_ch100_climb.py --to 100
python .tmp/vdim_compare.py 100
```

任一段出现 hard halt、accepted 缺口、budget 超线、CED 超线、overdue 超 sci-fi 同章尺度、health 低于门槛时，不继续烧后续章节；先冻结 DB，记录边界报告，再按 §8 路由。

### 6.3 resolve 健康度抽查

每个段边界至少记录：

| 指标 | 目的 |
|---|---|
| `status='resolved'` 的 foreshadowing 数量 | 证明 resolve 不再为 0 |
| due / overdue 且未 resolved 的数量 | 判断 backlog 是否真实受控 |
| 同一 id 是否出现 resolved 后又变 overdue | 防止 172c.r 第四层根因回归 |
| `foreshadowing_resolved` 事件数 | 与 DB 状态互证 |

若 Ch25 后 resolved 仍为 0，且存在 due/overdue 伏笔，直接停止并回到 172c.r 诊断，不做 floor 调参。

### 6.4 172c.s 后 Ch25 smoke 结果

第三轮 clean smoke（project `273a8408be8e4caf8cbc1e91954da600`）已完成：

| gate | Ch25 结果 | 判定 |
|---|---:|:---:|
| completeness | 25/25 accepted | PASS |
| budget_peak | 0.9646 | PASS |
| before_emerg_peak | 1.2566 | PASS |
| context_emergency | 29 | 观察 |
| overdue | 0（sci-fi Ch25=61） | PASS |
| health | 8.8 | PASS |
| consistency CED | 0.23（20 issues）vs sci-fi 0.33（32 issues） | PASS |
| resolve | resolved/archived 13 | PASS |

结论：172c.s 已完成；同一 clean DB 继续推进并已完成 Ch100。

### 6.5 Ch100 终判结果

最终 clean DB project：`273a8408be8e4caf8cbc1e91954da600`。

| up_to | accepted | budget_peak | CED/1k | CED issues | overdue | health | 判定 |
|---:|---:|---:|---:|---:|---:|---:|:---:|
| 25 | 25/25 | 0.965 | 0.23 | 20 | 0 | 8.8 | PASS |
| 50 | 50/50 | 0.965 | 0.20 | 35 | 0 | 9.8 | PASS |
| 75 | 75/75 | 0.965 | 0.18 | 48 | 22 | 8.1 | PASS |
| 100 | 100/100 | 0.965 | 0.17 | 58 | 35 | 8.3 | PASS |

Ch100 run `run-82968662` 最终 status=`completed`、failed=[]。Ch100 accepted version `v-17cdf3f6`，settlement valid，summary generated，arc summary generated。Ch100 终点 continuity audit：orphaned=13、forgotten=0、overdue=35、health=8.3。

## 7. 验收标准

Ch100 终判必须同时满足：

| gate | 判据 |
|---|---|
| completeness | Ch1-Ch100 全 accepted；若 isolate gap 出现，必须证明非系统性且最终补齐 |
| budget | `budget_used` 峰值 < 1.0；无 `context_emergency_budget_ratio_halt` |
| T9 hard | = 0 |
| continuity | critical orphan = 0；health 不持续退化，Ch100 health ≥ 8.0 |
| CED | consistency CED ≤ sci-fi Ch100 × 1.15，即 ≤ 0.4573 |
| overdue | unresolved overdue ≤ sci-fi Ch100 同尺度，即 ≤ 168 |
| resolve | `foreshadowings.status='resolved'` 数量 > 0，且无同事务翻回 overdue 证据 |
| report | `docs/reports/172c-wuxia-ch100-climb.md` 写明四段曲线、五门判定、失败/重试清单 |

通过后，172c 标记为完成；V8 多体裁中篇证据扩展为 xuanhuan + wuxia 两个非 sci-fi 体裁 Ch100。

## 8. 撞墙路由

| 信号 | 判断 | 路由 |
|---|---|---|
| resolved 仍为 0 | 172c.r 修复未在长窗口生效或 prompt/事实源回归 | 停止，回到 172c.r；不调 floor |
| resolved > 0 但 overdue 仍超线 | resolve 生效但回收强度不足，或 wuxia floor 长窗口不足 | 在 172c 主线记录实测曲线；已路由 `tasks/172c.s-wuxia-long-window-foreshadowing-and-health-calibration.md` |
| CED 超线 | 真实 consistency 热点或量具输入异常 | 冻结热点章，复用 172b.q 方法；若需修正文/审查输入，并入 `172c.s` 或另立后续任务 |
| health 低但 vdim overdue 同步高 | health 门真实反映 backlog | 先看 resolve / overdue，不放宽 health |
| health 低但正文真实回收 | matcher 漏记或 evidence 追踪问题 | 定点修 matcher，不松门禁 |
| budget 超线 | 运行时预算或 genre_rules 体量问题 | 优先 base_budget / genre_rules 内容，禁止先调 partition_ratios |
| harness / 环境失败 | 非质量信号 | 记录 isolate/retry；超过重试仍失败再人工处理 |

## 9. 完成后交付

- `docs/reports/172c-wuxia-ch100-climb.md`
- `tasks/172c-wuxia-ch100-climb.md` 状态更新为完成
- `docs/STATUS.md` 当前判断与最近验证更新
- `tasks/V8-README.md` 172c 状态与文档入口更新
- `README.md` 当前能力 / 路线图同步
- 新增 `tasks/172c-wuxia-ch100-clean-rerun-DONE.md`

## 10. 参考

- `tasks/172c-wuxia-ch100-climb.md` — 172c 主任务事实源
- `tasks/172c.r-wuxia-foreshadowing-resolve-and-health-fix-DONE.md` — clean rerun 的直接前置
- `tasks/172b-xuanhuan-ch100-climb.md` — Ch100 分段爬坡方法论
- `tasks/172b.q-consistency-ced-repair.md` — consistency CED 终判口径
- `docs/STATUS.md` — 当前阶段状态
- `tasks/V8-README.md` — V8 事实入口与编号治理
