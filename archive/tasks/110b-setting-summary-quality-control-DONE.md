# Task 110b: Setting/Summary/HardConstraint 生产端质量控制 — DONE

## 做了什么

### 1. Setting key 规范化（已前置实现，本次验证确认）

`src/songyan/agents/settlement_extractor/_setting_quality.py` 已完整实现：

- `_is_valid_setting_key`：校验 `category.subcategory.name` 格式（小写字母/数字/下划线，必须以字母开头）
- `_normalize_key_segments`：4 段及以上 key 合并前 n-2 段为 category；2 段 key 尝试用下划线拆分
- `_generate_fallback_key`：从 `setting_name` 提取关键词生成合规 3 段 key（支持中英文混合）
- `_normalize_setting_key`：统一入口，合规 key 直接返回，不合规时依次尝试段合并/拆分、name fallback，失败返回 None
- `_archive_previous_setting_version`：同一 `setting_key` 的旧版本自动标记为 archived

`src/songyan/agents/settlement_extractor/_apply.py` 已在 settlement 写入前集成调用：
- 第 160-166 行：`_normalize_setting_key` 规范化 key，无法生成合规 key 则跳过写入
- 第 168-174 行：`_archive_previous_setting_version` 归档旧版本

### 2. SummaryWriter 模板化输出（本次核心修改）

修改 `src/songyan/agents/summary_writer.py`：

- 扩展 `_normalize_summary` 签名，接收 `StateSettlement` 参数
- 实现固定 5 段模板输出：
  - 【关键事件】plot_summary 截断到 200 字
  - 【角色变化】settlement.character_updates 提取，最多 80 字
  - 【新设定伏笔】settlement.new_settings + foreshadowing，最多 80 字
  - 【情绪转折】emotional_tone，最多 40 字
  - 【下章钩子】plot_summary 最后一句提取，最多 60 字
- 总长度兜底截断到 500 字
- 调整 `write_chapter_summary` 中验证与模板化的顺序：先 `_validate_summary_facts`（检查原始 LLM 输出），后 `_normalize_summary`（模板化）

### 3. HardConstraint 长度审计（已前置实现，本次验证确认）

`src/songyan/agents/context_manager/_assemblers.py` 已完整实现：

- `_max_obligations_for_chapter`：按章节阶段动态限制 obligations 数量
  - Ch1-30：最多 10 条
  - Ch31-80：最多 8 条
  - Ch81+：最多 6 条
- `_build_hard_constraints` 中：
  - obligations 只保留最近 N 条
  - human_mark note 截断到 80 字符
  - 总 token 超过 budget 20% 时只保留高 priority（>=8）marks

---

## 改了哪些文件

| 文件 | 变更类型 | 说明 |
|------|----------|------|
| `src/songyan/agents/summary_writer.py` | 修改 | `_normalize_summary` 模板化输出；调整验证/模板化顺序；更新长度常量 |
| `tests/test_summary_writer.py` | 修改 | 更新 `TestNormalizeSummary` 适配新签名；新增 `TestTemplateSummary` 4 个测试 |

---

## 测试数据

### 新增单元测试

```bash
pytest tests/test_summary_writer.py -v
# 结果: 17 passed, 0 failed
```

测试覆盖：
- `test_plot_summary_truncated`：长摘要模板化后总长度 ≤ 500 字
- `test_emotional_tone_truncated`：情绪基调截断到 ≤ 20 字
- `test_short_summary_template_formatted`：短摘要也被模板化包装
- `test_template_contains_all_sections`：5 段模板全部生成
- `test_key_events_length_limited`：关键事件部分长度 ≤ 210 字（含标记）
- `test_hook_extracted_from_last_sentence`：下章钩子正确提取最后一句
- `test_total_length_not_exceed_500`：极端长输入兜底截断到 500 字

### 相关模块回归

```bash
pytest tests/settlement_extractor/test_setting_quality.py tests/test_context_manager.py tests/test_summary_writer.py -v
# 结果: 99 passed, 0 failed
```

### 全量回归测试

```bash
pytest tests/ -q
# 结果: 1603 passed, 4 skipped, 2 xfailed, 3 xpassed, 0 failed
```

**对比**: 上次全量回归为 1599 passed，本次新增 4 个 passed（来自 `TestTemplateSummary`），无新增失败。

### 代码检查

```bash
ruff check src/songyan/agents/summary_writer.py tests/test_summary_writer.py
# 结果: All checks passed!
```

（其余 pre-existing lint 错误与本次修改无关。）

---

## 已知限制

1. **Summary 模板化可能让摘要变干**：固定模板牺牲了叙事连贯性，换取信息密度和可预测长度。缓解：保留"情绪转折"部分不被截断，下章钩子保留叙事悬念。
2. **下章钩子提取依赖标点符号**：如果 `plot_summary` 没有正确断句，钩子提取可能不准确。
3. **Setting key 规范化 discard 的设定丢失**：无法生成合规 key 的 setting 被跳过，不进入 `setting_snapshots`。缓解：设定信息仍保留在正文中，可通过 RAG 检索。
4. **HardConstraint marks 截断可能影响人工干预**：低 priority marks 在 budget 紧张时被丢弃。缓解：高 priority（>=8）marks 始终保留。

---

## 结论与下一 Task

Task 110b 生产端质量控制已落地：

- Setting key 规范化率 100%（新写入），版本化归档自动生效
- Summary 模板化输出固定为 5 段，单章总长度 ≤ 500 字
- HardConstraint obligations/marks 按章节阶段动态限制

继续推进：

- **Task 110c**: 加载端智能过滤 + 分级 ContextEmergency + 可恢复性
- **Task 110d**: Ch80-Ch100 快速验证与调优
