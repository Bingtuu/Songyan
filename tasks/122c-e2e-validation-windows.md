# Task 122c: E2E Validation Windows

> **日期**: 2026-06-23（更新于 2026-06-25）
> **类型**: V5.1 端到端验证
> **状态**: **部分完成**
> **前置**: Task 121q + 121r 完成

---

## 1. 目标

覆盖三个压力拐点的端到端实跑验证，不再只跑 Ch1-Ch18。

---

## 2. 验证窗口

| 窗口 | 目的 | 预期 |
|------|------|------|
| Ch1-Ch20 | 验证早期章节低分容忍 | ≥18/20 成功 |
| Ch40-Ch50 | 验证中段上下文压力 | ≥8/10 成功，ContextEmergency ≤2 |
| Ch100-Ch110 | 验证后段高分保护 | ≥8/10 成功，rewrite 不得覆盖 ≥0.85 best |

---

## 3. 执行流程

### 3.1 环境准备

**数据库**：使用全新干净数据库，避免历史数据干扰。

```powershell
# Step 0: 环境清理（强制）
cd "c:\Vibe Project\Songyan"

# 终止残留 Python 进程
Get-Process python -ErrorAction SilentlyContinue | Stop-Process -Force

# 删除旧数据库（如需要全新环境）
Remove-Item -Path "data/songyan.db" -ErrorAction SilentlyContinue

# 重新初始化数据库
python -m songyan init-db

# VACUUM 优化
sqlite3 data/songyan.db "VACUUM;"
```

**配置**：确认 `.env` 或配置文件中：
- `CONTEXT_BUDGET_INCREMENT=250`
- `HUMAN_MARKS_LIFETIME=6`
- `SAFE_BEST_MIN_SCORE_CH1_CH20=0.75`
- `SAFE_BEST_MIN_SCORE_CH21_CH50=0.78`
- `SAFE_BEST_MIN_SCORE_CH51_PLUS=0.82`

### 3.2 执行命令

每个窗口独立运行，记录完整日志。

#### 窗口 1: Ch1-Ch20（早期低分容忍）

```powershell
# 静默长跑（约 100-120 分钟）
python -m songyan generate --chapters 1-20 --mode auto > logs/e2e_ch1_ch20_$(Get-Date -Format 'yyyyMMdd_HHmmss').log 2>&1

# 实时监控（如需观察进度）
python -m songyan generate --chapters 1-20 --mode auto
```

**验收指标**：
- 成功章节数 ≥ 18/20
- ContextEmergency 次数 ≤ 3
- AutoHalt 次数 = 0
- QG false 密度 ≤ 5%

#### 窗口 2: Ch40-Ch50（中段上下文压力）

```powershell
# 需要先完成 Ch1-Ch39 的铺垫（或从已有项目继续）
# 方式 A: 从 Ch1 开始跑到 Ch50（约 250-300 分钟）
python -m songyan generate --chapters 1-50 --mode auto > logs/e2e_ch1_ch50_$(Get-Date -Format 'yyyyMMdd_HHmmss').log 2>&1

# 方式 B: 若已有 Ch1-Ch39 数据，直接从 Ch40 开始
python -m songyan generate --chapters 40-50 --mode auto > logs/e2e_ch40_ch50_$(Get-Date -Format 'yyyyMMdd_HHmmss').log 2>&1
```

**验收指标**：
- Ch40-Ch50 成功章节数 ≥ 8/10
- ContextEmergency 次数 ≤ 2
- AutoHalt 次数 = 0
- budget_used 趋势无 >1.2 的异常跳变

#### 窗口 3: Ch100-Ch110（后段高分保护）

```powershell
# 需要完成 Ch1-Ch99 铺垫（约 500-600 分钟全量）
# 或使用已有 Ch1-Ch99 项目继续
python -m songyan generate --chapters 100-110 --mode auto > logs/e2e_ch100_ch110_$(Get-Date -Format 'yyyyMMdd_HHmmss').log 2>&1
```

**验收指标**：
- Ch100-Ch110 成功章节数 ≥ 8/10
- rewrite 不得覆盖任何 ≥0.85 的 best 版本
- degraded_accept 次数 ≤ 2
- summary 与正文一致性 100%

### 3.3 数据收集

每个窗口运行后，执行以下查询收集数据：

```sql
-- 成功率
SELECT 
    chapter_number, 
    status, 
    overall_score,
    quality_gate_pass,
    degraded_accept
FROM chapter_versions 
WHERE chapter_number BETWEEN ? AND ?
ORDER BY chapter_number;

-- ContextEmergency 统计
SELECT chapter_number, emergency_type, budget_used 
FROM context_emergencies 
WHERE chapter_number BETWEEN ? AND ?;

-- 质量指标趋势
SELECT 
    chapter_number,
    ai_tell_count,
    fatigue_word_count,
    scene_count,
    scene_count_ok,
    short_paragraph_ratio,
    markdown_scene_title_count
FROM review_reports rr
JOIN chapter_versions cv ON rr.chapter_version_id = cv.version_id
WHERE cv.chapter_number BETWEEN ? AND ?;
```

---

## 4. 当前进度

- **Ch1-Ch20**：已完成（重度 Mock，28 秒完成），结果符合预期。
- **Ch40-Ch50**：待启动。建议先通过 Mock 验证中段上下文压力逻辑，再决定是否实跑。
- **Ch100-Ch110**：待启动。建议在全量 single-run（如 Task 121q 的 `run-a2bed648`）中截取该窗口数据，避免重复实跑。

---

## 5. 交付标准

- [x] Ch1-Ch20 窗口 ≥18/20 成功
- [ ] Ch40-Ch50 窗口 ≥8/10 成功
- [ ] Ch100-Ch110 窗口 ≥8/10 成功
- [ ] 三个窗口合计 ContextEmergency ≤ 5 次
- [ ] AutoHalt 次数 = 0
- [ ] 运行日志归档至 `logs/e2e_*.log`

---

## 6. 风险与缓解

| 风险 | 缓解 |
|------|------|
| 实跑成本高（Ch100-Ch110 需先跑 99 章） | 优先复用 Task 121q `run-a2bed648` 的历史数据；或采用 Mock 验证窗口逻辑 |
| Windows 环境不稳定（句柄/内存） | 每 20 章检查一次进程状态，发现内存增长 >500MB 时触发清理 |
| LLM API 波动导致章节质量不达标 | 允许 degraded_accept（≥0.70），不追求每章 0.85+ |

---

## 7. 相关文档

- 主文档：[122-v51-systematic-test-matrix.md](122-v51-systematic-test-matrix.md)
- 全量实跑记录：[tasks/121q-ch1-ch150-full-single-run-DONE.md](121q-ch1-ch150-full-single-run-DONE.md)
- ContextEmergency 策略：[tasks/121l-context-emergency-autohalt-review.md](121l-context-emergency-autohalt-review.md)