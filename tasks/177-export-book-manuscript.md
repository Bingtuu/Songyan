# Task 177: songyan export 正文导出

> **阶段**: V9.2 交付与发布
> **类型**: 功能（交付链最后一公里）
> **优先级**: P0（V9-README 审计 P0 ③：写完 100 章拿不到书稿——无 export 命令，8+ 任务脚本各复制一份 `_export_prose()`）
> **依赖**: 无（只读功能；174 日志、175 成本不影响）
> **状态**: ✅ 完成
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
- 输出：打印生成的文件清单（路径 + 章数）；若 accepted head 指向的版本缺失或不匹配，额外输出 skipped 章数
- 输出文件命名：
  - flat：`<safe_project_title>-flat.<ext>`；项目标题为空时 fallback `project-<project_id[:8]>-flat.<ext>`
  - arc：`arc-<序号两位>-<safe_arc_title>.<ext>`；未覆盖章文件为 `arc-00-未分弧.<ext>`
  - volume：`volume-<序号两位>-<safe_volume_title>.<ext>`；未覆盖章文件为 `volume-00-未分卷.<ext>`
  - `safe_*` 必须清理 Windows 非法文件名字符（`<>:"/\|?*`、控制字符、尾随点/空格），空标题 fallback 到 `untitled`
- 重复导出语义：覆盖同名文件，但**不清理**输出目录中无关旧文件；CLI 的章数/文件清单以本次 `export_project()` 返回路径为准，不通过扫描目录推断。

### 2. Service：`src/songyan/services/export_service.py`（只读）

- `collect_accepted_chapters(project_id, chapters: tuple[int,int] | None) -> list[ChapterExport]`：经 `ChapterHeadRepository` 取 `status='accepted'` 的 head 按章号排序，经 `accepted_version_id` 取 `chapter_versions.content/word_count`；head 存在但 version 缺失 → 记 warning 并跳过（不中断导出），同时返回/记录 skipped 统计供 CLI 输出
- `render_book(project_title, chapters, fmt, by, arcs_or_volumes) -> dict[str, str]`：**纯函数**（文件名 → 文件内容），不落盘
- `export_project(...) -> ExportResult`：collect + render + 写文件（utf-8），返回本次生成文件与 skipped 统计
- export 是只读命令：不主动 `init_schema()`、不自动迁移 `DATABASE_URL` 指向的源库；schema 缺失时返回清晰错误，由调用方决定是否初始化/迁移
- 分组规则：
  - arc/volume 记录先过滤无效范围：`start_chapter < 1`、`end_chapter < start_chapter` 的分组不生成文件，只 warning（当前 Ch100 库存在 `(0,0)` 卷占位，必须被忽略）
  - 有效分组按 `(start_chapter, end_chapter, title)` 稳定排序并赋序号；空分组不生成文件
  - 章节落入多个重叠分组时归入第一个匹配分组并 warning，避免重复导出
  - 未被任何有效分组覆盖的章节统一进入 `arc-00-未分弧` / `volume-00-未分卷`

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
- **导出器禁止主动插入**：version_id、分数、字数统计、run 元数据、分隔线 `---`（历史 `_export_prose` 有，正式版去掉）
- 正文原文不改写、不 trim 内部空行；文件结尾单换行
- 纯净性口径：正文原文如果本身包含 `version_id` 或 `---`，导出器不得改写；“grep 无 `version_id` / `---`”只作为当前 Ch100 验收样本的辅助证据，不作为通用逻辑不变量。抽章 hash 对照只比较正文段，不比较导出器添加的标题/空行包装。

### 4. 测试（TDD，全部不进 tests/cli）

新建 `tests/test_177_export_service.py`：

- collect：只取 accepted、按章号排序、范围过滤正确、version 缺失跳过且 warning；
- render flat md：标题/章标题格式、**正文无 version_id 与字数统计**、无 `---`；
- render txt：无 `#` 符号、章标题行正确；
- render by arc：弧分文件命名、章归入正确弧、未覆盖章入"未分弧"、无 arc 记录回退 flat + 警告；
- render by arc/volume 异常分组：无效 `(0,0)` 占位被忽略、重叠分组 first-match + warning、空分组不生成文件；
- render by volume 同构一条；
- 文件名 sanitizer：Windows 非法字符、空标题、重名标题 fallback/去重行为稳定；
- CLI 接线函数（模块级，monkeypatch service 层）参数传递正确（参照 175 `_render_cost_section` 的测试模式）；
- Click 接线测试（不放 `tests/cli/`）：用 `CliRunner` 调 `cli ["export", "--project-id", "p1", "--format", "txt", "--by", "arc"]`，monkeypatch service 层，断言参数透传、输出文件清单、`exit_code == 0`；
- `--chapters` 非法输入：非数字、`a>b`、超出无 accepted 章时给可读 `ClickException` 或明确 warning（测试锁定）。

## 验证

### 回归命令

```powershell
python -m pytest tests/test_177_export_service.py -q
python -m pytest tests/ -q
ruff check src/ tests/
```

### 验收（V9-README 177 要点）

PowerShell：

