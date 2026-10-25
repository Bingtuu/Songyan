# ADR-0001: Plan-first 事实层

- **状态**: 已接受（方向）。2026-10-25：最小表和读写已落地；SettlementExtractor 权威尚未翻转。
- **日期**: 2026-10-22（决定）；2026-10-25（实现注记）
- **决定者**: Bingtuu（owner）；执行切片见 [HANDOFF-mew.md](../HANDOFF-mew.md)
- **相关**: [ROADMAP-plan-first.md](../ROADMAP-plan-first.md)

工程手册 [04-vibe-coding-engineering.md](../architecture/04-vibe-coding-engineering.md) 把 ADR 放在 `docs/decisions/ADR-NNN-*.md`，并列出 ADR-001–009。那些文件没有进当前仓库。本系列从 `docs/adr/0001` 起，避免和手册里的编号撞车。

## Decision

权威事实由**计划层**写入。正文对照计划做窄检查。

计划层是故事圣经、卷 / 案件大纲、以及章节事件卡。事实以类型化记录存在，每条有稳定 ID。至少包括：

- `entity(id, type, aliases)`
- `attribute(entity_id, key, value, valid_from_ch, valid_to_ch, source=plan|human)`
- `event(id, ch, time_anchor, participants, causes, reveals_evidence[])`
- `time_anchor(date, kind=story|history)`
- 悬疑再加 `clue(id, planted_ch, revealed_ch, must_mention_in[])`

生成一章时，只注入本章事件卡和被引用实体的当前属性。关键证物使用登记名。

验证只做窄任务：必须提及清单、主张对段落的支持 / 矛盾 / 未提及（附引文）、以及时间锚 / 数值 / 枚举属性的代码比较。正文里新出现的事实进入待审队列，**人批准后才入 canon**。

SQLite 仍是唯一长期事实库。变的是谁有权写入权威行：计划层和人，而不是结算抽取器。

## Reason

现行主路径是：规划故事 → 写正文 → 审查修订 → 接收 → 抽取事实 → 写入 SQLite（见 README 流水线）。抽取结果会变成下一章的 canon。

2026-10 的记录说明这条方向在新故事上召回不够：

- 霞飞路《旧案》ch1–3：人工跨章真错误 5 条，检查器召回 **0/5**。错误集中在证物属性（方向、位置、归属）、证据遗漏、历史时间锚。规则年代上调通的人名 / 性别 / 开头 / 数值类错误没有在这个新故事里复发。
- 《规则年代》审稿：长程一致性问题（人名、数值、章首、代价）没有被 CED、T9、五门或 LLM 审查抓住。父亲不是登记实体，settlement 把漂移后的名字写进了 setting。
- 调研报告（2026-10-13）把根因归为事实来源方向：抽取会抽象化证据、为同一物体建多条记录、并把漂移吸进 canon。文献侧（NoCha、FlawedFictions、FABLES、Lost in the Middle）支持的是「给定主张 + 证据的局部判断」和「按明确约束写作」，不支持开放式全书找错。

因此权威行的写入方向倒过来：**计划写 canon，正文接受检查**。机制和史实锚在计划阶段由人确认；模型负责按卡写作，以及逐条核验。

## Consequence

- Phase A（B5 / B7 / B18）已合入 main。运行信号先修完，对照实验才量得准。
- 最小事件卡 / 事实卡的表和读写已落地（见下方实现注记）。霞飞路 ch1–3 的召回 ≥4/5、人工 ≤10 分钟/章、成本与 v1 同量级，仍是下一刀的门。本切片没有开跑。
- `SettlementExtractor` 的抽取结果仍然走原结算路径。权威翻转是单独切片。在那之前不把抽取行自动写进 plan canon，避免半套权威源。抽取结果以后可以留下作比对或待审项；本切片没有这条通道。
- 不新增题材专用检查规则来追霞飞路类错误。第二体裁（Phase C）复用同一套卡和窄验证；失败则退到人维护事实圣经、AI 按圣经写。
- 研究 / report-only 信号仍然不进 runtime prompt、CED、T9 或 hard gate。本 ADR 不改那些门的口径。
- 待审队列和「计划才能写 canon」落地时，要有测试证明：未批准的抽取行不会被下一章上下文当成已成立事实。2026-10-25 的切片先钉住存储侧：`pending` 行不会被 canon 读返回。抽取行还不会自动进入这些表，下一章上下文也还没改去读它们。

## 实现注记（2026-10-25）

Phase A 已合入（B7 #5、B5 #6、B18 #8）。本切片只加表和读写：

| 记录 | 表 | 稳定 ID 与字段 |
|------|----|----------------|
| entity | `plan_entities` | `entity_id`，`entity_type`，`aliases` |
| attribute | `plan_attributes` | `attribute_id`，`entity_id`，`key`，`value`，`valid_from_ch`，`valid_to_ch`，`source=plan\|human` |
| event | `plan_events` | `event_id`，`ch`，`time_anchor_id`，`participants`，`causes`，`reveals_evidence` |
| time_anchor | `plan_time_anchors` | `anchor_id`，`date`，`kind=story\|history` |
| clue | `plan_clues` | `clue_id`，`planted_ch`，`revealed_ch`，`must_mention_in` |

五张表都有 `approval_status`：`approved` 或 `pending`。canon 读（`list_canon_*`）只返回 `approved`。attribute 的 canon 读还要求 `source` 是 `plan` 或 `human`。pending 行留在同一张表里，默认不会被当成已成立事实。

代码：`src/songyan/models/plan_facts.py`，`src/songyan/db/plan_fact_repo.py`，迁移 `_migrate_plan_fact_cards`。

这一刀明确不做：改写规划 / 写作 / 审查图节点；让 SettlementExtractor 停止写结算库；把抽取事实自动吸进这些表；写霞飞路或《规则年代》；实现必须提及、主张核验、类型化属性比较。
