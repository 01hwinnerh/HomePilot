# ADR-0001：认证令牌与租户隔离边界

**状态：** 已接受  
**日期：** 2026-08-05

## 背景

HomePilot 同时面向顾客、商家成员、平台管理员以及后续的 Agent 工具。系统既要在两个 React 前端中提供可恢复的登录体验，也必须防止前端、商家成员或模型伪造租户身份并跨商家访问数据。

## 决策

1. 使用 15 分钟 JWT access token 与 7 天可轮换 opaque refresh token；两个有效期均由 Typed Settings 配置。
2. access token 仅放前端内存，refresh token 仅放 `HttpOnly`、`SameSite=Lax` Cookie；数据库只保存 refresh token 的哈希和撤销状态。
3. refresh token 每次使用即轮换。`refresh` 和 `logout` 使用双重提交 CSRF；本地 `Secure` Cookie 可关闭，生产必须开启。
4. JWT 不保存 `merchant_id`、商家角色或可访问商家列表。每个商家请求都从数据库中的活跃 `MerchantMember` 关系构建 `TenantContext`。
5. 普通跨商家隔离由显式 `TenantContext` Repository 参数与 SQLAlchemy 租户过滤双重保证。平台跨租户查询只能经独立 `PlatformRepository`，并要求平台管理员身份。
6. 顾客可自助注册；商家成员和平台管理员首版只通过种子数据创建。

## 后果

优点：refresh token 可以撤销，前端刷新可恢复会话，模型和前端都无法把不可信的 tenant ID 变成授权结论，且安全边界便于独立测试。

代价：需要维护 `AuthSession`、Cookie/CSRF 处理和 refresh rotation 的并发测试。用户启用状态、商家成员关系和平台管理员权限由服务端在受保护请求中查询，因此这类授权变化不依赖 access token 过期才能生效。实现阶段必须把 JWT 与密码哈希库声明为后端直接依赖，不能依赖传递安装。

## 不采用的方案

- 不使用长效 JWT 作为唯一凭据：无法可靠注销或撤销。
- 不使用服务端 Cookie Session 作为首版主方案：会降低 API/JWT 场景的展示价值。
- 不把商家 ID 或角色写入 JWT 并直接信任：成员变化、用户多商家归属和模型越权场景均可能导致过期授权。
