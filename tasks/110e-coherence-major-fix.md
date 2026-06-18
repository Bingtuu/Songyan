# Task 110e: Auditor Coherence 阈值校准 + 审查上下文增强

> **Phase**: V5.0 Phase 4 修复 — Writer/Auditor 层面调优
> **优先级**: P0
> **依赖**: Task 110d 完成（coherence_major 根因已定位）
> **预计工作量**: 1-2 天

---

## Goal

解决 Task 110d 发现的 coherence_major 瓶颈。当前 Ch80-Ch100 的 QG 失败 100% 由 coherence_major 导致，而加载端优化（增加角色数量）无正收益。本 Task 从 **Auditor 阈值** 和 **审查上下文** 两个层面进行修复。

---

## Context

### Task 110d 关键发现

1. **coherence_major 是 Ch80+ 唯一失败模式**：10/17 失败章节全部标记 coherence_major
2. **加载端优化无效**：`character_states_loaded` 从 1→2 后，QG 通过率无改善，Ch92 甚至从 PASS→FAIL
3. **根因定位**：coherence_major 完全取决于 LLMAuditor 的 LLM 输出。LLM 只要标记 1 个 major 级别的 consistency issue（world_consistency / character_behavior / timeline / new_setting_unregistered），就会触发自动修订
4. **LLMAuditor 上下文不足**：当前 `_render_context_info` 只显示角色的 `name` + `emotional_state`，LLM 缺乏 `current_location`、`current_cultivation`、`active_relationships`、`unresolved_issues` 等关键信息，容易因"信息不足"导致误判

### 为什么是现在修复

- Task 111（Ch101-Ch150）即将启动，若 coherence_major 不解决，后半程达标率将进一步恶化
- 两个方案均为工程层调整，不涉及 Prompt 重写（V5.1 范畴），符合 P0 规则

---

## In Scope

### 方案 A：降低 ScoreAggregator 阈值（工程层）

- [ ] **修改 `ScoreAggregator._score_coherence`**
  - major 扣分从 -0.25 降到 -0.15
  - `coherence_major` 触发条件从 `major > 0` 改为 `major >= 2` 或 `coherence_score < 0.6`
  - 保留 `coherence_critical` 不变（critical issue 仍必须修复）

- [ ] **更新相关测试断言**
  - `tests/test_score_aggregator.py` 中涉及 coherence score 和 flags 的测试用例

### 方案 B：增加 LLMAuditor 审查上下文（准确性层）

- [ ] **修改 `llm_auditor.py` 的 `_render_context_info`**
  - 当前只显示：`name` + `emotional_state`
  - 增加显示：
    - `current_location`
    - `current_cultivation`
    - `active_relationships`
    - `unresolved_issues`
  - 格式保持简洁，避免 token 过度膨胀

- [ ] **评估 token 增量**
  - 预期增量：200-500 tokens / 角色
  - Ch80+ 通常 1-2 个角色 → 总增量 < 1000 tokens
  - 确保增量在 budget 可接受范围内

### 验证

- [ ] **Ch91-Ch93 快速验证**
  - 复用 proj-e74ef1e4，跑 Ch91-Ch93（之前问题最严重的区域）
  - 对比修复前后的 QG 通过率、coherence_major 次数

- [ ] **若 Ch91-Ch93 有效，扩展至 Ch80-Ch96 全量验证**
  - 与 Task 110d 基线对比
  - 确认无新增失败模式（如 readability、momentum 恶化）

---

## Out of Scope

- 不修改 Writer prompt（属于 V5.1，见 AGENTS.md P2-#51）
- 不新增 Agent/Workflow 节点
- 不调整 continuity_auditor 的 human_mark 生成逻辑
- 不修改 RuleAuditor 的判定标准

---

## 验收标准

| 指标 | 目标 |
|------|------|
| Ch91-Ch93 QG 通过率 | >= 50%（修复前 33.3%，即至少 1 章 PASS→修复后至少 2/3 或 3/3） |
| coherence_major 次数 | 较修复前下降 >= 50% |
| 无新增 critical issue | 是（critical 仍为有效红线） |
| budget_used 增幅 | <= +0.05（方案 B 的上下文增量可控） |
| 全量回归测试 | 无新增失败 |

---

## 技术要点

### 方案 A 修改点

**文件**: `src/songyan/evals/score_aggregator.py`

```python
# _score_coherence 中
def _score_coherence(llm_result: LLMAuditResult) -> tuple[float, dict[str, float], bool, bool]:
    ...
    score = 1.0 - critical * 0.40 - major * 0.15 - minor * 0.10  # major 从 0.25 降到 0.15
    score = max(0.0, min(1.0, score))
    ...
    return score, details, critical > 0, major >= 2  # coherence_major 需 2+ major
```

**注意**: `ScoreFlags.coherence_major` 的判定同时需要在 `aggregate` 方法中调整：

```python
coherence_major=has_major and coherence_score < 0.6,  # 或保持 has_major 语义，修改 has_major 定义
```

### 方案 B 修改点

**文件**: `src/songyan/agents/llm_auditor.py`

在 `_render_context_info` 的 character_states 渲染部分，增加字段：

```python
if ctx.character_states:
    char_lines = []
    for cs in ctx.character_states:
        info = f"{cs.name}"
        if cs.emotional_state:
            info += f"（情绪：{cs.emotional_state}）"
        if cs.current_location:
            info += f"（位置：{cs.current_location}）"
        if cs.current_cultivation:
            info += f"（修为：{cs.current_cultivation}）"
        if cs.active_relationships:
            info += f"（关系：{', '.join(cs.active_relationships)}）"
        if cs.unresolved_issues:
            info += f"（目标：{', '.join(cs.unresolved_issues)}）"
        char_lines.append(info)
    lines.append(f"**出场角色**：{'；'.join(char_lines)}")
```

---

## 风险

| 风险 | 影响 | 缓解 |
|------|------|------|
| 方案 A 过度宽容，漏掉真正严重的 consistency issue | 质量下降 | `critical` 阈值不变；`coherence_major` 同时要求 `coherence_score < 0.6`，确保总分过低时仍触发修订 |
| 方案 B token 增量挤压 budget | 其他分区被压缩 | 只增加 4 个字段，预期增量 < 1000 tokens；在 `_estimate_package` 中验证 |
| Ch91-Ch93 样本量小，结果不稳定 | 结论不可靠 | 若 Ch91-Ch93 有效，立即扩展至 Ch80-Ch96（17 章） |
| 两方案叠加后效果不可拆分 | 无法归因 | 先实施方案 A 验证，再叠加方案 B（但为节省时间，可并行实施） |

---

## 回滚策略

- 若验证后 QG 通过率无改善或恶化，回滚 `score_aggregator.py` 和 `llm_auditor.py` 的修改
- 回滚后 coherence_major 问题继续存在，需接受为 V5.0 已知限制，留待 V5.1 通过 Prompt 调优解决

---

## 下一 Task

**Task 111: Ch101-Ch150 流式验证 + 决策门 DG-2**

- 在 110e 修复后重新评估 Ch80-Ch100 达标率
- 若达标率 >= 65%，推进 Ch101-Ch150 验证
- 若仍 < 50%，考虑在 DG-2 中降低 Ch80+ 的 QG 目标至 >= 60%
