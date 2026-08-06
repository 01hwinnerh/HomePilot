# HomePilot 开发进度日志

## 2026-08-04

- `chore/project-scaffold` 已生成工程骨架：后端健康探针与测试、前端两个 Vite 应用、pnpm workspace、Docker Compose、`.env.example` 和无安装的环境检查脚本。
- 已通过 PowerShell 静态解析校验三个 `package.json`；尚未安装依赖，因此未运行后端、前端或 Docker 验证。
- 安装前静态复核已将前端构建命令修正为 `tsc --noEmit`，并补充 ESLint Flat Config 与 Vitest 运行器烟雾测试。
- 已定位并修复 `bootstrap.ps1` 的 Windows PowerShell 5.1 编码兼容问题：所有执行脚本保持 ASCII，避免无 BOM UTF-8 中文解析失败。
- 已修复 `uv sync` 的 Hatchling 可编辑构建失败：明确指定 `app` 为需打包的 Python 目录。
- 用户在 PowerShell 7 中成功执行 `uv sync --all-groups`，创建 `.venv`、生成 `uv.lock`并安装了后端与 Agent/RAG 依赖。
- 后端健康探针测试通过；已根据 Ruff 完整 diff 修正第三方/项目 import 分组与 import 区块后的空行数量。
- 用户复验 `uv run ruff check .` 通过；后端骨架的测试与静态检查已完成。
- 前端首次 `pnpm install` 完成 338 个包的解析；pnpm 阻止了 `esbuild` 安装脚本，已以 `onlyBuiltDependencies` 显式白名单修复。
- 商城与控制台均已通过 TypeScript/Vite 生产构建和 Vitest 烟雾测试。
- 在首次 ESLint 执行前发现 Flat Config 缺少 TS/TSX 解析器，已增加 `typescript-eslint` 和官方推荐规则。
- 用户已完成前端增量依赖安装，并复验 `pnpm run lint` 通过；前端骨架的构建、测试与静态检查全部通过。
- Docker Compose 已启动 MySQL、Redis、Qdrant 和 MinIO；四个服务均通过进程状态和实际连通性验证。

## 2026-08-05

- Task 3 认证服务进入实现与验证阶段：新增注册、登录、refresh 单次轮换、logout、`/me`、CSRF Cookie 和 Redis 固定窗口限流；无新增依赖或版本调整。
- 助手完成服务层与 HTTP 集成 Red→Green。首次 API 集成测试发现迁移 fixture 只定义在旧测试模块内，已提升为 `tests/integration/conftest.py` 的共享 fixture。
- 真实 `homepilot_test` + Redis 定向测试覆盖注册到 `/me`、refresh rotation/重放、CSRF/登出、并发 refresh 单次成功和限流 429。
- 一次后端全量收集遇到 pytest 同名模块冲突；已把单元测试重命名为 `test_auth_rate_limiter.py`，避免与集成测试冲突。
- 最新助手验证将在文档更新后由用户进行业务库迁移与最终回归；本模块尚未 Commit 或创建 PR。
- 提交前只读审查发现 4 项 Important；已按原规格补齐并完成定向回归：refresh token 分桶限流、拒绝路径显式 rollback、`/me` 的启用商家成员列表，以及 Cookie/CSRF、停用/过期会话、并发 refresh 与安全日志脱敏测试。
- 修复过程中，停用用户 refresh 回归暴露 rollback 后读取 ORM `user.id` 会触发 `MissingGreenlet`；现已在 rollback 前保存审计 ID。定向测试通过，等待重新执行全量最终验收。
- 用户已执行审查修订后的业务库迁移、认证定向回归、全量 pytest 与 Ruff；结果均达到预期，全量为 56 passed。当前仅等待复审确认与 Task 3 的独立 Commit/PR。
- 第二轮复审未发现 Critical；补齐剩余日志脱敏测试缺口及两项小型回归后，等待最终全量验证。未新增依赖、迁移或外部配置项。

