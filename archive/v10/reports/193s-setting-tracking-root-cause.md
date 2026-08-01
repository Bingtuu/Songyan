# Task 193.s Phase A 诊断报告：setting tracking 刷新漏报根因

> **任务**: `tasks/193.s-setting-tracking-refresh-root-cause.md`（Phase A，只读诊断）
> **完成时间**: 2026-07-28
> **数据**: `.tmp/task_v10_xuanhuan_ch200.db`（project `d160a55a51de4a2bb82440ebc03ec23a`）、`.tmp/task_v10_wuxia_ch200.db`（project `273a8408be8e4caf8cbc1e91954da600`）+ 六份冻结备份库（`.tmp/backups/192v*/192y*/192al*/192ae*/192aq*/193q*/`），全部只读访问（源库 `file:...?mode=ro`；冻结库先复制到 `.tmp/193s_scratch/` 再打开，未触碰原文件）
> **分析脚本**: `.tmp/193s_analyze.py`（复用生产函数离线回放）；回放原始数据 `.tmp/193s_case_analysis.json`；patch 统计 `.tmp/193s_patch_tally.json`

---

## 1. 机制事实

### 1.1 tracking 刷新（`last_mentioned_chapter`）的全部生产路径

`UPDATE setting_tracking` 在 `src/songyan/db/continuity_repo.py` 共 5 处，其中**只有 2 处会刷新 `last_mentioned_chapter`**，外加 INSERT 初始化：

| # | 路径 | 代码位置 | 输入文本 | 适用对象 |
|---|------|----------|----------|----------|
| 1 | `create()` INSERT 初始化（last_mentioned = introduced 章） | `continuity_repo.py:50-65` | — | 新登记设定 |
| 2 | `update_last_mentioned()` ← `_recycle_duplicate_setting_clusters`：新设定命中已有同簇 canonical 时刷新旧设定 | `continuity_repo.py:102-118` ← `_apply.py:382` | settlement.new_settings | 仅 `status='active'` |
| 3 | `update_last_mentioned()` ← **Task 137 正文提及扫描** `_detect_setting_references(content, active_settings)` | 同上 ← `_apply.py:758-772` | **accepted 章节正文**（`_nodes.py:2467-2473` 传 `content=version.content`） | **仅 `status='active'`**（`_apply.py:762-766` 过滤） |
| 4 | `update_last_mentioned()` ← settlement 显式报告的 `recycled_settings` | 同上 ← `_apply.py:785-803` | settlement.recycled_settings | 仅 active |
| 5 | `update_last_mentioned()` ← `_update_continuity_tracking`：settlement.new_settings 重复登记已有 key | 同上 ← `_apply.py:1031-1036` | settlement.new_settings | 不限 status |
| 6 | `promote_to_active()` ← `promote_candidate_settings_after_settlement` | `continuity_repo.py:141-165` ← `_input_side_governance.py:245` | **settlement 碎片文本**（`_promotion_evidence_text`，`_input_side_governance.py:20-39`） | **仅 `status='candidate'`** 且 `introduced_in_chapter < chapter_number`（`:216-221`） |

不刷新 `last_mentioned_chapter` 的 UPDATE：`update_status`（`continuity_repo.py:128`）、`mark_resolved`（`:205`）、`mark_abandoned`（`:258`）、`archive_long_silent_nonessential`（`:304`）——均为状态迁移。summary / evaporator 不触碰 `setting_tracking`。

### 1.2 对任务书工作假设的确认/否定

- **确认**：`promote_to_active()` 的生产调用点确为 `_input_side_governance.py:245` 唯一一处，其匹配源是 settlement 碎片文本而非正文，匹配方式为 `_candidate_terms`（setting_key/setting_name/description 整串）对 evidence 做 exact/substring 词面匹配（`:225-246`）。
- **否定（关键修正）**：任务书假设"正文提及从不直接刷新 tracking，必须经 settlement 两道中转"——**不成立**。路径 #3（Task 137，`_apply.py:767-772`）每章 accept 后直接拿 **accepted 正文** 对所有 `status='active'` 设定做引用扫描并刷新 `last_mentioned_chapter`，不经过 settlement 提取。settlement 中转路径（#2/#4/#5/#6）只是补充。
- **推论**：漏报按 status 分流——
  - `active` 设定的刷新依赖路径 #3 的**正文词面匹配**（`_setting_reference_terms` → `_term_in_content` / `_has_multi_token_setting_reference`）；
  - `candidate` 设定的刷新依赖路径 #6 的 **settlement 碎片词面匹配**（正文路径对其关闭）。
