# HomePilot 开发交接文档（2026-08-06）

> 本文用于在关闭当前对话后快速恢复开发。新 Coding Agent 应先阅读本文，再阅读根目录 `AGENTS.md`、`task_plan.md`、`findings.md`、`progress.md` 与对应的设计/实施计划；不要根据旧对话记录猜测项目状态。

## 1. 项目定位

**HomePilot** 是面向 AI 应用 / Agent 开发岗位作品集的多商家精品家居平台。首版是模块化单体：FastAPI + MySQL 处理交易与审计，Redis 处理缓存/限流/队列/Agent checkpoint，Qdrant + MinIO 提供版本化 RAG 知识库，LangChain/LangGraph/LangSmith 实现可审计客服 Agent。

首版明确不接入真实支付、物流、商家结算、发票和 OCR；支付与退货签收均为模拟流程。

## 2. 已合并并验证的能力

| 模块 | 状态 | 关键结果 |
|---|---|---|
| 工程骨架与 Docker 基础设施 | 已合并 | MySQL 8.4、Redis 7.4、Qdrant、MinIO；后端/双前端骨架与验证脚本可用。 |
| 数据库基础 | 已合并 | Async SQLAlchemy、Alembic、MySQL 隔离测试库与迁移安全闸门。 |
| 身份数据模型 | 已合并 | `User`、`Merchant`、`MerchantMember`、`AuthSession`，以及 UTC-aware 应用层时间模型。 |
| 认证 API | 已合并 | register/login/refresh rotation/logout/me、Argon2、HS256 access JWT、HttpOnly refresh Cookie、CSRF、Redis 限流与安全日志。 |
| 租户硬隔离 | 已合并 | DB Principal、可信 `TenantContext`、显式 Repository 条件 + SQLAlchemy `with_loader_criteria` 第二道过滤、平台独立 Repository。 |

上一次后端最终回归为：`65 passed`，`uv run ruff check .` 通过。Starlette `TestClient` 弃用警告是既有上游警告，当前不处理。

## 3. 当前未提交模块：Storefront 共享 auth-client

当前开发分支预期为 `feat/storefront-auth`。新 Agent **不得自行执行 Git 命令**；由用户在终端确认分支及提交状态。

已完成并经用户最终验收的第一小模块：

```text
frontend/packages/auth-client/
├─ package.json
├─ tsconfig.json
└─ src/
   ├─ index.ts
   └─ auth-client.test.ts
```

它是无 React 依赖的共享浏览器客户端，供 Storefront 与后续 Console 复用，提供：

- `register()`、`login()`、`refresh()`、`logout()`、`me()`；
- `credentials: "include"`，因此浏览器自动发送 HttpOnly refresh Cookie；
- refresh/logout 从可读取的 `csrf_token` Cookie 复制 `X-CSRF-Token`；客户端绝不读取 refresh token；
- `AuthApiError` 将安全的后端错误详情暴露给 UI；
- access token 仅由上层 Zustand 内存状态持有，严禁写入 `localStorage`、`sessionStorage`、URL 或持久化 middleware；
- 与实际后端一致的用户字段为 `user.memberships`，**不是**旧计划中的 `merchant_memberships`。

已验证：

```text
pnpm --filter @homepilot/auth-client test   # 2 tests passed
pnpm --filter @homepilot/auth-client build  # passed
pnpm --filter @homepilot/auth-client lint   # passed
```

预计还未提交的相关变更：

- `frontend/packages/auth-client/`（新增）；
- `frontend/pnpm-lock.yaml`（新增 workspace importer）；
- `task_plan.md`、`findings.md`、`progress.md`（已更新）；
- 本交接文档（新增）。

不要删除或覆盖用户/平台创建的 `AGENTS.md`；是否纳入当前 Commit 由用户决定。

## 4. 已处理问题与不可重复踩坑

1. 新 workspace 包仅执行 `pnpm install --lockfile-only` 时，不会建立包自己的可执行依赖链接，可能报 `vitest not found`。
   - 正确做法：用户在 `frontend` 普通执行一次 `pnpm install`。
   - 已执行后无需重复安装，直接运行 package scripts 即可。
2. auth-client 初始 `tsconfig` 未设 `skipLibCheck` 与 `ESNext` 类型库，Vitest/Vite 的第三方声明会报 Node/`Disposable`/`asyncDispose` 类型错误。
   - 已修复：保持 `strict: true`，只将该包配置为 `target/lib: ESNext` 并设置 `skipLibCheck: true`。
3. 实施计划中的 `merchant_memberships` 是过期字段名。
   - 必须在下一次修改 `docs/superpowers/plans/2026-08-05-identity-tenancy-auth-implementation.md` 时改为 `memberships`。
4. 旧计划中将前端锁文件更新写为 `pnpm install --lockfile-only`。
   - 对新 workspace 包的首次使用应修订为 `pnpm install`；否则测试二进制没有链接。

## 5. 恢复开发时的下一步（必须先讨论）

下一小模块是 **Storefront Zustand 内存会话状态**，只创建 `frontend/apps/storefront/src/auth/store.ts` 及对应单元测试；不要同时做登录界面。

恢复会话的目标行为：

1. 应用启动时调用 `AuthClient.refresh()`；
2. 成功时只把 access token 和 `user` 写入 Zustand 内存；
3. 失败时静默落为 `anonymous`，不把 refresh 失败当作页面错误；
4. `acceptAuth()` 接收 register/login 的响应；
5. `clear()` 清空内存身份状态；
6. 不使用 Zustand persist middleware，不读写 Web Storage。

