# Task 172c — wuxia Ch100 修复后干净重跑 DONE

> **完成时间**: 2026-07-18  
> **项目**: `273a8408be8e4caf8cbc1e91954da600`  
> **DB**: `.tmp/task172b_wuxia_ch100.db`  
> **Run**: `run-82968662`  
> **报告**: `archive/v8/reports/172c-wuxia-ch100-climb.md`

## 结论

172c 已完成。wuxia clean rerun 从 Ch1 推进到 Ch100，最终 100/100 accepted，0 failed，0 halt；Ch100 五门全部 PASS。V8 多体裁中篇证据从 xuanhuan Ch100 扩展为 xuanhuan + wuxia 两个非 sci-fi 体裁 Ch100。

| gate | wuxia Ch100 | sci-fi Ch100 | 判定 |
|---|---:|---:|:---:|
| completeness | 100/100 | 100/100 | PASS |
| budget_peak | 0.965 | 0.989 | PASS |
| consistency CED/1k | 0.17（58 issues） | 0.40（157 issues） | PASS |
| overdue unresolved | 35 | 168 | PASS |
| health | 8.3 | ≥8.0 | PASS |

## 关键修复链

- 172c.r：修复伏笔 resolve 四层根因，并让 continuity health 与 vdim overdue 口径对齐。
- 172c.s：将 wuxia 长窗口 `foreshadowing_horizon_floor` 校准到 48；`base_budget=10500`；角色状态长窗口档加宽；state_mismatch 降为 P3 观测；voice-anchor 软化。
- 172c.t：新增 `continuity.health_overdue_weight`，scifi 默认 0.3 不变，wuxia 设置为 0.15；Ch60/Ch99 health false-halt 消除，vdim overdue 门保持独立。

## 验证

```powershell
$env:TEMPLATE_ID = "wuxia"
python .tmp\vdim_compare.py 25
python .tmp\vdim_compare.py 50
python .tmp\vdim_compare.py 75
python .tmp\vdim_compare.py 100
```

四段均 PASS。Ch100 终点 continuity audit：health 8.3，orphaned 13，forgotten 0，overdue 35。

聚焦测试：

```powershell
python -m pytest tests/test_172ct_wuxia_health_overdue_weight.py tests/test_123_gates.py::test_health_low_streak_ignores_recovered_health_score -q
```

结果：5 passed。
