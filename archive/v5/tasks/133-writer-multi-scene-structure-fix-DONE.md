# Task 133: Writer 多场景结构输出修复 — DONE（代码与测试）

> **状态**: 代码与测试已完成；Task 136 采集窗口已验证 Writer 1.2.0 多场景结构有效
> **日期**: 2026-06-27  
> **前置**: Task 121r、Task 129  

---

## 问题

Task 129 enforce 模式验证（`run-89d7a2d4`）发现所有章节 `scenes_count=1`，导致 readability 在 Ch3/Ch14/Ch15 跌至 0.2–0.3，并触发 quality gate streak AutoHalt。

---

## 修复内容

| 文件 | 改动 |
|------|------|
| `prompts/cards/writer/1.2.0.yaml` | 新增 Writer prompt 版本：强制 2-4 场景、每场景 ≥600 字、空行分隔、场景切换信号（时间/地点/人物/情绪/揭示） |
| `src/songyan/utils/scene_parser.py` | `parse_scenes()` 支持 `### Scene N` 标记拆分与 blank-line 回退；过滤 <80 字符的短块 |
| `src/songyan/models/review.py` | `ReviewIssue.fix_type` 增加 `"scene_split"` |
| `src/songyan/workflows/review_merger.py` | 单场景且字数 >1500 时生成 `fix_type="scene_split"` 的 major issue；短章（≤1500 字）不再生成场景结构 issue |
| `src/songyan/agents/revision_handler/__init__.py` | 新增 `_handle_scene_split()` 与 `_filter_scene_split_issues()`；`run_revision()` 优先处理 scene_split 再进入 patch 流程 |
| `src/songyan/agents/revision_handler/_segmented_revision.py` | 保留 `_handle_scene_shortage` 别名兼容 |
| `prompts/cards/writer/_manifest.yaml` | 保留 `default_version: "1.1.0"`，1.2.0 已注册但暂不默认启用，以保护 observe 基线 |

---

## 新增/更新测试

- `tests/test_scene_parser.py`（新增）
  - 显式标记优先、blank-line 回退、短块过滤、空内容
- `tests/test_writer.py`（更新）
- `tests/test_rule_auditor.py`（更新）
- `tests/test_review_merger.py`（更新）
  - 短单场景无 issue、长单场景生成 `scene_split` major issue
- `tests/test_revision_handler.py`（更新）
  - `TestSceneSplitStrategy` 验证 scene_split 触发 LLM 拆分路径

---

## 验证

- `ruff check src/ tests/` ✅
- 目标测试（scene_parser / writer / rule_auditor / review_merger / revision_handler）：201 passed ✅
- 全量 `pytest tests/`：`1892 passed, 2 skipped, 1 xfailed` ✅

---

## 实跑验收口径

- Task 136 通过临时切换 `prompts/cards/writer/_manifest.yaml` 的 `default_version` 为 `"1.2.0"` 完成 Ch1–Ch20 采集窗口验证，`scenes_count >= 2` 占比 100%。
- Writer 1.2.0 当前仍非默认版本；普通 pipeline / CLI 默认读取 Writer 1.1.0，不代表 Task 133 修复被覆盖。
- 后续 Task 137 或更大窗口复跑必须复用 Task 136 脚本，或使用等效显式 Writer 1.2.0 配置。

---

## 交付物

- 本 `-DONE.md` 文件
- Writer 1.2.0 prompt、scene parser、review_merger、RevisionHandler 相关代码改动
- `tests/test_scene_parser.py` 等新增/更新测试
