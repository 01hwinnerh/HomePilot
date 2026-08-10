# 商家目录基础设计规格

## 1. 背景与目标

HomePilot 已经具备用户认证、商家成员关系、`TenantContext` 和租户硬隔离能力。下一步建立最小可扩展的商家目录基础，让两个演示商家都能拥有自己的店铺、商品和 SKU，并为后续库存、购物车、订单和前端商品浏览提供稳定数据契约。

本规格只覆盖目录基础，不提前耦合交易库存或文件存储。

## 2. 范围

### 包含

- `Merchant 1:N Store`；
- `Store 1:N Product`；
- `Product 1:N SKU`；
- 商品草稿、上架、归档生命周期；
- 商家租户范围内的 Store/Product/SKU 管理 API；
- 顾客公开读取已上架商品的 API；
- MySQL 迁移、约束、租户隔离和状态转换测试。

### 不包含

- 库存数量、预占和扣减；
- 图片、MinIO 对象和媒体处理；
- 购物车、订单、支付；
- 商品管理前端页面；
- 商品搜索、推荐和 RAG 索引；
- 单独的店铺内展示序号。

## 3. 领域模型

### Store

店铺属于一个商家，字段包括：

- `id`：全局自增内部主键；
- `merchant_id`：租户归属；
- `name`：展示名称；
- `slug`：店铺标识，在同一商家内唯一；
- `is_active`：是否允许公开展示和目录管理。

同一商家可以拥有多个 Store。数据库不设置“一商家只能一个 Store”的限制。

### Product

商品属于一个 Store，同时直接保存 `merchant_id` 以复用现有租户过滤机制。字段包括：

- `id`：全局自增内部主键；
- `merchant_id`；
- `store_id`；
- `name`；
- `description`；
- `status`：`DRAFT`、`PUBLISHED`、`ARCHIVED`；
- `created_at`、`updated_at`。

Product 的 `store_id` 决定店铺归属；服务层和数据库组合约束共同保证 Store 与 Merchant 一致。

### SKU

SKU 是商品真正可售卖的规格变体，不直接保存 `store_id`，通过 `Product → Store → Merchant` 归属店铺。字段包括：

- `id`：全局自增内部主键；
- `merchant_id`；
- `product_id`；
- `sku_code`：同一商家内唯一；
- `sku_name`；
- `variant_attributes`：受控 JSON 对象，例如 `{"color":"胡桃木","size":"1.8m"}`；
- `price_minor`：整数最小货币单位，不能为负数；
- `currency`：三位货币码，首版默认为 `CNY`；
- `is_active`；
- `created_at`、`updated_at`。

`variant_attributes` 只保存规格值，不保存价格、库存、权限或商家归属等核心事实。

所有内部 ID 都是全局唯一的；列表排序使用 `created_at` 或未来独立的 `sort_order`，不依赖自增 ID 连续。若将来需要隐藏可枚举 ID，可增加 UUID/ULID `public_id`，不改变租户授权逻辑。

## 4. 数据库约束

- `stores.merchant_id` 外键指向 `merchants.id`；
- `(stores.merchant_id, stores.slug)` 唯一；
- Store 增加 `(merchant_id, id)` 唯一键，供组合外键引用；
- Product 通过 `(merchant_id, store_id)` 组合外键引用 Store；
- SKU 通过 `(merchant_id, product_id)` 组合外键引用 Product；
- `(skus.merchant_id, skus.sku_code)` 唯一；
- `price_minor >= 0`；
- 状态和货币使用受控枚举/校验；
- 所有商家归属表保留 `merchant_id` 索引和时间戳。

组合外键使数据库层也能拒绝“把商家 A 的商品挂到商家 B 店铺”这类不一致数据；服务层仍执行清晰的业务错误转换。

## 5. API 边界

### 商家管理

以下接口需要 Bearer access token，并通过 `get_tenant_context`/`scoped_tenant_context` 验证 `merchant_id`：

