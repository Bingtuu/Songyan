# tasks/ — 任务工作循环

本目录是 **V1.0 写作助手**开工之后的任务队列。**先写任务文档，再写代码**；完成任务后归档，并同步 `docs/STATUS.md` 与 `docs/HANDOFF-mew.md`。

**M0 只读工作台步 1–4 已完成；M0 代码验收 PASS（`80f4107`）。tech-m1 已接受（Mew 拍板）。M1 步 1–5 已合入；M1 代码验收 PASS（`69d7ece`）。tech-m2 **草稿已起草**（待 owner 书面接受）。** 当前无 DOING 编码任务。下一闸门：owner 书面接受 tech-m2 后再开 M2 编码任务。归档：`done/200.md`（#28 / `1d8c0c0`）、`done/201.md`（#29 / `8f03453`）、`done/202.md`（#30 / `d5c2cc1`）、`done/203.md`（#31 / `48fa354`）、`done/204-m0-acceptance.md`（M0 验收 PASS）、`done/205-rejected迁移与过滤.md`（#35 / `1995181`）、`done/206-canon-edit.md`（#36 / `5a260a9`）、`done/207-confirm-dismiss.md`（#38 / `7c7ec43`）、`done/208-check.md`（#39 / `d3f127c`）、`done/209-w0-today-e2e.md`（#41 / `69d7ece`）、`done/210-m1-acceptance.md`（M1 验收 PASS）、`done/211-tech-m2草稿.md`（tech-m2 docs 草稿）。不要把 `docs/archive/` 里的旧 Task 001–019 或 V13–V15 抄进这里。

## 文件组织

```
tasks/
├── README.md            # 本规范
├── NNN-任务名.md         # 进行中/待办（平铺）
└── done/
    └── NNN-任务名.md     # 已完成（git mv 归档）
```

- 编号 `NNN` 三位数，从 **200** 起，顺序递增，**在本目录内永不复用**。
- 归档路线图和 `tests/test_<数字>_*.py` 里出现过的旧工程号（大约到 242）不是本队列。不要据此续写测试文件名，也不要把那些旧号当成这里的下一张任务。
- 任务名用简短中文动宾结构，如 `200-只读展示已确认事实.md`。
- 产品设计以 `docs/prd-v1.md` 为准。M0 的实现以 `docs/tech-m0.md` 为准；M1 的实现以已接受的 `docs/tech-m1.md` 为准，不得越出 PRD 对应里程碑。任务里发现设计要改，先改 PRD 再继续。

## 任务文档模板

```markdown
# NNN · 任务名

| 项 | 内容 |
|---|---|
| 状态 | TODO / DOING / DONE |
| 关联 | PRD 章节、工作流 W0–W6 |
| 预估 | 一个切片 |

## 目标
一句话说清要完成什么、为什么。

## 步骤
- [ ] 具体可执行的步骤

## 验收标准
- [ ] 可勾检的完成条件

## 完成总结（DONE 时填写）
做了什么 / 验收结果 / 遗留问题
```

## 工作循环

1. **拆任务**：从已接受的 PRD / 技术方案拆出任务。写 `NNN-任务名.md`（状态 TODO）。
2. **开工**：状态改 DOING。同一时刻原则上只有一个 DOING。`docs/HANDOFF-mew.md` 指向这一张。
3. **完工**：验收标准全部通过；填写完成总结；状态改 DONE；`git mv` 到 `tasks/done/`。
4. **同步**（同一次提交）：更新 `docs/STATUS.md` 与 `docs/HANDOFF-mew.md`。开发进度不进 README。
5. **测试**：新测试放在 `tests/<area>/test_<行为>.py`。禁止新增 `test_task###_*.py`。见 `tests/README.md`。

## 原则

- 没有任务文档就不开工。
- 验收过不了就不算 DONE。
- 做不完的任务不删，留 TODO 并写明阻塞。
- 标了 `[proposed]` 的命令，在对应任务落地之前，README 不得写成已经支持。
- **里程碑技术方案未经书面接受之前，不建该里程碑的编码任务。** tech-m1 已接受（M1 编码已完）。tech-m2 仅草稿：接受前不建 M2 编码任务；可有 docs 任务记录草稿本身。
