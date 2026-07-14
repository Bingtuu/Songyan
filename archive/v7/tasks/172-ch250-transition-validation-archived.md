# Task 172: Ch250 过渡验证

> **框架**: V7 阶段 Z 渐进爬坡（Ch200 → Ch250 → Ch300）
> **类型**: 长跑验证（阶段 Z 第二里程碑）
> **优先级**: P0（171w 完成后启动）
> **依赖**: 171u Ch200 D1 hard clean pass；171w Ch201-Ch220 hardening 重验 pass
> **状态**: 占位，待前置完成后开工

## 目标

Task 172 的目标不是重新证明 Ch200 能跑通，而是验证系统在 **D1 hard clean 已收口、Ch200+ 文学护栏已由 171w 证明可持久化/可审计/可落正文** 后，能否稳定推进到 Ch250。

放行重点：

1. T9 hard issue 在 Ch201-Ch250 持续为 0；
2. health/orphan/T12 不出现真实退化；
3. 171v 的角色主动选择、概念预算、母题疲劳、配角目标护栏在长一点的窗口内仍有效；
4. 至少保留 15% 人工抽读，不用单点机器文学分替代阅读判断。

## 前置条件

| 前置 | 标准 |
|---|---|
| 171u | Ch1-Ch200 当前 accepted head T9 duplicate/meta/artifact=0，报告事实源无 stale P1 污染 |
| 171w | Ch201-Ch220 20/20 accepted，T9 hard issue=0，配角目标落正文，主动选择/概念预算/母题疲劳有 observe 报告，Ch207 settlement 缺口已修复 |
| DB | `.tmp/task171_ch1_ch200.db` 或后续指定 Ch200 clean DB 可 resume |
| 文档 | `docs/STATUS.md`、`tasks/V7-README.md`、Ch200 分析报告已同步前置结论 |

## 执行边界

### 做

1. 从 Ch200 clean DB resume 至 Ch250。
2. 每 25 章输出一次中间报告，至少覆盖 Ch225、Ch250。
3. 保持 enforce + isolate，个别失败不阻塞整体，但必须记录 gaps。
4. 对 Ch201-Ch250 抽读至少 15%：
   - 固定样本 + 高风险章；
   - 如触发 Tier 2 spot_read，相关章必须纳入抽读。
5. 复核 171v 护栏效果：
   - 主角主动选择；
   - 概念密度；
   - 母题疲劳；
   - 配角独立目标。

### 不做

- 不放宽 T9/T10/T12/health/orphan 冻结口径；
- 不以文学机器分单点升降阻塞 run；
- 不在 172 内做大规模文学 prompt 重构；
- 不把 171u 未清干净的问题带入 Ch250；
- 不直接跳到 Ch300。

## 验证指标

| 面 | 判据 |
|---|---|
| accepted | Ch1-Ch250 当前事实源 250/250，或 gaps 有明确 isolate 记录与修复路由 |
| Halt | None，或 halt 对应真实退化且进入 172p |
| T9 | duplicate/meta/artifact=0 |
| health | median >= 8.5，无连续 health_low 真实退化 |
| orphan | orphan slope 不显著高于 Ch200 基线 |
| report | Ch250 report 只取最新事实源，无 stale 污染 |
| 文学观察 | 抽读无连续三章“被协议牵着走”、无连续三章纯概念解释推进 |

## 撞墙路由

如 Ch201-Ch250 出现阻断，优先拆成 `172p-*` 定点修复，不在 172 中临时改口径。

建议分类：

| 类型 | 路由 |
|---|---|
| T9 artifact/duplicate 新漏检 | 172p 文本洁净撞墙修复 |
| critical orphan false positive | 172p setting/continuity 同义刷新修复 |
| health/T12 真实退化 | 172p gate/health 定点修复 |
| 文学护栏失效但不触硬门 | 172p 或 171v 后续补丁，observe-first |

## 验证命令

```powershell
$env:DATABASE_URL = "sqlite:///.tmp/task171_ch1_ch200.db"
$env:START_CHAPTER = "201"
$env:END_CHAPTER = "250"
python scripts/run_171_ch200.py --resume
python scripts/run_171_ch200.py --report
```

常规回归仍按具体修复范围执行：

```powershell
python -m pytest tests/ -q
ruff check src/ tests/
```

## 出口标准

Task 172 完成后需产出：

1. Ch250 长跑报告；
2. 15% 抽读报告；
3. 是否进入 Ch300 的明确判定；
4. 如未通过，创建对应 `172p-*` 撞墙修复 task，而不是改阈值或跳过。
