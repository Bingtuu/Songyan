# Task 178: wheel 打包与资源加载修复

> **阶段**: V9.2 交付与发布
> **类型**: 基础设施（打包正确性，V9.2 连锁影响最大单项）
> **优先级**: P0（V9-README 审计 P0 ④：`pip install .` 成 wheel 即坏——`prompts/`、`genres/`、`creative_modes/`、`project_templates/` 等运行资源不是 package data）
> **依赖**: 引用面扫描已完成（2026-07-19，见本文"引用面事实"节）；177 完成（export 命令需在安装后可用）
> **状态**: ◻ 规划中
> **来源**: V9 生产就绪度审计；`tasks/V9-README.md` Task 178 行（2026-07-18 用户评审定稿版）

---

## 引用面事实（2026-07-19 扫描结论，设计依据）

- **8 处根目录相对路径解析点**（全在 `src/`）：`prompts/loader.py:42`（cards）、`literary_optimization/plugin_loader.py:10`（plugins，无注入口）、`genres/loader.py:22`、`creative_modes/registry.py:22-24`、`project_templates/loader.py:27-29`（templates）与 `:30-32`（**evals/seeds 连带，别漏**）、`agents/goal_planner.py:24` 与 `agents/creative_director/__init__.py:59`（**死代码 PROMPT_PATH，删除**）。
- **5.5 个资源目录**（全部纯数据，无 .py）：`prompts/cards/`、`prompts/literary_plugins/`、`genres/`、`creative_modes/`、`project_templates/`、`evals/seeds/`（模板 seed 兼容层，`loader.py:65-77,105-110` 读）。
- **链式依赖**：模板加载校验 genre/mode 存在性（`project_templates/loader.py:170-187`）→ project_templates 传递依赖 genres/ + creative_modes/。
- **运行时写入**：`scripts/run_170j_experiment.py:88` / `run_170k:91` / `run_170l:97` 把临时 mode JSON 写进 `creative_modes/` 再 unlink（**必须改**）；`scripts/inject_172d_genre_lexicons.py:77-83` 覆写 `genres/*.json`（数据维护脚本，改路径即可）。
- **注入口必须保留**：`set_genres_dir`/`set_modes_dir`/`get_prompt_loader(cards_dir=...)`/`ProjectTemplateLoader(templates_dir=...)`——tests 与 README:405 承诺依赖。
- **pyproject 现状**：`[tool.setuptools.packages.find] where=["src","."] include=["songyan*","evals*"]`，**零 package-data 声明**。
- **测试锚点**：`tests/test_172cs_wuxia_health_calibration.py:19,55-58`（唯一 ROOT 硬编码直读真实卡）；`tests/genres/*`、`tests/creative_modes/test_registry.py` 的 fixture 回指 `_GENRES_DIR`/`_MODES_DIR` 模块常量；`tests/test_project_template_loader.py:246` 默认 loader 全量加载（链式依赖 4 目录）；`tests/test_prompt_loader.py` 全文默认目录。

## 目标

1. 全部运行资源纳入 wheel：`prompts/cards`、`prompts/literary_plugins`、`genres`、`creative_modes`、`project_templates`、`evals/seeds`。
2. 干净 venv `pip install .` 后，**非仓库 cwd** 跑通：资源枚举（7 genre + 4 mode + 全部模板 + prompt cards + literary plugins 可加载）、`create-project --template scifi`、scifi 1-3 章实跑生成。
3. 测试注入口全部保留可用；全量测试绿、ruff 绿；scifi `--end 10` 实跑回归（生成行为逐值不变）。

---

## 技术方案（选定：目录入包 + importlib.resources 统一解析）

**决策**：把资源目录 `git mv` 进持有其 loader 的包内（不改 public API），加载点统一改为 `importlib.resources.files()` 解析；注入口（`set_*_dir`/构造参数）语义不变——注入时跳过 resources 直接用给定路径。

| 源（仓库根） | 目标（包内） | 解析点修改 |
|---|---|---|
| `prompts/cards/` | `src/songyan/prompts/cards/` | `prompts/loader.py:42` `_CARDS_DIR` → `files("songyan.prompts") / "cards"` |
| `prompts/literary_plugins/` | `src/songyan/prompts/literary_plugins/` | `plugin_loader.py:10` `PLUGINS_DIR` → `files("songyan.prompts") / "literary_plugins"`；**补注入口**（函数参数或保持模块变量可 monkeypatch） |
| `genres/*.json` | `src/songyan/genres/data/*.json` | `genres/loader.py:22` → `files("songyan.genres") / "data"` |
| `creative_modes/*.json` | `src/songyan/creative_modes/data/*.json` | `creative_modes/registry.py:22-24` 同构 |
| `project_templates/<dirs>` + `_schema.json` | `src/songyan/project_templates/data/` | `project_templates/loader.py:27-29` 同构 |
| `evals/seeds/` | `src/songyan/project_templates/seeds/`（并入模板包） | `project_templates/loader.py:30-32` → `files("songyan.project_templates") / "seeds"` |

（`prompts/cards` 与 `prompts/literary_plugins` 本身就是数据子目录，直接迁入；genres/creative_modes/project_templates 包内已有 .py，数据放 `data/` 子目录隔离。）

**pyproject.toml**：

```toml
[tool.setuptools.package-data]
songyan = ["**/*.yaml", "**/*.json", "**/*.md"]
```

