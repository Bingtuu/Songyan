# 250 · review --deep（显式 LLM 深审，成本前置）

| 项 | 内容 |
|---|---|
| 状态 | DONE（2026-11-13；全量绿 + 真实模型复验 PASS，深审实花 ¥0.0107） |
| 关联 | `docs/tech-m4-followup.md` §5 / B4 / B5 / B6；task 236 N3 写边界口径 |
| 预估 | 两个编码切片（成本门 + 深审合并）+ 一次真实模型复验（¥1 内） |

## 目标

`songyan review --project-id TEXT [--chapter INT] --deep [--yes] [--budget-cny FLOAT]`：在现网七源只读报告上追加 LLM 深审分区（同一 `ReviewFinding` 形状，source=`deep`）。不带 `--deep` 现网行为一字不动。成本前置（B4）；零写库（B5）；LLM 失败保留非 deep 分区（stderr 注明）。

## 关键口径

- **成本门（B4）**：预估费用（token 估算，现成工具）打印 → 交互 y/N；`--yes` 跳过；**非 TTY 且无 `--yes` → exit 2**；`--budget-cny` 硬上限（预估超限拒绝 exit 2；执行超支中断并保留已产出）。
- **输入三件套（B6）**：工作稿正文（head.current_version_id）+ 本章 approved 圣经 + 上一章 accepted 摘要（120 字截断，`_get_previous_summary` 现成）。
- **检查四条（B6）**：事实一致性（hard）/ 连续性（hard/warning）/ 复读复核（warning/info）/ 文风视角（info，措辞红线：只说「建议人复核」）。
- **归因**：`call_llm` 标准遥测，agent=`review.deep`；无第二记账。
- **exit**：0 = 报告（含发现，B11 同形）；2 = 成本门拒绝；1 = 缺库/缺项目/参数非法/LLM 失败（非 deep 分区照出）。

## 步骤

- [x] TDD 切片 1：成本门（交互确认 / --yes / 非 TTY 拒绝 / 超预算拒绝），mock call_llm
- [x] TDD 切片 2：深审装配（三件套输入 prompt、结构化 findings 映射 ReviewFinding、合并进报告分区）；零写库断言（表行数快照）
- [x] 既有 review 测试原样通过（不带 --deep 零变化；唯一改动 = JSON key 锁测试吸收 deep_count 新字段，意图保留）
- [x] 真实模型复验 1 次（复用 249 冒烟 imported 项目 ch2）：exit 0，预估 ¥0.0166 / 实花 ¥0.0107 同量级；deep_count=4，2 hard 事实矛盾 + 1 hard 未入典事实 + 1 warning 连续性断裂，全部带原文证据；agent=review.deep 归因逐行可查
- [x] 全量回归 3631 passed / 2 skipped / 1 xpassed + ruff 绿；完工同步 STATUS/HANDOFF；归档

## 验收标准

- [x] 成本门四分支全锁死；非 TTY 无 --yes 必 exit 2
- [x] deep findings 合并呈现，severity/source/message/evidence/location 齐
- [x] 零写库 + 费用归因 agent=review.deep 逐行可查
- [x] 不带 --deep 现网行为零变化
- [x] 全量 pytest 绿 + ruff 绿；不 bump 版本
- [x] 完工同步 `docs/STATUS.md` / `docs/HANDOFF-mew.md`；归档 `tasks/done/`

## 完成总结

**状态**：DONE（2026-11-13）。`review --deep [--yes] [--budget-cny]` 落地（tech-m4-followup 步 3 收官）。

**做了什么**：`services/review_deep.py`（prompt 三件套拼装 / token 估价 / JSON 容错解析→ReviewFinding / run_deep_review 遥测归因 agent=review.deep）；`review` CLI 加 --deep/--yes/--budget-cny 与成本门（B4：预估打印→超预算拒绝→--yes→交互 y/N→非 TTY 拒绝 exit 2）；deep findings 与七源同形合并呈现，报告加 deep_count 字段；LLM 角色清单注册 reviewer（可路由，默认回落全局配置）。

**测试**：16 新测（services 纯函数 8 + CLI 门/合并/零写库 8）TDD 全链路；既有 review 套件 15 测原样通过（JSON key 锁吸收 deep_count）；全量 3631 passed + ruff 绿。真实模型复验：深审 4 findings 全部有原文证据、口径符合 B6；预估 ¥0.0166 vs 实花 ¥0.0107。

**遗留**：无。tech-m4-followup 三步全部闭环，§9 清零（S5 产品向除外）。
