# Task 052: RevisionHandler 正文结构保护验证

> **Phase**: V3.0 Layer 0 — 修复稳定性底线
> **优先级**: P0
> **依赖**: 无（V3.0 首个 Task）
> **预计工作量**: 小（1 天）

---

## Goal

验证 RevisionHandler 的截断保护逻辑在真实场景下有效，确保 LLM 返回不完整正文时系统能正确回退或 fallback。

## Context

V2.x 末期发现 Ch12 在 Revision 后从 4045 字被截断到 991 字。代码层已添加 `MIN_CONTENT_RATIO=0.5` 保护，Prompt 已强化，但**从未在真实章节上验证修复有效**。本 Task 是 V3.0 的 P0 入口——如果这一层保护不可靠，后续 30 章运行的每一轮 revision 都有数据丢失风险。

## In Scope（必须完成）

- [ ] **单元测试增强**: 模拟 LLM 返回仅含 patch 片段的响应（content 字段远短于原文），验证 Fallback 逻辑触发
  - `test_truncated_content_fallback_to_patches`（已存在，确认通过）
  - `test_truncated_content_revert_to_original`（已存在，确认通过）
  - **新增**: `test_content_preservation_ratio_logged` — 验证每次 revision 后日志记录 `content_preservation_ratio`
- [ ] **真实验证**: 在 Ch12 或新 seed 上运行一轮 revision，确认 `content_preservation_ratio >= 0.7`
- [ ] **监控钩子**: 在 `run_revision()` 输出中显式返回 `content_preservation_ratio`，供 Layer 2 的 30 章监控采集

## Out of Scope（明确不做）

- 不修改 RevisionHandler 的核心 patch 逻辑
- 不调整 `MIN_CONTENT_RATIO` 阈值（保持 0.5）
- 不解决 revision 反弹率问题（属于 Prompt 调优，非稳定性）

## 接口契约

```python
# RevisionOutput 新增字段
class RevisionOutput(BaseModel):
    # ... 现有字段 ...
    content_preservation_ratio: float = Field(default=1.0, ge=0.0, le=1.0)
```

## 测试要求

### Layer 1: 模型测试
- [ ] `RevisionOutput` 可正确序列化/反序列化，含新增字段

### Layer 2: 模块测试
- [ ] `test_content_preservation_ratio_logged`: Mock LLM 返回截断响应，验证 ratio 计算正确
- [ ] `test_content_preservation_ratio_normal`: Mock LLM 返回正常响应，验证 ratio = 1.0

### Layer 3: 集成验证
- [ ] 在已有项目数据上运行 `run_revision()`，记录 ratio，确认 >= 0.7

## 验收标准

- [ ] `pytest tests/test_revision_handler.py -v` 全部通过（含新增测试）
- [ ] 真实章节验证通过，`content_preservation_ratio >= 0.7`
- [ ] `docs/STATUS.md` 更新（052 状态 → ✅）
- [ ] 生成 `tasks/052-revision-handler-protection-DONE.md`

## 参考文档

- `prd/v3.0-stability-closed-loop.md` — 4.1 P0-1
- `docs/review/merge_task054_ch10_plus.md` — Task 054 验证记录
