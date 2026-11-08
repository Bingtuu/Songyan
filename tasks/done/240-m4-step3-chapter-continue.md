# 240 · M4 步 3 — `chapter continue`（W2 短环核心编排）

| 项 | 内容 |
|---|---|
| 状态 | DONE（2026-11-08） |
| 关联 | tech-m4 §5 步 3（**已接受**）；前置 = 步 2（task 239，已提交 `f205f8a`，`accept_chapter` 可用） |
| 预估 | 大切片（M4 核心；编排 + 上下文组装 + run 壳；mock 模型测试） |

## 范围（tech-m4 §4.2 + B1/B4/B5/B6/B7/B9/B11/B12；评审 M1–M4 已修入）

- [x] **命令**：`songyan chapter continue --project-id TEXT [--count 1] [--variants N] [--require-plan] [--json]`（`chapter` 组第二个子命令）
- [x] **目标章判定（B1）**：= 第一个 `accepted_version_id IS NULL` 的章（章号升序，与步 1 视图同口径）。exit 2 两前置：① 目标章之前存在 picked 未 accept 的章（仅「accepted 章残留 picked 槽」可达——M3 pick 不拦 accepted 章；夹具按此构造）；② 目标章已有未确认工作稿（draft/picked）——提示先 `chapter accept` 或 `variant pick|abandon`；**无自动重生成旗标**。空项目 / 全 accepted → exit 0「全部章已 accepted」
- [x] **准备阶段（B5 + 评审 M1/M2）**：紧邻上一章 accepted 且**未 settlement**（复合判定：**summaries 无该章记录 且 结算观测层无该 accepted 版本行**——如 `character_states.source_version_id = accepted_version_id`；两条件皆无才重跑，测试钉死）→ 跑完整 settlement 序列（同 `settlement_extractor_node`：`extract_settlement` + `apply_settlement` + **SummaryWriter 写 summaries 行**，`_nodes.py:3265-3324` 子步骤）；重跑前 stderr 提示。RAG 索引 / lifecycle 清理 / SettingEvaporator **不属于本步**。首章（无上一章）跳过
- [x] **`--require-plan`（B12 + 评审 minor 4）**：判定 = 本章圣经五类 id 列表全空（用 `select_chapter_plan_bible_cards`，**不用** `text == ""`——仅有实体卡时 render 为空串但非真空）；缺 `chapter_goal` 同属缺失（见下回退）。默认：警告文案（stderr）+ 继续；旗标：拒绝 exit 2
- [x] **组装 + 生成（B6 + 评审 M3）**：
  - **节选注入通道（锁定）**：给 `workflows/_helpers.assemble_context_package` 加 `last_chapter_ending: str = ""` 透传 → `RecentPlot.last_chapter_ending`（现网通道，`context_manager/__init__.py:1037, 937`；**计入 budget_used、emergency 时按既有管线降级**——正是 B6 口径，禁止事后 setattr 绕过）。continue 截取上一章 accepted 正文末尾 ≤800 字传入；默认空串 = `run` 管线行为不变
  - **chapter_goal 回退**：`ChapterGoalRepository.get_by_chapter` 无行 → `ChapterGoal(chapter_number=N, word_count_target=project.words_per_chapter)` 兜底（B12 默认模式可继续）
  - **brief 来源**：新增 `CreativeBriefRepository.get_by_chapter` 窄查询（本步第二处 repo 只读窄扩建，申报；缺失 → `None` 继续，helper 签名允许）
  - **draft 落库复用 `agents/writer.py:694 write_chapter`**（渲染 + bible wrap + 追加 `version_type='draft'` + head 指针、无 head 则建——正是本步所需；其清 `accepted_version_id` 行为对 B1 目标章无影响）
  - 120 字 `plot_summary` 摘要经既有 recent_plot 注入（现网 `_get_previous_summary` 同款读取，截取逻辑不变）
- [x] **费用归因（评审 minor 6）**：continue 全程 `bound_contextvars(project_id, chapter_number, agent=...)`（照 `variant_generate.py:136-138`）；run 预算守卫所需 run 上下文一并绑定（`llm/client.py:494-509` 口径）
- [x] **`--variants N`（B7）**：函数级转调 `generate_chapter_variants`（M3 语义原样：不 auto-pick、plan_* 不变）；pick 仍由人显式调；`--variants` × `--count` 组合 = 本章转调生成后同停闸语义（逐章）
- [x] **`--count N`（B4 + 评审 minor 7）**：N ≤ 0 或 > 3 → exit 1；逐章循环，每章生成完毕即停闸打印「先 `chapter accept --chapter X`」；未 accept 不推进；循环因前置拒绝而停 → exit 0 + 进度消息。**单次 invocation 实际最多生成一章**（停闸结构决定，非实现缺陷，勿过度设计循环）
- [x] **run 壳（B9 + 评审 M4）**：continue 自建壳编码为**单章壳**（`chapter_range_start == chapter_range_end == 目标章`）；恢复查找借 `_find_resume_run` 方式但**加状态过滤（status ∈ running / paused）**且**只收养单章壳**——engine run 壳不匹配则新建，不收养；LLM 失败 / 预算熔断 → status=`paused`（现网值，非 pause）+ `pause_reason`；再次 continue → 续跑（只追加新版本，幂等）；「resume 时版本已落库」场景由 B1② exit 2 接管（锚定测试）
- [x] exit（B11 + 评审 minor 1）：0 = 生成待确认 / 停闸 / 全部完成；1 = 缺库 / 缺项目 / 参数非法 / **LLM 失败与 settlement 阶段 LLM 失败**（写 pause_reason 后 exit 1）；2 = B1 两前置 / `--require-plan` 拒绝；3 = 预算耗尽（已写保留，沿用 variant 语义）

