# Task 100b: 流程质量门 + 人工 edit 审计修复 — 交接报告

> **状态**: 已完成
> **完成时间**: 2026-06-13
> **验证范围**: 5 章端到端（Ch46-Ch50，项目 proj-e74ef1e4）

---

## 做了什么

### 1. 新增 `quality_gate_node` 工作流节点

在 `revision_router("pass")` 和 `human_confirm` 之间插入独立质量门节点，执行 accept 前的三联检：

| 检查项 | 阈值 | 失败策略 |
|--------|------|----------|
| 字数 | [0.80x, 1.30x] | >1.30x → rewrite；<0.80x → revision_needed |
| 保留率 | ≥ 0.70 | <0.70 → revision_needed |
| 新问题 | 必须为空 | 非空 → revision_needed |

### 2. 新增 `quality_gate_router` 路由函数

- `rewrite` → 路由到 `rewrite` 节点
- `revision_needed` → 路由到 `revision_handler`
- `pass` → 路由到 `human_confirm`
- `error` 存在时容错回退到 `pass`

### 3. 修复 `human_gate_node` 的 `edit` 分支

**修改前**：edit 后直接创建 `accepted` 版本并进入 `settlement`，**不经过 Audit**。

**修改后**：
- 创建 `edited` 版本
- 更新 `chapter_head` 为 `draft` 状态（`accepted_version_id=None`）
- 清空所有 audit 状态字段（`review_report_id`, `_has_critical`, `_new_issues_introduced` 等）
- 返回 `status="rule_auditing"`，重走完整 Audit 流程

### 4. 更新 `human_confirm_router`

- `edit` 决策不再映射到 `settlement_extractor`
- 新增 `edit_audit` 映射到 `rule_auditor`

### 5. 更新 `phase1_graph.py`

- `Phase1State` 新增 `_quality_gate_passed`, `_quality_gate_failures`, `_current_gate`
- `initial_state` 包含新字段默认值
- 图结构更新：`literary_auditor → revision_router → pass → quality_gate → [human_confirm/rewrite/revision_handler]`

---

## 验证结果

### 单元测试

```
pytest tests/test_100b_quality_gate.py tests/test_error_stage.py
       tests/test_revision_handler.py tests/test_088_revision_word_limit.py
       tests/test_079_segmented_revision.py tests/test_revision_handler_patch.py
       tests/test_revision_handler_fuzzy.py -v
# 146 passed, 0 failed
```

### 5 章端到端验证（proj-e74ef1e4，scifi / webnovel）

| 章节 | Accepted 版本 | 字数 | 目标 | 比例 | 质量门状态 |
|------|--------------|------|------|------|-----------|
| Ch46 | rev-46-6 | 4251 | 3500 | 1.214x | 通过 |
| Ch47 | rev-47-6 | 4109 | 3500 | 1.174x | 通过 |
| Ch48 | cv-7ce557fa | 4117 | 3500 | 1.176x | 通过 |
| Ch49 | rev-49-6 | 4022 | 3500 | 1.149x | 通过 |
| Ch50 | rev-50-8 | 4224 | 3500 | 1.207x | 通过 |

**关键结论**：
- 5 章全部通过质量门，无拦截、无误判
- 正常流程未被破坏，从 literary_auditor → quality_gate → human_confirm 链路通畅
- 无 edit 场景触发（auto-confirm 模式下），edit 重审计逻辑通过单元测试验证

---

## 代码变更清单

1. `src/songyan/workflows/_nodes.py`
   - 新增 `quality_gate_node` 函数
   - 修改 `human_gate_node` edit 分支：创建 edited 版本后路由到 rule_auditing，清空 audit 状态

2. `src/songyan/workflows/phase1_graph.py`
   - `Phase1State` 新增 `_quality_gate_passed`, `_quality_gate_failures`, `_current_gate`
   - 新增 `quality_gate_router` 路由函数
   - 修改 `human_confirm_router`：edit → edit_audit → rule_auditor
   - `build_phase1_graph` 注册 `quality_gate` 节点并更新边映射
   - `initial_state` 包含新字段

3. `tests/test_100b_quality_gate.py`（新增）
   - 覆盖 quality_gate_node 三联检（字数高/低/保留率低/新问题/全部通过）
   - 覆盖 quality_gate_router 路由
   - 覆盖 human_confirm_router edit_audit 映射
   - 覆盖 human_gate_node edit 后重走 Audit

---

## 已知限制

- ruff 报告 16 个 pre-existing 错误（E402, F541, E501, F401, F841, I001），不在本 Task 范围内
- `ProjectRunResult` 对象缺少 `completed` 属性（日志末尾报错），不影响生成功能
- auto-confirm 模式下未触发实际 edit 场景，edit 重审计通过单元测试覆盖

---

## 下一步

- Task 100c: 上下文压力优化
