# Task 170o：human_voice_homogeneity 说话人归因校准 + seeding gap 根因暴露 — DONE

> **专项**: 文学提质专项（`archive/v7/tasks/170-literary-quality-remediation-README.md`）
> **类型**: 量具校准（补 170m 未覆盖的 voice 量具）/ 根因暴露
> **优先级**: P0
> **依赖**: Task 170m 已完成（exposition_carrier 已校准；但 `detect_human_voice_homogeneity` 仅做了 non_character_keywords 注入，未修说话人归因）
> **状态**: ✅ **已完成**
> **负责人**: songyan-agent

---

## 背景

170m 校准了 `detect_exposition_carriers`（引号匹配 + 跨段落过滤 + 动态关键词，72→6），但 **voice 量具 `detect_human_voice_homogeneity` 仍在真实正文上恒为 0**。用户在合并 170j–170n 后要求复核，本任务对该量具做二次校准并落实修复。

## 复核实测（修复前）

对 170i 隔离 DB 的真实抽读正文 `.tmp/task170i_prose_ch28_ch32.md` 实测（弯引号 `""`，123 处）：

| 检测器 | 修复前（合并版 main） | 说明 |
|---|---:|---|
| `detect_exposition_carriers` | 8 | 170m 修复生效（方向性/去跨段落后真值 ~6–8，确认 170m 结论） |
| `detect_human_voice_homogeneity` | **0** | 说话人归因失败，量具形同虚设 |

### 修复前根因（逐场景插桩确认）

1. **说话人归因只认 `名字+说/道` 紧邻标签**：合并版虽加了后置说话人，但真实正文极少用 `X说："..."`，大量是**叙事归因**（`声音是陈薇的`、`陈薇的声音传来`、`陈薇的录音`）或**纯对白无提示**（`"陈薇在哪？"`）。
2. **无注册表 gating → 抓到叙事片段噪声**：放宽归因后，正则 `[一-龥]{1,6}` 会把引语邻近的叙事文字误当人名，实测抓到 `寻找更多`、`录音中`、`原始`、`的人发出` 等垃圾"说话人"，制造假信号。
3. **窗口本身是主角独角戏**：Ch29–Ch32 是林渊 vs 投影/录音的单主角内心戏，真正的"两个人类角色对白同场"场景本就稀少。

## 关键发现：真正的 blocker 是 seeding gap，不是正则

用项目角色注册表（`LiteraryKeywordRepository.get_project_character_names`）gating 后实测：

```
registry character names = {'林渊'}     # 整个 Ch1–Ch32 的 characters 表只有主角 1 行
```

DB 直查确认：
```
characters 表：[('林渊', 1)]
projects.protagonist_name：林渊
```

根因链：
```
SettlementExtractor 只 UPDATE 已存在角色（_apply.py: if update.character_id not in valid_char_ids → skip）
    ↓ 从不 INSERT 新出场配角（陈薇/老雷…）
characters 表长期只有主角 1 行（seeding gap）
    ↓
voice 量具无法归因配角、无法凑齐"≥2 人类角色同场"
    ↓
detect_human_voice_homogeneity 在真实正文上结构性恒 0
```

这与 **170e 当初定位的 voice 塌陷根因（characters 表为空/仅主角）是同一个 seeding gap**——170e 只 seed 了主角，配角仍缺席。**voice 量具与 voice 生成质量都被同一个数据缺口卡住。**

## 本次修复

### 1. `detect_human_voice_homogeneity` 说话人归因校准

**File:** `src/songyan/agents/rule_auditor.py`

- 新增 `character_names: set[str] | None` 参数（项目角色注册表）。
- 归因新增**叙事归因**形态：`X的声音/嗓音/录音/语音/话音/声线`、`声音是X的`（真实正文主流写法）；归因优先取引语**前窗口最靠近**的一次匹配，避免误取下一句说话人。
- **注册表 gating**：提供 `character_names` 时，只接受命中注册表的人名（支持子串，兼容"老陈/陈薇"指代），彻底过滤 `寻找更多`/`录音中` 类叙事片段噪声；未提供时回退"2–4 汉字 + 非代词 + 非非人实体"宽松启发式，保持向后兼容。
- 代词集合（他/她/它/我/你 及复数）显式过滤。

