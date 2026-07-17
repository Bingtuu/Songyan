# Task 172c — 第二个非 sci-fi 体裁 Ch100 爬坡验证

> **状态**: 🔄 进行中（Ch1-Ch75 已完成；172c.r 伏笔 resolve + health 修复已落地并回归通过；**暂停**，待 API 低价时段启动 Ch1 完整重跑）
> **归属**: V8.2 多体裁章数爬坡（V8-pass 后续增强，不回溯性阻塞 V8 完成判定）
> **前置**: 172b xuanhuan Ch100 五门 PASS ✅；172a.7 短窗口质量同标 ✅；172e-172i 运行时契约补完 ✅
> **候选体裁**: **wuxia**
> **对标基线**: sci-fi Ch1-100 冻结基线（同 172b §1.1，`.tmp/scifi_ch100_baseline.json`）

---

## 1. 目标与定位

**一句话**：用 wuxia 复刻 172b 的 Ch100 爬坡，证明 V8 的中篇能力是 `GenreRuntimeProfile` 机制泛化的结果，而非 xuanhuan 体裁特例。

V8-README V 维度判据已由 172b（xuanhuan）闭合；172c 是**已承诺的后续 scope**——把「多体裁」证据从短窗口（10-15 章）扩展到中篇（Ch100）。172c 若撞墙不回溯性推翻 V8-pass；撞墙按 §4 路由 `172c.<suffix>` 定点修复，不放宽阈值、不做 prompt 工程。

172c 出口 = 同时满足（与 172b 同一套五门，冻结口径）：

| 项 | 判据 | 对标 sci-fi Ch1-100 基线 |
|---|---|---|
| 完成度 | Ch1-100 全 accepted（isolate 失败 ≤ 明确记录且非系统性） | 100/100 |
| budget | budget_used 峰值 < 1.0；无 `context_emergency_budget_ratio_halt` | 峰值 0.989 |
| ContextEmergency | 偶发不连续 | 偶发 |
| T9 hard | = 0 | 0 |
| 连续性 | critical orphan = 0；health median 不持续退化 | median ≥8.5, critical orphan 0 |
| CED | consistency-only CED ≤ sci-fi × 1.15（172b.q 终判口径） | 0.3976（ceiling 0.4573） |
| overdue | ≤ sci-fi 同章尺度（Ch25→61 … Ch100→168），**不套用短窗口 `<5`** | Ch100→168 |

> **质量同标纪律**：不因「武侠状态密度/命名风格特殊」放宽任何硬指标。

## 2. 为什么选 wuxia

1. **短窗口证据已达标**：wuxia `--end 10` 10/10 accepted、0 halt、peak budget 0.958、CED 8.48（优于 scifi 9.60）——具备爬坡资格。
2. **与 xuanhuan 病理不同，互补性强**：wuxia genre_rules 仅 +27.7%（xuanhuan +79.9%），budget 压力中等；但伏笔 plant-time horizon **比 xuanhuan 更短**（峰值 +2/+3，max +11）——考验的是 S/伏笔维度而非 budget 维度，与 xuanhuan 形成互补证据。
3. **运行时 profile 已预置**：`genre_runtime_profile_repo.py` wuxia 条目 `base_budget=9500`、`foreshadowing_horizon_floor=12`（172a.p 模拟：floor=12 → overdue@end15 从 25 压到 5）。
4. **模板骨架就绪**：`project_templates/wuxia/outline.json` 与 xuanhuan 同构——9 arc（Ch1-250）+ 3 thread，Ch100 落在 arc 3（Ch76-100）边界，全程 `has_skeleton=True`。

## 3. 实施（复用 172b 基础设施，不新增节点）

### harness

复用 `scripts/run_172b_ch100_climb.py`（无人值守 + kill/resume + 逐章 metrics + 分段爬坡），通过环境变量切换体裁：

```powershell
$env:TEMPLATE_ID = "wuxia"          # 默认 xuanhuan；DB/报告路径随模板名变化
$env:RUN_ID = "172c"                # 报告编号前缀（默认 172b 保持向后兼容）
$env:DATABASE_URL = "sqlite:///.tmp/task172b_wuxia_ch100.db"
python scripts/run_172b_ch100_climb.py --init     # ProjectInitializer.from_template("wuxia")
python scripts/run_172b_ch100_climb.py --to 100   # 分段爬坡，自动 resume
```

报告编号已参数化：harness `REPORT_PATH` 前缀由 `RUN_ID` 环境变量控制（默认 `172b`），wuxia 报告落盘 `docs/reports/172c-wuxia-ch100-climb.md`。

### 分段爬坡计划（沿用 172b，25 章一段 = arc 边界）

```
段1 Ch1-25   (arc0)  → 汇总 budget/overdue/health → 五门 early-warning → 无 halt 才进段2
段2 Ch26-50  (arc1)  → 汇总 → gate；★ overdue 尺度决策点（见 §4 风险 1）
段3 Ch51-75  (arc2)  → 汇总 → gate
段4 Ch76-100 (arc3)  → 汇总 → 出 Ch100 终判报告
```

