# Task 170f: pacing 节奏 + exposition 融合提质

> **专项**: 文学提质专项（`tasks/170-literary-quality-remediation-README.md`）
> **类型**: 检测补强 + 生成侧提质（中风险——碰 RuleAuditor + 生成链）
> **优先级**: P0（pacing 用户通读确认偏慢；exposition 硬灌）
> **依赖**: 170d DONE（可信量具）、170e DONE（seeding 修复，声纹机制已激活）
> **状态**: ▶ Stage 1 — 生成侧提质（Stage 0 已跑，结论：代码指标不可靠 → 转纯生成侧）

---

## 问题（170b 实证）

- **pacing 2.4/5（用户通读确认偏慢）**：中段大量单人解谜 + 日志比对 + 意识流，**场景切换少、他者互动稀**，节奏拖沓。
- **exposition 2.1/5（偏弱）**：设定 / 协议靠内心独白、日志比对硬灌，信息未融进动作。

两者同源——**过度依赖单人内心独白与说明性铺陈**，因此合并为一个任务。

## 认知修正（查证代码得到）

**Writer 1.2.0 有大量相关文字约束，但 RuleAuditor 无对应代码检测**——已逐条核实：

- 文字约束存在：`paragraph_rhythm`（`writer/1.2.0.yaml:277`）、`info_release`（`:331` 禁连续 300 字纯说明）、`show_dont_tell`（`:295` 认知动词黑名单）、场景切换（`:222` 2–4 场景/≥600 字）；CreativeDirector 1.0.6 有【节奏地图】【行动承载】。
- **RuleAuditor 无 monologue/exposition 检测**：grep `rule_auditor.py` 的 `monologue/exposition/独白/说明` 检测函数**零命中**。现有观测指标只有 `_short_paragraph_ratio`（`:210`）、`duplicate_paragraph_count`、`scene_count`（`_split_scenes` `:203`）。
- **观测指标模式已成型**（可照抄）：`short_paragraph_ratio` 在 `run_rule_audit`（`:387`）计算 → 存入 `RuleAuditResult`（`models/review.py:182`）→ 在 `_generate_summary`（`:569`）按阈值出提示 → **不计入 `_compute_overall_score`（`:486`）**。这是"先观测不阻断"的落地范式。

**关键缺口**：约束写在 prompt 里但**没有代码去查**——"连续内心独白 / 说明段落 / 场景切换稀疏"无法量化、无法进审查反馈、无法在 170g 复评时客观对比。约束写了但没人查，模型自然容易违反。

## 认知修正 2（阈值不能拍脑袋——必须数据校准）

亲读 170b 正文发现：**Ch28（人工 pacing=3，全窗口最佳）反而是短段落密集的动作章**（大量 1–2 句短段），而 Ch33/39/40（pacing=2）才是独白/日志堆叠。所以：

- "长段落 = exposition"**证伪**——不能用段落长度naive判 pacing。
- 真正区分"慢"章的信号更可能是 **对白密度低 + 最长连续非对白叙述块长 + 场景切换稀**。
- 因此**先写校准脚本**在 Ch28–Ch40 上算候选指标、与人工 pacing 分（Ch28=3 好；Ch33/39/40=2 差）做区分度检验，**能区分才落为检测项**；区分不了就是发现（记录，不强行造坏指标）。这继承 170c/d/e 的"复现/校准脚本先行"纪律。

## Goal（已修正——Stage 0 负结果）

1. ~~Stage 0 校准~~ ✅ **结论：简单代码指标无法可靠区分 pacing 好/慢章**（见下方 Stage 0 结论）。
2. **Stage 1（原 Stage 2）生成侧提质**：在 Writer 1.1.0 卡中新增 `scene_interaction` 段落，直接约束 170b 失败模式（单人解谜、无他者互动）。
3. **Stage 2 小样本验证**：隔离 DB 重生成 Ch29-32，用 170d LiteraryAuditor 验证 pacing/exposition 改善。

## Stage 0 — 校准结论 ✅（已跑，负结果）

`scripts/calibrate_170f_pacing_metrics.py` 在 Ch28-Ch40 上算了 4 个候选指标，对照 170b 人工 pacing 分（≥3=好，≤2=慢）：

