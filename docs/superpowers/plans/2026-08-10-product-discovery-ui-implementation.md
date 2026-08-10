# 商品管理与商品发现 UI Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 将 Task 8 目录基础接成可扩展的家居商品发现与商家管理闭环，并用 Elasticsearch 提供公开搜索。

**Architecture:** MySQL 保存类目、商品、SKU、店铺状态和 Outbox 真源；商家写入在同一事务写业务表与事件。Outbox relay/worker 从 MySQL 重建版本化 Elasticsearch 商品索引，Storefront 先从 ES 找候选，再回 MySQL 校验公开资格并组装响应。Storefront 使用匿名可访问的类目/关键词浏览，Console 通过可信 `TenantContext` 管理当前商家目录。

**Tech Stack:** FastAPI、SQLAlchemy/Alembic、MySQL 8.4、Elasticsearch 8.x 单节点（本地）、Celery/Redis、React 19、TypeScript、TanStack Query、Ant Design、Vitest、pytest、Ruff。

**提交策略：** 用户要求一个独立模块只产生一次功能提交和一次 PR。因此 Task 1–9 只记录验证检查点，不单独提交；Task 10 在完整回归、学习材料和交接更新完成后统一提交。

---

## 文件地图

- 修改 `docker-compose.yml`、`.env.example`、`backend/pyproject.toml`、`backend/app/core/config.py`、`scripts/verify_stack.ps1`：ES 服务、配置、依赖和工程验证。
- 修改 `backend/app/modules/catalog/models.py`、`schemas.py`、`repositories.py`、`service.py`、`demo_seed.py`：类目、列表查询和事件触发。
- 创建 `backend/app/shared/outbox/models.py`、`service.py`、`__init__.py`：可复用的事务 Outbox。
- 创建 `backend/app/modules/catalog/search/contracts.py`、`mapping.py`、`elasticsearch.py`、`indexer.py`：搜索端口、mapping、ES adapter 和投影器。
- 创建 `backend/app/workers/celery_app.py`、`catalog_tasks.py`、`backend/scripts/rebuild_catalog_index.py`：事件 relay、重试任务和索引重建。
- 修改 `backend/app/api/v1/catalog.py`、`merchant_catalog.py`、`router.py`、`main.py`：公开搜索、类目、商家管理列表和 ES 生命周期。
- 创建 `backend/tests/unit/test_catalog_search.py`、`test_catalog_index_mapping.py`、`test_catalog_outbox.py`、`test_catalog_indexer.py`；修改现有 catalog API/migration/seed 测试：锁定红绿边界。
- 创建 `frontend/apps/storefront/src/catalog/api.ts`、`types.ts`、`CatalogBrowser.tsx`、`CatalogDetail.tsx`、对应测试；修改 `App.tsx`、`styles.css`。
- 创建 `frontend/apps/console/src/catalog/api.ts`、`CatalogWorkspace.tsx`、对应测试；修改 `App.tsx`、`styles.css`。
- 创建 `.learning/2026-08-10-product-discovery-ui.md`（被忽略）：概念、数据流、5 题及答案。
- 更新 `HANDOFF.md`、`docs/handover/2026-08-06-homepilot-handoff.md`、`task_plan.md`、`progress.md`，并与功能 PR 一起提交。

### Task 1: 锁定 Elasticsearch 运行基线

**状态：已完成**

**Files:**
- Modify: `backend/pyproject.toml`, `backend/app/core/config.py`, `.env.example`, `docker-compose.yml`
- Test: `backend/tests/unit/test_config.py`, `backend/tests/integration/test_search_stack.py`

- [x] **Step 1: Write the failing configuration tests**

断言 Settings 暴露 `elasticsearch_url`、`elasticsearch_index_alias`、连接超时和重试上限；空 URL、非 HTTP URL 和空 alias 必须被拒绝。

- [x] **Step 2: Run the focused tests**

Run from `backend/`: `uv run pytest tests/unit/test_config.py -q`  
Expected: FAIL because the new Settings fields do not exist.

- [x] **Step 3: Add the minimum dependency and configuration**

