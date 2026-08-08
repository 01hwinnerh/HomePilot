# 身份认证与多租户隔离实施计划

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 为 HomePilot 建立可撤销的登录会话、顾客自助注册、商家/平台 RBAC 与不可伪造的租户数据访问边界，并完成两个前端的最小登录闭环。

**Architecture:** FastAPI 以短期 HS256 JWT 作为 API access token，以数据库中的 `AuthSession` 保存 refresh token 哈希、过期和撤销链路。每个商家操作通过数据库中的 `MerchantMember` 关系创建 `TenantContext`；普通租户 Repository 与平台 Repository 完全分离。两个 React 应用共享一个轻量 auth client，access token 只保存在 Zustand 内存，刷新页面时经 HttpOnly refresh Cookie 恢复。

**Tech Stack:** Python 3.12、FastAPI、Pydantic v2、SQLAlchemy 2 异步 ORM、Alembic、MySQL 8.4、Redis 7.4、PyJWT、argon2-cffi、React 19、TypeScript、Zustand、Vite、Vitest、pytest。

---

## 0. 实施边界、顺序与提交规则

1. 认证安全原语当前在 `feat/identity-tenancy-auth` 分支实施。每个 Task 必须各自创建独立 PR 并合并：Task 1 合并后删除当前分支，Task 2 从更新的 `main` 新建 `feat/identity-tenancy-models`，Task 3 为 `feat/auth-session-api`，Task 4 为 `feat/tenant-context`，Task 5 为 `feat/storefront-auth`，Task 6 为 `feat/console-auth`，Task 7 为 `test/identity-demo-seed`。
2. Task 1 的依赖是硬门槛：在用户明确同意包名和版本范围前，不得编辑 `backend/pyproject.toml`，不得运行 `uv sync`。
3. 每个 Task 完成后，先运行该 Task 的回归命令，再由用户手动 Commit、创建独立 GitHub PR 并合并；随后切回 `main`、快进同步、删除已合并本地分支并创建下一 Task 的分支。后续 Task 不得混入上一个 Task 的未提交改动。
4. 按既定协作规则，助手执行预期失败的 Red/诊断；用户执行 Green、集成回归、Docker 状态变更、安装和所有 Git 命令。每条给用户的命令都要注明目录、作用和预期输出。
5. 本计划不实现商品、订单、入驻审核、成员邀请、密码找回、邮件验证、OAuth、MFA 或真实支付。

## 1. 文件结构与职责

| 路径 | 职责 |
|---|---|
| `backend/app/core/config.py` | 认证、Cookie、CORS、Redis 限流的集中 Typed Settings。 |
| `backend/app/core/database.py` | 应用级 `Database` 和 FastAPI session dependency，不放身份业务规则。 |
| `backend/app/core/redis.py` | 可关闭/可替换的异步 Redis client 生命周期。 |
| `backend/app/core/security.py` | Argon2 密码哈希、JWT 签发/校验、opaque refresh/CSRF token 生成与哈希。 |
| `backend/app/shared/models/base.py` | 现有 SQLAlchemy Base；不在此文件堆放领域模型。 |
| `backend/app/shared/models/tenant.py` | 含 `merchant_id` 的租户归属 mixin，供 Session 二次过滤和后续商家资源继承。 |
| `backend/app/shared/tenancy/context.py` | `Principal`、`TenantContext`、成员角色和平台身份类型。 |
| `backend/app/shared/tenancy/session.py` | 受控的 `ContextVar` tenant scope 与 `with_loader_criteria` Session 二次过滤。 |
| `backend/app/shared/tenancy/repositories.py` | 强制 `TenantContext` 的通用租户查询基类；不提供跳过过滤的选项。 |
| `backend/app/modules/identity/models.py` | `User`、`AuthSession` ORM 模型。 |
| `backend/app/modules/identity/schemas.py` | 注册、登录、当前用户和 token 响应的 Pydantic schema。 |
| `backend/app/modules/identity/service.py` | 注册、登录、refresh rotation、logout 与安全事件的事务编排。 |
| `backend/app/modules/identity/security_events.py` | 仅含脱敏字段的结构化认证/越权安全事件。 |
| `backend/app/modules/merchants/models.py` | `Merchant`、`MerchantMember` ORM 模型。 |
| `backend/app/modules/merchants/repositories.py` | 明确 tenant/platform 边界的商家查询实现。 |
| `backend/app/api/v1/auth.py` | 五个认证 HTTP 接口与 Cookie 写入/清理。 |
| `backend/app/api/v1/dependencies.py` | Bearer 认证、平台管理员校验、租户上下文构建依赖。 |
| `backend/app/api/v1/router.py` | 统一挂载 v1 路由，不让 `main.py` 直接包含领域路由。 |
| `backend/alembic/versions/20260805_0002_identity_and_tenancy.py` | 用户、会话、商家和成员的可逆迁移。 |
| `backend/tests/unit/...` | 安全工具、schema、服务和租户边界的无网络/无真实 MySQL 测试。 |
| `backend/tests/integration/...` | MySQL 迁移、真实事务、HTTP Cookie/CSRF/rotation 与 Redis 限流测试。 |
| `frontend/packages/auth-client/` | 共享的认证 HTTP 客户端和 Cookie/CSRF 读取；Zustand store 保持在各应用内。 |
| `frontend/apps/storefront/src/` | 顾客注册、登录、身份摘要和退出。 |
| `frontend/apps/console/src/` | 商家/平台登录、身份摘要、可访问商家列表和退出。 |
| `.env.example` | 变量名与非敏感示例；绝不放真实 JWT 或 API 密钥。 |

## 2. Task 1：依赖确认、配置契约与安全工具

**目的：** 先建立所有认证模块共同使用的配置和纯安全函数；不建立数据库表或路由。

**TDD 执行细化：** 本任务列出的密码、JWT、refresh token、CSRF 与 Settings 行为按“一个行为 → Red → 最小 Green”垂直切片实现，不把所有失败测试一次性写完。每一轮 Green 都只运行当前测试与既有相关测试；全部行为完成后再运行本 Task 的完整回归。

