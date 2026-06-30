# Task 138c: 剩余 orphan 最小修复

> **类型**: 代码 / 规则 / human mark 修复
> **状态**: 完成
> **前置**: Task 138b

## 背景

Task 138b 将基于 Task 138a 分类结果确定最小动作。本任务只实施已明确的最小修复，不扩大到无证据的全局规则放宽。

## 目标

让 Task 137 的剩余 orphan 有可验证收口，同时保护 critical/recurring/recovery_required 设定不被误 archive。

## 待办

- [x] 若根因为 background/technical 未 archive，修复 archive 触发或 ContinuityAuditor 过滤逻辑。
- [x] 若根因为 critical 未刷新/未合并，补充别名、canonical 同簇或正文引用检测规则，并避免伪匹配。
- [x] 若根因为人工保留项，写入 human mark 或等价事实源，不用代码静默吞掉。
- [x] 补充目标测试，覆盖修复分支和负例。
- [x] 必要时更新 prompt/card 文档。
- [x] 更新 Task 137 文档，记录修复内容、风险边界和测试结果。

## 实施摘要

- `src/songyan/db/continuity_repo.py`
  - `archive_long_silent_nonessential()` 改为保护所有 active unresolved setting human mark，不再只保护 `priority >= 8`。
  - 新增 `active_setting_mark_keys()`，供 ContinuityAuditor 在 orphan 扫描前查询人工保留/待回收事实源。
- `src/songyan/agents/continuity_auditor/_scanners.py`
  - 对非 `critical` / `recurring` 且存在 active unresolved human mark 的 setting，从自动 orphan 评分中豁免。
  - critical/recurring 仍保留为 orphan 候选，不 archive、不过滤。
- `src/songyan/agents/settlement_extractor/_apply.py`
  - 扩展 canonical/alias 同簇检测，覆盖 Task 138a/138b 指定表达：
    `巨型遗迹外层/表面/非欧几何合金`、`斐波那契序列频率/频率跳变序列`、
    `时空标记系统/非本地时空标记`、`墙壁能量纹路/遗迹墙壁活体特性`。
  - 保留负例边界：不使用裸 `频率`、裸 `墙壁`、裸 `巨型遗迹` 作为刷新依据。
- `src/songyan/agents/creative_director/__init__.py`
  - 回收输入加载 active unresolved setting human mark；即使未达到沉寂章数，也进入待回收列表。
  - 排序仍优先 critical/recurring，并在同类内提高 human mark priority。
- `tests/test_task137_setting_recycling.py`
  - 补充 Task 138c alias 正例/负例、active human mark archive 保护、ContinuityAuditor 豁免、CreativeDirector active mark 输入测试。

## 风险边界

- 未修改 Writer 生成策略，未做整章重写。
- 未修改 settlement numerical ledger 校验，`closing_value == formula` 硬校验保持不变。
- stale archive 仅作用于 `background` / `technical` 且 `recovery_required=0`、无 active human mark 的长期沉寂项；`critical` / `recurring` 不受影响。
- active human mark 项不被静默吞掉：非关键设定从自动 orphan 惩罚中豁免，但仍保留 human mark，并可进入 CreativeDirector 回收输入。
- alias 规则仅补窄同簇表达，不把宽泛词当作回收证据。

## 测试

- `python -m pytest tests/test_task137_setting_recycling.py -q`
  - 结果: `24 passed in 3.30s`
- `python -m pytest tests/test_task137_setting_recycling.py tests/test_task135_continuity_governance.py tests/test_continuity_health_governance.py -q`
  - 结果: `57 passed in 3.34s`
- `ruff check src/songyan/agents/settlement_extractor/_apply.py src/songyan/db/continuity_repo.py src/songyan/agents/continuity_auditor/_scanners.py src/songyan/agents/creative_director/__init__.py tests/test_task137_setting_recycling.py tests/test_task135_continuity_governance.py tests/test_continuity_health_governance.py`
  - 结果: `All checks passed!`
- `ruff check src/ tests/`
  - 结果: `All checks passed!`

## Task 138d 待验证指标

