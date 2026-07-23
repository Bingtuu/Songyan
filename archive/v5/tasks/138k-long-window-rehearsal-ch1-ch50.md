# Task 138k: 长窗口 Rehearsal Ch1-Ch50/100

> **类型**: 实跑验证 / 稳定性测试
> **状态**: 已完成（Ch1-Ch30；暴露长窗口 health 下滑，需 Task 138m 进一步决策）
> **前置**: Task 138h-138j 已完成，critical orphan 强制回收闭环建立，138j `recycle_hint` 显著有效（P1 5→2，health 3.0→3.9）
>
> **边界**: 不改代码，只跑实跑；若发现新缺陷，另起 task 修复

## 背景

Task 138h-138j 通过"注入 + 检测 + 回收提示"三层机制，将 Ch12 的 critical orphan 从 5 压缩到 2，health 从 3.0 提升到 3.9。但这些数据仅来自 Ch10-Ch12 的短窗口复跑（~15 分钟/章）。

根据 AGENTS.md 的 V5.0 目标，下一阶段优先级是：
1. **补 Ch1-Ch150 single-run rehearsal 证据**
2. 进入 V5.1 Prompt 调优（已在 138h-138j 中部分完成）
3. 后置预研 ContextEmergency / health_low 硬门禁

本任务的核心目标是：**验证 138h-138j 的改进在更长章节窗口（Ch1-Ch50 或 Ch1-Ch100）中是否稳定**，并补全 single-run 证据。

## 目标

1. **稳定性验证**：连续 50 章 single-run（不人工干预）无 halt，观察 critical orphan、health、settlement 通过率、QG 通过率的趋势。
2. **趋势分析**：记录每 10 章的 continuity 快照，绘制 health/orphaned/P1/P2/P3 趋势线，判断 138j 的改善是"一次性修复"还是"持续有效"。
3. **瓶颈识别**：如果 health 在 Ch30+ 再次下降到 <3.0，或 critical orphan 重新累积到 >3，记录具体根因（是新的 setting 未回收，还是已有 setting 的 recycle_hint 失效）。
4. **证据补全**：生成 `archive/v5/reports/task-138k-long-window-rehearsal-report.md`，作为 V5.1 收口的关键证据之一。

## 不做的事

- **不改代码**：本任务只做实跑和观察，不修改任何业务逻辑。若发现新缺陷，另起 task（如 138l/138m）修复。
- **不调整阈值**：`ORPHANED_THRESHOLDS` 和 `health` 计算公式保持当前值。
- **不引入新 Agent/Workflow**：保持现有架构不变。
- **不做 Ch150+**：Ch1-Ch100 已足够验证趋势，Ch100-Ch150 可后续补充。

## 要做的事

### 1. 准备干净的数据库副本

从主库 `songyan.db` 复制一个新的副本 DB：
```powershell
Copy-Item "songyan.db" ".tmp/task138k_ch1_ch50_rehearsal_20260629.db"
```

确认主库状态：Ch1-Ch10 已 accepted（当前项目状态）。

### 2. 运行长窗口 rehearsal

使用 `scripts/run_137_ch10_focus_validation.py` 的扩展版本，或新建脚本 `scripts/run_138k_long_window_rehearsal.py`：

```python
# 核心逻辑：从 Ch1 开始，连续运行到 Ch50（或 Ch100）
# 使用 auto_confirm=True，不人工干预
# 每章记录：settlement、summary、QG、continuity 结果
# 每 10 章输出一次趋势摘要
```

**脚本要求**：
- 使用新的 `.tmp` 副本 DB
- `DATABASE_URL` 指向副本 DB
- Writer 使用 1.2.0 工艺卡（当前 manifest default_version）
- 记录每章的：duration、word_count、settlement_success、qg_passed、continuity_health、orphaned_count、P1/P2/P3 分布
- 若触发 halt（如 quality_gate_fail_streak、settlement_validation_failed），记录 halt 原因和章节号

### 3. 趋势分析

 rehearsal 完成后，分析数据：

| 观察维度 | 目标 | 风险阈值 |
|---------|------|---------|
| 连续运行章节数 | ≥50 章无 halt | <30 章即 halt |
| health 趋势 | 稳定在 3.5-5.0 | Ch30+ 持续 <3.0 |
| critical orphan (P1) | ≤2 且不再增长 | Ch30+ 重新 >3 |
| settlement 通过率 | ≥95% | <90% |
| QG 通过率 | ≥95% | <90% |
| 单章平均耗时 | ≤15 分钟 | >20 分钟 |

**关键判断**：
- 如果 health 稳定在 3.5+ 且 P1 ≤2，说明 138j 的改进是**持续有效**的，可以宣告 V5.1 Prompt 调优阶段基本收口。
- 如果 health 在 Ch30+ 重新下降到 <3.0，需要分析是"新 setting 未回收"还是"旧 setting 重新 orphan"，另起 task 修复。
- 如果频繁触发 halt（如 Ch20 内 halt ≥2 次），说明系统稳定性仍有缺陷，需要优先解决 halt 根因。

