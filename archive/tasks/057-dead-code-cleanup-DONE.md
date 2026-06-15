# Task 057: 死代码清理 — DONE

> **Phase**: V3.0 Layer 1 — 消解代码结构债
> **优先级**: P2
> **完成时间**: 2026-06-04
> **Git Commit**: `a5c55de`

---

## 完成内容

### 1. 删除 GenreProfileLoader 包装类

`src/songyan/genres/loader.py:120-136` 的 `GenreProfileLoader` 是一个纯代理类，所有方法都是对同级独立函数的委托，业务代码中无引用。

**操作**:
- 删除 `GenreProfileLoader` 类定义
- 更新 `src/songyan/genres/__init__.py`，移除 `GenreProfileLoader` 导出
- 更新 3 个测试文件，使用底层函数替代:
  - `tests/genres/test_loader.py`: 删除 `TestGenreProfileLoader` 测试类
  - `tests/genres/test_new_genre_configs.py`: `list_genre_profiles()` 替代 `GenreProfileLoader.list_genres()`
  - `tests/genres/test_genre_profile_upgrade.py`: `load_genre_profile("scifi")` 替代 `GenreProfileLoader.load("scifi")`

**验证**:
```bash
rg "GenreProfileLoader" src/ tests/ --type py
# （返回空）
```

### 2. 评估冗余 isinstance 守卫

`agents/goal_planner.py` 中 `_build_chapter_goal` 的 `isinstance` 守卫经测试验证**不是冗余**:

- 测试 `test_invalid_field_types_fallback` 明确验证了非标准输入的回退行为
- `word_count_target="not a number"` 需要显式 `int()` 转换 + 异常回退
- `target_events="不是列表"` 需要回退到 `[]`（Pydantic 不会自动处理字符串→list 的失败场景）
- `emotional_arc=123` 需要回退到 `""`

**决策**: 保留所有守卫，未做删除。

### 3. 评估 retry.py 异常类型

`src/songyan/llm/retry.py` 已使用明确的异常列表:
```python
retryable_exceptions: tuple[type[Exception], ...] = (LLMError, TimeoutError, ConnectionError)
```

调用者 `llm/client.py` 进一步缩小为 `(LLMError,)`。**无需修改**。

### 4. TODO/FIXME 扫描

全项目扫描结果:

| 位置 | 内容 | 评估 | 操作 |
|------|------|------|------|
| `workflows/phase2_graph.py:69` | Phase1Graph 外部配置 max_revision_rounds | 仍有效 | 记录到 backlog |
| `workflows/phase2_graph.py:218` | Task 025 精确成本追踪 | 仍有效 | 记录到 backlog |

过时的 TODO: 无

已创建 `docs/review/v3_todo_backlog.md` 记录有效 TODO。

---

## 验证结果

### 测试

```bash
pytest tests/ --ignore=tests/integration -q
# 1071 passed, 4 failed, 10 warnings
```

- **1071 passed** — 核心路径全部通过
- **4 failed** — 均为 `test_eval_runner.py` 的既有 pydantic 校验问题，与本次清理无关
- **genre 测试** — 152 passed（含删除后的 loader 测试）

### 兼容性检查

- [x] `rg "GenreProfileLoader" src/ tests/` 返回空
- [x] 公共 API 不变（`load_genre_profile`、`list_genre_profiles` 等仍在）
- [x] 被删代码的替代测试通过

---

## 已知限制

- `goal_planner.py` 的 `isinstance` 守卫经测试验证为必要，保留未删
- `retry.py` 已使用明确异常列表，无需修改

---

## 交接检查清单

- [x] 删除清单全部执行
- [x] 被删代码有测试覆盖的测试保持通过
- [x] 更新了 docs/STATUS.md
- [x] 生成了 tasks/057-dead-code-cleanup-DONE.md
- [x] git commit 提交

---

> **松烟入墨，字句成锋。**
> Layer 1 全部完成（056 + 057）。
