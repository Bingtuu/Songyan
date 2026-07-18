# Task 172j: BudgetPruner max_* 生产路径遮蔽与 DB 覆盖层降回边界修复

> **阶段**: V8 后续 / V9 前置
> **类型**: 技术债清理 / 缺陷修复
> **优先级**: P1（阻塞 V9 按体裁深度调参：调这三个字段不会产生任何行为差异）
> **依赖**: 172e 完成（接线已存在，本 Task 修"生效性"）
> **状态**: ✅ 完成（2026-07-18）
> **来源**: 2026-07-18 V8 完成度独立 review（代码审计 + DB 复核 + 文档交叉核对）；同日设计复核完成前置量化

---

## 背景

172e 把 `max_soft_refs` / `max_foreshadowing` / `max_character_states` 接入了 `BudgetPruner._prune_*`，并设定优先级 **传入参数 > profile 值 > 模块常量**。但主 assemble 路径调用 `prune()` 时**总是显式传入** `_dynamic_max_for_chapter()` 派生的动态上限（`src/songyan/agents/context_manager/__init__.py:1238-1246`），导致这三个字段的 profile 值在生产链路被完全遮蔽，只在不显式传参的调用（单测）中生效。

**实测后果**：注册表中 wuxia / xuanhuan 的 `max_character_states=8`（`genre_runtime_profile_repo.py:85`、`:60`）在生产中未生效。172c.s 实际靠 `focal_gaps=8/20/60` 承载角色密度调节，五门 PASS 未受影响——所以这不是 V8 验收的反证，而是 V9 调参链路的坑：**届时往 DB/profile 写这三个字段，行为不会变**。

第二问题（同源，本 Task 只做文档化收口）：`load_profile()` 的 DB 覆盖以"与**全新代码默认模型**的 diff"为基准（`genre_runtime_profile_repo.py:207-216`），DB 存的是全量 `profile_json`、没有"哪些字段是显式提供"的信息，因此无法把注册表调优值**降回**代码默认（往 DB 写 xuanhuan `base_budget=8000` 会被视为"未覆盖"而保留 15000）。

---

## 前置量化（设计复核已完成，结论在此固化）

`_dynamic_max_for_chapter()`（`context_manager/__init__.py:99-111`）实际输出：

| 章节段 | max_setting_input | max_foreshadowing | max_character_states |
|---|---|---|---|
| Ch1-80 | 10（=常量） | 8（=常量） | 4（=常量） |
| Ch81+ | 6 | 5 | 3 |

对照注册表 profile 值（wuxia/xuanhuan `max_character_states=8`，其余字段两体裁均用默认值 10/8/4）：

- **profile=8 恒不小于动态值**（Ch1-80 动态=4、Ch81+ 动态=3，均 < 8）。
- 因此 `min(dynamic, profile)` 语义下 profile=8 **永远不被选中**——方案 A 对当前注册表值是**零行为变化**。
- 反之，要让"8 真正生效"（Ch1-80 从 4 放宽到 8）必须走方案 B（锚定动态曲线），那会**真实改变生产行为**，需要短窗口重新标定。

DB 降回边界的设计复核结论：**改 diff 基准不可行**。若把基准从代码默认改为注册表基线，则"用户从代码默认出发只改一个字段"的常规调参会误伤——例如只改 `health_overdue_weight=0.2` 时，记录里的 `base_budget=8000`（代码默认）会被判为"显式低于注册表 15000"而误降预算。当前实现对全量 JSON 存储是自洽的，真正的修法是稀疏覆盖存储（只存 diff），超出本 Task 范围。

---

## 目标

1. 三个 `max_*` 字段以**体裁级收紧上限**语义接入生产路径：调低到旧常量基线以下立即生效；调高由章节动态曲线接管（不生效）。当前注册表值下生产行为零变化。
2. 用 wuxia 短窗口实跑回答标定问题："`max_character_states` 4→8 是否有质量收益"——有则另开锚定方案 Task，无则在注册表注释中固化"8 为待标定占位，当前由动态值承载"。
3. DB 降回边界：文档化（`load_profile()` docstring + README 三层配置节），不改语义；稀疏覆盖存储如需要另开 Task。
4. 无 profile 体裁 100% 回退旧行为（scifi 回归逐值等价）。

