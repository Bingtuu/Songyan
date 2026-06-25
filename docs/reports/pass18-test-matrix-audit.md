# Pass 18 — 测试矩阵与覆盖率审查报告

> **范围**: TS-01 ~ TS-10 (动态阈值、degraded_accept、Settlement 子模块、Pipeline 集成、QG 硬拦截、Rewrite 清理、ContextEmergency、E2E、mock fixture、回归基线)
> **日期**: 2026-06-25
> **审查者**: Codex
> **状态**: 完成（静态分析 + pytest 运行时验证）

---

## 摘要

本 Pass 验证当前测试基线并识别测试矩阵缺口。

| ID | 检查项 | 状态 | 验证方法 | 说明 |
|----|--------|:----:|---------|------|
| TS-01 | 动态阈值单元测试 | ⚠️ | 审查 `test_106_scoring_system.py` + 全局搜索 | 代码有 `_safe_best_min_score`，但无专门测试覆盖三段阈值 |
| TS-02 | `degraded_accept` 降级回滚 | ⚠️ | 全局搜索 `degraded_accept` in `tests/` | 代码路径完整，测试零覆盖 |
| TS-03 | Settlement 子模块测试 | ⚠️ | 审查 `test_settlement_submodules.py` | 空壳文件（全 TODO）；`test_settlement_extractor.py` 有实际测试 |
| TS-04 | Pipeline 集成测试 | ✅ | 审查 `test_phase1_graph.py` + `integration/` | 路由全覆盖 + 3 章链路集成 |
| TS-05 | QG false 硬拦截 | ✅ | 审查 `test_108_core_nodes.py` | `test_qg_false_blocks_settlement` 存在 |
| TS-06 | Rewrite 状态清理 | ✅ | 审查 `test_rewrite_node.py` | `_was_rewritten`、avoid_list、字数约束均有测试 |
| TS-07 | ContextEmergency 降级 | ✅ | 审查 `test_104_budget_hard_ceiling.py` | 8 个测试覆盖触发/降级/硬约束/不突变 |
| TS-08 | Ch1-Ch20 E2E 模拟 | ⚠️ | 审查 `integration/` + `evals/` | 仅 3 章链路，无 Ch1-Ch20 端到端 |
| TS-09 | mock_llm fixture 使用 | ✅ | 审查 `conftest.py` | `mock_llm` fixture 已定义 |
| TS-10 | 测试回归基线 | ✅ | 执行 `pytest tests/ -q` | **1803 passed, 0 failed**，超基线 ≥1731 |

**6/10 项通过，4 项需关注（TS-01, TS-02, TS-03, TS-08）。**

---

## F1: TS-01 — 动态阈值单元测试

### 验证方法

全局搜索 `_safe_best_min_score` 和 0.75/0.78/0.82 在测试中的覆盖。

### 验证结果

**代码实现（`workflows/_nodes.py` L81-88）**：
```python
def _safe_best_min_score(chapter_number: int) -> float:
    """章节阶段感知的 safe-best 门槛：早期章节天然分数偏低。"""
    if chapter_number <= 20:
        return 0.75
    elif chapter_number <= 50:
        return 0.78
    else:
        return 0.82
```

**测试覆盖**：
- `test_106_scoring_system.py` 覆盖 ScoreAggregator 维度评分，但未覆盖章节阶段阈值
- 全局搜索 `0.75` / `0.78` / `0.82` 在 `tests/` 中，匹配均来自其他上下文（embedding benchmark、consistency test、run_logger 等），与 `_safe_best_min_score` 无关

**判定**：⚠️ **缺口（P1）**。动态阈值代码存在但无单元测试覆盖。建议补充 `test_safe_best_min_score` 覆盖 Ch1/Ch20/Ch21/Ch50/Ch51 的边界值。

---

## F2: TS-02 — `degraded_accept` 降级回滚

### 验证方法

全局搜索 `degraded_accept` 在 `tests/` 目录。

### 验证结果

**代码路径（`workflows/_nodes.py`）**：
- L238: `_score_card_is_degraded_acceptable` 实现
- L1812-1826: QualityGate 中 degraded accept 路径
- L2109-2129: SettlementExtractor 中 degraded accept 放行逻辑

**测试覆盖**：
```python
# tests/ 全局搜索 degraded_accept → 零处匹配
```

**判定**：⚠️ **缺口（P1）**。degraded accept 是 Task 121q 引入的关键容错路径，但测试矩阵完全未覆盖。建议补充：
1. `_score_card_is_degraded_acceptable` 单元测试（分数边界值）
2. QualityGate 中 degraded accept 触发测试
3. SettlementExtractor 对 degraded accept 放行测试

---

## F3: TS-03 — Settlement 子模块测试

### 验证方法

审查 `test_settlement_submodules.py`、`test_settlement_extractor.py` 和 `settlement_extractor/` 测试目录。

### 验证结果

