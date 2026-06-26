# Task 121r: Prompt Quality Cleanup Execution — DONE

- **状态**: DONE
- **完成日期**: 2026-06-26
- **任务类型**: V5.1 Prompt 修复

## 目标摘要

承接 Task 121k 的规划，执行 Prompt / 正文质量修复。在不修改 SQLite 事实源契约、不放宽 QualityGate 阈值的前提下，消除机械场景标题、HTML/元标记泄漏、短段落碎片化等问题，并将 CreativeDirector 的约束改写为可执行形式。

## 关键改动 / 交付物

1. **Writer Prompt 升级至 1.1.0**
   - 文件：`prompts/cards/writer/1.1.0.yaml`
   - `prompts/cards/writer/_manifest.yaml` 默认版本改为 `1.1.0`
   - 场景切换改用空行分隔，禁止 `### Scene N`、`Scene N:`、HTML 注释、`[[...]]`、`meta:` 等元标记
   - 新增格式纯净度约束与短段落控制（单句段落 <20 字占比 ≤15%，禁止连续短段落堆叠）

2. **CreativeDirector Prompt 升级至 1.0.5**
   - 文件：`prompts/cards/creative_director/1.0.5.yaml`
   - `prompts/cards/creative_director/_manifest.yaml` 默认版本改为 `1.0.5`
   - `forbidden_patterns` 全部写成 `【可执行约束】` 形式
   - 新增高概念信息的「行动承载」要求，避免设定说明清单化
   - `creative_intent` 聚焦读者体验而非信息交付

3. **RuleAuditor 新增观测指标**
   - 文件：`src/songyan/agents/rule_auditor.py`
   - 新增 Markdown / 裸场景标题检测（severity=info，不直接阻断）
   - 新增短段落比例（`<50 字`）观测指标
   - 元标记泄漏检测覆盖 HTML 注释、Mark 标签、Meta 前缀、旧式 `[[...]]` 标记
   - 配套工具：`src/songyan/utils/paragraph_rhythm.py`

## 验证证据

- **pytest**: `1764 passed`（来源：`docs/STATUS.md`）
- **ruff**: `ruff check src/ tests/` 已通过（来源：`docs/STATUS.md`）
- **Prompt 版本生效**：Writer manifest `default_version: "1.1.0"`，CreativeDirector manifest `default_version: "1.0.5"`
- **RuleAuditor 字段生效**：`RuleAuditResult` 已输出 `markdown_scene_title_count` 与 `short_paragraph_ratio`

## 遗留 / 后续

- 本次新增检测为观测指标（info / summary 提示），未直接接入 QualityGate 硬阻断；后续若质量窗口再出现类似问题，可由 Task 125 阈值调优或后续硬门禁任务决定是否升级为阻断项。
- 未进行单独 long-run 实跑；该 Prompt 清理已合并进后续 `run-a2bed648` 的 Ch1-Ch150 全量成功证据中。
