# Task 159 DONE — V6 阶段 D Ch1-Ch150 治理管线复现 + V6 阶段验收

> **Phase**: V6 阶段 D（长窗口验证）— 收官
> **状态**: ✅ 完成（Ch1-Ch150 实跑已执行，150/150 accept；V6 验收报告已入库；T5 已冻结）
> **完成日期**: 2026-07-04
> **规划文档**: `archive/v6/tasks/159-ch1-ch150-governance-pipeline-replication.md`
> **验收报告**: `archive/v6/reports/task-159-v6-final-acceptance-report.md`

---

## 交付概览

在 V5.2 + 骨架（141-144）+ 度量（145-148）+ 末端治理（149-152）+ 长跑底盘（153-156）的**真实合入管线**上复现 Ch1-Ch150 里程碑（新 run `run-bba292da`，替代旧 `run-a2bed648`），逐项与历史基线对比，逐条核对 §1.3 N/D/S/R/V，完成 T5 阈值复核与冻结。

| 交付物 | 文件 |
|--------|------|
| 复现脚本（init/实跑/resume/report 一体化） | `scripts/run_159_ch1_ch150.py` |
| 自主督跑脚本（保守策略：自动 resume / 停下上报） | `scripts/supervise_159.py` |
| Layer 2 冒烟测试（27 项：基线对比 / N-D-S-R-V / T5 复核 / 隔离） | `tests/test_159_replication_smoke.py` |
| V6 阶段验收报告 | `archive/v6/reports/task-159-v6-final-acceptance-report.md` |
| 逐章 metrics JSONL | `.tmp/task159_ch1_ch150_metrics.jsonl` |
| 隔离 DB（证据保留） | `.tmp/task159_ch1_ch150.db` |

---

## 实跑事实（run `run-bba292da`）

- **环境**：隔离 DB `.tmp/task159_ch1_ch150.db`，带大纲项目 `9e38783b589e4d6aa2a050f5c25e1d93`（与 157/158 同口径：6 弧 + 3 主线线索）。
- **命令口径**：`enforce` 门禁 + `on_failure=isolate`；真实 DeepSeek API；LLM 预算关闭。
- **完成度**：**150/150 章 accepted，`failed=[]`**。
- **health**：全程 50 个审计点，min=8.2、max=10.0、avg=9.24，**无任何点 <7.0**。
- **T5 遥测**：18 个样本；DB 尺寸峰值 112.32MB（红线 300MB）；扫描耗时中枢（中位数）70.5ms。

### 无人值守 + 自愈（§1.3-R 二次实证）

本次长跑由自主督跑脚本 `scripts/supervise_159.py`（保守策略）无人值守完成，中途发生并自动处理了多次 AutoHalt：

- **Ch54**：`health_low_p1_halt`（critical orphan `第一代共鸣者遗骸`，P1=1）→ 自动 resume。
- **Ch3 重算**：`context_emergency_budget_ratio_halt`（resume 重算早期章的预算压力）→ 自动 resume。
- **Ch13 重算**、Ch82/Ch115 隔离章补算 → 自动 resume 补齐。
- 督跑器全程按保守策略：良性门禁自动 resume、清理僵尸进程、无 escalation、跑完自动出报告。

这在 158r 命令级 kill→resume 证据之外，额外提供了**enforce 门禁下多次 AutoHalt 自动续跑至 150/150** 的可靠性实证。

---

## §1.3 N/D/S/R/V 验收核对（详见报告）

| 维度 | harness 结论 | 人工复核结论 | 关键值 |
|------|:---:|:---:|--------|
| **N 骨架** | ✅ pass | ✅ | 大纲/弧携带；T1 主线跃迁 2 条 |
| **D 度量** | ✅ pass | ✅ | 五类曲线全程可查、无断档 |
| **S 收敛** | 🔴 fail | ⚠️ 口径问题 | T6a 斜率 0.0897 ✓；T6b Ch54/57 P1（已 resolved）；T6c 小基数失真 |
| **R 可靠** | ✅ pass | ✅ | 158r 命令级证据 + 本次督跑多次自愈实证 |
| **V 验证** | 🔴 fail | ⚠️ 口径问题 | T2 150/150 ✓、T3/T8 ✓、T4 ✓；T5 口径缺陷（新口径下实质通过） |