---

## 技术方案

### 1. 收紧上限语义接入（主改动，已实现）

新增两个模块级函数（`src/songyan/agents/context_manager/__init__.py`，`_dynamic_max_soft_refs` 之后）：

```python
def _apply_profile_cap(dyn_value, profile_value, legacy_const):
    # profile < 旧常量 → min(dyn, profile) 收紧生效
    # profile ≥ 旧常量 → dyn 接管（调高不生效）
    if profile_value is None or profile_value >= legacy_const:
        return dyn_value
    return min(dyn_value, profile_value)

def _effective_hard_caps(chapter_number, total_settings, runtime_profile):
    # 章节动态曲线 + profile 收紧上限的合成结果，生产路径唯一来源
```

接线点：`_dyn_caps = _effective_hard_caps(ch, len(setting_snapshots), runtime_profile)`（伏笔入站过滤 `max_foreshadowing`、setting 入站 `max_setting_input` 同源）；`_dyn_max_char` / `_dyn_max_soft` 改从 `_dyn_caps` 取。

**开发期关键发现（修正原 min 方案）**：`_dyn_max_soft` 来自 `_dynamic_max_soft_refs()`，动态区间 **10-16**，而 scifi profile 默认 `max_soft_refs=10`——若直接 `min(dynamic, profile)` 会把 scifi 从 16 静默收紧到 10，破坏"无 Profile 体裁 100% 回退旧行为"。因此最终语义是"**仅调低到旧常量基线以下时生效**"而非裸 min：三个字段统一，scifi 逐值等价，且调低能力对三字段全部真实生效。

**语义写清**：profile 这三个字段是"收紧上限"——调低到旧常量基线以下立即生效、调高不生效（调高属于锚定方案，需重新标定）。docstring 与 README 已同步。

### 2. 标定实跑（只读对比，不改代码）

wuxia `--end 15` 两轮对比（用 DB 覆盖层临时把 `max_character_states` 设为 4 与 8 各跑一轮——但注意 min 语义下 8 不生效，所以本轮实际是"当前 4"对"锚定模拟 8"不可行；**改为**：直接在 `.tmp/` 用 harness  monkeypatch 常量做对比，或接受"4 已验证五门 PASS"的事实，把 8 标为待标定）。倾向后者：**零实跑成本收口**——V8 已证明 4（动态值）下 wuxia/xuanhuan Ch100 五门 PASS，没有证据表明 8 有收益；注册表保留 8 但注释其语义为"待标定，当前不生效"。

### 3. DB 降回边界文档化

- `load_profile()` docstring 补一段：DB 覆盖以代码默认值为 diff 基准，因此**无法把注册表调优值降回代码默认**；如需降回，改代码注册表。
- README「三层配置」节补同一句话。

### 4. 回退策略

无 profile 项目走原路径（动态值直传），逐值等价。scifi profile 三个字段默认值 = 旧常量（10/8/4），均满足"≥ 旧常量 → 动态接管"，行为逐值不变；`tests/test_172j_pruner_max_shadowing_fix.py` 用 scifi/None profile 对 Ch1/Ch81 × settings 0/20/100 全组合做逐值断言。

---

## 验证

### 测试（TDD）

新建 `tests/test_172j_pruner_max_shadowing_fix.py`：

- profile `max_character_states=3`（低于动态值 4）→ 生产 assemble 路径硬上限变为 3（调低生效）；
- profile `max_character_states=8`（高于动态值 4）→ 硬上限仍为 4（min 语义，调高不生效）；
- `max_soft_refs` / `max_foreshadowing` 各一个调低生效测试；
- 无 profile → 动态值逐值不变（回归基线）；
- scifi profile 默认 → 与无 profile 行为逐值等价。

### 回归命令

