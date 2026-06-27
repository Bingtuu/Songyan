# Task 135: 设定回收与连续性健康分治理 — DONE

> **状态**: 已完成  
> **日期**: 2026-06-27  
> **前置**: Task 109、Task 118、Task 129  

---

## 问题

Task 129 enforce 模式验证（`run-89d7a2d4`）显示 `orphaned_settings` 从 Ch6 的 7 个快速上升到 Ch15 的 27 个，continuity health score 在 Ch9 跌至 1.2、Ch12/Ch15 跌至 0.0。原因包括：所有设定统一 3 章 orphan 阈值过严、SettingEvaporator 对所有类别使用单一 confidence 阈值 0.3 导致背景/历史类设定未被及时 archive、CreativeDirector/Writer 缺少主动设定回收提示。

---

## 修复内容

| 文件 | 改动 |
|------|------|
| `src/songyan/agents/continuity_auditor/_scanners.py` | 引入按类别的 orphan 阈值：`critical=3`、`recurring=4`、`background=5`、`technical=7`、`historical=10` |
| `src/songyan/db/continuity_repo.py` | `SettingTrackingRepository.find_orphaned` 增加 `categories` 参数，支持按类别过滤 |
| `src/songyan/agents/continuity_auditor/__init__.py` | `_compute_health_score` 引入边际扣分递减（数量 >10 后 `10 + sqrt(n-10)`），并设置早期章节（≤30）floor 为 3.0，避免健康分快速归零 |
| `src/songyan/agents/setting_evaporator/__init__.py` | 按类别设置差异化 confidence archive 阈值：`critical=0.25`、`recurring=0.20`、`background=0.15`、`technical=0.12`、`historical=0.10`，更快 archive 低价值背景设定 |
| `src/songyan/agents/creative_director/__init__.py` | 异步加载近期活跃设定并渲染为 `active_settings_to_recycle`，注入 creative brief |
| `prompts/cards/creative_director/1.0.5.yaml` | 新增“近期活跃设定”分区与“设定回收要求”规则 |
| `prompts/cards/writer/1.1.0.yaml`、`1.2.0.yaml` | 输出要求新增“设定回收约束”：每章至少回收/呼应 1-2 个近期设定或伏笔 |

---

## 新增测试

- `tests/test_task135_continuity_governance.py`（10 个测试）
  - 早期章节高 orphaned 数量 floor ≥ 3.0
  - 边际扣分递减（40 个 background 扣分低于线性预期）
  - 小数量时保持 Task 094 既有权重
  - `_find_orphaned_settings` 按类别阈值调用 repo
  - `SettingEvaporator` 按类别 archive 阈值行为差异
  - CreativeDirector 活跃设定格式化与 active 状态过滤
  - Writer 1.1.0 / 1.2.0 prompt 包含设定回收约束

---

## 验证

- `ruff check src/ tests/` ✅
- 目标测试：`tests/test_continuity_auditor_suggested_marks.py`、`tests/test_continuity_health_governance.py`、`tests/test_setting_evaporator.py`、`tests/test_creative_director.py`、`tests/test_task135_continuity_governance.py` ✅
- 全量 `pytest tests/`：`1892 passed, 2 skipped, 1 xfailed` ✅

---

## 交付物

- 本 `-DONE.md` 文件
- ContinuityAuditor / SettingEvaporator / CreativeDirector / Writer prompt 相关改动
- `tests/test_task135_continuity_governance.py`
