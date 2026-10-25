# 霞飞路《旧案》ch1–3 批准卡与窄检查

稳定 `project_id`：`xiafei-jiuan`。

卡在 `src/songyan/plan_facts/xiafei_jiuan.json`，经 `songyan.db.plan_fact_loader` 写入 `plan_*`。全部 `approval_status=approved`。时局锚 `attr-era-window`（`1931-09-18前`）来自种子「九一八前夕」，`source=plan`。证物方向、数量、归属、机制方向、案发 `1931-03` 由 Mew 代批，`source=human`。这些是计划层应在写正文之前钉住的值，不是 canon-v4 漂移后的句子。

锦州战事记在历史锚 `xiafei-ta-jinzhou`（`1931-11后`），没有任何 ch1–3 事件指向它。本案故事锚是 `xiafei-ta-march`（`1931-03`）。

检查器在 `src/songyan/plan_checks/`，不写 canon，也不读结算库。

| 路线图类 | v4 里发生了什么 | 批准卡 | fixture 上谁标出 |
|----------|-----------------|--------|------------------|
| T1 证物属性漂移 | ch2 把一道「右向左」改成「自内向外」，并添纤维残留、得出至少两人 | 刮痕 `direction=右向左`，`count=1` | 必须提及缺「右向左」；类型化方向与数量不符；主张 `claim-ch2-scratch` 为矛盾 |
| T5 证物归属漂移 | ch3 把钩状弧线说成横杆拓片上的痕迹 | 钩痕 `ownership=门框暗处` | 类型化归属不符；主张 `claim-ch3-hook` 为矛盾。ch2 的「门框暗处」仍算提及 |
| T4 机制方向 | ch2「往外拉」，ch3「从外往内拉」 | 机制 `direction=往外拉` | ch3 必须提及缺「往外拉」；类型化方向不符；主张 `claim-ch3-pull` 为矛盾 |
| T2 证据遗漏 | ch2 正式报告不写后脑钝器伤 | 线索 `clue-blunt` 必须在第 1、2 章出现「钝器伤」 | 必须提及缺「钝器伤」；主张 `claim-ch2-blunt` 为未提及 |
| T6 时代时间线 | ch1 头版「日军进逼锦州」（1931 年末）；ch3 当票三月初九与九一八前相容 | 时局 `time_anchor=1931-09-18前`；案发 `1931-03` | ch1 必须提及缺「九一八」；类型化时间锚不符；主张 `claim-ch1-era` 为矛盾。ch3 的 `1931-03` 与卡一致 |

另有一条不计入这五类的章内主张：`claim-ch1-physics`（向左推闩时刮痕应为右向左，不能说方向反了）。v4 第 1 章写了「刮痕的方向反了」，确定性核验判为矛盾。

类型化比较用的摘录在 `tests/fixtures/xiafei_jiuan/v4_extracts.json`，是对 v4 正文的显式标注，不是从正文再抽进 canon。主张的确定性路径用同目录 `claim_anchors.json` 里该主张自己的支持 / 矛盾短语；矛盾短语优先。LLM 路径只发送这一条主张和这一章，测试注入 `complete`，不在 CI 里调用 API。

这组对照说明检查器会标出那五类。它不是重跑三章之后的召回数字。

2026-10-25 的重跑没有新正文：执行环境没有 LLM API key。召回未测量，见 [experiments/xiafei-plan-gate-rerun-2026-10-25](experiments/xiafei-plan-gate-rerun-2026-10-25/README.md)。审查 state 不提供类型化摘录和主张锚；同一段 v4 第 3 章在缺这两项时标不出钩痕归属漂移。
