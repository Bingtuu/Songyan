# Task 172k: C 维度判据证据补完（urban end15 / xuanhuan end10 / end20）

> **阶段**: V8 收口遗留
> **类型**: 实跑验证 / 判据收口
> **优先级**: P2（不阻塞 V9 开工，但阻塞"V8 五维全绿"的严格闭环表述）
> **依赖**: 172a.7 短窗口 harness（`scripts/run_172a7_genre_validation.py`）
> **状态**: ✅ 完成（2026-07-18 收口：urban end15 15/15、xuanhuan end10 10/10、wuxia end20 20/20 gap=0，三档证据全部落盘；xuanhuan resolved=12 确认 172c.r 生效）
> **来源**: 2026-07-18 V8 完成度独立 review（文档交叉核对发现）

---

## 背景

V8 的 C（完成度）判据原文（`tasks/V8-README.md` 阶段验收判定表）要求 xuanhuan/wuxia/urban 三体裁：

- `--end 10` 全 accepted；
- `--end 15` 全 accepted；
- `--end 20` gap ≤ 1 且有明确 isolate 记录。

**现有证据 vs 判据的差距**（2026-07-18 review 实测核对）：

| 档位 | 判据要求 | 现有证据 | 缺口 |
|---|---|---|---|
| end 10 | 三体裁全 accepted | scifi/wuxia/urban 各 10/10（172a.7） | xuanhuan 无独立 end10 运行（只能从 base=13000 的 end15 15/15 推断） |
| end 15 | 三体裁全 accepted | xuanhuan 15/15 + 14/15（Ch2 瞬时 LLM 错误，已 isolate）；wuxia 15/15（172c.r 回归） | **urban 无任何 end15 记录** |
| end 20 | gap ≤ 1 + isolate 记录 | **全仓无任何 end20 实跑** | 整档缺失 |

验收状态行把判据中的 xuanhuan end10 换成了 scifi，且未声明这是对判据的收窄。需要补证据或正式收窄判据，二选一闭环。

**附加观察项**：172c.r 修复伏笔 resolve 机制后，回归只跑了 scifi/wuxia；xuanhuan Ch100 DB 中 `resolved=0` 系修复前实跑。本 Task 的 xuanhuan 补跑顺带确认 `foreshadowing_resolved` 事件 > 0。

---

## 目标

二选一收口（推荐 A）：

- **路径 A（补证据）**：补齐缺口档位的实跑，结果落盘并在 V8-README C 行补证据链接。
- **路径 B（收窄判据）**：若实跑成本不允许，正式修订 C 判据为"end10/end15 两档 + end20 划归 V9"，在 V8-README 记录收窄理由与决策日期。**不允许不声不响维持现状。**

---

## 前置条件

- `.env` 有可用 `LLM_API_KEY`（实跑为真实 LLM 调用，单档预计数十分钟）；不可用则直接走路径 B。
- 时序：172j 已定为 min 语义（当前注册表值下零行为变化），与 172k 实跑顺序不敏感；若 172j 改走锚定方案，172k 必须先跑。

## 执行清单（路径 A）

```powershell
# 1. xuanhuan 独立 end10（同时观察 resolved 事件）
python scripts/run_172a7_genre_validation.py --templates xuanhuan --end 10

# 2. urban end15
python scripts/run_172a7_genre_validation.py --templates urban --end 15

# 3. end20 一档：xuanhuan 或 wuxia 任选其一（推荐 wuxia，172c.s/t 标定最新）
python scripts/run_172a7_genre_validation.py --templates wuxia --end 20
```

每轮结果 JSON 落盘 `.tmp/172k_<genre>_end<N>.json`，判定口径与 172a.7 相同：accepted 率、halt 次数、budget 峰值、T9、overdue、CED。

### 达标线（与判据同标，不放宽）

- end10 / end15：全 accepted、0 halt（瞬时 LLM 错误允许 isolate 记录）；
- end20：gap ≤ 1 且有明确 isolate 记录；
- xuanhuan end10：`foreshadowing_resolved` 事件 > 0（确认 172c.r 在 xuanhuan 生效）。

---

## 执行记录

### 2026-07-18 urban end15（证据补完 2/3）✅ 达标

- 命令：`python scripts/run_172a7_genre_validation.py --templates urban --end 15 --output .tmp/172k_urban_end15.json`
- 结果落盘：`.tmp/172k_urban_end15.json`；临时库 `Temp/task172a7_urban_1e16xo79/songyan.db`；逐章日志 `logs/chapter_runs/run-439c8994.jsonl`
- 判定（对照 172a.7 口径）：

| 指标 | 值 | 判定 |
|---|---|---|
| accepted | 15/15（failed=[]，status=completed） | PASS |
| halt | 0（无 isolate 记录需求；抽查 Ch13-15 `gate_triggered=false`） | PASS |
| budget_used 峰值 | 0.982 < 1.0 | PASS |
| overdue | 1 | PASS |
| CED/1k | 3.6776（209 issues / 56,830 words，低于 sci-fi end10 的 9.60） | PASS |
| T9 | 6 | 记录项，见观察 |

