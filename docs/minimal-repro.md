# Minimal Reproduction Guide

> 提交 Songyan 问题前，请尽量按本指南准备最小复现。目标是让维护者能在不接触你的私密书稿和密钥的情况下复现问题。

## 优先使用 run bundle

如果问题发生在一次 `songyan run` 中，并且你有 `run_id`：

```powershell
songyan bundle-run --run-id <run_id> --output bundles/
```

提交生成的 zip。bundle 默认包含：

- `bundle.json`
- `bundle.md`
- `logs/index.json`

bundle 默认不包含：

- `.env`
- API key / token / authorization header
- 日志正文
- 书稿正文
- 未脱敏绝对路径

## 必须提供的信息

请提供：

- Songyan 版本或 commit。
- 操作系统和 Python 版本。
- 安装方式：editable install / wheel install。
- 运行目录是否为仓库根目录。
- 执行的完整命令。
- `songyan doctor --json --init-db` 输出。
- 失败命令的 exit code。
- `project_id` 和 `run_id`，如果适用。
- run bundle zip，或说明为什么无法生成。

## 不要提交的信息

不要提交：

- `.env` 原文。
- `LLM_API_KEY`、token、cookie、authorization header。
- 完整私密书稿。
- 未脱敏的本地绝对路径。
- 原始数据库文件，除非维护者明确要求且你已确认不含私密内容。

## 常见最小复现命令

环境与资源问题：

```powershell
songyan doctor --json --init-db
```

项目创建问题：

```powershell
songyan create-project --template scifi
songyan list-projects
```

运行失败：

```powershell
songyan run --project-id <project_id> --chapters 1-3 --auto-confirm
songyan report --run-id <run_id>
songyan bundle-run --run-id <run_id> --output bundles/
```

导出问题：

```powershell
songyan export --project-id <project_id> --chapters 1-3 --format md --output exports/
```

备份恢复问题：

```powershell
songyan backup --project-id <project_id> --output backups/
songyan restore --backup <zip> --database-url sqlite:///restored.db
```

Profile 配置问题：

```powershell
songyan profile validate --genre <genre> --json
songyan profile history --genre <genre>
```

## 好的复现描述示例

```text
版本: 2.0.0 / commit <hash>
OS: Windows 11
Python: 3.11.9
安装方式: wheel
cwd: C:\Users\me\songyan-smoke，不是仓库根目录
命令: songyan create-project --template scifi
结果: exit code 1
期望: 成功创建项目并输出 project_id
附件: doctor.json、bundle.zip（若有 run_id）
```

## 维护者可能要求的补充材料

- `logs/reports/report-<run_id>.md`
- `logs/chapter_runs/<run_id>.jsonl` 的脱敏片段
- 失败命令的 stdout / stderr
- `songyan profile validate --genre <genre> --json`
- wheel smoke 输出
