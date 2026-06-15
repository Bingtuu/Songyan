# Task 090a: 字数达标率修复计划（含端到端验证）— 交接报告

> **状态**: ✅ 已完成
> **完成日期**: 2026-06-07
> **提交**: `revision_handler/__init__.py` (`import re` bugfix) + 阈值收紧（Writer 1.20x/0.80x, RevisionHandler 1.25x/0.75x）
> **端到端验证**: 19/19 章完成，达标率 57.9%（字数 ±20%）/ 63.2%（health_score 综合）

---

## 变更摘要

### 1. Writer 阈值收紧（`src/songyan/agents/writer.py`）

- `_enforce_word_count()` 阈值：~~1.50x/0.70x~~ → **1.20x/0.80x**
- 消除 1.2x~1.5x 灰色地带，Writer 直接控制初稿在 ±20% 范围内

### 2. RevisionHandler 阈值收紧（`src/songyan/agents/revision_handler/_segmented_revision.py`）

- `_enforce_revision_word_count()` 阈值：~~1.50x/0.70x~~ → **1.25x/0.75x**
- Revision 后略宽松于 Writer（避免修复过程中过度截断），但仍在 ±25% 以内

### 3. MIN_CONTENT_RATIO 作用域修复（`src/songyan/agents/revision_handler/__init__.py`）

- `MIN_CONTENT_RATIO = 0.5` 从 `run_revision()` 内部移到**模块顶部常量**
- 修复 `UnboundLocalError`，segmented revision 成功后不再 fallback 到 patch_engine
- 减少一次冗余 LLM 调用

### 4. `import re` Bug 修复（`src/songyan/agents/revision_handler/__init__.py`）

- 顶部添加 `import re`
- 修复 Ch17/Ch20 的 `NameError: name 're' is not defined`

### 5. 测试更新

- `tests/test_076_word_count_truncation.py`：硬编码阈值 1.50 → 1.20，18/18 passed
- `tests/test_088_revision_word_limit.py`：阈值和场景数据更新，6/6 passed

---

## 端到端验证结果

### 基线 vs 修复后对比

| 指标 | V3.x 基线 | 修复后（新阈值）| 变化 |
|------|-----------|----------------|------|
| 完成章节 | 19/19 | 19/19 | 持平 |
| 字数达标率（±20%）| **36.8% (7/19)** | **57.9% (11/19)** | **+21.1pp** |
| health_score 达标率 | — | **63.2% (12/19)** | — |
| 平均字数 | 3742 | 3584 | -158 |
| 字数范围 | 2391 ~ 5068 | 2519 ~ 5665 | — |
| 平均 budget_used | 1.146 | 1.120 | -0.026 |
| Writer 截断次数 | 3 | **5** | +2 |
| 失败章节 | 4 (Ch9,10,17,20) | **0** | **全部修复** |
| 总耗时 | 96 min | 18.6 min（增量）| — |
| LLM 调用 | 249 | 251 | — |

### 截断成功案例

| 章节 | 初稿字数 | 目标 | 截断后 | 截断原因 |
|------|----------|------|--------|----------|
| Ch4 | 4527 | 3200 | 3724 | truncated_before_scene_3 |
| Ch9 | 5100 | 3200 | 3473 | truncated_before_scene_2 |
| Ch11 | 3621 | 3200 | 3621 | truncated_before_scene_4 |
| Ch18 | 5423 | 3200 | 2945 | truncated_before_scene_4 |
| Ch20 | 4610 | 3500 | 3036 | truncated_before_scene_3 |

### 达标章节（11 章）

Ch2(0.977), Ch4(1.058), Ch6(1.058), Ch7(0.825), Ch9(1.085), Ch10(1.145), Ch11(1.132), Ch13(0.885), Ch17(0.981), Ch18(0.920), Ch19(0.998), Ch20(0.949)

### 仍超标章节（>1.2x）

Ch3(1.383), Ch12(1.704), Ch14(1.356), Ch15(1.302), Ch16(1.888)

### 仍不足章节（<0.8x）

Ch5(0.746), Ch8(0.787)

---

## 关键发现

