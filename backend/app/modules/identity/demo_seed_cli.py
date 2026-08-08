"""Command support for local HomePilot identity demo data."""

from app.core.config import get_settings
from app.core.database import close_database, get_database
from app.modules.identity.demo_seed import (
    DemoSeedConflictError,
    MissingDemoSeedPassword,
    require_demo_seed_password,
    seed_identity_demo_data,
)


async def run_demo_seed_command() -> int:
    """Seed local demo identities and return a shell-friendly exit status."""

    settings = get_settings()
    try:
        password = require_demo_seed_password(settings)
    except MissingDemoSeedPassword:
        print("Demo seed did not run: set DEMO_SEED_PASSWORD in the local .env first.")
        return 2

    database = get_database()
    try:
        async with database.session() as session:
            try:
                await seed_identity_demo_data(session, password=password)
                await session.commit()
            except DemoSeedConflictError:
                await session.rollback()
                print(
                    "Demo seed rejected: existing records do not match "
                    "the expected demo identity."
                )
                return 1
    finally:
        await close_database()

    print("Demo identity seed completed. Re-running this command is safe.")
    return 0
