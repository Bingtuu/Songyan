# V9 归档索引

> **阶段**: 生产化地基 + urban 第三体裁 Ch100
> **状态**: ✅ 已全量闭环（2026-07-23）
> **事实入口**: `tasks/V9-README.md`

V9 把系统从“验证过的研究原型”推进到“自用敢跑、按开源标准可发布”的工程状态：先补齐长跑可靠性、导出、打包、CI、日志、成本追踪、质量门工具链，再用 urban 第三体裁 Ch100 作为实战验收。

## 阶段结论

| 组 | 结果 | 证据 |
|----|------|------|
| A 组生产化地基 | PASS | Task 173-184 全部 DONE |
| B 组 urban Ch100 | PASS | Task 185-187，urban Ch1-Ch100 100/100 accepted，five-gate PASS，segment audit PASS，T9=0 |
| C 组守护项 | PASS | scifi 回归无漂移；CED/T9/five-gate 冻结口径未放宽 |
| 收口归档 | PASS | Task 188 文档一致性与归档完成 |

## 任务文档

| Task | 文档 |
|------|------|
| 173 | `173-interpreter-exit-hang-fix.md` / `173-interpreter-exit-hang-fix-DONE.md` |
| 174 | `174-logging-system-foundation.md` / `174-logging-system-foundation-DONE.md` |
| 175 | `175-cost-tracking-and-budget-circuit-breaker.md` / `175-cost-tracking-and-budget-circuit-breaker-DONE.md` |
| 176 | `176-windows-anti-hang-wrapper.md` / `176-windows-anti-hang-wrapper-DONE.md` |
| 177 | `177-export-book-manuscript.md` / `177-export-book-manuscript-DONE.md` |
| 178 | `178-wheel-packaging-resource-loading.md` / `178-wheel-packaging-resource-loading-DONE.md` |
| 179 | `179-cli-experience-fixes.md` / `179-cli-experience-fixes-DONE.md` |
| 180 | `180-doctor-environment-check.md` / `180-doctor-environment-check-DONE.md` |
| 181 | `181-ci-and-test-cleanup.md` / `181-ci-and-test-cleanup-DONE.md` |
| 182 | `182-five-gate-and-segment-audit-tools.md` / `182-five-gate-and-segment-audit-tools-DONE.md` |
| 183 | `183-profile-tuning-cli.md` / `183-profile-tuning-cli-DONE.md` |
| 184 | `184-genres-creative-modes-json-schema.md` / `184-genres-creative-modes-json-schema-DONE.md` |
| 185 | `185-urban-short-window-calibration-DONE.md` |
| 186 | `186-urban-ch100-climb.md` |
| 187 | `187-urban-ch100-climb-execution.md` / `187-urban-ch100-climb-execution-DONE.md` |
| 187.p | `187.p-urban-ch19-context-emergency-budget.md` |
| 187.s | `187.s-urban-ch25-health-calibration.md` |
| 187.t | `187.t-urban-ch23-double-slash-t9-clean.md` |
| 187.u | `187.u-urban-ch21-settlement-past-foreshadowing.md` |
| 187.v | `187.v-urban-ch3-numerical-settlement-isolate.md` |
| 187.w | `187.w-urban-ch50-t9-clean.md` |
| 188 | `188-v9-closure-and-archive-DONE.md` |

## reports/

- `reports/187-urban-ch100-climb.md` — Task 187 urban Ch100 分段指标摘要；终判以 `187-urban-ch100-climb-execution-DONE.md` 和 `.tmp/187_urban_ch100_final.json` 为准。

## 关键证据文件

| 证据 | 路径 |
|------|------|
| urban Ch100 终判 | `.tmp/187_urban_ch100_final.json` |
| urban Ch100 段审计 | `.tmp/187_seg100_audit.json` |
| urban Ch100 T9/metrics | `.tmp/187_seg100_metrics.md` |
| urban Ch100 运行 DB | `.tmp/task172b_urban_ch100.db` |
| urban Ch100 项目信息 | `.tmp/task172b_urban_project.json` |
| urban Ch100 分段记录 | `.tmp/task172b_urban_segments.jsonl` |
| urban 短窗口 registry 证据 | `.tmp/185_urban_registry_end15.json` |
| urban T9 复测说明 | `.tmp/185_t9_recompute_note.json` |
| scifi end10 回归 | `.tmp/185_scifi_end10_regression.json` |

## V10 预登记

- 跨体裁 Ch200：扩展 sci-fi/xuanhuan/wuxia/urban 的 Ch200 checkpoint 与冻结口径。
- 优秀度信号包：跨章同质化指数、中文 AI 腔规则包、judge 偏差对策、perplexity gate、style extraction → style card、角色声纹锚点。
- 结构升级 spike：章级 KG 图 diff、FactTrack validity interval、Storyline Tree。
- 工程增强候选：LiteLLM proxy fallback、tracing、修订停滞检测、LLM 幂等缓存、迁移版本账本。