## 明确不做（本步边界）

- 不做 `review`（步 4）；不改动 `accept_chapter`；不内嵌第二套生成逻辑（B7 转调）
- 不改 `run` 管线 / `phase1_graph` / `phase2_graph` 语义（helpers 透传参数默认空串 = 行为不变）
- 不做交互式确认提示符（B2）；不做 auto-pick / auto-accept / 自动重生成
- RAG 索引 / lifecycle 清理 / SettingEvaporator 不进本步 settlement 序列

## TDD 切片（mock 模型；先红后绿）

1. **门禁切片**：B1 两前置 exit 2 且零写入（① 夹具 = accepted 章残留 picked 槽）；目标章判定跨章；`--count 4` / `--count 0` → exit 1；空项目 / 全 accepted → exit 0 提示
2. **settlement 准备切片**：上一章 accepted 无 summary 且无结算行 → 完整序列（结算表新行 + summaries 新行 + plan pending 提案 + **approved 集不变**）；有 summary → 跳过；有结算行无 summary（replay 遗留）→ 跳过（复合判定，M2）；首章跳过
3. **组装 + 生成切片**：`last_chapter_ending` 透传断言（helpers 收到 ≤800 字节选；1200 字 → 末尾 800；不足 800 全取；**恰好 800 边界**）；chapter_goal 回退（无行 → words_per_chapter 兜底）；brief 缺失 None 继续；draft 版本追加 + head 指针；`--json` **全字段**（chapter / version_id / word_count / cost_cny / next_hint）锁死
4. **`--variants` 转调切片**：`--variants 2` → 两槽 generated、不 auto-pick、plan_* 不变；`--variants 2 --count 2` → 本章生成后停闸 exit 0
5. **run 壳切片**：mock LLM 抛错 → status=`paused` + pause_reason 落库 + exit 1；再次 continue → 续跑成功、版本只追加；预算熔断（mock `LLMBudgetExceededError`）→ 已写保留 + exit 3；engine run 壳不收养（锚定测试）
6. **逐章循环切片**：`--count 2` 第一章生成后停闸 exit 0 + next_hint；accept 后再 continue 推进第二章；resume 时版本已落库 → B1② exit 2

## 验收标准

- [x] 定向切片全绿；全量回归零失败；ruff / mypy 绿
- [x] 硬断言：每切片 `plan_*` approved 集不变 + accepted 集不变（无自动 accept）；settlement 切片断言 approved 集不变
- [x] 代码 review 无 blocker；STATUS/HANDOFF 记步 3 完成

## 完成总结

**状态**：DONE（2026-11-08）。

**做了什么**：

1. `services/chapter_continue.py`：M4 核心编排——B1 门禁（两前置 exit 2 零写入，复用步 1 `load_chapter_progress` 同口径）/ B5 settlement 准备（复合判定 + extract+apply+summary 序列，RAG/lifecycle/evaporator 不入）/ B6 组装（`assemble_context_package` 加 `last_chapter_ending` 透传，≤800 字节选走现网 RecentPlot 通道计入 budget；chapter_goal 回退；brief 窄查询）/ B7 函数级转调 M3 / B9 单章壳 + running/paused 过滤 + 不收养 engine 壳 / B12 五类 id 列表判定 / B11 exit 分层 / 费用 bound_contextvars 归因。
2. repo 窄扩建（申报两处）：`CreativeBriefRepository.get_by_chapter`；helpers 透传参数（默认空串 = run 行为不变）。
3. 测试 30 例（六切片 + M1 回归锁）：每切片 plan_* approved 集 + accepted 集不变硬断言。
4. **review major M1 修复**：`--variants` 路径 `VariantGenerateLLMError`（非 LLMError 子类）穿透暂停逻辑致 run 壳滞留 running + 裸 traceback——except 元组补该异常 + 新增 variants LLM 失败暂停测试。

**review**：任务文档深度评审 4 major（settlement 漏 SummaryWriter / 判定口径误报源 / 组装三卡点 / run 壳两欠定义）+ 7 minor 全部先行修入文档再实现；代码评审 1 major（M1，已修）+ 4 minor（记录：settlement 观测层只看 character_states 的已知盲区、壳不记进度字段、门禁零写入断言面、run_shell 切片 approved 断言缺口）。

**验证**：六切片 + 回归 62+ passed（M1 修复后受影响文件复跑绿）；ruff / mypy 绿；全量回归终验（见提交）。
