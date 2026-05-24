# Songyan（松烟）— 多 Agent 中文小说写作系统

> **松烟入墨，字句成锋。**
>
> 面向长篇中文小说创作的多 Agent AI 生产系统，基于 LangGraph 多 Agent 协作架构。

## 项目状态

V1.0 开发中 — 单章闭环验证

## 快速开始

```bash
# 安装
pip install -e ".[dev]"

# 配置环境变量
cp .env.example .env
# 编辑 .env，填入 LLM_API_KEY

# 运行
songyan --help
```

## 开发文档

- `CLAUDE.md` — 开发代理指令与不可违背规则
- `system_prompt/development-tech-plan-v2.md` — V2 技术方案
- `system_prompt/ai-collaboration-guide.md` — 多 AI 协作规范
- `docs/INDEX.md` — 文档索引

## 许可证

AGPL-3.0