- 观察（不阻塞 C 判据，供 V9 urban 标定参考）：
  - `context_emergency_count=17`（15 章连续触发，before_emergency 峰值 1.2792）：urban 未标定运行时 profile（注册表全默认，base_budget 8000 起步），与 xuanhuan Ch8 同类根因——溢出发生在不可裁核心；emergency 裁剪把 budget_used 压回 <1.0 且逐章五门全过，但 V9 应按 xuanhuan 路径标定 urban base_budget。
  - T9=6 构成：timeline_conflict 4（Ch6/8/9/12）+ meta_tag_leak 2（Ch8/10），duplicate_paragraph 0；分布零散（13/15 章为 0）。Q 判据 "T9 hard issue = 0" 原口径为 end10 矩阵，end15 档首次出现非零，建议 V9 urban 标定时一并复查。

### 2026-07-18 xuanhuan end10（证据补完 1/3）✅ 达标

- 首跑（13:02 启动）5 分钟内报 `[Errno 22] Invalid argument`，未产生任何章节记录，判定为瞬时环境问题；与 urban 并跑无共享 DB（每次运行独立 `tempfile.mkdtemp` 临时库）。
- 重跑（14:59 启动，15:44 落盘）：`.tmp/172k_xuanhuan_end10.json`；临时库 `Temp/task172a7_xuanhuan_c7k5rk9j/songyan.db`；逐章日志 `logs/chapter_runs/run-19fca3ff.jsonl`
- 判定（对照 172a.7 口径）：

| 指标 | 值 | 判定 |
|---|---|---|
| accepted | 10/10（failed=[]，status=completed） | PASS |
| halt | 0（逐章 gate_triggered=false） | PASS |
| budget_used 峰值 | 0.9755 < 1.0 | PASS |
| overdue | 0 | PASS |
| CED/1k | 5.3012（185 issues / 34,898 words，低于 sci-fi end10 的 9.60） | PASS |
| T9 | 0 | PASS |
| context_emergency | 0 次（xuanhuan 已标定 profile；对照 urban 未标定的 17 次） | PASS |

- **172c.r 生效确认（附加观察项闭合）**：临时库 `foreshadowings` 状态分布 planted=21 / resolved=12，`resolved=12 > 0` —— 伏笔 resolve 机制在 xuanhuan 体裁已恢复。

### 2026-07-18 wuxia end20（证据补完 3/3）✅ 达标

- 命令：`python scripts/run_172a7_genre_validation.py --templates wuxia --end 20 --output .tmp/172k_wuxia_end20.json`
- 结果落盘：`.tmp/172k_wuxia_end20.json`（15:56 启动，17:31 落盘）；逐章日志 `logs/chapter_runs/run-f5d3b3a0.jsonl`
- 判定（对照 172a.7 口径）：

| 指标 | 值 | 判定 |
|---|---|---|
| accepted | 20/20（failed=[]，status=completed，gap=0 ≤ 1，无需 isolate） | PASS |
| halt | 0（逐章 gate_triggered=false） | PASS |
| budget_used 峰值 | 0.9893 < 1.0 | PASS |
| overdue | 0 | PASS |
| CED/1k | 5.217（342 issues / 65,555 words，低于 sci-fi end10 的 9.60） | PASS |
| T9 | 0 | PASS |

- 观察（不阻塞 C 判据）：`context_emergency_count=23`（before_emergency 峰值 1.2685），与 urban end15 同类信号——wuxia 经 172c.s 标定后长章场景仍频繁触发 emergency 裁剪，但 budget_used 始终 <1.0 且逐章质量门全过；供 V9 按体裁深度调参参考。

> 运维注记：本日两轮实跑进程均在结果写盘后于解释器退出阶段挂死（残留 86 线程、零 CPU），疑似 LLM client 连接池非 daemon 线程未关闭；不影响落盘数据，已在确认结果后手动终止。后续实跑建议跑完后核对输出文件再清理进程。

---

## 验证

- 三份实跑 JSON 的关键指标摘录进本 Task 执行记录；
- V8-README C 行证据列更新为含 end20 的完整链路（或判据修订 diff）；
- `docs/STATUS.md` 最新证据表同步。

---

## 出口标准

1. C 判据三档均有落盘证据，或判据修订已记录理由；
2. V8-README / STATUS 的 C 行表述与实际证据严格一致（不再有未声明的收窄）；
3. xuanhuan resolve 机制实跑确认。

**2026-07-18 收口判定**：三条全部满足 —— 三档证据落盘（`.tmp/172k_xuanhuan_end10.json` / `.tmp/172k_urban_end15.json` / `.tmp/172k_wuxia_end20.json`）；V8-README 与 `docs/STATUS.md` 的 C 行已同步为实际证据链；xuanhuan end10 实跑 `resolved=12 > 0`。

---

## 撞墙路由

| 风险 | 触发信号 | 处理 |
|---|---|---|
| end20 出现系统性 halt | budget/health/overdue 门禁连续触发 | 不硬跑；按信号路由开定点修复子任务（172k.p 起），判据缺口如实保留 |
| urban end15 质量不达标 | accepted < 15/15 或 CED 显著超 sci-fi 量级 | urban 未标定过运行时 profile（注册表为全默认），先查 base_budget 是否需按 xuanhuan 路径标定；需要时开 172k.q 标定 |
| xuanhuan resolved 仍为 0 | end10 无 resolved 事件 | 172c.r 在 xuanhuan 体裁未生效，转缺陷排查（不阻塞 C 判据本身） |
| LLM 成本/时间不允许 | — | 走路径 B，判据修订 + 理由落档 |
