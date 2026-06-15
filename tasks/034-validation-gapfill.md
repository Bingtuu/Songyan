# Task 034: 遗留验证补齐

> **Phase**: Stage A（还债与封锁解除）
> **优先级**: P0（阻塞后续 Phase 5/6）
> **依赖**: Task 032（DONE 报告）、Task 033（工程优化）
> **预计工作量**: 中大

---

## Goal

补上 Phase 1~4 中标记为"待运行"或空壳的验证项，使 Phase 5 有可靠的基准数据，消除"假高分"风险。

## Context

Phase 1~4 完成了大量代码开发，但多项验证被标记为"待后续补齐"：
- Punch Engine 自动评估脚本从未运行（刺激点密度 / 情绪转折量化）
- ContinuityAuditor 的 `state_mismatches` 返回空列表
- Arc/Volume 摘要为空壳（需要 LLM 或人工填充）
- 50 章模拟测试缺失（无法验证分层上下文的 budget_used 和保留率）

## In Scope

- [ ] **Punch Engine 自动评估**：
  - 运行刺激点密度量化脚本（punch_points 数 / 章节字数）
  - 运行情绪转折量化脚本（emotion_arc 变化点 / 1500 字）
  - 输出指标落地到 `evals/output/punch_metrics.json`
  - 验证目标：刺激点密度 ≥ 1/章，情绪转折 ≥ 1/1500字
- [ ] **ContinuityAuditor state_mismatches 实装**：
  - 基于 `character_states` 历史对比，实现真正的状态矛盾检测
  - 检测类型至少覆盖：角色位置跳变、道具状态矛盾、数值账本不一致
  - 在已有 10 章数据上能检测到至少 1 类真实矛盾
  - 更新 `ContinuityAuditor._find_state_mismatches()` 返回真实数据
- [ ] **Arc/Volume 摘要自动生成**：
  - 在 Arc 边界（由 `projects.arc_boundaries` 或启发式检测触发）触发摘要生成
  - 方案选择：LLM 生成 或 基于 `ChapterSummary` 聚合
  - `ArcSummary` 和 `VolumeSummary` 非空字符串
  - 写入 `arc_summaries` / `volume_summaries` 表
- [ ] **50 章模拟测试**：
  - 用 10 章真实数据 + 40 章模拟数据构造测试场景
  - 验证 `budget_used` 在 50 章模拟中 ≤ 1.0
  - 验证关键信息保留率 ≥ 90%
  - 输出 `evals/output/50ch_simulation_report.json`

## Out of Scope

- 不重新生成 10 章真实内容（使用已有数据）
- 不修改 Phase 1~4 的核心逻辑（只补验证和空壳）
- 不做 100+ 章模拟（Phase 6 调研范围）

## 接口契约

```python
# Punch 自动评估
class PunchMetrics(BaseModel):
    chapter_number: int
    punch_density: float  # punch_points / word_count * 1000
    emotion_switches: int  # emotion_arc 变化次数
    emotion_switch_rate: float  # switches / word_count * 1500

async def evaluate_punch_metrics(project_id: int) -> list[PunchMetrics]:
    """对已有章节运行 Punch Engine 量化评估."""
    ...

# state_mismatches 增强
async def _find_state_mismatches(
    self,
    project_id: int,
    chapter_range: tuple[int, int],
) -> list[StateMismatch]:
    """基于 character_states 历史对比检测状态矛盾."""
    ...

# Arc/Volume 摘要生成
async def generate_arc_summary(
    project_id: int,
    arc_boundary: tuple[int, int],
) -> ArcSummary:
    """在 Arc 边界生成摘要（LLM 或聚合）."""
    ...

# 50 章模拟
async def run_50chapter_simulation(
    project_id: int,
    real_chapters: int = 10,
    simulated_chapters: int = 40,
) -> SimulationReport:
    """运行 50 章模拟，验证分层上下文性能."""
    ...
```

## 数据模型

```python
class SimulationReport(BaseModel):
    total_chapters: int
    budget_used: float  # 实际 token / 预算上限
    retention_rate: float  # 关键信息保留率
    critical_loss_count: int  # 丢失的关键信息数
    open_thread_count: int  # 未完结线索数
    permanent_scene_count: int  # 永久保留场景数
```

## 测试要求

### Layer 1: 模型测试
- [ ] `PunchMetrics` / `SimulationReport` 可正确实例化

### Layer 2: 模块测试
- [ ] `evaluate_punch_metrics` 在 10 章真实数据上输出有效指标
- [ ] `_find_state_mismatches` 能检测到至少 1 类真实矛盾（角色位置跳变 / 道具矛盾 / 数值不一致）
- [ ] `generate_arc_summary` 输出非空字符串摘要
- [ ] `run_50chapter_simulation` budget_used ≤ 1.0，retention_rate ≥ 0.9

### Layer 3: 集成测试
- [ ] 50 章模拟不破坏现有 DB 数据（使用独立测试 DB）
- [ ] Punch 指标与 RuleAuditor 的 `punch_check` 结果一致

## 验收标准

- [ ] Punch 评估脚本输出刺激点密度和情绪转折数（`evals/output/punch_metrics.json`）
- [ ] `state_mismatches` 能检测到至少 1 类真实矛盾（如角色位置跳变）
- [ ] Arc 摘要非空字符串（`arc_summaries` 表有有效数据）
- [ ] 50 章模拟 budget_used ≤ 1.0，关键信息保留率 ≥ 90%
- [ ] 所有现有测试继续通过（pytest 全绿）
- [ ] 更新了 `docs/STATUS.md`
- [ ] 生成了 `tasks/034-validation-gapfill-DONE.md` 交接文件

## 参考

- `docs/review/v2_work_plan_2026-06-02.md` — 验证缺口清单
- `docs/review/orbital_horror_ch2_ch11_assessment.md` — 基线评估报告（含矛盾实例）
- `src/songyan/agents/continuity_auditor.py`
- `src/songyan/agents/settlement_extractor.py`
- `src/songyan/agents/context_manager.py`
- `tests/test_layered_context.py`
- `tests/test_settlement_impact.py`