```powershell
$env:DATABASE_URL='sqlite:///.tmp/task172b_xuanhuan_ch100.db'
songyan export --project-id 1e7ce6279b224e7f8e476f6f4e963417 --by arc --output .tmp/177_export_check/xuanhuan_arc
```

Bash/Git Bash：

```bash
DATABASE_URL=sqlite:///.tmp/task172b_xuanhuan_ch100.db songyan export --project-id 1e7ce6279b224e7f8e476f6f4e963417 --by arc --output .tmp/177_export_check/xuanhuan_arc
```

- 导出章数 = 100（与 DB 中 accepted head 数一致）；
- 抽查至少 3 章内容与 DB `chapter_versions.content` 逐字一致（只 hash 正文段，不含导出标题包装）；
- 弧分组与 `arc_summaries` 有效范围一致；无效/空分组不生成文件；
- 当前样本全文 grep 无导出器主动插入的 `version_id`、字数统计；若命中 `---`，必须用 DB 正文段 hash 判定来源（本 Task 不改写正文）；
- 二验：`DATABASE_URL=sqlite:///.tmp/task172b_wuxia_ch100.db` + project `273a8408be8e4caf8cbc1e91954da600` flat 导出同样完整。

## 执行记录（2026-07-19）

### 实现落点

- 新增 `src/songyan/services/export_service.py`：`collect_accepted_chapters()` 只读 accepted head，经 `accepted_version_id` 加载 `chapter_versions.content`；`render_book()` / `render_book_files()` 提供纯函数渲染；`export_project()` 负责落盘并返回本次生成文件与章数。
- 新增 `songyan export` CLI：支持 `--project-id`、`--format md|txt`、`--by flat|arc|volume`、`--chapters a-b`、`--output <dir>`；输出本次文件清单，不扫描目录推断结果。
- 分组规则已落地：`(0,0)` 等无效分组 warning 后忽略；重叠分组 first-match + warning；空分组不生成文件；未覆盖章节归入 `arc-00-未分弧` / `volume-00-未分卷`。
- Windows 文件名脱敏已覆盖非法字符、控制字符、尾随点/空格、空标题 fallback 与保留名前缀保护；重复导出覆盖同名文件但不清理输出目录旧文件。

### 测试与验收

- 聚焦测试：`python -m pytest tests/test_177_export_service.py -q` → **13 passed**。
- 全量测试：`powershell -NoProfile -File scripts\run_with_timeout.ps1 -TimeoutSec 1200 -DetectPytestSummary -- python -m pytest tests/ -q` → **2895 passed, 2 skipped, 1 xfailed, 7 warnings**；wrapper → `WRAPPER_RESULT=PASS_NORMAL_EXIT`。
- Ruff：`ruff check src/ tests/` → **All checks passed**。
- xuanhuan arc 实导出：`.tmp/task172b_xuanhuan_ch100.db` + project `1e7ce6279b224e7f8e476f6f4e963417` → **100 章 / 4 个 arc 文件**，落盘 `.tmp/177_export_check/xuanhuan_arc/`。
- wuxia flat 二验：`.tmp/task172b_wuxia_ch100.db` + project `273a8408be8e4caf8cbc1e91954da600` → **100 章 / 1 个 flat 文件**，落盘 `.tmp/177_export_check/wuxia_flat/`。
- volume 模式补验：xuanhuan volume → warning 忽略 `(0,0)` 卷占位，生成 **2 个文件**：`volume-01-第一卷：觉醒.md`（25 章）与 `volume-00-未分卷.md`（75 章）。
- 抽章 hash：xuanhuan Ch1/50/100 与 wuxia Ch1/50/100 的导出正文段 sha256 前 16 位均与 DB `chapter_versions.content` 一致。
- 洁净性说明：验收 grep 发现若干 `---`，反查 hash 证明来自 DB 正文原文，非导出器包装主动插入；导出器未插入 `version_id`、评分、字数统计、run metadata 或历史 `_export_prose()` 的分隔线。

### Review follow-up（2026-07-19）

- `export_project()` / `collect_accepted_chapters()` 不再调用 `init_schema()`；导出历史库不会顺手迁移 schema，缺表时返回“不会自动迁移源库”的清晰错误。
- `export_project()` 返回 `ExportResult(files, skipped_count)`；CLI 在 skipped 非零时输出“已跳过 N 章（accepted head 指向的版本缺失或不匹配）”。
- `render_book()` 与 `render_book_files()` 的 docstring 已明确分工：前者是纯 `filename -> content` 便捷包装，后者是导出主 API，保留每文件章节归属。
- 复验：`tests/test_177_export_service.py` **15 passed**；全量 pytest（Task 176 wrapper）**2897 passed, 2 skipped, 1 xfailed**，`WRAPPER_RESULT=PASS_NORMAL_EXIT`；`ruff check src/ tests/` 全绿。

## 出口标准

1. ✅ `songyan export` 落地（CLI + service + 纯函数渲染），全量测试绿、ruff 绿；
2. ✅ 既有 Ch100 DB 导出验收证据落盘（章数/抽章 hash/分组/洁净性来源判定）；
3. ✅ 本 Task 执行记录补录本文档，V9-README 177 行翻正。

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
