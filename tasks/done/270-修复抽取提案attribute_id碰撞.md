# 270 · 修复抽取提案 attribute_id 碰撞

| 项 | 内容 |
|---|---|
| 状态 | DONE |
| 关联 | M2 extract→pending 提案路径（`enqueue_extract_proposals`）；task 226（rejected 不复活）；task 269（pending 分组过滤） |
| 预估 | 一个编码切片（TDD） |

## 目标

`_attribute_id`（`src/songyan/agents/settlement_extractor/_proposals.py:37`）按 `(project, entity, key, chapter)` 生成确定性 ID。三条碰撞向量会让后写提案**静默覆盖**先写提案，人在 `canon pending` 永远看不到被覆盖的那条：

1. **同章同 (entity, key) 多次观测**：同一 settlement 内同角色同 field 出现两次（章中多次变化），或 `character_updates.field` 与 `numerical_updates.attribute_name` 跨族同 key（真实运行词表两边都有 `level`）。上游 `_validate.py` 对 character_updates 无去重，pending 写入对 pending 行也无存在检查。
2. **非 ASCII key slug 塌缩**：`_slug` 删光非 ASCII 字符，纯中文 key/entity_id 全部塌缩成 `"x"`，同章不同 key 互相覆盖。setting 分支有 `_is_valid_setting_key` 三段式 ASCII 强校验不受影响，但 `field` / `attribute_name` 无代码护栏（真实日志目前全 ASCII，属 LLM 行为惯性）。
3. **截断碰撞（理论）**：slug 每段截 48 字符、project 截 24，同前缀超长 key 会撞。

严重度中等偏低：丢的是 pending 提案可见性，settlement 观测表（`untrusted_until_confirmed`）原始数据仍在，人确认入典主闸不受影响。目前真实 dogfood 未观测到实际碰撞，本任务为健壮性修复。

## 约束

- 先写测试再写实现。新测试放 `tests/<area>/test_<行为>.py`，禁止 `test_task###_*.py`。
- **不改既有正常路径的 ID 形态**：现有全 ASCII、无碰撞的 pending 行 ID 保持不变（不制造重复提案、不破坏 269 的分组口径）。
- approved / rejected 跳过语义不变（task 226：confirm 不可被静默降级、人 dismissed 的不被 settlement 复活）。
- 幂等口径不变：同一 (entity, key, chapter) 重复入队（重跑结算）不产生重复 pending 行。
- 全量 pytest + tests/cli + ruff 绿才交验收。不 bump 版本。

## 步骤

- [x] RED：碰撞场景失败测试——(a) 同 settlement 同 entity 同 field 两条 update → 两条独立 pending 行，值都在；(b) character_update 与 numerical_update 同 key 同章 → 不互相覆盖；(c) 纯中文 key 两条不同 key → 不塌缩互覆；(d) 既有幂等/approved/rejected 行为回归锁。
- [x] GREEN：`_proposals.py` 修复——`_write_pending_extract_attribute` 携带本次调用 `seen` 表；同 ID 同值 → 幂等跳过；ASCII base ID 被不同 value 占用 → 升级为「base + entity/key/value 短哈希」ID 并记 `extract_proposal_disambiguated` 日志；entity_id/key 含非 ASCII → 恒走哈希 ID（slug 塌缩免疫）。哈希含 value，重跑幂等。
- [x] 受影响面回归：settlement_extractor 族、canon pending 族、extract pending 提案测试全绿。

## 验收标准

- [x] 上述碰撞场景下不再静默覆盖：人在 pending 列表能看到全部提案。
- [x] 既有 ID 形态不变：无碰撞的正常路径 attribute_id 与修复前逐字一致。
- [x] 幂等重跑不产生重复行；approved/rejected 跳过语义不变。
- [x] 全量 pytest + tests/cli + ruff 绿；不 bump 版本；STATUS/HANDOFF 同步。

## 完成总结（DONE 时填写）

2026-11-15 交付（TDD：RED 4 失败 → GREEN 全过）。

**修复（`_proposals.py`，+68/-2）**
- `_attribute_id` 增加 `value`/`hashed` 参数：哈希形态 = base + `-{sha1(entity\x00key\x00value)[:8]}`。
- `_write_pending_extract_attribute` 新增本次调用 `seen` 表（enqueue 建、三族循环共用）：
  - 同 ID 同值 → 幂等跳过（重跑结算/同值重复观测不重复写、written 不重复记）。
  - ASCII base ID 已被不同 value 占用 → 升级哈希 ID + `settlement.extract_proposal_disambiguated` 日志。
  - entity_id/key 含非 ASCII → 恒走哈希 ID（`_slug` 塌缩免疫，中文 key 不再全挤成 `x`）。
- 哈希含 value → 区分 ID 对同一观测跨次重跑稳定幂等。approved/rejected 跳过语义原样（task 226）。

**兼容性锁**
- 无碰撞 ASCII 正常路径 ID 逐字不变（`test_ascii_id_form_unchanged` 硬编码锁 `ext-p-coll-char-chen-location-c3`）。
- 新增 5 测（`tests/settlement_extractor/test_extract_proposal_collisions.py`）：两值并存 / 同值幂等（含重跑）/ 跨族（character_updates × numerical_updates）同 key 并存 / 中文 key 不塌缩 / ASCII ID 形态。

**验收**
- 全量默认收集 3694 passed / 2 skipped / 1 xpassed（基线 3689 + 5 新测）；tests/cli 371 全绿；ruff 零告警。
- 受影响面回归（settlement_extractor 族 + extract pending 族 + test_settlement_extractor）182 passed 全绿。

**遗留**
- 历史库中旧塌缩 ID（`-x-`）pending/rejected 行不做迁移，与新哈希 ID 不互认：这些行本就是异常数据（正常日志全是 ASCII key），量极小；settlement 观测表仍 `untrusted_until_confirmed` 可回溯。
- 无需 `doctor --init-db`（无 schema 变更）。