- 使用新的 `.tmp` 副本 DB，从 Ch10 accepted 锚点复跑 Ch10-Ch12。
- Ch11/Ch12 settlement、summary、quality gate 均通过。
- run log 中 `settlement_validation_errors=[]`。
- Ch12 continuity 相比 `run-4ba8de9d` baseline `orphaned=19`、`health=3.0` 下降或脱离 3.0；目标为 `orphaned < 19`，理想降至 8 以下或 health 脱离 3.0。
- 若指标未达成，回到 Task 138a 对新剩余 orphan 重新分类。

## 验收

- 目标测试通过。
- `ruff check` 对相关文件通过。
- 修复说明包含负例和保护边界。
- 可以进入 Task 138d 的 Ch10-Ch12 副本 DB 复跑。

---

## Round 2 / run-4fd48756

> **类型**: 第二轮代码 / 规则修复
> **状态**: 完成
> **前置**: Task 138b-R2；baseline 为 `run-4fd48756` Ch12 continuity `health=3.0`、`orphaned=16`

### 改动摘要

- `src/songyan/db/continuity_repo.py`
  - `archive_long_silent_nonessential()` 继续只处理 non-critical、non-recurring、`recovery_required=0` 的 stale background/technical 项。
  - active unresolved setting mark 的保护逻辑改为只保护人工 mark 或早于当前章节的 continuity diagnostic mark；当前 report 同章新建的 `continuity_auditor` mark 不再阻止 archive。
  - `active_setting_mark_keys()` 支持 `current_chapter`，供 ContinuityAuditor orphan 过滤区分“复跑前已有人工/历史 mark”和“当前 report 新建诊断 mark”。
- `src/songyan/agents/continuity_auditor/_scanners.py`
  - 调用 `active_setting_mark_keys(project_id, current_chapter=up_to_chapter)`，避免同章诊断 mark 永久豁免 non-critical stale orphan。
  - `critical` / `recurring` 仍不因 human mark 被过滤。
- `src/songyan/agents/settlement_extractor/_apply.py`
  - 收紧 `artifact.mega_ruin.surface_material` 的正文 refresh alias：保留“非欧几何合金碎片”“巨型遗迹表面的能量纹路”，移除“巨型遗迹表面”“巨型遗迹外层”等过宽词。
  - 继续禁止裸 `巨型遗迹`、裸 `能量纹路` 触发刷新。
- `src/songyan/agents/creative_director/__init__.py`
  - CreativeDirector 回收输入忽略当前章节同章新建的 continuity diagnostic mark。
  - stale critical setting 仍会基于沉寂章数和类别优先级进入章节生成前回收输入，不依赖同章 report 事后 mark。
- 测试补强：
  - `tests/test_task137_setting_recycling.py`
  - `tests/test_task135_continuity_governance.py`

### 风险边界

- 未 archive 或过滤 `critical` / `recurring` / `recovery_required=1`。
- 当前 report 新建的 non-critical diagnostic mark 不再永久豁免 stale orphan；复跑前已有人工 mark 或历史 continuity mark 仍可保护。
- `surface_material` alias 仅接受明确材料/纹路证据短语，不把宽泛地名或视觉 motif 当作回收。
- 未修改 Writer、RevisionHandler、LLMAuditor、settlement numerical ledger 或 workflow 节点。
- 本轮未执行 Ch10-Ch12 复跑，也未执行 Ch1-Ch20/default run。

### 测试

- `python -m pytest tests/test_task137_setting_recycling.py tests/test_task135_continuity_governance.py tests/test_continuity_health_governance.py -q`
  - 结果: `60 passed in 4.36s`
- `ruff check src/ tests/`
  - 结果: `All checks passed!`

### Task 138d-R2 待验证指标

- 使用新的 `.tmp` 副本 DB，从 Ch10 accepted 锚点复跑 Ch10-Ch12。
- Ch11/Ch12 settlement、summary、quality gate 均通过，`settlement_validation_errors=[]`。
- Ch12 continuity 相比 `run-4fd48756` baseline `orphaned=16` 下降；目标降至 8 以下或 health 脱离 `3.0`。
- 若 orphan 未下降或出现新阻断，回到 Task 138a-R3 重新分类，不直接扩大到 Ch1-Ch20/default run。
