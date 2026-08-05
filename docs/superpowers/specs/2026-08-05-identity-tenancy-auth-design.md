# HomePilot 身份认证与多租户隔离设计

**状态：** 已确认，待编写实施计划  
**日期：** 2026-08-05  
**范围：** 阶段 1 的“身份、认证、RBAC 与租户上下文”子模块；不包含商家入驻审核、成员邀请、邮箱验证、找回密码或商品业务。

## 1. 目标与边界

本模块为用户商城、商家控制台、平台控制台和后续 Agent 工具提供统一且可审计的身份来源。它必须做到：

- 顾客能够使用邮箱和密码自行注册、登录、刷新登录状态和退出登录。
- 商家成员和平台管理员首版只通过种子数据创建，避免在早期引入邀请、审核和邮件服务。
- 前端页面刷新后可安全恢复会话，但不将长期凭据写入 `localStorage`。
- 商家成员只能在自己所属商家范围内操作；平台管理员跨商家操作必须经过显式的平台路径。
- 后续 LangGraph Agent 只能使用服务端构造的身份和租户上下文，不能由模型或前端参数伪造身份。

首版不实现：第三方 OAuth、MFA、邮箱验证、密码找回、成员邀请、全设备退出、商家入驻审核和细粒度资源权限配置界面。

## 2. 已选择方案与备选方案

选择“短期 JWT access token + 可轮换 opaque refresh token”的混合方案。

| 方案 | 结论 | 原因 |
|---|---|---|
| 短期 JWT + rotating refresh token | 采用 | 兼顾 FastAPI API 调用体验、前端无感恢复会话和 refresh token 可撤销能力；能展示安全设计能力。 |
| 只使用长效 JWT | 不采用 | 无法可靠注销或撤销已泄露令牌，且 token 轮换不可控。 |
| 服务端 Cookie Session | 不采用 | 也可行，但会弱化 JWT/API 场景展示；后续 Agent、SSE 和多前端客户端的认证契约不如混合方案直观。 |

## 3. 数据模型

### 3.1 `User`

| 字段 | 含义与约束 |
|---|---|
| `id` | 用户主键。 |
| `email` | 规范化后的邮箱，唯一且建立唯一索引。 |
| `password_hash` | Argon2 生成的密码哈希；绝不保存明文密码。 |
| `is_active` | 停用用户不能登录、刷新或访问受保护接口。 |
| `is_platform_admin` | 首版最小平台管理员标志；不把平台权限混入商家成员角色。 |
| `created_at` / `updated_at` | 审计时间戳。 |

注册时邮箱去除首尾空白并使用小写形式作为唯一性比较值；密码最少 12 个字符，不强制“必须含大小写/符号”这类容易导致可预测密码的复杂度规则。密码和邮箱格式校验失败返回字段验证错误，登录失败仍使用统一认证错误。

### 3.2 `Merchant` 与 `MerchantMember`

`Merchant` 表示租户，首版只需要稳定 ID、名称、启用状态和时间戳。`MerchantMember` 是用户与商家的多对多关系，支持用户未来属于多个商家。

| `MerchantMember` 字段 | 含义与约束 |
|---|---|
| `user_id` + `merchant_id` | 联合唯一，且两个外键分别建立查询索引。 |
| `role` | 仅允许 `OWNER`、`STAFF`。首版两者都可完成基础商家运营；后续按业务再收紧具体动作。 |
| `is_active` | 被停用的成员不再可建立该商家的租户上下文。 |
| 时间戳 | 保留加入和变更审计依据。 |

种子数据中每个商家成员可以只加入一个商家，但数据模型不得假设这一限制。

### 3.3 `AuthSession`

每一条记录代表一个浏览器或设备上的 refresh token 会话。

| 字段 | 含义与约束 |
|---|---|
| `id` | 会话主键；用于关联审计和 rotation 链路。 |
| `user_id` | 所属用户，建立索引。 |
| `refresh_token_hash` | opaque refresh token 的单向哈希，唯一；数据库不保存原文。 |
| `expires_at` | refresh token 的到期时间。 |
| `revoked_at` / `revoked_reason` | 注销、轮换、用户停用或安全事件后的撤销状态。 |
| `replaced_by_session_id` | refresh rotation 后指向新会话，确保旧 token 单次使用。 |
| `created_at` | 会话创建时间。 |

