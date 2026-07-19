# Task 177: songyan export 正文导出

> **阶段**: V9.2 交付与发布
> **类型**: 功能（交付链最后一公里）
> **优先级**: P0（V9-README 审计 P0 ③：写完 100 章拿不到书稿——无 export 命令，8+ 任务脚本各复制一份 `_export_prose()`）
> **依赖**: 无（只读功能；174 日志、175 成本不影响）
> **状态**: ◻ 规划中
> **来源**: V9 生产就绪度审计；`tasks/V9-README.md` Task 177 行

---

## 背景

- 正文只存于 `chapter_versions.content`（SQLite），**没有任何导出命令**：写完 100 章的用户拿不到书稿。
- 8+ 个任务脚本（`scripts/run_170b_readability_assessment.py:188` 等）各自复制粘贴 `_export_prose()`：格式为 `# 标题` + 逐章 `## 第 N 章（X 字）` + 正文 + `---`，绑定各自任务的硬编码路径。**本 Task 的"收编" = 把该模式提升为正式 service + CLI；历史任务脚本不改动**（任务产物，不在生产路径）。
- 分组元数据现成：`arc_summaries`（`start_chapter/end_chapter/arc_title`，schema.sql:397）、`volume_summaries`（同构，:415）。
- 验收数据现成：`.tmp/task172b_xuanhuan_ch100.db` / `.tmp/task172b_wuxia_ch100.db`（V8 双体裁 Ch100 库）。

## 目标

1. `songyan export --project-id <id>` 产出**纯净书稿**：accepted head 正文，按章序，无版本元数据（version_id/评分/字数统计不进正文）。
2. 支持 `--format md|txt` 与 `--by flat|arc|volume` 分组、`--chapters a-b` 范围过滤、`--output <dir>`。
3. 渲染逻辑为可单测纯函数（参照 175 `cost_report.py` 模式，测试不进 tests/cli）。
4. 从既有 Ch100 DB 导出完整可读书稿（V9-README 177 验收要点）。

---

## 技术方案

### 1. CLI

```
songyan export --project-id <id> [--format md|txt] [--by flat|arc|volume] [--chapters 1-100] [--output <dir>]
```

- 默认：`--format md --by flat --output exports/`
- `--by arc`：按 `arc_summaries` 的章范围分文件（`arc-01-<arc_title>.md`）；无 `arc_summaries` 记录时**警告并回退 flat**；未被任何弧覆盖的章归入 `arc-00-未分弧.md`（保持完整性，不丢章）
- `--by volume`：同构（`volume_summaries`）
- DATABASE_URL 走既有 `settings.database_url`（env 可指向任意库，如 `.tmp` 的 Ch100 库）——与 175 实跑验收同模式
- 输出：打印生成的文件清单（路径 + 章数）

### 2. Service：`src/songyan/services/export_service.py`（只读）

- `collect_accepted_chapters(project_id, chapters: tuple[int,int] | None) -> list[ChapterExport]`：经 `ChapterHeadRepository` 取 `status='accepted'` 的 head 按章号排序，经 `accepted_version_id` 取 `chapter_versions.content/word_count`；head 存在但 version 缺失 → 记 warning 并跳过（不中断导出）
- `render_book(project_title, chapters, fmt, by, arcs_or_volumes) -> dict[str, str]`：**纯函数**（文件名 → 文件内容），不落盘
- `export_project(...) -> list[Path]`：collect + render + 写文件（utf-8），返回生成路径

### 3. 书稿格式（纯净）

Markdown（flat）：

```markdown
# <项目标题>

## 第 1 章

<正文原文>

## 第 2 章

<正文原文>
```

- 弧/卷分组时每个文件顶部加 `# <arc_title 或 volume_title>` 与章范围注释行（`<!-- chapters 1-25 -->`）
- `txt`：无 markdown 符号——标题行 `第 N 章`，章间空两行
- **禁止进正文**：version_id、分数、字数统计、run 元数据、分隔线 `---`（历史 `_export_prose` 有，正式版去掉）
- 正文原文不改写、不 trim 内部空行；文件结尾单换行

### 4. 测试（TDD，全部不进 tests/cli）

新建 `tests/test_177_export_service.py`：

- collect：只取 accepted、按章号排序、范围过滤正确、version 缺失跳过且 warning；
- render flat md：标题/章标题格式、**正文无 version_id 与字数统计**、无 `---`；
- render txt：无 `#` 符号、章标题行正确；
- render by arc：弧分文件命名、章归入正确弧、未覆盖章入"未分弧"、无 arc 记录回退 flat + 警告；
- render by volume 同构一条；
- CLI 接线函数（模块级，monkeypatch service 层）参数传递正确（参照 175 `_render_cost_section` 的测试模式）。

## 验证

### 回归命令

```powershell
python -m pytest tests/test_177_export_service.py -q
python -m pytest tests/ -q
ruff check src/ tests/
```

### 验收（V9-README 177 要点）

`DATABASE_URL=sqlite:///.tmp/task172b_xuanhuan_ch100.db songyan export --project-id <xuanhuan_pid> --by arc --output .tmp/177_export_check/`：

- 导出章数 = 100（与 DB 中 accepted head 数一致）；
- 抽查一章内容与 DB `chapter_versions.content` 逐字一致（hash 对照）；
- 弧分组与 `arc_summaries` 范围一致；
- 全文 grep 无 `version_id`、无 `---` 分隔线、无字数统计；
- （可选二验）wuxia Ch100 库 flat 导出同样完整。

## 出口标准

1. `songyan export` 落地（CLI + service + 纯函数渲染），全量测试绿、ruff 绿；
2. 既有 Ch100 DB 导出验收证据落盘（章数/抽章 hash/分组/grep 洁净）；
3. 本 Task 执行记录补录本文档，V9-README 177 行翻正。

## 撞墙路由

| 风险 | 触发信号 | 处理 |
|---|---|---|
| 弧元数据不全（Ch100 库只有部分弧有 summaries） | 验收时大量章落入"未分弧" | 属正常数据现状，回退策略已覆盖；记录现象，不改导出逻辑 |
| 正文本身含 markdown 标题 | 导出格式与原文标题混淆 | 不改写正文（纯净原则）；章标题用固定"第 N 章"层级即可区分 |
| 大库导出性能 | 100 章以上导出慢 | 逐章流式写而非全量内存拼接（render 按文件分块返回即可，无需真流式 IO） |
| 非 accepted 版本混入 | 导出内容与 DB 抽章不一致 | collect 只经 `accepted_version_id`；验收 hash 对照兜底 |

## Out of Scope

- DOCX/EPUB 格式、网文平台投稿格式（后续按需）；
- 卷/弧标题的 LLM 润色（用既有元数据原文）；
- 历史任务脚本的 `_export_prose()` 改写（任务产物不动）；
- 项目备份/迁移（独立事项，V10 评估）。
