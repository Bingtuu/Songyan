# Task 091-DONE: Phase B 收官验证（Ch21-Ch50 + Ch51-Ch70）

> **Phase**: V4.0 Phase B — 修复验证
> **优先级**: P0
> **执行日期**: 2026-06-09
> **总耗时**: ~6 小时（含监控）

---

## 实际完成内容

### 1. Ch2-Ch70 端到端验证

- 完成章节：**69 章（Ch2-Ch70）**
- 失败章节：**0**
- 总耗时：**346.1 分钟**
- LLM 调用：**910 次**
- 预估成本：~¥0.12

### 2. 核心验收结果

| 验收项 | 目标 | Ch21-Ch50 | Ch51-Ch70 | 判定 |
|--------|------|-----------|-----------|------|
| 字数达标率（±20%） | > 65% | **33.3%** | **60.0%** | ❌ |
| budget_used 平均 | < 1.4 | 1.203 | 1.127 | ✅ |
| budget_used 最大 | < 1.6 | **1.768** | **1.676** | ❌ |
| health_score 平均 | ≥ 3.0 | 1.2 | 2.0 | ❌ |
| token_budget 平均 | < 1.4 | 1.144 | 0.996 | ✅ |
| token_budget 最大 | < 1.6 | 1.246 | 1.104 | ✅ |

### 3. 关键发现

#### 字数控制（不达标）
- 整体达标率仅 **49.3%**（目标 > 65%）
- Ch21-Ch50 达标率 **33.3%**，Ch51-Ch70 回升到 **60.0%**
- Ch46 极端超标 **1.768x**（5659 字 / 3200 字）
- 超标（>1.2x）32 章，不足（<0.8x）3 章
- Writer 场景级生成是"自底向上"，结构固化后难以压缩
- RevisionHandler 结构保护阻止截断，rewrite fallback 代价高（4-5 版本、16-19 次 LLM 调用）

#### Context Budget（优秀）
- token_budget 平均 **1.073**，最大 **1.291**（均未超过 1.4）
- Ch51-Ch70 平均 **0.996**，Phase A Context-on-Demand **完全成功**
- ContextManager 的 pruning + RAG 检索有效控制上下文规模

#### Health Score（不达标）
- 平均 **2.0**，目标 ≥3.0
- orphaned settings 在 Ch60 达到 **317** 个
- 根因：ContinuityAuditor 将"一次性背景 setting"标记为 orphaned，评分公式对长篇小说不公平

#### 生命周期管理（有效）
- Ch70 总 settings：**427**（91 active + 60 dormant + 276 archived）
- Active 占比从 100% 降至 **19.8%**
- 归档率 **64.6%**，生命周期清理有效
- Active settings 稳定在 **90±5**，未线性增长

#### Revision 反弹回滚（成功）
- Ch59、Ch65、Ch70 三次触发 `revision_rebound_detected`
- 自动回滚机制有效阻止 revision 引入更多问题

#### Settlement 提取（退化）
- Ch62 出现重复 setting key 错误
- Ch70 出现 character_id 不匹配警告
- 随着 setting 总量增加，提取准确性下降

### 4. 可扩展性预判

| 指标 | Ch70 | Ch100 预判 | Ch300 预判 |
|------|------|-----------|-----------|
| Token budget | 1.073 ✅ | ~1.1 ✅ | **~1.5-2.0 ❌** |
| 字数达标率 | 49% ❌ | 同水平 ❌ | 同水平 ❌ |
| Health score | 2.0 ❌ | **<1.5 ❌** | **崩盘 ❌** |
| Active settings | 91 | ~100 | **~150+** |
| 生成稳定性 | 0 失败 | 0 失败 | **可能失败** |

**结论**：当前架构可支撑到 **100 章**，但无法支撑到 **300 章**；字数控制和 health_score 是独立修复赛道。

### 5. 输出文件

- `evals/output/task_091_scifi_webnovel/report.md` — 完整验证报告
- `evals/output/task_091_scifi_webnovel/lifecycle_report.md` — 生命周期趋势
- `evals/output/task_091_scifi_webnovel/lifecycle_trend.json` — 生命周期数据
- `evals/output/task_091_scifi_webnovel/llm_calls.jsonl` — LLM 调用日志
- `evals/output/task_091_scifi_webnovel/test.db` — 完整数据库（69 章）
- `evals/output/task_091_scifi_webnovel/progress.json` — 逐章指标

### 6. 下一步决策

**Task 091 核心验收项未通过**，按 V4.0 流程需要回退优化：

1. **Task 092**: Writer 字数预算分配 + 动态目标调整（P0）
2. **Task 093**: Health Score 公式修正 + Settlement 去重（P1）
3. **Task 094**: 场景结构保护（P2）
4. **Task 095-096**: Ch2-Ch50 / Ch51-Ch70 回归验证
5. **Task 097**: Ch71-Ch100 扩展验证

---

## 交接清单

- [x] Ch2-Ch70 端到端验证完成
- [x] 完整报告生成
- [x] 数据库可复现
- [x] 0 失败章节
- [x] 更新 docs/STATUS.md
- [x] 生成 tasks/091-phase-b-ch21-ch50-e2e-DONE.md
