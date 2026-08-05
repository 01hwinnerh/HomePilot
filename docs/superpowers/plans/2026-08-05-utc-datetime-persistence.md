# HomePilot UTC 时间持久化实施计划

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 在不新增依赖的前提下，让身份模型和后续领域模型能够在 MySQL 上安全持久化并比较 UTC-aware 时间。

**Architecture:** `UTCDateTime` 是共享 SQLAlchemy `TypeDecorator`，底层仍是 MySQL `DATETIME`。它在写入边界把 aware 时间转换为 UTC-naive，在读取边界恢复 aware UTC；`TimestampMixin` 用 Python 的 `utc_now()` 生成审计时间，不依赖数据库服务器时区。

**Tech Stack:** Python 3.12、SQLAlchemy 2.0、Alembic、MySQL 8.4、pytest。

---

## 文件与职责

| 路径 | 职责 |
|---|---|
| `backend/app/shared/models/utc_datetime.py` | `utc_now()` 与复用的 `UTCDateTime` 类型。 |
| `backend/app/shared/models/timestamps.py` | 统一使用 UTC 类型和 Python 默认时间。 |
| `backend/app/modules/identity/models.py` | `AuthSession` 的到期/撤销时间使用 UTC 类型。 |
| `backend/alembic/versions/20260805_0002_identity_and_tenancy.py` | 保持物理 MySQL `DateTime()`，移除服务器本地时间默认值。 |
| `backend/tests/unit/test_utc_datetime.py` | 归一化、读取恢复和 naive 输入拒绝。 |
| `backend/tests/integration/test_identity_migration.py` | 真实 MySQL refresh session 的 aware UTC round-trip。 |

## Task 1：共享 UTC 类型

- [x] **Step 1：编写 Red 单元测试。**

  在 `backend/tests/unit/test_utc_datetime.py` 写入：

  ```python
  from datetime import UTC, datetime, timedelta, timezone

  import pytest

  from app.shared.models.utc_datetime import UTCDateTime


  def test_utc_datetime_normalizes_and_restores_aware_values() -> None:
      value = datetime(2026, 8, 5, 20, tzinfo=timezone(timedelta(hours=8)))
      value_type = UTCDateTime()

      stored = value_type.process_bind_param(value, dialect=None)
      restored = value_type.process_result_value(stored, dialect=None)

      assert stored == datetime(2026, 8, 5, 12)
      assert restored == datetime(2026, 8, 5, 12, tzinfo=UTC)


  def test_utc_datetime_rejects_naive_values() -> None:
      with pytest.raises(ValueError, match="timezone-aware"):
          UTCDateTime().process_bind_param(datetime(2026, 8, 5, 12), dialect=None)
  ```

- [x] **Step 2：运行 Red。**

  在 `backend` 目录运行：

  ```powershell
  uv run pytest tests/unit/test_utc_datetime.py -q
  ```

  预期因共享类型尚不存在而失败；由助手执行并记录。

- [x] **Step 3：实现最小类型。**

  新建 `backend/app/shared/models/utc_datetime.py`：

  ```python
  from datetime import UTC, datetime

  from sqlalchemy import DateTime
  from sqlalchemy.types import TypeDecorator


  def utc_now() -> datetime:
      return datetime.now(UTC)


  class UTCDateTime(TypeDecorator[datetime]):
      impl = DateTime
      cache_ok = True

      def process_bind_param(self, value: datetime | None, dialect: object) -> datetime | None:
          if value is None:
              return None
          if value.tzinfo is None or value.utcoffset() is None:
              raise ValueError("UTCDateTime requires a timezone-aware datetime.")
          return value.astimezone(UTC).replace(tzinfo=None)

      def process_result_value(self, value: datetime | None, dialect: object) -> datetime | None:
          if value is None:
              return None
          if value.tzinfo is not None:
              return value.astimezone(UTC)
          return value.replace(tzinfo=UTC)
  ```

- [x] **Step 4：运行 Green。**

  在 `backend` 目录运行：

  ```powershell
  uv run pytest tests/unit/test_utc_datetime.py -q
  ```

  预期通过。

## Task 2：模型、迁移与真实数据库验证

- [x] **Step 1：编写 MySQL round-trip Red 测试。**

  在 `backend/tests/integration/test_identity_migration.py` 新增异步 helper：创建 `User(email="utc.roundtrip@homepilot.test", password_hash="not-a-secret")`，再创建带 UTC+08:00 `expires_at` 的 `AuthSession`；重新查询该会话并断言：

  ```python
  assert session.expires_at == datetime(2026, 8, 5, 12, tzinfo=UTC)
  assert session.expires_at.tzinfo is UTC
  assert session.expires_at > datetime(2026, 8, 5, 11, tzinfo=UTC)
  ```

  测试必须使用现有 `migrated_identity_database_url`，因此每轮均从 `base → head` 重建，不污染业务库 `homepilot`。

- [x] **Step 2：运行 Red。**

  在 `backend` 目录运行：

  ```powershell
  uv run pytest tests/integration/test_identity_migration.py -q
  ```

  预期在 MySQL round-trip 后得到 naive datetime 而失败；由助手执行并记录。

- [x] **Step 3：接入领域模型。**

  将 `TimestampMixin` 改为：

  ```python
  created_at: Mapped[datetime] = mapped_column(
      UTCDateTime(), default=utc_now, nullable=False
  )
  updated_at: Mapped[datetime] = mapped_column(
      UTCDateTime(), default=utc_now, onupdate=utc_now, nullable=False
  )
  ```

  将 `AuthSession.expires_at`、`AuthSession.revoked_at` 改为 `mapped_column(UTCDateTime(), ...)`。迁移中的所有领域时间使用 `sa.DateTime()`，并删除四张表的 `created_at`/`updated_at` `server_default=sa.func.now()`；这保证物理数据库不依赖其服务器时区。

- [ ] **Step 4：运行定向 Green。**

  在 `backend` 目录运行：

  ```powershell
  uv run pytest tests/unit/test_utc_datetime.py tests/unit/test_identity_models.py tests/integration/test_identity_migration.py tests/integration/test_migrations.py -q
  uv run ruff check .
  ```

  预期全部通过。

- [ ] **Step 5：验证 metadata 与迁移一致。**

  在 `backend` 目录运行：

  ```powershell
  uv run python -c "from alembic import command; from alembic.config import Config; from app.core.config import get_settings; config = Config('alembic.ini'); config.set_main_option('sqlalchemy.url', get_settings().test_database_url); command.check(config)"
  ```

  预期输出 `No new upgrade operations detected.`。

## Task 3：记录与交付

- [ ] 将 ADR-0002、身份规格、Task 2 实施计划、`findings.md` 与 `progress.md` 更新为实际测试结果。
- [ ] 该修订属于未提交的 Task 2 身份模型工作，不单独创建 Commit；随 `feat(identity): add users merchants and auth sessions` 一起提交和 PR。