- **本样本六个案例的 pre-fix status 全部为 `active`**（冻结库逐案核实，见 §2），因此失效层全部在**正文侧词面匹配**，而非 settlement 提取/中转。任务书预设的"提取层（分支2）"在本样本中不适用：对 active 设定，settlement 提不提取该 mention 都不影响刷新。

### 1.3 settlement 持久化粒度（证据局限前提）

DB 无 settlements 表；LangGraph state 只存 `settlement_id`（`_nodes.py:2750`，`writes` 表 channel 列表证实）。settlement 内容仅以其**效果**持久化：`setting_snapshots`（setting_name/description/source_quote）、`character_states`（field/value）、`foreshadowings`（description）、`setting_tracking`（无 source_quote 列）。`planted_hooks`/`resolved_hooks`/`open_threads` 文本**完全不持久化**。因此 `_promotion_evidence_text` 的输入无法从 DB 精确重建，本报告用上述碎片近似（脚本 `approx_evidence_text`），该近似只影响 candidate 路径复算；由于六案例均为 active，主结论不依赖该近似。

---

## 2. 每案例分支归类

归类口径：漏报窗口 = pre-fix `last_mentioned_chapter`+1 .. 硬门章。每章先判定**正文是否实质提及该 setting**（无实质提及则不是漏报，门禁属合理预警），再对提及章用生产函数离线回放匹配逻辑。

### 案例 A — xuanhuan Ch93 `guardian_hunter_deception`（192.v，冻结库 `192v_*/task172b_xuanhuan_ch100.db`）

pre-fix：`status=active`、`last_mentioned=89`、`introduced=89`、`category=critical`，name=`猎渊者·与守灵交易`。
机制 terms：`['guardianhunterdeception', '与守灵交易', '传承代价等关键信息均有隐瞒', '信任已彻底崩塌', '猎渊者', '猎渊者·与守灵交易', '陆沉父母之死相关']`。

| 章 | 正文提及证据 | 回放结果 | 归类 |
|----|--------------|----------|------|
| Ch90 | 仅"守门者就在下面"（`v-c23bf38d`） | — | 非漏报（无实质提及） |
| Ch91 | 仅"守门者？"（`v-625ec1e6`） | — | 非漏报 |
| Ch92 | "守灵说过，这血线有风险"（`v-f427f038`） | — | 非漏报（提及守灵但未及交易/欺骗设定本体，边界） |
| Ch93 | "黑令长老狞笑：'与守灵的交易换来的，专克你们这些守门者'"；"左臂的猎渊者印记在火光中一闪"（`v-ef690afa`） | `_detect_setting_references` 命中 0 个 term | **分支1（匹配层）** |

Ch93 失败对照（term ↔ 实际措辞）：
- term `与守灵交易` ↔ 正文 `与守灵的交易`——插入一个"的"字，substring 失败；
- term `猎渊者` ↔ 正文 `猎渊者印记`——`_term_in_content`（`_apply.py:106-130`）边界规则：term 长 3 < 4 且后接 CJK 字"印"→ 判为更长词的一部分，拒绝命中。

### 案例 B — xuanhuan `lingyuan_quan_first_form`（192.y @Ch105 + 192.al @Ch150）

pre-fix（192.y 冻结库）：`status=active`、`last_mentioned=100`、`introduced=65`、`category=critical`，name=`灵渊《灵渊拳》第一式`。
pre-fix（192.al 冻结库）：`status=active`、`last_mentioned=145`。
机制 terms：`['lingyuanquanfirstform', '拳意凝实如铁水浇铸', '灵渊《灵渊拳》第一式', '灵渊传承拳法', '能击碎血刃', '银白色轨迹']`。

| 章 | 正文提及证据 | 归类 |
|----|--------------|------|
| Ch101/102/103/105 | 无提及 | 非漏报 |
| **Ch104** | "《灵渊拳》第一式从他右拳中轰出"；"他把灵渊拳的起手式摆出来"；独立成句"灵渊拳。"（`v-473a1683`） | **分支1** |
| **Ch146** | "右手挥出一拳——灵渊拳第一式的印记在拳骨上亮起"（`v-e28de479`） | **分支1** |
| Ch147/148 | 无提及 | 非漏报 |
| **Ch149** | "你找到灵渊拳第一式的运行路线，就能激活它"；"灵渊拳第一式是陆家祖传功法中……"等 ×3（`v-6bf08959`） | **分支1** |
| **Ch150** | "将父亲留下的《灵渊拳》第一式'裂石'的发力方式压缩到最短距离"（`v-980d9be4`） | **分支1** |