单次 refresh 时必须在同一数据库事务中锁定旧 `AuthSession`、判断其未撤销且未过期、撤销旧会话并创建新会话。并发或重放的旧 token 只会得到未认证响应，不能再次产生新 token。

## 4. 认证令牌、Cookie 与 CSRF

### 4.1 Access token

- 采用 JWT，默认有效期为 **15 分钟**，通过配置项统一管理。
- 首版使用 Settings 中的独立对称签名密钥和 `HS256`；密钥只能来自未提交的 `.env`，生产环境必须使用足够长的随机值。若未来拆分为多服务或需要第三方验证，再通过新的 ADR 迁移到非对称签名。
- claims 仅包含 `sub`（用户 ID）、`typ=access`、`jti`、`iat`、`exp` 和 `iss`。
- access token 不含 `merchant_id`、商家成员角色或可访问商家列表；这些授权事实必须每次从服务端数据源获取。
- 前端只将 access token 存放在 Zustand 内存状态；页面刷新后内存清空是预期行为。
- API 使用 `Authorization: Bearer <access_token>`。Bearer 接口不依赖 Cookie，因此不使用 CSRF 作为其认证机制。

### 4.2 Refresh token

- 采用高熵 opaque 随机值，默认有效期为 **7 天**，通过配置项统一管理。
- 仅通过名为 `refresh_token` 的 Cookie 发送，属性固定为 `HttpOnly=True`、`SameSite=Lax`、`Path=/api/v1/auth`。
- `Secure` 由 Settings 控制：本地 HTTP 开发默认关闭，生产 HTTPS 环境必须开启。
- 每次登录、注册成功和 refresh 成功都签发新 refresh token；refresh 时旧 token 立即失效。
- logout 仅撤销当前浏览器携带的 refresh session，并清理 refresh/CSRF Cookie；“退出所有设备”留到后续功能。

### 4.3 CSRF

因为 refresh 和 logout 依赖浏览器自动携带的 Cookie，它们采用双重提交 CSRF：

1. 登录、注册和刷新会设置非 `HttpOnly` 的 `csrf_token` Cookie。
2. 前端读取该 Cookie，并在 refresh/logout 请求中同时填写 `X-CSRF-Token` 请求头。
3. 后端以常量时间比较 header 与 Cookie；缺失或不一致统一拒绝。

本地商城和控制台与 API 即使使用不同端口，仍须使用配置中明确列出的 CORS origins，并启用 credentials；不得以 `*` 配置带凭据的 CORS。

登录、注册和 refresh 是凭据接口，应使用 Redis 进行可配置的限流；达到阈值时返回通用的 `429 Too Many Requests`，不透露账号状态。限流是防护层，不得替代密码校验、token 撤销或 CSRF 验证。

## 5. API 契约

统一前缀为 `/api/v1/auth`。响应中永远不返回密码哈希、refresh token 原文或内部 session 哈希。

| 接口 | 认证 | 行为 |
|---|---|---|
| `POST /register` | 无 | 顾客邮箱+密码注册；成功后返回用户信息与 access token，并设置 refresh/CSRF Cookie。重复邮箱返回冲突错误。 |
| `POST /login` | 无 | 校验邮箱+密码；成功后签发 token；用户不存在和密码错误返回同一安全错误。 |
| `POST /refresh` | refresh Cookie + CSRF | 原子轮换 refresh session，返回新的 access token，并重设 refresh/CSRF Cookie。过期、撤销、重放或用户停用均返回 401。 |
| `POST /logout` | refresh Cookie + CSRF | 撤销当前 refresh session 并清理两个 Cookie；成功时可幂等返回成功。 |
| `GET /me` | access Bearer | 返回当前用户、平台管理员标志和已启用的商家成员关系列表。 |

错误语义：缺失、无效、过期或已撤销的认证凭据返回 `401 Unauthorized`；身份已认证但不拥有目标商家/平台权限返回 `403 Forbidden`；注册邮箱已存在返回 `409 Conflict`。登录错误的外部文案不得暴露“邮箱不存在”或“密码错误”的差异。

## 6. Principal、RBAC 与租户隔离

### 6.1 服务端上下文

认证依赖把有效 access token 转换为不可由前端构造的 `Principal`，至少包含 `user_id`、`is_platform_admin` 和认证状态。商家路由在此基础上通过服务器查询创建 `TenantContext`：

