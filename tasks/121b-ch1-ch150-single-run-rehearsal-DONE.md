# Task 121b DONE — Ch1-Ch150 Single-Run Rehearsal

> **日期**: 2026-06-21
> **类型**: V5.0 证据补强 / V5.1 preflight
> **结论**: 已执行单次 run 排练；未跑通 Ch1-Ch150，阻断点提前暴露在 Ch5。

---

## 1. 目标

验证 V5.0 是否具备“单命令一次性 Ch1-Ch150”的实跑证据，而不仅依赖分段长跑和风险窗口复验。

验收目标来自 `tasks/121a-v50-goal-assessment-and-v51-plan.md`：

- 单一 run 覆盖 Ch1-Ch150。
- `success_rate == 100%` 或有明确失败点。
- 每章有 QG、settlement、summary、budget、health_low、ContextEmergency 指标。
- 输出 `songyan report --run-id <run_id>` 报告。

---

## 2. 执行命令

```powershell
powershell -NoProfile -ExecutionPolicy Bypass -File "scripts\run_songyan_chapter.ps1" `
  -ProjectId "proj-2375dbfc" `
  -Chapters "1-150" `
  -ModeId "webnovel_intense" `
  -Tag "ch1-ch150-single-run" `
  -TaskName "task121b" `
  -TimeoutSec 86400
```

项目选择：

- `proj-e74ef1e4` 已有 Ch1-Ch150 历史版本记录，不适合作为从零 single-run 证据。
- `proj-2375dbfc` 是 scifi 项目，执行前没有 `chapter_versions` 记录，适合作为干净 rehearsal 目标。

---

## 3. 运行结果

| 项 | 结果 |
|----|------|
| run_id | `run-21ff158b` |
| project_id | `proj-2375dbfc` |
| 目标范围 | Ch1-Ch150 |
| 实际完成 | Ch1-Ch4 成功，Ch5 失败 |
| project_runs.status | `partial` |
| completed_chapters | `[1, 2, 3, 4]` |
| failed_chapters | `[5]` |
| report | `logs/reports/report-run-21ff158b.md` |
| JSONL | `logs/chapter_runs/run-21ff158b.jsonl` |
| wrapper stdout | `logs/task121b/songyan-task121b-ch1-ch150-single-run-20260621-033116.out.log` |

报告摘要：

```text
章节范围: Ch1 ~ Ch150
总章节数: 5
成功: 4 | 失败: 1
达标率: 80.0% (4/5)
context_emergency 次数: 0
失败章节: Ch5
失败原因: Ch5: settlement_review / unknown_error
DG-2: 未通过
```

---

## 4. 逐章指标

| 章节 | 成功 | QG | settlement | summary | budget_used | ContextEmergency | revision_rounds |
|------|:----:|:--:|:----------:|:-------:|------------:|:----------------:|----------------:|
| Ch1 | Y | Y | Y | Y | 0.498 | N | 1 |
| Ch2 | Y | Y | Y | Y | 0.696 | N | 2 |
| Ch3 | Y | Y | Y | Y | 0.734 | N | 1 |
| Ch4 | Y | Y | Y | Y | 0.701 | N | 2 |
| Ch5 | N | N | N | N | 0.738 | N | 2 |

关键观察：

- Ch1-Ch4 的 QG、settlement、summary 均成功。
- Ch1-Ch5 均未触发 ContextEmergency，budget 不是本次阻断原因。
- Ch5 在 rewrite 后出现结构完整性失败，随后接受旧 best version，但 `skip_settlement=True`，导致 settlement/summary 缺失并标记失败。

---

## 5. Ch5 阻断点

Ch5 关键日志：

```text
rewrite.word_count_underflow chapter_number=5 lower_hard=2800 original_word_count=2543 target=3500
rewrite.struct_integrity_failed chapter_number=5 reason=missing_ending_hook version_id=v-5-4-4fc6a839
human_gate.decision chapter_number=5 decision=accept version_id=rev-5-3-4c8f78c7
settlement_extractor_node.skipping_settlement chapter_number=5 version_id=rev-5-3-4c8f78c7
run_logger.chapter_logged chapter_number=5 success=False
project_pipeline.end completed=[1, 2, 3, 4] failed=[5] final_status=partial
```

判定：

- 这不是 ContextEmergency 或上下文预算问题。
- 这是 rewrite / best-version / settlement skip 的早期阻断窗口。
- V5.0 工程验收结论不变，但“单命令一次性 Ch1-Ch150”严格宣称仍未达成。

---

## 6. Wrapper 处理

本次先发现 `scripts/run_songyan_chapter.ps1` 在 Windows PowerShell 5 下解析失败，原因是脚本为 UTF-8 无 BOM 且含非 ASCII 字符串。已修复：

- wrapper 改为 ASCII-only 注释和输出，避免 PowerShell 5 编码解析问题。
- 移除内部 `cmd.exe` 调用，直接 `Start-Process songyan`。
- 增加 `project_pipeline.end` 检测后的 `BusinessDoneGraceSec`，防止业务已结束但进程 teardown 卡住时等满长超时。

本次 run 在业务端已写出 `project_pipeline.end final_status=partial` 后，`songyan.exe` 仍残留，已按 Windows 长跑协议清理本次明确进程。

---

## 7. 改动文件

- `scripts/run_songyan_chapter.ps1`
  - 修复 PowerShell 5 编码解析问题。
  - 加强业务完成后进程收尾判定。
- `tasks/121b-ch1-ch150-single-run-rehearsal-DONE.md`
  - 新增本 DONE 文档。
- `docs/STATUS.md`
  - 更新当前 single-run rehearsal 证据状态。
- `tasks/V5-README.md`
  - 增加 Task 121b 结果和遗留项状态。
- `docs/INDEX.md`
  - 增加 Task 121b 查阅入口。
- `README.md`
  - 同步 single-run rehearsal 已执行但未跑通的当前口径。

---

## 8. 验证结论

Task 121b 已完成“补证据”的动作，但证据结论是失败而非通过：

- ✅ 单一 run 已启动并从 Ch1 开始执行。
- ✅ 已生成 JSONL 和 report。
- ✅ 明确失败点：Ch5。
- ❌ 未达成 Ch1-Ch150 100% single-run。

验证命令：

```powershell
ruff check src/ tests/
python -m pytest tests/ -q
```

验证结果：

- `ruff check src/ tests/`: All checks passed.
- `pytest tests/ -q`: `1718 passed, 2 xfailed, 14 warnings`，`WRAPPER_RESULT=PASS_NORMAL_EXIT`。
- `git diff --check`: 通过，仅有 CRLF 工作区提示。
- `scripts/run_songyan_chapter.ps1`: PowerShell parser check 通过。

后续已开 Task 121c 修复 Ch5 暴露的 rewrite/settlement skip 阻断；下一步按 Task 121d 使用新的干净 rehearsal 项目重跑 single-run rehearsal，不直接进入 Prompt 调优。
