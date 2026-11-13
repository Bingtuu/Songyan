# 252 · stale_vs_storyline（故事线 × 变体新鲜度）

| 项 | 内容 |
|---|---|
| 状态 | DONE（2026-11-13；tech-m4-followup-s5 项 ① 落地并归档） |
| 关联 | `docs/tech-m4-followup-s5.md` §3 / B1–B5 / B7；PRD :108 故事线非 Canon 红线 |
| 预估 | 一个编码切片（TDD）+ tests/cli 套件 |

## 目标

`chapter_variants` 加 `stale_vs_storyline` + `storyline_fingerprint` 两列；本章相关切片指纹（全书 outline 行 + 覆盖弧 + 相关线索）；懒刷新与 stale_vs_canon 同触发点（旧行只补指纹不标脏、只标不消）；generate 落指纹；list / chapter status 露出；pick 默认不拦 + stderr 软提醒。parent_canon_fingerprint 与 stale_vs_canon 零改动。

## 步骤

- [x] TDD：切片指纹纯函数 + loader 切片选择（覆盖弧 / 三条件并集 / 字段白名单）+ 迁移列 + repo 往返（storyline_fingerprint.py）
- [x] TDD：懒刷新（旧行补指纹不标脏 / 变了标 1 / 已标保持指纹同步 / 远弧改动不标）+ generate 落指纹
- [x] TDD：list（JSON+文本）/ chapter status 露出 + pick 软提醒（exit 0 不拦；CLI 行为测试经 stash 回退法实证 RED）
- [x] ruff + tests/cli 274 passed（唯一失败为既有 doctor flake）；完工同步 STATUS/HANDOFF；归档。全量默认收集回归随 253 之后统一跑（两任务同批触碰面）

## 验收标准

- [x] 切片指纹断言全绿；旧行首次刷新零标脏
- [x] pick 遇 stale_vs_storyline=1 仍 exit 0 且 stderr 有提醒
- [x] parent_canon_fingerprint / stale_vs_canon / M3 三态零变化（variant 全套件原样通过）
- [x] ruff 绿；不 bump 版本；全量随 253 后统一（本任务只增窄列与只读路径）
- [x] 完工同步 `docs/STATUS.md` / `docs/HANDOFF-mew.md`；归档 `tasks/done/`

## 完成总结

**状态**：DONE（2026-11-13）。`chapter_variants` 加 `stale_vs_storyline` + `storyline_fingerprint` 两列（幂等迁移）；`services/storyline_fingerprint.py` 切片指纹（全书 outline 行 + 覆盖弧含边界 + 相关线索三条件并集，字段白名单）；`refresh_stale_vs_storyline` 与 stale_vs_canon 同四处触发点（旧行只补指纹不标脏、只标不消）；generate 落指纹；list（JSON/文本 slStale）/ chapter status / pick（exit 0 + stderr 软提醒）露出。parent_canon_fingerprint / stale_vs_canon / M3 三态零变化。新增 28 测（services 11 + db 6 + cli 4 + 既有变体套件原样）。
