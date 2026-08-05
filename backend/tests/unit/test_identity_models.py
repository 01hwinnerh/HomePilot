from sqlalchemy import Table, UniqueConstraint

from app.modules.identity.models import AuthSession, User
from app.modules.merchants.models import Merchant, MerchantMember, MerchantMemberRole
from app.shared.models.tenant import MerchantOwnedMixin
from app.shared.models.timestamps import TimestampMixin
from app.shared.models.utc_datetime import UTCDateTime


def unique_constraint_columns(table: Table) -> set[frozenset[str]]:
    constraints = table.constraints
    return {
        frozenset(column.name for column in constraint.columns)
        for constraint in constraints
        if isinstance(constraint, UniqueConstraint)
    }


def test_membership_is_unique_per_user_and_merchant() -> None:
    assert frozenset({"user_id", "merchant_id"}) in unique_constraint_columns(
        MerchantMember.__table__
    )


def test_auth_session_stores_only_the_refresh_token_hash() -> None:
    assert "refresh_token_hash" in AuthSession.__table__.c
    assert "refresh_token" not in AuthSession.__table__.c


def test_user_email_has_an_explicit_unique_index() -> None:
    email_indexes = [
        index
        for index in User.__table__.indexes
        if tuple(column.name for column in index.columns) == ("email",)
    ]

    assert len(email_indexes) == 1
    assert email_indexes[0].unique is True


def test_membership_uses_the_shared_tenant_boundary() -> None:
    assert issubclass(MerchantMember, MerchantOwnedMixin)


def test_identity_models_share_timestamp_behavior() -> None:
    assert all(
        issubclass(model, TimestampMixin)
        for model in (User, AuthSession, Merchant, MerchantMember)
    )


def test_identity_audit_timestamps_use_the_utc_boundary() -> None:
    for model in (User, AuthSession, Merchant, MerchantMember):
        assert isinstance(model.__table__.c.created_at.type, UTCDateTime)
        assert isinstance(model.__table__.c.updated_at.type, UTCDateTime)


def test_membership_roles_are_limited_to_owner_and_staff() -> None:
    assert {role.value for role in MerchantMemberRole} == {"OWNER", "STAFF"}
    assert set(MerchantMember.__table__.c.role.type.enums) == {"OWNER", "STAFF"}