### 2. 调用链接入

**File:** `src/songyan/agents/rule_auditor.py`（`run_rule_audit`）

- `run_rule_audit` 已有的 `character_names` 参数现透传给 `detect_human_voice_homogeneity`。

### 3. 单测

**File:** `tests/test_rule_auditor.py`

- `test_human_voice_homogeneity_narrative_attribution_with_registry`：叙事归因 + 注册表可检出同质化。
- `test_human_voice_homogeneity_registry_filters_narration_noise`：叙事片段噪声不被误当说话人。
- `test_human_voice_homogeneity_single_seeded_character_no_false_positive`：注册表仅主角时不误报（对应 seeding gap 实况）。

## 修复后验证

| 场景 | 结果 | 期望 | 判定 |
|---|---:|---|:---:|
| 真实 170i 正文，无注册表 | 0 | 诚实低报（单主角窗口） | ✅ |
| 真实 170i 正文，注册表={林渊}（实况） | 0 | 无法凑齐 2 人 → 不误报 | ✅ |
| 合成同质化，前置标签，无注册表 | 3 | 命中 | ✅ |
| 合成同质化，注册表 gated | 3 | 命中 | ✅ |
| 合成异质声纹 | 0 | 不误报 | ✅ |
| 叙事归因同质化 + 注册表 | 1 | 命中（修复前为 0） | ✅ |

- `ruff check src/songyan/agents/rule_auditor.py tests/test_rule_auditor.py`：All checks passed。
- `pytest tests/test_rule_auditor.py tests/test_rule_auditor_dynamic_keywords.py`：87 passed。
- `pytest tests/test_rule_auditor.py tests/test_rule_auditor_dynamic_keywords.py tests/test_prompt_loader.py tests/test_creative_director.py`：141 passed。

## 结论与判定

1. **voice 量具已从"假 0"改为"注册表可用、真实正文诚实低报"**：注册表齐全时能检出叙事归因下的声纹同质化；注册表只有主角时诚实返回 0（而非靠噪声凑假信号）。
2. **真实 blocker 上移到数据层（seeding gap）**：`characters` 表长期只 seed 主角，SettlementExtractor 不 INSERT 新配角，导致 voice 量具与 voice 生成质量被同一缺口卡住。**这是 170e 未闭合的遗留，需独立任务处理**（见下"后续"）。
3. **不改变 170l/170i 未达标结论**：本次是量具修复，voice/exposition LLM rubric 仍未达 Ch200 入口线，维持 blocker。

## 附带发现（非本任务引入，需登记）

合并（`462c494`）后有 **2 个测试文件在 clean 状态即 collection error**，与本次改动无关（`git stash` 后复现）：

- `tests/test_non_character_voice_cards.py` → `ImportError: cannot import name '_build_non_character_voice_cards' from 'songyan.workflows._helpers'`
- `tests/test_revision_handler_literary.py` → `ImportError: cannot import name '_build_literary_issues' from 'songyan.agents.revision_handler'`

即测试引用的符号在当前源码中不存在（合并把测试与实现改花了）。**STATUS 中"分模块 pytest 全通过"的记录与此不符**，需要修测试导入或补回符号后再更新测试状态。

## 后续（建议）

1. **P0：修 seeding gap（独立任务，建议 170p）**——让 SettlementExtractor 或 pipeline 在配角首次出场时 INSERT `characters` 记录（幂等），使 voice 量具与声纹卡对配角生效。这是 voice 维度能否真正提升的前置。
2. **修复上述 2 个 pre-existing 测试 collection error**，恢复 `test_non_character_voice_cards` / `test_revision_handler_literary` 可收集，再重跑分模块 pytest 校正 STATUS 测试记录。
3. 修完 seeding gap 后，用注册表齐全的新样本重跑 `detect_human_voice_homogeneity`，取真实同质化分布，更新 mid-term-review 的 voice 结论。

## 交付物

- `src/songyan/agents/rule_auditor.py`（`detect_human_voice_homogeneity` 归因校准 + `run_rule_audit` 透传）
- `tests/test_rule_auditor.py`（3 个新增单测）
- `archive/v7/tasks/170o-voice-homogeneity-attribution-calibration-DONE.md`
