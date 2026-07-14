# Songyan 项目状态

> 短状态板。这里只保留当前判断、最新证据和下一步，避免挤占开发上下文。任务细节看 `tasks/V8-README.md`，文档路由看 `docs/INDEX.md`，长历史看 `archive/`。

## 当前判断

| 项 | 结论 |
|----|------|
| 当前阶段 | **V8**：多体裁可插拔质量 + 章数爬坡 |
| V7 收尾 | **已完成**。sci-fi/space_opera + webnovel_intense 单一体裁稳定跑到 Ch200，200/200 accepted，D1 hard clean pass；Ch201-Ch220 20/20 accepted |
| V7→V8 调整 | 结束单一体裁 Ch250/Ch300 继续爬坡；原 Task 172 取消归档，V8 从 **Task 172a** 开始 |
| V8 主线 | **Task 172a 体裁运行时画像（GenreRuntimeProfile）**：把 Context Diet 2.0 的运行时契约从 sci-fi 默认值解耦 |
| 当前风险 | xuanhuan `--end 15` 在 Ch8 因 `budget_used_before_emergency=1.4019 >= 1.3` 触发硬门禁暂停，暴露系统对科幻状态动力学过拟合 |

## 最新证据

| 维度 | 事实 |
|------|------|
| V7 单一体裁达成 | Ch1-Ch200 200/200 accepted；Ch201-Ch220 20/20 accepted；T9 hard clean 持续为 0 |
| 多体裁短窗口 | xuanhuan `--end 3` 通过；`--end 15` 在 Ch8 被 budget ratio halt 阻塞 |
| 根因 | V5/V6/V7 验证集中在 sci-fi，默认运行时是科幻的隐式画像；xuanhuan 状态项密度（功法/境界/势力/法宝/地图）远超科幻，导致 Context Diet 默认预算溢出 |
| 方向 | 结束单一体裁无限爬坡，建立按体裁定制的 `GenreRuntimeProfile` |

## 最近验证

| 命令 / 证据 | 结果 |
|-------------|------|
| V7 收尾验证 | Ch1-Ch220 全 accepted，T9=0，Halt=None |
| xuanhuan `--end 3` | completed=[1,2,3]，failed=[]，T9=0（后台任务已超时结束） |
| xuanhuan `--end 15` | Ch8 触发 `context_emergency_budget_ratio_halt`（后台任务已清理） |
| `python -m pytest tests/test_163_concept_budget.py tests/test_164_text_cleanliness.py tests/test_171u_d1_clean_application.py -q` | 31 passed |
| `ruff check src/ tests/` | 14 pre-existing warnings，无新增 |

## 项目整理

- V5/V6/V7 历史报告已归档到 `archive/v5/reports/`、`archive/v6/reports/`、`archive/v7/reports/`。
- Task 170 文学提质中间过程稿已归档到 `archive/v7/tasks/`，入口保留总览与关键 DONE 文档。
- Task 172（Ch250）已归档到 `archive/v7/tasks/172-ch250-transition-validation-archived.md`。
- `.tmp/` 已清理，仅保留当前关键数据库与实验数据。
- 后台任务已全部清理，当前无活动后台任务。

## 下一步

1. **V8 P0**：启动 Task 172a `GenreRuntimeProfile`。
2. 先完成 172a.1 现状审计，把 Context Diet 2.0 中体裁敏感的常量/阈值枚举清楚，并**把当前 sci-fi 默认行为显式固化为 baseline profile**。
3. 按 172a.2→172a.7 依次推进；过程中引入 **Consistency Error Density (CED)** 作为跨体裁可比指标。
4. 长调研结论已写入 `docs/reports/v8-literature-and-landscape-review.md`，后续设计以此报告为外部依据。

## 入口

- V8 任务事实：`tasks/V8-README.md`
- V7 历史事实：`tasks/V7-README.md`
- 文档路由：`docs/INDEX.md`
- Task 172a 规划：`tasks/172a-v8-genre-runtime-profiles.md`
- V7 归档：`archive/v7/INDEX.md`
- V6 归档：`archive/v6/INDEX.md`
- V5 归档：`archive/v5/INDEX.md`
