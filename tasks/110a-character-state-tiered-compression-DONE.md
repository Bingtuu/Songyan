# Task 110a: CharacterState 分层保真压缩 — DONE

## 做了什么

### 1. 生产端 CharacterState 分层保真压缩

新增 `src/songyan/agents/settlement_extractor/_state_compression.py`：

- 按角色层级设置差异化压缩上限：
  - `protagonist`: 400 字符
  - `antagonist`: 300 字符
  - `supporting`: 150 字符
  - `functional`: 60 字符
- 字段级压缩规则：
  - `location` 不压缩
  - `mental_state` / `physical_state` / `infection_stage` 等长文本字段提取关键分句
  - 过滤无信息分句，保留触发事件、状态变化、影响
- `functional` 角色极简压缩：仅保留位置 + 关键状态
- Fallback：规则压缩后仍超长时截断到上限

在 `src/songyan/agents/settlement_extractor/_apply.py` 中集成：

- `apply_settlement` 写入 `character_states` 前调用 `_compress_character_updates`
- 读取项目角色列表获取 `role_type`
- 对每条 `CharacterUpdate.new_value` 应用分层压缩
- 保持 `CharacterUpdate` 其他字段不变

### 2. 修复流式验证报告生成 bug

修复 `scripts/run_task_105b_ch51_ch100.py`：

- 原因：逐章运行会为每章创建独立 `run_id`，但原 `_generate_report` 只读取最后一个 `run_id` 的 JSONL，导致报告只统计最后一章
- 修复：
  - `main()` 收集所有章节的 `run_id` 列表
  - `_generate_report` 遍历所有 `run_id` 的 JSONL 并去重章节
  - 报告仍以最后一个 `run_id` 命名，保持与日志文件名一致

## 改了哪些文件

| 文件 | 变更类型 | 说明 |
|------|----------|------|
| `src/songyan/agents/settlement_extractor/_state_compression.py` | 新增 | 分层保真压缩核心逻辑 |
| `src/songyan/agents/settlement_extractor/_apply.py` | 修改 | 在写入 `character_states` 前调用压缩 |
| `tests/settlement_extractor/test_state_compression.py` | 新增 | 7 个压缩规则单元测试 |
| `scripts/run_task_105b_ch51_ch100.py` | 修改 | 修复报告只统计最后一章的 bug |

## 测试数据

### 单元测试

```bash
pytest tests/settlement_extractor/test_state_compression.py -v
# 结果: 7 passed, 0 failed
```

测试覆盖：
- 短值不压缩
- `location` 字段不压缩
- `protagonist` `mental_state` 压缩到上限内
- `supporting` 结构化压缩
- `functional` 极简压缩
- `physical_state` 关键信息保留
- Fallback 截断

```bash
pytest tests/test_105_streaming_validation.py tests/test_run_logger.py tests/models/test_project_run.py -v
# 结果: 48 passed, 0 failed
```

### 全量回归测试

```bash
pytest tests/ -q
# 结果: 1562 passed, 4 skipped, 2 xfailed, 3 xpassed, 0 failed
```

**对比**: Task 109 完成时为 1547 passed，本次新增 15 个测试（7 个 state_compression + 部分既有新增），无新增失败。xfailed/xpassed 数量有轻微波动（1→2 / 4→3），与本次修改无关。

### 代码检查

```bash
ruff check scripts/run_task_105b_ch51_ch100.py
# 结果: All checks passed!
```

## Ch80-Ch100 验证结果

| 指标 | Task 105b 基线 (Ch51-Ch100) | Task 110a (Ch80-Ch100) | 变化 |
|------|---------------------------|------------------------|------|
| 章节数 | 50 | 21 | — |
| 成功 | 50/50 (100%) | 21/21 (100%) | — |
| QG 通过率 | 58.0% (29/50) | 57.1% (12/21) | 基本持平 |
| ContextEmergency | 41/50 (82.0%) | 17/21 (81.0%) | 基本持平 |
| 平均 budget_used | 0.517 | 0.493 | -4.6% |
| 平均 revision_rounds | — | 0.5 | — |
| 平均字数 | — | 3661 | — |
| 总耗时 | — | 51.8 min | — |

压缩生效示例（Ch100）：

| field | original_length | compressed_length | role |
|-------|-----------------|-------------------|------|
| mental_state | 531 | 400 | protagonist |
| physical_state | 871 | 400 | protagonist |
| infection_stage | 570 | 80 | protagonist |

## 已知限制

1. **ContextEmergency 未显著下降**：Ch80-Ch100 的 emergency 比例（81.0%）与 105b 基线（82.0%）基本持平，未达成规划中的 ≥30% 下降目标。说明 `character_states` 不是当前 context 膨胀的主因，setting/foreshadowing/summary 等其他信息池仍需压缩。
2. **Protagonist 压缩上限仍较高**：400 字符约 200-300 tokens，对 16K writer budget 仍有影响。后续可考虑 protagonist 也做结构化摘要。
3. **压缩基于规则而非语义**：当前按关键词和分句规则提取，可能漏掉非触发/影响型的重要心理状态转折。
4. **未 retroactive 压缩历史状态**：只影响 110a 之后生成的新状态，旧项目状态保持不变。
5. **报告脚本在完成后偶发卡住**：本次验证完成后进程已退出但后台任务状态未同步更新，已手动停止。不影响实际数据。

## 结论与下一 Task

Task 110a 生产端压缩逻辑已落地并生效，但单一维度压缩不足以显著改善 ContextEmergency。按规划继续推进：

- **Task 110b**: Setting key 规范化、Summary 模板化、HardConstraint 长度审计
- **Task 110c**: 加载端智能过滤 + 分级 ContextEmergency
- **Task 110d**: Ch80-Ch100 快速验证与调优
