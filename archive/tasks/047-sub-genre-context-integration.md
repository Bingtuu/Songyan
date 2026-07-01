# Task 047 — GenreProfile.sub_genres 注入 ContextManager

> **目标**: ContextManager 在组装上下文时，将 `sub_genre_id` 对应的子类型规则注入 GenreRules。
> **Phase**: 8a
> **优先级**: P1
> **依赖**: Task 045

---

## 实现要点

1. `GenreRules` 新增 `sub_genre_rules: list[str]` 字段
2. `_build_genre_rules()` 接收 `project: ProjectSetting`，匹配 `sub_genre_id`
3. 匹配成功则将 `SubGenre.differentiation_rules` 追加到 `GenreRules.sub_genre_rules`
4. `assemble_context_package()` 调用处更新参数

## 验收标准

- [ ] `GenreRules` 模型包含 `sub_genre_rules` 字段
- [ ] 无 `sub_genre_id` 时 `sub_genre_rules` 为空列表
- [ ] `sub_genre_id` 匹配成功时 `differentiation_rules` 注入
- [ ] `sub_genre_id` 不匹配时 `sub_genre_rules` 为空列表（不报错）
- [ ] 测试通过，无回归
