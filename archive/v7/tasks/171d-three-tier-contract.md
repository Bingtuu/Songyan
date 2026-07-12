# Task 171d: 三层契约落地（框架 §8 A 组 —— A1 报告分层 + A3 Tier2 趋势地板/抽读 + A4 标定）

> **框架**: `docs/reports/v7-literary-framework-review.md` §8 **A 组**（A1/A3/A4；A2 行为层已达标）+ §6.1 三层契约
> **类型**: 契约落地（observe-only，不新增阻塞门）
> **优先级**: P1（阶段 PASS 缺口——A 组是 §8 五组之一）
> **依赖**: 171a/171a-1（可信量具）+ 171b（分层与标定语料）
> **状态**: ✅ **完成（A1/A3/A4 达标；见 `171d-three-tier-contract-DONE.md`）**
> **负责人**: songyan-agent

---

## 立项依据（代码级审计，2026-07-10）

对框架 §8 A 组做代码级核实，发现原表述把"三层契约"写得像已实现机制，实际：

- **A2 达标但属涌现属性**：文学分（voice/exposition/rubric）从不阻塞（quality gate 只判 length/budget/coherence/momentum/readability 五维；LiteraryAuditor 明确不阻塞）；T9 硬缺陷经 `review_merger` 提为 major/critical 仍阻塞。→ "Ch200 不被文学阻塞"在代码层为真。
- **A1 缺失**：`songyan metrics` 扁平拼接各段（`db_metrics.render_stage_a_metrics`），**无 Tier 1/2/3 分层视图**、硬缺陷与趋势/研究值不分离。
- **A3 缺失**：现有 `detect_literary_trend` 是 `×0.80`（20% 跌幅）、observe-only、未接抽读；**无 `×0.85` 地板 + 人工抽读触发**。
- **A4 缺失**：`baseline_n=10 / drop=0.20 / window=5` 均硬编码，非真实数据标定。

## 任务边界

**只做 observe 层落地，不新增任何阻塞门、不改冻结口径、不做 LLM 闭环。** 把"三层契约"从文档概念变成 metrics 出口的**可见、可复算**结构；Tier 2 趋势地板跌破只产出**人工抽读建议**（标志位 + 报告行），绝不 auto-block。

## 目标

1. **A1 三层分层视图**：在 `render_stage_a_metrics` 顶部新增"三层契约摘要"段，把已采集信号归类——
   - Tier 1 硬缺陷：T9（meta 泄漏 / 整段重复 / 时间线）——沿用既有阻塞语义，此处只汇总展示。
   - Tier 2 趋势：文学 rubric（voice/exposition/pacing/concept）趋势地板状态（observe）。
   - Tier 3 研究值：voice/exposition 原始读数（171a-1 已验证效度，供研究，不判定）。
   - 三类**分区标注、互不混淆**，每类标明是否阻塞。
2. **A3 Tier2 趋势地板 + 抽读触发**：新增 `detect_literary_spot_read`（复用 `detect_literary_trend` 结构）——滚动窗口均值 ≥ 首段基线 ×0.85 **且** ≥ 低绝对地板；跌破任一→输出 `spot_read_recommended=True` + 触发维度 + 首破章，**observe-only**（不接任何 halt/gate）。
3. **A4 参数标定**：用真实长跑语料（171b 的 scifi 170p + wuxia 171a-1 + 历史 170i DB）计算各维度基线分布，给 `×0.85` 系数、绝对地板、window/baseline_n 一个**可复算的数据依据**（脚本 + 报告），替换"拍脑袋"口径或显式声明沿用值的理由。

## 验收标准（对应框架 §8 A 组）
- **A1**：metrics 出口出现三层分区摘要，Tier 1/2/3 分列、标注阻塞性，互不混淆；有单测锁定分类。
- **A3**：`detect_literary_spot_read` 落地（×0.85 地板 + 绝对地板 + 抽读标志），observe-only（代码中无 gate/halt 接线，有测试证明不阻塞）；渲染出"抽读建议"行。
- **A4**：标定脚本 `scripts/run_171d_calibrate.py` 产出各维度基线 + 参数依据报告；`detect_literary_spot_read` 采用标定值或显式声明沿用理由。
- 工程：`ruff`/pytest 通过；不新增阻塞门；不放宽冻结口径。

## 交付物（预期）
- `src/songyan/evals/db_metrics.py`：`detect_literary_spot_read` + 三层契约摘要渲染。
- `scripts/run_171d_calibrate.py`（基线标定）。
- `docs/reports/task-171d-three-tier-contract-report.md`（标定依据 + 分层视图样例 + observe-only 证明）。
- `tests/test_171d_three_tier_contract.py`。
- `tasks/171d-three-tier-contract-DONE.md`。

## 明确不做
- 不把 Tier 2 趋势地板接成自动阻塞（只出抽读建议）；不改 T9/T10/T5/T6/T12 冻结阈值；不新增 Agent/节点；不做全自动 LLM 改写闭环；不阻塞 Ch200 主线。
