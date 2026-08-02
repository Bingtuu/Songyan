# Task 211 - V11 backup / restore / schema ledger

> **阶段**: V11 开源可用化收尾
> **状态**: DONE
> **依赖**: Task 208 readiness audit；Task 210 doctor / preflight 增强
> **目标**: 建立项目资产生命周期能力，让外部技术用户能把 SQLite 事实库、项目配置摘要、schema 校验状态、运行摘要和关键日志索引打包备份，并可恢复到新 SQLite DB 路径。

---

## 任务目标

完成 V11 Task 211 backup / restore / schema ledger：

1. 提供可执行 `songyan backup` 命令，生成项目资产包。
2. 提供可执行 `songyan restore` 命令，从资产包恢复到新 SQLite DB 路径。
3. 资产包包含 SQLite 一致性快照、manifest、schema ledger、项目配置摘要、运行摘要和关键日志索引。
4. 明确 `export` 与 `backup` 的边界：`export` 只导出 accepted 正文；`backup` 保存可恢复 / 可迁移项目资产。
5. 默认不打包 `.env` 原文、API key 或其他敏感凭据。

---

## 范围

包含：

- `songyan backup --project-id <id> --output <dir-or-zip>`。
- `songyan restore --backup <zip> --database-url sqlite:///... [--force]`。
- 备份 manifest 格式版本、创建时间、project 元信息、DB 快照 hash、schema 校验结果、运行摘要、日志索引、敏感项排除声明。
- restore 后 schema 校验和输出下一步命令。
- CLI / service 测试和隔离目录命令证据。

不包含：

- 不扩张核心生成能力。
- 不新增核心 Agent / Workflow 节点。
- 不修改 prompt、CED、T9、five-gate、segment audit 或质量 hard gate。
- 不实现失败恢复完整分类；该能力路由到 Task 212。
- 不实现 run bundle / 脱敏诊断包；该能力路由到 Task 213。
- 不实现 profile validate / rollback / history；该能力路由到 Task 214。
- 不实现 wheel smoke、release checklist、CHANGELOG、CONTRIBUTING 或 issue templates；这些路由到 Task 215。

---

## 资产包设计

默认 zip 结构：

```text
songyan-backup-<project_id>-<timestamp>.zip
├── manifest.json
├── db/songyan.db
├── config/config.summary.json
├── runs/project_runs.json
└── logs/index.json
```

说明：

- `db/songyan.db` 是 SQLite backup API 生成的一致性快照。
- `manifest.json` 是资产包事实入口。
- `config/config.summary.json` 只记录项目配置和非敏感 runtime 摘要，不包含 `.env` 原文或 API key。
- `runs/project_runs.json` 保存项目级 run 摘要。
- `logs/index.json` 只保存关键日志相对路径、存在性和文件大小，不打包日志内容。

---

## 当前缺口

| 缺口 | 当前表现 | 本任务处理 |
|------|----------|------------|
| 无 backup 命令 | 用户只能手动复制 DB / logs | 新增 `songyan backup` |
| 无 restore 命令 | 用户无法迁移到新 DB 路径并校验 | 新增 `songyan restore` |
| 无 schema ledger | 无法判断资产包 DB schema 兼容性 | manifest 写入 schema 校验结果 |
| export / backup 边界不清 | export 容易被误当项目备份 | 文档明确 export 只导出正文 |
| 敏感配置保护不足 | `.env` 不应默认进入资产包 | 只写 config summary 和敏感项排除声明 |

---

## 验收标准

必须满足：

- `songyan backup --project-id <id> --output backups/` 生成 zip，exit 0。
- zip 包含 `manifest.json`、`db/songyan.db`、`config/config.summary.json`、`runs/project_runs.json`、`logs/index.json`。
- manifest 包含 schema status、missing tables、schema version、DB sha256、project summary、run/log summary。
- `songyan restore --backup <zip> --database-url sqlite:///restored.db` 恢复 DB，exit 0。
- restore 拒绝覆盖已有 DB，除非显式 `--force`。
- restore 后 `songyan doctor --json` 可校验 DB schema。
- restore 后 `songyan list-projects` 能看到备份项目。
- 资产包默认不包含 `.env` 或 API key。
- 文档明确 `export` 与 `backup` 边界。

验证命令：

```powershell
python -m pytest tests/cli -q
python -m pytest tests/test_177_export_service.py tests/test_178_resource_loading.py tests/test_211_backup_restore.py -q
ruff check src/ tests/
python -m pytest tests/ -q
```

---

## 交付物

- `tasks/211-v11-backup-restore-schema-ledger.md`
- `tasks/211-v11-backup-restore-schema-ledger-DONE.md`
- `docs/reports/211-backup-restore-evidence.md`
- 相关代码和测试
- `README.md`、`docs/quickstart.md`、`docs/troubleshooting.md`
- `docs/STATUS.md`、`docs/INDEX.md`、`tasks/V11-README.md`
