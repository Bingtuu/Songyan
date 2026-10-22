# ADR-0001: Plan-first 事实层

- **状态**: 已接受（方向）。尚未实现。Day-1 不改生成代码。
- **日期**: 2026-10-22
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

- Phase A 只修 B5 / B7 / B18，不实现本 ADR 的表结构。运行不可信时，对照实验的召回、人工时间和成本都测不准。
- Phase B 才落地最小事件卡 / 事实卡，并用霞飞路 ch1–3 测召回 ≥4/5、人工 ≤10 分钟/章、成本与 v1 同量级。
- `SettlementExtractor` 的抽取结果不再作为权威写入。它可以留下作比对证据或待审项。在代码改到这一步之前，现有结算路径保持原样，避免半套权威源。
- 不新增题材专用检查规则来追霞飞路类错误。第二体裁（Phase C）复用同一套卡和窄验证；失败则退到人维护事实圣经、AI 按圣经写。
- 研究 / report-only 信号仍然不进 runtime prompt、CED、T9 或 hard gate。本 ADR 不改那些门的口径。
- 待审队列和「计划才能写 canon」落地时，要有测试证明：未批准的抽取行不会被下一章上下文当成已成立事实。
