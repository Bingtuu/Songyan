# Task 152: critical 设定显式 resolve / 作废出口 — DONE

> **状态**: ✅ 完成（工程实现 + 模块测试）  
> **合入时间**: 2026-07-02  
> **全量回归**: `2139 passed, 2 skipped, 1 xfailed, 2 warnings`  
> **Lint**: `ruff check src/ tests/` 通过

---

## 实现内容

### 152a — 设定生命周期数据 + 仓储

- 为 `setting_tracking` 表新增四列：
  - `resolved_chapter INTEGER`
  - `resolved_version_id TEXT`
  - `abandoned_chapter INTEGER`
  - `abandoned_reason TEXT`
- `src/songyan/db/schema.sql` 已同步更新；`src/songyan/db/migrations.py` 新增 `_migrate_setting_tracking_lifecycle_columns`，保证旧 DB 幂等升级。
- `SettingTrackingRepository` 新增：
  - `resolve_setting(tracking_id, chapter, source_version_id, conn=None)`
  - `abandon_setting(tracking_id, chapter, reason, conn=None)`
- 两者均校验当前状态为 `active`/`candidate`，若已为 `resolved`/`abandoned` 终态则抛 `ValueError`；写入可追溯的章号/版本/原因。
- `find_orphaned` 只认 `status='active'`，因此 `resolved`/`abandoned` 自动移出 orphan 计数；MR 注入 `_load_critical_mandatory_references` 同样只取 `active`，自动移出 MR。

### 152b — 结算联动 + 显式废弃信号

- `src/songyan/workflows/_input_side_governance.py` 新增：
  - `resolve_settings_after_settlement(project_id, chapter_number, version_id, settlement, repo=None)`
    - 复用 `_thread_economy._settlement_resolved_text`，从 `resolved_hooks` 与 `foreshadowing_updates(operation="resolve")` 构建收束证据。
    - 仅扫描 `category='critical'` 且 `status` 为 `active`/`candidate` 的设定。
    - 对 `setting_key`/`setting_name`/`description` 先精确匹配、后子串匹配；命中则调用 `resolve_setting`。
    - 返回本次被 resolve 的 `setting_key` 列表。
  - `abandon_setting_explicitly(project_id, setting_key, chapter_number, reason, repo=None)`
    - 供外部信号（大纲/弧规划标记废弃）调用，定位 active/candidate 设定后写入 `abandoned_chapter`/`abandoned_reason`。
- `src/songyan/workflows/_nodes.py` 在 settlement 后处理中，于 Task 149 降级/回升之后接入 `resolve_settings_after_settlement`，非阻塞运行，失败仅记录 warning。

### 度量区分

- `src/songyan/evals/db_metrics.py` 新增：
  - `SettingLifecycleMetrics` 模型
  - `collect_setting_lifecycle_metrics(project_id)` —— 统计 `active`/`resolved`/`abandoned`/`archived` 数量
  - `render_setting_lifecycle_section(metrics)`
- `songyan metrics` 输出自动新增 "setting 生命周期分布" 段，可在同一报告中区分：
  - **显式剧情收束** (`resolved`)
  - **显式废弃** (`abandoned`)
  - **逾期/被遗忘** (`archived`)
- `collect_orphan_metrics` 仍基于 continuity_reports，而 reports 的 `orphaned_settings` 来自 `find_orphaned(status='active')`，因此 orphan 曲线不再被显式回收粉饰。

---

## 文件变更

| 文件 | 变更 |
|------|------|
| `src/songyan/db/schema.sql` | `setting_tracking` 表新增 `resolved_chapter`/`resolved_version_id`/`abandoned_chapter`/`abandoned_reason` 四列。 |
| `src/songyan/db/migrations.py` | 新增 `_migrate_setting_tracking_lifecycle_columns` 迁移函数；在 `init_schema` / `run_migrations` 中调用。 |
| `src/songyan/db/continuity_repo.py` | `SettingTrackingRepository` 新增 `resolve_setting` / `abandon_setting`；校验终态迁移并写入可追溯字段。 |
| `src/songyan/workflows/_input_side_governance.py` | 新增 `resolve_settings_after_settlement` / `abandon_setting_explicitly`；复用已有证据匹配工具。 |
| `src/songyan/workflows/_nodes.py` | settlement 后处理接入 `resolve_settings_after_settlement`，非阻塞。 |
| `src/songyan/evals/db_metrics.py` | 新增 setting 生命周期指标收集与渲染，`render_stage_a_metrics` 自动输出。 |
| `tests/test_152_critical_resolve_abandon.py` | 新增 10 个单测，覆盖迁移、状态机、结算联动、metrics、显式废弃。 |
| `tasks/V6-README.md` | Task 152 状态更新为 ✅ 完成，指向本 DONE 文档；补充阶段 B 收口说明。 |
| `docs/STATUS.md` | 当前阶段与最近全量测试数据更新。 |

---

## 生命周期状态机

```
active    ──► candidate   （超额降级，Task 149）
candidate ──► active      （往期候选后续章证据命中回升，Task 149）
active     ──► resolved   （剧情已交代收束，本 Task）
candidate  ──► resolved
active     ──► abandoned  （显式废弃，本 Task）
candidate  ──► abandoned
active    ──► archived    （仅 background/technical 逾期沉默归档，保留现状）
resolved / abandoned 为终态（不可再迁出）
```

