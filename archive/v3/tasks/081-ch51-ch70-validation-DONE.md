# Task 081: Ch51-Ch70 验证 — 交接报告

> **状态**: ✅ 已完成（19/20 章，Ch51 缺失）  
> **完成日期**: 2026-06-07  
> **总耗时**: ~2.5 小时真实 LLM 运行 + 分析

---

## 做了什么

### 1. 运行 Ch52-Ch70 真实 LLM 验证

- 基于 Ch41-Ch50 验证数据库复制启动
- `auto_confirm=True`，无人工干预
- 运行 19 章（Ch51 因旧脚本崩溃缺失）
- 每章平均耗时 ~5-6 分钟

### 2. 修复验证中发现的两个 bug

**a. Writer 截断过度** (`src/songyan/agents/writer.py`)
- 阈值 1.3x → 1.5x
- 增加截断后字数下界保护 target × 0.70
- 修复兜底逻辑缺失 `_wc <= _upper` 检查

**b. GoalPlanner target_events 类型错误** (`src/songyan/agents/goal_planner.py`)
- LLM 偶尔输出 dict 而非 string
- 新增 `_clean_str_list()` 自动转换 dict → description 字段

### 3. 生成验证报告

- 报告: `docs/reports/v3.1_ch51_ch70_validation_report.md`
- 数据库: `evals/output/validation_ch51_70/test.db`
- 日志: `evals/output/validation_ch51_70/run.log`

---

## 验证结果

| 指标 | 目标 | 实际 | 达标 |
|------|------|------|:----:|
| 流程跑通率 | 100% | 100% (19/19) | ✅ |
| budget_used max | ≤1.5 | 2.32 (Ch70) | ❌ |
| 字数在 target±20% | 100% | 42% (8/19) | ❌ |
| 连续性健康分平均 | ≥5.0 | 2.0 | ❌ |

---

## 关键发现

1. **Phase A+B 修复有效但边际收益递减**
   - Ch52-Ch59 budget_used 0.88-1.31（显著优于 Ch50 的 2.0）
   - Ch60 后再次恶化，Ch70 达到 2.32

2. **字数控制仍不达标**
   - 平均字数 4062（目标 3200，+27%）
   - 仅 42% 章节在 ±20% 范围内
   - 截断阈值 1.5x 太宽，Revision 阶段增加字数

3. **上下文膨胀根本趋势未变**
   - setting_snapshots、foreshadowings、human_marks 持续增长
   - BudgetPruner 硬断言无法阻止"静态基线"上升

---

## 修改文件清单

| 文件 | 变更 |
|------|------|
| `src/songyan/agents/writer.py` | 截断阈值 1.5x + 下界保护 0.70x |
| `src/songyan/agents/goal_planner.py` | target_events/hooks/obligations 类型清洗 |
| `tests/test_076_word_count_truncation.py` | 测试数据匹配新阈值 |
| `docs/reports/v3.1_ch51_ch70_validation_report.md` | 新增验证报告 |
| `docs/STATUS.md` | 更新 Task 081 状态 |

---

## 已知限制

- Ch51 缺失（旧脚本崩溃，补跑任务超时）
- Ch57 第一次运行失败（goal_planner 类型错误），修复后成功
- 验证过程中出现多次后台任务竞争，已清理

---

## 下一步

- **Task 082**: Ch71-Ch100 验证（建议先完成上下文架构改造，否则 Ch70 后 budget_used 将 >2.5）
- **中期改造**: setting_snapshots 生命周期管理、human_marks 强制回收、动态预算提升
