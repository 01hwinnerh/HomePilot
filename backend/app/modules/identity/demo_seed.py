"""Local-only seed data for demonstrating HomePilot identity boundaries."""

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import Settings
from app.core.security import hash_password
from app.modules.identity.models import User
from app.modules.merchants.models import Merchant, MerchantMember, MerchantMemberRole

DEMO_PLATFORM_ADMIN_EMAIL = "platform.admin@homepilot.dev"
DEMO_MERCHANT_OWNER_A_EMAIL = "merchant.a.owner@homepilot.dev"
DEMO_MERCHANT_OWNER_B_EMAIL = "merchant.b.owner@homepilot.dev"
LEGACY_DEMO_EMAIL_MIGRATIONS = (
    ("platform.admin@homepilot.local", DEMO_PLATFORM_ADMIN_EMAIL),
    ("merchant.a.owner@homepilot.local", DEMO_MERCHANT_OWNER_A_EMAIL),
    ("merchant.b.owner@homepilot.local", DEMO_MERCHANT_OWNER_B_EMAIL),
)
DEMO_MERCHANT_A_NAME = "HomePilot Demo Merchant A"
DEMO_MERCHANT_B_NAME = "HomePilot Demo Merchant B"


class DemoSeedConflictError(ValueError):
    """Raised when an existing record is unsafe to treat as HomePilot demo data."""


class MissingDemoSeedPassword(ValueError):
    """Raised before a seed command can write data without an explicit password."""


def require_demo_seed_password(settings: Settings) -> str:
    """Read the local-only demo password without ever logging its value."""

    if settings.demo_seed_password is None:
        raise MissingDemoSeedPassword(
            "DEMO_SEED_PASSWORD must be set in the local .env before seeding demo data."
        )
    password = settings.demo_seed_password.get_secret_value()
    if not password:
        raise MissingDemoSeedPassword(
            "DEMO_SEED_PASSWORD must be set in the local .env before seeding demo data."
        )
    return password


async def seed_identity_demo_data(session: AsyncSession, *, password: str) -> None:
    """Create the minimum local identities needed to demonstrate tenant boundaries."""

    await _migrate_legacy_demo_emails(session)
    await _get_or_create_user(
        session,
        email=DEMO_PLATFORM_ADMIN_EMAIL,
        password=password,
        is_platform_admin=True,
    )
    owner_a = await _get_or_create_user(
        session,
        email=DEMO_MERCHANT_OWNER_A_EMAIL,
        password=password,
        is_platform_admin=False,
    )
    owner_b = await _get_or_create_user(
        session,
        email=DEMO_MERCHANT_OWNER_B_EMAIL,
        password=password,
        is_platform_admin=False,
    )
    merchant_a = await _get_or_create_merchant(session, name=DEMO_MERCHANT_A_NAME)
    merchant_b = await _get_or_create_merchant(session, name=DEMO_MERCHANT_B_NAME)
    await session.flush()

    await _get_or_create_owner_membership(
        session,
        user=owner_a,
        merchant=merchant_a,
    )
    await _get_or_create_owner_membership(
        session,
        user=owner_b,
        merchant=merchant_b,
    )
    await session.flush()


async def _migrate_legacy_demo_emails(session: AsyncSession) -> None:
    for legacy_email, current_email in LEGACY_DEMO_EMAIL_MIGRATIONS:
        legacy_user = await session.scalar(select(User).where(User.email == legacy_email))
        if legacy_user is None:
            continue

        current_user = await session.scalar(select(User).where(User.email == current_email))
        if current_user is not None and current_user.id != legacy_user.id:
            raise DemoSeedConflictError(
                f"Both legacy and current demo emails exist: {legacy_email}, {current_email}."
            )

        legacy_user.email = current_email
    await session.flush()


async def _get_or_create_user(
    session: AsyncSession,
    *,
    email: str,
    password: str,
    is_platform_admin: bool,
) -> User:
    existing = await session.scalar(select(User).where(User.email == email))
    if existing is not None:
        expected_identity = (
            "an active platform administrator"
            if is_platform_admin
            else "an active merchant owner"
        )
        if (
            not existing.is_active
            or existing.is_platform_admin is not is_platform_admin
        ):
            raise DemoSeedConflictError(
                f"Existing user {email} is not {expected_identity}."
            )
        return existing

    user = User(
        email=email,
        password_hash=hash_password(password),
        is_active=True,
        is_platform_admin=is_platform_admin,
    )
    session.add(user)
    return user


async def _get_or_create_merchant(session: AsyncSession, *, name: str) -> Merchant:
    existing = list(
        (await session.scalars(select(Merchant).where(Merchant.name == name))).all()
    )
    if len(existing) > 1:
        raise DemoSeedConflictError(f"Multiple merchants use the demo name {name}.")
    if existing:
        merchant = existing[0]
        if not merchant.is_active:
            raise DemoSeedConflictError(f"Existing merchant {name} is inactive.")
        return merchant

    merchant = Merchant(name=name, is_active=True)
    session.add(merchant)
    return merchant


async def _get_or_create_owner_membership(
    session: AsyncSession,
    *,
    user: User,
    merchant: Merchant,
) -> MerchantMember:
    existing = await session.scalar(
        select(MerchantMember).where(
            MerchantMember.user_id == user.id,
            MerchantMember.merchant_id == merchant.id,
        )
    )
    if existing is not None:
        if existing.role is not MerchantMemberRole.OWNER or not existing.is_active:
            raise DemoSeedConflictError(
                "Existing demo merchant membership is not an active OWNER relationship."
            )
        return existing

    membership = MerchantMember(
        user_id=user.id,
        merchant_id=merchant.id,
        role=MerchantMemberRole.OWNER,
        is_active=True,
    )
    session.add(membership)
    return membership
