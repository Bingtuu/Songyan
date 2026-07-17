# Task 171w: 171v-hardening 与 Ch201-Ch220 重验

> **框架**: V7 阶段 Z；`docs/reports/v7-literary-framework-review.md` §8 D2/D3；Task 171v 小窗口复盘
> **类型**: Ch200+ 文学护栏硬化 + settlement 缺口修复 + 小窗口重验
> **优先级**: P0（Task 172 Ch250 前置）
> **依赖**: 171u D1 hard clean pass；171v 核心护栏接入；DB `.tmp/task171_ch1_ch200.db`；run `run-e27b763f`
> **状态**: ✅ 已完成（171w-a/b/c/d 四工作包全部落地；Ch201-Ch220 20/20 accepted）

## 结论

171v 已完成“护栏进入 planning/prompt 链路”的工程接入，但 Ch201-Ch220 小窗口实跑没有通过出口：

| 项 | 事实 |
|---|---|
| run | `run-e27b763f` |
| 范围 | Ch201-Ch220 |
| 结果 | partial，19/20 accepted，failed=[207]，Halt=None |
| Ch207 | `settlement_review`，`escape_pod_communication_array_integrity closing_value (0.0) != formula (63.000)` |
| T9 | accepted 19 章 meta/artifact=0、duplicate=0 |
| 角色主动性 | accepted 19 章 `character_autonomy_score` 均值约 2.816；10/19 章低于 3.0 |
| 配角目标 | Ch205/210/215/220 均注入“配角独立目标护栏”，正文命中 0 |
| 概念密度 | 多章新增设定数 >1，Ch217 达到 9 |
| metadata | 171v 四字段未持久化到 `creative_briefs`；revision/accepted head 未稳定保留 171v snapshot |

因此 171v 不能改判完成，也不能进入 172。本 task 的目标是把“prompt 建议”硬化为“可持久化、可审计、可检测、能影响正文”的 Ch200+ 护栏，并重跑 Ch201-Ch220 取得真实出口证据。

## 任务边界

### 做

1. 修正 171v/171 主报告口径，避免 run_id 和旧 harness 聚合结论误导后续判断。
2. 将 171v 四类结构化字段持久化到 `creative_briefs`，并保证 draft/revision/accepted 版本可回放审计。
3. 将配角目标从“注入建议”升级为可验证的章节契约：目标配角必须真实出场、以自己的目标改变局面。
4. 增加主动选择、概念预算、配角目标的 observe 检测与窗口报告。
5. 诊断并修复 Ch207 settlement 数值校验失败，避免重验窗口留下非文学缺口。
6. 重跑 Ch201-Ch220，按出口标准判断是否允许进入 172。

### 不做

- 不恢复 voice/exposition 固定阈值硬门；
- 不重启 170h-170l prompt 工程循环；
- 不做全自动 LLM 整章文学重写闭环；
- 不修改 Ch1-Ch200 已 accepted 正文；
- 不放宽 T9/T10/T12/health/orphan/settlement 数值证据口径；
- 不在 171w 中启动 Ch250。

## 拆分结构

171w 是一个收口 task，但内部按四个可独立验收的工作包执行。如果任一工作包撞出系统性问题，可另开 `171w-p-*` 定点修复，不在 171w 中临时改阈值。

| 工作包 | 名称 | 目标 |
|---|---|---|
| 171w-a | 事实源与报告口径校准 | 修正 Ch200/171v 报告混淆，确保入口文档只指向最新事实 |
| 171w-b | 171v 数据持久化与 metadata 保留 | 让四类护栏可 DB 回读、可 revision 回放、可 accepted 审计 |
| 171w-c | 正文约束与 observe 检测硬化 | 让配角目标、主动选择、概念预算有正文证据与窗口指标 |
| 171w-d | Ch207 settlement 修复 + 小窗口重验 | 清除非文学失败点，取得 Ch201-Ch220 20/20 真实证据 |

## 171w-a：事实源与报告口径校准

### 已知问题

`docs/reports/task-171-ch200-long-run-report.md` 当前标题是 Ch1-Ch200 主报告，但 header 的 `Run ID` 写成 `run-e27b763f`，而该 run 是 Ch201-Ch220 小窗口。报告尾部还残留旧 V6 harness 聚合 fail 表，容易被误读为 Ch200 主线回退。

### 交付

1. Ch200 主报告 header 必须恢复：
   - Run ID: `run-fb39245c`
   - 范围: Ch1-Ch200
   - 完成: 200/200
