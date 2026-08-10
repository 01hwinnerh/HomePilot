# 商家目录基础实施计划

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 建立安全、可扩展的 `Merchant → Store → Product → SKU` 目录基础，并提供商家管理与顾客公开浏览 API。

**Architecture:** 新增独立 `catalog` 领域模块，复用现有 `MerchantOwnedMixin`、可信 `TenantContext`、`TenantRepository` 和 `tenant_scope`。MySQL 保存目录真源；Product 直接保存 `merchant_id/store_id`，SKU 直接保存 `merchant_id/product_id`，通过组合外键拒绝跨租户错配。商家写接口实时从数据库构造授权，公开接口只返回启用商家、启用店铺和 `PUBLISHED` 商品。

**Tech Stack:** Python 3.12、FastAPI、Pydantic v2、SQLAlchemy 2 async、Alembic、MySQL 8.4、pytest/pytest-asyncio、Ruff。

---

## 文件职责地图

- `backend/app/modules/catalog/models.py`：Store、Product、SKU ORM、状态枚举和约束。
- `backend/app/modules/catalog/schemas.py`：Store/Product/SKU 请求与响应 schema。
- `backend/app/modules/catalog/repositories.py`：租户内目录查询与平台公开读取的查询封装。
- `backend/app/modules/catalog/service.py`：创建、更新、发布、归档的事务和业务规则。
- `backend/app/api/v1/merchant_catalog.py`：需 `TenantContext` 的商家管理接口。
- `backend/app/api/v1/catalog.py`：无需登录的公开目录接口。
- `backend/app/api/v1/router.py`：挂载两个目录 router。
- `backend/alembic/versions/20260809_0003_catalog_foundation.py`：可逆目录迁移。
- `backend/tests/unit/test_catalog_models.py`：模型、枚举、纯校验行为。
- `backend/tests/unit/test_catalog_service.py`：状态和发布规则的 Red→Green。
- `backend/tests/integration/test_catalog_migration.py`：真实 MySQL 迁移与约束。
- `backend/tests/integration/test_catalog_api.py`：双商家 HTTP、公开读取和越权回归。
- `scripts/seed_catalog_demo_data.py`：复用既有两个演示商家，幂等创建店铺/商品/SKU。
- `backend/tests/integration/test_catalog_seed.py`：目录 seed 首次/重复/冲突行为。
- `docs/superpowers/specs/2026-08-09-catalog-foundation-design.md`：已批准设计真源。
- `progress.md`、`task_plan.md`、`HANDOFF.md`、`docs/handover/`：在创建本模块 PR 前同步最新验证状态。
- `.learning/task8-catalog-foundation.md`：完成后写入概念、数据流和 5 题材料；该目录已被 `.gitignore` 排除。

### Task 1：模型与迁移 Red→Green

**Files:**

- Create: `backend/app/modules/catalog/__init__.py`
- Create: `backend/app/modules/catalog/models.py`
- Create: `backend/tests/unit/test_catalog_models.py`
- Create: `backend/tests/integration/test_catalog_migration.py`
- Create: `backend/alembic/versions/<timestamp>_catalog_foundation.py`
- Modify: `backend/alembic/env.py` to import catalog models for metadata discovery.

- [x] **Step 1: 写模型 Red 测试**：断言三张表、状态枚举、`(merchant_id, slug)`、`(merchant_id, sku_code)` 唯一约束、组合外键和 `price_minor >= 0` 可表达。
- [x] **Step 2: 运行 Red**：在 `backend` 执行 `uv run pytest tests/unit/test_catalog_models.py -q`，预期因 `app.modules.catalog.models` 不存在而失败。
- [x] **Step 3: 实现最小 ORM**：Store 继承 `MerchantOwnedMixin`；Product 继承 `MerchantOwnedMixin` 并保存 `store_id`；SKU 继承 `MerchantOwnedMixin` 并保存 `product_id`；所有 ID 使用既有整数主键和 `TimestampMixin`。
- [x] **Step 4: 创建可逆 Alembic revision**：按 `merchants → stores → products → skus` 顺序创建表、索引、唯一约束和组合外键；downgrade 按反向依赖删除。
- [x] **Step 5: 运行 Green**：执行 `uv run pytest tests/unit/test_catalog_models.py tests/integration/test_catalog_migration.py -q` 和 `uv run ruff check .`，预期全部通过。

### Task 2：Schema 与目录服务 Red→Green

**Files:**

- Create: `backend/app/modules/catalog/schemas.py`
- Create: `backend/app/modules/catalog/service.py`
- Create: `backend/tests/unit/test_catalog_service.py`

- [x] **Step 1: 写失败行为**：覆盖新建 Store/Product/SKU 默认为 active/DRAFT、负价格拒绝、重复 SKU 由服务转换为领域冲突、无启用 SKU 发布拒绝、有效 SKU 才能发布、归档后不可重新发布。
- [x] **Step 2: 运行 Red**：执行 `uv run pytest tests/unit/test_catalog_service.py -q`，预期因 service/schema 未实现而失败。
- [x] **Step 3: 定义 schema**：`StoreCreate/Update/Response`、`ProductCreate/Update/Response`、`SkuCreate/Update/Response`；`price_minor` 为非负整数；`variant_attributes` 必须是字符串键到 JSON 标量值的对象；状态字段只允许服务端转换。
- [x] **Step 4: 实现事务服务**：服务构造函数接收 `AsyncSession` 与可信 `TenantContext`，所有查询带 merchant 条件；创建 SKU 前校验 Product 归属；发布前校验启用 Store 和至少一个启用 SKU；异常抛出可映射的领域错误并回滚。
- [x] **Step 5: 运行 Green**：执行定向 service 测试和 Ruff，预期全部通过。

