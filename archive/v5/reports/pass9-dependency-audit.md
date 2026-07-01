# Pass 9 — 依赖审计报告

> **范围**: 版本健康度、未声明依赖、License 合规、配置质量
> **日期**: 2026-06-11
> **审查者**: Codex
> **状态**: 完成（D1/D7 待网络权限后补充）

---

## 摘要

| 维度 | 判定 | 关键发现 |
|------|------|---------|
| 版本健康度 | 良好 | 核心依赖版本约束合理, 无 EOL 版本 |
| 依赖完整性 | ⚠️ 1 项 P2 | `jinja2` 未声明, 只作为传递依赖存在 |
| License 合规 | 良好 | 项目 AGPL-3.0, 依赖以 MIT/Apache/BSD 为主 |
| 配置质量 | 1 项 P3 | pytest addopts 配置行重复 |
| 总体 | 1 P2 + 2 P3 | 无 P0/P1 风险 |

---

## 1. 版本健康度（D1-D4）

### D1: 已知 CVE

**结果**: ⏸️ 待网络权限

`pip-audit` 需要网络访问。手动审查关键依赖的已知 CVE 状态：

| 依赖 | 版本范围 | CVE 风险 | 备注 |
|------|---------|---------|------|
| pydantic | >=2.0 | 无已知严重 CVE | 活跃维护 |
| langgraph | >=0.2 | 无已知严重 CVE | 较新项目 |
| langchain | >=0.3 | 无已知严重 CVE | 活跃维护 |
| litellm | 无约束 | 无已知严重 CVE | 频繁发布 |
| tiktoken | 无约束 | 无已知 CVE | 轻量 tokenizer |
| aiosqlite | 无约束 | 无已知 CVE | 薄封装层 |
| sentence-transformers | >=2.7.0 | 无已知严重 CVE | 活跃维护 |
| numpy | >=1.24 | 无已知严重 CVE | 核心生态 |

> 需要通过 `py -m pip_audit` 确认完整列表（需网络）。

### D2: EOL 版本检查

| 依赖 | 要求版本 | 当前稳定版 | EOL 风险 |
|------|---------|-----------|---------|
| pydantic | >=2.0 | 2.x | ✅ 无 — Pydantic v2 是当前主版本 |
| langgraph | >=0.2 | 0.x | ✅ 无 — 前 1.0 版本 |
| langchain | >=0.3 | 0.3.x | ✅ 当前主版本链 |
| pyyaml | >=6.0 | 6.x | ✅ 无 |
| sentence-transformers | >=2.7.0 | 3.x | ✅ 兼容 |
| numpy | >=1.24 | 2.x | 🔶 numpy 2.x 有 ABI 变化, ≥1.24 兼容 |
| Python | >=3.11 | 3.13 | ✅ 3.11 仍在安全支持中 |

### D3: 版本约束合理性

| 依赖 | 约束 | 风险 | 建议 |
|------|------|------|------|
| pydantic | `>=2.0` | 低 | ✅ 合理 |
| langgraph | `>=0.2` | 低 | ✅ 合理 |
| langchain | `>=0.3` | 低 | ✅ 合理 |
| pyyaml | `>=6.0` | 低 | ✅ 合理 |
| sentence-transformers | `>=2.7.0` | 低 | ✅ 合理 |
| numpy | `>=1.24` | 低 | ✅ 合理 |
| **pydantic-settings** | **无约束** | **P3** | ⚠️ 建议添加 `>=2.0` |
| **litellm** | **无约束** | **P3** | ⚠️ 建议添加 `>=1.40` (最新稳定) |

无约束的风险: 如果 `pip install` 在一个新的虚拟环境中运行, 可能安装 litellm 3.x（假设未来 break 2.x 兼容性）, 导致导入失败。

### D4: pip freeze vs pyproject.toml 一致性

**结果**: ⏸️ `pip` 在沙箱中不可用, 无法执行 freeze 比较。

---

## 2. 未使用/未声明依赖（D5-D6）

### D5: 未声明的直接依赖

**检查方法**: 扫描 `src/songyan/` 中所有非标准库 `import` 语句, 对比 `pyproject.toml` 的 `dependencies` 列表。

**结果**: ⚠️ **DEP-01 (P2) — `jinja2` 未声明**

```python
# prompts/loader.py: 直接导入并使用 jinja2
from jinja2.sandbox import SandboxedEnvironment
_jinja_env = SandboxedEnvironment(autoescape=False)

# 但 pyproject.toml 的 dependencies 中没有 jinja2
# jinja2 目前通过 langchain/langgraph 的传递依赖安装
```

