# Task 064: LLM client/parsing + migrations 测试补充

> **Phase**: V3.x Layer 3 — 系统化质量守卫
> **优先级**: P2
> **依赖**: 无
> **预计工作量**: 中（1~2 天）

---

## Goal

为 `llm/client.py`、`llm/parsing.py`、`db/migrations.py` 补充独立测试，补齐 V2.x 遗留的测试缺口。

## Context

| 模块 | 现状 | 风险 |
|------|------|------|
| `llm/client.py` | 零独立测试 | 超时、rate limit、重试逻辑变更无保护 |
| `llm/parsing.py` | 零独立测试 | JSON 解析鲁棒性变更无保护 |
| `db/migrations.py` | 零幂等测试 | 增量迁移重复执行可能报错 |

## In Scope（必须完成）

- [ ] **`llm/client.py` >=3 个测试**:
  - 超时模拟 + 重试
  - rate limit 触发退避
  - 正常调用链路
- [ ] **`llm/parsing.py` >=4 个测试**:
  - 嵌套 JSON 解析
  - 尾部逗号容错
  - markdown 代码块包裹
  - 畸形输入（非 JSON 字符串）
- [ ] **`db/migrations.py` >=1 个测试**:
  - 重复执行 `init_schema()` 不报错
  - 幂等性验证

## Out of Scope（明确不做）

- 不做真实 LLM API 调用测试（用 Mock / monkeypatch）
- 不做多模型路由测试

## 验收标准

- [ ] llm client/parsing 新增测试 >=7 个
- [ ] migrations 幂等测试 >=1 个
- [ ] `pytest tests/ -k "llm or migration" -v` 全部通过
- [ ] `docs/STATUS.md` 更新
- [ ] 生成 `tasks/060-llm-tests-DONE.md`

## 参考文档

- `prd/v3.0-stability-closed-loop.md` — 7.1 测试补充
