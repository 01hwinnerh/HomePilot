# HomePilot API

这个目录包含 HomePilot 的 FastAPI 模块化单体、异步 SQLAlchemy 数据层和 Alembic 迁移环境。认证、商家、交易与 Agent 模块按根目录实施计划增量加入。

## 本地配置

后端统一读取项目根目录的 `.env`：

- `DATABASE_URL` 指向本地业务库 `homepilot`；
- `TEST_DATABASE_URL` 指向隔离测试库 `homepilot_test`；
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
