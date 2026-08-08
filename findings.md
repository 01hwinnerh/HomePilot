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
- 认证：采用短期 JWT access token 与 rotating opaque refresh token；refresh token 仅保存于 HttpOnly Cookie，数据库仅保存其哈希与撤销状态。商家授权不写入 JWT，必须由 `MerchantMember` 实时构造租户上下文。

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

## 生产环境提醒约定（2026-08-05）

- 用户要求在未来提出上线、部署或发布时，先提醒生产与开发的配置差异并完成前置检查，尤其是 `AUTH_COOKIE_SECURE=true`、`APP_DEBUG=false`、精确 CORS 白名单、独立高熵密钥、HTTPS 与基础设施备份/监控。
- 在未明确生产环境域名、HTTPS、密钥来源、数据库备份和回滚策略前，不提供会直接对外暴露服务的部署操作。

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

## 认证安全原语发现（2026-08-05）

- 用户确认并同步了认证直接依赖；锁文件实际固定 `argon2-cffi 25.1.0`、`email-validator 2.3.0`、`PyJWT 2.13.0`，均满足已确认的版本范围与 Python 3.12。
- JWT 签名密钥只存在用户本地 `.env` 的 `AUTH_JWT_SECRET`，`.env.example` 只保留占位符；助手不读取或输出该密钥。
- 当前配置明确拒绝带凭据 CORS 的 `*`，本地开发默认 `AUTH_COOKIE_SECURE=false`；生产上线时必须改为 HTTPS 下的 `true`，该提醒已写入总计划。

## 身份数据模型与 UTC 时间发现（2026-08-05）

- `20260805_0002` 在同一 MySQL 事务域内创建 `users`、`merchants`、`merchant_members` 与 `auth_sessions`；主/外键、关键索引、refresh 哈希唯一和角色约束均由真实 `homepilot_test` 迁移验证。
- MySQL 会为唯一约束建立底层索引，但 SQLAlchemy ORM 仍应显式声明 `User.email` 的 `unique=True, index=True`，避免 metadata 与手写迁移漂移；迁移采用同名唯一索引。
- 测试 fixture 必须在每次 `base → head` 验证后回滚到 `base` 并确认领域表删除。否则编辑尚未提交的 revision 后，持久 `homepilot_test` 的 `alembic_version` 可能与实际表不一致。
- MySQL `DATETIME` 不保存时区。ADR-0002 规定 `UTCDateTime`：领域层只传递 aware UTC 时间，写入归一化为 UTC-naive，读取恢复 aware UTC；`TimestampMixin` 使用 Python `utc_now()`，不依赖数据库服务器时区。
- 当前 Alembic `command.check` 在 MySQL 测试库上返回 `No new upgrade operations detected.`，说明 ORM metadata 与 revision 的物理 schema 一致。

## 认证服务与会话 API 发现（2026-08-05）

- Cookie 名称和适用 Path 已补充为集中 Settings：`AUTH_REFRESH_COOKIE_NAME`、`AUTH_CSRF_COOKIE_NAME` 与 `AUTH_COOKIE_PATH`，避免路由中散落硬编码；默认仍是 `refresh_token`、`csrf_token` 与 `/api/v1/auth`。
- refresh rotation 在同一数据库事务中使用 `SELECT ... FOR UPDATE` 锁定旧会话：旧会话被标记 `rotated`、新会话创建、链路 ID 写回后才提交。真实 MySQL 并发回归确认同一 refresh token 只有一次 200，其余请求为 401。
- 认证限流采用 Redis `INCR` + 首次 `EXPIRE` 固定窗口；Redis key 只保存标准化 email 与 client IP 拼接值的 SHA-256，不保存可识别的邮箱或 IP 原文。
- FastAPI 的 `204 No Content` logout 必须显式构造无内容 `Response` 再删除 Cookie；复用注入的 `Response` 会导致 ASGI 测试传输无法完成响应。该边界已有 CSRF、清 Cookie 与 refresh 重放回归。
- unit 与 integration 目录不能使用同名顶层 pytest 模块；`test_auth_rate_limit.py` 与同名集成文件发生 module import mismatch，已将单元文件重命名为 `test_auth_rate_limiter.py`。
- 提交前独立审查发现 refresh 请求不能只以空 email + IP 限流，否则同一 NAT 下所有用户会共享 5 次配额。现在 refresh 使用 refresh token 的 SHA-256 再哈希分桶，login/register 仍使用 email+IP 哈希；Redis key 不含原始 token、邮箱或 IP。
- refresh 的 `SELECT ... FOR UPDATE` 拒绝路径现在显式 rollback。审查修复还发现 rollback 后 ORM 实例会过期，因此审计用 `user_id` 必须在 rollback 前提取，避免异步 `MissingGreenlet` 隐患；停用用户/过期 token 集成回归覆盖该场景。
- `/me` 按身份规格返回活动商家成员关系（`merchant_id`、`merchant_name`、`OWNER/STAFF`）；仅返回成员与商家均为启用状态的记录。它是展示信息，不能替代后续 TenantContext 的逐请求授权查询。
- 第二轮复审要求将安全日志验收从“仅不记录密码”提升为字段白名单保护。现有回归锁定 `security_event` payload 只能有 event/result/user_id/session_id/request_id/failure_reason，且 caplog 中不得出现 JWT、refresh/CSRF、Cookie 或 Authorization 的可识别值。

