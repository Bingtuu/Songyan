# Task 163 DONE: 概念预算约束

> **Phase**: V7 阶段 W（篇章级质量修复）
> **完成时间**: 2026-07-04
> **结论**: 完成。已新增概念台账 MVP、概念预算约束构建、CreativeDirector 规划侧注入和 metrics 诊断段；保持规划侧约束与诊断告警，不做自动改写。

---

## 目标回放

Task 163 针对 V6 `run-bba292da` 中后段 conceptual_grounding 退化和概念通胀，要求：

- 约束单章新概念/新机构/新术语引入数量；
- 优先让已引入但未落地的概念通过行动/冲突落地；
- conceptual_grounding 下滑时触发预算收紧；
- 不引入自动 LLM 改写闭环，不新增 Agent/Workflow 节点。

## 已完成改动

| 模块 | 改动 |
|------|------|
| `src/songyan/evals/concept_budget.py` | 新增 `ConceptLedgerEntry`、`ConceptualGroundingPoint`、`ConceptBudgetReport`；实现概念台账构建、conceptual_grounding 下滑检测、概念预算约束文本构建、诊断报告采集与渲染。 |
| `src/songyan/agents/creative_director/__init__.py` | 在 CreativeDirector prompt 渲染时调用 `build_concept_budget_constraint`；有概念台账/收紧信号时把约束追加到现有“近期活跃设定”区块。无概念台账时返回空字符串，保持旧行为回退。 |
| `src/songyan/evals/db_metrics.py` | `render_stage_a_metrics` 追加“概念预算诊断”段，展示概念总数、未落地数、新概念预算、是否触发收紧。 |
| `tests/test_163_concept_budget.py` | 新增专项测试，覆盖台账构建、预算文本、收紧触发、DB 集成、CreativeDirector prompt 注入、无台账回退和 report 渲染。 |

## 设计口径

### 概念台账 MVP

- 来源：`setting_tracking`。
- 概念 key：`setting_key`。
- 引入章：`introduced_in_chapter`。
- 落地判定：`status == resolved`，或 `last_mentioned_chapter > introduced_in_chapter`。
- 忽略项：`archived` / `abandoned`。

### 概念预算

- 默认单章新概念预算：`2`。
- conceptual_grounding 触发收紧时，预算降为 `1`。
- 约束文本要求：
  - 优先落地/复用既有概念；
  - 非必要不造新概念；
  - 确需新概念时必须使用 `【设定推导】` 说明来源；
  - 列出最多 5 个未落地概念作为本章优先落地对象。

### 收紧触发

- 基于 conceptual_grounding 分数序列；
- 前 10 章作为 baseline；
- W=5 滑窗均值下降 `>=20%` 时触发；
- 只影响后续规划提示，不自动改写正文，不阻塞 accept。

## 验收点

- 能区分“引入后复用”的 grounded 概念与“引入后未提及”的未落地概念。
- 有未落地概念时 CreativeDirector prompt 包含“概念预算约束”。
- 无概念台账时不注入约束，保持旧行为回退。
- conceptual_grounding 下滑时预算收紧到 1。
- metrics 报告能展示概念预算诊断段。

## 验证

```powershell
python -m pytest tests/test_163_concept_budget.py tests/test_144_thread_economy.py tests/test_147_literary_trend.py -q
```

结果：`33 passed`

```powershell
python -m pytest tests/ -q
```

结果：`2308 passed, 2 skipped, 1 xfailed, 2 warnings`

```powershell
ruff check src/ tests/
```

结果：`All checks passed!`

## 边界

- 未做真实小窗口 LLM 复跑；conceptual_grounding 是否止跌留 Task 165 的 Ch150 复跑统一验证。
- 不做概念图谱、语义聚类或 embedding 相似度。
- 不做自动改写；只通过 CreativeDirector 规划侧约束影响后续生成。
- 不新增 Agent/Workflow 节点。

## 下一步

进入 Task 164：文本洁净度度量入库 + `songyan report` 展示（T9 harness）。
