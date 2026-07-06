# Task 170e: voice 声纹区分提质

> **专项**: 文学提质专项（`tasks/170-literary-quality-remediation-README.md`）
> **类型**: 生成侧提质（中风险——碰生成链）
> **优先级**: P0（voice 是 170b 最痛短板，均值 1.8）
> **依赖**: 170d DONE（需校准后可信量具才能判断提质是否有效）
> **状态**: ◻ 规划中

---

## 问题（170b 实证）

voice（角色声纹区分度）全窗口均值 **1.8/5**，13 章 8 章 ≤1：对白"谁说话都一副冷静解说腔"，苏晚 / 医疗官 / 林渊语气无区分。是 5 维中最严重的塌陷。

## 认知修正（查证得到——机制已存在，重点是诊断为何失效）

**声纹机制已经建好且相当完整**，voice 仍塌陷 = 现有机制**没生效或没被触发**。查证到两条并存通路：

1. **CreativeDirector 卡内约束**（`prompts/cards/creative_director/1.0.6.yaml`）：
   - 强制规则 12：必须为每个主要出场角色定义语言指纹，≥2 个差异化特征（语速/用词/句式/口头禅/语气）。
   - 对话质量规则 9–11：禁直白独白、禁解释性对话、每对话场景 ≥1 层潜台词。
   - 运行时动态选版：有骨架且有待推进线索用 **1.0.6**，否则 1.0.5（`creative_director/__init__.py:148-157`）。

2. **DialogueStyleCard 结构化通路**（Task 074）：
   - 模型 `DialogueStyleCard`（`models/character.py:21-51`）：句长偏好、开场/收尾语、各情绪表达、比喻频率、反问习惯等。
   - 生成 `generate_dialogue_style_cards`（`creative_director/__init__.py:473-540`）：只为 `dialogue_style_card is None` 的角色生成，LLM 不可用则降级返回 `[]`。
   - 注入 Writer：`ContextPackage.dialogue_style_cards` → `writer.py:132-159` 格式化 → Writer 卡 `{% if dialogue_style_cards %}` 块（`1.2.0.yaml:78-90`）。

**所以 170e 的第一步不是"加声纹约束"，而是诊断这套机制为什么没兑现成 voice。**

## 诊断假设（需先验证）

| 假设 | 验证方式 |
|------|----------|
| A. `dialogue_style_cards` 根本没生成（LLM 降级 / 未触发 generate） | 查 170b 项目 DB 的 characters 表 `dialogue_style_card` 是否为空 |
| B. 生成了但没注入 Writer（ContextPackage 未携带） | 查 context snapshot / Writer prompt 实际是否含 dialogue_style 块 |
| C. 注入了但 Writer 未遵守（约束在 prompt 但被忽略） | 读正文对照 dialogue_style_card 定义，看是否落地 |
| D. CreativeDirector 1.0.6 未被选中（无骨架/无待推进线索路径） | 查 170b run 实际用的 CreativeDirector 版本 |
| E. 声纹特征生成了但雷同（模型给所有角色都是"冷静精确"） | 读多个角色的 dialogue_style_card 看是否真差异化 |

> 170b 的隔离 DB `.tmp/task170b_ch1_ch40.db` 还在，可直接查证 A–E，**这是本任务第一步**。

## Goal

1. 定位声纹机制失效的真实环节（A–E 中的一个或多个）。
2. 针对性修复：
   - 若 A（没生成）→ 确保 pipeline 在写作前触发 `generate_dialogue_style_cards`。
   - 若 B（没注入）→ 修 ContextPackage 组装，确保出场角色的 dialogue_style 进上下文。
   - 若 C（没遵守）→ 强化 Writer 卡对声纹的执行力（提到硬约束位置、加反例）。
   - 若 E（特征雷同）→ 改 `_DIALOGUE_STYLE_PROMPT_TEMPLATE` 强制差异化。
3. 用 170d 校准后量具复评 voice 是否提升（留给 170g，但本任务需局部验证）。

## In Scope

- [ ] 诊断脚本/查证：读 170b DB 的 dialogue_style_card 状态 + Writer prompt 实际注入情况，出根因。
- [ ] 按根因做最小修复（可能落在 CreativeDirector pipeline 触发、ContextManager 注入、Writer 卡、dialogue style prompt 之一或多个）。
- [ ] 局部验证：小样本（2–3 章）重生成，人工/校准量具确认对白开始可辨身份。

## Out of Scope

- 不做全自动 LLM 改写闭环（不对已生成正文自动重写 voice）。
- 不改 170d 的量具判定标准（用它，不改它）。
- 不启动 Ch200。
- 全窗口复评归 170g，本任务只做小样本局部验证。

## 风险提示

- **碰生成链**：改 CreativeDirector/Writer/ContextManager 有回归风险，需跑相关测试（`test_dialogue_style_card.py`、`test_creative_director*`、`test_writer.py`、`test_context_manager.py`）。
- **Writer 卡版本**：manifest default=1.1.0 但最新卡 1.2.0，改前先确认线上实际加载版本（与 170f 共享此风险）。
- **无骨架回退**：CreativeDirector 1.0.5/1.0.6 动态选版，修改不得破坏无骨架项目的回退行为。

## 验证要求

```powershell
python -m pytest tests/test_dialogue_style_card.py tests/test_writer.py tests/test_context_manager.py -q
ruff check src/ tests/
python -m pytest tests/ -q
# 小样本真实重生成（隔离 DB）验证 voice 局部改善
```

## 验收标准

- [ ] 声纹失效根因（A–E）定位并写入 DONE。
- [ ] 最小修复落地，相关测试通过。
- [ ] 小样本重生成显示对白可辨身份（校准量具 + 人工抽读）。
- [ ] 无骨架回退行为不破坏。
- [ ] 全量测试 + ruff 通过。
- [ ] 产出 `tasks/170e-...-DONE.md`。
