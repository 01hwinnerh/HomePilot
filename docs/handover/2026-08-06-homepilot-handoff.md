# HomePilot 开发交接文档（2026-08-07）

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

## 3. 已合并模块：Storefront 顾客认证 UI

Storefront 顾客认证 UI PR 已合并。新 Agent **不得自行执行 Git 命令**；由用户在终端确认本地是否已切回并同步 `main`。

共享 `@homepilot/auth-client` 与 Zustand 内存会话状态均已合并；当前分支只完成 Storefront 的认证 UI 闭环：

```text
frontend/apps/storefront/src/
├─ App.tsx
├─ App.test.tsx
├─ styles.css
└─ auth/
   ├─ StorefrontAuthPanel.tsx
   └─ StorefrontAuthPanel.test.tsx
```

页面使用已确认的温暖编辑感视觉：匿名用户可切换登录/注册；应用启动执行 refresh 恢复；认证成功显示邮箱；退出调用后端 logout，并且无论网络请求成功还是失败都会清空 Zustand 内存身份。access token 不落盘。

最终验证：auth-client 2 个测试、Storefront 11 个测试、TypeScript、ESLint 和 Vite production build 均通过；用户已完成集中验收并合并独立 Commit/PR。

## 3.1 已合并的共享 auth-client

已完成并经用户最终验收、现已合并的共享包：

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

不要删除或覆盖用户/平台创建的 `AGENTS.md`。

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

Console 登录、商家/平台身份展示 PR 已合并。当前模块是 **GitHub Actions CI 方案 A**：workflow 已实现并通过本地等价回归，学习材料已生成；用户选择不以复述阻塞流程，现可独立 Commit/PR 并观察首次 GitHub Actions 运行。不要同时开始商品或订单业务。

Console 必须复用 `@homepilot/auth-client`，但独立维护 UI store。它只展示后端 `/me` 返回的邮箱、`memberships` 和平台管理员标识，不能从 JWT 或前端参数伪造商家权限。开始前向用户说明并确认 Console 的界面方案、测试边界和无控制台权限的普通顾客提示策略。

## 6. 后续身份模块路线

完整实施计划：`docs/superpowers/plans/2026-08-05-identity-tenancy-auth-implementation.md`。

剩余顺序：

1. 完成 GitHub Actions CI PR 门禁并合并；
2. 可重复演示种子数据与端到端联调（Task 7）；
3. 再进入商家、商品、库存、订单、策略、知识库、RAG 与 Agent 阶段。

## 6.1 CI 当前状态

`.github/workflows/ci.yml` 已实现：每个指向 `main` 的 PR 运行锁文件安装、后端 pytest/Ruff、前端 test/build/lint；合并到 `main` 后也会留下最终检查记录。首次 PR 发现前端 pnpm 配置错误和后端 MySQL 初始化失败：前端已修复，后端已增加初始化防护与失败日志，等待修复推送后的下一次运行。代码讲解、复述题和参考答案已写入 `.learning/`；用户选择不以复述阻塞 Commit/PR。

每一个独立、可在 Commit 信息中清楚说明的模块都必须先生成完整学习材料，再单独 Commit/PR；用户复述是可选学习环节，禁止把不相关功能塞入同一提交。

## 7. 用户协作方式（强约束）

- 全程用中文说明，保留必要的英文术语和代码；用户正在边做边学习。
- 用户自行运行所有 Git、安装及 Docker 状态变更命令。每次需要用户执行命令时，必须写明：**终端目录、命令作用、预期结果**。
- Agent 可以在工作区内读写和执行常规测试，但不要自行执行 Git 命令，也不要读取、输出或改写 `.env` 中的任何真实密钥。
- 每个小模块都必须走四步学习协议：
  1. **概念课（编码前）**：说明问题、生活化类比、代码语境、推荐方案和 2～3 个未选方案；只有用户明确表示“真的听懂了”后才能编码。
  2. **开发**：采用纵向 TDD；Agent 完成 Red、定向测试、诊断和审查，用户只参与有学习价值的关键边界。
  3. **代码讲解（完成后）**：按“输入/请求 → 处理与决策 → 返回/持久化”讲清数据流，强调安全点和易错点。
  4. **复述材料**：生成 5 题（2 个是什么、2 个为什么、1 个如果……会怎样）和参考答案，连同概念课、代码讲解写入被 `.gitignore` 排除的 `.learning/`；用户可自主复述，但不阻塞提交和后续开发。
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

