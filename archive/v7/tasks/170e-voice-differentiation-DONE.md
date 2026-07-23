# Task 170e: voice 声纹区分提质 — DONE

> **专项**: 文学提质专项（`archive/v7/tasks/170-literary-quality-remediation-README.md`）
> **类型**: 生成侧提质（中风险——碰生成链）
> **状态**: ✅ 完成（2026-07-07）
> **依赖**: 170d DONE（校准后可信量具）

---

## 结论一句话

voice 塌陷（170b 均值 1.8）的**真正根因不是 A–E 中任一生成侧缺陷，而是更上游的 seeding gap**：
项目 `characters` 表为空 → `generate_dialogue_style_cards([])` 恒返回 `[]` → 声纹机制全程**死代码**。
修复 = 新增幂等 `ensure_protagonist_character`，在 CLI 建项目 + 流水线启动处补建 protagonist Character，
让声纹链路有落点。小样本真实生成验证：snapshot 声纹卡从 **170b 全 0** 变为 **Ch1=1/Ch2=3/Ch3=3**，
主角卡由 pipeline 自动生成，**机制激活证据闭合**。

## 根因诊断（Stage 0，复现脚本先行）

`scripts/repro_170e_voice_pipeline.py`（只读 170b 隔离 DB `.tmp/task170b_ch1_ch40.db`）逐环 Q1–Q6 查证：

- **Q1（假设 A）命中，但比 A 更上游**：`characters` 表 **0 行**（`character_states` 也 0 行），
  却有 40 章正文、满是苏晚/医疗官/林渊对白。
- 逐环确认声纹链路本身**已全线打通**（生成 `_nodes.py:437` → 落库 `repository.py:260` →
  重载+过滤 `_helpers.py:406` → 注入 `writer/1.1.0.yaml:78` 已含对话风格块 → 格式化 `writer.py:132`）。
- 但链路**从未被喂到角色**：170b 生成脚本 `_init_db` 只建 project + outline，**从不 seed 任何 Character**；
  且 settlement 遇未知 `character_id` 是 **skip 而非新建**（`_apply.py:445-452`），
  `songyan create` 也只把 `protagonist_name` 存进 projects 表、不建 Character（`cli/main.py`）。
- 因此 A–E 中的 B′-filter / B′-eviction / C / E 全部**无从谈起**——机制根本没运行。

> **认知修正**：170e 文档原假设 B′-filter + E 最可疑，实测证明都不是。根因在更上游的
> "characters 表为空"，是脚手架与生产 CLI 共有的 seeding gap。

## 探针验证假设 E 不成立（Stage 1 前置）

`scripts/probe_170e_dialogue_style.py`（独立隔离 DB）seed 轨道蜃景真实卡司后，
**只调一次** `generate_dialogue_style_cards`：返回 4 张**高区分度**声纹卡
（两两轴重叠 0%–21%，苏晚↔医疗官 0%）。**假设 E（卡雷同）否定**——
生成器被喂到角色后产出优秀差异化，voice 塌陷主因确为 seeding gap。

## 修复（Stage 1，最小改动）

用户决策：**生产端自动建 protagonist + harness 手动 seed 配角**。

1. 新增 `ensure_protagonist_character(project_id, project=None)`（`workflows/_helpers.py`）——幂等：
   - 项目不存在 / 已有任意 protagonist / protagonist_name 空 → no-op 返回 False；
   - 否则用 `project.protagonist_name` 补建一条最小 protagonist Character，返回 True。
2. 接入两处入口：
   - `cli/main.py` 建项目后立即调用（生产 `songyan create` 覆盖）；
   - `phase2_graph.py::run_project_pipeline` 启动处兜底调用（脚本/harness 绕过 CLI 时覆盖）。
3. **不动生成侧 prompt/卡**（探针证明卡生成器本身没问题），也不改 170d 量具。

> 为何不改 `_DIALOGUE_STYLE_PROMPT_TEMPLATE` / Writer 卡：探针已证明 seed 后卡高度差异化、
> snapshot 正常携带，问题不在 prompt 而在"没角色"。改 prompt 属过度修复。

