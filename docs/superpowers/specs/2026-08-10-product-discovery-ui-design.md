# HomePilot 商品管理与商品发现 UI 设计规格

日期：2026-08-10  
状态：设计已获用户批准，待编写实施计划

## 1. 目标与边界

本模块将 Task 8 的商家目录基础接成一个可用的纵向闭环：

- Storefront 面向匿名顾客提供家居商品发现、关键词搜索、类目筛选和商品详情；
- Console 面向已认证商家成员提供店铺、商品和 SKU 管理；
- 两个演示商家的商品都能出现在公开搜索结果中，商品卡片显示来源商家；
- 目录查询直接引入 Elasticsearch，展示搜索索引、异步投影和最终一致性处理；
- MySQL 仍是商品、类目、SKU、店铺状态和公开资格的唯一真源。

明确不在本模块实现：购物车、库存数量、下单、结算、收藏、支付、物流和商家结算。

## 2. 用户体验

### Storefront

首页不枚举全部商家。页面提供：

- 搜索框，支持商品名、描述、材质、风格或品牌关键词；
- 家居类目入口：客厅、餐厅、卧室、书房、收纳、装饰及其叶子类目；
- 商品结果网格。一个关键词可以返回多个商家的商品；
- 商品卡片显示商品名、起售价、类目和“来自某店铺”；
- 商品详情显示描述、启用 SKU、规格属性、价格和来源店铺；
- 店铺/品牌搜索作为辅助入口，仅在用户主动搜索或点击商品来源时出现。

匿名顾客可以浏览全部公开结果；当前阶段不渲染购物车、结算或伪造的“加入购物车”按钮。登录顾客复用同一浏览体验，购买能力留给后续模块。

### Console

登录后从后端 `/me` 返回的实时 `memberships` 得到可访问商家。工作台包含：

- 当前商家身份和角色；
- 当前商家的店铺列表；
- 当前店铺的商品列表；
- 商品基本信息编辑；
- SKU 创建、规格、价格和启用状态编辑；
- 商品发布和归档操作。

平台管理员身份仍只展示平台身份，不在本模块增加跨商家代编辑入口。所有商家写操作继续由可信 `TenantContext` 约束。

## 3. 类目模型

新增 `Category` 树：`id`、`parent_id`、`slug`、`name`、`sort_order`、`is_active`。首版每个商品绑定一个叶子类目，避免过早引入多标签交集查询。未来需要多维属性时，可在不破坏主类目的情况下增加筛选属性表或受控 JSON。

`Product.category_id` 使用外键指向启用类目；迁移和 demo seed 为现有双商家商品补齐类目。

## 4. HTTP API

### 公开接口

```text
GET /api/v1/catalog/categories
GET /api/v1/catalog/products?q=&category=&offset=&limit=
GET /api/v1/catalog/products/{product_id}
GET /api/v1/catalog/merchants?q=&offset=&limit=
```

公开查询只返回：启用 Merchant、启用 Store、`PUBLISHED` Product 和至少一个启用 SKU。搜索结果中的店铺与商家名称来自后端，不信任前端拼接。

### 商家接口

```text
GET   /api/v1/merchants/{merchant_id}/stores
GET   /api/v1/merchants/{merchant_id}/stores/{store_id}/products
GET   /api/v1/merchants/{merchant_id}/products/{product_id}
POST  /api/v1/merchants/{merchant_id}/stores/{store_id}/products
PATCH /api/v1/merchants/{merchant_id}/products/{product_id}
POST  /api/v1/merchants/{merchant_id}/products/{product_id}/skus
PATCH /api/v1/merchants/{merchant_id}/skus/{sku_id}
POST  /api/v1/merchants/{merchant_id}/products/{product_id}/publish
POST  /api/v1/merchants/{merchant_id}/products/{product_id}/archive
```

实际路由可复用 Task 8 的写接口；新增列表接口不得接受裸 `merchant_id` 作为授权事实，必须先通过 `scoped_tenant_context` 获取可信租户上下文。跨商家资源继续统一返回 404。

## 5. Elasticsearch 读模型

使用版本化索引，例如 `catalog-products-v1`，通过 `catalog-products-read` alias 读取。具体 Elasticsearch 8.x patch 版本、官方 Python client 版本和镜像 digest 在实施前核验后固定，禁止使用浮动 `latest`。

一个 Product 对应一个搜索文档：

```text
product_id, merchant_id, store_id
merchant_name, store_name, store_slug
category_id, category_path
name, description
active_skus[]
min_price_minor, currency
```

- ID、归属、类目使用精确过滤字段；
- 商品名、描述、商家名和店铺名使用全文字段；
- `active_skus` 使用 `nested`，防止不同 SKU 的规格条件错误组合；
- 金额使用整数最小货币单位；
- 索引 mapping 和 analyzer 由应用显式管理，索引可从 MySQL 全量重建。

## 6. 写入、Outbox 与一致性

```text
Console 请求
  → TenantContext + CatalogService
  → MySQL 业务表与 outbox 在同一事务提交
  → Worker 消费 outbox
  → 从 MySQL 重读完整 Product
  → 可公开则幂等 index，不可公开则幂等 delete
```

事件覆盖商品创建/修改/发布/归档、类目变更、SKU 变更和商家/店铺启停。Worker 不直接相信旧事件载荷，而是以 MySQL 当前状态生成投影；重复事件必须安全。索引落后期间，公开搜索先从 Elasticsearch 得到候选 ID，再由 MySQL 二次校验公开资格并补全响应，不能因最终一致性泄露草稿或停用资源。

Elasticsearch 不可用时返回 `503 SEARCH_UNAVAILABLE`，Storefront 展示可重试的错误状态；不退化为无边界全量查询。

## 7. 前端技术边界

Storefront 和 Console 继续复用现有 workspace、认证客户端和内存 access token。当前路由数量较少，不新增 React Router；使用小型 `window.location.pathname` 路由适配层，未来路由复杂后再单独评估。

异步请求必须覆盖 loading、空结果、公开 404、网络错误、搜索 503 和 Console 认证恢复失败。Storefront 不直接连接 Elasticsearch。

## 8. TDD 与验收

- 类目迁移、叶子类目约束和双商家 seed；
- Elasticsearch mapping、索引创建、alias 和全量重建；
- Outbox 与业务事务的提交/rollback 原子性；
- Worker 重复消费、事件乱序、索引失败重试和不可公开资源删除；
- 公开关键词/类目搜索的跨商家结果、匿名访问和公开资格二次校验；
- Console 商家列表、商品/SKU 管理和跨商家 404 隔离；
- Storefront/Console Vitest、TypeScript、ESLint、生产构建；
- Docker Compose ES healthcheck、后端全量 pytest、Ruff、Alembic check 和 `verify_stack.ps1`。

完成后补充数据流讲解与 `.learning/` 五题材料，并把规格、计划、交接文档和进度更新纳入同一个功能 PR。

## 9. 未采用方案

- 首页枚举全部商家或用商家 tab 作为主筛选：不符合顾客按需求发现商品的路径，无法扩展到大量商家；
- 前端拉取全量商品再过滤：数据暴露、首屏和网络成本不可控；
- 只使用 MySQL 模糊查询：当前可用但无法体现搜索索引能力；
- 让 Elasticsearch 成为商品或授权真源：违反 MySQL 交易真源和租户安全边界；
- 本模块立即引入 OpenSearch：许可更宽松，但不符合用户明确的 Elasticsearch 学习目标。
