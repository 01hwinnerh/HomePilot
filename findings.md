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

## 已验证的后端依赖解析（2026-08-04）

- `uv sync --all-groups` 成功解析并安装 101 个包，已生成 `backend/uv.lock`。
- Agent 关键组合：LangChain `1.3.14`、LangGraph `1.2.10`、langgraph-checkpoint-redis `0.5.1`、LangSmith `0.10.15`。
- 数据层关键组合：FastAPI `0.141.1`、SQLAlchemy `2.0.51`、Alembic `1.18.5`、Celery `5.6.3`、Redis Client `5.3.1`。
- uv 对硬链接失败已回退为文件复制，仅影响安装速度，不影响环境内容。
- FastAPI 健康探针测试已通过；Starlette 对现有 `httpx` TestClient 发出上游废弃预警，当前不影响功能，后续跟随 FastAPI 兼容组合升级。
- Ruff `0.16.1` 已通过全量后端静态检查。

## 前端依赖安全决策

- pnpm 11 默认阻止依赖的安装脚本；Vite 依赖的 `esbuild` 需要执行受信任的平台二进制准备脚本。
- `frontend/pnpm-workspace.yaml` 仅将 `esbuild` 加入 `onlyBuiltDependencies` 白名单，不开放其他依赖执行安装脚本。
- Node `24.14.1` + pnpm `11.9.0` 已通过两个 React 19/Vite 应用的生产构建、Vitest 和 ESLint 验证。

## Docker 基础设施验证（2026-08-04）

- MySQL `8.4` 容器为 healthy，应用用户可登录并执行 `SELECT 1`。
- Redis `7.4-alpine` 容器为 healthy，`redis-cli ping` 返回 `PONG`。
- Qdrant 容器运行正常，`/healthz` 返回 HTTP 200。
- MinIO 容器运行正常，`/minio/health/live` 返回 HTTP 200。
- Qdrant 已锁定为 `qdrant/qdrant@sha256:057ee3a8da769fe7310dd3537b4dc7583bf87a95ce8ac43c0af5a46bc580d1fc`。
- MinIO 已锁定为 `minio/minio@sha256:14cea493d9a34af32f524e538b8346cf79f3321eff8e708c1e2960462bd8936e`。

## Git 协作规则

- 助手不执行任何 Git 命令；用户在指定目录手动执行。
- 每个可独立说明的模块完成后，必须先创建一次语义清晰的 Conventional Commit，再创建或更新对应 GitHub PR。
- 不将无关功能混入同一次 Commit；进入下一个模块前，先提醒用户完成上一个模块的 Commit/PR。

## 错误记录

| 时间 | 现象 | 处理 |
|---|---|---|
| 2026-08-04 | 自动执行 `uv python install 3.12` 时权限审批代理返回 503 | 用户改为手动执行，已完成 |
| 2026-08-04 | 历史 README 的编码导致大批量补丁上下文本匹配失败 | 改为独立小补丁，新骨架文件已成功写入 |
| 2026-08-04 | Windows PowerShell 5.1 无法正确解析无 BOM UTF-8 中文 `.ps1` | 执行脚本统一使用 ASCII；已用 UTF-8 解析探针确认原脚本无语法错误 |
| 2026-08-04 | Hatchling 无法推断 `homepilot-api` 的实际代码包 | 在 `pyproject.toml` 显式设置 wheel 的 `packages = ["app"]` |
| 2026-08-04 | Ruff 要求将第三方 `fastapi` 与项目包 `app` 分组，且 import 区块后只保留一个空行 | 按 Ruff 完整 diff 调整为 `fastapi`、空行、`app`、空行、模块变量 |
| 2026-08-05 | Codex 受限沙箱在安装 PowerShell 7 后无法启动 WindowsApps `pwsh.exe` | 不影响用户终端；安装、Git 与验证命令继续由用户手动执行 |