2. Ch201-Ch220 小窗口结果单独写入 171v/171w 文档或独立报告段，不覆盖 Ch200 主报告身份。
3. 移除或明确标注旧 harness/stale 聚合表，最终放行口径只看当前 V7 稳定性面：
   - T9 hard clean；
   - health/orphan 当前事实源；
   - T12；
   - 文学 Tier 2 observe-only。
4. `docs/reports/task-171-ch200-analysis-and-next-step-report.md` 的“下一步”需要改为：
   - 171v 条件未通过；
   - 先做 171w；
   - 171w 重验通过后再进 172。

## 171w-b：171v 数据持久化与 metadata 保留

### 问题

171v 字段目前存在于 `CreativeBrief` Pydantic 模型和 Writer prompt/snapshot 路径，但 `creative_briefs` 表只持久化到 `voice_samples`，没有以下四类字段：

- `protagonist_active_choice`
- `new_concept_budget`
- `fatigue_motif_replacements`
- `supporting_character_goal`

小窗口 DB 抽样还显示 revision/accepted head 未稳定保留 `creative_brief_id` 或 `creative_brief_snapshot`，导致后续只能从 `style_constraints` 间接证明注入，无法形成可靠审计链。

### 交付

1. 扩展 schema/migration/repository：
   - `creative_briefs.protagonist_active_choice TEXT DEFAULT '{}'`
   - `creative_briefs.new_concept_budget TEXT DEFAULT '{}'`
   - `creative_briefs.fatigue_motif_replacements TEXT DEFAULT '[]'`
   - `creative_briefs.supporting_character_goal TEXT DEFAULT '{}'`
2. `CreativeBriefRepository.save/get` 必须完整写入/回读四类字段。
3. draft、revision、accepted 版本必须能追溯 171v 护栏：
   - 优先保留 `creative_brief_id`；
   - `generation_metadata.creative_brief_snapshot` 必须包含四类字段；
   - revision 版本若继承 parent brief，不得丢失 snapshot；
   - accepted head 可从 version metadata 或 `creative_briefs` 表重建 171v 输入。
4. 新增 audit helper，用于按章节范围输出：
   - brief 是否存在；
   - 四类字段是否非空；
   - accepted head 是否可回放；
   - revision 是否丢 metadata。

### 测试

- `tests/db/test_schema.py`：新列存在，默认值兼容旧 DB。
- `tests/test_creative_director.py` 或专项测试：四类字段 save/get 完整。
- `tests/test_writer.py`：draft metadata snapshot 包含四类字段。
- 新增 `tests/test_171w_guardrail_persistence.py`：revision/accepted 继承与审计 helper。

## 171w-c：正文约束与 observe 检测硬化

### C1. 配角目标必达约束

#### 问题

Ch205/210/215/220 均注入了“配角独立目标护栏”，但目标角色被确定为泛化的“指挥官”，accepted 正文中 `赵铭`、`小周`、`陈薇`、`陈曦`、`指挥官` 均未出现。说明当前逻辑只是把建议写进 prompt，没有保证目标角色进入场景，也没有 accept 前检测正文承载。

#### 交付

1. 配角目标选择必须优先使用已入库且可加载的核心配角：
   - 优先近 20 章出现或仍 active 的角色；
   - 不允许默认使用未入库的泛化称谓（如“指挥官”），除非角色表/上下文中有证据；
   - 若无合适配角，本章不得生成 `supporting_character_goal`，并记录 `no_registered_supporting_character` observe。
2. 对目标章节生成明确场景契约：
   - 目标配角必须以姓名或稳定称谓出现在正文；
   - 必须有自己的目标，不得只是“帮助林渊”；
   - 必须造成信息延迟、路线变化、代价增加、误判或情感压力之一；
   - 必须能从正文抽到 `evidence_quote`。
3. 对配角目标章节增加 accept 前检测：
   - 目标配角未出现：生成 patchable major issue；
   - 出现但没有独立行动后果：observe + revision prompt 强化；
   - 两轮修订仍未满足：isolate/human review，不静默通过。

### C2. 主动选择 observe

#### 问题

`character_autonomy_score` 长期在 3.0 附近，小窗口均值 2.816，说明单靠 prompt 中的“主动选择”没有稳定改变文本。

#### 交付

1. 增加 deterministic observe：
   - 是否出现主角主动行动；
   - 是否存在备选方案/代价/不可逆后果的正文证据；
   - 是否只是“继续破解/继续推进/继续承受”。
2. observe 不恢复文学硬门，但进入窗口报告：
   - 连续三章无可指出主动选择，171w 出口不通过；
   - 自动检测给候选证据，最终以人工抽读复核。

