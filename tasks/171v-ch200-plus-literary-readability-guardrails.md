# Task 171v: Ch200+ 文学性与可读性护栏

> **框架**: `docs/reports/v7-literary-framework-review.md` §8 D2 + Task 171 20% 抽读结论
> **类型**: Ch200+ 质量护栏（observe-first，不恢复文学硬门）
> **优先级**: P1（Task 172 Ch250 前置，须在 171u hard clean 后执行）
> **依赖**: 171u；分析报告 `docs/reports/task-171-ch200-analysis-and-next-step-report.md`
> **状态**: ⚠️ 条件未通过（核心工程护栏已落地；Ch201-Ch220 小窗口实跑 partial，需 171v-hardening）

## 结论

Task 171 Ch200 完成后，20% 抽读复盘确认：文本没有随长度明显劣化，硬科幻质感、动作推进和章节钩子仍可维持到 Ch200；但若目标是继续推进到 Ch250/Ch300 并“保证文学性和可读性”，需要在进入 Task 172 前加轻量护栏。

主要短板：

1. **角色自主性偏低**：LiteraryAuditor 分段均值约 3.0，抽读也显示林渊经常被协议/倒计时/外部危机推动，主动设局不足。
2. **后段概念密度偏高**：Ch127 后协议层、基因锁、陷阱协议、频率深渊、观察者、审判序列等概念密集叠加。
3. **动作母题重复**：指尖悬停、左臂发烫、神经接口刺痛、倒计时、控制台数据流、共鸣频率等高频出现。
4. **配角目标偏功能化**：赵铭、小周、陈薇/陈曦等常承担解释/提醒/情绪推进功能，但较少拥有与林渊冲突的独立目标。

本 task 不把文学分重新变成硬门禁，而是把抽读发现转成 CreativeDirector/Writer 的输入护栏和 observe 检测，作为 Ch250 前置质量底盘。

## 当前实施进度（2026-07-12）

已落地：

- `CreativeBrief` 新增 `protagonist_active_choice`、`new_concept_budget`、`fatigue_motif_replacements`、`supporting_character_goal` 四类结构化护栏字段，并支持 LLM JSON 解析。
- `CreativeDirector` 在 LLM 未输出字段时会确定性补齐最低可执行护栏：主角主动选择、每章 1 个新核心概念预算、每 5 章配角目标节点、近期 accepted 正文母题疲劳替代表达。
- `Writer` 通过既有 `style_constraints` 接收 171v 护栏，并在 `creative_brief_snapshot` 中保存 171v 字段，便于 Ch201+ 回放验证。
- `RuleAuditor` 新增 `detect_fatigue_motifs` 与 `motif_fatigue_matches` / `motif_fatigue_count` observe 指标；不参与硬门、不扣分、不触发自动修订。
- 新增 `tests/test_171v_literary_guardrails.py`，覆盖字段解析、CreativeDirector 注入、Writer prompt/metadata 承载、RuleAuditor observe 扫描。

已验证：

```powershell
python -m pytest tests/test_171v_literary_guardrails.py tests/test_creative_director.py tests/test_writer.py tests/test_rule_auditor.py -q
# 173 passed

python -m pytest tests/test_171v_literary_guardrails.py tests/test_108_core_nodes.py tests/test_rule_auditor.py -q
# 100 passed

ruff check src/ tests/
# All checks passed
```

小窗口实跑（2026-07-12）：

```text
run_id: run-e27b763f
range: Ch201-Ch220
result: partial，19/20 accepted，failed=[207]，Halt=None
```

已确认：

- `CreativeDirector` 对 Ch201-Ch220 **20/20** 注入了 171v 护栏；Ch205/210/215/220 也均注入了“配角独立目标护栏”。
- accepted 19 章中，T9 hard issue 仍为 0：meta/artifact=0、duplicate=0。
- 母题疲劳 observe 有改善但未清零：多章仍有 `motif_fatigue_count=1/2`，后段出现若干 0。

未通过：

- 小窗口出口要求 `20/20 accepted`，实际 Ch207 因 Settlement 数值校验进入 `settlement_review`：`escape_pod_communication_array_integrity closing_value (0.0) != formula (63.000)`。
- 角色主动性未达到预期：accepted 19 章 `character_autonomy_score` 均值约 **2.816**，10/19 章低于 3.0。
- 配角目标节点未落到正文：Ch205/210/215/220 均注入了配角目标约束，但正文中对应配角命中为 0；Ch210 的约束配角为“指挥官”，也未在正文出现。
- 概念密度仍偏高：`setting_tracking` 显示多章新增设定数 >1（如 Ch217 为 9）。

结论：

- 171v 当前证明了“护栏能进入 planning/prompt 链路”，但没有证明“护栏稳定改变正文输出”。
- 不建议进入 Task 172；下一步应先做 `171v-hardening`：强化配角目标为可验证必达约束、修复 CreativeBrief 171v 字段持久化/Revision metadata 丢失、为概念预算与主动选择增加 observe 检测。

## 修复边界

### 做

1. 在 CreativeDirector / ChapterGoal 中注入“角色主动选择”结构。
2. 为每章增加概念预算与落地场景约束。
3. 增加 deterministic 母题疲劳扫描，向 Writer 注入替代表达建议。
4. 增加配角目标节点要求，让配角不只是提示器。
5. 用 Ch201-Ch220 小窗口验证，不直接改 Ch1-Ch200 既有文本。