**`test_settlement_submodules.py`**（Pass 13 遗留）：
```python
async def test_apply_settlement_creates_records():
    pass  # TODO

async def test_apply_settlement_handles_duplicates():
    pass  # TODO

def test_validate_impact_score_range():
    pass  # TODO

async def test_constraints_honor_budget():
    pass
```

**实际覆盖**：
- `test_settlement_extractor.py`: 14+ 个测试，覆盖 `_render_prompt`、`_build_character_update`、`_build_new_setting`、`_build_foreshadowing_update`、`_backfill_foreshadowing_source_version_ids`、`_build_numerical_update`、`_build_state_settlement`
- `settlement_extractor/test_setting_quality.py`: setting_key 规范化测试
- `settlement_extractor/test_state_compression.py`: 状态压缩测试

**判定**：⚠️ **观察项（P1）**。`test_settlement_submodules.py` 是全空壳文件（6 个 TODO），但 settlement 核心逻辑通过 `test_settlement_extractor.py` 间接覆盖。建议：
- 将 `test_settlement_submodules.py` 中的 TODO 迁移到 `test_settlement_extractor.py` 或补充实现
- 删除空壳测试，避免误报覆盖率

---

## F4: TS-04 — Pipeline 集成测试

### 验证方法

审查 `test_phase1_graph.py` 和 `integration/test_multi_chapter.py`。

### 验证结果

**Phase1 路由测试（`test_phase1_graph.py`）**：
```python
class TestComputeOverallScore        # 评分计算
class TestMergeSummary               # 摘要合并
class TestMergeReviews               # 审查合并
class TestConvertRuleToIssues        # Rule→Issue 转换上限
class TestRevisionRouter             # revision 路由（critical/major/rewrite/pass）
class TestQualityGateRouter          # QG 路由
class TestRewriteRouter              # rewrite 路由（结构失败/成功/错误）
class TestHumanConfirmRouter         # human_confirm 路由（accept/edit/reject/back）
```

**多章链路集成（`integration/test_multi_chapter.py`）**：
```python
async def test_multi_chapter_3_success            # 3 章完整链路
async def test_multi_chapter_previous_summary_in_goal  # 跨章 summary 传递
async def test_multi_chapter_accumulated_summary   # accumulated_summary 拼接
```

**判定：TS-04 通过。** Pipeline 路由全覆盖，集成测试验证 3 章 DB 状态一致性。

---

## F5: TS-05 — QG false 硬拦截

### 验证方法

审查 `test_108_core_nodes.py`。

### 验证结果

```python
# test_108_core_nodes.py L126-123
class TestSettlementExtractorNodeQGFalseBlock:
    @pytest.mark.asyncio
    async def test_qg_false_blocks_settlement_and_returns_review(self) -> None:
        """QG false 时不提取 settlement，不应用 settlement，不生成 summary，进入复核态."""
        ...
        assert result["settlement_id"] is None
        assert result["status"] == "settlement_review"
        assert result["_settlement_needs_human_review"] is True
```

**判定：TS-05 通过。** 专门测试验证 QG false 时 settlement 被硬拦截。

---

## F6: TS-06 — Rewrite 状态清理

### 验证方法

审查 `test_rewrite_node.py` 和 `test_108_core_nodes.py`。

### 验证结果

```python
# test_rewrite_node.py
test_avoid_list_from_previous_issues          # avoid_list 构建
test_avoid_list_deduplication                 # 去重
test_avoid_list_cap_at_10                     # 上限
test_rewrite_injects_word_count_constraint    # 字数约束注入
test_rewrite_injects_scene_structure_constraint  # 场景约束注入
test_rewrite_hard_truncates_to_word_limit     # 硬截断

# test_108_core_nodes.py
test_rewrite_node_clears_best_version_id      # rewrite 后 _best_version_id 清理
```

**判定：TS-06 通过。** Rewrite 节点的前置清理（avoid_list、字数约束）和后置清理（best_version_id）均有测试覆盖。

---

## F7: TS-07 — ContextEmergency 降级

### 验证方法

审查 `test_104_budget_hard_ceiling.py`。

### 验证结果

```python
class TestContextEmergency:
    def test_emergency_triggered_when_budget_used_exceeds_1_0    # 触发条件
    def test_emergency_reduces_tokens_significantly               # token 降低
    def test_emergency_drastically_reduces_soft_partitions        # 软分区清空
    def test_emergency_preserves_hard_partitions                  # 硬约束保留
    def test_emergency_keeps_top_character_only                   # 主角保留
    def test_emergency_keeps_only_last_summary                    # recent_plot 清空
    def test_no_emergency_when_under_budget                       # 正常路径不触发
    def test_emergency_does_not_mutate_original                   # 不修改原始对象
```

**判定：TS-07 通过。** 8 个测试完整覆盖 ContextEmergency 的所有关键行为。

---

## F8: TS-08 — Ch1-Ch20 E2E 模拟

### 验证方法

审查 `integration/` 和 `evals/` 测试目录。

### 验证结果

**现有集成测试**：
- `integration/test_multi_chapter.py`: 3 章链路
- `integration/test_paths.py`: 路径测试
- `integration/test_ch41_50_validation.py`: Ch41-50 种子章节验证

