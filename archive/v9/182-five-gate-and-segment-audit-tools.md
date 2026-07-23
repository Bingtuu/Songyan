# Task 182: 五门判定器与段审计收编

> **阶段**: V9.3 爬坡工具链
> **类型**: 工具链收编 / 验收口径固化 / 回归重放
> **优先级**: P1（V9 A7：五门判定器 + 段审计从 `.tmp/` 收编为正式工具）
> **依赖**: 173-181 已完成；178 资源打包已支持包内 JSON；181 CI/mypy 已上线
> **状态**: ✅ 完成（DONE: `archive/v9/182-five-gate-and-segment-audit-tools-DONE.md`）
> **来源**: `tasks/V9-README.md` Task 182 行；V8 172b/172c Ch100 五门终判经验

---

## 任务边界

本任务把 V8 遗留在 `.tmp/` 的两个人工验收工具收编为 V9 正式工具：

1. `.tmp/vdim_compare.py` → 正式五门判定工具，支持参数化 DB、project、genre、baseline、up_to。
2. `.tmp/segment_audit.py` → 正式段边界审计工具，支持任意项目的 CED 热点、next-audit orphan 预测、health 轨迹输出。
3. sci-fi Ch1-Ch100 冻结基线 JSON 从 `.tmp/` 迁到正式包内资源，作为 V9/V10 中篇爬坡共同基线。
4. 对 xuanhuan / wuxia 既有 Ch100 DB 做重放，输出与 V8 归档报告一致。

不做：

- 不改变五门冻结口径、阈值或容忍系数。
- 不跑新的真实 LLM 章节生成。
- 不修复 xuanhuan / wuxia 历史 DB 数据。
- 不实现 `songyan profile` CLI；那是 Task 183。
- 不实现 JSON Schema；那是 Task 184。

## 当前事实

- 原型五门工具：`.tmp/vdim_compare.py`
  - 默认通过 `TEMPLATE_ID` 推导 `.tmp/task172b_<genre>_ch100.db` 与 `.tmp/task172b_<genre>_project.json`。
  - 默认 sci-fi DB 为 `.tmp/task171_ch1_ch200.db`，project 为 `835afdf11a294b5eac74a5d8998bd9a2`。
  - 读取 `.tmp/scifi_ch100_baseline.json`，但会重新从 sci-fi DB 计算 consistency-only CED，并覆盖 baseline JSON 里的旧 CED。
  - 五门：budget、CED、overdue、health、completeness。
- 原型段审计工具：`.tmp/segment_audit.py`
  - 当前硬编码 xuanhuan DB 和 project id。
  - 输出 CED hotspot chapters、next continuity audit orphan prediction、health trajectory。
- 冻结报告：
  - xuanhuan Ch100：`archive/v8/reports/172b-xuanhuan-ch100-climb.md`
  - wuxia Ch100：`archive/v8/reports/172c-wuxia-ch100-climb.md`
- 既有验证 DB：
  - xuanhuan：`.tmp/task172b_xuanhuan_ch100.db`，project `1e7ce6279b224e7f8e476f6f4e963417`
  - wuxia：`.tmp/task172b_wuxia_ch100.db`，project `273a8408be8e4caf8cbc1e91954da600`
  - sci-fi baseline DB：`.tmp/task171_ch1_ch200.db`，project `835afdf11a294b5eac74a5d8998bd9a2`

## 关键口径

Task 182 的核心约束是 **I/O 可重构，判定函数零漂移**：

| gate | 判据 | 不可改变点 |
|---|---|---|
| completeness | `accepted >= up_to - 1`；gap > 1 进入 documented-isolate 复核 | 不把 gap 静默算 PASS |
| budget | `budget_used_peak < 1.0` 且无 halt | 不因体裁放宽 budget 上限 |
| CED | target consistency-only CED <= sci-fi 同章尺度 CED * 1.15 | consistency-only、merged/source、正文证据；排除文学 craft 与 `rule-mr-*` 聚合项 |
| overdue | target overdue <= sci-fi 同章尺度 overdue | 不套短窗口 `<5` 口径 |
| health | latest health 非 None 且 >= 8.0 | 不按体裁降阈值 |

### baseline 迁移纪律

`.tmp/scifi_ch100_baseline.json` 中的 `ced_per_1k_words` 是早期宽口径（Ch100 约 9.1328），不能原样作为正式 CED 基线。正式 baseline JSON 必须满足以下之一：

