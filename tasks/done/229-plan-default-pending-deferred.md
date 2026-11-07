# 229 · plan 模型 approval_status 默认值（搁置）

| 项 | 内容 |
|---|---|
| 状态 | DONE（搁置记录） |
| 关联 | 全量评审 minor #5（`src/songyan/models/plan_facts.py` 五模型 `approval_status` 默认 `"approved"`） |
| 预估 | —（未实施） |

## 结论：搁置，待 owner 书面拍板

**发现**：五个 plan 模型（`PlanEntity` / `PlanAttribute` / `PlanEvent` / `PlanTimeAnchor` / `PlanClue`）的 `approval_status` 字段默认 `"approved"`。任何不显式传状态构造卡片的调用方即直写 Canon，绕过 pending 队列——这是与本产品「确认才入典」核心边界相悖的开放坑。

**评审建议**：默认改 `"pending"`，由计划层 / 夹具加载器（`load_plan_fact_fixture`）显式传 `"approved"`。

**搁置理由**：这是**行为变更**——种子夹具（都市灵异《末班铜牌》、霞飞路卡）、`canon edit` 之外的既有写入方可能依赖默认值。按 AGENTS.md 开工门，行为变更需 owner 书面授权；本次推进处于 autonomous 模式，无法取得拍板，故不实施，避免未授权改变写入语义。

**若 owner 批准，实施要点**（留给后续任务）：
1. 五模型默认值改 `"pending"`；
2. `load_plan_fact_fixture` 等计划层写入方显式传 `"approved"`（夹具语义 = 人已批准的卡）；
3. 全量回归（重点：`tests/db/test_plan_fact_cards.py`、`tests/plan_checks/`、M0–M2 CLI 测试）；
4. TDD：新增「不显式传状态即 pending」的模型级测试。

## 完成总结

记录完成：搁置理由、实施要点、风险面均已写明。无代码改动。
