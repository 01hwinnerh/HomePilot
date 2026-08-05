# HomePilot API

这个目录包含 HomePilot 的 FastAPI 模块化单体、异步 SQLAlchemy 数据层和 Alembic 迁移环境。认证、商家、交易与 Agent 模块按根目录实施计划增量加入。

## 本地配置

后端统一读取项目根目录的 `.env`：

- `DATABASE_URL` 指向本地业务库 `homepilot`；
- `TEST_DATABASE_URL` 指向隔离测试库 `homepilot_test`；
- `AUTH_JWT_SECRET` 是本地随机 JWT 签名密钥，必须只写入未提交的 `.env`；可在 `backend` 目录用 `uv run python -c "import secrets; print(secrets.token_urlsafe(48))"` 生成；
- `AUTH_COOKIE_SECURE=false` 仅适用于本地 HTTP 开发。未来生产 HTTPS 部署必须设为 `true`，并使用精确的 `BACKEND_CORS_ORIGINS`，不能使用 `*`；
- 集成测试不得在业务库中创建或清理测试数据。

测试库名称可以修改，但必须包含 `test` 且不得与业务库名称相同；集成测试和 Docker 初始化脚本会在执行 DDL/DML 前强制校验这两个条件。

全新 MySQL volume 会通过 Compose 挂载的初始化脚本自动创建测试库。对于脚本加入前已经存在的 volume，在项目根目录执行一次：

```powershell
docker compose exec mysql sh /docker-entrypoint-initdb.d/10-create-test-database.sh
```

## 数据库迁移

以下命令均在 `backend` 目录执行：

```powershell
uv run alembic upgrade head
uv run alembic current
```

第一条把 `DATABASE_URL` 对应的数据库升级到最新 revision；第二条只查看当前 revision。创建新迁移时使用：

```powershell
uv run alembic revision --autogenerate -m "describe schema change"
```

已合并的迁移文件不可修改或覆盖，应通过新 revision 演进数据库结构。

## 验证

```powershell
uv run pytest -q
uv run ruff check .
```

当前集成测试覆盖测试库真实连接、异常事务回滚和 `alembic upgrade head`。

认证基础单元测试还覆盖 Argon2 密码哈希、access JWT、opaque refresh token、CSRF 双重提交值、认证时长、CORS 白名单和限流配置：

```powershell
uv run pytest tests/unit/test_security.py tests/unit/test_database_settings.py -q
```

## 认证 API

认证接口统一位于 `/api/v1/auth`：`POST /register`、`POST /login`、`POST /refresh`、`POST /logout` 与 `GET /me`。access token 仅通过响应 JSON 返回，供前端保存在内存中；refresh token 仅通过 `HttpOnly` Cookie 发送，数据库只保存其 SHA-256 哈希。`/me` 同时返回用户的平台管理员标志和所有“成员、商家均启用”的商家成员关系，前端只将其用于展示；后续商家操作仍会重新从数据库构建 TenantContext。

`/refresh` 和 `/logout` 还必须在 `X-CSRF-Token` 请求头中带上与 `csrf_token` Cookie 一致的值。Cookie 名称与 Path 集中由 `AUTH_REFRESH_COOKIE_NAME`、`AUTH_CSRF_COOKIE_NAME`、`AUTH_COOKIE_PATH` 配置，生产环境应同时启用 HTTPS 与 `AUTH_COOKIE_SECURE=true`。
