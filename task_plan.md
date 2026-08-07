# HomePilot 项目总计划

**目标：** 构建用于 AI 应用 / Agent 开发岗位作品集展示的多商家精品家居平台，突出 FastAPI 交易能力、RAG、LangGraph、LangSmith、可审计 Agent 与多租户安全。

## 当前状态

- 当前阶段：阶段 1 — 身份、租户、商家与商品
- 当前状态：`in_progress`
- 项目名称：HomePilot
- 最近确认：用户已通过 uv 安装 Python 3.12；所有安装与 Git 命令由用户手动执行。
- 最近确认：采用“稳定大版本 + 锁文件固定精确版本”的依赖策略。
- 当前模块：Task 6 Console 登录与商家/平台身份展示（已完成内部实现、workspace 回归与用户集中验收，等待独立 Commit/PR）。
- 当前阻塞：无；本模块未新增第三方依赖，Storefront 已接入共享 auth-client workspace 包。

## 技术栈与版本基线

这是项目的已确认技术基线；新增依赖、框架升级或版本冲突必须先记录到 `findings.md` 并向用户说明，不能自行替换。

| 层级 | 技术选型 | 已确认版本/策略 |
|---|---|---|
| Python 运行时 | Python + uv | Python 3.12；由 uv 项目虚拟环境隔离，不覆盖本机 Anaconda 3.11 |
| 后端 API | FastAPI、Pydantic、SQLAlchemy、Alembic | Python 3.12；实际精确版本由 `backend/uv.lock` 固定 |
| 数据库 | MySQL | 8.4；交易、身份和审计数据真源 |
| 缓存/队列 | Redis、Celery、Transactional Outbox | Redis 7.4；不作为库存真源 |
| Agent | LangChain、LangGraph、LangSmith | 通过集中配置接入 DeepSeek，默认 `deepseek-v4-flash` |
| RAG | Qdrant、MinIO、Embedding/Reranker Provider | Qdrant/MinIO 使用已验证 digest；版本治理按生效知识版本执行 |
| Storefront | React、TypeScript、Vite、Zustand、TanStack Query、Tailwind | Node 24.14.1、pnpm 11.9.0；实际精确版本由 `frontend/pnpm-lock.yaml` 固定 |
| Console | React、TypeScript、Vite、Ant Design | 与 Storefront 共用 Node/pnpm workspace，按角色加载路由 |
| 测试与质量 | pytest、Vitest、Ruff、ESLint、TypeScript | 每个独立模块采用 TDD，并在 Commit/PR 前集中回归 |
| 本地基础设施 | Docker Compose、Nginx（后续部署） | Docker Compose 5.1.3；本地服务由 Docker Desktop 管理 |

### 当前锁定的关键解析版本

以下是当前锁文件已解析并验证过的关键直接依赖版本；完整依赖树仍以两个 lock 文件为准。

| 领域 | 关键版本 |
|---|---|
| 后端 Web/数据 | FastAPI 0.141.1、Pydantic 2.13.4、SQLAlchemy 2.0.51、Alembic 1.18.5、Uvicorn 0.52.1 |
| 后端任务/缓存 | Celery 5.6.3、Redis Python client 5.3.1、cryptography 46.0.7 |
| 认证 | argon2-cffi 25.1.0、email-validator 2.3.0、PyJWT 2.13.0 |
| Agent/观测 | LangChain 1.3.14、LangGraph 1.2.10、langgraph-checkpoint-redis 0.5.1、LangSmith 0.10.15 |
| RAG/存储 | qdrant-client 1.18.0、MinIO Python SDK 7.2.20 |
| 前端运行时 | Node 24.14.1、pnpm 11.9.0、React 19.2.8、TypeScript 5.7.3 |
| 前端工程/测试 | Vite 6.4.3、Vitest 3.2.7、ESLint 9.39.5、Zustand 5.0.14、jsdom 27.4.0 |
| 控制台 UI | Ant Design 5.29.3 |

### 配置与密钥边界

- 服务地址、Provider、模型名、开关统一由根目录 `.env` 和 `backend/app/core/config.py` 管理。
- `.env.example` 只保留变量名和非敏感示例；真实 DeepSeek/LangSmith/数据库等密钥不得提交。
- DeepSeek 默认 API 地址为 `https://api.deepseek.com`，默认模型为 `deepseek-v4-flash`；`deepseek-v4-pro` 仅作为手动切换项。
- 本地开发允许 `AUTH_COOKIE_SECURE=false`；上线前必须切换为 HTTPS + `AUTH_COOKIE_SECURE=true`，并完成生产配置前置检查。