```powershell
python -m pytest tests/test_172j_pruner_max_shadowing_fix.py tests/test_172e_context_manager_profile_wiring.py -q
python -m pytest tests/ -q
ruff check src/ tests/
python scripts/run_172a7_genre_validation.py --templates scifi --end 10
```

### 验收判据

- pytest 全绿、ruff 无新增 error；
- scifi `--end 10` 10/10、budget Ch1=8250（legacy 公式不变）；
- min 语义下 wuxia/xuanhuan 生产行为零变化（由"profile=8 恒不小于动态值"的量化结论 + scifi 回归共同保证，无需额外长跑）。

---

## 出口标准

1. 三个 `max_*` 字段 min 语义接入生产路径，调低生效有测试断言；
2. DB 降回边界已文档化（docstring + README）；
3. scifi 回归逐值等价；
4. 本 Task 执行记录（含"8 标为待标定"的决策）补录到本文档，注册表注释同步。

---

## 撞墙路由

| 风险 | 触发信号 | 处理 |
|---|---|---|
| min 语义实现位置误判（`_dyn_max_soft` 来源不明） | 测试中 profile 调低不生效 | 回到 `_dynamic_max_for_chapter` 调用链逐层核对，必要时把 soft_refs 纳入该函数统一派生 |
| scifi 回归漂移 | `--end 10` 非 10/10 或 Ch1 budget ≠ 8250 | 回滚，检查回退路径是否逐值等价 |
| 后续认为 8 应有收益 | V9 调参时提出 | 另开锚定方案 Task（动态曲线基准从 profile 派生），先短窗口标定再落地 |


---

## 执行记录（2026-07-18）

### 落地内容

1. **收紧上限语义接入生产路径**：新增 `_apply_profile_cap()` / `_effective_hard_caps()`（`src/songyan/agents/context_manager/__init__.py`，`_dynamic_max_soft_refs` 之后）；`_dyn_caps` 改由 `_effective_hard_caps(ch, len(setting_snapshots), runtime_profile)` 提供，伏笔入站过滤、`_dyn_max_char`、`_dyn_max_soft` 三处同源取值。
2. **开发期发现并修正原 min 方案**：`_dynamic_max_soft_refs` 动态区间 10-16 超过 scifi profile 默认 `max_soft_refs=10`，裸 min 会把 scifi 静默收紧。最终语义统一为"**profile 仅调低到旧常量基线以下时生效，调高由章节动态曲线接管**"，scifi 逐值等价。
3. **DB 降回边界文档化**：`load_profile()` docstring 补"无法把注册表调优值降回代码默认"边界；README 三层配置节同步；注册表 wuxia/xuanhuan `max_character_states=8` 加"调高不生效、待 V9 标定"注释。
4. **标定决策**：采纳零实跑成本收口——动态值（4/8/10 常量曲线）下 wuxia/xuanhuan Ch100 五门 PASS 已被 V8 实证，无证据表明 8 有收益；注册表保留 8 待 V9 锚定方案标定。

### 验证结果

| 项 | 结果 |
|---|---|
| 新增测试 `tests/test_172j_pruner_max_shadowing_fix.py` | **10 passed**（含 scifi/None profile 逐值等价、调低生效、调高不生效、注册表 8 不生效固化） |
| 聚焦回归（172j+172e+context_manager） | 99 passed |
| 全量 `python -m pytest tests/ -q` | **2801 passed, 2 skipped, 1 xfailed**（较基线 2791 +10，即 172j 新增） |
| `ruff check src/ tests/` | All checks passed |
| scifi `--end 10` 实跑回归（`.tmp/172j_scifi_end10.json`） | **10/10 accepted**、0 failed、t9=0、overdue=0、budget peak 0.9984<1.0、Ch1 budget=8250=legacy 公式（旧行为逐值不变） |

### 验收判据核对

- pytest 全绿、ruff 无新增 error ✅
- scifi `--end 10` 10/10、budget Ch1=8250 ✅
- min（收紧上限）语义下 wuxia/xuanhuan 生产行为零变化 ✅（量化结论 + 注册表值断言 + scifi 实跑共同保证）
