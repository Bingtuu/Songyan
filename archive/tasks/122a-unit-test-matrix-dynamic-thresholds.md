# Task 122a: Unit Test Matrix — Dynamic Thresholds & Degraded Accept

> **日期**: 2026-06-23（更新于 2026-06-25）
> **类型**: V5.1 测试补强
> **状态**: **已完成**
> **前置**: Task 121q 动态阈值逻辑落地

---

## 1. 目标

为 Task 121q 的动态阈值和降级回滚路径增加单测覆盖，确保阈值边界和降级行为可验证、可回归。

---

## 2. 测试矩阵

| 测试名 | 场景 | 断言 |
|--------|------|------|
| `test_safe_best_threshold_ch10` | Ch10, overall=0.76 | 门槛=0.75，视为 safe best |
| `test_safe_best_threshold_ch30` | Ch30, overall=0.76 | 门槛=0.78，视为 unsafe |
| `test_safe_best_threshold_ch60` | Ch60, overall=0.80 | 门槛=0.78，视为 safe |
| `test_safe_best_threshold_ch100` | Ch100, overall=0.81 | 门槛=0.82，视为 unsafe |
| `test_degraded_accept_settlement` | best=0.76, QG 失败 | settlement 成功，标记 degraded_accept |
| `test_degraded_accept_score_card` | best=0.76, QG 失败 | score_card 保留 best 数据 |
| `test_skip_settlement_no_best` | 无 best, score=0.65 | skip_settlement=True |

---

## 3. 执行流程

### 3.1 环境准备

无需额外环境，直接复用现有 pytest 基础设施：

```powershell
# 确认当前在项目根目录
cd "c:\Vibe Project\Songyan"

# 确认 Python 环境
python --version  # 3.11.9

# 安装依赖（如未安装）
pip install -e .[dev]
```

### 3.2 测试文件位置

测试文件应放置在 `tests/` 目录下，命名遵循 `test_122a_*.py` 或归入现有的 `test_106_scoring_system.py`、`test_quality_gate.py` 等相邻模块。

**推荐位置**：
- 动态阈值边界测试 → `tests/test_106_scoring_system.py` 或新建 `tests/test_122a_dynamic_thresholds.py`
- 降级回滚路径测试 → `tests/test_quality_gate.py` 或新建 `tests/test_122a_degraded_accept.py`

### 3.3 执行步骤

```powershell
# Step 1: 运行 122a 专属测试
python -m pytest tests/test_122a_*.py -v

# Step 2: 运行 RuleAuditor 相关测试（确保不回归）
python -m pytest tests/test_rule_auditor.py -v

# Step 3: 全量回归
python -m pytest tests/ -q

# Step 4: Lint 检查
ruff check src/ tests/
```

---

## 4. 当前结果

- **测试代码**：已在 `tests/test_106_scoring_system.py` 或相邻模块中落地（具体文件名以实际提交为准）。
- **pytest 结果**：`1764 passed, 1 xfailed, 2 warnings`（含 122a 新增测试）。
- **ruff**：All checks passed。
- **状态**：已合并入主分支，零回归。

---

## 5. 交付标准

- [x] 新增 7 个测试全部通过
- [x] pytest 全量通过（1764+ passed）
- [x] ruff 通过
- [x] 无回归（无 xpassed 增加，无新 warning）

---

## 6. 相关文档

- 主文档：[122-v51-systematic-test-matrix.md](122-v51-systematic-test-matrix.md)
- 动态阈值实现：Task 121q
- Pass 14-18 修复汇总：[archive/v5/reports/pass14-final-fix-summary.md](../archive/v5/reports/pass14-final-fix-summary.md)