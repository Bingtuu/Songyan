# 237 · M4 技术方案草稿（docs/tech-m4.md）

| 项 | 内容 |
|---|---|
| 状态 | DONE（2026-11-08，草稿已交付，**待 owner 书面接受**） |
| 关联 | 输入 = `docs/236-m4-preresearch.md`（owner 三轮评审定稿）；owner 2026-11-08 批准分阶段推进 |
| 预估 | 文档切片（草稿交付，接受权在 owner） |

## 范围

- [x] 精读 tech-m0–m3 全文，对齐结构、语气、约束表述方式
- [x] 起草 docs/tech-m4.md：逐字回答 S1–S4、P0-1..6、P1-1..7（P1-5 已决、P1-7 不改）
- [x] 必含节：状态口径 / review 写边界 / 确认交互模型（chapter accept vs resume、--json accept、三线接口定义）/ status 命令分工
- [x] 小步 5 步（对应编码任务 238–242）+ 验收 + 验证命令 + 风险
- [x] 自审 → 只读 review（0 blocker / 2 major / 10 minor，已全部修入）→ 归档 → 同步 STATUS/HANDOFF → 提交

## 验收标准

- [x] 与 tech-m0–m3 同构；不越出 PRD M4 边界（:172）；不声称 V1.0；不 bump。
- [x] 四条写死句各有唯一确定答案（无二义）。
- [x] review 无 blocker；owner 接受前不进入任何编码。

## 完成总结

**状态**：DONE（2026-11-08）。**草稿待 owner 按接受注记格式拍板**（对照 tech-m3 先例：widget 编号 + 「接受 tech-m4，按 B1–B12 开 M4 编码」）。

**产出**：`docs/tech-m4.md`——B1–B12 绑定决策：B1 严格 accepted 判定 + 目标章已有工作稿再跑 continue 的拒绝语义；B2 新 `chapter accept`（CLI 确认、不用 thread resume、**`--from-file` 人改稿写回路径**、PRD §9.2 树增量声明）；B3 accepted 写径作者路径唯一收口 + run 引擎路径不动的知情偏离理由 + N7 分列句；B4 逐章确认闸 + count 上限 3 仅防误敲；B5 accept 与 settlement 拆开（事务内仅此两件事、双指针同指副本、settlement 延至 continue 准备阶段、「是否已 settlement」判定口径钉死）；B6 正文节选 800 字硬顶 + 计入 budget_used + 走既有 emergency 管线；B7 `--variants` 函数级转调 M3；B8 review 零写库 + 不调 merge_reviews + 输入并集含人的 mark；B9 continue 挂 run 壳中断恢复；B10 `songyan status` 承载 ContextEmergency（chapter status 不承载）；B11 全命令 exit 码表；B12 `--require-plan` 默认警告 / 旗标拒绝。小步 5 步对应 task 238–242，顺序锁定（accept 在 continue 前）。

**review**：agent-14 对照调研 §9 全覆盖核查 + PRD 边界 + 10 处现网事实抽查全对；2 major（人改稿写回路径缺失 → B2 `--from-file`；目标章已有工作稿再跑 continue 语义未定义 → B1 拒绝钉死）与 8 minor 已全部修入（含 plan_* approved 集 vs pending 提案断言口径、双指针、B3 偏离理由、B4 措辞、mark 并集、status 计数口径）。

**验证**：无代码改动；review 修订后无 blocker / 未修 major。

**下一步（owner）**：书面接受 tech-m4（B1–B12 原样或点名修改）→ 按 §5 启动 task 238（步 1：章进度视图 + status）。
