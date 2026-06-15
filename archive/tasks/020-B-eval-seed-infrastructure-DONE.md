# Task 020-B 交接报告：评测集基础设施（Runner + 种子项目）

> **Phase**: Phase 4 — 评测与优化
> **状态**: ✅ 完成
> **日期**: 2026-05-27
> **测试增量**: +6（634 → 641 total，不含性能测试）

---

## 做了什么

构建了可重复运行的评测基础设施，实现 `evals/runner.py` 评测运行器，准备 3 个预置种子项目配置和人工种子章节。

### 新增文件

| 文件 | 说明 |
|------|------|
| `evals/__init__.py` | 包入口 |
| `evals/models.py` | SeedProjectConfig / SeedCharacter / SeedSetting / SeedNumericalSystem / EvaluationResult |
| `evals/runner.py` | `import_seed_project()` / `import_seed_chapter()` / `run_seed_project()` / `_import_seed_character_states()` |
| `evals/__main__.py` | CLI 入口 `python -m evals` |
| `evals/seeds/xuanhuan_webnovel.json` | P0 — 玄幻 + 网文，4 角色 + 10 设定 + 数值体系 |
| `evals/seeds/urban_hybrid.json` | P1 — 都市 + 混合，3 角色 + 5 设定 |
| `evals/seeds/scifi_webnovel.json` | P1 — 科幻 + 网文，3 角色 + 5 设定 |
| `evals/seeds/chapters/xuanhuan_ch1.md` | 人工种子 Chapter 1（~2400 字） |
| `evals/seeds/chapters/urban_ch1.md` | 人工种子 Chapter 1（~800 字） |
| `evals/seeds/chapters/scifi_ch1.md` | 人工种子 Chapter 1（~900 字） |
| `tests/test_eval_runner.py` | 6 个测试：导入 2 + 种子章节 1 + runner 集成 3 |

### 关键技术决策

1. **character_states 外键约束**：`character_states.source_version_id` 必须引用 `chapter_versions.version_id`。因此 `import_seed_project` 不直接写入 character_states，而是在 `import_seed_chapter` 返回真实 version_id 后，由 `_import_seed_character_states()` 补充写入。
2. **种子章节 summary**：`import_seed_chapter` 自动生成简易 ChapterSummary 并写入 `summaries` 表，确保 Chapter 2 的 goal_planner / context_manager 能读取到前置摘要。
3. **NumericalLedger 初始化**：玄幻项目的数值体系在 `import_seed_project` 阶段为每个角色创建初始 ledger（chapter_number=0）。

---

## 验证命令

```bash
# 评测 runner 测试
pytest tests/test_eval_runner.py -v
# Expected: 6 passed

# CLI 帮助
python -m evals --help

# 单种子项目 mock 评测
python -m evals --seed-config evals/seeds/xuanhuan_webnovel.json \
                --seed-chapter evals/seeds/chapters/xuanhuan_ch1.md \
                --output-dir evals/output/test_run \
                --auto-accept
```

---

## 已知限制

- 种子章节为人工撰写，未经过真实 LLM 生成验证
- 种子 2/3（urban/scifi）为简化版，角色和设定数量较少
- 评测仅覆盖单章闭环（Chapter 1 → Chapter 2），未验证连续多章

---

## 下游依赖

- **020-C**: 验收指标收集 + 性能测试 + 文档收尾
