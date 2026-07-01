# Task 111f DONE: Context Snapshot、Prompt 与 Metadata 一致性修复

> **完成日期**: 2026-06-19
> **状态**: ✅ 已完成
> **提交范围**: ContextSnapshot 持久化 / Writer-Auditor 上下文复用 / generation_metadata 回放字段

---

## 完成内容

1. **新增轻量 ContextSnapshot**
   - 新增 `ContextSnapshot` Pydantic 模型。
   - 新增 SQLite `context_snapshots` 表与迁移。
   - 新增 `ContextSnapshotRepository`，集中处理 snapshot 写入与读取。
   - LangGraph state 只保存 `context_snapshot_id`，不保存完整 `ContextPackage`。

2. **统一 Writer/Auditor 上下文来源**
   - `context_manager_node()` 组装裁剪后 `ContextPackage` 后立即写入 snapshot。
   - `_get_context_package()` 优先按 `context_snapshot_id` 读取同一份 snapshot。
   - Writer、LLMAuditor、LiteraryAuditor 复用 ContextManager 的上下文快照。
   - snapshot 缺失时返回明确错误，不静默重新组装导致字段丢失。

3. **保留 human instruction 与 CreativeBrief 动态字段**
   - ContextManager 组装时继续注入 `human_instructions`。
   - snapshot payload 保留 `narrative_fullness`、`character_focus`、`foreshadowing_due`、`focal_distance` 等 CreativeBrief 派生字段。
   - human instruction 兼容旧 `type` 字段与新 `action` 字段渲染。

4. **补齐 generation_metadata 回放信息**
   - `write_chapter()` 新增 `context_snapshot_id` 参数。
   - `generation_metadata` 写入 `context_snapshot_id`。
   - `generation_metadata` 写入精简 `creative_brief_snapshot`。
   - 保留原有 `creative_brief_id` 外键与轻量 `context_snapshot` 指标。

5. **补充防回归测试**
   - 覆盖 ContextManager 返回 snapshot ID 且不返回完整 context package。
   - 覆盖 `_get_context_package()` 通过 snapshot 读取 human instruction。
   - 覆盖 LLMAuditor 与 LiteraryAuditor 复用同一 snapshot。
   - 覆盖 Writer prompt 渲染 `action` 字段。
   - 覆盖 Writer metadata 中的 `context_snapshot_id` 与 `creative_brief_snapshot`。

---

## 修改文件

- `src/songyan/agents/writer.py`
- `src/songyan/db/migrations.py`
- `src/songyan/db/repository.py`
- `src/songyan/db/schema.sql`
- `src/songyan/models/__init__.py`
- `src/songyan/models/context.py`
- `src/songyan/workflows/_nodes.py`
- `src/songyan/workflows/phase1_graph.py`
- `tests/test_phase1_graph.py`
- `tests/test_writer.py`
- `docs/STATUS.md`
- `tasks/111f-context-snapshot-prompt-metadata-fix-DONE.md`

---

## 验证结果

```bash
pytest tests/test_phase1_graph.py tests/test_writer.py tests/test_context_manager.py -q
```

结果：`160 passed`

```bash
pytest tests/test_prompt_loader.py tests/test_rule_auditor.py -q
```

结果：`54 passed`

```bash
pytest tests/db/test_migrations.py tests/db/test_schema.py -q
```

结果：`21 passed`

```bash
pytest tests/ -v
```

结果：`1649 passed, 4 skipped, 1 xfailed, 4 xpassed, 10 warnings`

```bash
python -m pytest tests/ -q
```

结果：`1649 passed, 4 skipped, 2 xfailed, 3 xpassed, 10 warnings`

```bash
ruff check src/songyan/agents/writer.py src/songyan/db/migrations.py src/songyan/db/repository.py src/songyan/models/__init__.py src/songyan/models/context.py src/songyan/workflows/_nodes.py src/songyan/workflows/phase1_graph.py tests/test_phase1_graph.py tests/test_writer.py
```

结果：`All checks passed!`

```bash
ruff check src/ tests/
```

结果：失败，仍为历史 lint 存量 `116 errors`，集中在未触及测试文件的 E501/F841；本 Task touched files 的 ruff 已通过。

---

## 已知限制

- snapshot payload 保存的是裁剪后的 prompt/audit 输入，不是完整业务对象缓存；ContextManager DB 查询性能优化仍留给 Task 111g。
- rewrite 路径会基于 rewrite 后上下文写入新的 snapshot，避免复用初稿版本的 prompt 输入。
- 全量 ruff 仍有历史存量，本 Task 未扩大范围清理无关测试文件。

---

## 下一步

进入 **Task 111g: 长跑性能缺陷收敛**。
