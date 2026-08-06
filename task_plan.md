# HomePilot 项目总计划

**目标：** 构建用于 AI 应用 / Agent 开发岗位作品集展示的多商家精品家居平台，突出 FastAPI 交易能力、RAG、LangGraph、LangSmith、可审计 Agent 与多租户安全。

## 当前状态

- 当前阶段：阶段 1 — 身份、租户、商家与商品
- 当前状态：`in_progress`
- 项目名称：HomePilot
- 最近确认：用户已通过 uv 安装 Python 3.12；所有安装与 Git 命令由用户手动执行。
- 最近确认：采用“稳定大版本 + 锁文件固定精确版本”的依赖策略。
- 当前模块：Principal、TenantContext 与 Repository 硬隔离（Task 4，等待集中最终验收）。
- 当前阻塞：无；本模块不新增依赖或 Alembic migration。

## 阶段追踪

| 阶段 | 目标 | 状态 | 验收结果 |
|---|---|---|---|
| 0 | 环境基线、依赖锁定、工程骨架与本地基础设施 | 已完成 | PR #1 已合并，全量回归通过 |
| 1 | 身份、租户隔离、商家、店铺、商品与库存 | 进行中 | 认证 API 已合并；租户硬隔离等待最终验收 |
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

## 当前模块：Principal、TenantContext 与 Repository 硬隔离（Task 4）

- [x] 审查修订：Principal/TenantContext 带内部 provenance capability；`tenant_scope`、TenantRepository 与 PlatformRepository 都拒绝普通参数手造的对象，避免后续 Agent/服务把不可信身份包装成授权上下文。
- [x] Red→Green：仅由活跃 `MerchantMember` + 活跃 `Merchant` 构造的 `TenantContext`，跨商家构造一律拒绝。
- [x] Red→Green：普通 `TenantRepository` 强制携带 TenantContext 与显式 merchant 条件；`PlatformMerchantRepository` 只接受平台管理员 Principal。
- [x] Red→Green：`tenant_scope` 通过 SQLAlchemy `with_loader_criteria` 为所有 MerchantOwned ORM `SELECT`、bulk `UPDATE`、bulk `DELETE` 追加第二道过滤；真实 MySQL 测试验证直接查询和跨商家 bulk update 都无法绕过，且 scope 退出后不会泄漏。
- [x] 复审加固：真实 MySQL 回归新增跨商家 bulk delete 拒绝、异常退出 reset、两个并发 asyncio Task 的独立 ContextVar 作用域；ADR 明确 capability 防止不可信业务参数误用，但不把拥有任意 Python 导入/执行权的同进程恶意代码当作可隔离主体。
- [x] API 认证依赖从 access token 仅取得 user ID，再从数据库读取 active/platform 状态；`/me` 已复用该可信 Principal。
- [x] 助手全量回归：`65 passed`，Ruff 通过；保留既有 Starlette 上游弃用警告。
- [ ] 提交前独立审查、用户最终集中验收与 Commit/PR。

## 更新约定

1. 每个阶段开始前更新本文件的“当前状态”和“当前阶段任务”。
2. 每完成一个可验证单元，记录到 `progress.md`；环境与兼容性结论记录到 `findings.md`。
3. 任何架构变更先更新 `docs/adr/` 与实施计划，再修改代码。
4. 任何依赖冲突、外部服务缺失或连续失败三次的事项都标注为阻塞，并先向用户说明。
5. 每个可独立说明的模块完成后，先提示用户手动执行 Commit 并发起 GitHub PR；下一模块不得与该 Commit 混合。Commit 信息采用 Conventional Commits，并准确描述本模块边界。
6. 预期必然失败的 TDD Red、诊断命令和静态探针由助手执行并记录；用户主要执行 Green、阶段回归、安装/Docker 状态变更和 Git 命令，且每条用户命令都说明目录、作用与预期结果。
7. 同一小模块内连续的 Green 测试和静态检查应合并为一组命令交给用户执行；助手在内部仍按单个行为完成 Red→Green，避免未验证改动累积。

## 未来上线的强制前置检查

当用户提出上线、部署、发布或对外开放访问时，必须先提醒并逐项确认以下内容，再提供任何生产部署命令：

1. `APP_ENV=production`、`APP_DEBUG=false`，配置独立 HTTPS 域名与精确 `BACKEND_CORS_ORIGINS`，不得使用 `*`。
2. `AUTH_COOKIE_SECURE=true`；若需要跨站 Cookie，再单独评估 `SameSite=None` 与 HTTPS。JWT 签名密钥、数据库/Redis/MinIO 密码均替换为生产随机值，且只来自密钥管理或未提交的环境变量。
3. 生产 MySQL 迁移、备份/恢复演练、Redis 持久化、对象存储 bucket 权限和最小账号权限均已验证。
4. Docker 镜像不使用漂移的 `latest`；反向代理 HTTPS、健康检查、日志脱敏、Sentry/Prometheus 告警、回滚方案和域名/DNS 均已确认。
5. 真实 DeepSeek、LangSmith 等外部 Key 的权限、额度、Trace 脱敏和成本上限已检查；非生产 Key 不得复用到生产环境。

## 非范围

首版不接入真实支付、物流、商家结算、发票、税务、扫描件 OCR；不使用 Saga 或 Redis-first 库存真源。
