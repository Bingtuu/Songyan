# Task 138g: critical orphan 根因复核与最小收口

> **类型**: 语义复核 / 最小代码修复 / 聚焦复跑
> **状态**: 已关闭
> **前置**: Task 138d-R2 retry4

> **V5.2 收口说明**：本任务未单独收口，critical orphan 的根因分析与修复由 Task 138m/138n/138o 完成并验证。
## 背景

Task 138d-R2 retry4 已证明 settlement 阻断解除：

- Run ID: `run-bcee6ab6`
- DB: `.tmp/task138d_r2_retry4_ch10_focus_20260629_101459.db`
- Ch11/Ch12 settlement、summary、QG 全部通过。
- Ch12 continuity 已生成：`health=3.0`、`orphaned=14`、`mismatches=0`。

health 仍为 3.0 的直接原因不是流程失败，而是剩余 orphan 中仍有 3 个 `critical`：

```text
score = 10
- critical 3 * 2.0 = 6.0
- background 9 * 0.1 = 0.9
- technical 2 * 0.05 = 0.1
- forgotten 2 * 0.5 = 1.0
= raw 2.0
Ch12 early floor = 3.0
```

本任务只处理这 3 个 critical orphan，先确认语义归属，再做最小收口，避免继续追着指标做泛化修补。

## 3 个 critical orphan

| setting_key | 名称 | tracking 状态 | 处置 |
|---|---|---|---|
| `artifact.mega_ruin.surface_material` | 巨型遗迹表面材料特性 | `introduced=3`、`last_mentioned=3`、`active`、`critical` | `refresh_missing` |
| `organization.expedition.team_7` | 第7远征队·静默节点 | `introduced=4`、`last_mentioned=7`、`active`、`critical` | `planner_recall` |
| `artifact.ruin.phase_flush_mechanism` | 相位冲刷机制 | `introduced=7`、`last_mentioned=7`、`active`、`critical` | `planner_recall` |

## 语义复核

### `artifact.mega_ruin.surface_material`

原始设定：

- source_version_id: `rev-3-3-de0d24f8`
- source_quote: `指尖触到的是冷冰冰的金属感，但他按下时，指腹下的表面向内凹陷了不到一毫米，随即又弹回原状。不是刚性结构。是半流体。一种能根据外部压力改变密度的材料`

Ch12 accepted 正文已有明确证据：

- `星图是从墙壁内部生长出来的，像是遗迹的记忆正在被低温激活，一层层地从表面材料下浮现出来。`
- `舰体表面的涂装在遗迹表面半流体材料的反光中扭曲变形。`
- `墙壁上的能量纹路在低温下变得更加明亮。`

结论：这是正文证据存在但 tracking 未刷新的 `refresh_missing`。应补窄 alias / reference term，不应归档或降级。

### `organization.expedition.team_7`

原始设定：

- source_version_id: `v-4-1-596d5a8d`
- description: `十年前被派往静默遗迹核心区域的远征队，胸牌显示‘第7远征队·静默节点’及‘最终迭代——循环计数：7’`

近期证据：

- Ch7 accepted 明确提及 `第7远征队·静默节点`。
- Ch8/Ch9 有 `第7远征队`、`静默节点` 的持续语义关联。
- Ch12 accepted 无明确提及。

结论：这是仍需主线回收的 `planner_recall`。不能用 Ch12 弱相关内容刷新；也不能 archive 或降级。

### `artifact.ruin.phase_flush_mechanism`

原始设定：

- source_version_id: `v-7-1-7044ef21`
- source_quote: `每72分钟……一次相位冲刷……所有纳米蜂群进入休眠……只有那个时候……核心的量子纠缠网络会暂时关闭`

近期证据：

- Ch7 accepted 明确提及完整机制。
- Ch12 accepted 只有 `相位偏移` 等弱相关表达，不是 `每72分钟相位冲刷机制` 证据。

结论：这是仍需主线回收的 `planner_recall`。不能用裸 `相位`、`相位偏移`、`纳米蜂群` 等宽泛词刷新。

## 本轮改动边界

本轮做：

- 修复 `artifact.mega_ruin.surface_material` 的窄证据刷新。
- 增强 CreativeDirector 对 stale critical setting 的提示强度。
- 补充正负例测试，防止宽匹配伪刷新。
- 使用新的 `.tmp` 副本 DB 复跑 Ch10-Ch12。

本轮不做：

- 不修改 `ContinuityAuditor._compute_health_score()`。
- 不 archive 或降级 `critical` orphan。
- 不用 Ch12 弱相关词刷新 `team_7` / `phase_flush_mechanism`。
- 不扩大到 Ch1-Ch20/default run。
- 不污染主库。

