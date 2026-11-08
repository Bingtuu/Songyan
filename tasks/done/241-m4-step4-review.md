# 241 · M4 步 4 — `review`（只读共审报告）+ 复读/专名启发式

| 项 | 内容 |
|---|---|
| 状态 | DONE（2026-11-09） |
| 关联 | tech-m4 §5 步 4（**已接受**）；前置 = 步 1–3（已提交 `23bd3f3`） |
| 预估 | 中切片（只读聚合 + 两个新纯代码检查器） |

## 范围（tech-m4 B8 / §4.4 / B11；评审 M1–M5 已修入）

- [x] **命令**：`songyan review --project-id TEXT [--chapter INT] [--json]`；默认章 = 章宇宙中最近一章（B1 口径章号最大者）；`--chapter` 指定章不存在（不在章宇宙）→ exit 2
- [x] **被审正文口径（M1 决策）**：review 的被审对象 = **`head.current_version_id` 工作稿**（W2 共审针对未 accept 的工作稿，与 `check` 的 accepted 口径**显式分叉**并写明理由）；无 head / 无工作稿 → 依赖正文的源（gate / 复读 / 专名）分区空 + 注明「无工作稿」，不 exit 2
- [x] **输入并集（B8 七源，评审 M2/M3 修入）**：
  ① `run_plan_fact_gate` **现算**（mock 断言被调用 + 入参正文 = 工作稿；typed-attribute extracts 腿恒空，同 `check` 生产路径不传 extracts）；
  ② 三审报告：遍历该章**全部版本**取每版最新（`load_latest_audits(version_id)`）——审计跑在生成时 draft 版上，只看 accepted 副本会恒空；
  ③ `literary_observations`（`list_observations_by_chapter_range` 按章读，同受全版本口径影响——按章范围读即可）；
  ④ 复读启发式（新纯代码检查器，现算）；
  ⑤ 专名启发式（新纯代码检查器，现算）；
  ⑥ variant 备注：**直读 `ChapterVariantRepository().list_for_chapter`**（禁用 `list_variant_rows` 服务入口——它会 `refresh_stale_vs_canon` 写库，违反 B8）；
  ⑦ 人的 mark：`HumanMarkRepository` 纯读，过滤 `created_at_chapter ≤ 被审章`
- [x] **零写库（S4/B8 硬约束）**：全程不写任何表；**默认不调用 `merge_reviews`**（内存合并呈现）；测试 mock 断言 merge_reviews 未调用 + **表行数前后不变清单**：plan_* 五表 / review_reports / literary_observations / chapter_heads / chapter_versions / chapter_variants / context_snapshots / human_marks
- [x] **呈现**：markdown 默认（按严重度分组、带证据引用）；`--json` 结构化七源分区；发现问题仍 exit 0；exit 1 = 缺库 / 缺项目 / 参数非法；2 = 指定章不存在
- [x] **复读启发式检查器**（新纯代码，`plan_checks/repetition_check.py`，**不 import evals 模块**——拷贝纯函数，evals 顶层有 DB/采样依赖）：
  - 逐字句子复读：句子归一化 ≥12 字符且 ≥3 次（阈值原样保留，`excellence_signals.py:30,636-671`）
  - 逐字段落复读：段落归一化 ≥40 字符且 ≥2 次
  - 跨章句复读：**语义改写并写明理由**——evals 原语义是「跨样本语料索引」（不适配单项目逐章审）；review 场景 = **与上一章比对**（章号-1 的 **accepted** 正文，无 accepted 则跳过此腿并注明）；句 ≥14 字符
  - 输入 = 章正文 (+上一章 accepted 正文)；输出 = 结构化命中（quote / 位置 / 次数）；不调 LLM
- [x] **专名启发式检查器**（`plan_checks/proper_noun_check.py`，纯函数 v1，可判定规格）：
  - 拉丁候选 = 连续 A-Za-z 且首字母大写串（≥2 字符）
  - CJK 候选 = 出现 ≥3 次的 2-4 字 n-gram，减停用字表（实现锁定的虚词小表：的了吗呢吧啊哦嗯在与把被让向从和及或等）
  - 已登记集合 = `list_canon_entities`（approved）aliases ∪ `projects.protagonist_name` ∪ characters 表 protagonist 名（三处并集）
  - 匹配 = 精确、大小写不敏感；命中 = **info 级提示**（「未登记专名，考虑登记」），非错误