## 2026-08-06

- Task 5 第一小模块已实现：新增无 React 依赖的 `@homepilot/auth-client`，统一封装 register/login/refresh/logout/me、HttpOnly Cookie 凭据、CSRF 请求头和安全 API 错误。
- 按 TDD 先写 refresh/logout Cookie+CSRF 行为测试；初次运行因新 workspace 包尚未建立依赖链接而无法找到 `vitest`，不是业务测试失败。用户执行普通 `pnpm install` 后已恢复测试环境。
- auth-client 内部验证通过：2 个 Vitest 测试、TypeScript build、ESLint lint 均通过。发现并修正新包 TypeScript 未配置 `skipLibCheck`/`ESNext` 导致的第三方声明类型错误。
- 当前暂停在 auth-client 小模块边界，等待用户确认后再进入 Storefront Zustand 内存会话状态；尚未开始商城 UI。
- 已新增根目录 `HANDOFF.md` 作为恢复开发的显式入口，并在 `AGENTS.md`、`README.md` 中强制/醒目链接；详细交接内容保留在 `docs/handover/2026-08-06-homepilot-handoff.md`。两份文档记录当前已合并能力、auth-client 未提交状态、验证结果、待修订计划项、下一小模块设计选项、协作方式和安全红线。

- Task 3 已合并并同步到干净的 `main`；用户创建 `feat/tenant-context` 后进入 Task 4。
- Task 4 完成首轮 Red→Green：Principal 从服务端 active User 构造、TenantContext 从 active membership/merchant 构造、Tenant/Platform Repository 边界、SQLAlchemy tenant scope 过滤与 FastAPI 认证依赖。
- 集成测试使用真实 `homepilot_test` 验证商家 A 不能建立商家 B Context，且在 tenant scope 内直接 ORM 查询和 Repository 查询都无法读到商家 B 的成员资源；平台管理员独立 Repository 可跨商家列出商家。
- 最新助手验证：后端 `63 passed`，`uv run ruff check .` 通过。等待独立复审后再请求用户进行一次集中最终验收。
- 独立复审发现 3 个 Important：手造 Principal/Context、仅 SELECT 的 scope 过滤、以及依赖链测试不完整。已按 ADR-0001 修订：内部 provenance capability、scope DML 过滤、真实 Bearer→get_tenant_context→403 和 platform dependency 链路测试。定向回归通过，准备最终全量验证。
- 第二轮复审确认无 Critical；补齐 scoped bulk delete、异常 scope reset 与并发 task ContextVar 隔离回归，并在 ADR 中准确记录 capability 的进程内威胁模型边界。等待最终全量验证与最终复审。
- 修订后最终助手验证：`uv run pytest -q` 为 65 passed，`uv run ruff check .` 通过；保留既有 Starlette TestClient 上游弃用警告。

- 认证安全原语 PR 已合并；已从更新后的 `main` 创建 `feat/identity-tenancy-models`，进入 Task 2。
- Task 2 采用纵向 TDD 建立 `User`、`Merchant`、`MerchantMember` 与 `AuthSession`。已验证商家成员联合唯一、`OWNER/STAFF` 角色、refresh token 仅保存哈希、用户/租户/轮换链路外键、关键索引及严格反向迁移。
- 迁移测试曾因开发中扩展未提交 revision `20260805_0002` 而保留不完整 head 状态；已重建隔离库并改造 fixture，使每次测试结束后回滚到 `base` 且断言领域表已清理，后续修改同一未提交 revision 不再污染测试库。
- 两轮独立审查关闭了显式 email 唯一索引、模型/迁移时间类型对齐、外键/角色/Mixin/回滚测试覆盖等问题。
- 审查发现 MySQL `DATETIME` 不保留时区；用户确认 ADR-0002 的 `UTCDateTime` 方案。实现已覆盖 aware 值归一化、naive 输入拒绝、真实 MySQL UTC+08:00 round-trip 与数据库拒绝非法成员角色。
- 最新助手验证：`uv run pytest -q` 为 `41 passed`（保留既有 Starlette TestClient 废弃警告），`uv run ruff check .` 通过，`alembic check` 输出 `No new upgrade operations detected.`。等待用户执行业务库迁移与最终 Green 回归后提交本 Task 的独立 PR。

