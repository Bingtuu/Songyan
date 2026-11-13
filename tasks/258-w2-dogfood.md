# 258 · 方向 D：W2 dogfood（owner 侧）+ runbook

| 项 | 内容 |
|---|---|
| 状态 | DOING——**助手侧备料完毕，等 owner 执行**（2026-11-13；runbook `.tmp/dogfood-w2.sh` + 复盘模板 `.tmp/dogfood-复盘模板.md`，均在 gitignore） |
| 关联 | `docs/tech-post-m4.md` §D；S6/S9（PRD §5.2）；249 runbook 模式 |
| 预估 | 助手备 runbook + 复盘模板（半个切片，零模型费由 owner 执行时产生） |

## 目标

owner 用 W2 在真实模型上写 3–5 章（《末班铜牌》或新书）：today → continue → review → canon confirm → accept → 下一章，抽卡路至少一章。产出复盘：真实摩擦清单（命令面/文案/流程断点）→ 逐项转新立项。

## 步骤

- [x] 助手：`.tmp/dogfood-w2.sh` runbook（造项目 → ch1 run → ch2-5 empty head + continue 循环 → confirm 批处理 → accept → review → signals → 费用归因；预算 ¥3 熔断）+ `.tmp/dogfood-复盘模板.md`（摩擦清单格式）
- [ ] owner：执行（预算 ¥3 内），填复盘
- [ ] 助手：复盘摩擦项评估 → 建议立项清单交 owner 拍板

## 验收标准

- [ ] 3–5 章 W2 走完，费用归因完整
- [ ] 复盘清单落地（每项：现象/频率/建议方向）
- [ ] 不因此而静默扩产品面（新立项须 owner 拍板）

## 完成总结

（待 DONE 时填写）
