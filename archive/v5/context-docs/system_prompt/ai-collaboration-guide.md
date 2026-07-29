# Songyan 多 AI 协作工程规范

> 本文件定义多个 AI 实例协作开发 Songyan 项目时的工程规范。
> 核心思想：**把 AI 当作人类开发者来管理**——有入职手册、有项目文档、有任务看板、有交接单、有代码仓库。

---

## 1. 只需要 1 个 API Key

### 1.1 配置方式

项目根目录只有一个 `.env` 文件管理所有 API 配置：

```bash
# .env（gitignored，不提交到仓库）
LLM_API_KEY=sk-xxx
LLM_BASE_URL=https://api.deepseek.com
LLM_MODEL=deepseek-chat
LLM_TEMPERATURE=0.7
```

### 1.2 为什么只需要 1 个

- **开发层的 AI**（Kimi Code CLI / Cursor / Claude Code）由用户运行环境提供 LLM 能力，不需要项目配置 API
- **应用层的 API**（Songyan 系统运行时调用 DeepSeek-chat）通过同一个 `.env` 配置
- 如果开发 AI 需要调用外部 LLM（如测试 Writer Agent），同样读取这个 `.env`

### 1.3 Key 维护原则

- `.env` 文件已加入 `.gitignore`，绝不提交到仓库
- 新 AI 接手时，用户只需告知"请确保 `.env` 已配置"
- 不允许多个 Key 分散配置（如不同的 config.json、不同的环境变量名）

---

## 2. 规范一致性：文档分层 + "先读后做"协议

### 2.1 文档金字塔

```
                    ┌──────────────┐
                    │   AGENTS.md   │  ← 所有 AI 必须读，不可违背规则
                    │  (全局约束)   │
                    └──────┬───────┘
                           │
              ┌────────────┼────────────┐
              ▼            ▼            ▼
        ┌─────────┐  ┌──────────┐  ┌──────────┐
        │ 技术方案 │  │ 状态看板  │  │ 协作规范  │
        │  V2.md  │  │ STATUS   │  │ guide    │
        └────┬────┘  └────┬─────┘  └────┬─────┘
             │            │             │
             └────────────┼─────────────┘
                          ▼
                    ┌──────────────┐
                    │ 当前 Task 文件 │  ← 当前 AI 只读这一个
                    │ 00x-xxx.md   │
                    └──────────────┘
```

**注意**：V1→V2 的 review 记录（`dev_design_v1_review_fn.md`）已吸收到 V2 方案，开发 AI 不需要读。

### 2.2 "先读后做"启动协议

**每个 AI 接手任务时必须执行：**

```markdown
## 启动协议

1. 读取 `AGENTS.md`（全局约束）
2. 读取 `development-tech-plan-v2.md`（技术方案）
3. 读取 `docs/STATUS.md`（当前项目状态）
4. 读取 `tasks/00x-xxx.md`（当前 Task 规格）
5. 用 5-8 行总结你理解的任务边界
6. 确认边界后再开始修改代码
7. 不要读取完整架构文档，除非当前任务明确需要
```

### 2.3 为什么能保持一致性

- **AGENTS.md 是"宪法"**：所有 AI 必须遵守，违反会触发审查
- **Task 文件是"合同"**：当前 AI 只对这个 Task 负责，不越界
- **STATUS.md 是"黑板"**：记录当前进度，防止 AI 重复做已完成的任务

---

## 3. 信息传递：交接文件 + 状态黑板 + Git

### 3.1 交接文件（每个 Task 完成后生成）

文件名：`tasks/00x-xxx-DONE.md`

```markdown
# Task 00X: XXX — 交接报告

## 完成状态
- [x] 代码实现
- [x] 测试通过
- [x] 文档更新

## 改了哪些文件
- `src/songyan/agents/xxx.py` — 新增 XXX 功能
- `src/songyan/models/xxx.py` — 新增 XXX 模型
- `tests/test_xxx.py` — 新增 5 个测试用例

## 如何验证
```bash
pytest tests/test_xxx.py -v
# 期望：5 passed
```

## 已知问题 / 限制
- XXX 功能目前只支持 YYY，ZZZ 场景未覆盖（留给 Task 00Y）

## 下一步依赖
- Task 00Y 依赖本 Task 的 `XXX` 接口
- Task 00Z 需要本 Task 生成的 `YYY` 数据

## 关键设计决策
- 选择了 ABC 方案而不是 DEF，原因是 GHI
- 如果后续发现问题，需要回头修改本 Task
```

### 3.2 状态黑板（`docs/STATUS.md`）

每次任务完成后必须更新：

```markdown
# 项目状态板

## 当前阶段
Phase 2 — 写前管线（Task 008-011 + 017-018）

## 已完成
- [x] Task 001: 项目初始化
- [x] Task 002: Pydantic 模型
- ...

## 进行中
- [ ] Task 008: GoalPlanner Agent（当前 AI 负责）

## 待开始
- [ ] Task 009: CreativeDirector Agent
- ...

## 阻塞项
- 无

## 最近变更
- 2026-05-24: Task 007 完成，CLI 创建项目可交互运行
```

### 3.3 AI 间信息传递流程

```
AI-1 完成 Task 008
  │
  ├──▶ 更新 docs/STATUS.md（标记 Task 008 完成）
  ├──▶ 生成 tasks/008-goal-planner-DONE.md（交接文件）
  └──▶ git commit（提交代码 + 交接文件 + 状态更新）
       │
       ▼
AI-2 接手 Task 009
  │
  ├──▶ 读取 docs/STATUS.md（了解当前状态）
  ├──▶ 读取 tasks/008-goal-planner-DONE.md（了解上游输出）
  ├──▶ 读取 AGENTS.md + 技术方案（确认规范）
  ├──▶ 读取 tasks/009-creative-director.md（当前 Task）
  │
  └──▶ 执行"先读后做"协议 → 开始开发
```

### 3.4 Git 提交规范

```bash
# 每个 Task 完成后提交
git add -A
git commit -m "task-008: GoalPlanner Agent 实现

- 实现 define_chapter_goal() 接口
- 输出结构化 ChapterGoal（含 target_events, emotional_arc, hooks）
- 遵守 Genre Profile pacing_rule
- 5 个测试用例全部通过
- 交接文件: tasks/008-goal-planner-DONE.md"
```

---

## 4. 交接检查清单

AI 完成任务时必须确认：

- [ ] 代码实现完成
- [ ] 测试通过（pytest -v）
- [ ] 不违反 AGENTS.md 任何规则
- [ ] 更新了 docs/STATUS.md
- [ ] 生成了 tasks/00x-xxx-DONE.md 交接文件
- [ ] git commit 提交（包含代码 + 文档）
- [ ] 向用户汇报：做了什么、如何验证、已知限制

AI 接手任务时必须确认：

- [ ] 读取了 AGENTS.md
- [ ] 读取了技术方案 V2
- [ ] 读取了 docs/STATUS.md
- [ ] 读取了当前 Task 文件
- [ ] 读取了上一个任务的 DONE.md（如果有依赖）
- [ ] 用 5-8 行总结了任务边界
- [ ] 确认边界后再开始修改代码