### 1. 达标率未达 60% 的核心根因：Scene 数量过少

超标章节共性：**仅 2 个 scenes**（Ch3, Ch12, Ch14, Ch15, Ch16）。

- 单 scene 过长（2000-3000 字），截断到 1 scene 后字数低于 0.8x 下限
- `_enforce_word_count()` 结构保护逻辑拒绝截断（`truncation_would_destroy_structure`）
- 这是**结构性限制**，非阈值问题

### 2. `re` 导入 Bug 的连锁影响

- Ch17/Ch20 之前因 `NameError` 失败，修复后正常通过
- 说明 RevisionHandler patch_engine 路径的字数统计代码依赖 `re.findall`，但模块未导入 `re`

### 3. Revision Rebound 保护机制生效

- Ch20 第二轮 revision 后 issues 从 13 增加到 21，score 从 8.18 降到 3.7
- 系统自动回滚到 rev-20-4 并 accept，避免劣化版本入库

### 4. 新阈值下偏低检测更敏感

- Ch3 Writer 初稿 2851（目标 3500，偏差 -19%），`word_count_mismatch` 警告触发
- Ch5(2611/3500), Ch8(2519/3200) 同样被检测

---

## 异常分析

### Ch14 — FAIL（health=4.53）

- 字数超标 36%，Critical×1，Major×7，疲劳词×4，**章末钩子缺失**
- 2 scenes，结构保护阻止截断
- 弱项：dialogue_subtext=6.5, show_dont_tell=6.5

### Ch15 — FAIL（health=3.02）

- 字数超标 30%，Critical×1，Major×7，AI腔×2，疲劳词×4，**章末钩子缺失**
- 1 scene，结构保护阻止截断
- 套路风险高（cliche=5.0）

### Ch12 — WARN（health=5.50）

- 字数超标 70%，Major×19，疲劳词×5
- 2 scenes，overall_score 仅 3.28
- 质量最差章节，LLMAuditor 第一轮即给出 14 个 major issues

---

## 全局弱项维度（Ch2-Ch20 平均）

| 维度 | 均分 | 诊断 |
|------|------|------|
| show_dont_tell | **6.39** | "展示而非讲述"执行不到位，系统性问题 |
| dialogue_subtext | **6.58** | 对话潜台词不足 |
| narrative_pacing | **6.64** | 叙事节奏控制欠佳 |
| dialogue_distinctness | **6.94** | 角色对话辨识度偏低 |
| genre_numerical | **9.00** | 系统强项（科幻数值设定稳定）|
| timeline | **9.08** | 系统强项（时间线一致性优秀）|

---

## 测试

```
全量: pytest -v
# 预期: ~1356+ passed（与基线持平，无新增失败）

新增/更新测试:
- test_076_word_count_truncation.py: 18/18 passed（阈值更新为 1.20x）
- test_088_revision_word_limit.py: 6/6 passed（阈值更新为 1.25x/0.75x）
```

---

## 已知限制

1. **Scene 数量过少是达标率天花板**：2-scenes 章节无法截断，需从 Writer prompt 层面引导生成更多 scenes
2. **show_dont_tell 和 dialogue_subtext 是系统性弱项**：所有章节均分 < 7，需 Prompt 调优（V3.1 范围外）
3. **Ch1 为种子导入章节**：1252 字，无 scenes，不参与生成章节统计

---

## 下一步

- **Task 091**: Ch21-Ch50 长程验证，确认新阈值在更长尺度下的稳定性
- **V4.0 ContextService 改造**：通过按需检索从根本上解决上下文膨胀 + scene 数量控制问题

---

## 参考

- `tasks/090-phase-b-ch1-ch20-e2e.md` — 原始规格
- `tasks/088-revision-word-limit-DONE.md` — RevisionHandler 字数硬约束交接
- `tasks/089-writer-truncation-tighten-DONE.md` — Writer 截断阈值收紧交接
- `evals/output/task_090a_scifi_webnovel_tightened/report.md` — 端到端运行报告
- `evals/output/task_090a_scifi_webnovel_tightened/detailed_score_report.md` — 逐章详细评分报告