将官方 `elasticsearch` Python client 加入已批准的稳定大版本范围；Settings 默认只指向本地 ES，不读取任何密钥。`.env.example` 增加 `ELASTICSEARCH_URL`、`ELASTICSEARCH_INDEX_ALIAS` 和开发 heap 配置名，不修改真实 `.env`。

- [x] **Step 4: Add a pinned single-node Compose service**

使用经过核验的 Elasticsearch 8.x patch tag/digest，设置 `discovery.type=single-node`、开发 heap 上限和健康检查；暴露 `9200`，添加独立 `elasticsearch_data` volume。生产安全认证不在本地关闭配置中被误带入生产文档。

- [x] **Step 5: Verify the stack boundary**

用户在根目录执行 `docker compose config --quiet`，启动 ES 后执行 `Invoke-WebRequest http://localhost:9200`；预期 Compose 配置通过、ES 返回版本 JSON。后端执行 `uv lock`/`uv sync --all-groups` 后重跑配置测试。

- [x] **Step 6: Record task checkpoint (do not commit independently)**

保留本 Task 代码、测试、锁文件和 findings 更新；不创建独立提交。

### Task 2: 建立类目模型和迁移

**状态：已完成**

**Files:**
- Modify: `backend/app/modules/catalog/models.py`, `schemas.py`, `demo_seed.py`
- Create: `backend/alembic/versions/20260810_0004_catalog_search.py`
- Test: `backend/tests/unit/test_catalog_models.py`, `backend/tests/integration/test_catalog_migration.py`, `test_catalog_seed.py`

- [x] **Step 1: Add Red tests**

锁定根类目、叶子类目、停用类目拒绝新商品、`Product.category_id` 外键、双商家类目 seed 幂等和旧数据补齐行为。

- [x] **Step 2: Run Red**

Run from `backend/`: `uv run pytest tests/unit/test_catalog_models.py tests/integration/test_catalog_migration.py -q`  
Expected: FAIL because Category and `category_id` are absent.

- [x] **Step 3: Implement migration/model/schema**

添加 `categories` 表、父子自引用 FK、slug 唯一约束、排序/启用字段和 `products.category_id`；API Schema 返回类目树和公开类目字段。

- [x] **Step 4: Update the idempotent seed**

为两个演示商家创建稳定家居叶子类目并为现有商品绑定；发现同 slug 但名称/父级/启用状态不匹配时 rollback 抛出明确冲突。

- [x] **Step 5: Run Green and migration safety checks**

Run: `uv run pytest tests/unit/test_catalog_models.py tests/integration/test_catalog_migration.py tests/integration/test_catalog_seed.py -q`; `uv run alembic check`; `uv run ruff check .`  
Expected: all focused tests pass, no pending migration operations, Ruff clean.

- [x] **Step 6: Record task checkpoint (do not commit independently)**

保留本 Task 代码和测试；不创建独立提交。

### Task 3: 实现通用 Transactional Outbox

**状态：已完成**

**Files:**
- Create: `backend/app/shared/outbox/models.py`, `service.py`, `__init__.py`
- Modify: `backend/alembic/versions/20260810_0004_catalog_search.py`, `backend/alembic/env.py`
- Test: `backend/tests/unit/test_catalog_outbox.py`, `backend/tests/integration/test_catalog_migration.py`

- [x] **Step 1: Write failing transaction tests**

测试业务对象与事件同事务提交；业务异常 rollback 时业务行和 outbox 行都不存在；同一 `event_id` 重复写入被唯一约束拒绝或安全忽略。

- [x] **Step 2: Run Red**

Run: `uv run pytest tests/unit/test_catalog_outbox.py -q`  
Expected: FAIL because the outbox model/service does not exist.

- [x] **Step 3: Add the outbox table and service**

字段固定为 `id`、`event_type`、`aggregate_type`、`aggregate_id`、`payload`、`occurred_at`、`published_at`、`attempts`、`last_error`；提供 `append_event(session, ...)` 和按顺序 claim/retry 的查询接口。事件 payload 不包含密码、token 或用户隐私。

- [x] **Step 4: Wire catalog writes without breaking atomicity**

在 `CatalogService` 的 create/update/publish/archive/store/SKU 变更路径加入事件，但只在业务 session commit 前 append；任何 IntegrityError 或领域异常必须 rollback 两类数据。