## 租户上下文与硬隔离发现（2026-08-06）

- access JWT 仍然只表达用户 ID；`Principal.is_platform_admin` 每次从 active `User` 记录读取，避免 JWT 中过期的角色事实成为授权依据。
- `TenantContext` 只能由 `TenantContextFactory` 查询活跃 membership 与活跃 merchant 后生成。它不是前端、URL 参数或 Agent 工具参数可直接信任的数据。
- `TenantRepository` 的显式 `merchant_id` 条件是第一道防线；`tenant_scope` 通过 SQLAlchemy `with_loader_criteria(MerchantOwnedMixin, ...)` 注入的条件是第二道防线。真实 MySQL 集成测试同时验证了 Repository 和直接 ORM 查询的跨商家拒绝。
- 平台跨商家查询不复用 TenantRepository 的 bypass 参数，而是独立的 `PlatformMerchantRepository`，构造时就拒绝非平台 Principal。
- 审查指出 frozen dataclass 只能防止字段修改，不能阻止内部代码重新实例化。因此本模块额外使用仅由身份依赖/工厂签发的 provenance capability；正常业务、Agent 工具和 Repository 不能仅凭 user_id、merchant_id 或 `is_platform_admin=True` 构造可用授权上下文。
- `with_loader_criteria` 不能仅用于 SELECT：在 `do_orm_execute` 中也要覆盖 ORM bulk UPDATE/DELETE，否则后续遗漏 merchant 条件的批量写可能跨租户。集成回归断言 scoped update 商家 B 记录的 rowcount 为 0，scope 退出后查询恢复正常。
- ContextVar 在同一 task 的异常退出由 context manager 的 `finally` 重置；不同 asyncio task 使用各自设置的 tenant scope 时保持独立。本模块没有在 tenant scope 内创建后台 task，后续异步 worker 必须重新从受控输入构造上下文，不能复制 Web 请求 ContextVar。
- provenance capability 是减少错误调用面的服务端内部机制，不是 Python 进程内的安全沙箱。任何能任意导入私有模块并运行代码的主体已拥有服务端执行权；Agent 工具层的实际安全要求仍是只接受闭包注入的 context，绝不接受前端/模型字段构造 context。

## Storefront auth-client 发现（2026-08-06）

- 共享认证客户端不依赖 React，商城和控制台均通过同一 HTTP/CSRF 契约，access token 只由上层以内存状态持有。
- `pnpm install --lockfile-only` 能更新 importer，但不会建立新 workspace 包的可执行依赖链接；新包首次测试因此出现 `vitest not found`。普通 `pnpm install` 后测试命令正常。
- auth-client 的 TypeScript 检查必须启用 `skipLibCheck`，并使用 `ESNext` 标准库类型；否则 Vitest/Vite 声明文件会暴露 Node disposable 类型错误。该配置只作用于共享包，不放宽业务源码的 `strict` 检查。

