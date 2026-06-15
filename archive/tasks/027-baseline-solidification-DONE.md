# Task 027: 基线固化 — V2.0.0 Phase 0（已完成）

> **Phase**: Phase 0 — 基线固化
> **优先级**: P0
> **依赖**: V1.x 全部完成（Task 026 结束）
> **完成日期**: 2026-06-02
> **执行者**: AI Agent

---

## 完成项

- [x] 环境清理：终止残留 Python 进程，释放 Windows `songyan.db` 锁定
- [x] 归档所有 `tasks/*-DONE.md` 到 `archive/tasks/`（27 个文件已归档）
- [x] 清理残留的 `__pycache__`、`.pytest_cache`、egg-info
- [x] 确认 `tests/` 全部通过：711 passed（2 deselected）
- [x] 创建 `scripts/evaluate_project.py` — 输入 project_id，输出基线指标：
  - 逐章字数/场景数/版本数统计
  - 跨章一致性扫描（orphaned settings, forgotten items）
  - 重复修辞检测（喃喃自语、呼吸停滞等）
  - 情绪曲线分析（基于情感词频）
  - 综合评分
- [x] 修复评估脚本 import 路径：
  - `SummaryRepository` 从 `songyan.db.context_repo` 导入
  - 移除不存在的 `SettingSnapshot` model 导入
  - 新增文件系统 fallback：DB 无数据时从 `projects/{id}/chapters/` 加载
- [x] 运行基线评估，生成 `docs/review/baseline_orbital_horror.json`
- [x] V2 框架保护：
  - `CreativeModeProfile` 添加 `extra="ignore"`，确保向后兼容
  - 新增 `creative_modes/webnovel_intense.json` 作为 Phase 1 实验沙盒

---

## 关键决策

### 文件系统 fallback
`orbital_horror` 项目数据在数据库中不存在（可能是环境清理/DB 重建导致），但 `projects/orbital_horror/chapters/` 目录保留了 Ch2~Ch11 的 markdown 文件。评估脚本增加了文件系统 fallback 逻辑，确保基线报告仍可生成。

### CreativeModeProfile extra="ignore"
为未来 Phase 1~6 在 creative mode JSON 中添加新字段（如 `punch_engine`）做准备，避免 Pydantic 验证错误破坏现有加载逻辑。

---

## 基线报告摘要

| 指标 | 数值 |
|------|------|
| 项目 | orbital_horror（轨道上的怪谈）|
| 评估章节 | Ch2~Ch11（10 章）|
| 总字数 | ~37,428 |
| 综合评分 | 7.09/10 |
| 重复修辞项 | 7 类（盯着看×9、低声说×6、僵住/停住×6 等）|
| 对话占比 | 24.9% |
| 平均段落长度 | 35.8 字 |

> 注：文件系统模式下 version_count=1、revision_rounds=0，因此连续性评分显示为 10.0（无 DB 历史数据）。实际连续性断点见 `docs/review/orbital_horror_ch2_ch11_assessment.md`。

---

## 交付物

- `scripts/evaluate_project.py` — 基线评估脚本
- `docs/review/baseline_orbital_horror.json` — 基线报告
- `creative_modes/webnovel_intense.json` — Phase 1 实验沙盒配置
- `src/songyan/models/creative_mode.py` — 添加 `extra="ignore"`

---

## 下一步

**Task 028: Punch Engine — 刺激点控制**
- 解决"节奏太慢，缺乏爆炸点"
- 每章刺激点密度 ≥ 1，每 1500 字情绪转折 ≥ 1
- 新增 `PunchPoint` 模型、`webnovel_intense` 模式激活