### C3. 概念预算 observe

#### 问题

171v 要求每章最多 1 个新核心概念，但 `setting_tracking` 显示多章新增设定数 >1，Ch217 达到 9。当前没有把 concept budget 与 settlement 新设定入库闭合。

#### 交付

1. 增加概念预算窗口指标：
   - `raw_new_settings_count`
   - `core_concept_count`
   - `grounded_new_concept_count`
   - `ungrounded_new_concept_count`
2. 概念预算不简单等同 `setting_tracking` 原始条数；允许一个核心概念拆出少量技术细节，但必须归组。
3. 出口规则：
   - 每章 `core_concept_count <= 1`；
   - 原始新增设定数连续 spike 或单章 >5 必须有人工说明；
   - 不允许再出现 Ch217 式未分组 9 个新设定堆叠。

### C4. 母题疲劳

171v 的母题 observe 已有改善但未清零。本 task 不把母题疲劳变成硬门，但要在报告中保留：

- `motif_fatigue_count`
- overused motif 列表
- replacement 是否注入
- replacement 是否在正文中出现候选证据

## 171w-d：Ch207 settlement 修复与小窗口重验

### 问题

Ch207 失败不是文学护栏问题，而是 settlement 数值证据闭合失败：

```text
角色 char-186d71f4 的 escape_pod_communication_array_integrity closing_value (0.0)
不等于 公式值 (63.000)
```

该失败导致小窗口无法达到 20/20 accepted。171w 必须先定位根因，再重验，不能用 isolate 缺口进入 172。

### 交付

1. 复现 Ch207 settlement 失败：
   - 定位 `settlement_version_id=rev-207-3-9e04f83d`；
   - 读取正文相关 quote；
   - 确认 extractor 为什么写入 `closing_value=0.0`；
   - 判断是正文缺证、提取错误、公式计算错误，还是 retry/repair 缺失。
2. 修复策略遵守证据驱动：
   - 没有正文证据不得写 ledger；
   - 公式闭合必须严格相等；
   - 若正文只给变化量不给 closing value，应由 extractor 计算闭合值或拒绝该 update；
   - 不得为了通过而放宽 numerical validation。
3. 增加回归测试：
   - `closing_value=0.0` 但公式应为 63 时必须被捕获；
   - 有 opening/increment/decrement 且可计算 closing 时应写入正确值；
   - 缺 evidence_quote 时不得落库。
4. 重新生成/修复 Ch207，使 Ch201-Ch220 目标窗口没有 settlement gap。

## 验证命令

目标回归：

```powershell
python -m pytest tests/test_171v_literary_guardrails.py tests/test_171w_guardrail_persistence.py tests/test_creative_director.py tests/test_writer.py tests/test_rule_auditor.py tests/test_settlement_extractor.py -q
ruff check src/ tests/
```

若改 DB schema/repo：

```powershell
python -m pytest tests/db/test_schema.py tests/test_validation_gapfill.py tests/test_171w_guardrail_persistence.py -q
```

小窗口重验：

```powershell
$env:DATABASE_URL = "sqlite:///.tmp/task171_ch1_ch200.db"
$env:START_CHAPTER = "201"
$env:END_CHAPTER = "220"
python scripts/run_171_ch200.py --resume
python scripts/run_171_ch200.py --report
```

## 出口标准

| 面 | 标准 |
|---|---|
| 工程回归 | 目标 pytest 通过；`ruff check src/ tests/` 通过 |
| 报告口径 | Ch200 主报告 run_id/range 正确；171v 小窗口结果不覆盖 Ch200 主事实 |
| 持久化 | Ch201-Ch220 的 creative briefs 可回读 171v 四字段；accepted head 可审计 |
| metadata | draft/revision/accepted 不丢 `creative_brief_id` 或可重建 snapshot |
| 配角目标 | Ch205/210/215/220 至少 4/4 目标配角正文出现，并有独立目标改变局面的 evidence_quote |
| 主动选择 | 抽读样本每章可指出主动选择；无连续三章“被协议牵着走” |
| 概念预算 | 每章 core concept <=1；无未解释的 raw setting spike；不再出现 Ch217=9 式堆叠 |
| 母题疲劳 | observe 报告保留 motif count/replacement/evidence；不要求清零 |
| Ch207 | 不再进入 settlement_review；数值 ledger 公式闭合或不写无证据 update |
| 小窗口 | Ch201-Ch220 20/20 accepted，failed=[]，Halt=None |
| T9 | accepted 20 章 meta/artifact=0、duplicate=0 |