- `POST /api/v1/merchants/{merchant_id}/stores`；
- `GET/PATCH /api/v1/merchants/{merchant_id}/stores/{store_id}`；
- `POST /api/v1/merchants/{merchant_id}/stores/{store_id}/products`；
- `GET/PATCH /api/v1/merchants/{merchant_id}/products/{product_id}`；
- `POST /api/v1/merchants/{merchant_id}/products/{product_id}/skus`；
- `PATCH /api/v1/merchants/{merchant_id}/skus/{sku_id}`；
- `POST /api/v1/merchants/{merchant_id}/products/{product_id}/publish`；
- `POST /api/v1/merchants/{merchant_id}/products/{product_id}/archive`。

创建或更新时，服务层验证所有路径 ID 属于当前 Merchant。跨商家资源返回 `404`，避免向普通成员暴露资源存在性；没有有效成员关系返回 `403`。

首版 OWNER 和 STAFF 均可执行基础目录管理，细粒度发布/价格权限留待后续权限模块。

### 顾客公开浏览

- `GET /api/v1/catalog/products`：只返回启用商家、启用店铺和 `PUBLISHED` 商品；
- `GET /api/v1/catalog/products/{product_id}`：按全局商品 ID 查询同样的公开条件，并返回启用 SKU。

公开详情即使命中草稿、归档或停用资源，也统一返回 `404`，不泄露隐藏资源状态。

## 6. 请求数据流与安全边界

商家写请求：

```text
Bearer token
→ 读取活跃 User
→ 查询活跃 MerchantMember + Merchant
→ 构造可信 TenantContext
→ 进入 tenant_scope
→ Service 校验 Store/Product/SKU 归属
→ TenantRepository + ORM 二次过滤查询/写入
→ 提交 MySQL 事务
```

顾客公开请求不建立商家成员上下文，但查询必须显式连接并过滤 Merchant、Store、Product、SKU 的启用/发布状态。JWT、URL 参数和前端表单都不能直接构造授权上下文。

## 7. 错误与事务语义

- 未登录或无效 Bearer：`401`；
- 已登录但不是目标商家成员：`403`；
- 跨商家或隐藏资源：`404`；
- 重复店铺 slug/SKU code：`409`；
- 不满足发布条件：`409`；
- 非法价格、货币或规格结构：`422`。

创建 Product、创建 SKU、发布/归档均在单个 MySQL 事务中执行。发布时至少存在一个启用 SKU，且店铺与商家仍处于启用状态；任何失败都回滚，不产生半成品关系。

## 8. 测试与验收

### 单元测试

- 状态转换和发布前置条件；
- `price_minor` 非负、货币码和规格 JSON 校验；
- 同商家 SKU 编码冲突、跨商家同码允许；
- Service 拒绝商品/店铺/商家关系不一致。

### 集成/API 测试

- Alembic upgrade/downgrade 与约束存在性；
- 两个商家各自拥有店铺、商品和 SKU；
- 商家 A 不能读取或修改商家 B 的 Store/Product/SKU；
- 篡改 URL 中任一 ID 得到预期 `403/404`；
- 草稿/归档/停用商家或店铺不出现在公开列表和详情；
- 商品无有效 SKU 时发布失败；
- 事务失败后不残留 Store/Product/SKU。

完成门槛：目录定向测试、后端全量 pytest、Ruff 均通过；不改变现有认证、租户隔离和前端回归结果。

## 9. 采用方案与未采用方案

采用全局自增内部 ID、商家直接归属字段和组合外键：实现简单、查询明确，并能与当前整数 ID 模型和 `MerchantOwnedMixin` 对齐。

未采用以下方案：

1. 每个商家独立自增 Product ID：公开详情必须携带商家上下文，容易混淆并增加路由复杂度；
2. SKU 直接重复保存 `store_id`：制造 Product/Store 不一致的冗余事实；
3. 用 Redis 保存目录或库存真源：失去 MySQL 事务、约束和审计能力。
