# Task 170g: 提质复评出口（Ch200 放行判定）

> **专项**: 文学提质专项（`tasks/170-literary-quality-remediation-README.md`）
> **类型**: 出口验证（终检）
> **优先级**: P0（决定能否放行 Task 171 Ch200）
> **依赖**: 170c + 170d + 170e + 170f 全部 DONE
> **状态**: ◻ 规划中

---

## Goal

用**修复后的量具**（170c T9 近似去重 + 170d 校准后 LiteraryAuditor）复评**提质后重生成**的中段窗口，与 170b 基线逐维对比，判定文学质量能否从 blocker 转为 pass/observation——即能否放行 Ch200。

## 前置条件（全部满足才开工）

- [ ] 170c DONE：T9 能抓近似/改写重复（Ch31 不再漏报）。
- [ ] 170d DONE：LiteraryAuditor character_autonomy 已校准，机器分向人工判断收敛。
- [ ] 170e DONE：voice 声纹机制修复，小样本已显改善。
- [ ] 170f DONE：pacing/exposition 检测 + 工艺卡约束落地，小样本已显改善。

## 复用现有工具（查证确认，靠环境变量参数化，无需改代码）

| 步骤 | 复用 | 参数 |
|------|------|------|
| 重生成中段窗口 | `scripts/run_170b_midwindow_generation.py` | `DATABASE_URL`(新隔离DB)、`END_CHAPTER=40`、`--init` |
| 抽读复评 | `scripts/run_170b_readability_assessment.py` | `DATABASE_URL`、`ASSESS_START=28`/`ASSESS_END=40`、5 维 rubric 已内置且与提质维度对齐 |

**硬编码注意点**（查证发现）：`run_170b_readability_assessment.py` 的 `PROSE_EXPORT_PATH`（`:52`，写死 `ch28_ch40`）和 `REPORT_PATH`（`:51`，写死 170b 报告路径）**会覆盖 170b 产物**。170g 执行前需：
- 要么改这两个常量指向 170g 专属路径（如 `task170g_prose_*.md` / `task-170g-...report.md`）；
- 要么先备份 170b 产物。

建议 170g 复制一份评估脚本为 `run_170g_reeval.py`（或加输出路径参数），避免覆盖基线证据。

## In Scope

- [ ] 用提质后代码 + 新隔离 DB 重生成 Ch1–Ch40（保证与 170b 同大纲种子，可比）。
- [ ] 用校准后 LiteraryAuditor + 修复后 T9 复评 Ch28–Ch40。
- [ ] **逐维对比 170b 基线**：
  | 维度 | 170b 基线 | 170g 目标 |
  |------|:---:|------|
  | voice | 1.8 | 可测量提升 |
  | pacing | 2.4 | 可测量提升 |
  | exposition | 2.1 | 可测量提升 |
  | concept | 3.2 | 不回退 |
  | ai_tone | 2.2 | 不回退 |
  | 机器/人工偏差 | 5/13 章 ⚠️ | 收敛 |
  | T9 近似重复 | 漏报 | 不再漏报 |
- [ ] 助手初筛 + 用户复核（沿用 170b 分工：助手标重点/偏差，用户终判）。
- [ ] 出复评报告 + pass/observation/blocker 判定。

## Out of Scope

- 不启动 Ch200（本任务仍是中段窗口复评）。
- 不在复评中临时改量具或提质代码（复评是冻结态验证；发现新问题另开迭代）。
- 不放宽任何冻结口径。

## 判定标准

| 结论 | 条件 | 后续 |
|------|------|------|
| **pass** | voice/pacing/exposition 均较基线提升且无维度塌陷（建议均值 ≥3）；偏差收敛；T9 不漏报 | 放行规划 Task 171 Ch200 |
| **observation** | 主要维度提升但仍有轻微债，不影响爬坡；量具已可信 | 记录残余债，可进 Ch200，Task 171 首窗仍抽读 |
| **blocker** | 提质无效或量具仍失真或引入新缺陷 | 记录根因，回炉 170e/170f 迭代，或缩小 Ch200 目标重议 |

## 验证要求

```powershell
# 提质后全量回归先过
python -m pytest tests/ -q
ruff check src/ tests/

# 重生成 + 复评（真实 LLM，隔离 DB，新输出路径）
$env:DATABASE_URL="sqlite:///.tmp/task170g_rerun.db"
python scripts/run_170b_midwindow_generation.py --init   # 或专属 170g 脚本
$env:END_CHAPTER="40"; python scripts/run_170b_midwindow_generation.py
python scripts/run_170g_reeval.py   # 或参数化的 170b 评估脚本
```

## 验收标准

- [ ] 提质后重生成完成（Ch1–Ch40），与 170b 同种子可比。
- [ ] 复评报告含逐维基线对比表 + 机器/人工偏差 + T9 复查。
- [ ] 用户复核终判：pass / observation / blocker。
- [ ] 若 pass/observation：明确写"放行 Task 171 Ch200"结论。
- [ ] 更新 `tasks/V7-README.md` / `docs/STATUS.md` / `docs/v7-plan.md`。
- [ ] 产出 `tasks/170g-...-DONE.md` + 专项总结（回填 170 专项 README）。

## 专项收口

170g DONE 时，回填 `tasks/170-literary-quality-remediation-README.md` 的出口结论，并在 V7 文档中明确：文学提质专项完成、量具已可信、Ch200 是否放行。
