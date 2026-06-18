# Task 110d: Ch80-Ch100 快速验证与参数调优 — DONE

> **完成日期**: 2026-06-17
> **状态**: 部分达标 — ContextEmergency 问题解决，QG 通过率未达目标

---

## 1. 做了什么

### 1.1 流式验证（两轮实跑）

- **第一轮（基线参数）**: Ch80-Ch96 逐章流式验证，复用 `proj-e74ef1e4`，保留 Ch1-Ch79 已接受版本
- **第二轮（调参验证）**: Ch89-Ch100 重跑，验证参数调整效果
- ** runner 脚本**: `scripts/run_task_105b_ch51_ch100.py --start 80 --end 100 --no-resume`

### 1.2 参数调优与回滚

根据第一轮数据分析，识别到 coherence_major 是主要失败模式，尝试了两项调整：

| 参数 | 调整方向 | 预期效果 | 实际效果 | 最终状态 |
|------|---------|---------|---------|---------|
| `_build_recent_plot` 截断长度 | chapter 120→150, arc 280→320 | 改善近期剧情完整性，减少 coherence_major | 局部改善（Ch89、Ch90 PASS），但整体恶化（Ch92、Ch94、Ch96 FAIL） | **已回滚** |
| `continuity_health_threshold` | 7.0→5.0 | 减少 settlement 跳过，打断连锁反应 | 未显著改善整体通过率 | **已回滚** |

回滚依据：调参后 Ch89-Ch100 通过率仅 25%（3/12），低于基线的 41.7%（5/12），方向错误。

---

## 2. 改了哪些文件

| 文件 | 变更 | 状态 |
|------|------|------|
| `src/songyan/agents/context_manager/_assemblers.py` | 摘要截断长度调整（150/320/220）→ 回滚 | 无变更 |
| `scripts/run_task_105b_ch51_ch100.py` | `continuity_health_threshold` 5.0 → 回滚 7.0 | 无变更 |
| `tests/test_load_layered_summaries.py` | 测试断言同步调整 → 回滚 | 无变更 |
| `tasks/110d-ch80-ch100-validation-and-tuning-DONE.md` | 本文件 | 新增 |

---

## 3. 测试数据

### 3.1 回归测试

```bash
pytest tests/ -q --ignore=tests/test_layered_context.py
```

结果: **1588 passed, 4 skipped, 2 xfailed, 3 xpassed, 11 warnings**

注：`test_layered_context.py` 存在 pre-existing 导入错误（`_calculate_dynamic_relevance` 未从 `__init__.py` 导出），已忽略。

### 3.2 代码检查

```bash
ruff check src/ tests/
```

无新增 lint 错误。

---

## 4. 验证结果

### 4.1 最终有效数据（第一轮，基线参数，Ch80-Ch96）

| 指标 | 数值 | Task 110a 基线 | 目标 | 是否达标 |
|------|------|---------------|------|---------|
| QG 通过率 | **10/17 = 58.8%** | 57.1% (12/21) | ≥80% | ❌ |
| ContextEmergency 次数 | **0/17 = 0.0%** | 81.0% (17/21) | ≤10/21 | ✅ |
| 平均 budget_used | **0.945** | ~0.95 | ≤0.70 | ❌ |
| 最大连续失败 | **3 章** (Ch89-Ch91) | 3 章 | 无连续 3 章 | ❌ |
| 平均 revision 轮数 | **0.41** | — | — | — |
| 失败原因"上下文过载"占比 | **0%** | — | ≤30% | ✅ |

### 4.2 失败模式分析

**所有 QG 失败均为 `coherence_major`**（7/7 失败章节），无 length/readability/momentum 主导失败。

失败章节明细：
- Ch80: coherence_major | budget=0.913
- Ch82: coherence_major | budget=0.929
- Ch89: coherence_major | budget=0.964
- Ch90: coherence_major | budget=0.972
- Ch91: coherence_major + readability_fail | budget=0.930
- Ch93: coherence_major | budget=0.973
- Ch95: coherence_major | budget=0.993

**关键发现**：
1. `character_states_loaded=1` 在所有章节均为 1，是系统性问题
2. `budget_used` 与 QG 通过无显著线性关系（通过的章节 budget 0.894-0.988，失败的章节 budget 0.913-0.993）
3. `skip_settlement` 在失败章节高度相关（6/7 失败章节 settlement 被跳过）

---

## 5. 结论与建议

### 5.1 Task 110d 成果

- **ContextEmergency 从 81% 降至 0%**：Task 110a-110c 的加载端优化（智能过滤、分级裁剪、分区预算制）非常成功，上下文过载问题已基本解决。
- **QG 通过率未改善**：58.8% vs 57.1%，基本持平。失败模式 100% 为 coherence_major，与上下文数量无关。

### 5.2 根因判断

Ch80-Ch100 的 coherence_major 失败不是上下文加载问题，而是：
1. **角色信息严重不足**：`character_states_loaded=1` 意味着 Writer 几乎只获得主角档案，多角色互动场景缺乏足够的状态支撑
2. **连锁反应**：`skip_settlement` 导致后续章节连贯性受损，形成恶性循环
3. **Writer/Auditor 层面**：coherence_major 的判定标准在 Ch80+ 压力区过于严格，或 Writer 的生成质量在该区间自然下降

### 5.3 对后续验证任务的建议

- **接受 Ch80-Ch100 的自然损耗**：该区间是上下文压力极限区，57-59% 的 QG 通过率可能是当前架构下的局部最优
- **不继续调优加载端参数**：ContextEmergency 已为 0%，进一步放宽只会增加 budget_used，不会改善 coherence_major
- **Task 112 重点**：在 Task 111a-111c 前置一致性修复后，验证 Ch101-Ch150 是否能维持相似通过率，并确认 budget_used 不重新触发 Emergency
- **如需提升 QG 通过率**：需要 Writer 层面的改进（如增强角色连贯性 Prompt）或 Auditor 层面的阈值调整，超出 Task 110d 范围

---

## 6. 已知限制

1. **样本量有限**：Ch80-Ch96 仅 17 章（目标 21 章）， runner 因连续 3 章失败熔断未能完成 Ch97-Ch100
2. **参数调优无正收益**：已验证的两项参数调整均未改善整体通过率
3. **character_states_loaded=1 的系统性问题未解决**：需要更深层级的角色加载策略调整，超出本次 Task 范围
