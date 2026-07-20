# V11 Plan 备忘：开源可用化收尾

> **状态**: 预登记备忘，不是当前阶段任务事实源。
> **前置**: V9 完成 urban Ch100 与阶段收口；V10 完成跨体裁 Ch200 与优秀度信号包。
> **定位**: V11 作为项目开源前的最后一个工程收尾阶段，把 Songyan 从“作者本人可稳定使用的复杂工程系统”推进到“外部技术用户可独立安装、运行、诊断、恢复、导出”的负责任开源状态。
> **边界**: 不做大众商业产品，不做 Web/UI/桌面端，不新增核心 Agent / Workflow 节点。

---

## 一句话目标

> **V11 不再扩张核心生成能力，而是把已有能力交付出去：让一个懂命令行、会配置 API key 的外部用户，不读 V5-V10 历史任务文档，也能按 README/docs 完成安装、初始化、短窗口生成、失败恢复、报告理解和书稿导出。**

---

## 背景判断

Songyan 到 V9/V10 后，核心引擎应已具备：

- 长篇生成闭环：规划、生成、审查、修订、接收、结算、摘要、长期记忆；
- 多体裁运行时画像：scifi/xuanhuan/wuxia/urban 等体裁通过 `GenreRuntimeProfile` 解耦；
- 长窗口证据：sci-fi Ch200+，多体裁 Ch100/Ch200 分段验收；
- 生产化地基：日志、成本追踪、预算熔断、wheel 打包、CI、doctor、export、五门工具；
- 质量信号：五门判定、T9、CED、overdue、health，以及 V10 引入的优秀度信号包。

但“核心能力强”不等于“外部用户能顺利使用”。V11 要补的是外部使用路径上的边缘工程：初始化、恢复、诊断、配置安全、项目资产管理、文档和发布纪律。

---

## 用户画像

V11 面向的用户不是普通商业软件用户，而是外部技术用户：

- 能使用命令行；
- 能准备 Python 环境；
- 能配置 LLM API key；
- 愿意阅读 README 和少量 docs；
- 不应被要求理解 V5-V10 历史任务、诊断 DB / 终判 DB 区别、五门工具内部口径、profile 覆盖层实现细节。

这一定义使 V11 可在一个阶段内完成；如果目标换成非技术用户的完整写作产品，则需要 Web/UI、后台任务、账户、可视化编辑器等另一条产品线，不纳入 V11。

---

## 开发主题

### 1. 安装与初始化闭环

目标：新环境中从安装到生成第一章的路径足够短、可诊断、可复现。

候选工作：

- 强化 `songyan doctor`：覆盖 Python/package 版本、资源枚举、DB schema、LLM key/base_url/model、日志目录、写权限、成本预算配置。
- 增加首次运行向导或文档化的最短路径：配置 key、初始化 DB、创建项目、跑 Ch1-3、导出。
- 给出成本预估：短窗口、Ch100、Ch200 的粗略区间，明确预算熔断变量。
- 统一错误提示：缺 key、资源缺失、schema drift、DB 路径不可写时给出下一步命令。

### 2. 项目资产生命周期

目标：用户知道一个长期创作项目如何保存、迁移、恢复和归档。

候选工作：

- `songyan backup`：打包 DB、项目配置、关键日志索引、运行摘要。
- `songyan restore`：从备份恢复到新路径，并校验 schema / resource compatibility。
- `songyan migrate` 或 schema 版本账本：明确当前 DB schema 版本、迁移状态、缺失列/索引。
- `songyan clone-project` / `archive-project`：支持复制项目或封存项目资产。
- 明确 `export` 与 `backup` 的边界：`export` 只产书稿，`backup` 保存可续跑资产。

### 3. 失败恢复体验

目标：系统不仅能恢复，还要告诉用户如何恢复。

候选工作：

- 将常见失败分类并标准化输出：LLM JSON 错误、成本熔断、上下文预算墙、T9 失败、settlement 失败、schema drift、资源缺失。
- 每类失败输出明确动作：重试、resume、isolate、提额、查看报告、运行 five-gate、生成诊断包。
- 保证失败章正文、version、run log、app log、cost usage 可追溯。
- 增加恢复路径测试：故意触发失败后，按提示命令恢复到可继续运行状态。

### 4. 运行报告包

目标：一条命令生成可分享、可归档、可复查的 run bundle。

候选工作：

- `songyan report --bundle` 或新命令 `songyan bundle-run`。
- 包含：run 元信息、章节状态、accepted/version 列表、成本明细、五门结果、T9、CED、overdue、health、热点章节、日志索引。
- 输出机器可读 JSON + 人类可读 Markdown。
- 支持脱敏：API key、绝对路径、敏感环境变量不得进入 bundle。

### 5. 配置安全

目标：外部用户可以调参，但不容易把系统调坏。

候选工作：