**文件：**

- 修改：`backend/pyproject.toml`
- 修改：`backend/uv.lock`（只由用户执行 `uv sync --all-groups` 生成）
- 修改：`backend/app/core/config.py`
- 新建：`backend/app/core/security.py`
- 新建：`backend/tests/unit/test_security.py`
- 修改：`backend/tests/unit/test_database_settings.py`
- 修改：`.env.example`
- 修改：`backend/README.md`
- 修改：`findings.md`、`progress.md`、`task_plan.md`

- [x] **Step 1: 先进行依赖确认，停止编码等待用户答复。**

  向用户说明当前 `pyproject.toml` 没有直接声明认证所需包，建议加入以下运行时依赖；Redis client 已存在，不新增限流第三方库：

  ```toml
  "argon2-cffi>=25,<26",
  "email-validator>=2.2,<3",
  "PyJWT>=2.10,<3",
  ```

  同时建议为两个 React 应用分别加入仅测试使用的 `@testing-library/react>=16,<17` 与 `jsdom>=26,<28`，使组件测试能在模拟浏览器 DOM 中验证登录表单和页面刷新状态；它们不会被 Vite 生产构建打入用户代码。

  说明用途：`argon2-cffi` 用于密码哈希，`email-validator` 支持 Pydantic `EmailStr`，`PyJWT` 用于 HS256 access token，前端两个包只用于测试。询问用户确认后才进入 Step 2；若实际锁定版本与已有 Python 3.12、FastAPI/Pydantic、React 19/Vitest 组合不兼容，记录到 `findings.md` 并再次等待用户选择。

- [x] **Step 2: 助手编写安全工具的 Red 单元测试。**

  在 `test_security.py` 写出以下可独立验证的行为，使用固定 Settings/密钥而不读取用户 `.env`：

  ```python
  def test_password_hash_never_equals_plaintext() -> None:
      password_hash = hash_password("correct horse battery staple")
      assert password_hash != "correct horse battery staple"
      assert verify_password("correct horse battery staple", password_hash) is True
      assert verify_password("incorrect", password_hash) is False

  def test_access_token_requires_access_type_and_valid_signature() -> None:
      token = create_access_token(user_id=42, settings=auth_settings)
      assert decode_access_token(token, settings=auth_settings).user_id == 42
      with pytest.raises(InvalidAccessToken):
          decode_access_token(create_refresh_like_jwt(), settings=auth_settings)
  ```

  同时在 `test_database_settings.py` 扩展 Settings 测试，断言 `auth_access_token_minutes == 15`、`auth_refresh_token_days == 7`、本地 `auth_cookie_secure is False`，并验证逗号分隔的 CORS origin 被解析为精确列表。

- [x] **Step 3: 助手运行 Red 并记录失败原因。**

  在 `backend` 目录运行：

  ```powershell
  uv run pytest tests/unit/test_security.py tests/unit/test_database_settings.py -q
  ```

  预期在 `app.core.security` 尚不存在或函数未定义时失败；该失败由助手诊断，不要求用户手动重复执行。

- [x] **Step 4: 用户确认依赖后，声明直接依赖并同步锁文件。**

  助手只用补丁把三个已确认的版本范围写入 `backend/pyproject.toml`，不手工编辑 `uv.lock`。用户在 **`D:\Project\Codex\vibe-coding\backend`** 终端执行：

  ```powershell
  uv sync --all-groups
  ```

  此命令将依据已确认的范围更新项目虚拟环境和 `uv.lock`；预期输出包含新增/确认的认证包且命令以退出码 0 结束。若解析提示版本冲突，停止，不尝试替换版本。

- [x] **Step 5: 实现集中认证 Settings 与 `.env.example`。**

  在 `Settings` 中增加并只从 `.env` 读取以下字段：

  ```python
  backend_cors_origins: Annotated[list[str], NoDecode] = ["http://localhost:5173", "http://localhost:5174"]
  redis_url: str = "redis://127.0.0.1:6379/0"
  auth_jwt_secret: SecretStr
  auth_jwt_issuer: str = "homepilot-api"
  auth_jwt_algorithm: Literal["HS256"] = "HS256"
  auth_access_token_minutes: int = Field(default=15, ge=1, le=60)
  auth_refresh_token_days: int = Field(default=7, ge=1, le=30)
  auth_cookie_secure: bool = False
  auth_cookie_same_site: Literal["lax"] = "lax"
  auth_rate_limit_enabled: bool = True
  auth_rate_limit_max_attempts: int = Field(default=5, ge=1, le=100)
  auth_rate_limit_window_seconds: int = Field(default=900, ge=1, le=3600)
  ```

  从 `pydantic_settings` 导入 `NoDecode`，并为 CORS 使用 `field_validator(..., mode="before")`：当环境变量是 `http://localhost:5173,http://localhost:5174` 时返回去除空白和空项的列表。`.env.example` 增加 `AUTH_JWT_SECRET=replace-with-a-local-random-secret` 等变量名及中文说明；不写真实密钥。用户在自己未提交的 `.env` 填入随机 secret。生成方式由用户在 **`backend`** 目录执行：

  ```powershell
  uv run python -c "import secrets; print(secrets.token_urlsafe(48))"
  ```

  预期输出一行随机字符串；用户复制到 `.env` 的 `AUTH_JWT_SECRET=` 后面，且不提交该文件。

- [x] **Step 6: 实现 `security.py` 的最小纯函数。**

  使用 `argon2.PasswordHasher`，并将验证失败转换为 `False`；使用 `secrets.token_urlsafe(48)` 生成 refresh token、`secrets.token_urlsafe(32)` 生成 CSRF token；使用 SHA-256 十六进制摘要保存 refresh token；使用 `hmac.compare_digest` 比较 CSRF。JWT payload 和解码接口固定如下：

  ```python
  @dataclass(frozen=True)
  class AccessTokenClaims:
      user_id: int
      token_id: str

  def create_access_token(*, user_id: int, settings: Settings, now: datetime | None = None) -> str: ...
  def decode_access_token(token: str, *, settings: Settings, now: datetime | None = None) -> AccessTokenClaims: ...
  def hash_refresh_token(token: str) -> str: ...
  def csrf_tokens_match(cookie_value: str | None, header_value: str | None) -> bool: ...
  ```

  `decode_access_token` 必须验证签名、算法、issuer、`typ == "access"` 和过期时间；任何 JWT 库异常统一转换为不包含 token 内容的 `InvalidAccessToken`。

