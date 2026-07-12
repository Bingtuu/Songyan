# Task 171c: 改进杠杆组合验证报告（离线证据 + 退出判定）

> 生成时间: 2026-07-10
> 对应框架 `docs/reports/v7-literary-framework-review.md` §6.2 支柱 4 + §7.1 R2 + §8.5 退出判据。
> 前置：171a/171a-1（量具可信，两体裁 F1 ≥ 0.8）+ 171b（代表性样本，仅在对话承载层评估）。
> 度量工具：`scripts/run_171c_ab.py`（复用 171a 检测器 + 171b 分层，不改量具、不调 LLM）。

---

## 0. 一句话结论

**唯一可全离线验证的杠杆（确定性后处理）经实证是 Goodhart 假提升**：把一句自然对白拆成 2–4 段短引号，量具 exposition/章 0.8→0.0，但行文更碎、并未变好 —— 按框架 §8.5 **退出该杠杆**。其余杠杆（温度效应、换模型横比）需 live API 生成资源；本任务已**把温度死配置通电**（去 dead config），并给出各杠杆的假设 + 退出判据 + 现状结论。**未重启 prompt 仓鼠轮、未阻塞 Ch200、未放宽任何冻结口径、未做全自动 LLM 改写闭环。**

---

## 1. A/B 度量口径

- **度量集**：171b 分层后的**对话承载/混合层**章（scifi 5 章 + wuxia 4 章；稀疏章不计，对治样本错配）。
- **指标**：每章 exposition 单条命中数（排除 `repeated_revelation_beat` aggregate 双计）+ 每章 voice 同质命中数。
- **边际增益判据**：exposition/章相对降幅 ≥ 10% 才算"提升"；否则按退出判据停该杠杆、换下一根（防重演路径 B 递减迭代）。
- **基线**（`arm_baseline_*`）：scifi exposition 0.8/章、voice 0.2/章；wuxia exposition 0.5/章、voice 0.25/章。

---

## 2. 杠杆逐项结论

| 杠杆 | 假设 | 类型 | 结论 | 退出判定 |
|---|---|---|---|---|
| **确定性后处理 rewrite** | 拆长说明性引语能降 exposition | **离线已验证** | **Goodhart 假提升**：scifi 0.8→0.0（降幅 1.0）但纯属把长引语切成短片段规避 50 字阈值，prose 更碎；wuxia 0.5→0.5（降幅 0，无可拆多句长引语） | ❌ **退出**（§8.5：假提升不固化） |
| 解码参数（temperature） | 声纹同质部分源于低多样性解码 | 需 live | **配置已通电**（本任务修 dead config），效果验证待 live A/B | ⏳ 就绪待验证 |
| 换模型 | deepseek-chat 是当前天花板 | 需 live + 第二 provider 凭证 | 通道现成（litellm，改 `.env` 即可换），横比待资源 | ⏳ 就绪待验证 |
| 好样本 few-shot | 好对白示例比抽象约束有效 | —— | **不作为本任务杠杆**：该机制即已封存的路径 B（Task 170l `voice_samples`/`voice_anchor`），框架明确排除 170h–170l | 🚫 排除 |
| 人工定点抽读 | 长跑兜底 | 常驻 | 经 171p/172p/173p 注入，不设退出 | 常驻 |

---

## 3. 确定性后处理杠杆：实证细节（关键发现）

### 3.1 数据
```
scifi:  baseline expo/ch=0.8  → postproc expo/ch=0.0  （relative_drop=1.0, "improved"=true）
wuxia:  baseline expo/ch=0.5  → postproc expo/ch=0.5  （relative_drop=0.0, "improved"=false）
```

### 3.2 为什么"improved=true"是假象（Goodhart）
变换只在句子边界把 ≥50 字的多句引语拆成相邻短引语（**只改引号标点，零内容损失**）。scifi Ch1 实例：

- **BEFORE**：`"木卫二石板上的星图，指向的是这个坐标。十万年前的星图，指向的是这里。现在太阳系边缘的信号里嵌着同样的星图。你们觉得这是巧合？"`
- **AFTER**：`"木卫二石板上的星图，指向的是这个坐标。""十万年前的星图，指向的是这里。""现在太阳系边缘的信号里嵌着同样的星图。""你们觉得这是巧合？"`

exposition 命中归零，**仅因为**每个碎片都掉到 `info_delivery_dialogue_min_chars=50` 阈值之下。**行文没有变好，反而变碎**（连续 4 段独立短引号，读感更机械）。这正是"优化了指标、没优化被指标代表的东西"。

### 3.3 判定
确定性后处理无法**语义地**把 info-dump 转成"动作 + 短对白"（那需要理解与改写，即 LLM）；它能做的只有规避阈值。**按框架 §8.5 退出该杠杆，不固化、不注入 171p。**这也复证了框架的核心论断：文学提质是语义问题，不是可被确定性代码闭环解决的形式问题。

---

## 4. 温度死配置修复（去 dead config）

- **发现**：`settings.llm_temperature`（默认 0.7）自定义以来**从未被任何代码读取**——温度在各 agent 调用点硬编码（Writer 0.8、Revision 0.3 等）。"改配置调温度"这根杠杆此前**根本没接线**。
- **修复**：`call_llm(temperature=None)` 时回退 `settings.llm_temperature`（与 `max_retries` 同模式）。**行为保持**：所有生产 caller 都显式传温度，解析出的默认值 = 旧硬编码 0.7，无回归；但配置从此**可达、可测**，为"解码参数"杠杆的 live A/B 备好开关。
- 单测：`test_call_llm_temperature_defaults_to_settings` + `test_call_llm_explicit_temperature_overrides_settings`。

---

## 5. 出口纪律（框架 §8.5）

- 确定性后处理 = **假提升 → 退出**（已固化为不采纳的证据，不注入长跑）。
- 温度 / 换模型 = **就绪待 live 验证**（通道备好，需 API 预算 / 第二 provider 凭证；不达增益即停，达则经 `NNNp` 注入）。
- **不回退到用文学阻塞 Ch200**：Tier 3 迭代按判据推进/退出，主线不受影响。

---

## 6. 复现

```
python scripts/run_171c_ab.py score --db .tmp/task170p_validation.db --arm baseline_scifi
python scripts/run_171c_ab.py score --db .tmp/task170p_validation.db --arm postproc_scifi --postproc
python scripts/run_171c_ab.py compare --base baseline_scifi --arm postproc_scifi
# wuxia 同理（.tmp/task171a1_wuxia.db）
```
- arm/compare 产物：`.tmp/task171c/arm_*.json`、`.tmp/task171c/compare_*.json`