### 4. 报告生成

生成 `archive/v5/reports/task-138k-long-window-rehearsal-report.md`，包含：
- 运行配置（DB、run_id、章节范围、Writer 版本、gate_mode）
- 每章关键指标表格
- 每 10 章趋势图（用文字描述或 ASCII 图表）
- 异常章节分析（halt、settlement fail、qg fail）
- 结论与下一步建议

## 验收标准

### 实跑层

- 成功完成 Ch1-Ch50（或 Ch1-Ch100）single-run rehearsal，无残留进程中断。
- 记录每章的 settlement、summary、QG、continuity 结果。
- **最低出口**：连续 30 章无 halt，health 未跌破 3.0。
- **理想出口**：连续 50 章无 halt，health 稳定在 3.5+，P1 ≤2。

### 分析层

- 生成趋势分析报告，包含 health/orphaned/P1/P2/P3 趋势线。
- 识别出 health 下降的关键章节和根因。
- 给出是否进入 V5.2（ContextEmergency 预研）或继续 Prompt 调优的建议。

### 文档层

- 本文件更新实施记录和结论。
- `STATUS.md`、`V5-README.md`、`docs/INDEX.md` 同步更新。

## 技术细节备忘

- 长窗口 rehearsal 耗时预估：50 章 × 15 分钟/章 = ~12.5 小时。建议分批次运行（如 Ch1-Ch20、Ch21-Ch40、Ch41-Ch50），或 overnight 运行。
- 副本 DB 大小会快速增长（每章新增 version、report、settlement 记录），建议监控磁盘空间。
- 若 rehearsal 过程中发现严重缺陷（如 Ch5 就 halt），可提前终止，分析根因后另起 task 修复，不必强行跑完 50 章。
- 与 Task 137 的关系：本任务的数据是 Task 137"Ch10 起点聚焦验证"收口判断的重要依据。

---

## 实施记录

- **2026-06-29**: 启动 Ch1-Ch30 快速窗口 rehearsal。
  - 脚本: `scripts/run_138k_long_window_rehearsal.py`
  - 副本 DB: `.tmp/task138k_ch1_ch30_rehearsal_20260629.db`
  - 源项目: `e95a1fa3`（克隆为新验证项目 `3bef1af8d54d4d0e887658516e1ed350`）
  - Writer 版本: `1.2.0`（临时切换，退出恢复）
  - Gate 模式: `observe`
  - 背景任务 ID: `bash-rre5r8z9`
  - 结果: **Ch1-Ch9 成功完成，Ch10 settlement validation 失败**（未触发 AutoHalt，run 状态 `partial`）。
    - Ch10 错误类型：`numerical_update` closing_value 与公式值不匹配。
    - 样例：`char_lin_shen.external_signal_pulse_width_ms closing_value (2.7) ≠ 公式值 (0.000)`。
    - 详细报告：`archive/v5/reports/task-138k-long-window-rehearsal-report.md`
    - 决策点：需先定位 Ch10 settlement 失败根因，或接受 Ch1-Ch9 作为部分证据。
- **2026-06-29**: 创建 Task 138l 修复 settlement 数值遥测误报；修复后继续使用同一副本 DB 跑 Ch10-Ch30。
  - 任务文档：`archive/v5/tasks/138l-settlement-telemetry-false-positive-fix-DONE.md`
  - 修复文件：`src/songyan/agents/settlement_extractor/_validate.py`
  - 回归测试：`tests/test_settlement_extractor.py`（4 个新增用例）
  - Continuation 命令：
    ```powershell
    $env:DATABASE_URL = "sqlite:///.tmp/task138k_ch1_ch30_rehearsal_20260629.db"
    $env:PROJECT_ID = "3bef1af8d54d4d0e887658516e1ed350"
    python scripts/run_138k_long_window_rehearsal.py
    ```
  - 背景任务 ID: `bash-9t1kkpng`（Ch13 处为跑全量 pytest 临时中断，manifest 已恢复为 1.1.0）
- **2026-06-29**: 全量 pytest 确认无回归后恢复 continuation。
  - 全量结果：`2007 passed, 1 xfailed, 2 warnings`
  - `ruff check src/ tests/` 通过
  - 新背景任务 ID: `bash-lpc56rtc`
- **2026-06-29**: Ch1-Ch30 rehearsal 全部完成。
  - 最终 Run ID: `run-6f2a10d3`
  - 完成章节: 30/30，无失败，无 AutoHalt
  - 总耗时: 4799.8s（约 80 分钟）
  - 关键趋势:
    - Ch9 health 7.1，P1=1
    - Ch15 health 3.0，P1=5
    - Ch30 health 3.0，P1=35
  - 结论: Task 138l 修复后 settlement 无阻断；但 138h-138j 改进在 Ch21+ 无法阻止 critical orphan 快速堆积。建议启动 Task 138m 深入分析 Ch21-Ch30 的 orphan 根因并决定下一阶段方案。
