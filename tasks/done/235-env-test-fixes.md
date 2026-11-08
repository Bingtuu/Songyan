# 235 · 本机环境项修复批（191 编码 + llm_http_timeout 时序窗口）

| 项 | 内容 |
|---|---|
| 状态 | DONE（2026-11-08） |
| 关联 | STATUS「环境项」条目（2026-11-08 评估结论）；task 231 记录不修 #6 |
| 预估 | 小切片（两处测试侧修复，均不动 src 生产代码） |

## 背景

2026-11-08 评估结论：

1. `test_191_ch200_harness.py`：`_run_harness` 用 `text=True` 起子进程，父进程按本机 locale（cp936）解码子进程 UTF-8 中文输出 → `UnicodeDecodeError` + stdout 为 None。根因确定。
2. `test_llm_http_timeout`：负载敏感时序 flake。`litellm request_timeout` 生效（单独跑通过），但断言窗口 8s 在全量重载下偶发不够；服务端 hold 15s 仅比窗口大 7s，余量小。

## 范围

- [x] 191：`_run_harness` 显式 `encoding="utf-8"` + 子进程强制 `PYTHONUTF8=1` / `PYTHONIOENCODING=utf-8`（双侧固定，消除 locale 依赖；不带 PYTHONUTF8 也绿）
- [x] llm_http_timeout：断言窗口放宽（`_ASSERT_BOUND_SECONDS` 8→20），服务端 hold 同步放大（15→30，保持 hold > 窗口的判别性：超时机制真坏时仍等满 hold 才返回）
- [x] 两文件定向回归（不带 PYTHONUTF8 跑 191 证明修复生效）
- [x] 全量回归 → review → 归档 → 同步 STATUS 环境项条目 → 本地提交

## 验收标准

- [x] 不带 `PYTHONUTF8=1` 跑 `tests/test_191_ch200_harness.py` 全绿。
- [x] `test_llm_http_timeout` 单独跑绿；窗口/hold 常量按上述比例调整且注释说明判别性保留。
- [x] 全量 pytest 绿（允许零失败；若 llm_http_timeout 仍 flake 则记录观察）。
- [x] ruff / mypy 绿；不触碰 src/ 生产代码。

## 完成总结

**状态**：DONE（2026-11-08）。

**做了什么**：

1. `test_191_ch200_harness.py` `_run_harness`：父进程 `encoding="utf-8"` + 子进程 `env` 强制 `PYTHONUTF8=1`、`PYTHONIOENCODING=utf-8`。关键认知修正：只修父进程侧不够——Windows 下子进程 stdout=pipe 时按 locale（cp936）**编码**中文输出（0xa3 字节实证），必须双端固定。不带 PYTHONUTF8 全量 11/11 绿。
2. `test_llm_http_timeout.py`：`_ASSERT_BOUND_SECONDS` 8→20、`_SERVER_HOLD_SECONDS` 15→30；hold > 窗口的判别结构保留（真坏 → 等满 30s → 断言失败；生效 → 窗口内切断）。动机注释入档。
3. review 跟进 minor：补 `PYTHONIOENCODING=utf-8`（防外部预置 cp936 的边角）。

**review**：无 blocker / major；3 minor（1 已顺手修，2 为放宽窗口固有代价已注释，3 流程项）。

**验证**：两文件定向 12 passed（不带 PYTHONUTF8）；ruff / mypy 绿；全量回归终验（唯一与回归快照的差异 = 本文件内一行 env dict 追加，已同文件验证）。