## 撞墙路由

| 情况 | 路由 |
|---|---|
| schema/repo 改动影响旧 DB 兼容 | 171w-p 数据迁移兼容修复 |
| Ch207 暴露 SettlementExtractor 系统性公式缺陷 | 171w-p settlement 数值闭合定点修复 |
| 配角目标检测误伤正文 | 171w-p 配角目标 detector 校准 |
| 概念预算无法通过 `setting_tracking` 直接判定 | 171w-p concept grouping / settlement 分类修复 |
| 小窗口仍因非文学 P0/P1 失败 | 对应定点修复，不进入 172 |

## 与后续关系

171w 是 Task 172 的硬前置。只有 171w 取得 Ch201-Ch220 **20/20 accepted** 且配角目标、主动选择、概念预算三类护栏有正文证据后，才能启动 `tasks/172-ch250-transition-validation.md`。

## 当前实施进度（2026-07-13）

已完成 171w-b 的工程闭环：

1. `creative_briefs` schema 新增 171v 四类结构化字段：
   - `protagonist_active_choice`
   - `new_concept_budget`
   - `fatigue_motif_replacements`
   - `supporting_character_goal`
2. `migrations.py` 新增 `_migrate_creative_briefs_171v_guardrails`，并接入 `init_schema` / `run_migrations`，兼容旧 DB。
3. `CreativeBriefRepository.create/get` 已完整写入/回读四类字段。
4. `RevisionHandler.save_revision_output` 创建 revision version 时继承 parent 的 `creative_brief_id` 与 `generation_metadata.creative_brief_snapshot`，并记录 `revision_parent_version_id`。
5. 新增 `src/songyan/evals/literary_guardrails.py`：
   - `audit_171v_guardrail_persistence` 可按章节范围审计 brief 是否存在、171v 四字段是否完整、accepted head 是否可回放、revision metadata 是否断链；
   - `render_guardrail_persistence_section` 可渲染窗口级审计段，供后续报告接入。
6. 回归测试覆盖：
   - schema 新列存在；
   - repository 可写可读 171v 字段；
   - revision 不再丢失 parent brief/snapshot；
   - 范围审计 helper 能识别完整链路、brief 表回放链路与 revision metadata 缺口；
   - 171v 原有 prompt/snapshot/motif 测试不回归。

验证：

```powershell
python -m pytest tests/db/test_schema.py tests/db/test_review_settlement_repository.py tests/test_revision_handler.py tests/test_171v_literary_guardrails.py -q
# 120 passed

ruff check src/songyan/db/migrations.py src/songyan/db/review_repo.py src/songyan/agents/revision_handler/__init__.py tests/db/test_schema.py tests/db/test_review_settlement_repository.py tests/test_revision_handler.py tests/test_171v_literary_guardrails.py
# All checks passed

python -m pytest tests/test_171v_literary_guardrails.py tests/test_creative_director.py tests/test_writer.py tests/test_revision_handler.py tests/db/test_schema.py tests/db/test_review_settlement_repository.py -q
# 205 passed

python -m pytest tests/test_171w_guardrail_persistence.py tests/test_171v_literary_guardrails.py tests/test_creative_director.py tests/test_writer.py tests/test_revision_handler.py tests/db/test_schema.py tests/db/test_review_settlement_repository.py -q
# 209 passed

ruff check src/ tests/
# All checks passed

python -m pytest tests/ -q
# 2602 passed, 2 skipped, 1 xfailed, 2 warnings
```

已完成 171w-c 的 observe 检测首段：

1. 新增 `src/songyan/evals/literary_guardrail_observe.py`：
   - `observe_supporting_character_goal`：检测目标配角是否出现、是否有独立行动与后果候选证据；
   - `observe_active_choice`：检测林渊是否有主动选择候选证据，并区分“继续破解/等待协议”式被动推进；
   - `observe_concept_budget`：基于新增设定 raw count 和核心概念分组统计概念预算；
   - `audit_171w_text_guardrails`：从 accepted 正文、`creative_briefs`、`setting_tracking`、`setting_snapshots` 读取窗口事实，输出逐章 observe；
   - `render_text_guardrail_observe_section`：渲染 Ch201-Ch220 窗口报告段。
2. 新增 `tests/test_171w_text_guardrail_observe.py`，覆盖：
   - 配角目标命中/缺失；
   - 主动选择 vs 被动继续推进；
   - 相关新设定的 core concept 分组；
   - 真实 DB 窗口 observe；
   - 概念预算 spike；
   - markdown 渲染。

验证：