## 验收

- 目标测试通过。
- `ruff check src/ tests/` 通过。
- 新副本 DB 复跑 Ch10-Ch12：
  - Ch11/Ch12 settlement、summary、QG 全部通过。
  - Ch12 continuity 生成。
  - `artifact.mega_ruin.surface_material` 不再出现在 Ch12 orphan。
  - 若 `team_7` / `phase_flush_mechanism` 仍未被正文回收，它们应继续作为 critical orphan 暴露，不被静默吞掉。

---

## 实施记录

### 代码改动

- `src/songyan/agents/settlement_extractor/_apply.py`
  - 为 `artifact.mega_ruin.surface_material` 补充窄证据短语：
    - `遗迹表面半流体材料`
    - `从表面材料下浮现`
    - `半流体材料`
    - `遗迹表面的能量纹路`
    - `墙壁上的能量纹路`
  - 保留宽泛词负例，不使用裸 `巨型遗迹`、裸 `表面`、裸 `能量纹路`、普通 `金属表面` 刷新。
- `src/songyan/agents/creative_director/__init__.py`
  - `_load_active_settings_to_recycle()` 为待回收项注入 `current_chapter`。
  - `_format_active_settings_to_recycle()` 对已达到 orphan 阈值的 `critical` 项输出 `严重级别：P1` 与“本章必须明确回收、提及、或给出无法回收的剧情原因”。

### 测试

- `python -m pytest tests/test_task137_setting_recycling.py -q` -> `36 passed`
- `python -m pytest tests/test_task137_setting_recycling.py tests/test_task135_continuity_governance.py tests/test_continuity_health_governance.py -q` -> `70 passed`
- `ruff check src/ tests/` -> `All checks passed!`

### 复跑 / run-715f7d09

- Run ID: `run-715f7d09`
- DB: `.tmp/task138g_ch10_focus_20260629_105803.db`
- Report: `archive/v5/reports/task-137-ch10-focus-validation-report.md`
- 运行窗口: Ch10-Ch12
- `project_runs.status`: `completed`
- `completed_chapters`: `[10, 11, 12]`
- `failed_chapters`: `[]`
- Ch11 accepted: `v-11-4-323c4e94`
- Ch12 accepted: `v-12-1-0f5d66d5`
- Ch11 run log: `success=true`、`settlement_success=true`、`summary_success=true`、`quality_gate_passed=true`、`settlement_validation_errors=[]`
- Ch12 run log: `success=true`、`settlement_success=true`、`summary_success=true`、`quality_gate_passed=true`、`settlement_validation_errors=[]`
- Writer manifest 已恢复为 `default_version: "1.1.0"`；复查无 `run_137_ch10_focus_validation.py` 残留进程。

### Ch12 continuity 结果

| 指标 | Retry4 `run-bcee6ab6` | Task 138g `run-715f7d09` | 变化 |
|------|------------------------|---------------------------|------|
| health | 3.0 | 3.0 | 持平 |
| orphaned | 14 | 16 | +2 |
| critical orphan | 3 | 4 | +1 |
| state_mismatches | 0 | 0 | 持平 |
| overdue | 0 | 0 | 持平 |

Task 138g 复跑 critical orphan:

- `artifact.mega_ruin.surface_material`
- `artifact.ruin.phase_flush_mechanism`
- `artifact.ruin.e7_channel_phase_node`
- `artifact.ruin.e7_channel_phase_node_detail`

### 结果判断

- 本轮代码层目标测试通过，但实跑验收未通过。
- `artifact.mega_ruin.surface_material` 仍为 orphan 的原因不是 alias 正例失效，而是 `run-715f7d09` 的 Ch12 accepted 正文没有出现 `表面材料`、`半流体材料`、`墙壁上的能量纹路` 等明确证据；因此无法刷新。
- `organization.expedition.team_7` 在 Ch12 accepted 中被明确提及，因此不再是 orphan。
- `artifact.ruin.phase_flush_mechanism` 仍未被明确回收。
- 新增 critical orphan 为 E-7 相关设定，说明“增强 CreativeDirector 提示文本”不足以稳定约束 Writer 回收 critical 设定。

### 结论

Task 138g 不能判定收口。当前最新证据表明，问题已经不是 settlement 或窄 alias 单点缺陷，而是 critical recall 从 CreativeDirector 到 Writer 正文执行之间缺少稳定闭环。下一步不应继续补单个 alias，而应复核 Writer 输入中的连续性审计约束是否足够具体、是否需要把 critical orphan 作为可验证的 Writer 硬约束或 QG/settlement 前置检查。
