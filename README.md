# HomePilot

> **继续开发前请先阅读 [HANDOFF.md](HANDOFF.md)**。它是当前项目状态、协作约束和下一步工作的根目录交接入口。

面向多商家精品家居场景的电商与 Agent 客服作品集项目。项目采用 FastAPI 模块化单体承载交易和售后业务，以 LangGraph 编排具备 RAG、订单查询、售后草稿和人工接管能力的可信客服 Agent。

当前状态：按已审核设计进行增量实现。架构基线见 `docs/superpowers/specs/2026-08-04-multi-merchant-home-rag-agent-design.md`，任务追踪见 `docs/superpowers/plans/2026-08-04-multi-merchant-home-rag-agent-implementation.md`。

## 本地身份演示数据

身份模块提供仅用于本地开发的可重复演示数据：一个平台管理员、两个独立商家及各自的 OWNER 成员。先在未提交的项目根目录 `.env` 设置非空 `DEMO_SEED_PASSWORD`，再在 `D:\Project\Codex\vibe-coding\backend` 执行：

```powershell
uv run python ..\scripts\seed_identity_demo_data.py
```

命令只输出成功或安全拒绝结果，绝不显示密码。它可重复执行；若同名演示标识已经指向不符合预期的记录，则会停止且不覆盖已有业务数据。具体账号和前后端联调步骤见 [backend/README.md](backend/README.md)。