**缺口**：
- 无 Ch1-Ch20 端到端模拟测试
- `evals/runner.py` 存在，但 `tests/` 中无调用 runner 的 E2E 测试

**判定**：⚠️ **缺口（P1）**。最长集成测试仅 3 章，未覆盖 Ch1-Ch20 的端到端上下文累积效应。建议补充 `integration/test_ch1_20_e2e.py` 或使用 `evals/runner.py` 做自动化 E2E 验证。

---

## F9: TS-09 — mock_llm fixture 使用

### 验证方法

审查 `tests/conftest.py`。

### 验证结果

```python
# conftest.py L29-35
@pytest.fixture
def mock_llm():
    """P2-7: Unified mock LLM fixture for all test suites."""
    from unittest.mock import patch
    with patch("songyan.llm.client.call_llm") as mock:
        mock.return_value = '{"result": "test"}'
        yield mock
```

**使用现状**：
- 集成测试更多使用 `mock_call_llm`（自定义 fixture）
- `mock_llm` fixture 定义存在，但部分测试套件未统一迁移

**判定：TS-09 通过。** Fixture 已定义并可用，统一迁移为后续优化项，非阻塞。

---

## F10: TS-10 — 测试回归基线

### 验证方法

执行 `pytest tests/ -q`。

### 验证结果

```
1803 passed, 2 skipped, 1 xfailed, 1 xpassed, 24 warnings in 351.32s
```

- **通过数**: 1803（≥ 基线 1731）✅
- **失败数**: 0 ✅
- **新增失败**: 0 ✅
- **xpassed**: 1（预期失败但通过了，建议修复 xfail 标记）⚠️ 轻微
- **warnings**: 24（主要是 `@pytest.mark.asyncio` 误用于同步函数，无害）

**判定：TS-10 通过。** 测试基线健康，通过数超过目标 1731，零失败。

---

## Pass R 回归检查

| ID | 检查项 | 状态 |
|----|--------|:----:|
| RG1 | 新增 import 是否引入未声明依赖 | ✅ 无新增 import |
| RG2 | 新增 except 是否用了裸 Exception | ✅ 无代码变更 |
| RG3 | 修改文件是否保持 < 400 行 | ✅ 无代码变更 |
| RG4 | pytest 回归全绿 | ✅ 1803 passed, 0 failed |

---

## 发现汇总

| ID | 严重度 | 发现 | 文件 | 建议 |
|----|:------:|------|------|------|
| TS-01-gap | P1 | `_safe_best_min_score` 三段阈值无单元测试 | `tests/test_106_scoring_system.py` | 补充 Ch1/Ch20/Ch21/Ch50/Ch51 边界值测试 |
| TS-02-gap | P1 | `degraded_accept` 路径零测试覆盖 | `tests/` | 补充 `_score_card_is_degraded_acceptable` + QualityGate + SettlementExtractor 降级路径测试 |
| TS-03-obs | P1 | `test_settlement_submodules.py` 是全空壳（6 个 TODO） | `tests/test_settlement_submodules.py` | 迁移 TODO 到 `test_settlement_extractor.py` 或补充实现后删除空壳 |
| TS-08-gap | P1 | 无 Ch1-Ch20 端到端集成测试 | `tests/integration/` | 补充 `test_ch1_20_e2e.py` 或接入 `evals/runner.py` |
| TS-10-xp | P2 | 1 个 xpassed 测试 | `tests/` | 修复 xfail 标记或移除过时预期 |

---

## 汇总

```
Pass 18 状态:
  TS-01 (动态阈值)           ██████▁▁▁▁  ⚠️ 缺口
  TS-02 (degraded_accept)    ██████▁▁▁▁  ⚠️ 缺口
  TS-03 (Settlement 子模块)  ████████▁▁  ⚠️ 观察项
  TS-04 (Pipeline 集成)      ██████████  ✅
  TS-05 (QG false 拦截)      ██████████  ✅
  TS-06 (Rewrite 清理)       ██████████  ✅
  TS-07 (ContextEmergency)   ██████████  ✅
  TS-08 (Ch1-Ch20 E2E)       ██████▁▁▁▁  ⚠️ 缺口
  TS-09 (mock_llm fixture)   ██████████  ✅
  TS-10 (回归基线)           ██████████  ✅

  通过:  6/10
  缺口:  4/10 (TS-01, TS-02, TS-03, TS-08)
```

**测试矩阵核心结论**：
- **基线健康**：1803 passed / 0 failed，远超 ≥1731 目标
- **关键缺口**：动态阈值、degraded_accept、 settlement 子模块独立测试、Ch1-Ch20 E2E 四项无覆盖
- **风险评级**：P1。虽然整体通过率高，但 degraded_accept 和动态阈值是 V5.1 核心功能，缺测试意味着回归风险不可见

---

> **松烟入墨，字句成锋。**
> 测试是代码的倒影 — 当每一行关键逻辑都有测试守护，重构才有底气，长跑才不惧。