## 阶段追踪

| 阶段 | 目标 | 状态 | 验收结果 |
|---|---|---|---|
| 0 | 环境基线、依赖锁定、工程骨架与本地基础设施 | 已完成 | PR #1 已合并，全量回归通过 |
| 1 | 身份、租户隔离、商家、店铺、商品与库存 | 进行中 | 认证与租户基础已完成，正在接入前端认证闭环 |
| 2 | 跨店购物车、订单、库存预占与模拟支付 | 未开始 | — |
| 3 | 售后策略版本、规则引擎、售后状态机 | 未开始 | — |
| 4 | 知识版本、异步索引、RAG 与跨店对比 | 未开始 | — |
| 5 | LangGraph Agent、持久化、确认动作、人工接管 | 未开始 | — |
| 6 | 前端体验、观测、LangSmith 评测、部署与作品集文档 | 未开始 | — |

## 当前阶段任务

- [x] 确认项目名为 `HomePilot`。
- [x] 确认 uv 管理的 Python 3.12 已由用户安装。
- [x] 创建可持续维护的计划、发现与进度文档。
- [x] 确认 Python、前端、Docker、Agent/RAG 依赖版本矩阵策略。
- [x] 由用户手动创建项目虚拟环境并安装后端锁定依赖。
- [x] 由用户手动安装前端锁定依赖。
- [x] 创建后端、前端、基础设施与测试骨架。
- [x] 由用户手动启动 Docker Compose 并验证服务健康。
- [x] 锁定 Qdrant/MinIO 已验证镜像 digest。
- [x] 运行工程骨架小型全量回归。
- [x] 完成 `chore/project-scaffold` Commit 与 GitHub PR #1。
- [x] 完成数据库基础层 Commit 与 GitHub PR，已合并至 `main`。
- [x] 确认身份、refresh token、CSRF、RBAC 与多租户隔离设计；规格见 `docs/superpowers/specs/2026-08-05-identity-tenancy-auth-design.md`。
- [x] 编写身份、租户与认证的 TDD 实施计划；见 `docs/superpowers/plans/2026-08-05-identity-tenancy-auth-implementation.md`。

## 已完成模块：数据库基础层

- [x] Red：为数据库 Settings、SQLAlchemy Database 封装和 Base metadata 写失败单元测试，已确认因目标模块缺失而失败。
- [x] Green：实现集中数据库配置、AsyncEngine/Session 和命名约定，4 个单元测试连续两次通过。
- [x] Quality：Ruff import 格式问题已修复，用户复验全量静态检查通过。
- [x] Alembic：创建可运行的异步迁移基线。
- [x] Integration：验证 MySQL 连通、事务回滚和 Alembic upgrade。
- [x] Regression：审查修复后后端 11 个测试、Ruff 及工程小型全量回归通过，复审无 Critical/Important。
- [x] 完成 `feat/database-foundation` Commit 与 GitHub PR。

## 已完成模块：认证配置与安全原语

- [x] 用户确认后端认证依赖：`argon2-cffi`、`email-validator`、`PyJWT`，并完成 `uv sync --all-groups`。
- [x] Red→Green：Argon2 密码哈希、access JWT、opaque refresh token、CSRF 双重提交比较与随机 CSRF token。
- [x] Red→Green：CORS 精确白名单与通配符拒绝、Cookie 安全开关、access/refresh 有效期、Redis 限流地址与限流默认值。
- [x] 补充篡改 JWT 和有效签名但 `typ != access` 的拒绝测试。
- [x] 执行本模块完整单元回归、后端全量回归与 Ruff：认证定向 16 passed，后端全量 26 passed，Ruff 通过。
- [x] 完成 `feat(auth): add security configuration and token primitives` Commit 与 GitHub PR，并已合并至 `main`。

## 已完成模块：身份、商家与 refresh session 数据模型（Task 2）