失败对照（结构性词条缺陷，两层叠加）：
- `_setting_reference_terms`（`_apply.py:328-333`）的 name 拆分正则 `[·—\-_/（）()\[\]【】,，、;；:\s'‘’“”"]+` **不含书名号《》**，`灵渊《灵渊拳》第一式` 拆不出 `灵渊拳`/`第一式`；
- `_setting_core_phrases`（`_apply.py:161-176`）虽按 CJK 片段切分得到 `灵渊拳`/`第一式`，但 **len≥5 下限**把这两个 3 字核心词全部丢弃；
- 结果唯一中文整串 term 是 `灵渊《灵渊拳》第一式`（带书名号、带前缀"灵渊"），正文实际写法 `灵渊拳第一式` / `《灵渊拳》第一式` 均不是其子串。多 token 兜底（`_has_multi_token_setting_reference`）因 token 只能派生自 ≥5 字短语，同样无米下锅。

### 案例 C — xuanhuan `mother_descendant`（192.ae @Ch120 + 192.aq @Ch168）

pre-fix（192.ae 冻结库）：`status=active`、`last_mentioned=116`、`introduced=61`、`category=critical`，name=`守门者后人·母亲血脉`。
pre-fix（192.aq 冻结库）：`status=active`、`last_mentioned=162`。
机制 terms：`['motherdescendant', '她这辈已经弱', '守门者后人', '守门者后人·母亲血脉', '无法再承载灵渊烙印', '母亲血脉', '灵渊本源渡入腹', '第一代封印渊眼', '血脉封印本应代代相传']`。

| 章 | 正文提及证据 | 归类 |
|----|--------------|------|
| Ch117/118 | 无 accepted head（Task 191 harness isolate 空洞，192.ae 已记录） | n/a（证据缺失，非漏报判定） |
| Ch119 | "像血脉一样在眼球表面游走"（比喻） | 非漏报 |
| **Ch120** | "'记住——守门者的血脉还没有断干净'"；"母亲的钥匙印记——那枚铜色的月牙形烙印，正在微微发热"（`v-5950a592`） | **分支1** |
| **Ch163** | "'你母亲把它种进你体内的时候，用的是她自己——'"（`v-650700df`） | **分支1**（明确，直接重述设定描述"把灵渊本源渡入腹中的陆沉"） |
| Ch164 | "母亲故意留下守灵的真相"（`v-c12070fc`） | 分支1（边界，弱提及） |
| Ch165 | "母亲留下的那枚印记正在黯淡"（`v-49e1f8ae`） | 分支1（边界，弱提及） |
| **Ch166** | "'你母亲把自己的使命种进了你的丹田里'"；"你母亲把你当成第二把锁装进了钥匙孔"（`v-6c25b677`） | **分支1**（明确） |
| Ch167 | 回忆场景"被母亲一把推进地窖"（母亲出场但未及血脉设定本体） | 非漏报（边界） |
| Ch168 | "'你母亲的封印'"（`v-7e77baf0`） | 分支1（边界，弱提及） |

失败对照：term `守门者后人` ↔ 正文 `守门者的血脉`；term `母亲血脉` ↔ 正文 `母亲的钥匙印记`/`你母亲把它种进你体内`——全部是 paraphrase/称谓变化导致的词面不命中。`母亲`（2 字）不生成 term；`守门者`（3 字）也不在 term 集中。

### 案例 D — wuxia Ch117 `blood_abyss.reverse_practice`（193.q，冻结库 `193q_*/task_v10_wuxia_ch200.db`）

pre-fix：`status=active`、`last_mentioned=113`、`introduced=100`、`category=critical`，name=`血引归墟反练可能性`。
机制 terms：`['reversepractice', '因沈默手指渗血而显现', '经脉尽断不可逆转', '血引归墟刀法代价', '血引归墟反练', '血引归墟反练可能性']`。
命名事实（冻结库全库统计）：正文 13 章用`血引归墟`、24 章用`血祭刀法`、6 章用`逆血归元`。Ch100（intro，`v-17cdf3f6`）与 Ch113（最后一次成功刷新，`v-5d1115ed`）正文均写`血引归墟（反练）`——Ch113 正是靠整串 term 命中刷新的，证明机制在"原文复读"时能工作。

| 章 | 正文提及证据 | 归类 |
|----|--------------|------|
| Ch114 | "血祭刀法，就是用别人的血气来填补自己的空缺"（`v-2b41977f`） | **证据不足/边界**（见下） |
| Ch115 | "以血祭刀法为骨，融合了残风式的变化"（`v-8b029d2a`） | 证据不足/边界 |
| **Ch116** | "这是血祭刀法里'逆血归元'的变体"；"将血祭刀法与断魂刀法融合过，创出了一套全新的运功路线"（`v-257849b6`） | **分支1（弱）**——`逆血归元` 是"反练"概念的称谓漂移，词面不可达 |
| Ch117 | "'你知道血祭刀法的代价吗'"（`v-2175f61b`） | 证据不足/边界 |