- [x] **Step 7: 用户执行 Green 单元回归。**

  在 **`D:\Project\Codex\vibe-coding\backend`** 执行：

  ```powershell
  uv run pytest tests/unit/test_security.py tests/unit/test_database_settings.py -q
  uv run ruff check .
  ```

  第一个命令验证密码、JWT、token 哈希、CSRF 和 Settings；预期全部通过。第二个命令验证导入和静态规则；预期 `All checks passed!`。

- [ ] **Step 8: 更新文档并由用户提交独立 Commit/PR。**

  `findings.md` 记录实际解析版本，`progress.md` 记录测试结果，`task_plan.md` 勾选本任务。用户确认工作区只包含本 Task 文件后，在项目根目录执行：

  ```powershell
  git add backend/pyproject.toml backend/uv.lock backend/app/core/config.py backend/app/core/security.py backend/tests/unit/test_security.py backend/tests/unit/test_database_settings.py .env.example backend/README.md findings.md progress.md task_plan.md
  git commit -m "feat(auth): add security configuration and token primitives"
  git push -u origin feat/identity-tenancy-auth
  ```

  作用：提交可独立复用的认证基础。预期 commit 成功并将当前分支推送到远程；随后用户在 GitHub 为该分支创建独立 PR，合并后再开始 Task 2。

## 3. Task 2：身份、商家与会话持久化模型

**目的：** 用可逆 Alembic 迁移建立用户、商家、商家成员和 refresh session 真源；本任务不暴露 HTTP 登录接口。

**文件：**

- 新建：`backend/app/modules/__init__.py`
- 新建：`backend/app/modules/identity/__init__.py`
- 新建：`backend/app/modules/identity/models.py`
- 新建：`backend/app/modules/merchants/__init__.py`
- 新建：`backend/app/modules/merchants/models.py`
- 新建：`backend/app/shared/models/tenant.py`
- 新建：`backend/app/shared/models/utc_datetime.py`
- 修改：`backend/app/shared/models/__init__.py`
- 修改：`backend/alembic/env.py`
- 新建：`backend/alembic/versions/20260805_0002_identity_and_tenancy.py`
- 新建：`backend/tests/unit/test_identity_models.py`
- 新建：`backend/tests/unit/test_utc_datetime.py`
- 新建：`backend/tests/integration/test_identity_migration.py`
- 修改：`backend/tests/integration/conftest.py`
- 修改：`progress.md`、`task_plan.md`

> **已批准架构补充（2026-08-05）：** MySQL `DATETIME` 不持久化时区。Task 2 先按 `docs/adr/0002-utc-datetime-persistence.md` 实现 `UTCDateTime` 与 `utc_now()`：领域层只使用 aware UTC，写入时转换为 UTC-naive，读取时恢复 aware UTC，拒绝 naive 输入；共享时间戳使用 Python 默认值，不依赖 MySQL `CURRENT_TIMESTAMP`。该补充不新增依赖，作为本 Task 的一部分随同提交。

- [x] **Step 1: 助手写模型和迁移的 Red 测试。**

  `test_identity_models.py` 断言以下结构存在且约束可表达：

  ```python
  def test_membership_has_unique_user_and_merchant_constraint() -> None:
      constraint_columns = unique_constraint_columns(MerchantMember.__table__)
      assert {"user_id", "merchant_id"} in constraint_columns

  def test_auth_session_never_exposes_plain_refresh_token_column() -> None:
      assert "refresh_token_hash" in AuthSession.__table__.c
      assert "refresh_token" not in AuthSession.__table__.c
  ```

  集成测试先 `downgrade base → upgrade head`，再检查四张表和关键索引：`users.email` 唯一、`merchant_members(user_id, merchant_id)` 唯一、`auth_sessions.refresh_token_hash` 唯一、`auth_sessions.user_id` 索引。

- [x] **Step 2: 助手运行 Red。**

  在 `backend` 目录执行：

  ```powershell
  uv run pytest tests/unit/test_identity_models.py tests/integration/test_identity_migration.py -q
  ```

  预期因领域模型和 revision `20260805_0002` 尚不存在而失败；助手记录精确失败，不要求用户执行。

- [x] **Step 3: 实现 ORM 模型。**

  使用 `Mapped` 和 `mapped_column`，所有 ID 首版使用自增整数；模型最小定义必须满足：

  ```python
  class MerchantMemberRole(StrEnum):
      OWNER = "OWNER"
      STAFF = "STAFF"

  class User(Base):
      __tablename__ = "users"
      id: Mapped[int] = mapped_column(primary_key=True)
      email: Mapped[str] = mapped_column(String(320), unique=True, index=True)
      password_hash: Mapped[str] = mapped_column(String(255))
      is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
      is_platform_admin: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)

  class AuthSession(Base):
      __tablename__ = "auth_sessions"
      id: Mapped[int] = mapped_column(primary_key=True)
      user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), index=True)
      refresh_token_hash: Mapped[str] = mapped_column(String(64), unique=True)
      expires_at: Mapped[datetime]
      revoked_at: Mapped[datetime | None]
      revoked_reason: Mapped[str | None] = mapped_column(String(32))
      replaced_by_session_id: Mapped[int | None] = mapped_column(ForeignKey("auth_sessions.id"))
  ```

  `Merchant` 至少含 `id`、`name`、`is_active`；`MerchantMember` 含 `id`、`user_id`、`merchant_id`、`role`、`is_active` 及联合唯一约束。`MerchantMember` 继承 `MerchantOwnedMixin`，该 mixin 只声明 `merchant_id: Mapped[int]`，让后续每个商家资源可加入同一 Session 二次过滤。为 `created_at`/`updated_at` 建立一个明确的可复用 mixin，不能把时间戳复制到四个模型。将模型导入 Alembic metadata 加载路径，确保自动/运行迁移都能发现表。