- [x] Red→Green：`User`、`Merchant`、`MerchantMember`、`AuthSession` ORM；商家成员联合唯一、refresh token 仅保存哈希、角色枚举、共享租户/审计 Mixin。
- [x] Red→Green：revision `20260805_0002` 正向创建四张表、关键唯一/查询索引、外键与角色约束；反向按依赖顺序删除。
- [x] 测试库迁移 fixture 在每次测试后回滚至 `base` 并断言四张领域表已删除，避免未提交迁移演进污染持久测试库。
- [x] 架构修订：采用 ADR-0002 的 `UTCDateTime`；MySQL 存 UTC-naive，应用层读写 aware UTC，拒绝 naive 输入，不依赖数据库服务器时区。
- [x] 助手验证：后端全量 `41 passed`、Ruff 通过、Alembic metadata 检查无新增操作。
- [x] 用户执行业务库迁移与最终 Green 回归。
- [x] 用户完成 `feat(identity): add users merchants and auth sessions` Commit 与 GitHub PR，已合并。

## 已完成模块：认证服务、Cookie/CSRF API 与 Redis 限流（Task 3）

- [x] Red→Green：`AuthService` 完成注册、统一登录失败、refresh rotation、用户有效性校验和当前用户查询；refresh 原文始终不写入数据库或日志。
- [x] Red→Green：FastAPI `register/login/refresh/logout/me`、精确 CORS、HttpOnly refresh Cookie、双重提交 CSRF 和 Cookie 清理。
- [x] Red→Green：Redis 固定窗口限流，键仅含 email/IP 的 SHA-256 组合摘要；真实 Redis 集成测试覆盖阈值拒绝。
- [x] 集成回归：注册→`/me`、refresh rotation 与重放拒绝、CSRF 拒绝、logout 撤销、并发 refresh 至多成功一次。
- [x] 提交前独立审查修复：refresh 限流按 refresh token 哈希分桶，不再让同一 IP 的不同用户共用配额；拒绝/幂等路径显式 rollback；`/me` 返回启用商家成员关系；补足停用/过期、Cookie 属性和安全日志脱敏回归。
- [x] 复审加固：安全事件 payload 锁定为六个允许字段，回归检查不出现密码/JWT/refresh/CSRF/Cookie/Authorization 字符串；同 IP 不同 refresh session 使用不同限流 bucket；logout 缺失 CSRF 明确拒绝。
- [x] 用户执行业务库迁移、认证定向回归、后端全量回归和 Ruff；复核修订后的全量测试为 56 passed，Ruff 通过。
- [x] 用户完成 `feat(auth): add rotating session authentication API` Commit 与 GitHub PR，已合并至 `main`。

## 已完成模块：Storefront auth-client（Task 5 第一小模块）

- [x] 共享包 `@homepilot/auth-client`：认证类型、register/login/refresh/logout/me、Cookie/CSRF 和错误契约。
- [x] auth-client 行为测试、TypeScript build 与 lint 已由助手验证通过。
- [x] 用户完成该小模块验收并提交独立 Commit/PR。

## 已完成模块：Storefront Zustand 内存会话状态（Task 5 第二小模块）

- [x] `createAuthStore(authClient)` 依赖注入接口。
- [x] refresh 成功、refresh 失败匿名、clear 清空内存状态。
- [x] 并发 `restoreSession()` Promise 去重，避免 StrictMode 触发重复 refresh rotation。
- [x] 4 个行为测试、TypeScript build、ESLint、Vite production build 已通过。

## 当前模块：Storefront 顾客认证 UI（Task 5 第三小模块）

- [x] 温暖编辑感登录/注册面板，含提交态与安全错误文案。
- [x] 应用启动恢复 refresh session；失败时安全落为匿名状态。
- [x] 注册/登录成功后仅将 access token 保存至 Zustand 内存。
- [x] 退出时调用服务端 logout；无论请求成功或失败都清空本地认证状态。
- [x] 行为测试覆盖匿名、注册、登录失败、启动恢复、退出成功与退出网络失败。
- [x] 用户集中验收并完成 Task 5 完整 UI 闭环独立 Commit/PR；PR 已合并。

## 下一模块：Console 登录、商家/平台身份展示（Task 6）

- [x] 用户确认本地 `main` 已包含 Storefront UI 合并结果，并创建 Console 特性分支。
- [x] 说明并确认 Console UI 选型、普通顾客无控制台权限提示和测试边界。
- [x] 复用 `@homepilot/auth-client`，实现 Console 内存会话 store、登录、启动恢复、身份摘要和退出。
- [x] Console 行为测试、TypeScript、ESLint 和 Vite production build 已由助手通过；用户已完成前端 workspace 最终验收。

