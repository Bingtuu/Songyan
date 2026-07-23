# Task 170n：文学提质下一阶段方向评估（路径 B 升级 / AI 腔后处理 / 目标降级）

> **专项**: 文学提质专项（`archive/v7/tasks/170-literary-quality-remediation-README.md`）
> **类型**: 方向评估 / 决策前置
> **优先级**: P0
> **依赖**: Task 170m 已完成（量具二次校准确认：170l 原 exposition_carrier=72 校准为 6，但 voice/exposition 仍未达 Ch200 放行线）
> **状态**: ✅ 已完成
> **负责人**: songyan-agent

---

## 任务边界

Task 170m 完成后，已经确认：
1. **量具可信**：exposition carrier 检测器经动态化 + ground truth 校准后，候选集 P/R/F1 = 1.0；170l 的 72 处计数主要受硬编码关键词和跨段落伪引语放大。
2. **文学维度仍未达标**：voice 2.00 / exposition 2.00 / 窗口均值 2.40，不满足 Ch200 入口标准（voice≥3.0、exposition≥3.0、窗口均值≥3.0、exposition_carrier≤1、T9 0/0、偏差<3 分）。
3. **路径 B 轻量策略到顶**：170h→170i→170j→170k→170l 连续五步，收益递减/劣化，继续追加同层级约束不可行。

本任务目标：在投入下一轮工程前，对三条候选方向做量化评估——**路径 B 升级**、**AI 腔后处理**、**目标降级**，输出工程量、预期收益、风险、回退点，供用户决策。

**本任务不改生成侧代码，只做评估、文档和可能的小范围验证脚本。**

---

## 三条候选方向

### 方向 A：路径 B 升级（更激进结构性改写）

**核心假设**：当前失败是因为约束不够硬。如果像 enforce 治理管线那样，给 Writer/CreativeDirector 增加不可绕过的硬节拍和配额，可以强制 voice/exposition 达标。

**候选子策略**：
1. **人类角色台词硬配额**：单个人类角色单章台词字数上限、单句信息密度上限。
2. **非人实体信息投递硬限制**：非人实体单句最多 N 个高概念词、单章最多 M 句直接揭示。
3. **对白-动作交替硬节拍**：任何说明性对白后必须跟动作/冲突/失败反应，否则触发 RevisionHandler patch。
4. **认知冲突前置模板**：CreativeDirector 强制要求每章至少 2 处“主角误判→对立判断→付出代价→修正认知”节拍。
5. **声纹降级惩罚**：人类角色对白同质化（detect_human_voice_homogeneity 命中）直接扣 quality gate 分，触发 rewrite。

**预期收益**：理论上可以硬压 exposition/voice 达标。
**风险**：
- 工程量大，可能触碰 AGENTS.md“不做全自动 LLM 改写闭环”边界；
- 硬约束可能让模型把“说明性对白”换成“说明性内心独白/叙事解释”，换壳不解决问题；
- 可能显著拖慢生成速度、提高 LLM 成本；
- 可能引入新的 meta_tag / 字数异常 / 场景碎片化。
**回退点**：如果 Ch29–Ch32 小样本复评仍不达标，直接判定当前 deepseek-chat 在该 prompt 深度下不可行，转向方向 C。

### 方向 B：AI 腔后处理（反模板化 rewrite 规则）

**核心假设**：模型输出本身带有模板化、说明性、排比句等 AI 腔，单靠 prompt 约束不够，需要在 RevisionHandler 层做硬性后处理。

**候选子策略**：
1. **说明性对白压缩**：RevisionHandler 检测到 `info_delivery_dialogue` / `direct_revelation_monologue` 时，直接压缩或拆成动作+短对白。
2. **反模板化改写**：针对高频 AI 腔句式（“不是不想…是…”、“这个认知像…”、“他从一开始就在…”）做规则化改写。
3. **声纹同质化拆分**：对 detect_human_voice_homogeneity 命中的角色对白，强制插入语气词、打断、口癖、动作反应差异。
4. **自动 few-shot 替换**：从人工审定的“好对白”样本库中抽取替换模板。

**预期收益**：不改动 Writer 创作自由度，只在后处理层削峰，实施相对可控。
**风险**：
- 局部改写可能破坏上下文连贯性；
- 需要大量人工样本库才能达到“不劣化”质量；
- 改写后仍需重新跑 RuleAuditor/LLMAuditor，可能引入新的 T9/重复问题；
- 仍然可能换壳（把长对白换成长内心独白）。
**回退点**：如果后处理样本无法稳定提升 voice/exposition，转向方向 C。

