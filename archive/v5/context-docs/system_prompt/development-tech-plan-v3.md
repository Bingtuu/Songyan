# Songyan V3.0 技术方案

> **版本**: V1.0
> **创建日期**: 2026-06-04
> **状态**: Draft
>
> V3.0 一句话：**不新增任何功能，修到 30 章稳定跑通。**

---

## 1. 与 V2 技术方案的关系

本方案**不覆盖** V2 已实现的能力（单章闭环、Punch Engine、跨章一致性、RAG 自动层等），只定义 V3.0 在 V2 基线上做的**稳定性加固**工作。

V2 技术方案中的架构设计、数据模型、Agent 职责划分**全部保留**，V3.0 只修改实现层面的稳定性问题。

---

## 2. 四层结构

```
Layer 0: 修复稳定性底线（P0/P1 bugs）      —— 不修完不进下一层
Layer 1: 消解代码结构债（文件拆分 + 死代码） —— 不改架构，只做一次
Layer 2: 封闭验证生成（30 章试跑）          —— 核心验证层
Layer 3: 系统化质量守卫（RAG 补测 + 合规）  —— 防止回退
```

层间串行。前一层退出条件不满足，不进入下一层。

---

## 3. Layer 0 技术实现

### 3.1 RevisionHandler 正文结构保护（052）

**问题**: LLM 返回不完整正文，导致截断。

**已实现保护**:
- 代码层: `MIN_CONTENT_RATIO = 0.5`，低于 50% 自动回退
- Prompt 层: 强化"必须输出完整修改后正文"

**待做**:
- 新增 `content_preservation_ratio` 字段到 `RevisionOutput`
- 单元测试覆盖截断 fallback / revert 两条路径
- 真实章节验证

### 3.2 database locked（053）

**问题**: WAL 模式下多连接竞争。

**候选方案对比**:

| 方案 | 改动 | 风险 | 决策 |
|------|------|------|------|
| A: busy_timeout + 重试 | 小 | 低 | ✅ 采用 |
| B: 单事务批量写入 | 中 | 中（事务膨胀） | 留待 054 |
| C: 写队列 | 大 | 高（新架构） | V3.0 不做 |

**实施方案 A**:
- `connection.py`: `busy_timeout = 30000`（30 秒）
- `_update_continuity_tracking()` / `_save_permanent_scenes()`: 最多 3 次重试，指数退避

### 3.3 settlement_extractor DB 访问重构（054）

**问题**: Agent 直接管理 DB 连接和事务，违反规则 53。

**重构路径**:
1. 所有子表写入方法支持可选 `conn` 参数（Repository 层）
2. `_apply_to_db()` 接收 `conn` 参数，不自行管理事务
3. 调用方（`save_settlement()`）统一创建连接、开启事务、提交/回滚

### 3.4 _helpers.py 直接 DB 访问清理（055）

**问题**: 绕过 Repository 执行原始 SQL。

**清理路径**:
- `load_open_threads()` → `SummaryRepository.list_recent()` + 调用方构建 OpenThread
- `load_chapter_goal()` → `ChapterGoalRepository.get_by_chapter()`

---

## 4. Layer 1 技术实现

### 4.1 文件拆分原则

- 不改函数签名或行为
- 不引入新抽象层
- 通过同级 `__init__.py` 暴露公共 API
- 主模块保留编排函数（`extract()` / `assemble()` / `revise()` / `audit()`）

### 4.2 拆分清单

| 文件 | 拆出模块 | 内容 |
|------|---------|------|
| `settlement_extractor.py` | `_validate.py` + `_apply.py` | 验证逻辑 + DB 写入 |
| `context_manager.py` | `_assemblers.py` | 各上下文组装函数 |
| `revision_handler.py` | `_patch_engine.py` + `_diff.py` | Patch 应用 + 模糊匹配 |
| `continuity_auditor.py` | `_scanners.py` + `_constraints.py` | 扫描 + 约束生成 |
| `creative_director.py` | `_brief_builder.py` | Brief 构造逻辑 |

---

## 5. Layer 2 技术实现

### 5.1 运行参数

- Seed: scifi, mode: webnovel_intense
- `--auto-confirm`: 不设 human gate
- 从 Ch1 到 Ch30（或从已有 Ch12 续到 Ch30）

### 5.2 监控数据模型

```python
class ChapterRunLog(BaseModel):
    chapter: int
    timestamp: str
    status: Literal["accepted", "paused", "failed"]
    metrics: dict[str, float | int | bool]
    warnings: list[str]
```

### 5.3 日志输出

每章生成后追加到 `docs/review/v30_layer2_runlog.jsonl`。

### 5.4 失败策略

| 失败类型 | 策略 |
|---------|------|
| database locked（重试 3 次失败） | 暂停，记录 |
| LLM 超时（重试 3 次失败） | 暂停，记录 |
| RevisionHandler 截断（< 50%） | 自动回退到 pre-revision 版本 accept |
| Settlement 部分失败 | 标记 needs_human_review，继续 |
| Continuity score < 6/10 | 记录警告，不暂停 |

---

## 6. Layer 3 技术实现

### 6.1 测试补充优先级

| 模块 | 新增测试数 | 策略 |
|------|-----------|------|
| `rag/*.py`（5 文件）| >=11 | Mock embedding，不加载真实模型 |
| `llm/client.py` | >=3 | Mock 超时 / rate limit |
| `llm/parsing.py` | >=4 | 畸形 JSON 输入 |
| `db/migrations.py` | >=1 | 幂等性 |

### 6.2 Agent 深审输出格式

沿用 V2 Pass 7-9 模板：
1. 发现摘要（优先级分布）
2. 逐项详述（位置 / 现象 / 根因 / 修复建议）
3. 已确认合规项

### 6.3 合规扫描工具

```bash
# 文件长度
find src/ -name "*.py" | xargs wc -l | sort -n

# 裸 except
rg "except\s+Exception" src/ tests/ evals/

# 类型标注（随机抽样）
# 手动检查 30 个函数签名

# print 残留
rg "print\(" src/ tests/ evals/
```

---

## 7. V3.0 明确不做

| 类别 | 不做 |
|------|------|
| 新功能 | 不新增 Genre、Mode、Agent、Workflow 节点 |
| 架构变更 | 不做知识图谱 / Narrative Memory Agent / 并行化原型 |
| 质量调优 | 不做 Prompt 优化、字数控制、钩子质量提升 |
| 产品化 | 不做 Web UI、TUI、多模型路由、多租户 |
| 评测 | 不做盲测、多 genre 交叉验证、人工金标 |
| 文档 | 只写开发者交接文档，不写用户文档 |

---

## 8. 时间估计

```
Layer 0: 2-3 天（含测试 + 验证复跑）
Layer 1: 1-2 天
Layer 2: ~36-60 小时生成（可夜间运行）+ 1 天分析
Layer 3: 2-3 天
总计（不含生成等待）: ~7-9 天
```

---

> **松烟入墨，字句成锋。V3.0 不是再搭一层楼，是把地基浇到能撑五十层。**