## 局部验证（Stage 2，小样本真实生成）

`scripts/run_170e_stage2_small_sample.py`（隔离 DB `.tmp/task170e_stage2.db`，`.tmp/` 硬防护）：
seed 完整卡司（主角**故意留空 card**验证 pipeline 会生成），真实 LLM 跑 Ch1–Ch5。

| 验证项 | 170b 基线 | 修复后 |
|--------|:---:|:---:|
| characters 表有声纹卡 | 0/0（表空） | **4/4**（主角卡由 pipeline 生成） |
| Ch1 snapshot 声纹卡数 | 0 | **1** |
| Ch2 snapshot 声纹卡数 | 0 | **3** |
| Ch3 snapshot 声纹卡数 | 0 | **3** |

Ch3 后因 enforce 门禁 `health_low_p1_halt`（P1=5，settlement/orphan）AutoHalt——
**与 voice 无关**，是开局章已知 friction（对齐 Task 129），只是让样本停在 3 章。
**机制激活证据已闭合**：声纹卡从死代码状态变为真实进入 Writer 上下文。

## 交付物

- 诊断脚本：`scripts/repro_170e_voice_pipeline.py`（Q1–Q6 逐环钉根因，只读）
- 探针脚本：`scripts/probe_170e_dialogue_style.py`（假设 E 否定，`.tmp/` 硬防护）
- 局部验证脚本：`scripts/run_170e_stage2_small_sample.py`（seed+生成+验证，`.tmp/` 硬防护）
- 生产修复：`src/songyan/workflows/_helpers.py`（`ensure_protagonist_character`）、
  `src/songyan/cli/main.py`、`src/songyan/workflows/phase2_graph.py`
- 单测：`tests/test_170e_ensure_protagonist.py`（7 用例，幂等契约）

## 验证结果

```
python -m pytest tests/test_170e_ensure_protagonist.py -q   → 7 passed
python -m pytest tests/ -q                                   → 2435 passed, 2 skipped, 1 xfailed
ruff check（170e 触及文件）                                   → All checks passed
小样本真实生成                                                → snapshot 声纹卡 0→1/3/3，主角卡自动生成
```

## 验收对照

- [x] 声纹失效根因定位并写入 DONE（seeding gap，比 A–E 更上游）。
- [x] 最小修复落地，相关测试 + 全量 + ruff 通过。
- [x] 小样本重生成显示机制激活（snapshot 携带声纹卡、主角卡自动生成）。
- [x] 无骨架回退行为不破坏（幂等 no-op，项目缺失/已有 protagonist 不写）。
- [x] 产出本 DONE 文档。

## 与 170g 的衔接

170e 只证明**机制被激活**；"对白是否真正可辨身份"（假设 C：Writer 是否遵守卡）
需在**对白密集的中段窗口**用 170d 校准量具全窗口复评——归 **170g**：
- 重跑中段窗口（seed 完整卡司），用 LiteraryAuditor 1.0.2 看 `character_autonomy` 是否抬离 ~2.0 地板、
  `polyphony_weakness` 是否在可辨处停止触发；
- 人工遮标签抽读确认苏晚/医疗官/林渊语气可分。
- 170e 的机制激活是 170g 复评的前提；两者合起来才构成 voice 提质的完整证据链。

## 遗留观察（非 170e 引入，供后续处理）

- **跨测试耦合**：`tests/test_phase2_graph.py` 用硬编码 `project_id="proj-001"` 但自身不建项目，
  依赖 `tests/test_105_streaming_validation.py` 的 module fixture 向主库 seed 的 `proj-001` 行。
  全量运行通过（test_105 先跑并 seed），但**隔离子集运行会 FK 失败**。本次因清理主库暴露该脆弱性。
  建议后续让 phase2 测试自建项目或用 `test_db` fixture 隔离——属测试卫生，不影响产品逻辑。
- **开局章 enforce friction**：Ch3 `health_low_p1_halt` 是 settlement/orphan 累积（Task 129 已知），
  与 voice 修复无关；170g 中段窗口重跑需按 170b 同样策略（isolate/督跑）处理。
