# Task 134: SettlementExtractor 角色状态与数值台账提取修复 — DONE

> **状态**: 已完成  
> **日期**: 2026-06-27  
> **前置**: Task 111b、Task 129  

---

## 问题

Task 129 enforce 模式验证（`run-89d7a2d4`）显示：即使 settlement 成功应用的章节，`character_states` 与 `numerical_ledgers` 记录数仍为 0。Root cause 是 SettlementExtractor prompt 在 `current_character_states` 为空时未给 LLM 提供角色基线档案，导致 LLM 将 `character_updates` / `numerical_updates` 输出为空数组；同时 parser 对缺失字段静默丢弃，未触发 review。

---

## 修复内容

| 文件 | 改动 |
|------|------|
| `prompts/cards/settlement_extractor/1.0.2.yaml` | 新增 prompt 版本：强制提取主角状态与数值变化，提供角色基线档案，增加 `formula` 字段示例，声明主角出场时 `character_updates` 与 `numerical_updates` 不允许同时为空 |
| `prompts/cards/settlement_extractor/_manifest.yaml` | `default_version` 升级为 `1.0.2` |
| `src/songyan/agents/settlement_extractor/__init__.py` | 加载 `CharacterRepository` 角色档案并渲染为 `character_profiles`；`_render_prompt` 增加 `characters` 参数；parser 对缺失 `character_id`/`field`、`character_id`/`attribute_name` 等关键字段显式记录 warning |
| `src/songyan/models/settlement.py` | `NumericalUpdate` 增加可选 `formula: str = ""` 字段，注释从“玄幻专用”改为“所有题材通用” |
| `src/songyan/workflows/_nodes.py` | enforce 模式下，若 settlement 有效但 `character_updates` 与 `numerical_updates` 同时为空、正文长度充足且项目存在角色档案，则阻断 accept 并进入 `settlement_review`；observe 模式保持 warning 不阻断 |

---

## 新增测试

- `tests/test_settlement_extractor_task134.py`（12 个测试）
  - 角色基线档案渲染与 prompt 注入
  - parser 缺失字段返回 None 且不静默通过
  - `formula` 字段解析保留
  - enforce 空结算阻断、observe 空结算放行、短内容放行

---

## 验证

- `ruff check src/ tests/` ✅
- 目标测试：`tests/test_settlement_extractor.py`、`tests/test_settlement_extractor_task134.py`、`tests/test_prompt_loader.py` ✅
- 全量 `pytest tests/`：`1892 passed, 2 skipped, 1 xfailed` ✅

---

## 交付物

- 本 `-DONE.md` 文件
- SettlementExtractor 1.0.2 prompt 与相关代码改动
- `tests/test_settlement_extractor_task134.py`
