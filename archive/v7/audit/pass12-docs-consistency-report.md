# Pass 12: 文档与状态一致性审计报告

## 执行摘要
- **发现总数**: 3
- **P0**: 0, **P1**: 0, **P2**: 3
- **关键结论**: `docs/STATUS.md` 与 `tasks/V7-README.md` 状态一致，V7 Task 160-169 均存在对应 `-DONE.md` 文件，Task 170 已规划；`AGENTS.md` 核心不可违背规则在代码层面被遵守（Pass 1 已验证）；主要不一致点在于 `docs/code-review-plan.md` 仍为 V4.0 旧版且未指向 V7 审计计划，以及 8 个源文件/测试文件存在 CRLF 行尾污染。

## 检查项与发现

### 12-1 `docs/code-review-plan.md` 仍为 V4.0 旧版，未指向 V7 审计计划
- **级别**: P2
- **文件**: `docs/code-review-plan.md`
- **问题描述**: 该文件标题为“Songyan V4.0 全域代码审查计划”，日期 2026-06-11，基线为 V4.0-Phase B，状态为“审查完成，修复进行中”。当前项目已进入 V7，V7 审计计划位于 `docs/superpowers/plans/2026-07-06-v7-code-review-and-architecture-audit-plan.md`，但旧文档未更新指向，也无“已归档/已替代”说明。新开发者容易误入旧计划。
- **证据**:
  > `# Songyan V4.0 全域代码审查计划`
  > `> **日期**: 2026-06-11`
  > `> **状态**: 审查完成，修复进行中`
- **潜在影响**: 文档入口混淆；V4.0 的修复清单（如 P0-1 chapter_versions 版本覆盖）可能被视为未完成，造成误判。
- **修复建议**: 在 `docs/code-review-plan.md` 顶部添加归档声明，说明“本文件为 V4.0 历史审查计划，已归档；当前代码审查/架构审计见 `docs/superpowers/plans/2026-07-06-v7-code-review-and-architecture-audit-plan.md` 与 `docs/reports/v7-audit/`”。
- **验证方式**: 阅读 `docs/code-review-plan.md` 顶部应看到 V7 指向链接。

### 12-2 8 个源文件/测试文件存在 CRLF 行尾污染
- **级别**: P2
- **文件**:
  - `src/songyan/agents/revision_handler/__init__.py`
  - `src/songyan/agents/revision_handler/_segmented_revision.py`
  - `src/songyan/agents/writer.py`
  - `src/songyan/models/review.py`
  - `tests/test_079_segmented_revision.py`
  - `tests/test_revision_handler.py`
  - `tests/test_rule_auditor.py`
  - `tests/test_writer.py`
- **问题描述**: `git status` 显示这 8 个文件已修改，但 `git diff` 无可见差异。`git ls-files --eol` 确认原索引为 LF（`i/lf`），而工作区为 CRLF（`w/crlf`）。这是 Windows 编辑器或 Git 自动转换导致的行尾不一致，会污染 diff、干扰代码审查。
- **证据**:
  ```
  i/lf    w/crlf  attr/  src/songyan/agents/writer.py
  i/lf    w/crlf  attr/  tests/test_writer.py
  ...（共 8 个文件）
  ```
- **潜在影响**: 后续真正修改这些文件时，CRLF/LF 差异会淹没实际变更；跨平台协作时产生噪音提交。
- **修复建议**:
  1. 配置仓库 `.gitattributes`（若不存在）强制文本文件使用 LF：`*.py text eol=lf`。
  2. 对上述 8 个文件执行行尾统一化（例如 `git add --renormalize .` 或 `dos2unix`）。
  3. 在 `AGENTS.md` 或贡献指南中明确“Python 源码使用 LF 行尾”。
- **验证方式**:
  - `git ls-files --eol` 显示 `i/lf w/lf`。
  - `git status --short` 不再显示这 8 个文件为 modified。

### 12-3 `.env.example` 本身使用 CRLF 行尾
- **级别**: P2
- **文件**: `.env.example`
- **问题描述**: 与上述 8 个文件类似，`.env.example` 在 `Read` 输出中显示 `\r`（CRLF）。虽然 `.env` 文件在 `.gitignore` 中不参与代码 diff，但模板文件作为新环境配置入口，应保持 LF 以与项目其余文档一致。
- **证据**: `Read .env.example` 时系统提示 `Mixed or lone carriage-return line endings are shown as \r`。
- **潜在影响**: 轻度的跨平台不一致；复制为 `.env` 后在 Linux/macOS 编辑器中可能出现 `^M`。
- **修复建议**: 将 `.env.example` 转换为 LF；在 `.gitattributes` 中声明 `*.env text eol=lf`（若适用）。
- **验证方式**: `file .env.example` 显示 `ASCII text` 而非 `ASCII text, with CRLF line terminators`。

## 通过项

| 检查项 | 结论 | 证据 |
|--------|------|------|
| `docs/STATUS.md` 当前阶段 | 通过 | 明确“V7 阶段 W 已通过，Task 166/167/168/169 已完成，Task 170 已规划，下一步开工 170” |
| `docs/STATUS.md` 最近全量测试 | 通过 | 记录 `2397 passed, 2 skipped, 1 xfailed, 2 warnings`，与本次审计实测一致 |
| `docs/STATUS.md` V6 验收 | 通过 | V6 Task 159 验收结论、run-bba292da、health≥8.2、T5 冻结等描述与 `tasks/V6-README.md` 一致 |
| `tasks/V7-README.md` Task 状态 | 通过 | Task 160-169 均标记 ✅ 完成并指向存在的 `-DONE.md`；Task 170 指向存在的规划文件；171-173 为占位 |
| `-DONE.md` 文件存在性 | 通过 | 19 个 V7 子任务 `-DONE.md` 全部存在（160、161、162、163、164、165、165p、166、166a、166b、167、167a、167b、168、168a、168b、169、169a、169b） |
| `AGENTS.md` 规则与代码一致性 | 通过 | Pass 1 已验证：版本不可覆盖、character_states INSERT-only、Agent 不直连 DB、state 只存 ID、结算证据校验、自动修订 ≤2 轮等核心规则均成立 |
| 文档入口 | 通过 | `docs/INDEX.md`、`README.md`、`AGENTS.md` 均指向 `docs/STATUS.md` 与 `tasks/V7-README.md` 作为当前入口 |
| `docs/v7-plan.md` 存在 | 通过 | V7 阶段规划与 Task 160-173 路线图文件存在，且与 V7-README 的四个决策边界一致 |

## 待修复清单

| ID | 级别 | 问题 | 建议修复文件 | 验证命令 |
|----|------|------|--------------|----------|
| 12-1 | P2 | V4.0 code-review-plan 未归档/未指向 V7 | `docs/code-review-plan.md` | 文件顶部含 V7 指向 |
| 12-2 | P2 | 8 个 Python 文件 CRLF 行尾污染 | 上述 8 个文件 + `.gitattributes` | `git ls-files --eol` 全为 `w/lf`；`git status` 干净 |
| 12-3 | P2 | `.env.example` CRLF 行尾 | `.env.example` | `file .env.example` 无 CRLF |

---
> 审计结论：文档状态一致性良好，无 P0/P1；P2 项为行尾卫生与旧文档指向清理，建议在汇总报告前批量处理，避免后续 diff 噪音。