新 Agent 必须先向用户说明并确认以下方案，而不是直接编码：

| 方案 | 结论 | 原因 |
|---|---|---|
| Zustand 全局内存 store（推荐） | 采用 | 项目既定技术栈；Storefront 顶层、登录面板、后续订单/客服页面都可订阅；接口小且可独立测试。 |
| React Context + `useReducer` | 不采用 | 无额外依赖，但每次新增跨页面身份消费都会增加 Provider/Selector 重渲染与样板代码。 |
| TanStack Query 作为唯一身份状态 | 不采用 | 适合服务端缓存，但 access token 是短生命周期本地敏感状态，不宜混为可查询缓存。 |

推荐测试顺序（TDD）：先写“refresh 成功进入 authenticated”的一个 Red 测试，再实现最小 store；随后单独增加“refresh 失败匿名”和“clear 清空 token/user”测试。每个行为单独 Red→Green，定向测试由 Agent 执行。

完成 store 并经用户小模块验收后，才进入下一个小模块：Storefront 登录/注册面板。该 UI 阶段应先做设计说明，采用温暖、编辑感的精品家居风格（纸张/石灰岩色、炭黑正文、暖琥珀点缀），避免泛紫色渐变和模板化 SaaS 卡片。

## 6. 后续身份模块路线

完整实施计划：`docs/superpowers/plans/2026-08-05-identity-tenancy-auth-implementation.md`。

剩余顺序：

1. Storefront Zustand 内存会话状态；
2. Storefront 登录/注册面板、启动恢复、退出和 jsdom 组件测试；
3. 完成 Task 5 的独立 Commit/PR；
4. Console 登录、商家/平台身份展示（Task 6）；
5. 可重复演示种子数据与端到端联调（Task 7）；
6. 再进入商家、商品、库存、订单、策略、知识库、RAG 与 Agent 阶段。

每一个独立、可在 Commit 信息中清楚说明的模块都必须先通过用户参与式验收，再单独 Commit/PR；禁止把不相关功能塞入同一提交。

## 7. 用户协作方式（强约束）

- 全程用中文说明，保留必要的英文术语和代码；用户正在边做边学习。
- 用户自行运行所有 Git、安装及 Docker 状态变更命令。每次需要用户执行命令时，必须写明：**终端目录、命令作用、预期结果**。
- Agent 可以在工作区内读写和执行常规测试，但不要自行执行 Git 命令，也不要读取、输出或改写 `.env` 中的任何真实密钥。
- 每个小模块开始前：说明目标、技术选型理由，并给出 2～3 个备选方案与未选原因；获得用户确认后才能编码。
- Agent 内部完成 Red、定向测试、诊断和代码审查；用户每小模块只做一次集中最终验收，避免反复让用户运行同类命令。
- 用户习惯在提交前执行 `git add .` 与 `git diff --cached --stat`；确认范围后，应直接给出 commit、push、PR 标题与 PR 描述，不要要求无意义的额外 Git 检查。
- 任何新增第三方依赖、版本冲突、Docker 镜像兼容问题，先写入 `findings.md`，解释可选方案并等待用户确认；不要擅自安装或升级。

## 8. 安全与架构红线

- MySQL 是交易、身份、审计真源；Redis 不是库存真源。
- access JWT 只表达用户 ID；商家/平台权限必须每次从数据库实时构造，不能信任 JWT、前端或模型传入的 merchant/role。
- 后续 Agent 工具只能使用服务器注入的可信上下文，不能让模型或请求参数构造 `TenantContext`。
- refresh token 数据库只保存 SHA-256 哈希；原文仅存在 HttpOnly Cookie，禁止日志记录。
- 所有带商家归属的数据访问都必须经 `TenantRepository` + `tenant_scope`；跨商家平台查询必须使用独立 Platform Repository。
- 知识库、RAG、订单、售后开发前必须回看 ADR/规格，尤其是 MySQL 本地 ACID 交易、知识版本激活和策略快照决策。

## 9. 环境与常用验证

基础版本已验证：Python 3.12（uv）、Node 24.14.1、pnpm 11.9.0、Docker Compose 5.1.3。Docker Desktop 已配置 MySQL/Redis/Qdrant/MinIO。

```powershell
# 后端目录：D:\Project\Codex\vibe-coding\backend
uv run pytest -q
uv run ruff check .

# 前端目录：D:\Project\Codex\vibe-coding\frontend
pnpm run test
pnpm run build
pnpm run lint

# 项目根目录：D:\Project\Codex\vibe-coding
.\scripts\verify_stack.ps1
```

只有在用户明确提出上线/部署/发布时，才讨论生产部署。届时必须先确认：`APP_ENV=production`、`APP_DEBUG=false`、`AUTH_COOKIE_SECURE=true`、HTTPS、精确 CORS、生产密钥管理、MySQL 备份恢复、监控告警、镜像 digest 与回滚方案。

## 10. 关键文档索引

- 总计划：`task_plan.md`
- 环境与技术发现：`findings.md`
- 开发/测试日志：`progress.md`
- 总体设计：`docs/superpowers/specs/2026-08-04-multi-merchant-home-rag-agent-design.md`
- 身份与租户规格：`docs/superpowers/specs/2026-08-05-identity-tenancy-auth-design.md`
- 身份实施计划：`docs/superpowers/plans/2026-08-05-identity-tenancy-auth-implementation.md`
- ADR：`docs/adr/0001-authentication-token-and-tenant-isolation.md`、`docs/adr/0002-utc-datetime-persistence.md`