- [x] **Step 5: Run integration Green**

Run: `uv run pytest tests/unit/test_catalog_outbox.py tests/integration/test_catalog_api.py -q`  
Expected: catalog 写 API 和 outbox 原子性通过。

- [x] **Step 6: Record task checkpoint (do not commit independently)**

保留本 Task 代码和测试；不创建独立提交。

### Task 4: 建立 ES mapping 和搜索端口

**状态：已完成**

**Files:**
- Create: `backend/app/modules/catalog/search/contracts.py`, `mapping.py`, `elasticsearch.py`
- Modify: `backend/app/main.py`, `backend/app/core/config.py`
- Test: `backend/tests/unit/test_catalog_search.py`, `test_catalog_index_mapping.py`

- [x] **Step 1: Write failing contract/mapping tests**

锁定 `CatalogSearchPort.search_product_ids(q, category, offset, limit)`、`index_product(document)`、`delete_product(product_id)`、alias 名称和 `nested active_skus` mapping；查询不能接受 merchant/role 作为可信授权输入。

- [x] **Step 2: Run Red**

Run: `uv run pytest tests/unit/test_catalog_search.py tests/unit/test_catalog_index_mapping.py -q`  
Expected: FAIL because the port and adapter do not exist.

- [x] **Step 3: Implement the adapter**

使用 `AsyncElasticsearch`，集中处理连接超时、连接关闭、`NotFoundError` 和不可用错误；请求只发给后端 adapter，API/React 不导入 ES client。

- [x] **Step 4: Implement versioned mapping and alias operations**

显式定义精确字段、全文字段、价格排序字段和 SKU nested 字段；提供 create-if-missing、alias 切换、clear/rebuild 所需的最小操作。

- [x] **Step 5: Test with a fake client**

Run: `uv run pytest tests/unit/test_catalog_search.py tests/unit/test_catalog_index_mapping.py -q`; `uv run ruff check .`  
Expected: client 请求 payload、异常转换和 mapping 全部通过。

- [x] **Step 6: Record task checkpoint (do not commit independently)**

保留本 Task 代码和测试；不创建独立提交。

### Task 5: 实现索引投影 Worker 与重建命令

**状态：已完成**

**Files:**
- Create: `backend/app/modules/catalog/indexer.py`, `backend/app/workers/celery_app.py`, `backend/app/workers/catalog_tasks.py`, `backend/scripts/rebuild_catalog_index.py`
- Modify: `backend/app/modules/catalog/repositories.py`, `backend/app/core/redis.py`
- Test: `backend/tests/unit/test_catalog_indexer.py`, `backend/tests/integration/test_catalog_search.py`

- [x] **Step 1: Write failing projector tests**

测试公开商品生成完整文档；草稿、归档、停用店铺、停用商家或无启用 SKU 会删除文档；重复事件和乱序事件最终以 MySQL 当前状态为准。

- [x] **Step 2: Run Red**

Run: `uv run pytest tests/unit/test_catalog_indexer.py -q`  
Expected: FAIL because projector/task does not exist.

- [x] **Step 3: Implement MySQL-to-document projection**

Repository 一次性加载 Product、Store、Merchant、启用 SKU 和类目；`CatalogIndexer.project_product(product_id)` 只产生 index/delete 两种结果，确保事件 payload 过期不会覆盖新状态。

- [x] **Step 4: Add retryable Celery task**

复用现有 Redis/Celery 依赖；task 以事件 ID 幂等 claim，成功记录 `published_at`，失败递增 `attempts` 并保存不含敏感值的错误摘要，按固定退避重试。重复消费不能生成重复文档。

- [x] **Step 5: Add full rebuild CLI**

`uv run python -m scripts.rebuild_catalog_index`（从 `backend/`）创建版本化索引、扫描 MySQL 全部公开商品、bulk index、切 alias；命令可重复运行，失败不切换 alias。

- [x] **Step 6: Run focused and real-ES tests**


用户启动 ES 后运行：`uv run pytest tests/unit/test_catalog_indexer.py tests/integration/test_catalog_search.py -q`；预期 fake-client 单测和隔离 ES 集成测试通过。

- [x] **Step 7: Record task checkpoint (do not commit independently)**