1. 存储 corrected consistency-only CED（Ch100 归档口径约 0.3976，157 issues / 394,839 words），并保留旧宽口径为 `legacy_ced_per_1k_words`（如需要审计）。
2. 或工具强制要求 `--baseline-db` + `--baseline-project-id`，每次从 sci-fi DB 重算 consistency-only CED。

本任务优先方案是 1：把 corrected sci-fi Ch25/50/75/100 基线冻结为包内 JSON，并在测试中证明读取该 JSON 不需要 `.tmp/task171_ch1_ch200.db`。

## 设计方案

### 1. 正式代码结构

建议拆成“可测核心 + 脚本入口”：

| 路径 | 职责 |
|---|---|
| `src/songyan/evals/five_gate_acceptance.py` | 五门指标读取、sci-fi baseline 插值、gate 判定、JSON/human report 数据结构 |
| `src/songyan/evals/segment_audit.py` | CED hotspot、next-audit orphan prediction、health trajectory 的纯函数 |
| `src/songyan/evals/baselines/scifi_ch100_baseline.json` | 正式 sci-fi Ch1-Ch100 baseline |
| `scripts/five_gate_check.py` | CLI wrapper；参数解析；human/JSON 输出 |
| `scripts/segment_audit.py` | CLI wrapper；参数解析；human/JSON 输出 |

说明：

- 正式工具可以不接入 `songyan` 主 CLI，先保持脚本工具形态，符合 V9 A7。
- 核心模块不写 `print`，脚本入口负责输出。
- SQLite 只读查询，不调用 `init_schema()`，不迁移历史 DB。
- 历史 DB 访问必须优先使用 SQLite URI 只读模式（`file:<path>?mode=ro` + `uri=True`）；读不到时 fail fast，不创建空 DB。
- `DATABASE_URL` 可在脚本入口临时设置，但核心函数显式接收 `db_path`，避免隐藏状态。

### 2. `five_gate_check.py` 参数

```powershell
python scripts/five_gate_check.py `
  --genre xuanhuan `
  --db .tmp/task172b_xuanhuan_ch100.db `
  --project-id 1e7ce6279b224e7f8e476f6f4e963417 `
  --up-to 100 `
  --baseline src/songyan/evals/baselines/scifi_ch100_baseline.json
```

必需参数：

- `--genre <id>`：只作为报告标签，不影响判定阈值。
- `--db <path>`：target DB。
- `--project-id <id>`：target project。
- `--up-to <n>`：判定章节上限。

可选参数：

- `--baseline <path>`：默认使用包内 sci-fi baseline JSON。
- `--format text|json`：默认 text；CI/回归可用 JSON。
- `--allow-gap 1`：默认 1，显式参数但默认值必须等同 `.tmp/vdim_compare.py`。

输出字段至少包含：

- `verdict`: `PASS` / `FAIL`
- `final`: `up_to >= 100`
- `gates`: 每门 `passed`、target 值、baseline 值、threshold
- `metrics`: accepted、budget peak、CED issue/words、overdue、health、gap

### 3. `segment_audit.py` 参数

```powershell
python scripts/segment_audit.py `
  --db .tmp/task172b_xuanhuan_ch100.db `
  --project-id 1e7ce6279b224e7f8e476f6f4e963417 `
  --up-to 75 `
  --top 8