- [x] **Step 4: 编写可逆迁移。**

  revision `20260805_0002` 的 `upgrade()` 依次创建 `users`、`merchants`、`merchant_members`、`auth_sessions`，外键引用已创建表；`downgrade()` 必须按反向依赖顺序删除 `auth_sessions`、`merchant_members`、`merchants`、`users`。使用已存在的命名约定生成约束名，不手写数据库方言专属名称。

- [ ] **Step 5: 用户执行迁移和 Green 回归。**

  在 **`D:\Project\Codex\vibe-coding\backend`** 执行：

  ```powershell
  uv run alembic upgrade head
  uv run pytest tests/unit/test_identity_models.py tests/integration/test_identity_migration.py tests/integration/test_migrations.py -q
  uv run ruff check .
  ```

  第一个命令把本地业务库升级至新增 revision；预期显示 `20260805_0002 ...`。第二个命令只使用 `homepilot_test` 验证迁移可从 base 重建并检查约束；预期通过。第三个命令预期通过。

- [ ] **Step 6: 用户提交模型/迁移 Commit/PR。**

  在项目根目录执行：

  ```powershell
  git add backend/app/modules backend/app/shared/models/tenant.py backend/app/shared/models/__init__.py backend/alembic/env.py backend/alembic/versions/20260805_0002_identity_and_tenancy.py backend/tests/unit/test_identity_models.py backend/tests/integration/test_identity_migration.py backend/tests/integration/conftest.py progress.md task_plan.md
  git commit -m "feat(identity): add users merchants and auth sessions"
  git push
  ```

  作用：把可迁移的身份和租户数据结构作为独立模块交付；预期提交和 push 成功，并创建独立 PR。

## 4. Task 3：认证服务、Cookie/CSRF API 与 Redis 限流

**目的：** 实现顾客注册/登录、`/refresh`、`/logout`、`/me`，保证 refresh 单次轮换、Cookie 安全属性和统一错误语义。

**文件：**

- 新建：`backend/app/core/redis.py`
- 修改：`backend/app/core/database.py`
- 新建：`backend/app/modules/identity/schemas.py`
- 新建：`backend/app/modules/identity/service.py`
- 新建：`backend/app/modules/identity/security_events.py`
- 新建：`backend/app/modules/identity/rate_limit.py`
- 新建：`backend/app/api/__init__.py`
- 新建：`backend/app/api/v1/__init__.py`
- 新建：`backend/app/api/v1/auth.py`
- 新建：`backend/app/api/v1/router.py`
- 修改：`backend/app/main.py`
- 新建：`backend/tests/unit/test_auth_service.py`
- 新建：`backend/tests/integration/test_auth_api.py`
- 新建：`backend/tests/integration/test_auth_rate_limit.py`
- 修改：`backend/tests/integration/conftest.py`
- 修改：`progress.md`、`task_plan.md`

- [x] **Step 1: 助手写服务层 Red 测试。**

  使用 fake session/repository 与固定时钟验证事务规则，不使用真实 Cookie：

  ```python
  @pytest.mark.asyncio
  async def test_rotate_refresh_token_revokes_old_session_and_creates_new_one() -> None:
      old_session = make_active_session(token_hash=hash_refresh_token("old-token"))
      result = await auth_service.rotate_refresh_token("old-token", now=NOW)
      assert old_session.revoked_reason == "rotated"
      assert result.refresh_token != "old-token"
      assert result.session.replaced_by_session_id is None

  @pytest.mark.asyncio
  async def test_login_hides_whether_email_exists() -> None:
      with pytest.raises(InvalidCredentials) as missing:
          await auth_service.login(email="missing@example.com", password="bad")
      with pytest.raises(InvalidCredentials) as incorrect:
          await auth_service.login(email="known@example.com", password="bad")
      assert str(missing.value) == str(incorrect.value)
  ```

  增加测试：注册 email 规范化、重复邮箱拒绝、禁用用户拒绝、refresh 过期/已撤销拒绝、refresh 并发只有一次成功、logout 仅撤销当前 session。

- [x] **Step 2: 助手写 HTTP/API Red 测试。**

  集成测试通过真实 `homepilot_test` 与 `TestClient`/HTTPX ASGI client 验证：

  ```python
  response = client.post("/api/v1/auth/register", json={"email": "buyer@example.com", "password": "safe-password-123"})
  assert response.status_code == 201
  assert response.json()["access_token"]
  assert "HttpOnly" in response.headers["set-cookie"]
  assert "refresh_token=" in response.headers["set-cookie"]

  refresh = client.post("/api/v1/auth/refresh", headers={"X-CSRF-Token": csrf_cookie})
  assert refresh.status_code == 200
  assert client_with_old_cookie.post("/api/v1/auth/refresh", headers={"X-CSRF-Token": old_csrf}).status_code == 401
  ```

  另写 `GET /me` 的 401/200、login 统一 401、refresh/logout 缺失或错误 CSRF 的 403、logout 后 refresh 401、`Secure` 配置变化、以及 Redis 达到阈值返回 429 的测试。测试数据通过 fixture 清理，禁止触碰业务库。使用 `caplog` 增加安全事件测试，确认事件只带 `event`、`result`、`user_id`、`session_id`、`request_id`、`failure_reason` 等脱敏键，且日志文本不包含密码、JWT、refresh token、Cookie 或 Authorization header。

- [x] **Step 3: 助手运行 Red 并检查失败属于缺失实现。**

  在 `backend` 目录执行：

  ```powershell
  uv run pytest tests/unit/test_auth_service.py tests/integration/test_auth_api.py tests/integration/test_auth_rate_limit.py -q
  ```

  预期失败于 service/router 尚不存在；如失败是测试库、Docker 或缺少用户配置，先修复环境问题并记录，不能把环境故障当作业务 Red。