## 已完成模块：Principal、TenantContext 与 Repository 硬隔离（Task 4）

- [x] 审查修订：Principal/TenantContext 带内部 provenance capability；`tenant_scope`、TenantRepository 与 PlatformRepository 都拒绝普通参数手造的对象，避免后续 Agent/服务把不可信身份包装成授权上下文。
- [x] Red→Green：仅由活跃 `MerchantMember` + 活跃 `Merchant` 构造的 `TenantContext`，跨商家构造一律拒绝。
- [x] Red→Green：普通 `TenantRepository` 强制携带 TenantContext 与显式 merchant 条件；`PlatformMerchantRepository` 只接受平台管理员 Principal。
- [x] Red→Green：`tenant_scope` 通过 SQLAlchemy `with_loader_criteria` 为所有 MerchantOwned ORM `SELECT`、bulk `UPDATE`、bulk `DELETE` 追加第二道过滤；真实 MySQL 测试验证直接查询和跨商家 bulk update 都无法绕过，且 scope 退出后不会泄漏。
- [x] 复审加固：真实 MySQL 回归新增跨商家 bulk delete 拒绝、异常退出 reset、两个并发 asyncio Task 的独立 ContextVar 作用域；ADR 明确 capability 防止不可信业务参数误用，但不把拥有任意 Python 导入/执行权的同进程恶意代码当作可隔离主体。
- [x] API 认证依赖从 access token 仅取得 user ID，再从数据库读取 active/platform 状态；`/me` 已复用该可信 Principal。
- [x] 助手全量回归：`65 passed`，Ruff 通过；保留既有 Starlette 上游弃用警告。
- [x] 提交前独立审查、用户最终集中验收与 Commit/PR。

## 更新约定

1. 每个阶段开始前更新本文件的“当前状态”和“当前阶段任务”。
2. 每完成一个可验证单元，记录到 `progress.md`；环境与兼容性结论记录到 `findings.md`。
3. 任何架构变更先更新 `docs/adr/` 与实施计划，再修改代码。
4. 任何依赖冲突、外部服务缺失或连续失败三次的事项都标注为阻塞，并先向用户说明。
5. 每个可独立说明的模块完成后，先提示用户手动执行 Commit 并发起 GitHub PR；下一模块不得与该 Commit 混合。Commit 信息采用 Conventional Commits，并准确描述本模块边界。
6. 预期必然失败的 TDD Red、诊断命令和静态探针由助手执行并记录；用户主要执行 Green、阶段回归、安装/Docker 状态变更和 Git 命令，且每条用户命令都说明目录、作用与预期结果。
7. 同一小模块内连续的 Green 测试和静态检查应合并为一组命令交给用户执行；助手在内部仍按单个行为完成 Red→Green，避免未验证改动累积。
8. 每个独立模块的 PR 合并后，或用户主动要求更新时，必须同步更新 `HANDOFF.md` 与 `docs/handover/`；交接内容以最新已验证和已合并状态为准，不能继续描述已完成模块为“待开发”。

## 未来上线的强制前置检查

当用户提出上线、部署、发布或对外开放访问时，必须先提醒并逐项确认以下内容，再提供任何生产部署命令：

1. `APP_ENV=production`、`APP_DEBUG=false`，配置独立 HTTPS 域名与精确 `BACKEND_CORS_ORIGINS`，不得使用 `*`。
2. `AUTH_COOKIE_SECURE=true`；若需要跨站 Cookie，再单独评估 `SameSite=None` 与 HTTPS。JWT 签名密钥、数据库/Redis/MinIO 密码均替换为生产随机值，且只来自密钥管理或未提交的环境变量。
3. 生产 MySQL 迁移、备份/恢复演练、Redis 持久化、对象存储 bucket 权限和最小账号权限均已验证。
4. Docker 镜像不使用漂移的 `latest`；反向代理 HTTPS、健康检查、日志脱敏、Sentry/Prometheus 告警、回滚方案和域名/DNS 均已确认。
5. 真实 DeepSeek、LangSmith 等外部 Key 的权限、额度、Trace 脱敏和成本上限已检查；非生产 Key 不得复用到生产环境。

## 非范围

首版不接入真实支付、物流、商家结算、发票、税务、扫描件 OCR；不使用 Saga 或 Redis-first 库存真源。
