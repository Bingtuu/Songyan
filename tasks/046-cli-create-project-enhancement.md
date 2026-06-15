# Task 046 — CLI `create-project` 新增交互 + 自动推导 arc_boundaries

> **目标**: 让 `create-project` 收集 Phase 8a 新增的种子信息，并自动推导 arc_boundaries。
> **Phase**: 8a
> **优先级**: P0
> **依赖**: Task 045

---

## 新增交互步骤

在现有 `create-project` 流程后追加：

1. **预估总章数** — 默认 30，直接回车跳过
2. **每章目标字数** — 默认 3000
3. **故事结构** — 1.三幕式 2.五幕式 3.序列化连载 4.自由结构（默认 4）
4. **题材子类型** — 可选，基于 genre_id 动态列出 sub_genres

## 自动推导 arc_boundaries

如果 `story_structure != "free"` 且 `estimated_chapters` 已填写：

```python
derive_arc_boundaries("three_act", 40)  # → [10, 30]
derive_arc_boundaries("five_act", 50)   # → [10, 20, 30, 40]
derive_arc_boundaries("serial", 60)     # → [25, 50]
```

推导结果写入 `arc_boundaries`，并设置 `arc_boundaries_auto=True`。

## 验收标准

- [ ] 交互流程覆盖全部新增字段
- [ ] 故事结构非法输入有重试提示
- [ ] 无 sub_genres 时子类型步骤自动跳过
- [ ] 自动推导结果正确
- [ ] 自由结构不推导 arc_boundaries
- [ ] 测试通过（Click CliRunner 模拟交互）

---

## 已知限制

- `sub_genres` 当前 genre 配置中为空列表，CLI 会自动跳过子类型选择
- 自动推导的 arc_boundaries 可通过 `update_seed_config` 后续修改