- [x] **Step 4: 实现应用依赖与认证服务。**

  `database.py` 增加缓存的 `get_database()` 与 `async def get_db_session() -> AsyncIterator[AsyncSession]`，将每次 HTTP 请求的 session 关闭责任放在 dependency。`redis.py` 提供 `get_redis()`，用 `redis.asyncio.from_url(settings.redis_url, decode_responses=True)` 创建客户端，并在 FastAPI lifespan 关闭。

  `AuthService` 的公开接口固定为：

  ```python
  class AuthService:
      async def register(self, *, email: str, password: str) -> AuthResult: ...
      async def login(self, *, email: str, password: str) -> AuthResult: ...
      async def refresh(self, *, refresh_token: str, now: datetime) -> AuthResult: ...
      async def logout(self, *, refresh_token: str, now: datetime) -> None: ...
      async def current_user(self, *, user_id: int) -> User: ...
  ```

  `refresh()` 用 `SELECT ... FOR UPDATE` 读取 refresh token 哈希对应的 session，并在一个 commit 内填入旧 `revoked_at`/`revoked_reason="rotated"`、创建新 session、写回 `replaced_by_session_id`。任何失败必须 rollback；不记录原始 token。`AuthRateLimiter` 以 `INCR` + 首次 `EXPIRE` 实现固定窗口，Redis key 只保存 SHA-256 后的 IP/邮箱组合，不保存明文邮箱。`security_events.py` 只允许以下事件名：`auth.registered`、`auth.login_succeeded`、`auth.login_failed`、`auth.refresh_succeeded`、`auth.refresh_rejected`、`auth.logout`、`auth.user_inactive`、`tenancy.access_denied`；所有事件通过 `logger.info("security_event", extra={"security_event": payload})` 发出。

- [x] **Step 5: 实现 schema、路由和 Cookie 处理。**

  schema 最小结构：

  ```python
  class RegisterRequest(BaseModel):
      email: EmailStr
      password: Annotated[str, Field(min_length=12, max_length=128)]

  class LoginRequest(BaseModel):
      email: EmailStr
      password: Annotated[str, Field(min_length=1, max_length=128)]

  class AuthResponse(BaseModel):
      access_token: str
      token_type: Literal["bearer"] = "bearer"
      user: CurrentUserResponse
  ```

  每次成功注册/登录/refresh 调用同一个 `set_auth_cookies(response, refresh_token, csrf_token, settings)`；它设置 refresh 的 `httponly=True` 和 CSRF 的 `httponly=False`，两者 `samesite="lax"`、相同 path 和配置化 secure。`require_csrf()` 只在 cookie/header 都存在且 `csrf_tokens_match` 时通过。认证失败响应固定为 `{"detail": "Invalid credentials"}`，不含底层异常。`main.py` 用 `CORSMiddleware` 挂载明确 origins、`allow_credentials=True`，并挂载 `api_v1_prefix` 下的 auth router。

- [x] **Step 6: 用户执行 Green、数据库迁移和小型后端回归。**

  在 **`D:\Project\Codex\vibe-coding\backend`** 执行：

  ```powershell
  uv run alembic upgrade head
  uv run pytest tests/unit/test_security.py tests/unit/test_auth_service.py tests/integration/test_auth_api.py tests/integration/test_auth_rate_limit.py -q
  uv run pytest -q
  uv run ruff check .
  ```

  作用依次为升级本地表、验证认证关键路径、执行后端小型全量回归、检查静态规范。预期全部通过；如果 Redis 连接失败，保留容器运行状态并检查连接配置，不绕过限流测试。

- [ ] **Step 7: 用户提交认证后端 Commit/PR。**

  在项目根目录执行：

  ```powershell
  git add backend/app/core/database.py backend/app/core/redis.py backend/app/modules/identity backend/app/api backend/app/main.py backend/tests/unit/test_auth_service.py backend/tests/integration/test_auth_api.py backend/tests/integration/test_auth_rate_limit.py backend/tests/integration/conftest.py progress.md task_plan.md
  git commit -m "feat(auth): add rotating session authentication API"
  git push
  ```

  作用：提交完整、可独立验证的顾客认证 API。预期 push 成功，并创建独立 PR。

## 5. Task 4：Principal、TenantContext 与 Repository 硬隔离

**目的：** 不信任 JWT/前端给出的 merchant 信息；从数据库关系构造租户上下文，并使平台跨租户查询走独立入口。

**文件：**

- 新建：`backend/app/shared/tenancy/__init__.py`
- 新建：`backend/app/shared/tenancy/context.py`
- 新建：`backend/app/shared/tenancy/session.py`
- 新建：`backend/app/shared/tenancy/repositories.py`
- 新建：`backend/app/modules/merchants/repositories.py`
- 新建：`backend/app/api/v1/dependencies.py`
- 修改：`backend/app/api/v1/auth.py`
- 新建：`backend/tests/unit/test_tenant_context.py`
- 新建：`backend/tests/unit/test_tenant_repositories.py`
- 新建：`backend/tests/integration/test_tenant_isolation.py`
- 修改：`progress.md`、`task_plan.md`

- [x] **Step 1: 助手写越权 Red 测试。**

  用商家 A/B、成员 A、成员 B 和平台管理员建立数据，验证如下断言：

  ```python
  @pytest.mark.asyncio
  async def test_member_cannot_build_context_for_another_merchant() -> None:
      with pytest.raises(TenantAccessDenied):
          await tenant_context_factory.for_merchant(principal=member_a, merchant_id=merchant_b.id)

  @pytest.mark.asyncio
  async def test_tenant_repository_always_filters_by_context_merchant() -> None:
      result = await repository.get_by_id(context=merchant_a_context, resource_id=merchant_b_resource.id)
      assert result is None

  def test_platform_repository_requires_platform_principal() -> None:
      with pytest.raises(PlatformAccessDenied):
          PlatformMerchantRepository(principal=merchant_member)
  ```

  集成测试不得靠“前端隐藏按钮”证明安全性，而应直接验证商家 A 的认证 token 无法获取商家 B 的 `TenantContext`，且平台管理员在普通 tenant repository 中也没有 bypass 方法。