| 指标 | 区分能力 | 结论 |
|------|----------|------|
| `dialogue_paragraph_ratio` | ❌ 反向 | 好章（Ch28）对白密度反而低于部分慢章——动作戏对话少 |
| `max_narration_run_chars` | ❌ 反向 | 好章（Ch28）最长叙述块反而更长——动作描写也是叙述 |
| `monologue_ratio` | ❌ 弱 | 区分度不足，噪声大 |
| `scene_switch_density` | ❌ 混淆 | `_split_scenes` 是段落计数，非真正场景切换 |

**诚实结论**：pacing 是语义概念，"单人解谜无互动"需理解角色关系和场景内容才能判定——简单代码指标不可靠。**不强行落坏指标**，转为纯生成侧约束。

## Stage 1 — 生成侧提质（Writer 1.1.0 卡修补）

**170b 失败模式定义**：章节中主角长时间独自分析线索/推理/回忆，无任何其他角色在场互动，导致叙事节奏拖沓、信息以独白形式硬灌。

Writer 1.1.0 现有约束已覆盖：`paragraph_rhythm`（段落节奏）、`info_release`（禁连续 300 字纯说明）、`show_dont_tell`（认知动词黑名单）、`dialogue_basics`（禁直白独白）。**但缺少对"整章无他者互动"的显式约束**。

- [ ] 新增 `scene_interaction` 段落：要求每章至少 1 个多人互动场景、禁止整章单人解谜、连续单人叙述上限 500 字。
- [ ] 追加到 `sections` 列表，确保渲染生效。

## Stage 2 — 小样本验证

- [ ] 隔离 DB 重生成 Ch29-32（170b 慢章窗口），用 170d LiteraryAuditor 对比改善。
- [ ] 人工通读抽样，确认 pacing/exposition 分数提升。

## In Scope / Out of Scope

**In**：Stage 0 校准脚本（✅ 已完成）；Stage 1 Writer 1.1.0 卡 `scene_interaction` 段落新增；Stage 2 小样本验证。

**Out**：
- ~~不做 RuleAuditor 代码检测落地~~（Stage 0 证明代码指标不可靠，已取消）。
- 不做全自动 LLM 改写闭环（V7 边界 2）。
- 不在 LiteraryAuditor 加 pacing 语义维度（170d 已明确归生成侧路径）。
- 不改 170d 量具判定标准；不启动 Ch200；全窗口复评归 170g。
- 不新增 LangGraph 节点 / Agent。

## 风险提示

- **生成侧约束可能不被模型遵循**：prompt 约束不等于模型执行——Stage 2 小样本验证是关键 gate。
- **碰 Writer 卡 + 生成链**：跑 `test_writer.py`、`test_creative_director.py`、全量。
- **Writer 卡版本**：线上实际 1.1.0，改前已确认。

## 验证要求

```powershell
# 相关回归（不再碰 rule_auditor）
python -m pytest tests/test_writer.py tests/test_creative_director.py -q
ruff check src/ tests/ scripts/
python -m pytest tests/ -q
```

## 验收标准

- [ ] Stage 0 校准结论已写入 DONE：4 指标全部无法可靠区分，转为纯生成侧。
- [ ] Writer 1.1.0 卡新增 `scene_interaction` 段落，渲染生效（tags 无条件，始终激活）。
- [ ] 小样本重生成（Ch29-32）170d LiteraryAuditor pacing ≥ 3.0、exposition ≥ 2.5。
- [ ] 全量测试 + ruff 通过。
- [ ] 产出 `tasks/170f-...-DONE.md`。

## 与 170g 的衔接

170f 给 170g 提供**生成侧 pacing/exposition 约束**（Writer 卡 `scene_interaction` 段落）。170g 复评中段窗口时：
- 用 170d LiteraryAuditor 对比修复前后 pacing/exposition 分；
- 结合人工抽读，综合判定是否达 pass/observation。
- 若模型不遵循生成侧约束（Stage 2 验证失败），则 pacing 需更深度介入（如 CreativeDirector 章节目标层面控制），归 170g 决策。