- 用户确认认证运行时依赖并完成 `uv sync --all-groups`；锁文件固定 `argon2-cffi 25.1.0`、`email-validator 2.3.0` 和 `PyJWT 2.13.0`。
- 认证配置与安全原语按垂直 TDD 完成：Argon2 密码哈希、HS256 access JWT、opaque refresh/CSRF token、CSRF 常量时间比较、JWT 篡改/类型拒绝、精确 CORS、Cookie 安全开关、时长边界、Redis 地址和限流配置。
- 用户已在本地 `.env` 设置 `AUTH_JWT_SECRET`；助手未读取该值。`.env.example` 仅含安全占位符和开发默认值。
- 用户与助手均完成认证定向回归；最新后端全量验证为 `26 passed`，Ruff 为 `All checks passed!`。FastAPI/Starlette 的既存 TestClient 废弃警告保留，未混入本模块处理。
- 认证安全原语模块待用户手动 Commit 和 GitHub PR；在此之前不开始身份数据模型和 Alembic 迁移。

- 数据库基础层 PR 已合并至 `main`，本地工作区已同步且干净。
- 用户确认身份、认证、RBAC 与租户隔离设计：顾客自助注册；商家成员/平台管理员由种子数据创建；采用内存 access JWT、HttpOnly rotating refresh Cookie 和 CSRF 防护。
- 已新增身份认证设计规格与 ADR；尚未修改认证代码、数据库迁移或依赖声明，下一步是让用户审阅规格后编写实施计划。
- 用户已确认身份认证规格；已完成对应的细化 TDD 实施计划。计划把依赖确认设置为 Task 1 的硬门槛，并将模型、认证 API、租户隔离、商城登录、控制台登录和最终联调拆分为独立 Commit/PR 边界。

