# 252 · stale_vs_storyline（故事线 × 变体新鲜度）

| 项 | 内容 |
|---|---|
| 状态 | TODO（tech-m4-followup-s5 项 ①；owner 已接受 B1–B8，2026-11-13） |
| 关联 | `docs/tech-m4-followup-s5.md` §3 / B1–B5 / B7；PRD :108 故事线非 Canon 红线 |
| 预估 | 一个编码切片（TDD）+ tests/cli 套件 |

## 目标

`chapter_variants` 加 `stale_vs_storyline` + `storyline_fingerprint` 两列；本章相关切片指纹（全书 outline 行 + 覆盖弧 + 相关线索）；懒刷新与 stale_vs_canon 同触发点（旧行只补指纹不标脏、只标不消）；generate 落指纹；list / chapter status 露出；pick 默认不拦 + stderr 软提醒。parent_canon_fingerprint 与 stale_vs_canon 零改动。

## 步骤

- [ ] TDD：切片指纹纯函数（弧边界移动 / 无关弧不动 / outline 改动全书变 / 线索三条件并集）+ 迁移列 + repo 往返
- [ ] TDD：懒刷新（旧行补指纹不标脏 / 指纹变了标 1 / 已标保持）+ generate 落指纹
- [ ] TDD：list/status 露出 + pick 软提醒（exit 0 不拦）
- [ ] 全量回归 + ruff；完工同步 STATUS/HANDOFF；归档

## 验收标准

- [ ] 切片指纹四条断言全绿；旧行首次刷新零标脏
- [ ] pick 遇 stale_vs_storyline=1 仍 exit 0 且 stderr 有提醒
- [ ] parent_canon_fingerprint / stale_vs_canon / M3 三态零变化（既有套件原样通过）
- [ ] 全量 pytest 绿 + ruff 绿；不 bump 版本
- [ ] 完工同步 `docs/STATUS.md` / `docs/HANDOFF-mew.md`；归档 `tasks/done/`

## 完成总结

（待 DONE 时填写）