### 不做

- 不恢复 voice/exposition 固定阈值硬阻塞；
- 不重启 170h-170l prompt 仓鼠轮；
- 不做全自动 LLM 整章文学重写闭环；
- 不以机器文学分单点升降作为唯一成功标准；
- 不放宽 T9/T10/T12/health/orphan 口径；
- 不清理 Ch200 D1 artifact（已由 171u 负责）。

## 工程方案

### 1. 角色主动选择护栏

每章规划中增加结构化字段：

```text
protagonist_active_choice:
  choice: 当前必须做出的主动选择
  alternatives: 至少一个可行备选方案
  cost: 选择代价
  irreversible_consequence: 不可逆后果
```

Writer 约束：

- 每章至少一次由林渊主动改变局面；
- 禁止只写“继续破解 / 继续推进 / 继续承受”；
- 主动选择必须有代价或误判风险；
- 如果该章是逃亡/防守章，也必须写出策略选择而不是纯反应。

验收观察：

- 抽读样本中每章能指出一个主动选择；
- 不要求机器 character autonomy 分硬达阈值，但要求人工抽读无“被协议牵着走”的连续三章。

### 2. 概念密度护栏

每章限制：

```text
new_concept_budget:
  max_new_core_concepts: 1
  grounding_scene: 用行动/失败/对话/物理结果落地
  forbidden_mode: 禁止连续解释协议机制
```

规则：

- 每章最多 1 个新核心概念；
- 新概念必须通过具体事件落地；
- 连续 3 章不得都以“协议解释/系统播报”作为主要推进方式；
- 旧概念可回收，但必须服务于行动目标。

### 3. 母题疲劳扫描

新增轻量检测函数，统计近 N 章高频母题：

- 指尖悬停 / 手指悬停
- 左臂发烫 / 金属化左臂
- 神经接口刺痛 / 颅骨内侧
- 倒计时
- 控制台数据流 / 全息屏刷新
- 共鸣频率跳动

当某一母题超阈值时，不阻塞章节，只向 Writer 注入替代表达建议：

```text
fatigue_motif_replacements:
  overused: "指尖悬停"
  alternatives:
    - 身体重心变化
    - 环境反应
    - 配角动作打断
    - 战术动作
```

### 4. 配角目标注入

每 5 章至少 1 个配角目标节点：

```text
supporting_character_goal:
  character: 角色名
  goal: 该角色自己的目标
  conflict_with_protagonist: 与林渊目标的偏差
  scene_consequence: 该角色行为如何改变局面
```

要求：

- 配角目标不能只是“帮助林渊”；
- 必须造成信息延迟、路线变化、代价增加、误判或情感压力之一；
- 尽量优先使用已入库角色，不硬编码新角色。

## 接线建议

### CreativeDirector

在 creative brief 生成时增加：

- `protagonist_active_choice`
- `new_concept_budget`
- `supporting_character_goal`
- `fatigue_motif_replacements`

### Writer

Prompt card 增加短约束：

- 主角主动选择；
- 概念落地；
- 母题替换；
- 配角目标冲突。

### RuleAuditor / metrics

只做 observe：

- 检测母题频次；
- 检测新概念密度；
- 记录是否缺少主动选择结构；
- 不自动阻塞 accept。

## 测试

建议新增：

1. CreativeDirector 输出结构测试：
   - brief 包含 active choice / concept budget / supporting goal。
2. Writer prompt 渲染测试：
   - 护栏字段被渲染进入 prompt；
   - 空字段时旧行为不破坏。
3. 母题疲劳扫描测试：
   - 高频“指尖悬停”等能被识别；
   - 低频不触发；
   - 触发只生成 observe 建议，不阻塞。
4. 小窗口实跑：
   - Ch201-Ch220 20/20 accepted；
   - T9 hard issue=0；
   - 抽读至少 3/3 章存在可指出的主动选择。

## 验证命令

```powershell
python -m pytest tests/test_171v_* tests/test_108_core_nodes.py tests/test_rule_auditor.py -q
ruff check src/ tests/
```

小窗口：

```powershell
$env:DATABASE_URL = "sqlite:///.tmp/task171_ch1_ch200.db"
$env:START_CHAPTER = "201"
$env:END_CHAPTER = "220"
python scripts/run_171_ch200.py --resume
python scripts/run_171_ch200.py --report
```

## 出口标准

| 项 | 标准 |
|---|---|
| 工程 | 测试 + ruff 通过 |
| 小窗口 | Ch201-Ch220 20/20 accepted |
| T9 | duplicate/meta/artifact=0 |
| 角色主动性 | 抽读样本每章能指出主动选择 |
| 概念密度 | 无连续 3 章纯协议解释推进 |
| 母题疲劳 | 高频母题有替代表达注入记录 |
| 配角目标 | 20 章内至少 4 个有效配角目标节点 |

## 与后续关系

171v 完成后进入 Task 172：Ch250 过渡验证。Task 172 不应只看 accepted 率，还要继续保留人工抽读，并重点复核：

- character autonomy 是否稳定；
- 概念密度是否可读；
- 后段是否出现母题疲劳；
- 配角是否有独立目标；
- 171u 的 D1 hard clean 是否在 Ch201-Ch250 持续成立。
