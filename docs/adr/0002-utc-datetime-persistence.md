# ADR-0002：MySQL UTC 时间持久化边界

**状态：** 已接受  
**日期：** 2026-08-05

## 背景

HomePilot 的 refresh session、审计记录和后续订单、售后、Agent 动作都需要可靠的时间比较。MySQL `DATETIME` 不保存时区；SQLAlchemy 的 `DateTime(timezone=True)` 也不能让 MySQL 自动保留 `tzinfo`。若应用把读回的 naive 时间与 `datetime.now(UTC)` 比较，refresh 过期判断会出现 `TypeError` 或不一致。

## 决策

1. 应用层的领域时间统一为 UTC-aware `datetime`。
2. 建立共享 `UTCDateTime` 类型。它拒绝 naive 输入，把 aware 输入归一化为 UTC-naive `DATETIME` 写入 MySQL，并在读取时恢复 UTC-aware 值。
3. 建立 `utc_now()`，供 `created_at`、`updated_at` 的 ORM `default/onupdate` 使用；不以数据库本地时区的 `CURRENT_TIMESTAMP` 作为业务时间真源。
4. Alembic 迁移显式使用 MySQL 物理 `DateTime()`，与 `UTCDateTime` 的底层存储一致。
5. 对该类型执行无数据库单元测试和真实 MySQL round-trip 集成测试；测试覆盖非 UTC 输入归一化、naive 输入拒绝及安全比较。

## 后果

优点：服务、JWT、刷新会话和后续 Agent/订单模块可在 Python 层始终安全比较 aware UTC 时间，不依赖 Docker 或生产 MySQL 的服务器时区。

代价：所有领域时间字段都必须复用 `UTCDateTime`，直接 SQL 写入需要显式提供 UTC-naive 值；该项目首版通过 ORM 和领域服务写入业务数据，不把这视为限制。

## 不采用的方案

- 全项目约定 UTC-naive datetime：与现有 JWT 的 aware UTC 时间混用风险高，难以在代码审查中发现。
- 将时间存为 Unix timestamp 整数：可行但降低 MySQL 可读性和日期查询能力，不符合当前关系型业务模型。
- 仅使用 `DateTime(timezone=True)`：对 MySQL 没有实际时区持久化保证，不能解决问题。