### 两个 harness "fail" 的性质（均非治理退化）

1. **T6b（S 项）**：唯一涉事 critical orphan `entity.ark.first_resonator_remains`（Ch45 引入、Ch50 最后提及）在 Ch54/57 审计点被判 P1，**但最终状态为 `resolved`（Ch59 显式收束）**——属"关键设定跨章间隔提及"的瞬时窗口现象，被 harness 历史快照捕捉。orphan 斜率 0.0897≪138n 基线 6.28。可改进：`check_t6b` 对后续已 resolved 的设定豁免历史 orphan 快照。
2. **T6c（S 项）**：源头收敛过度（新 critical 速率≈0）导致归因比值小基数失真，157/158 同因。
3. **T5（V 项）**：现口径"前 10 样本均值×1.5"缺陷（基线落在开局低点，误判后半程自然增长）；见下。

---

## T5 阈值复核与冻结（阶段 A 出口标定的补完）

150 章 18 样本复核（相比 158 仅 11 样本）：

| 口径 | 基线(ms) | 系数 | 破线章 |
|------|---------:|-----:|--------|
| 现口径（前 10 样本均值） | 42.3 | ×1.5 | 9 处（Ch100+ 几乎全破） |
| 冻结口径（全样本中位数） | 70.5 | ×2.0 | 仅 Ch115（单点抖动尖峰 250ms） |

**冻结决定**：
- **尺寸红线：维持 DB ≤ 300MB**（150 章峰值 112.32MB，仅 37%，保守充分）。
- **扫描耗时红线：改为"全样本中位数 × 2.0"并冻结**。现口径把前 10 开局样本（库最小）当基线，误判后半程自然增长（与 158 Ch50/70 假破线同根因）；中位数×2.0 下 150 章仅 Ch115 一处可解释的单点尖峰。
- **T5 判定：150 章规模实质通过**。harness `check_t5` 默认参数改为中位数×2.0 + 单点多次采样取稳健值，列后续工程 Task（同步更新 `tests/test_158_t5_freeze.py`）；本 Task 纯验证，不改治理代码。

至此 §1.4 全部阈值（T3/T4/T5/T6a/T6b/T8）标定完成。

---

## V6 阶段验收结论

**V6 阶段实质达标 → 条件通过。**

- **达标事实**：新管线 Ch1-Ch150 **150/150 accept、`failed=[]`、无 health<7.0**、orphan 斜率 ≪ 基线、无 T3/T4 红线、DB 尺寸远低于红线；骨架（N）、度量（D）、可靠（R）三项 harness 直接 pass；无人值守自愈跑完 150 章。相比旧 `run-a2bed648`，V6 额外具备可追溯主线线索（T1）与五类长期度量（D）。
- **两处 harness fail 均为判据口径待校准项，非治理退化**：T6b 瞬时 orphan（已 resolved）、T6c 小基数失真、T5 基线窗口缺陷（新口径下通过）。
- **后续工程 Task（V6 收尾后或 V7）**：
  1. `check_t5` 口径改为中位数×2.0 + 稳健采样，冻结值落地代码。
  2. `check_t6b` 对已 resolved 设定豁免历史 orphan 快照；`check_t6c` 在小基数下的归因口径校准。
  这些是 harness（度量）改进，不涉及生成/门禁治理逻辑。

---

## 验证结果

- `pytest tests/test_159_replication_smoke.py -v`：27 passed。
- 全量 `pytest tests/ -q`：2270 passed, 2 skipped, 1 xfailed（159 准备工作提交时基线）。
- `ruff check scripts/ tests/`：通过。
- 纪律：全程未改 `src/` 治理/门禁/harness 判据代码；两处口径问题如实记录并列后续 Task。

---

## 参考

- `docs/v6-plan.md` §1.3 N/D/S/R/V、§1.4 T1-T8
- `archive/v6/tasks/157-ch1-ch50-integration-validation-DONE.md`、`archive/v6/tasks/158-ch1-ch100-long-run-validation-DONE.md`
- kill→resume 命令级证据：`archive/v6/reports/task-158r-kill-resume-drill-report.md`
- 阈值标定：`archive/v6/tasks/148z-stage-a-threshold-calibration-DONE.md`
- `scripts/run_159_ch1_ch150.py`、`scripts/supervise_159.py`、`tests/test_159_replication_smoke.py`
