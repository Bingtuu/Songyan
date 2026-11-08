# 238 · M4 步 1 — 章进度视图 + `songyan status`

| 项 | 内容 |
|---|---|
| 状态 | DONE（代码落地，待 review） |
| 关联 | tech-m4 §5 步 1（**已接受**，B1–B12 原样）；编码循环第 1 步 |
| 预估 | 中切片（纯只读、无 LLM、零迁移） |

## 范围（tech-m4 §5 步 1 原文 + B 决策映射）

- [x] **章进度视图纯函数**（B1 推导）：推导输入 = `chapter_heads`（可能为 None）∪ `chapter_variants`（该章活动槽）∪ `chapter_versions` 存在性——**无 head 有版本的章可达**（`variant generate` 不写 head，`variant_generate.py:202-234`），输入必须含版本/variant 而不能只看 head。六态（全局优先级 **accepted 系 > picked > variants_ready > drafting > empty**，自上而下首个匹配）：
  - `stale` = 章已 accepted 且 `content_stale=1`
  - `settled` = 章已 accepted 且 `content_stale=0`（**accepted 系两态吸收所有 accepted 章**，无论其是否有活动 variant / 工作稿——评审 M2 修补）
  - `picked` = 章未 accepted 且存在 `status='picked'` 槽
  - `variants_ready` = 章未 accepted、无 picked 槽、存在未 abandoned/archived 的 `generated` 槽
  - `drafting` = 章未 accepted、无任何活动 variant、存在版本（head 的 `current_version_id` 非空或版本表有该章行）
  - `empty` = 以上皆否（head 存在但双指针 NULL 且无版本/variant 的罕见行；**章宇宙不含虚构章号**，见下）
  - 不可判定态（outlined / human_rewriting / in_review / needs_settlement）**不映射**（调研 Q1A / owner 认可）
- [x] **章宇宙口径**（评审 M3 修补）：统计与视图遍历的章集合 = `chapter_heads ∪ chapter_variants ∪ chapter_versions` 中出现过的章号；**不**虚构 `1..max_chapter`（`projects` 无计划章数列，`schema.sql:10-25`）
- [x] repo 只读扩建（§3.2 窄扩建范畴，两处）：`ContextSnapshotRepository` 按 project 查询 + `ChapterVariantRepository.list_by_project`（现网仅 `list_for_chapter`，`chapter_variant_repo.py:132`；章宇宙与 status 遍历需要）
- [x] `ContextSnapshotRepository` 查询用真实列名 `budget_used_before_emergency`（`schema.sql:222`）
- [x] **`songyan status --project-id TEXT [--json]`**（B10/B11）：项目级计数面——章进度分布（各态章数，按章宇宙口径）、未确认 picked 数、ContextEmergency 触发次数 / 最近触发章 / `budget_used_before_emergency`；纯只读；exit 0 = 成功 / 1 = 缺库 / 缺项目；usage 错误（缺 `--project-id` 等）按 Click 默认 exit 2 锁死（与 M3 variant 命令现网一致；**这是对 B11 的口径澄清**，完成总结里向 owner 标注）
- [x] `today` 接入视图：文本与 **`--json` 同步**增加章进度摘要（下一章状态 + 待确认 picked 数）；「下一章」显式用 B1 口径（范围内第一个非 accepted 章）；**`next` 固定文案保持 M3 口径不动**（M4 文案属步 5）
- [x] 测试：`tests/services/test_chapter_progress.py`（六态真值表 + 优先级 + 章宇宙 + 无 head 有 variant 边角）、`tests/cli/test_status_command.py`（字段含 emergency 三字段 + 无记录时 0/空边界 + exit 码 + --json）、`test_workbench_commands.py` 补 today 新行与 --json 断言；全部含**只读断言**（运行前后表行数不变）；`tests/cli` 单独跑（不在默认收集）

## 明确不做（本步边界）

