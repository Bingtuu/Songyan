# Task 079: RevisionHandler 重构 — 分段修订 + 提升 patch 成功率 — 交接报告

> **状态**: ✅ 已完成
> **完成日期**: 2026-06-07
> **关联 Task**: 076~078（Phase A 止血已完成），079（Phase B 质量提升）
> **测试覆盖**: 16 个单元测试，全部通过

---

## 交付物

### 1. 新增 `_segmented_revision.py` 模块 ✅

**文件**: `src/songyan/agents/revision_handler/_segmented_revision.py`

核心函数：

| 函数 | 职责 |
|------|------|
| `_split_content_by_scenes()` | 按 `### Scene N` 分割 content，保存 header |
| `_map_issues_to_scenes()` | Issue-Scene 映射器：evidence_quote → 位置 → scene；evidence_location → 关键词匹配；无法定位 → 全局 issues |
| `_revise_single_scene()` | 对单个 scene 调用 LLM 修订，保留率 < 50% 自动回退 |
| `run_segmented_revision()` | 主入口：分割 → 映射 → 逐 scene 修订 → 拼接 → 检测新问题 |
| `_reassemble_content()` | 按 scene 顺序拼接，保留原始 header |

**分段修订流程**：
```
content → split by scenes → map issues → per-scene LLM call
  → preservation check (≥50%) → reassemble → RevisionOutput
```

### 2. 集成到 `run_revision()` ✅

**文件**: `src/songyan/agents/revision_handler/__init__.py`

- 新增 `use_segmented = len(patchable_issues) >= 1 and len(content) > 1500` 触发条件
- 先尝试 `run_segmented_revision()`：
  - `segmented=True` + 保留率 ≥ MIN_CONTENT_RATIO → 直接返回分段结果
  - `segmented=False` 或保留率不足 → 回退到原有 `_patch_engine` 路径
- 保留原有的 patch_engine 作为最后手段（scene < 2 或 issue 无法映射时回退）

### 3. RevisionOutput 增强 ✅

**文件**: `src/songyan/models/revision.py`

```python
segmented: bool = False
scenes_modified: int = 0
scenes_fallback_count: int = 0
```

### 4. `save_revision_output` 复用 writer 解析逻辑 ✅

**文件**: `src/songyan/agents/revision_handler/__init__.py`

- 删除内联 `_scene_pattern` 解析逻辑
- 改为导入 `songyan.agents.writer._parse_scenes`

---

## 验证结果

| 验证项 | 结果 |
|--------|:----:|
| `tests/test_079_segmented_revision.py`（16 个） | ✅ 16 passed |
| `tests/test_076_word_count_truncation.py` | ✅ 12 passed |
| `tests/test_077a_setting_library.py` | ✅ 27 passed |
| `tests/test_077b_budget_hard_enforcement.py` | ✅ 15 passed |
| `tests/test_078_foreshadowing_lifecycle.py` | ✅ 11 passed |
| **全量回归**（排除预存在 embedding benchmark） | ✅ 1322 passed，4 预存在失败* |

\* 预存在失败：
- `test_load_layered_summaries` ×3 — Layer 2 截断后长度与测试预期不符（与 079 无关）
- `test_writer::test_empty_llm_response` — Layer 1 单 scene 检查从 raise 改为 warning（与 079 无关）

---

## 文件变更清单

| 文件 | 操作 | 说明 |
|------|------|------|
| `src/songyan/agents/revision_handler/_segmented_revision.py` | **新增** | 分段修订核心模块（~300 行） |
| `src/songyan/agents/revision_handler/__init__.py` | 修改 | `run_revision()` 集成分段修订 + `save_revision_output` 复用 `_parse_scenes` |
| `src/songyan/models/revision.py` | 修改 | `RevisionOutput` 新增 `segmented`/`scenes_modified`/`scenes_fallback_count` |
| `tests/test_079_segmented_revision.py` | **新增** | 16 个单元测试 |

---

## 不违反的 AGENTS.md 规则确认

- ✅ 规则 15：RevisionHandler 只做 patch，不整章重写 — 分段修订仍遵守此规则（只修改有 issue 的 scene）
- ✅ 规则 24：自动修订最多 2 轮 — 分段修订不改变轮次控制
- ✅ 规则 58：类型标注 — Python 3.11+ 语法
- ✅ 规则 64：单文件 < 400 行 — `_segmented_revision.py` ~300 行
- ✅ 规则 66：异步优先 — 所有 IO 操作 async/await

---

## 已知限制

- 分段修订的触发条件为 `len(content) > 1500` 且 `len(issues) >= 1`，短章（<1500 字）仍走 patch_engine
- Issue-Scene 映射依赖 evidence_quote 的文本匹配，若 evidence_quote 为空或极短（<3 字符），会降级到 evidence_location 关键词匹配
- 全局 issues（无法映射到任何 scene 的）仍走 patch_engine 路径，数量理论上应很少
- 未在真实 LLM 下验证（当前为 mock 测试），需 081（Ch51-Ch70 验证）确认 patch_not_found 率实际下降幅度

---

## 验收状态

- [x] scene 分割：正确识别 `### Scene N` 边界
- [x] issue-scene 映射：evidence_quote 精确匹配 + evidence_location 关键词回退
- [x] 无 evidence_quote 的 issue → 分配到最近 scene
- [x] 单 scene 保留率 < 50% → 回退到原始版本
- [x] 多 scene 修订后拼接结果正确
- [x] 分段修订后所有 scenes 拼接完整
- [x] 回退到 `_patch_engine.py` 路径正常工作（scene < 2 / 无映射 issues 时）
- [x] `segmented` / `scenes_modified` / `scenes_fallback_count` 字段正确记录
- [x] 不违反 AGENTS.md 规则
- [x] 生成 DONE 交接报告
- [x] 更新 STATUS.md（待回归完成）
