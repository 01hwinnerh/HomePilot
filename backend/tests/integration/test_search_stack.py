import asyncio

from elasticsearch import AsyncElasticsearch

from app.core.config import Settings


def test_elasticsearch_is_reachable_on_the_configured_local_url() -> None:
    asyncio.run(_assert_elasticsearch_is_reachable())


async def _assert_elasticsearch_is_reachable() -> None:
    settings = Settings(
        auth_jwt_secret="test-signing-secret-that-is-never-used-outside-this-test",
    )
    client = AsyncElasticsearch(settings.elasticsearch_url)
    try:
        info = await client.info()
    finally:
        await client.close()

    assert str(info["version"]["number"]).startswith("8.")
