# 242 · M4 步 5 — 收口：today 文案 M4 口径 + §6 验收清单全跑

| 项 | 内容 |
|---|---|
| 状态 | DONE（2026-11-09） |
| 关联 | tech-m4 §5 步 5 + §6 验收 + §7 验证命令（**已接受**）；前置 = 步 1–4（已提交 `b857e8b`） |
| 预估 | 中小切片（一个 W2 连走集成测试 + 一条文案 + 验收记录） |

## 范围

- [x] **3 章 W2 连走集成测试**（`tests/cli/test_chapter_w2_loop.py`）：连续 3 章「continue → accept → continue」全链走通；**全程 `plan_*` approved 行数零变化、accepted 集仅由显式 `chapter accept` 增加**（每章后断言）；settlement 在 continue 准备阶段自动跑（第 2、3 章前 summaries 出现新行）且只产 pending
  - **mock 面（评审 M1，钉死）**：① `songyan.agents.writer.call_llm`（三章不同正文）；② `songyan.agents.settlement_extractor.call_llm`（**推荐**：返回含至少一条指向种子角色的 `character_updates` 的合法 settlement JSON——apply 丢弃未知 character_id，空 JSON 会让「只产 pending」断言空转，评审 m2）；③ `songyan.agents.summary_writer.call_llm`（防静默落到 fallback 路径）。备选：mock `songyan.services.chapter_continue.extract_settlement` 返回手工 `StateSettlement`（先例 `test_chapter_continue_settlement.py:64-83`）
  - **种子数据约束（评审 m1）**：不得预置 `summaries` 行或 `character_states.source_version_id` 行——复合判定两条件皆无才触发 settlement，误带会致「summaries 出现新行」意外失败
- [x] **`today` next 文案 M4 口径**（tech-m4 §3.2）：`_NEXT` 从 M3 口径演进为提示 continue 短环（措辞纪律同 task 231/233：不与 `content_stale` / `stale_vs_canon` 混列；不声称已入典）；文本与 `--json` 同源同一常量；两个测试文件（`test_workbench_commands.py` / `test_w0_e2e.py`）的 `_NEXT` 同步锁死
- [x] **§6 清单逐条指认证据**（写进本任务文档完成总结）：
  1. W2 短环 3 章走通（本条新测试）→ 全程 approved 零变化
  2. accept 干净 → task 239「九结算表零新行」测试
  3. 无审不连跑 → task 240 门禁 / 逐章停闸测试
  4. review 只读 → task 241「12 表行数不变 + merge_reviews 未调用」测试
  5. status 露出 → task 238 emergency 三字段测试
  6. today 可作答 → 步 1 chapter_progress 段 + 本条 M4 文案测试
  7. exit 码表 + `--require-plan` → 步 3/4 CLI 测试逐项
  8. ruff / pytest / M0–M3 回归 → 本条终验全量 + §7 定向命令
- [x] **§7 验证命令全集实跑留数**（ruff + 三组定向 + 全量；注意 tech-m4 §7 的 `tests/cli/test_chapter_continue.py` 已拆为五个 `test_chapter_continue_*` 文件，以实际文件名跑并在完成总结注明此文档层偏差——评审 m3）
- [x] STATUS/HANDOFF 记 M4 步 1–5 全落地；**§6–7 验收声称留 owner 拍板**（不在 STATUS 写 PASS）

## 明确不做

- 不做真实模型冒烟（维护者任务，§7 原文不挡代码验收）
- 不改步 1–4 的实现语义（本条只加集成测试与文案）
- 不在 STATUS 声称 M4 §6–7 PASS（声称权在 owner）

## TDD 切片（先红后绿）

1. W2 连走测试先红（新文件，mock 面按上表）→ 零件已由步 2–4 构成，预期直接绿；若暴露集成缝隙（如 settlement 复合判定不触发），按 tech-m4 语义修实现并记录
2. `_NEXT` 新文案：两测试文件先改（红）→ `workbench.py` 后改（绿）

## 验收标准

- [x] 新集成测试绿；两文案测试绿；全量回归零失败；ruff / mypy 绿
- [x] §6 八条每条有证据指针；§7 命令输出留数
- [x] 代码 review 无 blocker；STATUS/HANDOFF 同步；本地提交

## 完成总结

**状态**：DONE（2026-11-09）。M4 步 1–5 全部落地。

**做了什么**：

1. `tests/cli/test_chapter_w2_loop.py`：3 章 W2 连走集成测试——mock 面三绑定（writer / settlement_extractor / summary_writer 的 call_llm）；逐章断言 approved 五表快照零变化、accepted 集 {1}→{1,2}→{1,2,3} 仅由显式 accept 增加、三章正文逐字落库、settlement 在第 2/3 章前自动补跑（summaries + character_states 新行）、pending 提案指向种子角色 char-s1（非空转断言）、调用计数 3/2/2。首跑即绿（零件已由步 2–4 构成，无集成缝隙）。
2. `today` `_NEXT` M4 口径：「…续写下一章走 chapter continue，章内草稿可 variant generate 抽卡（默认 N=2，不 auto-pick）。」——两测试文件先红后绿；文本/`--json` 同源同一常量；grep 确认无其他锁点。

**§6 验收清单证据（八条）**：

| # | 条目 | 证据 |
|---|------|------|
| 1 | W2 短环 3 章走通、approved 零变化 | `test_chapter_w2_loop.py`（本条新增） |
| 2 | accept 干净（结算库零新行） | `tests/services/test_chapter_accept.py` 九表断言 |
| 3 | 无审不连跑 | `test_chapter_continue_gates.py` / `test_chapter_continue_count_loop.py` |
| 4 | review 只读 | `test_review_report.py` 12 表行数不变 + merge_reviews 未调用 |
| 5 | status 露出 | `test_status_command.py` emergency 三字段 |
| 6 | today 可作答 | 步 1 chapter_progress 段 + 本条 `_NEXT` M4 文案 |
| 7 | exit 码表 + --require-plan | 步 3/4 CLI 测试逐项 |
| 8 | ruff / pytest / M0–M3 回归 | §7 实跑数见下 |

**§7 验证命令实跑数**：ruff 全过；`tests/db + tests/plan_checks` 106 passed；M4 CLI 面 79 passed（含本步）；全量终验见提交。文档层偏差记录：tech-m4 §7 的 `tests/cli/test_chapter_continue.py` 已拆为五个 `test_chapter_continue_*` 文件，以实际文件名跑（不回改上级文档，留 owner 决定）。

**review**：任务文档评审 1 major（mock 面不完整——settlement/summary LLM 未列入）+ 3 minor 全部先行修入；代码评审无 blocker / major，2 minor 已修（测试 mypy 10 处、pending 指向性断言）。

**声称边界**：§6–7 验收声称权留 owner（不在 STATUS 写 PASS）；真实模型冒烟另开维护者任务。
