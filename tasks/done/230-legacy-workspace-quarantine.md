# 230 · 旧 lineage 工作区文件隔离

| 项 | 内容 |
|---|---|
| 状态 | DONE |
| 关联 | 2026-11-07 整体分析 P1-5；tasks/README.md 队列规则（编号 200 起、永不复用） |
| 预估 | 一个切片 |

## 背景

`tasks/` 根目录存在 78 个旧 lineage（V10–V15 时代）未跟踪文件，编号 208–245 与现行队列（200 起）**撞号**——例如新 208 = `check`（done），旧 208 = v11-readiness-audit。`tasks/README.md` 明确规定编号在本目录内永不复用；这些文件的存在直接违反队列规则，极易误读为活任务。`scripts/_dump_ch2_*.py` 同为旧 lineage 残留。

## 处理

**隔离而非删除**（autonomous 模式下删除不可恢复，保守处理）：全部移至 `.tmp/legacy-workspace-sweep-2026-11-07/`（.tmp 已被 gitignore，不入库）。

- 78 个 `tasks/*.md`（旧 208–245 任务对、V10/V11/V12 README、TEMPLATE）
- `scripts/_dump_ch2_plan.py`、`scripts/_dump_ch2_version.py`

处理后 `tasks/` 根目录只剩 `README.md` 与 `done/`；`git status` 工作区干净。

## 完成总结

隔离完成。若确认无用，删除 `.tmp/legacy-workspace-sweep-2026-11-07/` 即可；若要留档，建议日后由 owner 决定移入 `archive/` 或删除。无代码与文档内容改动。