- [x] **Step 2: 助手运行 Red。**

  在 `backend` 目录执行：

  ```powershell
  uv run pytest tests/unit/test_tenant_context.py tests/unit/test_tenant_repositories.py tests/integration/test_tenant_isolation.py -q
  ```

  预期因 tenancy 模块和 dependencies 不存在而失败；由助手记录。

- [x] **Step 3: 实现上下文和 Repository 边界。**

> **审查修订（2026-08-06）：** Principal/TenantContext 不能只依赖 frozen dataclass 约束。它们由身份依赖与 membership factory 写入内部 provenance capability，`tenant_scope`、TenantRepository 与 PlatformRepository 会拒绝未签发对象。SQLAlchemy 第二道 `with_loader_criteria` 同时覆盖 scoped ORM 的 `SELECT`、bulk `UPDATE` 与 bulk `DELETE`；显式 Repository 条件仍为第一道防线。

  `context.py` 定义不可变数据类型：

  ```python
  @dataclass(frozen=True)
  class Principal:
      user_id: int
      is_platform_admin: bool

  @dataclass(frozen=True)
  class TenantContext:
      principal: Principal
      merchant_id: int
      membership_role: MerchantMemberRole
  ```

  `TenantContextFactory.for_merchant()` 必须查询 `MerchantMember(user_id, merchant_id, is_active=True)` 和 `Merchant(is_active=True)`；不存在时抛 `TenantAccessDenied`。`get_current_principal()` 从已验证 access token 得到 user ID 后读取 active `User`，而不是从 JWT claims 读取平台标志。`require_platform_principal()` 读取 `User.is_platform_admin`，失败抛 403。

  `tenant_scope(context)` 将已验证 context 放入私有 `ContextVar`；SQLAlchemy `do_orm_execute` listener 仅在该 scope 存在时通过 `with_loader_criteria(MerchantOwnedMixin, lambda model: model.merchant_id == context.merchant_id, include_aliases=True)` 注入第二层过滤。scope 由后端 dependency 创建和重置，前端、JWT、模型工具参数都不能直接写入该 `ContextVar`。

  `TenantRepository` 构造函数强制 `context: TenantContext`，并提供如下安全查询形态：

  ```python
  async def get_by_id(self, *, resource_id: int) -> T | None:
      statement = select(self.model).where(
          self.model.id == resource_id,
          self.model.merchant_id == self.context.merchant_id,
      )
      return await self.session.scalar(statement)
  ```

  平台查询使用独立 `PlatformRepository` 抽象和 `PlatformMerchantRepository(session, principal)`；其构造函数拒绝非平台 Principal。测试过滤器不能被普通 Repository 的参数关闭，并确认 Platform Repository 只在 `require_platform_principal()` 已通过后创建。

- [ ] **Step 4: 用户执行 Green 和跨模块回归。**

  在 **`D:\Project\Codex\vibe-coding\backend`** 执行：

  ```powershell
  uv run pytest tests/unit/test_tenant_context.py tests/unit/test_tenant_repositories.py tests/integration/test_tenant_isolation.py -q
  uv run pytest -q
  uv run ruff check .
  ```

  第一个命令验证 A/B 商家隔离、平台专用路径和 JWT 不携带 merchant 权限；第二、三个命令确保认证和旧数据库模块未回归。预期全部通过。

- [ ] **Step 5: 用户提交租户隔离 Commit/PR。**

  在项目根目录执行：

  ```powershell
  git add backend/app/shared/models/tenant.py backend/app/shared/models/__init__.py backend/app/shared/tenancy backend/app/modules/merchants/repositories.py backend/app/api/v1/dependencies.py backend/app/api/v1/auth.py backend/app/modules/identity/security_events.py backend/tests/unit/test_tenant_context.py backend/tests/unit/test_tenant_repositories.py backend/tests/integration/test_tenant_isolation.py progress.md task_plan.md
  git commit -m "feat(tenancy): enforce principal scoped merchant access"
  git push
  ```

  作用：以独立可审计的提交交付后续商品、订单和 Agent 都要复用的多租户安全边界。

## 6. Task 5：共享前端 auth client 与顾客商城登录

**目的：** 将后端认证契约接入 Storefront，验证 access token 不落盘且页面刷新通过 Cookie 恢复。

**文件：**

- 新建：`frontend/packages/auth-client/package.json`
- 新建：`frontend/packages/auth-client/tsconfig.json`
- 新建：`frontend/packages/auth-client/src/index.ts`
- 新建：`frontend/packages/auth-client/src/auth-client.test.ts`
- 修改：`frontend/apps/storefront/package.json`
- 修改：`frontend/apps/storefront/src/main.tsx`
- 新建：`frontend/apps/storefront/src/auth/store.ts`
- 新建：`frontend/apps/storefront/src/auth/StorefrontAuthPanel.tsx`
- 新建：`frontend/apps/storefront/src/auth/StorefrontAuthPanel.test.tsx`
- 修改：`frontend/apps/storefront/src/styles.css`
- 修改：`frontend/pnpm-lock.yaml`（由用户执行普通 `pnpm install` 更新并建立新 workspace 包的依赖链接）
- 修改：`progress.md`、`task_plan.md`

- [x] **Step 1a: 助手写并验证 auth client。**

  已新增无 React 依赖的 `@homepilot/auth-client`，并用 fake `fetch` 验证 refresh/logout 显式携带 credentials 与 CSRF header。其 2 个 Vitest 测试、TypeScript build 与 ESLint lint 已通过。后端真实字段名为 `memberships`，不是早期草案中的 `merchant_memberships`。

- [x] **Step 1b: 助手写 Storefront Red 测试。**

  auth-client 的测试用 fake `fetch` 验证 refresh/logout 显式使用 credentials 和 CSRF header：

  ```ts
  await client.refresh();
  expect(fetchMock).toHaveBeenCalledWith(
    "/api/v1/auth/refresh",
    expect.objectContaining({ credentials: "include", headers: { "X-CSRF-Token": "csrf-value" } }),
  );
  ```

  Storefront 测试使用 `@testing-library/react` 和 jsdom 验证：未登录显示“登录/注册”；注册成功显示返回的邮箱；应用初始化调用 `refresh()`；退出后清除 Zustand 内存 token。测试不读取或写入 `localStorage`。

