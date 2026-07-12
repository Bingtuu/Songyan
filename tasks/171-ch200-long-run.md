# Task 171: Ch200 长跑（V7 阶段 Z 第一里程碑，文学=观测，已解冻）

> **框架**: V7 文学质量框架级复盘（`docs/reports/v7-literary-framework-review.md`），本任务对应框架 §8 **D 组** + §7 主线
> **类型**: 长程爬坡验证（阶段 Z 主线）
> **优先级**: P0（V7 第一里程碑）
> **依赖**: 阶段 W/X/Y 已完成、T9/T10/T12 已冻结；V6 已验证 Ch1–150 稳定性（`run-bba292da` 150/150 accept）
> **状态**: ✅ **完成**——Ch200 live 长跑已完成（200/200 accepted），171t/171u 后 D1 hard clean pass；Ch200+ 文学护栏拆至 171v
> **负责人**: songyan-agent

---

## 最新结论（2026-07-12）

- **Ch200 规模化证据已取得**：run `run-fb39245c` Ch1-Ch200 **200/200 accepted、gaps=[]、Halt=None**。
- **稳定性面长跑底盘已跑通**：171p/171q/171r/171s 依次修复 state_mismatch、分段修订 duplicate、state_mismatch health/P1 构念、critical setting 同义提及刷新等撞墙问题。
- **D1 hard clean pass 已取得**：171t 补齐文本洁净量具，171u 对 Ch200 当前 accepted head 创建 20 个 clean versions 并复算报告；当前 T9 meta/artifact=0、duplicate=0，T6b critical orphan peak=0。
- **后续拆分**：171v = Ch200+ 文学可读性护栏；172 = Ch250 过渡验证。
- **事实报告**：`docs/reports/task-171-ch200-long-run-report.md`、`docs/reports/task-171-ch200-analysis-and-next-step-report.md`。

## 历史进度（2026-07-10）

- **harness 就绪**：`scripts/run_171_ch200.py`（复用 159 项目/大纲 + 稳定性面验收 harness，爬坡目标延至 Ch200）。`--init`/`--report` 离线路径已跑通（隔离 DB `.tmp/task171_ch1_ch200.db`，项目大纲 6 弧 3 线程导入成功）。
- **D2 通路已验证**：报告集成「文学 Tier 2 观测」段 + 171d 三层契约摘要（metrics 顶部 Tier1/2/3 分区），文学分随跑观测、不阻塞、可经报告查询。
- **D3 就绪**：报告结构 + `171p` 撞墙修复占位可承接 171c 成熟杠杆（当前 171c 结论为无达标杠杆，注入通道待成熟杠杆出现）。
- **D1 待执行**：Ch1→Ch200 真实 API 长跑（≈200 章，数小时、消耗预算、难以回滚）——按用户"小窗口验证先行"偏好，实跑规模/窗口待用户确认后再启动。

## 小窗口验证结果（Ch1-5，2026-07-11，run-ae6336b3）

按用户"小窗口先行"偏好，先跑 Ch1-5 真实 API 验证 harness。结果（隔离 DB `.tmp/task171_ch1_ch200.db`，enforce + isolate）：

- **Ch1-3 accepted（3/3）**，QG 通过、settlement + summary 正常；**Ch3 后 enforce 门 AutoHalt**。
- **halt 原因 = 稳定性面（非文学）**：`health_low_p1_halt: P1_count=11`，`continuity.health_low score=3.0 < 7.0`。细查：**Ch3 `orphaned=0, overdue=0`，P1 全部来自 `continuity_auditor.state_mismatches=11`**（角色状态契约 `character_update.old_value` 与 DB 不符），非孤儿设定。
- **框架前提被实证**：长跑在稳定性面（health/state_mismatch）halt，**从未被文学 rubric 阻塞**；文学随跑观测（本窗口 3 章基线不足、spot_read=False）。
- **harness 端到端跑通**：`run_171_ch200.py` 生成 + 稳定性面验收 + 三层契约 metrics（报告 Tier 1 汇总 8 处 meta/重复硬缺陷、Tier 2 observe、Tier 3 指针）+ D2 文学观测段，全部正常。温度死配置通电实证：日志 `llm.init temperature=0.7`（call_llm 默认解析 settings），Writer 显式 0.8 不受影响。

### 结论与路由

- **harness / D2 / D3 就绪且经真实 API 验证**；**D1 全量 Ch200 被 Ch3 的 state_mismatch=11 稳定性面 halt 挡住**——这是真实治理信号（V6 期 SettlementExtractor 角色状态提取精度已知关注点，Task 138 系列），**不在本 Task 内联修**。
- **路由至 `171p`**：Ch3 `state_mismatch` 峰值定点排查（是否早章瞬时/gate 灵敏度 vs 真实退化）。修复并复验后再放 D1 全量长跑。**不放宽 T9/health 冻结口径。**
- 报告：`docs/reports/task-171-ch200-long-run-report.md`。

---

## 任务边界

Task 171 是 Ch150 → Ch200 的渐进爬坡长跑，取真实证据。经框架改判，**文学质量不再是本任务的放行闸门**——放行判据回到**已验证的稳定性面**，文学质量作为**观测项**随跑输出、不自动阻塞（框架 §6.1 三层契约、§8 D 组）。

本任务与文学 R&D 线（171a→171b→171c）**并行**：R&D 不阻塞本长跑；R&D 产出的成熟杠杆经 `171p` 撞墙修复占位定点注入。

---

## 放行判据（回到稳定性面，不含文学 rubric）

| 面 | 判据 | 强度 |
|---|---|---|
| **Tier 1 硬缺陷（P/T9）** | accepted 正文零元标记泄漏、零整段落重复；时间线矛盾 report-only | 阻塞（沿用冻结阈值） |
| **continuity health** | 全程 health 不触红线（沿用 V6 冻结口径） | 阻塞 |
| **orphan 斜率** | orphan 累积斜率不显著恶化（对标 V6 基线 0.0897） | 阻塞 |
| **自适应门禁 T12** | AutoHalt 均对应真实退化（良性 FP=0，Task 170 已冻结） | 阻塞 |
| **文学质量（Tier 2）** | pacing/concept/voice/exposition 作为**观测**：滚动窗口趋势 + 低地板，跌破触发人工抽读 | **不自动阻塞** |

> Tier 2 具体参数（窗数 N、地板值）依赖 171a 可信量具 + 本长跑真实数据标定（框架 §8 A4），实跑初期可先只观测入库、不设触发。

---

## 验收标准（对应框架 §8 D 组）
- **D1**：Ch200 长跑完成，取得新 run_id 真实证据；放行以稳定性面判定，未以文学 rubric 为闸门。
- **D2**：长跑全程 Tier 2 文学趋势指标入库、可经 `songyan report`/metrics 查询；跌破触发的人工抽读有记录。
- **D3**：171p 撞墙修复占位可承接 171c 成熟杠杆（至少验证注入机制可用）。

## 实施要点（骨架，实跑前细化）
- 隔离 DB + enforce + isolate + 真实 API，沿用 V6 Task 159 的无人值守督跑模式（`scripts/supervise_*.py` 思路）。
- 分段推进 Ch151→Ch200，撞线走 `171p` 定点修复，不放宽冻结口径。
- 文学观测：复用/接入 171a 量具（若已达标）；未达标维度按框架转人工抽读，不入自动判据。

## 撞墙修复占位
- `tasks/171p-*`（待实跑反馈后确定具体内容）。

## 明确不做
- 不以文学 rubric 阻塞长跑；不放宽 T9/T10/T5/T6/T12 冻结口径；不等 171a/b/c 完成才启动（并行）。