## Storefront Zustand 会话状态发现（2026-08-06）

- Storefront 通过 `@homepilot/auth-client` workspace 依赖消费共享认证契约；本模块不新增第三方依赖。
- `restoreSession()` 在 store 闭包内维护唯一 in-flight Promise；React StrictMode 或多个页面同时恢复时只发起一次 refresh，完成/失败后释放引用。
- refresh 失败只转换为 anonymous，不向 UI 泄露底层异常；access token 只进入 Zustand 内存状态，未使用 persist middleware。
- 用户执行 Storefront lint 时，pnpm 因新增 workspace manifest 自动补建本地链接；后续验证应先由用户执行普通 `pnpm install`，再运行测试/build/lint。

## Storefront 顾客认证 UI 发现（2026-08-07）

- 登录、注册、启动恢复与退出都复用 `@homepilot/auth-client`，未新增依赖或浏览器存储。
- 退出采用 `try/catch/finally`：请求后端撤销 refresh Cookie，即使网络异常也必须清空 Zustand 内存身份，防止共享设备继续显示已登录界面。
- 此策略不把网络异常展示为可继续使用的登录状态；用户可重新登录，服务端 refresh session 的最终失效由下一次成功 logout 或自然到期保障。
- Storefront 顾客认证 UI PR 已合并；下一模块不得复用旧特性分支上的未确认状态，应先从已同步的 `main` 创建 Console 分支。

## Console 认证 UI 发现（2026-08-07）

- Console 复用 `@homepilot/auth-client` 与 Zustand 内存会话模式；仅在 Console manifest 中声明已有 workspace/test 依赖，没有新增外部版本。
- Console 权限展示完全来自后端 `AuthUser.is_platform_admin` 与 `memberships`；普通顾客只显示无控制台权限，不由前端推断商家身份。
- Ant Design 保留为基础组件/主题提供者，认证页采用自定义编辑感 CSS；不提前引入完整后台设计系统或业务导航。
- Console 的 `import.meta.env` 类型声明需要独立的 `src/vite-env.d.ts`；这是 Vite 类型接线，不放宽 TypeScript strict 检查。

## Console 合并与 CI 决策（2026-08-07）

- Console 登录与身份展示 PR 已合并，用户已同步 `main` 并确认工作区干净。
- GitHub Actions CI 已实现并合并；首次真实 GitHub Runner 的 backend 与 frontend Job 已通过。
- CI 第一版只运行锁文件安装、后端 pytest/Ruff、前端 test/build/lint；本地人工 push 前仍保留快速检查，CI 负责远端最终裁决和留痕。
- 不在第一版 CI 中强制启动所有 Docker 服务或调用真实 DeepSeek/LangSmith；这些放入独立集成/nightly job，避免外部服务波动阻塞普通 PR。
- CI review 已确认：Compose `up --wait` 会等待 `running|healthy`，现有 MySQL/Redis healthcheck 已覆盖数据库可连接前的初始化；额外设置 `--wait-timeout 120` 和 Job `timeout-minutes: 15`，防止服务或测试无限等待。
- Compose 步骤保留在 workflow 根目录；仅 uv/pytest/Ruff 通过 `working-directory: backend` 进入后端目录，因此不会丢失根目录 `docker-compose.yml`。
- CI review 核验：当前 `frontend/package.json` 的 workspace test 脚本最终执行 `vitest run`，不会进入 watch mode；Node 24.14.1 是本地已验证基线且被 engines `>=22 <25` 接受，暂不因时间敏感的旧版本判断降级到 Node 20/22。
- 为降低未来维护者对工作目录的误解，workflow 的 Compose 启停命令显式指定根目录 `docker-compose.yml`。
- CI workflow 本地等价回归已通过：后端 65 tests 与 Ruff、前端三个 workspace 的 test/build/lint，以及 `docker compose config --quiet` 均成功；首次真实 GitHub Runner 已完成并通过。

## 错误记录

## 认证联调修复发现（2026-08-08）

