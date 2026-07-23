# Task 150: `_infer_setting_category` 收紧（critical 双命中 + 去硬编码主角名）— DONE

> **Phase**: V6 阶段 B（末端治理）
> **状态**: ✅ 完成
> **完成日期**: 2026-07-02

---

## 1. 实现内容

### 1.1 去硬编码主角名

- 删除 `_infer_setting_category` 中写死的 `"林渊"`。
- 新增 `protagonist_names: set[str] | None = None` 参数，由调用方从项目档案注入主角名 + 常见别名。

### 1.2 收紧 critical 第二命中条件

- `critical_keywords` 保持为：
  `["主角", "protagonist", "main", "命格", "天赋", "血脉", "传承"]`。
- 第二命中条件从过泛的通用代词（他/她/能力/状态/命运/目标）改为**主角名/别名**或明确的保守回退词集。
- 当 `protagonist_names` 非空时，要求同时命中 critical_keywords **且** 命中 `protagonist_names` 中的具体名称，才判为 `critical`。
- 当 `protagonist_names` 为 `None` 或空集时，回退到不含通用代词的保守集合：
  `{"主角", "主人公", "protagonist", "命定之人", "全书核心"}`。

### 1.3 项目主角名加载

- 在 `_update_continuity_tracking` 中通过 `ProjectRepository().get(project_id)` 读取项目配置。
- 新增 `_build_protagonist_names(project)`：
  - 若项目存在且 `protagonist_name` 非空，返回 `{name, name[:2]}`（2 字名时两者重复，集合自然去重）。
  - 否则返回保守回退词集。

### 1.4 保持其他分类不变

- `technical` 仍优先判定。
- `historical` 判定逻辑不变。
- 默认值仍为 `background`。
- 未新增/删除 category 取值，未改动 CHECK 约束。

---

## 2. 文件变更

| 文件 | 变更 |
|------|------|
| `src/songyan/agents/settlement_extractor/_apply.py` | 重写 `_infer_setting_category`；新增 `_build_protagonist_names`；`_update_continuity_tracking` 加载项目主角名并传入分类器 |
| `tests/test_settlement_extractor.py` | 更新 `TestInferSettingCategory` 辅助方法以支持 `protagonist_names`；修正血脉测试用例 |
| `tests/test_150_infer_category_tightening.py` | 新增 11 个单测，覆盖收紧规则、去硬编码、138m 命中率、回退策略、technical/historical 不变性、项目加载集成 |
| `archive/v6/tasks/150-infer-category-tightening-DONE.md` | 本文件 |
| `tasks/V6-README.md` | Task 150 状态更新为 ✅ 完成 |
| `docs/STATUS.md` | 当前优先级更新：Task 150 已完成，下一步 Task 151 |

---

## 3. 测试结果

```powershell
python -m pytest tests/test_150_infer_category_tightening.py -v
# 11 passed

python -m pytest tests/test_149_input_side_demotion.py -v
# 8 passed

python -m pytest tests/test_settlement_extractor.py::TestInferSettingCategory -v
# 6 passed

ruff check src/ tests/
# All checks passed
```

全量回归（排除 evals/cli 后）也全部通过：

```powershell
python -m pytest tests/ -q --ignore=tests/integration --ignore=tests/rag --ignore=tests/evals --ignore=tests/cli
# 2048 passed, 1 xfailed, 1 warning

python -m pytest tests/integration tests/rag -q
# 70 passed, 2 skipped, 1 warning
```

---

## 4. 命中率证据

### 4.1 138m 误判样本

构造 22 个代表性世界观细节样本（同时命中旧代码的 `critical_keywords` 与过泛通用代词 `他/她/能力/状态/命运/目标`），旧代码会全部判为 `critical`：

- **提供主角名 `{"林渊"}` 时**：22/22 不再判为 `critical`（≥20/22 达标）。
- **`protagonist_names=None` 回退时**：15/22 不再判为 `critical`（≥15/22 达标）。

### 4.2 真 critical 不漏

主角名 + 命格/血脉/传承类设定在提供主角名时仍稳定判为 `critical`。

### 4.3 去硬编码验证

当项目主角为 `"萧炎"` 时，仅含 `"林渊"` 的设定不再被判为 `critical`。

---

## 5. 回退策略

- 无主角信息（`protagonist_names=None` 或项目无 `protagonist_name`）时，第二命中条件回退到：
  `{"主角", "主人公", "protagonist", "命定之人", "全书核心"}`。
- 该回退集合**不含**通用代词（他/她/能力/状态/命运/目标），因此比旧代码显著减少误判。
- 无主角档案项目行为可回退，且不劣于现状（138m 样本中 ≥15/22 不再误判）。

---

## 6. 设计约束遵守情况

- [x] 未新增 LLM 调用或 Agent。
- [x] 五类 category（technical/critical/recurring/background/historical）取值未变。
- [x] 分类函数仍是确定性关键词规则。
- [x] 所有函数带类型标注。
- [x] 使用 structlog 日志（已有）。

---

## 7. 后续衔接

- Task 150 收口后，阶段 B 剩余 Task 151（MR 上限自适应 + 相关性排序）与 Task 152（critical 显式 resolve/作废出口）。
- 本改动与 Task 149 录入侧降级正交，可共同降低 critical orphan 产生速率。