保留本 Task 代码和测试；不创建独立提交。

### Task 6: 接通公开类目、搜索和详情 API

**状态：已完成**

**Files:**
- Modify: `backend/app/api/v1/catalog.py`, `backend/app/modules/catalog/repositories.py`, `backend/app/modules/catalog/schemas.py`, `backend/app/main.py`
- Test: `backend/tests/integration/test_catalog_api.py`, `backend/tests/integration/test_catalog_search_api.py`

- [x] **Step 1: Add API Red tests**

测试匿名 `GET /catalog/categories`、关键词“沙发”返回来自多个商家、类目过滤、商家搜索、ES 503、详情 404 和 MySQL 二次公开校验。

- [x] **Step 2: Run Red**

Run: `uv run pytest tests/integration/test_catalog_api.py tests/integration/test_catalog_search_api.py -q`  
Expected: FAIL because routes and search service are absent.

- [x] **Step 3: Implement category and search orchestration**

API 只接收 q/category/分页参数；SearchService 调 ES 取得候选 ID，再用 PublicCatalogRepository 批量按 ID、顺序和当前公开资格重建响应。详情保持 MySQL 直接读取并返回商家/店铺信息。

- [x] **Step 4: Implement 503 and safe empty-page behavior**

将 ES connection/timeout 映射为 `SEARCH_UNAVAILABLE` 503；过滤掉已失效候选后不足一页时返回实际结果，不以全量扫描补洞。

- [x] **Step 5: Run Green**

Run: `uv run pytest tests/integration/test_catalog_api.py tests/integration/test_catalog_search_api.py -q`; `uv run ruff check .`  
Expected: anonymous public search, cross-merchant results and hidden-resource rejection all pass。

- [x] **Step 6: Record task checkpoint (do not commit independently)**

保留本 Task 代码和测试；不创建独立提交。

### Task 7: 接通 Console 商家目录管理

**状态：已完成**

**Files:**
- Modify: `backend/app/api/v1/merchant_catalog.py`, `backend/app/modules/catalog/service.py`, `backend/app/modules/catalog/schemas.py`
- Create: `backend/tests/integration/test_merchant_catalog_lists.py`

- [x] **Step 1: Write Red tests**

测试商家只能列出自己的 stores/products/SKUs；平台管理员和另一商家不能通过路径参数读取或修改；列表结果支持类目/状态分页。

- [x] **Step 2: Implement scoped list endpoints**

复用 `scoped_tenant_context`，Service 接受可信 context；任何路径 merchant mismatch 或资源不属于当前 merchant 都返回 404。列表不从 JWT 或前端 membership 推断授权。

- [x] **Step 3: Run Green**

Run: `uv run pytest tests/integration/test_merchant_catalog_lists.py -q`; `uv run ruff check .`  
Expected: tenant isolation and list pagination pass。

- [x] **Step 4: Record task checkpoint (do not commit independently)**

保留本 Task 代码和测试；不创建独立提交。

### Task 8: 实现 Storefront 商品发现 UI

**状态：已完成**

**Files:**
- Create: `frontend/apps/storefront/src/catalog/api.ts`, `types.ts`, `CatalogBrowser.tsx`, `CatalogDetail.tsx`, `catalog.test.tsx`
- Modify: `frontend/apps/storefront/src/App.tsx`, `styles.css`

- [x] **Step 1: Write Vitest Red tests**

测试匿名启动显示类目和搜索框；输入关键词发起 API 请求；结果可同时显示两个商家的商品；点击卡片进入 `/products/:id`；详情渲染 SKU/价格；空结果、404、503 有明确提示；测试源码检索确保没有 `localStorage`/`sessionStorage`。

- [x] **Step 2: Run Red**

Run from `frontend/`: `pnpm --filter @homepilot/storefront test -- --run src/catalog/catalog.test.tsx`  
Expected: FAIL because catalog components and API client do not exist。

- [x] **Step 3: Implement API client and small pathname router**

使用 `VITE_API_BASE_URL`、`fetch` 和 TanStack Query；路由只支持 `/`、`/products/:id`，不引入 React Router。公开请求不附加伪造授权，认证状态只用于页头展示。

