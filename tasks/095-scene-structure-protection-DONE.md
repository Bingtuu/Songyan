# Task 095: 场景结构保护 + RevisionHandler 增强 — 交接报告

> **状态**: ✅ 已完成
> **完成日期**: 2026-06-10
> **测试通过**: `pytest -q` — 1434 passed, 6 skipped, 0 failed

---

## 修改概览

| 文件 | 修改类型 | 说明 |
|------|---------|------|
| `src/songyan/agents/writer.py` | 修改 | `_enforce_word_count` 增加 `min_scenes=2` 参数，截断不得破坏最小场景数 |
| `src/songyan/workflows/_nodes.py` | 修改 | `rewrite_node` 注入场景结构约束（至少 2 场景 + 单场景 ≤60%） |
| `src/songyan/workflows/review_merger.py` | 修改 | `_convert_rule_to_issues` 增加场景结构 issue 转换（单场景 major / 过多 minor） |
| `src/songyan/agents/revision_handler/__init__.py` | 修改 | `run_revision` 增加 scene_split / scene_merge 策略选择 + 2 个新处理函数 |
| `tests/test_writer.py` | 新增 | Task 095 截断保留 min_scenes 测试（3 个用例） |
| `tests/test_review_merger.py` | 新增 | 场景结构 issue 转换测试（3 个用例） |
| `tests/test_revision_handler.py` | 新增 | scene_split / scene_merge 策略测试（4 个用例） |
| `tests/test_076_word_count_truncation.py` | 修改 | 更新测试数据以兼容 min_scenes=2（5 个用例调整） |
| `tests/test_rewrite_node.py` | 修改 | 更新断言以匹配新增的场景结构约束注入 |
| `docs/STATUS.md` | 修改 | 标记 Task 095 为完成 |

---

## 关键设计决策

### 1. Writer 截断保护（min_scenes=2）

- `_enforce_word_count` 新增 `min_scenes: int = 2` 参数
- 所有截断路径检查 `len(scenes_after_cut) >= min_scenes`
- 当截断会破坏结构（只剩 1 场景）时返回原内容 + `truncation_would_destroy_structure`
- 兼容旧调用方（默认值自动生效）

### 2. Rewrite 场景约束注入

在原有字数约束基础上，追加：
```
【场景结构约束】本章必须包含至少 2 个场景，推荐 3 个。
每个场景字数不得超过总字数的 60%。
场景之间应有清晰的叙事转折或时空切换。
```

### 3. RevisionHandler 策略选择

**触发条件**（需同时满足）：
- `scene_count < 2` **且** `report` 中存在 `NARRATIVE_PACING` + `major/critical` + 含"场景"的 issue → `scene_split`
- `word_count > target * 1.4` **且** `scenes_count > 3` **且** 同上 → `scene_merge`

**不无条件触发**：避免测试中/简单内容被误触发。

### 4. ReviewMerger 场景 Issue 转换

- `scene_count == 1` → `severity="major"`, `fix_type="rewrite_scene"`
- `scene_count >= 5` → `severity="minor"`, `fix_type="patch"`

---

## 测试覆盖

### 新增测试（10 个）

| 测试类 | 文件 | 数量 |
|--------|------|------|
| `TestEnforceWordCountMinScenes` | `tests/test_writer.py` | 3 |
| `TestSceneStructureIssues` | `tests/test_review_merger.py` | 3 |
| `TestSceneSplitStrategy` | `tests/test_revision_handler.py` | 2 |
| `TestSceneMergeStrategy` | `tests/test_revision_handler.py` | 2 |

### 修改测试（6 个）

| 测试类 | 文件 | 数量 |
|--------|------|------|
| `TestTruncationMultiScene` | `tests/test_076_word_count_truncation.py` | 3 |
| `TestSceneReParse` | `tests/test_076_word_count_truncation.py` | 2 |
| `TestRewriteNode` | `tests/test_rewrite_node.py` | 1 |

---

## 验证结果

```bash
$ pytest -q
1434 passed, 6 skipped, 20 warnings in 274.78s
```

无回归，无失败。

---

## 已知限制

1. **scene_split / scene_merge 依赖 LLM**：策略函数调用 LLM 进行场景拆分/合并，输出质量受模型能力限制
2. **触发条件较保守**：只有在 review_merger 明确生成场景结构 issue 时才触发，避免误伤
3. **未做端到端 Ch1-Ch10 验证**：当前为单元/集成测试覆盖，完整端到端验证需在 Task 096 回归时进行

---

## 下一步

- **Task 096**: Ch2-Ch50 回归验证（达标率 > 75%，health ≥ 3.5，0 失败）