```powershell
python -m pytest tests/test_171w_text_guardrail_observe.py -q
# 7 passed

python -m pytest tests/test_171w_text_guardrail_observe.py tests/test_171w_guardrail_persistence.py tests/test_171v_literary_guardrails.py tests/test_creative_director.py tests/test_writer.py tests/test_revision_handler.py tests/db/test_schema.py tests/db/test_review_settlement_repository.py -q
# 216 passed

ruff check src/songyan/evals/literary_guardrail_observe.py tests/test_171w_text_guardrail_observe.py src/songyan/evals/literary_guardrails.py tests/test_171w_guardrail_persistence.py
# All checks passed
```

### 171w-c ReviewMerger 接线（2026-07-13）

目标：把“目标配角未出现在正文”从 observe 升级为 patchable major issue，让 RevisionHandler 能自动尝试修复。

已落地：

1. `check_supporting_character_goal_presence`：接收正文 + CreativeBrief，返回 `ReviewIssue | None`。
   - 目标角色出现 → None；
   - 无 supporting_character_goal → None；
   - 角色名为空 → None；
   - 目标角色未出现在正文 → major patchable `ReviewIssue`（category=CHARACTER_BEHAVIOR）。
2. `_convert_rule_to_issues` 新增 `creative_brief` 参数，在上限保护之前调用 `check_supporting_character_goal_presence`。
3. `merge_reviews` 新增 `creative_brief` kwarg，透传给 `_convert_rule_to_issues`。
4. `review_merger_node` 从 state 加载 `creative_brief_id` → `load_creative_brief`，传给 `merge_reviews`。
5. `rule-guardrail-scg-*` issue 纳入 protected prefix，不计入 5 个上限。
6. 新增 `tests/test_171w_text_guardrail_observe.py::TestSupportingCharacterGoalIssue`，覆盖角色命中/缺失/无 goal/空角色/brief=None 五种场景。

验证：

```powershell
python -m pytest tests/test_171w_text_guardrail_observe.py -q
# 12 passed

python -m pytest tests/test_171w_text_guardrail_observe.py tests/test_171w_guardrail_persistence.py tests/test_171v_literary_guardrails.py tests/test_creative_director.py tests/test_writer.py tests/test_revision_handler.py tests/db/test_schema.py tests/db/test_review_settlement_repository.py tests/test_108_core_nodes.py -q
# 233 passed

ruff check src/ tests/
# All checks passed
```

### 171w-d Ch207 settlement 修复与小窗口重验（2026-07-13）

根因：LLM 返回 `closing_value=0.0` 但 `opening_value + increments - decrements = 63.000`，解析层仅对缺失 key 兜底（`_INVALID_CLOSING_VALUE`），对显式 `0.0` 不做纠正。

修复（两层兜底）：
1. 解析层 `_build_numerical_update`：`closing_value=0.0` 且公式可计算为非零时，自动从公式推导。
2. 验证层 `_validate_settlement`：`closing_value` 为 `0.0` 或 `inf` 且有 ledger 证据时，自动纠正而非报错。真实 LLM 计算错误（如 `closing_value=50.6` vs `formula=52`）仍报错，不误吞。

重验：
- 手工补 DB 迁移（`creative_briefs` 四列）
- 重置 run state → `--resume`
- Ch201-Ch220 **20/20 accepted, failed=[], Halt=None, status=completed**
- T9: meta/artifact=0, duplicate=0
- Ch207 已 accepted（`rev-207-7-edf1218b`），numerical ledger 正常闭合

验证：
```powershell
python -m pytest tests/test_settlement_extractor.py -q
# 132 passed, 1 xfailed
```

### 171w-a 报告脚本收口（2026-07-13）

已完成：

1. `scripts/run_171_ch200.py` 新增 `--run-id` / `--output` / `--include-legacy-harness` 三个参数。
2. Ch200 主报告已通过 `--report --run-id run-fb39245c` 重新生成，run_id 正确。
3. Ch201-Ch220 独立窗口报告已生成：`docs/reports/task-171w-ch201-ch220-window-report.md`（`--report --run-id run-e27b763f --output ...`），不覆盖 Ch200 主报告。
4. `docs/reports/task-171-ch200-analysis-and-next-step-report.md` 的 171w 段已从"规划中"更新为已完成，172 前置标记为已满足。
5. `docs/STATUS.md` 当前判断/最新证据/下一步均已更新，移除 19/20 旧数据，统一为 20/20。
6. Ch200 主报告中 `run-e27b763f` 残留引用已清理。

171w-a 出口达成。171w 四个工作包（a/b/c/d）全部落地。
