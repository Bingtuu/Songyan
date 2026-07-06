# Task 170f: pacing 节奏 + exposition 融合提质

> **专项**: 文学提质专项（`tasks/170-literary-quality-remediation-README.md`）
> **类型**: 生成侧提质 + 检测补强（中风险——碰生成链）
> **优先级**: P0（pacing 用户通读确认偏慢；exposition 硬灌）
> **依赖**: 170d DONE（可信量具）
> **状态**: ◻ 规划中

---

## 问题（170b 实证）

- **pacing 2.4/5（用户通读确认偏慢）**：中段大量单人解谜 + 日志比对 + 意识流，场景切换少、他者互动稀，节奏拖沓。
- **exposition 2.1/5（偏弱）**：设定 / 协议靠内心独白、日志比对硬灌，信息未融进动作。

两者同源——**过度依赖单人内心独白与说明性铺陈**，因此合并为一个任务。

## 认知修正（查证得到）

**Writer 1.2.0 已有大量相关文字约束，但缺代码检测**：

- `paragraph_rhythm`（`1.2.0.yaml:277-293`）：段长分布、禁连续短段。
- `info_release`（`:331-341`）：禁连续 300 字以上纯说明。
- `show_dont_tell`（`:295-316`）：认知动词黑名单 + 结尾 200 字内心独白例外。
- 输出要求 10 节奏控制（`:234`）：禁平铺、相邻段落须节奏变化。
- 场景切换（`:222`）：两个连续空行分隔、2–4 场景、每场景 ≥600 字。

CreativeDirector 1.0.6 也有【节奏地图】（规则 16）、【行动承载】（规则 6，对应 exposition）。

**关键缺口**：这些都是 **prompt 文字约束**，`RuleAuditor` **没有对应的代码检测**——即"连续内心独白 / 说明段落"无法被自动量化、无法进审查反馈。约束写了但没人查，模型自然容易违反。

## Goal

1. 给 RuleAuditor 增加可代码化的节奏/说明检测项（连续内心独白比例、连续说明段落长度、场景切换密度），把 Writer 卡的文字约束变成**可检测信号**。
2. 强化 CreativeDirector/Writer 工艺卡对节奏与信息融合的约束（在诊断能捕捉后，约束才有反馈闭环）。
3. 用 170d 校准量具 + 新检测项验证 pacing/exposition 改善。

## In Scope

### 检测侧（RuleAuditor）
- [ ] 新增检测函数（放 `rule_auditor.py` 或 `utils/`），候选：
  - `detect_consecutive_exposition`：连续纯说明/独白段落的最大长度与占比（对齐 Writer `info_release` 的"连续 300 字纯说明"）。
  - `detect_monologue_ratio`：内心独白段落占全章比例（对齐 `show_dont_tell`）。
  - 场景切换密度：复用 `_split_scenes`（`rule_auditor.py:190`）计场景数/章长比。
- [ ] 在 `run_rule_audit`（`:302-432`）加为第 15+ 项，结果入 `RuleAuditResult` 新字段（参考 `_short_paragraph_ratio` 的**观测指标模式**，先不阻断）。
- [ ] `RuleAuditResult`（`models/review.py`）加对应 match/标量字段。
- [ ] 决定是否计入 `_compute_overall_score`（倾向先观测、后按 170g 数据决定权重）。

### 生成侧（工艺卡）
- [ ] 确认 Writer 线上实际加载版本（**manifest default=1.1.0 但最新卡 1.2.0**，改前必查）。
- [ ] 强化场景切换 / 控独白比例约束，使其与新检测项对齐（检测什么就约束什么）。
- [ ] CreativeDirector 章节目标层面控制"单场景独白比例"（可选，视诊断结果）。

## Out of Scope

- 不做全自动 LLM 改写闭环。
- 不把新检测项立即设为硬阻断（先观测，阻断与否由 170g 后决策）。
- pacing 的 LiteraryAuditor 语义维度不在此做（若需，与 170d 协调；本任务走 RuleAuditor 可代码化路径）。
- 不启动 Ch200。

## 风险提示

- **碰生成链 + RuleAuditor**：改检测和工艺卡有回归风险，跑 `test_rule_auditor.py`、`test_writer.py`、`test_creative_director*`。
- **检测误伤**：内心独白/说明是合法叙事手段，检测阈值需保守（先观测不阻断），避免逼模型写成流水账。
- **Writer 卡版本一致性**：与 170e 共享，需统一确认。

## 验证要求

```powershell
python -m pytest tests/test_rule_auditor.py tests/test_writer.py -q
python -m pytest tests/test_170f_pacing_exposition.py -q   # 新增
ruff check src/ tests/
python -m pytest tests/ -q
```

## 验收标准

- [ ] RuleAuditor 能量化"连续说明/独白/场景密度"，在 170b 正文上复算能反映 pacing/exposition 问题。
- [ ] 工艺卡约束与新检测项对齐。
- [ ] 新检测项默认观测、不误伤正常叙事（负样本测试）。
- [ ] 小样本重生成显示节奏/信息融合改善。
- [ ] 全量测试 + ruff 通过。
- [ ] 产出 `tasks/170f-...-DONE.md`。