### 方向 C：目标降级（诚实降级文学目标）

**核心假设**：当前 deepseek-chat + 当前 prompt 工程深度，在 V7 MVP 边界内无法稳定让 voice/exposition 同时 ≥3.0。继续攻坚的边际收益低于长跑验证的边际收益。

**子策略**：
1. 把文学质量目标从“voice/exposition ≥3.0”调整为：
   - 不劣化 pacing/concept（≥3.0）；
   - voice/exposition 保持 ≥2.0 且不继续塌陷；
   - T9 0/0、exposition_carrier 高置信 ≤3；
   - 长跑中每 25 章人工抽读，发现问题定点修复。
2. 启动 Task 171 Ch200 长跑，把文学修复从“放行前置门”改为“长跑中持续抽读+定点修复”。
3. 预留 171p/172p/173p 撞墙修复占位，允许在长跑中尝试方向 A/B 的小范围 patch。

**预期收益**：阶段 Z 可以继续推进，取得 Ch200/Ch250/Ch300 真实证据；避免无限期卡在文学专项。
**风险**：
- 文学质量债可能随长跑放大；
- 需要明确“不劣化”的量化口径和人工抽读纪律；
- 后续修复成本可能更高（发现越晚，影响越大）。
**回退点**：如果 Ch200 长跑中 voice/exposition 继续塌陷，再回滚到方向 A/B。

---

## 评估维度

| 维度 | 方向 A | 方向 B | 方向 C |
|------|--------|--------|--------|
| 工程量（人天） | 大 | 中 | 小 |
| LLM 调用成本增量 | 高 | 中 | 低 |
| 对现有管线影响 | 大（可能改 Writer/CreativeDirector/QualityGate） | 中（主要改 RevisionHandler） | 小（主要改放行标准与抽读纪律） |
| 预期 voice/exposition 提升 | 高（若假设成立） | 中 | 无直接提升，但阻止继续塌陷 |
| 引入劣化/换壳风险 | 高 | 中 | 低 |
| 与 V7 MVP 边界兼容性 | 可能越界 | 基本兼容 | 完全兼容 |
| 可回退性 | 中 | 中 | 高 |

---

## 验收标准

- [ ] 完成三向评估文档（本文件）。
- [ ] 对每条方向输出：核心假设、子策略、预期收益、风险、回退点、大致改动文件清单。
- [ ] 给出推荐方向及理由（由用户最终决策）。
- [ ] 更新 `docs/STATUS.md`、`tasks/V7-README.md`、`archive/v7/tasks/170-literary-quality-remediation-README.md`、`README.md`。
- [ ] 回填 `archive/v7/tasks/170n-literary-next-step-assessment-DONE.md`。

---

## 执行顺序

1. 建立本 task 文档（当前步骤）。
2. Review task 文档。
3. 调研代码改动面：
   - Writer / CreativeDirector / RevisionHandler / RuleAuditor 当前接口与扩展点；
   - `literary_optimization` 插件注册表是否支持新增策略；
   - QualityGate 是否支持新增硬约束扣分。
4. 评估每条方向的工程量和风险。
5. 创建小范围验证脚本（可选）：
   - 方向 A：在 Ch29–Ch32 跑一次“硬配额”实验；
   - 方向 B：在 RevisionHandler 加一层说明性对白压缩规则并跑 Ch29–Ch32；
   - 方向 C：制定降级后的量化口径。
6. 汇总评估报告。
7. 请用户决策。
8. 更新状态文档并回填 DONE。

---

## 风险与回退

| 风险 | 缓解 |
|------|------|
| 评估过于理论化 | 对方向 A/B 做小样本（Ch29–Ch32）快速验证，用真实数据支撑 |
| 用户方向选择后工程超支 | 评估中明确每个方向的最小可行版本（MVP）和回退触发条件 |
| 方向 C 放行后文学债累积 | 制定明确的抽读纪律和 halt 触发条件 |

---

## 交付物

- `archive/v7/tasks/170n-literary-next-step-assessment.md`（本文件）
- `archive/v7/tasks/170n-literary-next-step-assessment-DONE.md`
- `archive/v7/reports/task-170n-literary-next-step-assessment-report.md`（评估报告）
- 可能的小范围验证脚本（`scripts/run_170n_*_probe.py`）

---

## 下一步

等待用户 review 本 task 文档并确认评估方向后，开始执行三向评估。