## 明确不做（本步边界）

- 不做 `review --deep`（LLM 深审）；不做写库审计（含复读/专名命中落库）
- 不调 `merge_reviews`；不触发 settlement / 任何生成；不调用 `list_variant_rows`
- 不做题材专用检查器；专名启发式保持薄封装
- 不改 `check` / gate 语义（gate 复用只读；正文口径分叉已写明）

## TDD 切片（先红后绿）

1. [x] **零写库切片**：运行前后上述八表行数不变 + merge_reviews 未被调用（mock）；exit 码三态（0 发现问题 / 1 缺库缺项目 / 2 章不存在）
2. [x] **输入并集切片**：七源 fixture（gate 硬伤 / 已落库三审 draft 版 / literary / 复读命中 / 专名命中 / variant stale / 人的 mark）→ 各源分区计数断言；**mock 断言 run_plan_fact_gate 被现算调用且入参正文 = 工作稿**；缺某源 → 分区空而不炸；无工作稿章 → 相关分区注明
3. [x] **复读启发式切片**：三腿各自命中 + 干净正文不误报（阈值原样）；跨章腿用上一章 accepted 正文、无 accepted 跳过
4. [x] **专名启发式切片**：未登记专名命中（拉丁 + CJK 各一）；approved aliases / 主角名 / characters protagonist 不命中；大小写不敏感
5. [x] **呈现切片**：markdown 严重度分组 + 证据引用存在；`--json` 全字段锁死；默认章 = 章宇宙最大章号

测试文件：`tests/plan_checks/test_repetition_check.py`、`tests/plan_checks/test_proper_noun_check.py`、`tests/cli/test_review_command.py`、`tests/services/test_review_report.py`（命名钉死）。

## 验收标准

- [x] 定向切片全绿；全量回归零失败；ruff / mypy 绿
- [x] 硬断言：零写库（八表行数 + merge_reviews 未调用 + gate 现算）有测试锁死
- [x] 代码 review 无 blocker；STATUS/HANDOFF 记步 4 完成

## 完成总结

**状态**：DONE（2026-11-09）。

**做了什么**：

1. `plan_checks/repetition_check.py`：复读启发式三腿纯函数（阈值 12/40/14 原样；跨章腿语义改写 = 与上一章 accepted 比对，写明理由；不 import evals）。
2. `plan_checks/proper_noun_check.py`：专名启发式 v1（拉丁大写串 / CJK ≥3 次 2-4 字 n-gram 减停用表；已登记 = approved aliases ∪ protagonist_name ∪ characters protagonist；精确大小写不敏感；info 级；长词吸收防刷屏）。
3. `services/review_report.py`：B8 七源只读聚合（被审正文 = current_version_id 工作稿，与 check accepted 口径显式分叉；三审遍历全版本；variant 直读 repo 不碰 list_variant_rows；不调 merge_reviews；12 表 ZERO_WRITE 清单）。
4. `cli/commands/review.py`：`songyan review --project-id [--chapter] [--json]`；markdown 严重度分组 + 证据引用；exit 0/1/2；空章宇宙 exit 0（--json 结构化空报告）。
5. 测试 32 例五切片：12 表行数不变 + merge_reviews 模块级未绑定断言 + gate 现算入参断言 + 七源分区计数 + 阈值/并集锁死。

**review**：任务文档评审 5 major（gate 正文口径 / 章→version 映射 / variant 写库陷阱 + 漏表 / 复读跨章语义与阈值 / 专名规格不可测试）全部先行修入；代码评审 1 major（usage exit 2 与 B11 字面冲突——按 task 238 确立的口径澄清裁决为既有约定非违规）+ 6 minor（m2/m3/m4/m5 已修，m1 章宇宙 heads 口径分叉已写明理由、全库两个章宇宙定义留观察，m6 边角记录）。

**验证**：定向 32 passed；受影响文件修复后复跑绿；全量回归终验（见提交）。
