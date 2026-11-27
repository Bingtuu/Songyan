# 270 · 修复抽取提案 attribute_id 碰撞

| 项 | 内容 |
|---|---|
| 状态 | TODO |
| 关联 | `enqueue_extract_proposals` / `_attribute_id`（`src/songyan/agents/settlement_extractor/_proposals.py`）；task 269 `filter_pending`（`src/songyan/services/pending_groups.py`）；2026-11-16《后巷座钟》实模型验收 |
| 预估 | 一个编码切片（TDD） |

## 上下文

2026-11-16 用 `urban_horror` 验收《后巷座钟》（project `73de90bcd4de4af9bbc11c4a41bd61b8`）第 1–2 章时，`canon pending` 全集是 3 个实体 + 5 条属性，但 `canon pending --chapter 1` 只给出 2 个实体 + 5 条属性，缺了设定「后巷座钟」。

当时看起来像 269 的按章归组漏了「没有章节引用的实体」。查库后，**269 的过滤口径没有写错**：`plan_entities` 本身没有章节列，`--chapter N` 生效时 entity 只经过滤后 attribute 的 `entity_id` 引用归组。全集里的「后巷座钟」实体是因为**一条描述属性都没有**，所以按章过目时落选。

根因在抽取写提案。`_attribute_id` 对 `entity_id` 调用 `_slug(..., max_len=48)`。下面两个设定 id：

- `ext-set-73de90bcd4de4af9bbc11c4a-urban_supernatural-clock-alley_standing_clock`
- `ext-set-73de90bcd4de4af9bbc11c4a-urban_supernatural-pocket_watch-engraved`

截断后都是 `ext-set-73de90bcd4de4af9bbc11c4a-urban_supernatu`，于是同一章的 `description` 生成了同一个 `attribute_id`：

`ext-73de90bcd4de4af9bbc11c4a-ext-set-73de90bcd4de4af9bbc11c4a-urban_supernatu-description-c1`

`write_attribute` 走 `ON CONFLICT(attribute_id) DO UPDATE`，后写入的「刻字怀表」描述覆盖了先写的「后巷座钟」描述。验收库里只剩刻字怀表那一条 `description`；后巷座钟实体还在（`approval_status=pending`），属性为 0。结果是：按章过目看不见它，它的描述提案也丢了。

本任务修的是这个碰撞，不是放宽 269 的过滤。

## 目标

同一章抽出的不同实体，必须写下互不覆盖的 pending 属性。这样 `canon pending --chapter N` 才能按 269 口径列出本章全部相关实体，描述等提案也不会被后一个实体抢走。

## 约束

- 先写测试再写实现。新测试放 `tests/<area>/test_<行为>.py`，禁止新增 `test_task###_*.py`。
- 269 的过滤口径保持不变：`--chapter` / `--source` 生效时，entity 仍只经过滤后 attribute 的 `entity_id` 引用归组。不要靠放宽过滤来「带上」孤儿实体，那修不回被覆盖掉的描述提案。不要给 `plan_entities` 加章节列来绕过这次碰撞。
- 不要改结算权威。结算库仍是 `untrusted_until_confirmed` 对照，不升格 Canon；结算声称回收只进提案（task 226），本任务不动。
- `canon confirm batch --yes` 保持显式捷径，不进入 `chapter continue` / `chapter accept` 的默认环。
- 不必迁移或修复已经写进旧库、已被覆盖的碰撞行；说明一下即可。新抽取不得再碰撞。
- 包版本保持 `0.5.0`，不宣称 V1.0。STATUS/HANDOFF 等验收通过后再同步。

## 步骤

- [ ] 先补失败测试，再改 `_attribute_id`（或同等生成函数）。夹具：同一章调用 `enqueue_extract_proposals`，写入两个 `new_settings`，`setting_key` 要足够长且前缀相同（复现 `urban_supernatural-…` 这类），两个设定名不同。
- [ ] 生成规则自定，但必须钉死：`(project_id, entity_id, key, chapter)` 对应稳定且全局唯一的 `attribute_id`；同一实体同一 key 同一章再入队仍幂等（更新同一行，不另插一行）；不得覆盖**另一个**实体已写下的属性。
- [ ] 跑相关回归：`tests/cli/test_extract_pending_proposals.py`、`tests/test_settlement_extractor.py`、pending 分组测试；全量 pytest + ruff。

## 验收标准

- [ ] 上述长前缀双设定夹具：抽出后有两条 pending `description`，分别挂在两个 `entity_id` 上；`canon pending --chapter N`（或同等过滤函数）同时列出这两个实体和这两条属性。
- [ ] 同一实体、同一 key、同一章第二次入队：仍是同一 `attribute_id`，不新增行；值按既有幂等规则更新。
- [ ] 不同章的同一实体同一 key：id 不同，互不覆盖。
- [ ] 角色属性路径（`character_updates` / `numerical_updates`）不回归；既有抽取提案测试和 pending 分组测试保持绿。
- [ ] 全量 pytest + ruff 绿；不 bump 版本。

## 完成总结（DONE 时填写）

（待 DONE 时填写）
