# Task 005: Genre Profile 系统 — 交接报告

## 完成状态

- [x] 代码实现
- [x] 测试通过：36/36（genres 专项）+ 158/158（全量）
- [x] ruff 检查通过：0 errors
- [x] 文档更新

---

## 改了哪些文件

### 新增文件（8 个）

| 文件 | 说明 |
|------|------|
| `genres/xuanhuan.json` | 玄幻完整题材配置（20 疲劳词、8 写手规则、6 审查焦点、12 审查维度） |
| `genres/urban.json` | 都市基础题材配置 |
| `genres/scifi.json` | 科幻基础题材配置 |
| `src/songyan/genres/__init__.py` | Genre 模块公共接口导出 |
| `src/songyan/genres/loader.py` | 加载器实现：load_genre_profile、list_genre_profiles、GenreProfileLoader、缓存管理 |
| `tests/genres/__init__.py` | 测试包标识 |
| `tests/genres/test_loader.py` | 36 个测试：配置校验、加载器行为、缓存、集成 |

---

## 如何验证

```bash
pytest tests/genres/ -v
# Expected: 36 passed

pytest tests/ -v
# Expected: 158 passed

ruff check src/songyan/genres/ tests/genres/
# Expected: All checks passed
```

---

## 关键实现决策

1. **JSON 为事实源**：所有题材规则写在 `genres/*.json`，不在代码中硬编码题材内容。
2. **路径解析基于包位置**：通过 `songyan.__file__` 定位仓库根目录，避免受当前工作目录影响。
3. **`set_genres_dir()` 支持测试覆盖**：测试可通过 `set_genres_dir(tmp_path)` 临时切换加载目录，无需 monkeypatch 私有变量。
4. **内存缓存**：`_CACHE` 在首次加载后复用，`clear_cache()` / `GenreProfileLoader.clear_cache()` 可重置。
5. **`active_audit_dimensions` 运行时校验**：加载时校验所有维度值必须属于 `ReviewCategory`，失败抛出 `GenreProfileError`。
6. **异常信息包含可用 genre**：`GenreProfileNotFoundError` 消息中自动列出当前扫描到的所有 genre_id，方便排查。
7. **未修改 `models/genre.py`**：现有 `GenreProfile` 模型已足够表达需求，无需改动。

---

## 已知限制

- 缓存为进程级内存缓存，多进程部署时需重新加载（V1.0 为单机 CLI，不构成问题）。
- `urban` / `scifi` 为基础配置，完整度低于 `xuanhuan`，后续 Task 如需扩展可直接编辑 JSON。

---

## 下一步依赖

- **Task 006（CreativeModeProfile 系统）** 可参考本 Task 的 JSON + Loader 模式。
- **Task 011（Writer Agent）** 可通过 `load_genre_profile(project.genre_id).writer_rules` 注入题材规则。
- **Task 012（RuleAuditor Agent）** 可通过 `.fatigue_words` 获取疲劳词列表。
- **Task 013（LLMAuditor Agent）** 可通过 `.reviewer_focus` + `.active_audit_dimensions` 注入审查焦点。