**迁移纪律**：用 `git mv` 保历史；先改 pyproject + loader 解析点 + 迁移目录，再跑全量测试；测试锚点 4 类按扫描表逐个核对（fixture 回指模块常量的随模块新值自动正确；`test_172cs` 的 ROOT 直读改为包内路径或注入）。

**scripts 改造**：
- `run_170j_experiment.py` / `run_170k` / `run_170l`：临时 mode JSON 改写 `tempfile.TemporaryDirectory()`，用 `set_modes_dir()` 指向"包内默认 + 临时覆盖"的合成视图（或加载后注入 mode 对象，取改动小者）；
- `inject_172d_genre_lexicons.py`、`audit_172a1_genre_tokens.py`：ROOT 路径更新为包内 data 路径（它们是仓库数据维护/审计脚本，写/读仓库副本合法）；
- 删除两处死代码 `PROMPT_PATH`（`goal_planner.py:24`、`creative_director/__init__.py:59`）。

**文档同步**（最后做）：README 项目结构图与「三层配置」节、AGENTS.md 相关路径提示、`docs/INDEX.md`、README:405 注入口承诺核对。

### TDD 测试（新建 `tests/test_178_resource_loading.py`，不进 tests/cli）

- `importlib.resources.files("songyan.genres") / "data"` 可枚举 7 个 genre json；`files("songyan.creative_modes") / "data"` 4 个 mode；`files("songyan.project_templates") / "data"` 模板目录与 `_schema.json`；cards `_manifest.yaml` 可读；literary_plugins 4 个策略目录存在；
- 各 loader 默认路径下加载成功（genre/mode/template/card/plugin 各一）；
- 注入口回归：`set_genres_dir(tmp_path)`、`get_prompt_loader(cards_dir=tmp_path)`、`ProjectTemplateLoader(templates_dir=tmp_path)` 仍生效（模拟包外目录）；
- plugin_loader 新注入口可注入临时插件目录；
- `test_172cs` 直读路径改后仍读真实卡。

## 验证

### 回归命令

```powershell
python -m pytest tests/test_178_resource_loading.py -q
python -m pytest tests/ -q
ruff check src/ tests/
python scripts/run_172a7_genre_validation.py --templates scifi --end 10   # 生成行为回归
```

### wheel 验收（干净环境，分两步）

1. **构建与安装**：`python -m build`（或 `pip wheel .`）→ 干净 venv `pip install <wheel>` → 检查 site-packages 内含 `songyan/prompts/cards/...`、`songyan/genres/data/...`。
2. **非仓库 cwd 跑通**（`cd %TEMP%\178_accept`）：资源枚举脚本（7 genre/4 mode/全模板/cards/plugins 加载清单打印）→ `songyan create-project --template scifi`（交互输入喂默认值）→ `SONGYAN_RUN_COST_BUDGET=2 songyan run --chapters 1-3 --auto-confirm`（实跑 1-3 章 accepted；成本遥测落库正常——与 175 联动）。

### 验收判据

- wheel 内资源完整（上述检查点全部命中）；非仓库 cwd 全部跑通；
- 全量测试绿、ruff 绿；scifi `--end 10` 10/10、Ch1 budget=8250（生成行为逐值不变）；
- 注入口测试全绿；旧根目录（`prompts/`、`genres/` 等）在仓库中已移除，无残留引用（`grep -rn "prompts/cards" src/ tests/ scripts/` 只剩包内新路径）。

## 出口标准

1. 6 个资源目录入包 + `importlib.resources` 统一解析 + package-data 声明落地；
2. wheel 验收与非仓库 cwd 实跑证据落盘；scifi `--end 10` 回归通过；
3. scripts（170j/k/l、inject_172d、audit_172a1）改造完成；死代码 PROMPT_PATH 删除；
4. 文档同步；本 Task 执行记录补录本文档，V9-README 178 行翻正。

## 撞墙路由

| 风险 | 触发信号 | 处理 |
|---|---|---|
| `git mv` 后引用遗漏 | 全量测试红 / `grep` 检出旧根路径 | 按扫描表 8 处解析点 + 4 类测试锚点 + 7 个脚本逐项核对；禁用"看起来对了就提交" |
| editable install 与 wheel 行为分叉 | dev 下绿、wheel 下资源缺失 | 验收以 wheel 安装为准；`importlib.resources.files()` 两种安装形态均返回真实路径，若 editable 失效检查 setuptools editable 模式（建议 `pip install -e . --config-settings editable_mode=compat` 兜底） |
| 170j/k/l 改造语义变化 | 三个实验脚本跑不通 | 临时 mode 写 TemporaryDirectory + `set_modes_dir` 覆盖；保持实验结果与历史可比 |
| 链式依赖断 | 模板加载报 genre/mode 不存在 | project_templates/data 与 genres/data、creative_modes/data 三处同批迁移同批验证（`test_all_listed_templates_load` 是第一道闸） |
| 生成行为漂移 | scifi end10 非 10/10 或 Ch1 budget ≠ 8250 | 回滚；路径解析改动不应触达生成逻辑——漂移说明有意外耦合，逐一对照 |

## Out of Scope

- `evals/` 顶层包本身的去留/瘦身（dev 工具，seeds 迁走后无资源依赖，维持 `include` 现状）；
- 版本号 bump 机制与发布流程（归 Task 181 CI 一并设计）；
- `project_templates/_schema.json` 的加载时校验启用（184 的 schema 任务）；
- 文档面历史引用改写（`docs/architecture/*` 等历史文档保持原样）。
