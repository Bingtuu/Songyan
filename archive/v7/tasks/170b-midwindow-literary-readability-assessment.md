# Task 170b: 中段窗口真实生成 + 文学性/可读性实读评估（Ch200 前置文学 gate）

> **Phase**: V7 阶段 Y→Z 之间的前置验证
> **优先级**: P0（Task 171 Ch200 长跑的文学放行前置）
> **状态**: ◻ 规划中（本文档待用户确认后再执行；执行会消耗真实 LLM API）
> **依赖**: Task 170 DONE（T12 冻结）；复用 157b 生成脚手架、LiteraryAuditor、T9 harness
> **事实入口**: `tasks/V7-README.md`；规划 `docs/v7-plan.md` 阶段 Z

---

## 为什么要有这个任务（问题陈述）

过去所有 "X/X accept" 的成功，**衡量的是治理与事实源质量，不是文学质量**：

1. QualityGate 读的 `readability` 只是规则级代理（短段落比例、AI 腔密度、疲劳词），能拦"机械的烂"，拦不住"干净但无聊"。
2. LiteraryAuditor 只诊断、不阻塞 accept（AGENTS.md 硬边界）——文学维度从未进入"能否通过"的判定。
3. 长跑用 `--auto-confirm`，人工确认被跳过——"accept" 与"好不好看"基本脱钩。

叠加 V7 决策边界 2（文学修复保守，不做全自动 LLM 改写闭环）：**当前管线结构上不会自动修复 prose 质量**。因此若 Task 171 照旧跑，大概率得到"200/200 accept、事实源健康、但读起来平淡"的空心胜利。

**本任务在 Ch200 长跑前插入一道"文学 gate"**：用真实生成的中段窗口，人工实读确认 prose 的真实水位与机器诊断的可信度，给出"直接爬坡 / 先提质再爬坡"的证据结论。

## Goal

用真实 LLM 生成中段窗口（Ch1–Ch40），抽读 Ch28–Ch40，回答三个问题：

1. **当前 prose 的文学水位在哪？**（中段窗口——设定累积、上下文变长后 prose 是否衰减，正是主要担心的场景）
2. **机器诊断可不可信？**（LiteraryAuditor 4 维分 vs 人工实读分，偏差多大——机器失真是比 prose 差更底层的缺陷）
3. **够不够格进 Ch200？**（pass / observation / blocker）

## 边界

- 不启动 Ch200；本任务只跑到 Ch40。
- 不改 Writer / RevisionHandler / CreativeDirector / SettlementExtractor（本任务是评估，不是提质）。
- 不做自动 LLM 改写闭环。
- 不放宽 T9/T10/T5/T6/T12 冻结口径。
- 不改变 LiteraryAuditor 不阻塞 accept 的现状（本任务的"文学 gate"是人工判定 gate，不是代码 gate）。
- 若评估结论为 blocker，提质工作另开任务（可能是生成侧工艺卡迭代），不在本任务内实现。

## 分工

- **助手（初筛）**：跑生成 → 抽 Ch28–Ch40 正文 → 取机器分（LiteraryAuditor 4 维）→ 按 5 维 rubric 做 LLM 初评 → **标出可疑段落 + 机器/人工可能偏差大的地方** → 生成结构化评分表和正文摘录。
- **用户（复核重点）**：只读助手标出的重点段落和偏差项，做最终文学判断，给每维终评分。

## 5 维 rubric（对齐已有机器维度，1–5 分；1=差 5=好）

| 维度 | 对应机器信号 | 差(1) → 好(5) |
|------|------------|---------------|
| AI 腔密度 | `ai_rhythm_pattern` / RuleAuditor ai_tell | 句式模板化、排比堆砌、万能过渡句 → 句式自然多变 |
| 角色声纹区分度 | `polyphony_weakness` / character_autonomy_score | 谁说话都一个腔 → 对白可辨身份、有个体语气 |
| 概念空转 | `conceptual_idling` / conceptual_grounding_score | 科幻名词砸脸不落地 → 概念有具体质感与后果 |
| 说明文堆叠 | `authorial_intrusion` / `excessive_smoothing` | 大段解说 / 设定清单式交代 → 信息融进动作与场景 |
| 场景节奏 | momentum_score / `excessive_smoothing` | 平铺无张力 / 停滞 → 有推进、有张弛呼吸 |

每维给：窗口均值 + 最差样本章号 + 证据引文。

## 复用的现有工具（勘查已确认）

