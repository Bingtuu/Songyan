# 术语表 v1（task 264）

给作者与贡献者的统一口径。纪律：**用户可见输出**（命令输出、帮助、错误）遵守本表右两列；**代码标识符/表名/列名**不变（--json 机器面保持英文原键）。

## 治理原则

1. 用户输出不出现内部隐喻（章宇宙/章头/empty head）、任务号（task NNN）、方案章节引用（tech-mX §N）——历史溯源走 git，不走 UI。
2. 状态枚举值（`approved`/`pending`/`rejected`/`settled`/`picked`…）保留英文原值（它们是数据语义，与 `--json` 一致）；叙述性文案用中文。
3. 缩写列名不得直出（`slStale`/`fp`/`ref`）；输出用中文标签或删除低价值字段。
4. 同一概念全库一个中文词；英文原词首次出现给中文注释。
5. 错误消息一句人话 + 下一步建议；内部细节（异常原文/堆栈）只进日志。

## 核心术语

| 概念 | 用户面统一说法 | 代码/表 | 说明 |
|---|---|---|---|
| Canon | 已确认事实（入典） | `canon` / `plan_*` approved 行 | 「入典」= 人确认动作；「已确认事实」= 结果。不用「圣经」对用户 |
| 圣经 bible | （仅 prompt 内部） | `bible.text` | 写手 prompt 概念，不露出 |
| 计划卡/计划行/提案 | 提案 | `plan_*` pending 行 | CLI 统一「提案」；README 旧文「计划卡」改「提案」 |
| 章宇宙 | 章节工作记录 | chapter universe（B1 口径） | 用户面说「该章还没有章节工作记录」 |
| 抽卡 | 抽卡 | variant | 命令名保留 `variant`；叙述用「抽卡」 |
| 槽 slot | 槽 N | `slot_index` | 不用「槽号（slot_index）」混排 |
| 指纹 | 指纹 | fingerprint | 不用 `fp=`；低价值场景直接删 |
| 标脏/过期 | 已过期（需重看） | `content_stale` / `stale_vs_canon` | 标脏族三词（标脏/过期/content_stale）统一为「过期」叙述；列名值保留 |
| 故事线过期 | 相对故事线已演进 | `stale_vs_storyline` | 不用 `slStale=` |
| 已确认（章） | 已确认 | `accepted`（章） | promise 销账用「已销账」，不与章混 |
| 已定稿态 | settled（已定稿） | `settled` | 章进度六态英文值保留；叙述「已定稿」 |
| 待确认 | 待确认（pending） | `pending` | 首现可中英并注 |
| 承诺/伏笔 | 承诺 | foreshadowing | 「伏笔」仅限 import 面的叙述传统，新文案统一「承诺」 |
| 结算 | 结算 | settlement | 不展开解释，少用 |
| 信号 | 信号 S1–S7 | signals | 保留编号；文本输出用中文标签分行，不裸 JSON |
| 质量门拒写原因 | 判失败（太短/占位/拒写关键词） | `quality_flag` | 枚举值对用户翻译为中文短语 |
| 章头/head 指针 | 工作稿指针 | `chapter_heads` | 用户面说「当前工作稿」 |

## 有意保留项（不治理，记录原因）

- 命令名与旗标全英文（`--project-id`、`--yes`）：CLI 惯例，--json 键同源。
- `review` 报告的 `source=deep` 等机器标签：报告同时是机器面。
- doctor/preflight 的英文骨架（`[PASS]`/`Summary:`）：工程面命令，对外一致性收益低。