- 已将实际拉取并通过健康验证的 Qdrant/MinIO 镜像 digest 写入 `.env.example`，防止 `latest` 标签漂移。
- 已同步本地 `.env` 的两个镜像变量，未读取或修改 API Key。
- 已新增 ASCII PowerShell 全量验证脚本 `scripts/verify_stack.ps1`，覆盖后端、前端和 Docker 基础设施。
- 用户已成功执行 `scripts/verify_stack.ps1`：后端 pytest/Ruff、前端 build/Vitest/ESLint、Compose 配置及四个基础服务连通性全部通过。
- `chore/project-scaffold` 实施与验证已完成，待用户手动 Commit 并创建 GitHub PR。
- PR #1 已合并到 `main`，本地 `main` 已同步，旧工程骨架分支已删除。
- 已创建 `feat/database-foundation` 分支，数据库基础层进入 TDD Red 阶段。
- 数据库基础层 Red 测试按预期因 `app.core.database` 与 `app.shared.models` 未实现而失败。
- 已实现 Green 最小代码：数据库 URL Settings、异步 Engine/Session 封装与 SQLAlchemy Base 命名约定。
- `uv run pytest tests/unit -q` 连续两次通过（4 passed），数据库基础层 TDD Green 阶段完成。
- Ruff 首次检查发现 3 处 import 格式问题：两处多余空行与一处同行 import 名称顺序，已按诊断修正。
- 用户复验 `uv run ruff check .`，输出 `All checks passed!`；数据库基础层单元测试与静态检查均已通过，开始 Alembic + MySQL 集成阶段。
- 数据库集成 TDD 第一个 Red 切片已加入：`test_test_database_accepts_queries` 明确使用 `TEST_DATABASE_URL` 连接隔离测试库；尚未创建测试库，等待用户运行以确认预期失败。
- 用户运行数据库连接 Red，确认失败为 MySQL `1044 Access denied`；已增加测试库配置、最小权限初始化脚本及 Docker init 挂载，下一步只需为既有 volume 执行一次初始化并复验 Green。
- 用户已重新加载 MySQL Compose 配置，并成功执行测试库初始化脚本；终端仅出现 MySQL 命令行密码提示警告，无执行错误。
- 数据库连接 Green 复验两次均推进到 MySQL `caching_sha2_password` 认证后失败；已确认根因是后端未声明 `cryptography`，依赖变更按约定暂停并等待用户确认。
- 用户确认采用现代 MySQL 认证兼容方案；已在后端运行时依赖中声明 `cryptography>=44,<47`，等待用户通过 uv 更新锁文件和虚拟环境。
- 用户已成功同步后端环境：安装 `cryptography==46.0.7`，并重新安装本地 editable `homepilot-api`；准备复验数据库真实连接 Green。
- 助手复验数据库真实连接 Green 通过（`1 passed`）；已加入 Alembic `upgrade head` 集成测试，开始异步迁移基线 Red→Green 切片。
- Alembic 测试先按预期因缺少 `script_location` 失败；补齐异步 `env.py`、配置、迁移模板和空基线 revision 后复验通过，测试库当前 revision 为 `20260805_0001`。
- 数据库事务异常回滚集成测试通过；首次后端回归发现两处 Alembic import 分组格式问题，已按 Ruff 确定输出修正。
- 修正 import 后，后端全量 `8 passed`、Ruff `All checks passed`。
- 项目级 `scripts/verify_stack.ps1` 回归通过：后端、两个前端的 build/Vitest/ESLint，以及 MySQL、Redis、Qdrant、MinIO 连通性全部正常。
- 已补充后端配置、测试库初始化、Alembic 使用和验证文档，并同步数据库基础层计划勾选项。
- 用户已将本地业务库升级到 `20260805_0001`；助手复验 `alembic current` 显示 `20260805_0001 (head)`。
- 提交前独立审查发现 1 个 Critical 和 2 个 Important：测试库误配保护不足、迁移测试可能假阳性、测试库名称硬编码与配置冲突。
- 已完成审查修复：统一测试库隔离校验及 3 个单元测试、所有集成测试复用安全 fixture、迁移测试先降至 base、Docker 初始化脚本拒绝同名/无 test 标识，并在全量脚本中验证拒绝分支。
- 审查修复的定向验证已通过：安全单元测试 3 passed、数据库集成测试 3 passed、Ruff 通过、容器同名库保护按预期拒绝。
- 审查修复后项目级全量回归通过：后端 11 passed、Ruff 通过、前端 build/Vitest/ESLint 通过、四个 Docker 服务连通；独立复审确认无剩余 Critical/Important，可进入 Commit/PR。

- 完成架构、业务边界、租户安全、库存策略、策略快照、RAG 版本治理、Agent 人工接管和评测方案确认。
- 用户确认 Python 通过 uv 管理，不覆盖 Anaconda Python 3.11。
- 用户确认默认模型为 DeepSeek `deepseek-v4-flash`，模型与 API 地址均集中由 `.env` 和 Typed Settings 管理。
- 用户确认后续所有安装命令和 Git 命令自行在终端执行；助手只提供目录、命令和预期结果。
- 用户已手动完成 `uv python install 3.12`。
- 已创建项目级计划与进度追踪文档；阶段 0 保持进行中，等待依赖版本矩阵确认。
- 用户确认采用“稳定大版本 + 锁文件固定精确版本”的依赖策略。
- 用户要求每个独立模块完成后，先手动 Commit 并创建/更新 GitHub PR；该规则已写入项目计划。