- [x] **Step 2: 助手运行 Storefront Red。**

  在 `frontend` 目录执行：

  ```powershell
  pnpm --filter @homepilot/auth-client test
  pnpm --filter @homepilot/storefront test
  ```

  预期因 auth store 和组件不存在而失败；由助手诊断，不要求用户手动执行。

- [x] **Step 3: 实现共享 client。**

  `@homepilot/auth-client` 只封装契约，不耦合 React：

  ```ts
  export type AuthUser = { id: number; email: string; is_platform_admin: boolean; memberships: MerchantMembership[] };
  export type AuthResponse = { access_token: string; token_type: "bearer"; user: AuthUser };

  export class AuthClient {
    constructor(private readonly baseUrl = import.meta.env.VITE_API_BASE_URL ?? "http://localhost:8000") {}
    register(input: RegisterInput): Promise<AuthResponse> {
      return this.request<AuthResponse>("/register", { method: "POST", body: JSON.stringify(input) });
    }
    login(input: LoginInput): Promise<AuthResponse> {
      return this.request<AuthResponse>("/login", { method: "POST", body: JSON.stringify(input) });
    }
    refresh(): Promise<AuthResponse> {
      return this.request<AuthResponse>("/refresh", { method: "POST", csrf: true });
    }
    async logout(): Promise<void> {
      await this.request<void>("/logout", { method: "POST", csrf: true });
    }
    me(accessToken: string): Promise<AuthUser> {
      return this.request<AuthUser>("/me", { headers: { Authorization: `Bearer ${accessToken}` } });
    }
    private async request<T>(path: string, init: RequestInit & { csrf?: boolean } = {}): Promise<T> {
      const headers = new Headers(init.headers);
      headers.set("Content-Type", "application/json");
      if (init.csrf) headers.set("X-CSRF-Token", readCookie("csrf_token"));
      const response = await fetch(`${this.baseUrl}/api/v1/auth${path}`, { ...init, headers, credentials: "include" });
      if (!response.ok) throw new AuthApiError(response.status, (await response.json()).detail);
      return response.status === 204 ? (undefined as T) : (await response.json() as T);
    }
  }
  ```

  不将 token 写入 `localStorage`、`sessionStorage`、URL 或持久化 Zustand middleware。CSRF cookie 读取函数在非浏览器测试环境安全返回空字符串。

- [x] **Step 4: 实现 Storefront auth store 与最小面板。**

  `store.ts` 的状态和动作固定如下：

  ```ts
  type AuthState = {
    status: "loading" | "anonymous" | "authenticated";
    accessToken: string | null;
    user: AuthUser | null;
    restoreSession: () => Promise<void>;
    acceptAuth: (response: AuthResponse) => void;
    clear: () => void;
  };
  ```

  `StorefrontAuthPanel` 提供邮箱、密码、登录/注册切换、提交中状态、后端安全错误文案、登录后邮箱和退出按钮。入口组件首次渲染调用 `restoreSession()`；刷新失败只进入 anonymous，不显示 token 相关错误。应用 package 加入 `"@homepilot/auth-client": "workspace:*"`、`"@testing-library/react": ">=16 <17"` 和 `"jsdom": ">=26 <28"`；共享 package 的 exports 指向 `src/index.ts` 并通过自身 `tsc --noEmit`、Vitest、ESLint 脚本参与根 workspace 校验。Storefront 的 `vite.config.ts` 将 `test.environment` 设为 `"jsdom"`。

- [x] **Step 5: 用户更新前端依赖链接并执行 Green。**

  在 **`D:\Project\Codex\vibe-coding\frontend`** 执行：

  ```powershell
  pnpm install
  pnpm --filter @homepilot/auth-client test
  pnpm --filter @homepilot/storefront test
  pnpm --filter @homepilot/storefront build
  pnpm --filter @homepilot/storefront lint
  ```

  第一个命令按已确认版本同步 workspace lockfile，并为新包建立本地可执行依赖链接；其余命令验证共享 client、商城表单、类型构建和静态检查。预期全部通过。

- [x] **Step 6: 用户提交商城登录 Commit/PR。**

  在项目根目录执行：

  ```powershell
  git add .
  git diff --cached --stat
  git commit -m "feat(storefront): add customer authentication panel"
  git push -u origin feat/storefront-auth-ui
  ```

  作用：提交顾客端可演示的登录、注册、刷新恢复和退出闭环。用户已完成提交、推送并合并 PR；下一步进入 Task 6 Console 登录。

## 7. Task 6：控制台登录、身份展示与跨端回归

**目的：** 复用共享 auth client 接入商家/平台控制台，确保前端只根据后端身份呈现可访问商家和平台标识。

**文件：**

- 修改：`frontend/apps/console/package.json`
- 修改：`frontend/apps/console/src/main.tsx`
- 新建：`frontend/apps/console/src/auth/store.ts`
- 新建：`frontend/apps/console/src/auth/ConsoleAuthPanel.tsx`
- 新建：`frontend/apps/console/src/auth/ConsoleAuthPanel.test.tsx`
- 修改：`frontend/pnpm-lock.yaml`（由用户更新）
- 修改：`backend/README.md`
- 修改：`README.md`
- 修改：`progress.md`、`task_plan.md`

- [ ] **Step 1: 助手写控制台 Red 测试。**

  使用 mock `AuthClient` 验证：商家成员登录后只渲染 API 返回的商家名称/角色；平台管理员额外渲染“平台管理员”；access token 不会显示在 DOM 或存储中；点击退出调用 `logout()` 并清空状态。

  ```ts
  expect(screen.getByText("平台管理员")).toBeInTheDocument();
  expect(document.body.textContent).not.toContain("eyJ");
  ```

- [ ] **Step 2: 助手运行 Red。**

  在 `frontend` 目录执行：

  ```powershell
  pnpm --filter @homepilot/console test
  ```

  预期因 console auth 组件和 store 尚不存在而失败；由助手记录。

