# Task 111g: 长跑性能缺陷收敛

> **Phase**: V5.0 Phase 4 前置修复 — Long-run Performance Containment
> **优先级**: P2
> **依赖**: Task 111f 完成
> **预计工作量**: 1-2 天

---

## Goal

在 Task 112 长跑前收敛 post-111 review 发现的性能风险，优先处理会按章节数、版本数、角色数、设定数或伏笔数线性/平方放大的成本点，避免 Ch101-Ch150 验证期间出现不必要的 LLM 成本、DB 查询放大、prompt 膨胀或报告写放大。

## Context

post-111 review 的性能观察项包括：

1. 每个章节版本会重复组装 ContextPackage：ContextManager 组装一次，Writer、LLMAuditor、LiteraryAuditor 又各自重新组装。
2. LiteraryAuditor 是诊断型节点，但每轮版本都强制 LLM 审查，增加长跑成本和失败面。
3. SettlementExtractor 正文已截断，但角色状态、active settings、foreshadowings 渲染无数量上限。
4. SettingEvaporator 每 50 章做 active settings O(S²) 相似合并，规模增大后可能产生尾延迟。
5. `ProjectRunState.accumulated_summary` 每章 join 全量 summary 并写回 DB，存在 O(N²) 字符串写放大。

## In Scope（必须完成）

- [ ] **减少重复上下文组装**
  - 若 Task 111f 已引入 `context_snapshot_id`，本 Task 应复用 snapshot，避免 Writer/Auditor 重复 DB/RAG 组装
  - 记录每章 context assembly 次数或在测试中用 mock 断言调用次数

- [ ] **控制 LiteraryAuditor 调用频率**
  - 保持 LiteraryAuditor 诊断定位
  - 优先改为最终候选 / QG 通过后 / best_version 路径执行
  - 或对同一 version_id 缓存 observation，避免重复 LLM
  - 不允许 LiteraryAuditor 重新成为自动修订阻断源

- [ ] **限制 SettlementExtractor prompt 事实源规模**
  - 只传本章相关角色状态，或按出现角色 / source quote / chapter goal 过滤
  - active settings 限制为正文命中、due、recent 或 top-N
  - foreshadowings 限制为 due/overdue/relevant/top-N
  - old_value 校验所需事实可在代码层按 update keys 查询，不必全量塞入 prompt

- [ ] **优化 SettingEvaporator 合并**
  - O(S²) merge 仅比较同 category / 同 source window / 最近变更 settings
  - 或使用 normalized key/token bucket 缩小候选集
  - 保持 merge 结果确定性，避免引入 LLM

- [ ] **减少 `accumulated_summary` 写放大**
  - `project_runs` 只保存 last chapter、最近 N 章摘要或摘要计数
  - 完整跨章摘要从 `summaries` 表或报告脚本聚合
  - 不破坏现有 run recovery 需要的最小状态

## Out of Scope（明确不做）

- 不做大型异步队列或分布式缓存
- 不引入新的向量数据库或外部服务
- 不改文学质量评分阈值
- 不执行 Ch101-Ch150 正式长跑；只做小窗口性能/调用次数验证

## 性能预算目标

| 项 | 目标 |
|----|------|
| ContextPackage 组装 | 每个 version 最多 1 次可解释组装；审查复用 snapshot |
| LiteraryAuditor LLM | 每个 accepted/final candidate 最多 1 次，或同 version 缓存 |
| Settlement prompt facts | 角色、设定、伏笔列表有明确上限或相关性过滤 |
| Setting merge | 避免全量 O(S²)，候选集有 bucket/window 限制 |
| project run summary | 每章写入量 O(1) 或 O(recent N)，避免 O(N²) 累积 |

## 关键测试标准

### Layer 1: 单元测试

- [ ] mock `assemble_context_package()`，确认 Writer/Auditor 不重复触发不必要组装
- [ ] LiteraryAuditor 对同一 `version_id` 不重复 LLM，或只在最终候选路径执行
- [ ] SettlementExtractor prompt builder 对 characters/settings/foreshadowings 执行 top-N 或相关性过滤
- [ ] SettingEvaporator merge 不对所有 active settings 做无条件两两比较
- [ ] `ProjectRunState.update_after_chapter()` 不再每章重建并持久化全量 accumulated summary

### Layer 2: 小窗口性能测试

- [ ] 构造 5-10 章 mock run，统计 context assembly 调用次数较基线下降
- [ ] 构造 100+ active settings，merge 候选比较次数小于全量 N²
- [ ] 构造大量 summaries，project run 更新耗时和写入 payload 不随总章数平方增长

### Layer 3: 回归测试

- [ ] `pytest tests/test_phase1_graph.py tests/test_context_manager.py tests/test_settlement_extractor.py -q`
- [ ] `pytest tests/test_setting_evaporator.py tests/test_eval_runner.py -q`（如存在对应测试）
- [ ] `pytest tests/ -q`
- [ ] 本次触及文件 `ruff check` 通过

## 验收标准（Acceptance Criteria）

- [ ] 长跑主链路不存在明显重复 context assembly
- [ ] LiteraryAuditor 不再对每个中间版本无条件增加 LLM 成本
- [ ] SettlementExtractor prompt 事实源有明确上限或相关性过滤
- [ ] SettingEvaporator 避免全量 O(S²) 默认路径
- [ ] `ProjectRunState.accumulated_summary` 不再造成 O(N²) 写放大
- [ ] 生成 `tasks/111g-long-run-performance-containment-DONE.md`
- [ ] 更新 `docs/STATUS.md`
- [ ] Git commit 包含代码、测试、DONE 文档和状态更新

## 参考证据

- `src/songyan/workflows/_nodes.py` — Writer/Auditor context 读取、LiteraryAuditor 路由、post-processing
- `src/songyan/agents/settlement_extractor/__init__.py`
- `src/songyan/agents/setting_evaporator/__init__.py`
- `src/songyan/workflows/phase2_graph.py`

## 下一 Task

**Task 112: Ch101-Ch150 流式验证 + 决策门 DG-2**