```

输出字段至少包含：

- `hotspots`: legacy evidence hotspot top N by chapter，沿用 `.tmp/segment_audit.py` 的 all-version critical/major evidence count；它是段审计定位信号，不等同五门 CED gate。
- `next_audit_chapter`: `((up_to // 3) + 1) * 3`。
- `critical_orphans` / `total_orphans`。
- `halt_would_fire`: critical orphan 是否非零。
- `health_trajectory`。

### 4. 回归重放

正式工具必须在现有 DB 上复现 V8 归档结论：

| genre | up_to | expected |
|---|---:|---|
| xuanhuan | 100 | PASS；accepted 100/100；budget 0.981；CED 0.4434 <= 0.3976 * 1.15；overdue 166 <= 168；health 9.1 |
| wuxia | 100 | PASS；accepted 100/100；budget 0.965；CED 0.17；overdue 35 <= 168；health 8.3 |

还需要用同库对比 `.tmp/vdim_compare.py`：

- xuanhuan: `python .tmp/vdim_compare.py 100`
- wuxia: `$env:TEMPLATE_ID='wuxia'; python .tmp\vdim_compare.py 100`

参数化版本的每门 PASS/FAIL、关键数值与原脚本/归档报告一致；允许 text 输出格式不同，但 JSON 数值应可机器比对。

## TDD 测试计划

1. 针对 baseline 插值写单元测试：Ch25/50/75/100 命中原点，Ch37 线性插值 overdue/CED，budget 取区间峰值。
2. 针对 CED accepted source 选择写小型 SQLite fixture：
   - accepted wrapper 无 report，parent 有 merged report，应计 parent。
   - merged/source 优先，避免 llm + merged 双计数。
   - craft issue、`rule-mr-*`、无正文 evidence 的 issue 不计入 CED。
3. 针对五门判定写纯函数测试：budget fail、CED fail、gap > allow_gap、health None 均可单独失败。
4. 针对段审计写小型 SQLite fixture：hotspot 排序、next audit 计算、critical orphan 阈值。
5. 针对脚本参数写 smoke 测试：`--format json` 输出可解析；缺 required 参数返回非零。
6. 针对只读 DB 访问写回归测试：目标路径不存在时必须报错，不得创建空 SQLite 文件。
7. 本地验收使用真实 `.tmp` DB 重放 xuanhuan/wuxia Ch100；这类测试不放进默认 CI，避免依赖未跟踪大 DB。

## 验证命令

```powershell
python -m pytest tests/test_182_five_gate_tools.py -q
python scripts/five_gate_check.py --genre xuanhuan --db .tmp/task172b_xuanhuan_ch100.db --project-id 1e7ce6279b224e7f8e476f6f4e963417 --up-to 100 --format json
$env:TEMPLATE_ID = "wuxia"
python .tmp\vdim_compare.py 100
python scripts/five_gate_check.py --genre wuxia --db .tmp/task172b_wuxia_ch100.db --project-id 273a8408be8e4caf8cbc1e91954da600 --up-to 100 --format json
python scripts/segment_audit.py --db .tmp/task172b_xuanhuan_ch100.db --project-id 1e7ce6279b224e7f8e476f6f4e963417 --up-to 100 --format json
Remove-Item Env:TEMPLATE_ID -ErrorAction SilentlyContinue
python -m pytest tests/ -q
python -m pytest tests/cli -q
mypy src/
ruff check src/ tests/ scripts/five_gate_check.py scripts/segment_audit.py
```

Windows 长测如卡住，默认使用 Task 176 wrapper：

```powershell
powershell -NoProfile -File scripts\run_with_timeout.ps1 -TimeoutSec 1800 -DetectPytestSummary -- python -m pytest tests/ -q
```

## 验收判据

- `scripts/five_gate_check.py` 与 `scripts/segment_audit.py` 可从仓库根目录直接运行。
- 五门工具不依赖 `TEMPLATE_ID`、不依赖 hardcoded project id。
- 传入不存在的 DB 路径不会创建新 DB，命令以非零退出并给出清晰错误。
- 默认 baseline 从正式包内 JSON 读取；非仓库 cwd 下仍可通过 `importlib.resources` 加载。
- xuanhuan/wuxia 既有 Ch100 DB 重放 PASS，数值与归档报告一致。
- 参数化版本与 `.tmp/vdim_compare.py` 在同库同 up_to 的 PASS/FAIL 逐门一致。
- 段审计工具对 xuanhuan Ch100 能输出 hotspot、next-audit orphan、health trajectory。
- 默认 pytest、CLI pytest、mypy、ruff 全绿。

## 执行记录（2026-07-20）

- 新增 `src/songyan/evals/five_gate_acceptance.py`：
  - 正式收编五门判定核心逻辑；
  - 用 SQLite URI 只读模式打开历史 DB，不调用 `init_schema()`；
  - CED 使用 consistency-only / merged-source / 正文证据口径；
  - budget gate 补充 halt 检测：读取 `adaptive_halt_decisions.status='halt'` 与 `project_runs` paused/failed 兜底。
- 新增 `src/songyan/evals/segment_audit.py`：
  - 正式收编段审计核心逻辑；
  - 保留 legacy evidence hotspot（all-version critical/major evidence count）语义，不与五门 CED 混用；
  - `--up-to` 显式传入时仍校验 project accepted 边界，防止伪造 Ch999 审计结果。
- 新增 `src/songyan/evals/baselines/scifi_ch100_baseline.json`：
  - corrected CED：Ch25/50/75/100 = 0.3309 / 0.3570 / 0.3878 / 0.3976；
  - 保留旧宽口径 `legacy_ced_per_1k_words` 供审计追溯。
- 新增 `scripts/five_gate_check.py` 与 `scripts/segment_audit.py`：
  - 支持 `--db`、`--project-id`、`--up-to`、`--format json|text`；
  - 五门工具额外支持 `--genre`、`--baseline`、`--allow-gap`。
- 新增 `tests/test_182_five_gate_tools.py`，覆盖 baseline 插值、parent review source、merged/source 去重、只读 DB 缺失不创建文件、halt gate、segment up_to 边界与脚本 JSON smoke。

### Code Review 记录

`bits-code-guard` review 发现并修复：

1. P2：`segment_audit --up-to` 显式传入时绕过 project evidence 边界校验；已改为始终读取 max accepted，并对未知 project、`up_to < 1`、`up_to > max_accepted` fail fast。
2. 本地 review 补充：五门 budget gate 的 `halt` 字段未从 DB 读取；已接入 `adaptive_halt_decisions` 与 `project_runs` 兜底，并补回归测试。

报告产物：

- `.tmp/code_guard_182/report.html`
- `.tmp/code_guard_182/report.md`

### 验证结果（2026-07-20）

| 项 | 结果 |
|---|---|
| 聚焦测试 | `python -m pytest tests/test_182_five_gate_tools.py -q` → **10 passed** |
| xuanhuan 五门重放 | `python scripts/five_gate_check.py --genre xuanhuan ... --up-to 100 --format json` → **PASS**；accepted 100/100、budget 0.9811、CED 0.4434、overdue 166、health 9.1 |
| wuxia 五门重放 | `python scripts/five_gate_check.py --genre wuxia ... --up-to 100 --format json` → **PASS**；accepted 100/100、budget 0.9646、CED 0.1662、overdue 35、health 8.3 |
| 原型对照 | `.tmp/vdim_compare.py 100` 对 xuanhuan/wuxia 均 **PASS**，逐门结果与正式工具一致 |
| 段审计 | `python scripts/segment_audit.py --db .tmp/task172b_xuanhuan_ch100.db ... --up-to 100 --format json` → 输出 hotspot / next_audit / health trajectory |
| mypy | `mypy src/` → **Success: no issues found in 174 source files** |
| Ruff | `ruff check src/ tests/ scripts/five_gate_check.py scripts/segment_audit.py` → **All checks passed** |
| 默认全量 pytest | Task 176 wrapper → **2914 passed, 2 skipped, 1 xfailed, 7 warnings**；`WRAPPER_RESULT=PASS_NORMAL_EXIT` |
| CLI 测试 | `python -m pytest tests/cli -q` → **35 passed** |

## 撞墙路由

| 风险 | 触发信号 | 处理 |
|---|---|---|
| baseline CED 口径污染 | 正式 JSON 仍使用 9.x 宽口径 CED | 重新从 sci-fi DB 用 consistency-only helper 生成 corrected baseline；旧值只能作为 legacy 字段 |
| 工具读取历史 DB 时写入 schema | DB mtime 变化或新增表/索引 | 禁止调用 `init_schema()`；所有查询用 SQLite URI 只读连接 |
| `.tmp` 原脚本与正式工具数值不一致 | xuanhuan/wuxia 某门 PASS/FAIL 漂移 | 先定位是否为输出格式、baseline CED 修正或 accepted source 选择差异；判定函数不得为追平格式而改口径 |
| CI 依赖 `.tmp` 大 DB | 默认测试在 clean checkout 缺 DB | 真实 DB 重放只做本地验收；CI 用小型 fixture 覆盖算法 |
| 段审计 hardcoded threshold 漂移 | orphan prediction 与历史脚本不同 | Task 182 先复制冻结阈值；后续若要统一到 production scanner 常量，必须增加同库回归证明无漂移 |

## Out of Scope

- 新增 `songyan five-gate` 或 `songyan audit` 主 CLI 子命令。
- 修改五门阈值、CED tolerance、health 门槛。
- 重新生成 sci-fi/xuanhuan/wuxia Ch100 DB。
- 将 `.tmp` 历史 DB 纳入 Git。
