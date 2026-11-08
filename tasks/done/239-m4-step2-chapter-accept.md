# 239 · M4 步 2 — `chapter accept`（章级人确认写径）

| 项 | 内容 |
|---|---|
| 状态 | DONE（2026-11-08） |
| 关联 | tech-m4 §5 步 2（**已接受**）；前置 = 步 1（task 238，已提交 `c55a714`） |
| 预估 | 中切片（M4 核心写径，副作用路径 TDD 从严） |

## 范围（tech-m4 B2/B3/B5/B11）

- [x] **accepted 写径唯一服务函数** `services/chapter_accept.py`：`accept_chapter(project_id, chapter_number, from_file: Path | None) -> AcceptOutcome`
- [x] **事务内容（仅此两件事，B5）**：① `ChapterVersionRepository.accept_version`（现成语义：追加 `version_type='accepted'` 副本、`parent_version_id` 指向被确认稿、原稿不动、`version_number` 递增——`repository.py:555-607`）；② `ChapterHeadRepository.update`：`accepted_version_id` 与 `current_version_id` **一并指向该副本**、`status='accepted'`（upsert 只更四列、不落 `content_stale`，`repository.py:786-817`，无需 head repo 扩建）。**同一连接同一事务**，镜像 `accept_with_settlement_boundary` 的事务骨架（`workflows/_nodes.py:2946-2974`）去掉 settlement 部分
- [x] **settlement 拆开锁死（B5）**：事务内**不**调用 SettlementExtractor、**不**写任何结算表、**不**产生 `plan_*` pending 提案；settlement 提取属 continue 准备阶段（步 3），本步不做
- [x] `--from-file PATH`（B2）：外置编辑稿作为 accepted 副本来源——事务内先物化 `version_type='edited'` 行（parent = 原工作稿、**word_count 按文件内容实算**，照 `_nodes.py:2763` 口径；`version_number` 在**同一 conn** 上 `MAX+1`，**不用** `get_next_version_number`——它自建连接看不到本事务未提交写入），再对该行走 `accept_version` 副本链（edited → accepted）。edited 行物化属于 B5① 的一部分（复用 `accept_version` 只能整行复制的必然形状，与现网 run 人改分支同构 `_nodes.py:2756-2766`）；文件为空 / 读失败 → exit 1
- [x] **命令**：`songyan chapter accept --project-id TEXT --chapter INT [--from-file PATH] [--json]`（新 `chapter` 子组的首个子命令——建组再挂，模式参照 `register_variant_commands` 的组注册）；exit 照抄 B11：0 = 成功 / 1 = 缺库 / 缺项目 / 参数非法（含文件错误）/ 2 = 无可确认稿 / 重复 accept（幂等提示）
- [x] **plan_* 零触碰**：accept 前后 `plan_*` 五表行数与 approved 集不变（测试快照断言，B3 精神）

## 明确不做（本步边界）

- 不做 `chapter continue`（步 3）；不做 settlement 触发；不做 `--require-plan`
- 不改 `run` 管线内既有 accept 写径（B3：引擎路径不动）
- 不 touched `chapter_heads` schema；不动 variant 行（pick 留下的 picked 槽保持原状）
- 不做 `chapter status` / 任何其他 `chapter` 子命令

## TDD 切片（先红后绿）

1. [x] **副作用路径先红**：accept 后结算库零新行——断言明细照 SettlementExtractor apply 写集：`characters`、`character_states`、`numerical_ledgers`、`setting_snapshots`、`setting_tracking`、`inventory_tracker`、`location_tracker`、`foreshadowings`、`permanent_scenes` 九表 + plan 五表（pending 行数与 approved 集）；`plan_*` 前后快照不变；事务原子性 = 终态断言 + **故障注入**（head.update 抛错 → `chapter_versions` 无新行、`chapter_heads` 原状、无残留事务）
2. [x] **副本链**：`draft → accepted`（parent 链、version_number 递增、原稿 `version_type` 不变）；`picked → accepted`；`--from-file` 三段链 `draft → edited → accepted`（edited 行 **word_count 按文件实算**、version_number 同 conn MAX+1 口径）
3. [x] **拒绝路径**：无可确认稿 exit 2 且**失败路径零写入**；区分两种 exit 2——head 行不存在（防 upsert 静默建新 head）与 `current_version_id` 为空；重复 accept exit 2（幂等提示，不产生新版本）
4. [x] **CLI**：文本 + `--json`（accepted_version_id / 章号 / 字数）；exit 码表逐项

## 验收标准

- [x] 定向测试全绿；全量回归零失败；ruff / mypy 绿
- [x] 测试含「accept 后结算库零新行」与「plan_* approved 集不变」两条硬断言
- [x] 代码 review 无 blocker；STATUS/HANDOFF 记步 2 完成

## 完成总结

**状态**：DONE（2026-11-08）。

**做了什么**：

1. `services/chapter_accept.py`：accepted 写径唯一服务函数 `accept_chapter`；事务镜像 `accept_with_settlement_boundary` 去 settlement（B5）；head 先 get 后判（防 upsert 静默建行）；异常三件套（NothingToAccept/AlreadyAccepted→exit 2、ChapterFileError→exit 1）。
2. `cli/commands/chapter.py`：`chapter` 子组 + `accept` 命令（--from-file / --json）；main.py 注册。
3. `repository.py` 共享改动：`accept_version` 传 conn 时同连接读原稿（`--from-file` 事务内 edited 行未提交、自建连接读不到的必要修改；既有两调用方行为等价，review 核实无回归）。
4. 测试 22 例：九结算表零新行 + plan 五表快照 + 故障注入回滚 + from-file 三段链（parent/word_count/同 conn 连续编号）+ 三种拒绝零写入 + CLI --json + B11 exit 码逐项。

**review**：任务文档评审 2 major（回滚故障注入、head 缺失零写入断言）+ 7 minor 已先行修入；代码评审无 blocker / major，6 minor 已修 2（过期注释、row_factory 注记），余 4 记录（TOCTOU 单写者可接受、悬空指针兜底留步 3、弱名测试、`_do` 闭包读法）。

**验证**：定向 22 passed；相关回归 43+5 passed；ruff / mypy 绿；全量回归终验（见提交）。

**同切片附带修复（生产 bug，review 级重大发现）**：`test_llm_http_timeout` 在全量回归中失败，深挖后发现**真根因**与任务 235 的「负载敏感 flake」诊断不同——`ChatLiteLLM` 没有 `base_url` 字段（只有 `api_base`，Pydantic extra=ignore 静默丢弃），自定义 base_url 从未真正生效；当天上午该测试的「通过」全部是假通过（断网期 ConnectTimeout 恰好匹配「超时」断言，401 被掩盖），网络恢复（push 直连成功同一时段）后暴露。修复：`_build_llm_client` 改传 `api_base=base_url`（`src/songyan/llm/client.py`），并在 `tests/test_llm_client.py` 加防回归断言（client.api_base 锁死）。修复后该测试真实打本地悬挂服务器并按时切断。STATUS 环境项条目已同步修正。
