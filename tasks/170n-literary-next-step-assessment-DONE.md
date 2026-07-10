# Task 170n：文学提质下一阶段方向评估 — DONE

> **专项**: 文学提质专项（`tasks/170-literary-quality-remediation-README.md`）
> **类型**: 方向评估 / 决策前置
> **优先级**: P0
> **依赖**: Task 170m 已完成
> **状态**: ✅ 评估已完成，等待用户最终决策
> **负责人**: songyan-agent

---

## 结论

Task 170m 校准后确认：voice/exposition 仍未达标，路径 B 轻量策略（170h→170l）已到顶。本任务对三条候选方向做了代码面调研与工程量评估。

**推荐顺序（由 songyan-agent 提出，待用户决策）**：
1. **首选方向 C（目标降级）+ 同步准备方向 B（AI 腔后处理）的最小可行版本**：
   - 方向 C 可以立即解除 Ch200 入口冻结，把文学修复从“放行前置门”转为“长跑中抽读+定点修复”，符合 V7 MVP 边界和当前资源约束；
   - 方向 B 的 RevisionHandler 后处理可作为长跑中的 171p/172p/173p 撞墙修复工具，不阻塞阶段 Z。
2. **方向 A（路径 B 升级）作为备选，但建议先跑最小可行小样本验证**：
   - 工程量最大、越界风险最高，只有在方向 C 长跑中 voice/exposition 继续塌陷时才值得投入。

**关键理由**：
- 路径 B 升级（方向 A）需要大幅重写 CreativeDirector/Writer/QualityGate，可能越界“不做全自动 LLM 改写闭环”的 V7 纪律，且模型可能换壳（说明性对白→说明性独白/叙事解释）。
- AI 腔后处理（方向 B）兼容现有架构，但样本库建设和质量稳定性成本不低，适合作为长跑中的定点工具而非放行前置门。
- 目标降级（方向 C）与 V7 MVP 边界完全兼容，且能把阶段 Z 重新推进；同时可以保留方向 B 的小范围后处理作为后续修复手段。

---

## 代码面调研结果

### 方向 A（路径 B 升级）改动面

- `src/songyan/agents/creative_director/_brief_builder.py`：新增“认知冲突前置模板”硬约束字段；`_build_creative_brief` 已支持 `voice_anchors`、`voice_samples`，可扩展新字段。
- `prompts/cards/creative_director/1.0.*.yaml`：增加对白-动作交替、非人实体台词配额等强制规则；当前最新卡为 1.0.6，170l 已新增 voice_samples 注入。
- `src/songyan/agents/writer.py`：在 prompt 组装时注入硬配额（台词字数、单句信息密度）。
- `src/songyan/agents/rule_auditor.py`：新增/强化 `human_voice_homogeneity`、`non_character_monologue_overflow` 扣分，接入 QualityGate。
- `src/songyan/workflows/_gates.py`：QualityGate 增加文学硬约束扣分项；当前只有 continuity/context/health_low 门禁，quality gate 在 `ScoreAggregator` 层。
- 风险：越界“不做全自动 LLM 改写闭环”，模型可能换壳，生成速度/成本显著上升。
- **估算**：8–12 个文件，15–25 个新增单测，2–3 轮小样本验证。

### 方向 B（AI 腔后处理）改动面

- `src/songyan/agents/revision_handler/__init__.py`：已支持 readability 专精路径和 literary 优化插件注入（Task 170l）。可在 `_build_readability_issues` 中新增 exposition carrier issue → ReviewIssue 转换。
- `src/songyan/agents/revision_handler/` 下新增 `literary_patches.py`：实现说明性对白压缩、反模板化句式替换、声纹同质化拆分。
- `prompts/cards/revision_handler/1.1.*.yaml` 或新增 `1.2.0.yaml`：加入后处理专用 prompt。
- `src/songyan/literary_optimization/strategies/`：可新增 `ai_tone_rewrite.py` 策略，复用现有 `_REGISTRY` 注册表（`registry.py` 已支持 AiToneBlocklistStrategy、FewShotVoiceAnchorStrategy、MinimalVoiceAnchorStrategy、OpposingGoalAnchorStrategy，新增策略只需 import 并注册）。
- 风险：局部改写破坏连贯性，样本库不足时质量不稳定。
- **估算**：4–6 个文件，10–15 个新增单测，1 轮小样本验证。