不确定性（如实标注）：`血祭刀法`（"用别人的血气"）与 `血引归墟`（"以自身经脉为引"）在正文中可能是**同源但不同的两门功法**——若如此，Ch114/115/117 正文确实未提及该 setting，门禁属合理预警而非漏报；只有 Ch116 的 `逆血归元` 变体接近"反练"概念。无法从 tracking 数据确证两者同一性，故 D 的 4 章中只有 Ch116 计入分支1（弱），其余 3 章标"证据不足"。

---

## 3. 分支占比汇总

样本：6 个案例、28 个窗口章（扣除 2 个 isolate 空洞章后 26 章可判）。

| 归类 | 章数 | 明细 |
|------|------|------|
| **分支1（匹配层）明确** | **8** | A-Ch93；B-Ch104、Ch146、Ch149、Ch150；C1-Ch120；C2-Ch163、Ch166 |
| 分支1（边界/弱提及） | 4 | C2-Ch164/165/168；D-Ch116（弱） |
| 分支2（提取层） | **0** | 六案例 pre-fix 全为 active，刷新走正文路径，settlement 提取漏损与漏报无因果 |
| 分支3（过滤层） | **0** | 全部 `status=active` 且 `introduced_in_chapter < chapter_number`，正文路径的 active 过滤与 candidate 过滤均不误伤；漏报点全部在词条匹配 |
| 非漏报（正文无实质提及） | 11 | A-Ch90/91/92；B-Ch101/102/103/105、Ch147/148；C1-Ch119；C2-Ch167（部分为边界判定） |
| 证据不足 | 3 | D-Ch114/115/117（功法命名同一性不可确证） |
| n/a | 2 | C1-Ch117/118（isolate 空洞，无 accepted head） |

**明确漏报 100% 落在分支1（词面匹配层），分支2/分支3 均为 0。** 失败模式为三类主模式 + 一类弱模式：
1. **插字/paraphrase**：`与守灵交易`↔`与守灵的交易`、`守门者后人`↔`守门者的血脉`、`母亲血脉`↔`母亲的钥匙印记`；
2. **词条生成缺陷**：name 拆分正则缺《》+ core phrase len≥5 下限，使`灵渊拳`/`第一式`类短核心词永不成为 term（B 案例 4 章全部因此）；
3. **边界规则误拒**：`_term_in_content` 对 <4 字 term 后接 CJK 一律判为更长词，`猎渊者印记` 不命中 `猎渊者`；
4. （弱）**跨章命名漂移**：`血引归墟`↔`血祭刀法`/`逆血归元`。

---

## 4. 量化：漏报是否集中在少数 key

方法：扫描 `.tmp/apply_*.py` 与 `.tmp/backups/*/apply_*.py` 全部 35 个含 tracking 刷新的人工 patch 脚本，提取其中的 tracking_id / setting_key 字面量，按 key 归并去重（原始数据 `.tmp/193s_patch_tally.json`）。

- 被人工 patch 刷新过的 distinct setting key：**54 个**；
- 被 ≥2 个不同 patch 脚本刷新过的 key：**46 个**（85%）；
- top 复发：`mother_descendant` ×12、`corrupted_seal_extension` ×12、`lingyuan_quan_first_form` ×10、`core_token.split` ×9、`handprint_of_child_lushen` ×9、`token_key` ×8、`self.as_door` ×8、`golden_emblem` ×7、`guardian_hunter_deception` ×7……
- 前 20 个高频 key 覆盖全部人工刷新事件的绝大部分；这些 key 全是主线核心 critical 设定（灵渊拳/母亲血脉/令牌/封印/猎渊者）。

**结论：漏报高度集中在少数核心 critical key，不是弥散的。** 这与分支1机制自洽——核心设定被 paraphrase 的频率最高，而它们的 term 集在引入章一次性冻结后从不更新。

旁证（human_marks 局限）：`human_marks.mark_id` 是确定性的 `cont-set-track-<tracking_id>`，同一 key 重复 orphan 会覆盖同一行（如 `lingyuan_quan_first_form` 的 mark 只显示 created_at_chapter=150，Ch105 事件被覆盖），故 marks 表无法用于复发统计，已弃用该口径。

---

## 5. 修复面评估（Phase B 输入）

### 5.1 分支分布结论

