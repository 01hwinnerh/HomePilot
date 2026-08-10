"""CLI support for local catalog demo data."""

from app.core.database import close_database, get_database
from app.modules.catalog.demo_seed import CatalogSeedConflictError, seed_catalog_demo_data


async def run_catalog_seed_command() -> int:
    """Seed catalog data for both pre-existing demo merchants."""

    database = get_database()
    try:
        async with database.session() as session:
            try:
                await seed_catalog_demo_data(session)
                await session.commit()
            except CatalogSeedConflictError:
                print(
                    "Catalog seed rejected: existing records do not match "
                    "the expected demo catalog."
                )
                return 1
    finally:
        await close_database()

    print("Demo catalog seed completed. Re-running this command is safe.")
    return 0
