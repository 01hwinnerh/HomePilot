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

## 数据库基础层发现（2026-08-05）

- 当前仓库尚无 `backend/alembic.ini` 与 `backend/alembic/`，异步迁移环境需要从明确的 Red 测试开始建立。
- Docker MySQL 当前只通过 `MYSQL_DATABASE` 初始化业务库 `homepilot`；集成测试必须使用独立 `homepilot_test`，不能在业务库中创建或清理测试表。
- 本地已存在的 MySQL volume 不会重新执行 `docker-entrypoint-initdb.d` 初始化脚本，因此补充自动初始化脚本后，本机仍需显式执行一次测试库初始化命令；该命令由用户手动运行。
- 第一个数据库集成 Red 实际返回 MySQL `1044 Access denied`，说明 `homepilot` 用户没有 `homepilot_test` 权限；修复边界是创建隔离测试库并只授予该库权限，而不是提升业务用户的全局权限。
- 后续 TDD 中，结果完全可预测且只产生冗长堆栈的 Red 不再要求用户手动执行；助手记录 Red 依据，用户重点执行 Green、集成回归和提交前验证。
- 测试库权限修复后，`asyncmy` 已进入 MySQL 8.4 默认 `caching_sha2_password` 认证流程，但环境缺少其 RSA 加密所需的可选包 `cryptography`；`pyproject.toml`、`uv.lock` 与 `uv pip show` 均确认该包不存在。
- 推荐保留 MySQL 8.4 的现代认证方式，并将 `cryptography` 声明为后端直接运行时依赖；不回退到较弱且在 MySQL 8.4 中默认禁用的 `mysql_native_password`，也不为本地开发单独引入 TLS 证书体系。
- 已检查已安装的 `asyncmy 0.2.11` 包元数据：它没有提供可选 extra 来自动拉取该依赖，因此需要在 HomePilot 的 `pyproject.toml` 中显式声明 `cryptography`。
- 用户执行 `uv sync --all-groups` 后解析并安装 `cryptography 46.0.7`；该版本满足已确认的 `>=44,<47` 范围，并已由 `uv.lock` 精确固定。
- 数据库基础层项目级回归通过；前端仍有既存的 Ant Design 控制台 chunk 超过 500 kB 和 `eslint.config.js` 未声明 ESM 的非阻塞警告，留到前端功能阶段单独处理，不混入数据库 Commit。
- 提交前独立审查发现：带 DDL/DML 的集成测试若误配 `TEST_DATABASE_URL` 可能操作业务库；迁移测试在持久库上直接 `upgrade head` 也可能产生假阳性。现采用统一安全闸门（测试库名必须含 `test` 且不同于业务库）、pytest session fixture、Docker 初始化脚本同名拒绝，以及 `downgrade base → upgrade head` 修复。
- 独立复审确认上述 Critical/Important 均已关闭，未发现新的提交阻塞项。

## 错误记录

| 时间 | 现象 | 处理 |
|---|---|---|
| 2026-08-04 | 自动执行 `uv python install 3.12` 时权限审批代理返回 503 | 用户改为手动执行，已完成 |
| 2026-08-04 | 历史 README 的编码导致大批量补丁上下文本匹配失败 | 改为独立小补丁，新骨架文件已成功写入 |
| 2026-08-04 | Windows PowerShell 5.1 无法正确解析无 BOM UTF-8 中文 `.ps1` | 执行脚本统一使用 ASCII；已用 UTF-8 解析探针确认原脚本无语法错误 |
| 2026-08-04 | Hatchling 无法推断 `homepilot-api` 的实际代码包 | 在 `pyproject.toml` 显式设置 wheel 的 `packages = ["app"]` |
| 2026-08-04 | Ruff 要求将第三方 `fastapi` 与项目包 `app` 分组，且 import 区块后只保留一个空行 | 按 Ruff 完整 diff 调整为 `fastapi`、空行、`app`、空行、模块变量 |
| 2026-08-05 | Codex 受限沙箱在安装 PowerShell 7 后无法启动 WindowsApps `pwsh.exe` | 不影响用户终端；安装、Git 与验证命令继续由用户手动执行 |
| 2026-08-05 | MySQL 权限修复后，`asyncmy` 报错缺少 `cryptography` | 已确认是 `caching_sha2_password` 的运行时依赖缺口；等待用户确认新增依赖后修复 |
| 2026-08-05 | Alembic 新目录导致 Ruff 将 `alembic` import 识别为项目本地分组 | 按 Ruff 的项目路径解析结果，将 SQLAlchemy 与 `alembic/app` 分组 |
| 2026-08-05 | Codex 工具环境无法识别 `C:\\Program Files\\PowerShell\\7\\pwsh.exe` | 未进入项目验证脚本；改由工具当前 PowerShell 进程直接执行 ASCII 脚本 |
| 2026-08-05 | 提交前审查发现测试库误配可能让回滚测试在业务库执行 DDL/DML | 增加 Python 与 Docker 双重安全闸门，并将拒绝分支加入自动化验证 |