- 目标 `merchant_id` 只能来自受保护路由路径、已经受限的资源记录或服务端动作；即使客户端提交，也必须验证当前用户有激活的 `MerchantMember` 关系。
- `TenantContext` 包含 `Principal`、已验证的 `merchant_id` 和该商家内的 `OWNER/STAFF` 角色。
- 用户属于多个商家时，可以选择目标商家，但选择只是请求目标；授权结论只能由 `MerchantMember` 查询得出。
- 顾客不自动获得商家租户上下文；平台管理员也不自动伪装为某商家成员。

### 6.2 Repository 边界

- 普通 `TenantRepository` 的方法必须显式接收 `TenantContext`；每次查询同时按资源 ID 与 `merchant_id` 限制。
- SQLAlchemy Session 额外注入租户过滤，作为遗漏条件时的第二道防线，而不是唯一授权机制。
- 跨租户的平台查询只允许使用独立 `PlatformRepository`，该 Repository 必须要求平台管理员 `Principal`；普通 Tenant Repository 不提供“忽略 tenant filter”的开关。
- 后续 Agent 工具不得接收可信度不足的 `user_id`、`merchant_id` 或角色参数；它们只能使用服务端注入的 `Principal`/`TenantContext`。

## 7. 前端最小闭环

首版只实现可验证的认证体验，不提前实现完整个人中心或权限管理页面。

- **Storefront：** 注册页、登录页、登录后的身份摘要和退出按钮。
- **Console：** 登录页、登录后的身份摘要、可访问商家列表和退出按钮；平台管理员显示平台身份。
- Zustand 只维护内存中的 `accessToken`、用户和加载状态。应用启动时调用 refresh；成功后写入内存，失败则显示未登录状态。
- 通过共享 API client 统一附加 access Bearer token；refresh/logout 使用 `credentials: include` 与 CSRF header。
- 后端以返回的身份为准。前端路由守卫只改善体验，不能作为权限控制。

配置集中于 `backend/app/core/config.py` 与本地 `.env`：JWT 签名密钥、issuer、access/refresh 有效期、Cookie `Secure` 开关、CORS origins、Cookie 名称和认证限流开关均不得散落在路由或前端代码中。

## 8. 可观测性与审计

- 注册、登录成功、登录失败、refresh、refresh 重放/拒绝、logout、用户停用导致的拒绝和租户越权尝试均记录结构化安全事件。
- 日志只记录用户 ID、会话 ID、结果、失败类型和必要的请求关联 ID；不得记录密码、access token、refresh token、Cookie 或完整 Authorization header。
- 后续 `AuditLog` 复用此身份上下文，为商家、平台、Agent 和售后高风险操作提供操作者来源。

## 9. 验收与测试

后端至少覆盖以下测试，前端为登录表单和会话恢复编写最小单元测试：

1. 密码只以 Argon2 哈希保存，正确密码可验证、错误密码不可验证。
2. 重复邮箱不能注册；错误登录不泄露用户是否存在。
3. access token 仅接受 `typ=access`、有效签名和未过期时间；refresh token 不得作为 Bearer 使用。
4. refresh 成功后旧 session 已撤销，旧 refresh token 再使用失败；并发 refresh 只能成功一次。
5. logout 后当前 refresh token 无法恢复登录；用户停用后不能刷新或访问受保护接口。
6. refresh/logout 缺少、错误或不匹配的 CSRF token 时被拒绝。
7. 商家 A 成员不能为商家 B 构造有效 `TenantContext`，也不能通过 Repository 读取 B 的资源。
8. 平台管理员不能通过普通 `TenantRepository` 跳过租户条件；跨租户操作必须经 `PlatformRepository` 和显式 RBAC 校验。
9. 应用刷新时前端使用 refresh Cookie 恢复 access token；退出后状态清空，受保护路由回到登录入口。
10. 凭据接口达到限流阈值时返回通用 429，且不影响既有用户的 tenant/RBAC 校验。

## 10. 实施前提

- 实施计划完成后再检查 `backend/pyproject.toml` 是否已经直接声明 JWT、Argon2、邮箱校验和认证限流所需依赖。
- 若需要新增、升级或锁定直接依赖，先向用户说明包名、版本范围、用途及兼容性影响，得到确认后才修改依赖声明；用户自行执行安装命令。
- 本规格不改变既有数据库基础层，也不创建迁移。数据表、迁移、接口、前端和测试将在后续独立功能分支中按 TDD 实施。
