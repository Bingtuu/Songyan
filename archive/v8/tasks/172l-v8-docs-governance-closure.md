# Task 172l: V8 文档治理收口

> **阶段**: V8 收口遗留
> **类型**: 文档治理
> **优先级**: P3（纯文档，不影响代码与实跑证据；但影响 V8 事实源的可信度）
> **依赖**: 无（172b 报告 CED 注记一项建议与 172j/172k 无依赖，可立即做）
> **状态**: ✅ 完成（2026-07-18）
> **来源**: 2026-07-18 V8 完成度独立 review（文档交叉核对发现）

---

## 背景

Review 确认 V8 核心事实（P/Q/S/V、双体裁 Ch100 五门 PASS）证据链完整、数字互洽，且两次口径修正（172b.q CED、172c.r health）均为透明披露。但文档治理有四处欠账，会让单读某份文档的读者得到错误印象或找不到完成证据。

---

## 修复清单

| # | 位置 | 问题 | 修复动作 |
|---|---|---|---|
| 1 | `tasks/172c.q-wuxia-inventory-identity.md` | 头部仍写"🔄 实现完成，待段 3 实跑复验"，与 V8-README 的 ✅ 完成矛盾；段 3 与 clean rerun 早已完成 | 头部翻正为 ✅ 完成，补段 3 复验结论 + clean rerun 证据引用（`tasks/172c-wuxia-ch100-clean-rerun-DONE.md`） |
| 2 | `docs/reports/172b-xuanhuan-ch100-climb.md` | 仍展示旧 harness 口径 CED/1k=10.7489（旧口径下 > 10.50 ceiling，是 FAIL），未加修正说明；单读该报告会得到 V 维度未达标的错误印象 | 参照 `docs/reports/172c-wuxia-ch100-climb.md` 的口径说明格式，加注记：旧口径仅历史存档，终判以 172b.q 修正口径 0.4434 ≤ 0.4573 为准（`tasks/172b.q-consistency-ced-repair.md`） |
| 3 | `tasks/172e-*.md` ~ `tasks/172i-*.md` 五份 | 均为规划文体，正文无执行结果/验证记录；完成证据只寄存在 `docs/STATUS.md` | 每份补"执行记录"小节：测试文件清单、新增测试数（合计 41）、全量 `2746 passed`（172e-i 合入时）→ `2791 passed`（172c 收口）、ruff 全绿、scifi end10 回归结果，从 STATUS.md 回填 |
| 4 | `tasks/V8-README.md` 文档入口 | `172b.p` 文档存在（`tasks/172b.p-xuanhuan-foreshadowing-long-window.md`）但未进文档入口；172c.s 报告模板遗留（标题误写 Task 172b）未记录 | 文档入口补 172b.p；172c.s 模板遗留作为已知小瑕疵登记或顺手修掉 |

---

## 验证

- 纯文档任务，无需 pytest；
- 完成后 grep 一致性自查：
  - `grep -r "🔄" tasks/172c.q*.md` 无残留；
  - V8-README 任务表中每个 ✅ 的任务文档头部状态一致；
  - `docs/reports/172b-xuanhuan-ch100-climb.md` 中 CED 数字旁必有口径指引。
- 数字回填必须与 STATUS.md / 172b.q / 172c DONE 逐值一致，不凭记忆写数。

---

## 出口标准

1. 清单 4 项全部落地；
2. V8-README「当前验收状态」与「Task 状态」表无与实际文档矛盾的行；
3. 单读 172b Ch100 报告不会再得出 V 维度 FAIL 的错误结论。


---

## 执行记录（2026-07-18）

| # | 修复 | 结果 |
|---|---|---|
| 1 | `tasks/172c.q-wuxia-inventory-identity.md` 头部翻正为 ✅ 完成，补段 3 复验 + clean rerun 证据引用 | `grep 🔄` 残留 0 |
| 2 | `docs/reports/172b-xuanhuan-ch100-climb.md` 结论段补 CED 口径注记（旧 harness 10.7489 仅存档，终判以 172b.q 0.4434 ≤ 0.4573 为准） | 已落盘 |
| 3 | 172e-172i 五份文档各补「执行记录」小节（测试文件与用例数 12/14/5/5/5=41、2746→2791 passed、ruff 全绿、scifi end10 回归） | 已落盘 |
| 4 | V8-README 文档入口补 `172b.p`；172c.s 模板遗留经核对为已修复（harness 按 RUN_ID 输出，现报告标题正确），无需动作 | 已落盘 |

验证：五项 wiring 测试文件复跑 **58 passed**；文档间状态一致。