### 方向 C（目标降级）改动面

- `docs/v7-plan.md` / `tasks/V7-README.md` / `tasks/170-literary-quality-remediation-README.md`：更新 Ch200 入口标准，明确降级后的“不劣化”口径。
- `src/songyan/workflows/_nodes.py` 或 `phase2_graph.py`：增加长跑中每 N 章触发 LiteraryAuditor + RuleAuditor 联合抽读并生成报告。
- `scripts/run_171_ch200_long_run.py`（新建）：启动 Ch200 长跑，内置抽读窗口和 halt 条件。
- 风险：文学债可能累积，需要人工抽读纪律。
- **估算**：2–4 个文件，5–8 个新增单测，无额外 LLM 成本（复用现有审查）。

---

## 三向评估表（量化）

| 维度 | 方向 A | 方向 B | 方向 C |
|------|--------|--------|--------|
| 预计改动文件数 | 8–12 | 4–6 | 2–4 |
| 新增单测数 | 15–25 | 10–15 | 5–8 |
| LLM 调用成本增量 | 高（每章可能多 1–2 次） | 中（只在 revision 命中时） | 低（抽读时可选 LLM） |
| 对现有管线稳定性影响 | 高 | 中 | 低 |
| 越界 V7 MVP 风险 | 高 | 低 | 无 |
| 预期 Ch200 放行时间 | 慢（需小样本验证+全量复评） | 中 | 快（可立即启动） |
| 可回退性 | 中 | 中 | 高 |

---

## 建议执行方案

### 如果用户选择方向 C（推荐）

1. 创建 Task 171 规划文档：**Ch200 长跑 + 降级后文学口径 + 抽读纪律**。
2. 明确降级后的量化标准：
   - pacing ≥ 3.0、concept ≥ 3.0、ai_tone ≥ 2.5（不回退）；
   - voice ≥ 2.0、exposition ≥ 2.0（不继续塌陷）；
   - T9 0/0、exposition_carrier 高置信 ≤ 3；
   - 每 25 章人工抽读，发现 voice/exposition 连续 2 窗 < 2.5 时触发 halt。
3. 启动 Ch200 长跑脚本，内置抽读与 halt 逻辑。
4. 同步把方向 B 的 RevisionHandler 后处理作为 171p 撞墙修复工具预留。

### 如果用户选择方向 B

1. 先建最小样本库：从 170m 校准后的“好对白”段落 + 外部人工示例中提取 10–20 条。
2. 实现 RevisionHandler 的说明性对白压缩 patch。
3. 在 Ch29–Ch32 跑小样本验证，确认不劣化后再接入主流程。

### 如果用户选择方向 A

1. 先实现最小可行版本：仅给 Writer 增加“说明性对白后必须跟动作/冲突反应”的硬节拍。
2. Ch29–Ch32 小样本验证；若 voice/exposition 不达 3.0，立即回退到方向 C。

---

## 验证清单

- [x] 完成三向评估文档。
- [x] 对每条方向输出核心假设、子策略、预期收益、风险、回退点、改动文件清单。
- [x] 完成代码面调研（Writer/CreativeDirector/RevisionHandler/QualityGate 扩展点）。
- [x] 给出推荐方向及理由。
- [x] 更新 `docs/STATUS.md`、`tasks/V7-README.md`、`tasks/170-literary-quality-remediation-README.md`、`README.md`。
- [x] 回填本 DONE 文档。

---

## 交付物

- `tasks/170n-literary-next-step-assessment.md`
- `tasks/170n-literary-next-step-assessment-DONE.md`
- `docs/reports/task-170n-literary-next-step-assessment-report.md`
- 更新后的 `docs/STATUS.md`、`tasks/V7-README.md`、`tasks/170-literary-quality-remediation-README.md`、`README.md`

---

## 关键判定记录

> **170n 评估结论**：路径 B 轻量策略已到顶，不建议继续追加同层级约束。
> **推荐**：方向 C（目标降级）+ 同步准备方向 B（AI 腔后处理）作为长跑中的定点修复工具。
> **决策权**：最终方向由用户决定；决定后立即进入对应 Task（171 或 170n-B 小样本验证）。