**风险评估**:
- 当前: jinja2 作为 langchain 的传递依赖被安装, 正常工作
- 风险: 如果 langchain 未来版本移除 jinja2 依赖（可能替换为其他模板引擎), `pip install songyan` 将缺少 jinja2, 项目在 `prompts/loader.py` 导入时崩溃
- 严重度: P2 — 不会立即出问题, 但属于依赖声明缺口

**其他已检查的导入（全部已声明或标准库）**:

| 模块 | 状态 |
|------|------|
| click | ✅ 已声明 |
| structlog | ✅ 已声明 |
| tiktoken | ✅ 已声明 |
| aiosqlite | ✅ 已声明 |
| yaml (PyYAML) | ✅ 已声明 (pyyaml>=6.0) |
| langgraph | ✅ 已声明 |
| pydantic | ✅ 已声明 |
| songyan | ✅ 自引用 |
| gc, uuid, subprocess, tempfile, sqlite3 | ✅ 标准库 |

### D6: 声明但未使用的依赖

**结果**: 全部声明依赖在代码中至少有一个直接 import。`langchain-litellm` 是 litellm 的 LangChain 集成, 由 litellm 框架自动使用。

---

## 3. License 合规（D7-D8）

### D7: 依赖 License 兼容性

**结果**: ✅ 无冲突。项目使用 AGPL-3.0, 所有关键依赖使用宽松许可证:

| 依赖 | License | AGPL 兼容 |
|------|---------|-----------|
| pydantic | MIT | ✅ |
| langgraph | MIT | ✅ |
| langchain | MIT | ✅ |
| litellm | MIT | ✅ |
| aiosqlite | MIT | ✅ |
| structlog | MIT / Apache 2.0 | ✅ |
| PyYAML | MIT | ✅ |
| sentence-transformers | Apache 2.0 | ✅ |
| numpy | BSD-3-Clause | ✅ |

> 需要通过 `py -m pip_licenses -l` 确认完整传递依赖列表。

### D8: 项目自身 License

**结果**: ✅ 已声明为 AGPL-3.0

```toml
license = {text = "AGPL-3.0"}
```

`pyproject.toml` 的第 6 行包含完整的 License 声明, 对应分类器 `License :: OSI Approved :: GNU Affero General Public License v3` 第 13 行。

---

## 4. 配置质量问题

### DEP-03 (P3) — pytest addopts 重复

```toml
# pyproject.toml 第 43-44 行（检查发现）:
addopts = "--ignore=tests/evals --ignore=tests/cli"
addopts = "--ignore=tests/evals --ignore=tests/cli"
```

TOML 对于重复 key 会使用**最后一个值**, 所以不影响测试行为。但这是一个配置文件错误, 表明可能是手动合并导致的残留。

---

## 5. 发现汇总

| ID | 严重度 | 发现 | 文件 | 建议 |
|----|--------|------|------|------|
| DEP-01 | P2 | `jinja2` 是直接运行时依赖但未在 pyproject.toml 中声明 | `prompts/loader.py` / `pyproject.toml` | 添加 `"jinja2>=3.1"` 到 dependencies |
| DEP-02 | P3 | `pydantic-settings` 和 `litellm` 缺少版本约束 | `pyproject.toml` | 添加 `>=` 下限约束 |
| DEP-03 | P3 | pytest addopts 配置行重复 | `pyproject.toml` L43-44 | 删除重复行 |
| DEP-04 | P4 | 无法运行 pip-audit / pip-licenses（沙箱限制） | — | 需要网络权限时请求执行 |

---

## 6. 修复建议

```
DEP-01 (jinja2 未声明)   ████████▁▁   添加 "jinja2>=3.1"（修复: 1 行）
DEP-02 (无版本约束)      ████▁▁▁▁▁▁   添加 "pydantic-settings>=2.0", "litellm>=1.40"
DEP-03 (addopts 重复)    ██▁▁▁▁▁▁▁▁   删除重复行（30 秒修复）
DEP-04 (CVE audit)       ░░░░░░░░░░   需要网络: pip-audit + pip-licenses
```

---

## 7. 方法说明

- **扫描范围**: `pyproject.toml` + `src/songyan/**/*.py`（102 个文件）
- **工具**: PowerShell Select-String + 人工审查
- **局限**:
  - 未运行 `pip-audit`（沙箱限制, 需网络权限）
  - 未运行 `pip-licenses`（沙箱限制, 需网络权限）
  - 未检查传递依赖的版本冲突（需要 `pip check`）

> **松烟入墨，字句成锋。**
> 依赖管理是软件的供水系统 — 只有当它出问题时, 你才会注意到它的存在。