### Task 3：商家管理 API 与租户越权回归

**Files:**

- Create: `backend/app/api/v1/merchant_catalog.py`
- Create: `backend/tests/integration/test_catalog_api.py`
- Modify: `backend/app/api/v1/router.py`

- [x] **Step 1: 写 HTTP Red 测试**：用演示商家 A/B 的 Bearer token 覆盖 Store/Product/SKU 创建、发布、归档、重复 SKU `409`、A 访问 B 返回 `404`、无成员返回 `403`、无 token 返回 `401`。
- [x] **Step 2: 运行 Red**：执行 `uv run pytest tests/integration/test_catalog_api.py -q`，预期因 router 未挂载而失败。
- [x] **Step 3: 实现路由**：所有商家接口依赖 `scoped_tenant_context`；从路径 `merchant_id` 获取可信上下文；错误映射为 `401/403/404/409/422`；不接受前端传入的 `merchant_id` 覆盖租户上下文。
- [x] **Step 4: 运行 Green**：执行目录 API 定向测试、现有租户隔离测试和 Ruff，预期通过。

### Task 4：顾客公开浏览 API

**Files:**

- Create: `backend/app/api/v1/catalog.py`
- Modify: `backend/app/api/v1/router.py`
- Modify: `backend/tests/integration/test_catalog_api.py`

- [x] **Step 1: 写公开查询 Red 测试**：验证公开列表/详情只返回启用商家、启用店铺、`PUBLISHED` 商品和启用 SKU；草稿、归档、停用资源统一 `404` 或不出现在列表。
- [x] **Step 2: 运行 Red**：执行公开接口测试，预期因路由未实现而失败。
- [x] **Step 3: 实现查询**：使用显式 SQL join 和状态过滤，不创建用户租户上下文；详情按全局 `product_id` 查询，禁止通过 URL 参数绕过公开状态条件；列表固定分页上限和稳定排序。
- [x] **Step 4: 运行 Green**：执行完整目录 API 测试与 Ruff，预期通过。

### Task 5：幂等目录演示 seed

**Files:**

- Create: `scripts/seed_catalog_demo_data.py`
- Create: `backend/app/modules/catalog/demo_seed.py`
- Create: `backend/tests/integration/test_catalog_seed.py`

- [x] **Step 1: 写 seed Red 测试**：复用两个固定演示商家，首次创建各自店铺、商品和至少一个 SKU；第二次运行不重复；同商家 slug/SKU code 结构冲突时 rollback 且不覆盖既有数据。
- [x] **Step 2: 运行 Red**：执行目录 seed 定向测试，预期因模块缺失而失败。
- [x] **Step 3: 实现薄 CLI 与领域 seed**：只按固定商家名称定位既有 Merchant；使用固定演示店铺、商品、SKU 标识；不读取或打印任何密码；所有写入在事务中完成，冲突抛出并回滚。
- [x] **Step 4: 运行 Green**：执行 seed 定向测试、后端全量 pytest 和 Ruff，预期通过。

### Task 6：文档、学习材料与 PR 前门禁

**Files:**

- Modify: `progress.md`
- Modify: `task_plan.md`
- Modify: `HANDOFF.md`
- Modify: `docs/handover/2026-08-06-homepilot-handoff.md`
- Create: `.learning/task8-catalog-foundation.md`

- [x] **Step 1: 写完成后数据流讲解**：描述商家请求、TenantContext、组合外键、Service、Repository、公开查询和事务回滚。
- [x] **Step 2: 写 5 道复述题**：2 个“是什么”、2 个“为什么”、1 个“如果……会怎样”，给出参考答案并保存到 `.learning/`。
- [x] **Step 3: 更新计划与交接**：记录新增表、API、测试数量和未处理范围；不记录分支或 PR 合并状态。
- [x] **Step 4: 执行 PR 前门禁**：在 `backend` 运行 `uv run pytest -q` 与 `uv run ruff check .`；根目录运行 `scripts/verify_stack.ps1`；确认没有 `.env` 和学习材料被暂存。
- [ ] **Step 5: 将代码、迁移、测试和文档一次性提交到同一个模块 PR**；用户执行 Git 操作，推荐 Conventional Commit：`feat(catalog): add tenant-safe product catalog foundation`。

## 验收命令

在实现完成后，用户执行：

```powershell
# backend
uv run pytest tests/unit/test_catalog_models.py tests/unit/test_catalog_service.py tests/integration/test_catalog_migration.py tests/integration/test_catalog_api.py tests/integration/test_catalog_seed.py -q
uv run pytest -q
uv run ruff check .

# repository root
.\scripts\verify_stack.ps1
```

预期：目录定向测试通过、后端全量测试通过、Ruff 通过、工程级验证通过；保留既有上游弃用警告，不把警告当作本模块失败。