- [ ] **Step 3: 实现控制台最小闭环。**

  Console 的 store 复用 Task 5 的状态结构和 `AuthClient`，不复制 HTTP/CSRF 实现。`ConsoleAuthPanel` 只提供登录，成功后调用 `/me` 的数据展示当前邮箱、平台身份和 `memberships`。无商家关系的普通顾客可登录但显示“当前没有控制台访问权限”，不伪造商家入口。退出后回到登录面板。Console package 加入 `"@homepilot/auth-client": "workspace:*"`、`"@testing-library/react": ">=16 <17"` 和 `"jsdom": ">=26 <28"`，并在 `vite.config.ts` 把 Vitest 环境设为 `"jsdom"`。

- [x] **Step 4: 用户更新锁文件并完成前端全量回归。**

  在 **`D:\Project\Codex\vibe-coding\frontend`** 执行：

  ```powershell
  pnpm install
  pnpm run test
  pnpm run build
  pnpm run lint
  ```

  作用：同步 workspace 包引用，并运行共享包、商城和控制台的完整前端测试/构建/lint。用户已完成最终验收，三个检查均通过；Node ESM warning 为非阻塞提示。

- [x] **Step 5: 用户提交控制台与跨端验证 Commit/PR。**

  在项目根目录执行：

  ```powershell
  git add frontend/apps/console frontend/pnpm-lock.yaml backend/README.md README.md progress.md task_plan.md
  git commit -m "feat(console): add merchant and platform sign-in"
  git push
  ```

  作用：交付控制台身份展示并记录前后端启动方式；用户已完成独立 Commit/PR，PR 已合并并同步 `main`。

## 8. Task 7：种子身份、端到端验收与交付收尾

**目的：** 为演示创建可重复的商家/平台身份种子数据，验证后端、前端和 Docker 的联动，不触碰真实用户数据。

**文件：**

- 新建：`scripts/seed_identity_demo_data.py`
- 新建：`backend/app/modules/identity/demo_seed.py`
- 新建：`backend/app/modules/identity/demo_seed_cli.py`
- 新建：`backend/tests/integration/test_identity_seed.py`
- 新建：`backend/tests/unit/test_demo_seed.py`
- 修改：`.env.example`
- 修改：`README.md`
- 修改：`backend/README.md`
- 修改：`docs/superpowers/plans/2026-08-05-identity-tenancy-auth-implementation.md`
- 修改：`findings.md`、`progress.md`、`task_plan.md`

- [x] **Step 1: 助手写种子数据 Red 测试。**

  集成测试在 `homepilot_test` 中执行 seed 两次，并断言幂等：有一个平台管理员、两个启用商家、每家至少一个成员、两个成员属于不同商家；第二次执行不会产生重复 email 或重复 membership。

  ```python
  await seed_identity_demo_data(session)
  await seed_identity_demo_data(session)
  assert await count_users_by_email("platform.admin@homepilot.dev") == 1
  assert await count_memberships() == 2
  ```

- [x] **Step 2: 助手运行 Red。**

  在 `backend` 目录执行：

  ```powershell
  uv run pytest tests/integration/test_identity_seed.py -q
  ```

  预期因 seed 模块缺失而失败；助手记录。

- [x] **Step 3: 实现安全、可重复的演示种子。**

  种子只使用固定的本地展示邮箱/商家名白名单和从环境变量读取的演示密码；若 `DEMO_SEED_PASSWORD` 缺失或为空，脚本在连接业务库前拒绝运行并打印不含 secret 的设置说明。执行前通过 `get_or_create` 查询 email/merchant name；任一既有记录与预期的启用状态、平台身份或 OWNER 成员关系不符时安全失败并 rollback。脚本绝不覆盖已有密码哈希或将 demo 密码打印到日志。

- [ ] **Step 4: 用户进行最终联调。**

  先在 **项目根目录** 确认 Docker Desktop 仍在运行，然后执行：

  ```powershell
  .\scripts\verify_stack.ps1
  ```

  此脚本验证后端 pytest/Ruff、前端 test/build/lint 和 MySQL/Redis/Qdrant/MinIO 连通性；预期结束时报告所有项目检查通过。随后在 **`backend`** 目录执行：

  ```powershell
  uv run python ..\scripts\seed_identity_demo_data.py
  ```

  此命令只写入本地 `homepilot` 的幂等演示账号；预期输出种子成功数量，不显示密码。最后分别启动两个前端与 API，手工验证：顾客注册/登录、页面刷新恢复、退出失效、商家 A/B 身份差异和平台管理员标识。

- [ ] **Step 5: 用户提交验收与文档 Commit/PR。**

  在项目根目录执行：

  ```powershell
  git add scripts/seed_identity_demo_data.py scripts/verify_stack.ps1 backend/tests/integration/test_identity_seed.py README.md backend/README.md docs/superpowers/plans/2026-08-05-identity-tenancy-auth-implementation.md findings.md progress.md task_plan.md
  git commit -m "test(identity): add demo seed and end-to-end verification"
  git push
  ```

  作用：提交可重复演示、联调验证和最终文档；预期推送成功。创建 PR 时在描述中列出：认证 API、refresh rotation、CSRF、租户越权测试、两个前端登录闭环、实际回归命令及结果。

## 9. 完成定义

此模块只有同时满足以下条件才可合并：

- 顾客可注册、登录、刷新、退出，密码和 refresh token 均不以明文存储。
- refresh token 单次轮换，旧 token、过期 token、注销 token 和错误 CSRF 均无法恢复会话。
- JWT 中没有 merchant/role 授权事实；商家 A 无法构建或使用商家 B 的 `TenantContext`；平台跨租户查询没有普通 Repository 的绕过入口。
- Storefront 与 Console 都能在不持久化 access token 的前提下恢复和退出会话。
- `uv run pytest -q`、`uv run ruff check .`、`pnpm run test`、`pnpm run build`、`pnpm run lint` 和 `scripts/verify_stack.ps1` 均有本次实际通过记录。
- 文档、ADR、计划、发现和进度文件均更新；每个独立 Task 已按约定形成清晰 Commit，并通过 GitHub PR 审阅。
