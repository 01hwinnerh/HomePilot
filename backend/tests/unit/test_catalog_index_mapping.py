from app.modules.catalog.search.mapping import CATALOG_PRODUCT_INDEX_ALIAS, catalog_product_mapping


def test_catalog_mapping_is_versioned_and_keeps_skus_nested() -> None:
    mapping = catalog_product_mapping()["mappings"]

    assert CATALOG_PRODUCT_INDEX_ALIAS == "catalog-products-read"
    assert mapping["properties"]["product_id"]["type"] == "keyword"
    assert mapping["properties"]["active_skus"]["type"] == "nested"
    assert mapping["properties"]["active_skus"]["properties"]["price_minor"]["type"] == "integer"