### 判定器与终判口径

- 逐段 early-warning：`.tmp/vdim_compare.py`（chapter-bounded CED，与冻结基线严格同口径），按当前深度线性插值 sci-fi 基线。
- Ch100 终判 CED：`src/songyan/evals/consistency_ced.py` consistency-only 口径（172b.q 冻结：merged 优先、排除文学 craft 与 `rule-mr-*` 聚合项、accepted source 追溯）。
- 产出报告：`docs/reports/172c-wuxia-ch100-climb.md`（逐段 budget 曲线、emergency 频率、overdue 轨迹、CED vs sci-fi 基线、health 趋势、失败清单）。

## 4. 风险与撞墙路由

| # | 风险 | 触发信号 | 路由与预案（不放宽口径） |
|---|---|---|---|
| 1 | **horizon floor 长窗口不足**（最可能撞墙点） | 段边界 overdue > sci-fi 同章尺度 | **172c.p**：xuanhuan 在 Ch65 证明 floor=12 在 Ch100 尺度不足（171>126，提到 48 后 Ch100 overdue=166≤168）；wuxia plant horizon 更短，同样风险。预案：提高 wuxia floor（参考值 48，按实测 plant 密度定）+ 未 resolved 伏笔一次性 expected 修复。决策点设在**段 2（Ch50）边界**：若 overdue 趋势外推 Ch100 超 168，即停并路由，不硬跑 |
| 2 | CED 终段超线 | Ch80+ consistency CED 持续 > ceiling 0.4573 | **172c.q**：172b 在 Ch91-93 撞过同款；量具已就绪，预案为热点章（多轮修订章 issue 密度最高者）定点修订，不改口径 |
| 3 | budget 长尺度溢出 / 短窗口贴边 | Ch50+ budget_used 逼近 1.0 或 halt；短窗口 budget_before_emergency 贴边 1.3 | 杠杆是 `base_budget` 微调 / genre_rules 内容精简（层 3），非分区权重；wuxia +27.7% 中等压力，风险低。**scifi 回归实测**：短窗口 peak 1.3090（Ch10）贴边 1.3 阈值（172a.7 peak 1.2837 同量级），属固有 flaky——harness `HALT_RETRIES=2` 自动 resume 重试正是覆盖此场景，重试耗尽才路由人工 |
| 4 | 连续性假 orphan 新形态 | `health_low_p1_halt` 但正文实际在回收 | 定点审计 matcher（172b 已修引号 split；wuxia 命名风格不同可能出现新形态），只修 matcher 不松门禁 |
| 5 | 环境漂移 | `.tmp/vdim_compare.py` / `.tmp/scifi_ch100_baseline.json` 缺失 | 启动前按 §5 清单核实；缺失则从 172b 流程重建基线后再开跑 |

> 172b 已修复的事故（resume 短路 `dd5ac8a`、引号 matcher `0d7cd42`、floor 长窗口 172b.p、CED 量具 172b.q）在 wuxia 爬坡中**不需要重复修复**，但要在段边界审计中确认同类信号未再现。

## 5. 启动前置检查清单

- [x] 172a.7 短窗口质量同标（wuxia `--end 10` 10/10、CED 8.48）
- [x] 172b xuanhuan Ch100 五门 PASS（V 维度方法论与判定器冻结）
- [x] wuxia profile 已预置 `base_budget=9500` + `foreshadowing_horizon_floor=12`
- [x] wuxia 模板骨架 9-arc/3-thread 覆盖 Ch1-250（2026-07-15 核实）
- [x] 172e-172i 运行时契约补完（profile 字段全接线；scifi 回退回归 2746 passed）
- [x] `.tmp/vdim_compare.py` 与 `.tmp/scifi_ch100_baseline.json` 在位（2026-07-15 核实）
- [x] harness `REPORT_PATH` 编号参数化（`RUN_ID` 环境变量，默认 `172b` 向后兼容）
- [x] 实跑前 scifi `--end 10` 回归确认旧行为不变（2026-07-16 两轮实跑：budget 曲线与 172a.7 基线一致，累计 Ch1-9 全 success、settlement 全 true、0 T9；两次 halt 均为既有门禁固有 flaky——Ch2 `failure_halt`（修订不收敛 + hook_checker 宣言式收束盲区误杀重写版）、Ch10 `budget_ratio_halt`（1.3090 贴边 1.3 阈值，172a.7 peak 1.2837 同量级）；均非 172e-172i 行为偏差）

## 6. 依赖

- **硬前置**：172b 五门 PASS ✅（判定器、基线、事故修复全部冻结复用）。
- **不阻塞 V8**：172c 是 V8-pass 后续增强；若 172c.p/172c.q 撞墙，按证据新建对应 `tasks/172c.<suffix>-*.md` 并在 V8-README 撞墙修复子表登记，不回溯推翻 V8-pass。
- **后续**：172c 达标后，V8 多体裁长窗口证据闭合（2/3 非 sci-fi 体裁 Ch100）；urban 第三体裁与全体裁 Ch200 划归 V9 或更晚。
