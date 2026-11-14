# Context 断链评估：W2 短环「裸奔」与 storyline/角色/设定不可见

- 日期：2026-11-14
- 状态：pre-立项评估（任务号待定，按队列下一个 265 占位）
- 证据来源：都市恐怖 dogfood《末班电梯》（`.tmp/dogfood-G-urban-horror-末班电梯-230946/`，项目 5c00939e804b49429d86dd2cb56da328，3 次 LLM 调用 ¥0.0417）+ 代码层逐链路核实

## 1. Dogfood 复现事实

1. `create-project --template urban --title 末班电梯` 后直接 `chapter continue --chapter 1`：生成 2946 字职场文（陈屿=项目经理，模型自造林述/赵广平），恐怖设定零体现。
2. 同库 SQL 核对：writer 的 prompt（6882 字符 = prompt_tokens 4118）只含工艺卡 + urban 题材规则 + 2 个人名（陈屿/周牧野，无背景）+ 4 条通用 taboo。**storyline、角色背景、设定全部被丢弃或从未进入**。
3. `canon edit` 写入 6 条事实 + `canon confirm batch` 入典后，`variant generate` 两槽全部精准命中恐怖设定 → **事实圣经（plan_facts bible）是当前唯一确定生效的剧情定向通道**。
4. 抽卡两槽字数 985/1478，远低于 3000 目标；校准窗口文案在 prompt 里但无门拦截，accept 照过。

## 2. 数据流全景（代码核实）

### W1 引擎管线（`songyan run`）

```
story_outlines / arc_plans / plot_threads ─┐
project.protagonist_background/core_hook ──┤→ goal_planner(LLM) → chapter_goals
characters(含background) / settings / ... ─┤→ creative_director(LLM) → creative_briefs
arc_plans ─────────────────────────────────┤→ arc_summary_generator(LLM) → arc_context
chapter_goals + briefs + arc_context + bible + states → writer
```

- goal_planner 消费：project 字段（protagonist_background、core_hook、tone…）+ arc_goal + open_threads + 伏笔（`goal_planner.py:225` 起，NarrativeGoalContext）。
- creative_director 消费：characters 含 background（`creative_director/__init__.py:195,767`）、settings。
- **story_outlines 的 core_conflict / mainline_synopsis / themes / intended_ending 在生成期消费方为零**（全仓 grep 证实：只被 storyline CLI、workbench 展示、fingerprint 读取）。

### W2 短环（`chapter continue`）

- 只读 chapter_goals / creative_briefs 是否已存在；**不存在时不生成、不告警**，goal 兜底为「裸 ChapterGoal(字数)」、brief=None（`chapter_continue.py:341-352`）。这是 tech-m4 B12 接受的回退语义。
- writer 输入 = 工艺卡 + genre/mode 规则 + character_states（ch1 无 settled 状态，roster 兜底只带人名/重要性）+ 4 条 taboo + bible（若有）。
- `setting_snapshots` 被组装进 `soft_references(type=world_setting)`（`_assemblers.py:521`）但 **writer.py 没有任何分支渲染 world_setting**（全仓 grep 证实零消费）。死数据。
- `CharacterStateSnapshot` 模型无 background 字段（`models/context.py:31`）。

## 3. 断链清单

| # | 断链 | 后果 | 严重度 |
|---|------|------|--------|
| C1 | W2 无 goal/brief 时裸奔（B12 语义） | 全新项目首章定向全靠运气；体裁默认发挥 | **高** |
| C2 | story_outlines 生成期零消费 | 人改大纲/梗概/主题对续写零影响，「工作台先行」路径空心化 | **高** |
| C3 | characters.background 不进任何 writer 输入 | W2 下角色只有人名；设定集角色形同虚设 | 高 |
| C4 | setting_snapshots 组装后被丢弃 | 世界观设定不进正文定向 | 高 |
| C5 | project.core_hook/protagonist_background 只在建项时写入，无编辑 CLI | storyline 改写后这两个字段陈旧，继续污染 goal_planner（W1 也受影响） | 中 |
| C6 | （正面）plan_facts bible 链路完整 | 人写事实入典 → writer 定向，已验证 | — |

注：C3/C4 在 W1 中间接成立（creative_director 的 brief 带背景），但 W2 全断；C2 在 W1/W2 都断。

## 4. 红线核对

- **B12（tech-m4）**：「chapter_goal 无行 → words_per_chapter 兜底」是 owner 已接受语义。本评估不建议改 B12 的「不生成」决定；建议的修复走 context 注入，不动 goal 语义。
- PRD 人主导定位：「人编辑事实与故事线，系统提供一致性支持」——C2/C3/C4 使人编辑的故事线/设定对生成无效，修复方向与 PRD 一致。
- 不做题材检查器、不自动选优、不写「可发表」——本方案均不涉及。

## 5. 方案选项

### 选项 A：W2 缺失 goal/brief 时自动调用 goal_planner/creative_director（LLM）
- 优点：与 W1 完全同构，writer 输入面不变。
- 缺点：每章 +2 次 LLM 调用（¥0.02–0.05/章）、短环变慢；**与 B12「可继续」的轻量语义冲突，需 owner 推翻 B12**；仍不解决 C2（core_conflict/synopsis 依然没人读）。

### 选项 B：确定性注入（零 LLM 成本）——推荐
在 context 组装/writer 渲染层注入四块纯文本：
1. **story_brief**：书名 + core_conflict + mainline_synopsis + themes（+当前章所属 arc 的 arc_goal + open threads）。
2. **character_roster**：全部（或前 N 个）角色 `名字（角色类型）：背景`，来源 characters 表。
3. **world_settings**：复用已组装进 soft_references 的 world_setting refs，在 writer.py 增加渲染分支。
4. **project 钩子**：protagonist_background + core_hook（ProjectSetting 现成字段）。

配套：`chapter continue` 输出在「bible 空 且 goal/brief 空」时打印一行可见提醒（不阻断）。
- 优点：零成本、立即可验证、直接兑现「人编辑故事线系统必须听见」；不碰 B12。
- 缺点：writer 卡要新增版面（需控制 token，走独立小分区，cap ~600 token）；C5 仍建议补一个编辑面（可并小项）。

### 选项 C：A + B
- 推荐 **先 B 后看**：B 落地后，W2 首章至少有题材+大纲+人名+背景+设定+圣经五层定向，裸奔风险基本消除；若 owner 仍要章节级 specificity（target_events/hooks），再单独立项讨论 A（那时是推翻 B12 的产品决定）。

## 6. 建议切片（若立项）

- **切片 1（本体）**：B 的四块注入 + writer 卡新版面 + 空定向提醒。验收：构造无 goal/brief 项目，`chapter continue --chapter 1` 两次（空 bible / 有 bible）内容均贴大纲；回归 3654 全绿 + tests/cli 334 全绿 + ruff。
- **切片 2（小项）**：C5——`storyline edit outline` 时允许同步刷新 project.core_hook/protagonist_background（或新增 project edit 命令）。可并进切片 1。
- **另立小项（质量门）**：variant generate 产出低于校准下限时标记/拦截（F9），与 256 类质量小项同批。

## 7. 风险

- 注入文本挤占 writer 预算：需实测 token 占用（ch1 包当前 1705/14250，余量充足）。
- 角色背景可能含后文剧透（种子背景写了「他知道真相」类描述）：注入是确定性转述，人能看到自己在模板/编辑里写了什么，符合人主导；可用「仅注入主角+配角前 200 字」之类的保守裁剪，立项时定。
- card 版面变更要同步 craft card 版本（1.1.1 → 1.2.0）与既有测试断言。