- 强化 `songyan profile diff/show/upsert`：支持推荐范围、危险字段提示、回滚历史。
- 增加 `profile validate`：检查 base_budget、horizon floor、health weight、max_* 等关键字段的合理范围。
- 对体裁 / mode JSON 给出更友好的 schema 错误信息。
- 明确哪些配置属于内容画像，哪些属于运行时画像，哪些属于冻结验收口径，不允许混改。

### 6. 文档与样例

目标：用户只读 README + docs 就能完成一次短篇验证。

候选工作：

- Quickstart：从空环境到 Ch1-3 accepted + export。
- 10 章教程：解释 run_id、resume、成本、日志、report。
- Ch100 长跑手册：预算设置、wrapper 使用、段边界五门检查、失败早停纪律。
- 故障排查手册：按错误类型路由。
- 配置手册：体裁、mode、profile、prompt card、LLM endpoint。
- 样例项目：提供小型可运行模板或只读样例 DB，便于用户理解输出结构。

### 7. 发布纪律

目标：开源发布不是“代码能跑”，而是发布物可验证。

候选工作：

- 版本号与 CHANGELOG。
- Release checklist：wheel 构建、非仓库 cwd 验收、Windows 路径验收、资源枚举、CLI smoke、doctor、export。
- CI 扩展：默认 pytest、CLI pytest、mypy、ruff、wheel smoke。
- License / AGPL 说明、贡献指南、问题模板、最小复现模板。

---

## V11 验收判据草案

V11 通过不以新增生成质量为核心，而以外部可用路径为核心。

1. 新环境 `pip install` 后，用户只按 README/docs 能完成 `doctor -> create-project -> run Ch1-3 -> export`。
2. 非仓库 cwd 下 wheel 安装路径通过资源枚举、项目创建、短窗口生成和导出。
3. 至少 5 类常见失败能给出明确恢复路径，并有自动化或半自动化验收证据。
4. 任意 run 可生成完整诊断 bundle，包含成本、章节状态、五门/T9/CED/overdue/health、日志索引，并支持脱敏。
5. 项目可 backup/restore，恢复后能继续 `--resume` 或至少通过 doctor 校验为可读可导出状态。
6. 配置变更可 diff、validate、回滚；危险运行时参数有提示。
7. README + docs 足以让外部技术用户完成短篇验证，不需要阅读历史任务文档。
8. 发布物有版本号、CHANGELOG、release checklist、CI 绿线和最小复现指南。
9. V9/V10 既有守护项不破：scifi 回归、五门口径、CED consistency-only 口径、T9 clean rerun 纪律、SQLite 唯一事实源。

---

## 明确不做

V11 不做以下事项：

- Web UI、桌面端、移动端、小程序；
- 账号系统、云同步、模型 key 托管；
- 后台任务队列、多人协作、权限管理；
- 模板市场、插件市场；
- 新增核心 Agent / Workflow 节点；
- 新一轮体裁研究或质量研究主线；
- 把 Songyan 包装成普通非技术用户可无门槛使用的商业写作软件。

这些方向可以基于 Songyan 另起项目，但不应挤占 V11 的开源收尾目标。

---

## 建议执行顺序

编号待 V10 收口后正式分配。建议顺序如下：

1. 文档与 Quickstart 先行，定义外部用户最短路径。
2. 强化 doctor 与错误提示，先让失败可解释。
3. 做 backup/restore 与 schema 版本账本，稳住项目资产生命周期。
4. 做 run bundle，把诊断、成本、质量门、日志索引收成一个交付物。
5. 做配置安全：validate、rollback、危险项提示。
6. 做 release checklist 与 wheel/非仓库 cwd/Windows 验收矩阵。
7. 最后做开源前总验收：新环境从零跑通、故障注入、文档复核、发布物检查。

---

## 风险

| 风险 | 对策 |
|------|------|
| V11 膨胀成产品化大改 | 明确只面向技术用户；不做 UI/账号/后台服务 |
| 继续新增质量研究导致收不了口 | V11 禁止新增核心质量研究主线；质量能力留在 V10 完成 |
| 文档仍依赖历史任务事实 | README/docs 重新组织为用户路径，任务文档只作开发审计材料 |
| 配置能力强但误用风险高 | `profile validate`、推荐范围、危险项提示、回滚历史 |
| 诊断信息分散 | run bundle 统一收口，日志只保留索引与必要片段 |
| 发布验收只在仓库 cwd 成立 | wheel + 非仓库 cwd + Windows 路径作为硬验收 |

---

## 与 V9/V10 的关系

- V9 解决“系统能不能稳定跑、能不能按生产化地基交付”。
- V10 解决“多体裁长窗口是否仍稳定、生成质量是否不只是一致而是更好”。
- V11 解决“外部技术用户能不能负责任地使用这个项目”。

因此 V11 是开源前收口，不是新产品线。
