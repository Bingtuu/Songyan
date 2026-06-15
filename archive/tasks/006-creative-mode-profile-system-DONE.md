# Task 006: CreativeModeProfile 系统 — 交接报告

## 完成状态

- [x] 代码实现
- [x] 测试通过：38/38（creative_modes 专项）+ 196/196（全量）
- [x] ruff 检查通过：0 errors
- [x] 文档更新

---

## 改了哪些文件

### 新增文件（9 个）

| 文件 | 说明 |
|------|------|
| `creative_modes/webnovel.json` | 网文模式完整配置（5 阶段全 Agent、12 维度权重、standard 修订策略） |
| `creative_modes/literary.json` | 严肃文学模式基础配置（minimal 修订、侧重文学性维度） |
| `creative_modes/hybrid.json` | 混合模式基础配置（selective 修订、均衡权重） |
| `src/songyan/creative_modes/__init__.py` | CreativeMode 模块公共接口导出 |
| `src/songyan/creative_modes/registry.py` | 注册表实现：load_creative_mode_profile、list_creative_mode_profiles、CreativeModeProfileLoader、缓存管理 |
| `tests/creative_modes/__init__.py` | 测试包标识 |
| `tests/creative_modes/test_registry.py` | 38 个测试：配置校验、加载器行为、缓存、集成 |

### 修改文件（1 个）

| 文件 | 变更 |
|------|------|
| `docs/STATUS.md` | 更新 Task 006 完成状态 |

---

## 如何验证

```bash
pytest tests/creative_modes/ -v
# Expected: 38 passed

pytest tests/ -v
# Expected: 196 passed

ruff check src/songyan/creative_modes/ tests/creative_modes/
# Expected: All checks passed
```

---

## 关键实现决策

1. **JSON 为事实源**：所有创作模式规则写在 `creative_modes/*.json`，不在代码中硬编码模式内容。
2. **路径解析基于包位置**：通过 `songyan.__file__` 定位仓库根目录，避免受当前工作目录影响。
3. **`set_modes_dir()` 支持测试覆盖**：测试可通过 `set_modes_dir(tmp_path)` 临时切换加载目录，无需 monkeypatch 私有变量。
4. **内存缓存**：`_CACHE` 在首次加载后复用，`clear_cache()` / `CreativeModeProfileLoader.clear_cache()` 可重置。
5. **`active_audit_dimensions` 运行时校验**：加载时校验所有维度值必须属于 `ReviewCategory`，失败抛出 `CreativeModeProfileError`。
6. **异常信息包含可用 mode**：`CreativeModeProfileNotFoundError` 消息中自动列出当前扫描到的所有 mode_id，方便排查。
7. **未修改 `models/creative_mode.py`**：现有 `CreativeModeProfile` 模型已足够表达需求，无需改动。
8. **与 Task 005 完全对称**：`creative_modes/` 与 `genres/`、 `registry.py` 与 `loader.py` 保持一致的代码结构，降低维护成本。

---

## 已知限制

- 缓存为进程级内存缓存，多进程部署时需重新加载（V1.0 为单机 CLI，不构成问题）。
- `literary` / `hybrid` 为基础配置，完整度低于 `webnovel`，后续 Task 如需扩展可直接编辑 JSON。

---

## 下一步依赖

- **Task 007（CLI 创建项目）** 可在交互向导中列出可用创作模式（`list_creative_mode_profiles()`），让用户选择 `mode_id`。
- **Task 008（GoalPlanner Agent）** 需遵守 `CreativeModeProfile` 的约束（如上下文裁剪策略）。
- **Task 011（Writer Agent）** 可通过 `load_creative_mode_profile(project.mode_id).enabled_agents` 了解当前模式启用哪些 Agent。
- **Task 012（RuleAuditor Agent）** 可通过 `.tolerance` 获取容错阈值（如 `max_ai_tells`、`max_fatigue_words`）。
- **Task 013（LLMAuditor Agent）** 可通过 `.audit_weights` 获取各维度权重，通过 `.active_audit_dimensions` 获取启用的审查维度。