| 能力 | 复用 | 备注 |
|------|------|------|
| 起真实生成 run | `run_project_pipeline`（`workflows/phase2_graph.py`）；脚手架仿 `scripts/run_157b_ch1_ch50.py` | 改窗口到 Ch1–Ch40 |
| 大纲种子 | 157b 内联 `_build_outline`（6 弧 / 3 主线，Ch1–40 完全覆盖） | 无需外部 outline 文件 |
| 抽 accepted 正文 | `ChapterHeadRepository.get/list_by_project` + `ChapterVersionRepository.get` | 走 head 指针取 accepted 版本 |
| 文学分 | `LiteraryObservationRepository.list_scores_by_chapter_range(project_id, start, end)` | run 默认已写库；每章取最新一条 |
| run log | `read_run_logs(run_id)`（`evals/streaming_report.py`） | **注意：run log 无文学分字段**，文学分只在 literary_observations 表 |
| T9 洁净度 | `refresh_text_cleanliness_metrics(project_id, 28, 40)` 复算后 `load_...` | **该表 run 中不自动填**，抽读前须先 refresh |

## In Scope

- [ ] 中段窗口生成脚本 `scripts/run_170b_midwindow_generation.py`（复用 157b 脚手架，窗口 Ch1–Ch40，隔离 DB `.tmp/task170b_ch1_ch40.db`，enforce + isolate）。
- [ ] 抽读导出 + 评估工具 `scripts/run_170b_readability_assessment.py`：
  - 抽 Ch28–Ch40 accepted 正文（供人工阅读，导出为 markdown）。
  - 取 LiteraryAuditor 4 维分数。
  - 复算 + 读 T9 洁净度。
  - 拉 run_log 关键字段（quality_gate_passed / continuity health / degraded_accept）。
  - LLM 初评 + 标可疑段落 + 机器/人工偏差候选。
  - 汇总成结构化评估表。
- [ ] 评估报告 `archive/v7/reports/task-170b-literary-readability-assessment-report.md`。
- [ ] 人工复核记录（用户终评分写入报告）。

## Out of Scope

- 不启动 Ch200 / Ch250 / Ch300。
- 不改生成侧任何 Agent 或 prompt / 工艺卡。
- 不做自动改写。
- 不新增 LangGraph 节点。
- 不把文学分接入 QualityGate（不改 accept 行为）。

## 执行阶段（用户确认后逐步执行）

1. **生成阶段**（消耗真实 LLM API，耗时长）：跑 `run_170b_midwindow_generation.py`，产出 Ch1–Ch40 accepted 正文 + literary_observations + run log。中途 AutoHalt 则记录并按需 resume。
2. **抽读导出阶段**：跑 `run_170b_readability_assessment.py`，导出 Ch28–Ch40 正文、机器分、T9、run_log 汇总，生成初评 + 偏差候选。
3. **人工复核阶段**：用户读助手标出的重点，给 5 维终评分。
4. **结论阶段**：综合成报告，给 pass / observation / blocker 判定。

## 判定标准

| 结论 | 含义 | 后续 |
|------|------|------|
| **pass** | 5 维均值达标（建议 ≥3/5），无单维塌陷；机器/人工偏差可接受；T9 硬红线=0 | 允许规划 Task 171 Ch200（171 首窗仍抽读） |
| **observation** | 有轻微文风债但不影响爬坡；或机器诊断有偏但方向对 | 记录债项，可进 Ch200，但 Task 171 需带文学抽读 |
| **blocker** | prose 明显不足（多维塌陷）或机器诊断严重失真 | **先开提质任务，暂缓 Ch200** |

## 关键风险与提醒

- **真实 LLM 成本**：Ch1–Ch40 是真实 API 调用（生成 + 多轮审查），耗时长，需正确配置 LLM 环境。
- **enforce AutoHalt**：enforce 门禁遇候选硬门禁会暂停；若纯为抽读可评估用 observe，但需与"enforce 为默认"纪律权衡（默认仍用 enforce，AutoHalt 则记录并 resume）。
- **开局高估风险**：选中段窗口正是为了避免开局窗口（设定少、上下文轻）高估真实水位。
- **文学分不入 run log**：抽读工具必须从 literary_observations 表取分，不能依赖 run log。
- **T9 表需手动 refresh**：抽读前先复算，否则读到空。

## 与 Task 171 的关系

本任务是 Task 171 的**文学放行前置**。只有 170b 结论为 pass 或 observation，才规划 Task 171；若 blocker，先做生成侧提质，再回到 170b 复评。
