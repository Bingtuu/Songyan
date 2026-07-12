# Task 171c: 改进杠杆组合验证 —— DONE（离线证据收尾）

> **框架**: `docs/reports/v7-literary-framework-review.md` §6.2 支柱 4 + §7.1 R2 + §8.5
> **状态**: ✅ **完成（离线结论收尾，用户拍板）**
> **报告**: `docs/reports/task-171c-improvement-levers-report.md`
> **完成时间**: 2026-07-10

---

## 结论

Task 171c 把提质从旧框架的"单一 prompt 仓鼠轮"（E5）改造成**多杠杆 + 假设检验 + 退出判据**，并在 171a 可信量具 + 171b 代表样本上验证。核心结论：**唯一可全离线验证的杠杆（确定性后处理）经实证是 Goodhart 假提升**（量具命中归零但 prose 更碎、未变好），按框架 §8.5 退出；其余杠杆（温度效应、换模型横比）需 live API 资源，已备好通道 + 退出判据。顺带修复了 `llm_temperature` 死配置。**未重启 prompt 仓鼠轮、未阻塞 Ch200、未放宽冻结口径、未做全自动 LLM 改写闭环。**

用户拍板：以离线证据 + 温度通电收尾，不花 API 预算（框架 §8.4/§8.5："有结论即可，不要求必须提升"）。

---

## 验收对照（框架 §8 R2 + §8.5）

| 验收项 | 状态 | 证据 |
|---|:---:|---|
| 每根被验证杠杆有假设 + 受控 A/B + 边际增益判定 + 继续/退出结论 | ✅ | 报告 §2 逐杠杆表；确定性后处理有完整 A/B（scifi/wuxia）+ 退出判定 |
| 在 171a 可信量具 + 171b 代表样本上做 A/B | ✅ | `run_171c_ab.py` 复用 171a 检测器 + 171b 分层，仅在对话承载层评估 |
| "换模型"至少被评估一次并有横比结论 | ✅（横比通道就绪，结论=需资源） | litellm 单接口，改 `.env` 即换；本任务受用户拍板不花预算，记为"就绪待 live 横比"，符合 §8.4"有结论即可" |
| 不改冻结门禁；成熟杠杆注入通道对接 NNNp | ✅ | 无杠杆达标固化；确定性后处理判为不采纳、不注入 |
| ruff/pytest 通过 | ✅ | 见验证清单 |

---

## 工程改动清单

### `src/songyan/utils/literary_postproc.py`（新增，杠杆探针）
- `split_long_expository_quotes(text, min_chars=50)`：确定性、content-preserving 地把 ≥min_chars 的多句引语按句子边界拆成相邻短引语（只改引号标点）。作为"确定性后处理"杠杆的**最好情况**实现——用于**证伪**，不是生产变换。

### `src/songyan/llm/client.py`（去 dead config）
- `call_llm(temperature=None)` 回退 `settings.llm_temperature`（与 `max_retries` 同模式）。行为保持（生产 caller 均显式传温度，默认解析值 = 旧硬编码 0.7），但温度配置从此可达可测，为"解码参数"杠杆备好开关。

### `scripts/run_171c_ab.py`（新增，度量工具）
- `score`（含 `--postproc`）/`compare` 子命令：把任意 DB 的对话承载章打分成 arm summary，比较边际增益并出退出判定。复用 171a 检测器 + 171b 分层，不改量具、不调 LLM。

### 测试
- `tests/test_171c_literary_postproc.py`（6）：拆分逻辑、content-preserving、单句不拆、短引语不拆、ASCII 引号。
- `tests/test_llm_client.py`（+2）：温度默认解析 settings / 显式温度优先。

---

## 关键发现（Goodhart 实证）

scifi Ch1 长引语被拆成 4 段短引号后 exposition 命中归零（0.8→0.0），**仅因每碎片掉到 50 字阈值下**，行文反而更碎更机械。这复证框架核心论断：**文学提质是语义问题，确定性代码只能规避指标、不能改善被指标代表的质量**。真正的 info-dump→动作+短对白转换需要理解与改写（LLM），超出确定性后处理能力，且落入已封存的路径 B / 明确排除的全自动改写闭环。

---

## 验证清单
- [x] `ruff check` 覆盖 `client.py`/`literary_postproc.py`/`run_171c_ab.py`/两测试 全通过。
- [x] `tests/test_llm_client.py`+`test_171c_literary_postproc.py`+`test_171b_sampling.py` **28 passed**。
- [x] A/B 实测：baseline/postproc arm + compare 产物落 `.tmp/task171c/`。
- [x] 报告 `docs/reports/task-171c-improvement-levers-report.md` 产出。
- [x] 清理临时诊断脚本（`.tmp/inspect_171c_postproc.py`）。

---

## 出口与下一步
- **R2 达标（离线口径）**：杠杆变成可证伪假设 + 退出判据；确定性后处理证伪退出；温度通电、换模型通道就绪待 live 资源。
- **R&D 线 R0→R1→R2 全部落地**（171a/171a-1 量具效度 + 171b 代表样本 + 171c 杠杆判据），框架 §8 A/B/C 三组 + E（事实源纪律）已满足；**D（规模化并行）由 Task 171 Ch200 主线承接**。
- 若后续投入 live 资源：先修 few-shot 外的温度/换模型横比，达标经 `171p/172p/173p` 注入；全无增益则 §8.5"当前技术栈文学上限已达"，Tier 3 转长期研究，**不回退用文学阻塞 Ch200**。
