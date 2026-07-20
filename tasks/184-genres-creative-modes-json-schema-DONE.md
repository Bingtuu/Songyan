# Task 184 DONE: genres/creative_modes JSON Schema

> 完成日期：2026-07-20
> 阶段：V9.3 爬坡工具链
> 对应任务书：`tasks/184-genres-creative-modes-json-schema.md`

## 结论

Task 184 已完成。`genres/data` 与 `creative_modes/data` 已拥有正式 `_schema.json`，loader 在 JSON parse 后、Pydantic 实例化前执行 schema 校验。7 个 genre JSON 与 4 个 creative mode JSON 全部通过校验，坏字段、错类型、坏枚举会 fail fast，且错误信息包含资源与 JSON path。

## 变更范围

- `src/songyan/genres/data/_schema.json`
  - 约束 `GenreProfile` 资源结构、审查维度枚举、感官枚举、嵌套对象和数值范围。
- `src/songyan/creative_modes/data/_schema.json`
  - 约束 `CreativeModeProfile` 资源结构、revision/context/RAG 枚举与 human memory。
  - 显式允许现有历史兼容字段 `punch_engine`，不改变模型消费行为。
- `src/songyan/utils/json_schema.py`
  - 基于 `jsonschema.Draft7Validator` 的通用资源校验 helper。
  - 兼容 `Traversable` 包资源读取。
- `src/songyan/genres/loader.py`
  - 加载前 schema 校验。
  - `list_genre_profiles()` 排除 `_*.json` 元文件。
- `src/songyan/creative_modes/registry.py`
  - 加载前 schema 校验。
  - `list_creative_mode_profiles()` 排除 `_*.json` 元文件。
- `pyproject.toml`
  - 新增 runtime dependency `jsonschema>=4.0`。
- `tests/test_184_resource_json_schema.py`
  - 9 个聚焦测试覆盖 package data、生产资源、坏样本、列表污染与兼容字段。
- `tests/test_178_resource_loading.py`
  - 更新资源枚举断言，区分业务 JSON 与 `_schema.json` 元文件。

## 验收结果

| 项 | 结果 |
|---|---|
| 7+4 生产资源 | 全部通过 schema + Pydantic loader |
| 坏样本 | unknown field / wrong type / invalid enum 均被拒 |
| `_schema` 列表污染 | `list_genre_profiles()` / `list_creative_mode_profiles()` 不返回 `_schema` |
| `punch_engine` 兼容 | `webnovel_intense` 正常加载 |
| 聚焦测试 | `86 passed` |
| CLI 测试 | `35 passed` |
| 全量默认 pytest | `2930 passed, 2 skipped, 1 xfailed, 7 warnings`；`WRAPPER_RESULT=PASS_NORMAL_EXIT` |
| mypy | `Success: no issues found in 176 source files` |
| Ruff | All checks passed |
| Code review | 1 个 P2，已修复并补测 |

## 备注

- 本任务未改变 `GenreProfile` / `CreativeModeProfile` Pydantic 模型语义。
- 本任务未改变 `GenreRuntimeProfile` / DB override / Task 183 Profile CLI 语义。
- `_schema.json` 位于 `data/` 目录下，受 `.gitignore` 的 `data/` 规则影响，提交时必须强制纳入跟踪。