- `EmailStr` 会拒绝 `.local` special-use 域名；最终没有放宽正式邮箱校验，而是把三个固定本地 demo 标识改为标准 `homepilot.dev`，并在 seed 中对旧 `.local` 记录做精确、无覆盖迁移。若新旧邮箱同时存在则冲突并 rollback。
- refresh Cookie 与 CSRF Cookie 不能共用 Path：refresh 继续限制为 `/api/v1/auth`，CSRF 改为 `/`，否则前端页面无法读取 CSRF 值，启动 refresh 会收到 403 并被前端安全地转换为匿名状态。
- Console 的 login/refresh 响应不应被视为商家授权事实；Console 现在取得 access token 后调用 `/me`，以数据库实时返回的 active memberships 展示商家与角色。
- 认证限流拆为 IP 请求总量桶和失败凭据桶：失败密码才增加后者，成功登录清零；refresh 保持独立 token-hash 桶。429 通过 `Retry-After` 告知客户端等待窗口。
- 后端认证全量回归为 78 tests，Ruff 通过；前端 workspace test/build/lint 全部通过。Node ESM 与 Starlette 上游弃用警告仍为非阻塞既存警告。

## 本地身份演示种子发现（2026-08-08）

- 演示 seed 采用固定邮箱与商家名白名单，而非新增 `is_demo` 数据库字段：避免为本地展示需求引入迁移；同名记录不满足预期结构时安全拒绝，绝不“修正”或覆盖原有账号。
- 种子业务规则在 `app.modules.identity.demo_seed`，外层脚本只负责 CLI 启动；集成测试因此可使用隔离的 `homepilot_test` 直接验证真实 MySQL 行为，不会测试或写入业务库。
- `DEMO_SEED_PASSWORD` 是可选 `SecretStr` setting，但 CLI 要求它非空；密码只在进程内传给 Argon2 哈希，不进入数据库明文字段、日志、异常或命令输出。
- `verify_stack.ps1` 保持只读验证，不调用 seed；否则每次回归都会修改业务库，破坏验证脚本的可预测性。

## GitHub Actions 首次运行发现（2026-08-07）

- Frontend Job 在 `pnpm install --frozen-lockfile` 失败：pnpm 11.9 的干净安装仍将 esbuild 判为 ignored build script 并以退出码 1 结束。最终确认项目需要新版显式批准配置 `allowBuilds: { esbuild: true }`；本地强制重建依赖已执行 `esbuild postinstall ... Done`，随后 frozen install、test、build、lint 已复验通过。
- Frontend Job 随后在 lint 阶段失败：`@homepilot/auth-client` 定义了 `eslint src`，但没有在自身 `devDependencies` 声明 ESLint。pnpm 的干净 workspace 安装不会让它借用其他包的二进制，因此报 `eslint: not found`。用户确认后补充与两个应用一致的 `eslint: ^9.20.0` 并更新锁文件；本地完整 lint 已通过。
- Backend Job 后续测试失败：CI 正确注入 `APP_ENV=test`，但健康检查测试硬编码期望 `development`。运行时接口返回当前 Settings 环境的行为是正确的；已将测试改为断言 `get_settings().app_env`，同时覆盖本地和 CI 环境。
- Backend Job 在全新 GitHub Runner 的 MySQL 初始化阶段退出。完整日志确认：初始化脚本被官方 entrypoint source 后，脚本的 `set -u` 泄漏到 entrypoint，后续读取可选变量 `MYSQL_ONETIME_PASSWORD` 时触发 `unbound variable`。已移除 nounset，仅保留 `set -e`，并保留 Compose 启动失败日志。

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
| 2026-08-05 | 修改未提交的 `20260805_0002` 后，测试库 migration head 与实际表不一致 | 一次性重建隔离库，并让每个迁移测试 teardown 回滚到 base 后断言领域表已删除 |
| 2026-08-05 | PowerShell → Docker Compose → `sh -c` 的嵌套 SQL 引号两次解析失败 | 先在相同 PowerShell 环境以只读探针验证；需要临时传 SQL 时优先标准输入，避免多层嵌套引号 |
| 2026-08-05 | MySQL `DATETIME` 读回 naive 时间，UTC+08:00 refresh 到期时间未归一化 | 用户确认 ADR-0002；使用 `UTCDateTime` 与真实 MySQL round-trip 测试固定 aware UTC 边界 |
