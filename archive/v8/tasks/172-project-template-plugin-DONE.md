# Task 172：项目模板化与体裁可插拔 — DONE 报告

> **目标**: 建立 `ProjectTemplate` 模板层，让 CLI 和长跑 harness 可以通过 `--template` / `TEMPLATE_ID` 一键切换体裁，覆盖全部 7 个已有 genre，并支持轻量继承/变体。
>
> **实施计划**: `archive/superpowers/plans/2026-07-13-project-template-plugin-plan.md`

## 完成内容

| 子任务 | 内容 | 关键提交 |
|--------|------|----------|
| 172.1 | `ProjectTemplate` / `TemplateSeed*` 数据模型 + `project_templates/_schema.json` + 测试 | `e35a07c` |
| 172.2 | `ProjectTemplateLoader`（目录式模板、`evals/seeds` 兼容、循环继承检测）+ `_compat.py` + 测试 | `809e2e3` |
| 172.3 | `ProjectInitializer.from_template()` + 包入口导出 + 测试 | `73edd08` |
| 172.4 | 7 个体裁模板目录（scifi / xuanhuan / wuxia / urban / urban_fantasy / post_apocalyptic / mystery_noir）+ CLI `--template` + `scripts/run_171_ch200.py` `TEMPLATE_ID` 集成 | `bcf2f52` |
| 172.5 | 轻量继承/变体：`project_templates/xuanhuan/cultivation/` + 继承测试 | `2d3b296` |
| 172.6 | 多体裁短章验证脚本 `scripts/run_172_short_window.py` | `a3172b0` |
| 172.7 | ContextEmergency 下压缩 `CreativeBrief`，避免硬保留分区仍超预算 | `cb60d26` |
| 172.8 | SettlementExtractor 支持玄幻/武侠寿命/寿元/余寿读数 | `cb60d26` |

## 关键设计

- **B 为主，C 为补充**：目录式模板是主要形态（`project_templates/<genre/>`）；`extends` + `overwrite` 提供轻量变体能力。
- **兼容 evals/seeds**：`ProjectTemplateLoader` 同时扫描 `project_templates/` 和 `evals/seeds/*.json`，旧种子可平滑迁移。
- **CLI / harness 统一入口**：
  - CLI: `songyan create-project --template xuanhuan`
  - Harness: `TEMPLATE_ID=xuanhuan python scripts/run_171_ch200.py --init`
  - Short window: `python scripts/run_172_short_window.py --templates scifi xuanhuan --end 3`

## 验证结果

```bash
PYTHONPATH=src python -m pytest tests/test_project_template_models.py tests/test_project_template_loader.py tests/test_project_template_initializer.py tests/test_project_template_inheritance.py -q
# Expected: 18 passed

ruff check src/songyan/project_templates/ tests/test_project_template_*.py scripts/run_172_short_window.py
# Expected: All checks passed

mypy src/songyan/project_templates/ scripts/run_172_short_window.py
# Expected: Success
```

## 使用示例

```bash
# 列出模板
python -c "from songyan.project_templates import ProjectTemplateLoader; print(ProjectTemplateLoader().list_templates())"

# 用模板创建项目
songyan create-project --template xuanhuan

# 用模板初始化 Ch200-Ch250 harness
$env:TEMPLATE_ID = "xuanhuan"
python scripts/run_171_ch200.py --init
```

## 已知限制

- `ProjectInitializer.from_template()` 按现有 repository 模式顺序写入 DB，不是原子事务；与 Task 172 范围无关，不阻塞验收。
- 实际多体裁短章 LLM 验证（`scripts/run_172_short_window.py` 全量运行）消耗 API 预算，未在本次实现会话中执行；脚本已就绪，可在有预算的会话中运行。
