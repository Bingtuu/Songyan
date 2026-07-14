# Task 172d: 文学护栏跨体裁化（GenreProfile 层 3）

> **阶段**: V8 多体裁可插拔质量  
> **类型**: 风格实现层（layer 3）解耦——把既有文学护栏从科幻硬编码参数化为按体裁可插拔  
> **优先级**: P0（是 172a.7 多体裁质量报告的硬前置）  
> **依赖**: 无强代码依赖（改 `GenreProfile` 层，与 172a 运行时层解耦，可并行）；但**必须先于 172a.7 合入**  
> **状态**: 规划中

## 背景

三轮审计发现：V7 的"文学护栏"（Task 171w-c）虽已接入生产管线，但**通体硬编码为科幻形状**。文件 `src/songyan/evals/literary_guardrail_observe.py`：

| 硬编码点 | 位置 | 科幻形状 |
|---|---|---|
| 主角名默认值 | `observe_active_choice(..., protagonist_name="林渊")` `:222`；`audit_171w_text_guardrails(..., protagonist_name="林渊")` `:294` | `林渊` 是科幻项目主角名 |
| 主动动词 | `_ACTIVE_VERBS` `:15-33` | 含"按下/启动/命令/破解"等技术动作 |
| 被动模式 | `_PASSIVE_ONLY_PATTERNS` `:34` | "继续破解/继续推进/等待协议" |
| 代价词 | `_COST_KEYWORDS` `:35` | "损耗/不可逆" |
| 配角动作词 | `_SUPPORTING_ACTION_KEYWORDS` `:36-52` | 通用度较高但仍偏技术 |
| 后果词 | `_CONSEQUENCE_KEYWORDS` `:53-63` | "改变路线/误判" |

### 为什么这是 V8 范围（而非 Task 170 重做）

用户对 V8 的核心诉求是"**V7 文学性优化只完成了科幻单一体裁，其他体裁无法复用**"。`GenreRuntimeProfile`（172a）只解耦运行时层（预算/阈值/压缩）的**数字**，**一行都不会动**这些文学 lexicon。若不做 172d：

1. **xuanhuan 文学 observe 全假失败**：`observe_active_choice` 在玄幻正文里找"林渊"和"按下/启动"，必然每章判"主动选择 MISSING"——不是玄幻真的缺主动选择，而是审计器在找科幻词。
2. **172a.7 的多体裁质量报告失真**：该报告用 `render_text_guardrail_observe_section` 渲染，跑在这条 observe 路径上。
3. **用户目标未达成**：文学护栏依然只对科幻有效。

> **与"明确不做"的区分**：V8 不做 Task 170 式**文学提分**（新增 rubric、重写 Writer prompt 追求更高文学分）。172d 只做**参数化既有护栏**，使其在非科幻体裁不失真。前者是提分，后者是止损，性质不同。

### live 门禁 vs observe 报告（重要区分）

- **live 门禁**（进生产、影响 accept/CED）：只有 `check_supporting_character_goal_presence`（`review_merger.py:532` 接线为 major patchable issue）。它按 **brief 里的配角名**判定（每项目生成，**体裁中性**），本身不受科幻 lexicon 影响。
- **observe 报告路径**（172a.7 交付物、不阻塞 accept）：`observe_active_choice` / `observe_supporting_character_goal` + `render_text_guardrail_observe_section`。**这条才是科幻硬编码重灾区。**

172d 主要修 observe 路径与主角名；live 门禁的 `_SUPPORTING_ACTION_KEYWORDS`/`_CONSEQUENCE_KEYWORDS` 也一并参数化以保证 evidence 质量跨体裁一致。

## 真实字段落点（已核对代码）

- **主角名**：`ProjectSetting.protagonist_name: str`（`models/project.py:16`）。172d 从项目读取，替换 `"林渊"` 默认。
- **lexicon 宿主**：`GenreProfile`（`models/genre.py:84-115`），已含 `fatigue_words`/`taboos`/`writer_rules`/`style_baseline`，加 lexicon 字段结构同构；`model_config={"extra":"ignore"}` 保证旧 JSON 不破。
- **genre 内容源**：`genres/*.json`（经 `load_genre_profile` 加载）。

## 目标

把文学护栏的主角名与 lexicon 从科幻硬编码解耦为按体裁可插拔，无 profile 100% 回退当前科幻组（AGENTS.md 回退硬约束）。

## 子任务

### 172d.1: 主角名去硬编码

**做**：
1. `observe_active_choice` / `audit_171w_text_guardrails` 的 `protagonist_name` 默认值删除，改为**必传**或从项目 `ProjectSetting.protagonist_name` 读取。
2. 调用链（report 脚本、`audit_171w_text_guardrails`）传入项目真实主角名。

**验收**：scifi 项目取到"林渊"，xuanhuan 取到其模板主角名；无 `"林渊"` 字面量残留在函数签名。

### 172d.2: lexicon 迁入 GenreProfile

**做**：
1. `GenreProfile` 新增可选字段：`active_verbs` / `passive_only_patterns` / `cost_keywords` / `supporting_action_keywords` / `consequence_keywords`（均 `list[str]`，默认空）。
2. `literary_guardrail_observe.py` 的 5 组模块常量降级为**科幻回退默认**（当 profile 未提供时使用）。
3. observe/check 函数签名新增可选 `genre_profile: GenreProfile | None`，从中取 lexicon；为 None 或字段空则回退科幻默认组。
4. 为 xuanhuan/wuxia/urban 在各自 `genres/*.json` 配 lexicon：
   - xuanhuan 主动动词：闭关/夺舍/立誓/破境/祭炼/斩道；代价：折寿/道心受损/根基受创/因果缠身。
   - wuxia 主动动词：出剑/挑战/退隐/立誓/断交；代价：内伤/断脉/结仇。
   - urban 主动动词：辞职/摊牌/举报/签约/断绝；代价：失业/名誉受损/亏损。

**验收**：xuanhuan 正文用玄幻 lexicon 命中主动选择；scifi 无 profile lexicon 时回退科幻组、行为与今日等价。

### 172d.3: 回归 + 集成

**做**：
1. 更新 `tests/test_171w_text_guardrail_observe.py`：科幻用例（回退路径）保持全绿。
2. 新增 `tests/test_172d_cross_genre_guardrails.py`：xuanhuan/wuxia/urban 正文样例 + 对应 profile → 主动选择/配角目标正确命中。
3. 跑 `python -m pytest tests/ -q` + `ruff check src/ tests/`。

**验收**：pytest 全绿；ruff 无新增；scifi 回退等价；observe 报告对 xuanhuan 不再全 MISSING。

## 出口标准

1. `tasks/172d-cross-genre-literary-guardrails-DONE.md` 记录最终 lexicon 与验证结果；
2. 5 组 lexicon 在 `GenreProfile` 可配置，无 profile 回退科幻组；
3. 主角名无硬编码；
4. 172a.7 可安全使用 observe 报告做多体裁对标。

## 验证命令

```powershell
python -m pytest tests/test_171w_text_guardrail_observe.py tests/test_172d_cross_genre_guardrails.py -q
ruff check src/ tests/
```
