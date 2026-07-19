# Task 177 DONE: songyan export 正文导出

> **阶段**: V9.2 交付与发布
> **完成日期**: 2026-07-19
> **状态**: ✅ 完成

## 交付内容

- 新增正式导出 service：`src/songyan/services/export_service.py`。
- 新增 CLI：`songyan export --project-id <id> [--format md|txt] [--by flat|arc|volume] [--chapters a-b] [--output <dir>]`。
- 新增聚焦测试：`tests/test_177_export_service.py`，覆盖 accepted head 取数、flat/txt 渲染、arc/volume 分组、Windows 文件名安全、无效/重叠/空分组、重复导出不清理旧文件、Click 接线与非法章节范围。

## 行为口径

- 导出只读 SQLite accepted head：`chapter_heads.status='accepted'` + `accepted_version_id` → `chapter_versions.content`。
- 导出不主动 `init_schema()`，不会自动迁移 `DATABASE_URL` 指向的历史源库；schema 缺失时给出可读错误。
- 导出器不主动插入 `version_id`、评分、字数统计、run metadata 或历史 `_export_prose()` 的 `---` 分隔线。
- 正文原文不改写；若源正文自带 `---`，导出结果保留。
- accepted head 指向版本缺失或不匹配时跳过该章并记录 warning；CLI 在 skipped 非零时输出跳过章数。
- 无效分组（如 `(0,0)` 卷占位）warning 后忽略；重叠分组 first-match + warning；未覆盖章节归入 `arc-00-未分弧` / `volume-00-未分卷`。
- 重复导出只覆盖同名文件，不清理输出目录旧文件。

## 验证

- `python -m pytest tests/test_177_export_service.py -q` → **15 passed**（含 review follow-up：不自动迁移源库 + skipped CLI 输出）。
- `powershell -NoProfile -File scripts\run_with_timeout.ps1 -TimeoutSec 1200 -DetectPytestSummary -- python -m pytest tests/ -q` → **2897 passed, 2 skipped, 1 xfailed, 7 warnings**；`WRAPPER_RESULT=PASS_NORMAL_EXIT`。
- `ruff check src/ tests/` → **All checks passed**。
- xuanhuan Ch100 arc 导出：100 章 / 4 个 arc 文件。
- wuxia Ch100 flat 导出：100 章 / 1 个 flat 文件。
- xuanhuan volume 补验：忽略 `(0,0)` 占位，100 章 / 2 个 volume 文件。
- xuanhuan Ch1/50/100 与 wuxia Ch1/50/100 导出正文段 hash 均与 DB `chapter_versions.content` 一致。

## 证据路径

- 任务书与执行记录：`tasks/177-export-book-manuscript.md`
- xuanhuan arc 输出：`.tmp/177_export_check/xuanhuan_arc/`
- wuxia flat 输出：`.tmp/177_export_check/wuxia_flat/`
- xuanhuan volume 输出：`.tmp/177_export_check/xuanhuan_volume/`
