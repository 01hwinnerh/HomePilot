# HomePilot 技术发现与决策记录

## 环境基线（2026-08-04）

| 项目 | 当前结果 | 结论 |
|---|---|---|
| uv | `0.11.19` | 可用 |
| Python | 用户已执行 `uv python install 3.12` | 可用于项目隔离环境 |
| Node.js | `24.14.1` | 可用；需在前端依赖矩阵中确认工具链支持 |
| pnpm | `11.9.0` | 可用 |
| Docker Compose | `v5.1.3` | 用户已启动 Docker Desktop；后续由用户手动执行 Docker 命令 |
| Git | 仓库已初始化、尚无提交 | 所有 Git 命令由用户手动执行 |

## 已确认技术决策

- 项目名称：`HomePilot`；展示名为 **HomePilot — Your AI-Powered Home Marketplace**。
- 后端：Python 3.12、FastAPI、Pydantic v2、SQLAlchemy 2、Alembic、MySQL 8.4。
- 前端：React、TypeScript、Vite、TanStack Query、Zustand、Tailwind；控制台使用 Ant Design。
- 交易真源：同一 MySQL 中的本地 ACID 事务；Redis 仅用于缓存、限流、Celery Broker 与 Agent Checkpoint。
- Agent：LangChain、LangGraph、LangSmith；DeepSeek OpenAI-compatible API，默认 `deepseek-v4-flash`。
- RAG：Qdrant、bge-m3、reranker、MinIO；本地 Embedding/Reranker 与远程 SiliconFlow Provider 通过配置切换。
- 密钥：全部来自未提交的 `.env`；只提交 `.env.example`。

## 待确认的兼容性事项

- 依赖策略已确认：采用兼容的稳定大版本范围，并由 `uv.lock`、`pnpm-lock.yaml` 固定实际解析版本。
- Docker 对 MySQL 固定 `8.4`、Redis 固定 `7.4`；Qdrant 与 MinIO 在用户首次成功拉取后记录精确 tag/digest。
- Node 24 与 Vite/Vitest/ESLint 的实际兼容性将在用户执行 `pnpm install` 后通过锁文件和测试结果确认；若解析失败则停止并向用户提供替代版本。

## Git 协作规则

- 助手不执行任何 Git 命令；用户在指定目录手动执行。
- 每个可独立说明的模块完成后，必须先创建一次语义清晰的 Conventional Commit，再创建或更新对应 GitHub PR。
- 不将无关功能混入同一次 Commit；进入下一个模块前，先提醒用户完成上一个模块的 Commit/PR。

## 错误记录

| 时间 | 现象 | 处理 |
|---|---|---|
| 2026-08-04 | 自动执行 `uv python install 3.12` 时权限审批代理返回 503 | 用户改为手动执行，已完成 |