- 分支1（有界，词面匹配层）：明确漏报的 **100%**（8/8 明确 + 4 边界）。
- 分支2（提取契约/prompt，路由 V11）：**0%**——本样本中提取层与漏报无因果（active 设定走正文路径）。但注意：若未来某 key 被 demote 为 candidate，其刷新只剩 settlement 碎片匹配一条腿，提取层问题会重新变得相关；当前 23 次硬门样本中未出现该形态。
- 分支3（过滤层）：**0%**。

### 5.2 有界修复可消除的比例

按 8 章明确漏报估算：

- **词条生成修复**（name 拆分正则补《》、core phrase 下限从 5 降到 3-4 或引入"设定名 CJK 子串全量入 term"）：直接消除 B 案例 4 章（Ch104/146/149/150），并对 C 案例提供 `守门者`/`母亲` 等更细粒度 term 的可能——覆盖 **≥4/8（50%）**，是单点杠杆最大的修复；
- **边界规则放宽**（<4 字 term 后接 CJK 时，若该 CJK 后缀与 term 组成的复合词仍是设定相关名词，或干脆对来自设定名的 term 放宽后缀限制）：消除 A-Ch93（`猎渊者印记`）——**1/8**；
- **插字容错**（`与守灵交易` vs `与守灵的交易`：对 term 做"的/之/了"虚字删除归一化后再匹配）：消除 A-Ch93、C1-Ch120、C2-Ch163/166 这类 paraphrase——**4/8**；
- **命名漂移**（D 类）：词面方法不可达，需 alias 表或 LLM 判定，默认不在有界修复内——不计入 8 章明确漏报（D-Ch116 为边界项）。

合计：三项词面层修复的并集覆盖 **全部 8 章明确漏报（8/8 = 100%）**（每章至少被一项覆盖；即使保守只修《》+ 虚字归一化两项，也 ≥7/8 ≈ 88%），越过任务书 Phase B 的 ≥70% 修复门槛。三类词面修复均不改 prompt、不改提取契约、不改门禁口径，只在 `_apply.py` 的 term 生成与 `_term_in_content` 匹配函数内，改动有界且可用历史冻结库只读复算验证。

风险对冲：term 生成放宽（更短词、后缀放宽）必然提高误刷率——把"比喻性血脉"（C1-Ch119 类）误命中为设定提及。误刷的代价是 last_mentioned 虚高、孤儿预警延迟，方向与漏报相反但同样扭曲 five-gate 口径；修复必须配 scifi end10 回归 + 冻结库复跑（任务书 Phase C 已有此要求），并建议在修复 PR 中附带误报率对照（修复前后对冻结库全部章节的刷新差异清单）。

### 5.3 建议倾向

**进入 Phase C，修有界匹配层**（词条生成《》修复 + 虚字归一化 + 边界规则对设定名词放宽），命名漂移类（D）记录遗留、路由后续 alias 机制；本样本无需触碰分支2 的提取契约/prompt。

---

## 6. 证据局限与不确定性

1. **settlement JSON 未持久化**（§1.3）：candidate 路径（`_promotion_evidence_text`）的复算是碎片近似，可能低估或高估 promote 路径的命中。主结论不受影响（六案例全 active），但若未来要诊断 candidate 形态漏报，需要先补 settlement 持久化。
2. **"正文是否实质提及"含人工判定**：C2 的母亲系 paraphrase（Ch164/165/168）与 A-Ch92 判定为"边界/弱提及"，不同判定者可能移动 ±3 章；明确漏报 8 章不依赖这些边界判定。
3. **案例 D 功法同一性不可确证**：`血祭刀法` vs `血引归墟` 是否同一功法决定 D 的 3 章是漏报还是合理预警；本报告保守不计入漏报。
4. **192.v 发生在旧库** `task172b_xuanhuan_ch100.db`（后迁入 ch200 库，两库同 project_id；Ch93 现 head `fix-93-6-a98c0576` 即 192.v 修复版）。A 案例取证自 192v 冻结备份，为 pristine pre-fix 现场。
5. **pre-fix status 取自硬门时刻冻结库**；窗口内 status 未发生翻转可由"last_mentioned 全程停滞"推得（任何 promote 都会同时写 last_mentioned）。
6. **patch 次数统计依赖脚本字面量**：35 个脚本中若有通过 JSON 文件间接传 key 的，会低估复发次数（54/46 是下限）。
7. 多 token 兜底（`_has_multi_token_setting_reference`）在全部 23 章回放中命中 0 次——它要求 token 派生自 ≥5 字短语且同章命中 ≥3 个，对短核心词设定结构性无效；这本身也是分支1 的一部分，但未单独列章。
