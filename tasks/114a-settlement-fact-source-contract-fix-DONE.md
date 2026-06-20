# Task 114a DONE: Settlement 事实源契约修复

> **完成日期**: 2026-06-20
> **Phase**: V5.0 Phase 4 — Task 114 阶梯式执行第一步
> **结果**: ✅ 完成，Task 114b (Phase 1 重跑 Ch102-Ch110) 可启动

---

## 问题背景

V5.0 在 Ch103 结算阶段触发 validation 错误导致中断，根因分析确认两大核心契约缺陷：

1. **`old_value` mismatch**：`SettlementExtractor` 要求 LLM 精确复现 DB 中的长文本 `old_value`，但 LLM 输出了截断的局部值，导致 3 个字段（mental_state、physical_state、inventory）验证失败。

2. **`quote_filter` 内部 ID 误杀**：`CharacterUpdate` 使用内部 `character_id=char-ce09ac00` 作为正文关键词过滤条件，但中文正文中不会出现该 ID，导致合法引用被误过滤。

此外还发现两个潜在风险：
3. **run logger 判定逻辑脆弱**：`settlement_success` 仅依赖 `_settlement_needs_human_review` 单一标志位。
4. **后处理触发条件宽松**：RAG、SettingEvaporator、layered summary 可能通过历史 `version_type in ("accepted", "edited")` 旁路触发。

## 修复内容

### P0: `old_value` 代码回填逻辑

**文件**: `src/songyan/agents/settlement_extractor/_validate.py`

- 移除 `old_value` 严格相等校验，改为由代码从 DB 事实源自动回填。
- 当 `(character_id, field)` 在 DB 中有当前值时，无论 LLM 输出的 `old_value` 是什么，都用 DB 值覆盖。
- 对未知角色/字段（DB 中无对应状态）记录警告但不阻断。
- 新增日志 `settlement.old_value_backfilled` 记录回填操作，包含字符长度对比。

### P0: `quote_filter` 角色名替代内部 ID

**文件**: `src/songyan/agents/settlement_extractor/_quote_filter.py`

- 新增 `_build_character_name_map()` async 函数，通过 `character_id` 查询角色名。
- `filter_settlement_source_quotes()` 改为 async 函数，优先使用角色名做关键词校验。
- 角色名缺失时回退至仅做长度和存在性校验，防止误杀合法引用。
- 日志中新增 `character_name` 字段，便于排查。

**文件**: `src/songyan/agents/settlement_extractor/__init__.py`

- 调用 `filter_settlement_source_quotes()` 处添加 `await`。

### P1: run logger 判定逻辑加固

**文件**: `src/songyan/workflows/_run_logger.py`

- `settlement_success` 改为多维度判定，必须同时满足：
  1. 章节整体成功 (`success=True`)
  2. 不需要人工审核 (`_settlement_needs_human_review=False`)
  3. 没有跳过 settlement (`_skip_settlement=False`)
  4. 错误阶段不是 settlement 相关
  5. 有 `settlement_id`（证明 settlement 已成功应用）
- 新增 debug 日志 `run_logger.settlement_success_calculated` 记录各维度状态。

### P1: settlement 后处理触发条件收紧

**文件**: `src/songyan/workflows/_nodes.py`

- 移除三处后处理逻辑中的 `version.version_type in ("accepted", "edited")` 旁路条件。
- RAG 向量索引、SettingEvaporator、分层摘要生成都改为仅由 `accepted_for_postprocessing` 触发。
- 确保后处理只在本次 accept + settlement 事务成功后执行。

### Ch103 回归测试

**文件**: `tests/test_settlement_extractor.py`

- `test_ch103_old_value_backfill_from_db`：验证 LLM 输出截断值时，old_value 被自动回填为 DB 完整值。
- `test_ch103_old_value_backfill_multiple_fields`：验证多个字段同时回填。
- `test_ch103_old_value_backfill_with_warning`：验证未知角色/字段不阻断。
- 更新 `test_old_value_mismatch` 和 `test_validation_fails` 以匹配新行为。

**文件**: `tests/test_quote_filter.py`

- `test_ch103_quote_filter_uses_character_name_not_id`：验证使用角色名而非内部 ID 做关键词校验。
- `test_ch103_quote_filter_fallback_to_length_check`：验证角色名缺失时回退逻辑。
- `test_ch103_quote_filter_internal_id_still_filtered`：验证含内部 ID 的非法 quote 仍被过滤。
- 将 `TestFilterSettlementSourceQuotes` 类中所有测试改为 async。

## 改动文件

- `src/songyan/agents/settlement_extractor/_validate.py`
- `src/songyan/agents/settlement_extractor/_quote_filter.py`
- `src/songyan/agents/settlement_extractor/__init__.py`
- `src/songyan/workflows/_run_logger.py`
- `src/songyan/workflows/_nodes.py`
- `tests/test_settlement_extractor.py`
- `tests/test_quote_filter.py`
- `docs/STATUS.md`
- `tasks/114a-settlement-fact-source-contract-fix-DONE.md`

## 验证结果

### Ch103 回归测试

```bash
python -m pytest tests/test_settlement_extractor.py::TestValidateSettlement::test_ch103_old_value_backfill_from_db tests/test_settlement_extractor.py::TestValidateSettlement::test_ch103_old_value_backfill_multiple_fields tests/test_settlement_extractor.py::TestValidateSettlement::test_ch103_old_value_backfill_with_warning tests/test_quote_filter.py::TestFilterSettlementSourceQuotes::test_ch103_quote_filter_uses_character_name_not_id tests/test_quote_filter.py::TestFilterSettlementSourceQuotes::test_ch103_quote_filter_fallback_to_length_check tests/test_quote_filter.py::TestFilterSettlementSourceQuotes::test_ch103_quote_filter_internal_id_still_filtered -v
```

结果：**6 passed**

### 聚焦测试

```bash
python -m pytest tests/test_quote_filter.py tests/test_settlement_extractor.py tests/test_settlement_submodules.py -v
```

结果：**84 passed, 1 xfailed**

### 全量回归测试（Windows 防卡协议）

```bash
# PowerShell Job + 600s 硬超时
python -m pytest tests/ -q --tb=short
```

结果：**1665 passed, 4 skipped, 1 xfailed, 4 xpassed**（基线 1659，新增 6 个 Ch103 回归测试）

### 代码质量检查

```bash
ruff check src/songyan/agents/settlement_extractor/_validate.py src/songyan/agents/settlement_extractor/_quote_filter.py src/songyan/agents/settlement_extractor/__init__.py src/songyan/workflows/_run_logger.py src/songyan/workflows/_nodes.py tests/test_settlement_extractor.py tests/test_quote_filter.py
```

结果：**All checks passed!**

## 已知限制

- `filter_settlement_source_quotes()` 改为 async 函数后，所有调用方需添加 `await`。本次已修复主调用路径，如有其他外部调用需同步更新。
- 全量 ruff 检查仍有 116 个历史存量错误（E501、F841 等），均不在本次改动文件中，不影响本次修复质量。

## 下一步

进入 `archive/v5/plans/114-ch101-ch150-streaming-validation.md` 的 **Task 114b**：Phase 1 重跑 Ch102-Ch11