- [x] **Step 4: Implement approved UI**

按已批准线框实现家居类目入口、关键词搜索、跨商家商品卡片、来源店铺和详情页；不渲染购物车/结算入口。

- [x] **Step 5: Run frontend Green**

Run: `pnpm --filter @homepilot/storefront test`; `pnpm --filter @homepilot/storefront build`; `pnpm --filter @homepilot/storefront lint`  
Expected: all storefront tests, TypeScript/Vite build and lint pass。

- [x] **Step 6: Record task checkpoint (do not commit independently)**

保留本 Task 代码和测试；不创建独立提交。

### Task 9: 实现 Console 商品、店铺和 SKU 管理 UI

**状态：已完成**

**Files:**
- Create: `frontend/apps/console/src/catalog/api.ts`, `CatalogWorkspace.tsx`, `catalog.test.tsx`
- Modify: `frontend/apps/console/src/App.tsx`, `styles.css`

- [x] **Step 1: Write Vitest Red tests**

测试已登录商家看到当前 membership、店铺与商品列表；能创建/编辑商品、创建/编辑 SKU、发布/归档；无 membership 显示无权限；401 触发已有 refresh 逻辑；不渲染平台代编辑入口。

- [x] **Step 2: Run Red**

Run: `pnpm --filter @homepilot/console test -- --run src/catalog/catalog.test.tsx`  
Expected: FAIL because catalog workspace is absent。

- [x] **Step 3: Implement scoped Console API client**

所有请求携带内存 access token；merchant ID 只来自当前后端 `/me` membership 选择，不从用户可编辑字段取得。将 401、403、404、409 映射为可理解的 UI 状态。

- [x] **Step 4: Implement Ant Design workspace**

增加当前商家/店铺选择、商品表格、商品编辑表单、SKU 表格和发布/归档操作；保存成功后 invalidate 相关 TanStack Query，避免显示过期目录。

- [x] **Step 5: Run frontend Green**

Run: `pnpm --filter @homepilot/console test`; `pnpm --filter @homepilot/console build`; `pnpm --filter @homepilot/console lint`  
Expected: all console tests/build/lint pass。

- [x] **Step 6: Record task checkpoint (do not commit independently)**

保留本 Task 代码和测试；不创建独立提交。

### Task 10: 端到端回归、文档和学习材料

**状态：已完成（等待用户提交功能 PR）**

**Files:**
- Modify: `scripts/verify_stack.ps1`, `HANDOFF.md`, `docs/handover/2026-08-06-homepilot-handoff.md`, `task_plan.md`, `progress.md`
- Create: `.learning/2026-08-10-product-discovery-ui.md`, `backend/tests/integration/test_search_stack.py`（若 Task 1 未创建）

- [x] **Step 1: Add verification gates**

`verify_stack.ps1` 增加 ES Compose 配置、健康状态、`/_cluster/health` 和索引 alias 检查；脚本失败时输出 ES 日志，不写入业务数据。

- [x] **Step 2: Run complete verification**

按目录运行后端 `uv run pytest -q`、`uv run ruff check .`；前端 test/build/lint；根目录运行 `./scripts/verify_stack.ps1`。预期后端、双前端、MySQL/Redis/Qdrant/MinIO/Elasticsearch 全部通过。

- [x] **Step 3: Write data-flow explanation and five learning questions**

在被 `.learning/` 忽略的文件中写 2 个“是什么”、2 个“为什么”、1 个“如果……会怎样”及参考答案，覆盖类目、ES 文档、Outbox、MySQL 二次校验和索引故障。

- [x] **Step 4: Refresh handoff documents**

记录已验证能力、测试数量、ES 本地启动方式、索引重建命令和下一模块；不记录易变分支/PR 合并状态。

- [ ] **Step 5: Final review and one feature PR**

用户确认 `git diff --cached --stat` 只包含本模块代码、测试、规格/计划和交接更新后，创建一个功能 PR；不要为交接文档再创建第二个 PR。

## 验收命令汇总

```powershell
# backend
uv run pytest -q
uv run ruff check .
uv run alembic check

# frontend
pnpm run test
pnpm run build
pnpm run lint

# root
.\scripts\verify_stack.ps1
```