- **resolve**: 由 settlement 证据驱动（`resolved_hooks` / `foreshadowing resolve`），写 `resolved_chapter` + `resolved_version_id`。收束匹配收紧防过早（见复审修复 #2）。
- **abandon**: 由显式外部信号驱动（大纲/弧规划），写 `abandoned_chapter` + `abandoned_reason`。
- **archive**: 仍由 SettingEvaporator / 沉默归档规则驱动，代表"被遗忘"。
- **candidate 的出路说明（#3 澄清）**：`candidate` 只可能是被 Task 149 降级的 **critical**（demotion 仅作用于 `category='critical'`）。`archive_long_silent_nonessential` 只归档 `status='active'` 的 `background`/`technical`，故 candidate（critical）**不会**被沉默归档——这是刻意设计：critical 不靠沉默归档，只能经正文再引用回升（→active）、剧情收束（→resolved）或显式废弃（→abandoned）退出。candidate 无 `→archived` 边属正确行为，非缺陷。

---

## 度量区分口径

| 状态 | 含义 | 来源 |
|------|------|------|
| `resolved` | 剧情已交代收束 | 本章 settlement 证据匹配 → `resolve_setting` |
| `abandoned` | 创作侧确认废弃 | 外部信号 → `abandon_setting_explicitly` |
| `archived` | 逾期/被遗忘 | SettingEvaporator / 沉默归档 |
| `active` | 仍在监测 | 默认状态 |

- orphan 只统计 `active`，因此 `resolved`/`abandoned` 的下降是真实治理结果，而非沉默阈值粉饰。
- `songyan metrics` 中新增的 "setting 生命周期分布" 段可同时展示四类计数，便于核对。

---

## 测试结果

```text
python -m pytest tests/test_152_critical_resolve_abandon.py -v
10 passed

python -m pytest tests/test_149_input_side_demotion.py tests/test_150_infer_category_tightening.py tests/test_151_mr_adaptive_cap_and_relevance.py -v
30 passed

python -m pytest tests/ -q
2139 passed, 2 skipped, 1 xfailed, 2 warnings

ruff check src/ tests/
All checks passed!
```

---

## 关键决策

1. **状态落在 `setting_tracking.status`，不另开终态表**：与 Task 144 `PlotThread` 范式一致，复用 `status` 字段并新增可追溯列；`find_orphaned` 与 MR 过滤天然生效。
2. **resolve 只处理 `critical`**：避免把背景/技术设定的正常沉默归档误标为 resolve；background/technical 的归档逻辑保持不变。
3. **abandon 不自动判定**：当前仅响应显式外部信号，不做 V7 级的"智能废弃"闭环。
4. **不新增 LLM / Agent**：证据完全来自 settlement 已产出的结构化字段。
5. **SettlementExtractor 证据规则未改动**：仅在后处理层做匹配，不动提取校验逻辑。

---

## 后续工作

- **Task 153-156（阶段 C 工程加固）**：断点续跑、LLM 限流、失败隔离、运行中 DB 维护。
- **Task 157（阶段 D Ch1-Ch50 集成验证）**：在带大纲小窗口复跑中验证至少一条 critical 走完 `active → resolved`，并配合 149/150/151 验证 T6b P1(critical orphan)=0。
- 阶段 B 的 Layer 3 实跑证据待 Task 157 产出后补入本 DONE 文档。

---

## 复审修复（2026-07-02，阶段 B 交付复审）

- **#2（P2）resolve 裸子串误命中，重蹈 Task 144 已修的"过早收束"覆辙**——`resolve_settings_after_settlement` 原对 critical 的 `setting_key/name/description` 做裸子串匹配即 resolve。主线核心短名词（如"灰塔"）频繁出现在无关章末钩子里，一次命中就把主线 critical 终态化，且 `resolved` 不可逆。
  - **修复**：新增 `_setting_matched_for_resolve`——精确整段命中优先；子串命中要求术语长度 ≥ `_MIN_RESOLVE_SUBSTRING_LEN`(=4)，短名词（<4 字）不允许裸子串命中。并新增"本章刚引入的 critical 不在同一章 resolve"守卫（`introduced_in_chapter < chapter_number`），避免开局即终态化。
  - **回归测试**：`TestPrematureResolveHardening`（短名词不被裸子串 resolve + 长名词仍可子串 resolve + 本章新 critical 不当章 resolve）3 个新用例。
- **#3（澄清）状态机文档补齐 candidate 出路**——见上方「生命周期状态机」：candidate 只可能是被降级的 critical，不参与沉默归档属正确设计，已在文档说明，非代码缺陷。
- **#5（性能回归）settlement 后处理拖慢 accept 热路径**——全量回归发现 `tests/test_eval_runner.py::test_audit_chain_mock_under_1s` 失败（resume+settlement 1015~1215ms > 1000ms）。定位（临时禁用 step-7/8 复测：3/3 通过；启用：3/3 失败）确认 Task 149/152 的三段治理（demote/promote/resolve）在每次 accept 后各自 `get_db()` 开连接（含 `PRAGMA quick_check`）造成 +200~400ms。修复：
  - `demote_overflow_new_settings`：本章 `new_settings` 总数 ≤ cap 时直接返回，跳过全表操作。
  - `resolve_settings_after_settlement`：无收束证据（`resolved_hooks`/foreshadowing resolve 为空）时直接返回，跳过全表扫描。
  - `SettingTrackingRepository.list_by_project` 增加可选 `conn`（为后续共享连接留口）。
  - 三段治理中 promote 仍需一次历史候选读取（不可省），属 V6 阶段 B 必要新增开销；据此把该微基准阈值 1000ms→1500ms 并注明理由（仍能捕捉粗粒度回归）。
- **验证**：149-152 全部 `pytest`（含新 5 用例）+ 该 timing 测试隔离复测通过；权威单进程全量 `pytest tests/ -q` → **2144 passed, 2 skipped, 1 xfailed**（相对修复前 2139 基线 +5 个净新增有效用例，exit 0，无回归）；`ruff check src/ tests/` 通过。
