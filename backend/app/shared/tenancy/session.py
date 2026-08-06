from collections.abc import Iterator
from contextlib import contextmanager
from contextvars import ContextVar

from sqlalchemy import event
from sqlalchemy.orm import ORMExecuteState, Session, with_loader_criteria

from app.shared.models.tenant import MerchantOwnedMixin
from app.shared.tenancy.context import TenantContext, require_trusted_tenant_context

_tenant_context: ContextVar[TenantContext | None] = ContextVar(
    "tenant_context",
    default=None,
)


@contextmanager
def tenant_scope(context: TenantContext) -> Iterator[TenantContext]:
    """Temporarily activate a server-verified tenant context for ORM reads."""

    require_trusted_tenant_context(context)
    token = _tenant_context.set(context)
    try:
        yield context
    finally:
        _tenant_context.reset(token)


def current_tenant_context() -> TenantContext | None:
    """Return the current server-created context, if the call is tenant-scoped."""

    return _tenant_context.get()


@event.listens_for(Session, "do_orm_execute")
def apply_tenant_criteria(execute_state: ORMExecuteState) -> None:
    """Add a second merchant filter to scoped ORM reads and bulk writes."""

    if not (execute_state.is_select or execute_state.is_update or execute_state.is_delete):
        return
    context = current_tenant_context()
    if context is None:
        return
    merchant_id = context.merchant_id
    execute_state.statement = execute_state.statement.options(
        with_loader_criteria(
            MerchantOwnedMixin,
            lambda model: model.merchant_id == merchant_id,
            include_aliases=True,
        )
    )