- 不改 `chapter_heads` schema、不加列、不加 CHECK（B1 视图原则）
- 不注册 `chapter accept|continue` / `review`（步 2–4）
- 不动 `next` 文案、不动 `run` 管线
- status 不做 `chapter status`、不承载章 drill-down（B10）

## TDD 切片

1. 模型/推导测试先红：`ChapterProgressState` 六态 + 纯函数 `derive_chapter_progress(...)` 真值表（含优先级、无 head 有 variant、accepted 章再有 generated 槽、双指针 NULL 罕见行）
2. 服务组装测试：`load_chapter_progress(project_id)` 章宇宙（三源并集）+ 分布计数
3. repo 查询测试：snapshot 按 project 列表（含 emergency 三字段映射）+ variant `list_by_project` + 「无记录 → 空列表」边界
4. CLI 测试：`status` 文本 + `--json`（emergency 次数 / 最近触发章 / `budget_used_before_emergency` 三字段锁死 + 无记录时 0/空）+ exit 码；`today` 文本新行 + `--json`  parity

## 验收标准

- [ ] tech-m4 §7 定向命令过；全量回归零失败；ruff / mypy 绿
- [ ] 只读不变量：status / today / 视图函数全程零写库（测试断言行数不变）
- [ ] 代码 review 无 blocker；STATUS/HANDOFF 记步 1 完成

## 完成总结（DONE 时填写）

- **TDD 红→绿**：切片 1–3 先红（`ModuleNotFoundError: songyan.models.chapter_progress`，collection 失败）；切片 4 同上；实现后 40 passed（tests/services 13 + tests/cli/test_status_command 6 + tests/cli/test_workbench_commands 21，含 2 个新增 today 测试 + 1 个既有 shape 测试同步更新）。
- **新增**：`src/songyan/models/chapter_progress.py`（六态 StrEnum + `derive_chapter_progress` 纯函数 + Summary 模型）、`src/songyan/services/chapter_progress.py`（`load_chapter_progress` / `load_context_emergency`，纯只读）、`src/songyan/cli/commands/status.py`（`songyan status --project-id [--json]`）。
- **修改**：`db/repository.py`（`ContextSnapshotRepository.list_by_project` + 行映射抽 `_from_row`；`ChapterVersionRepository.list_chapter_numbers_by_project`）、`db/chapter_variant_repo.py`（`list_by_project`，全状态行，章号+槽号升序）、`cli/commands/workbench.py`（today 文本 + `--json` 增 `chapter_progress` 摘要行；`_NEXT` 未动）、`cli/main.py`（注册 `register_status_commands`）。
- **锁死**：六态真值表 11 例（优先级 / 无 head 有 variant / accepted 吸收 generated 槽 / 双指针 NULL）；章宇宙三源并集不虚构章号；snapshot emergency 三字段映射 + 无记录 0/空边界；status 文本 + `--json` 字段；缺库缺项目 exit 1；缺 `--project-id` exit 2（B11 口径澄清：usage 错误走 Click 默认，与 M3 variant 命令一致）；today 文本/json parity；只读断言（status/today/服务运行前后 chapter_* / context_snapshots 行数不变）。
- **验证**：`pytest tests/services/test_chapter_progress.py tests/cli/test_status_command.py tests/cli/test_workbench_commands.py -q` = 40 passed；`ruff check src/ tests/` 全过；`mypy`（6 个相关 src 文件）无 issue；全量回归 `pytest tests/ -q` + `pytest tests/cli -q` 见交接说明。
- **口径标注（给 owner）**：①B11 的 exit 2 具体化 = 仅 usage 错误（缺 `--project-id` 等 Click 参数错误）；业务/缺库缺项目面不改。②「已 accepted」实现口径 = `chapter_heads.accepted_version_id IS NOT NULL`（B1 写死句同源），不另看 `status` 列。③文本输出中无记录时 `last_chapter=-` / `budget_used_before=-`，`--json` 中为 `null`。
- **遗留**：无（M4 步 2 `chapter accept` 未动，按 §5 顺序下一切片做）。

