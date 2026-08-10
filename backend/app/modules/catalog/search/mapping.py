CATALOG_PRODUCT_INDEX_ALIAS = "catalog-products-read"
CATALOG_PRODUCT_INDEX_VERSION = "catalog-products-v1"


def catalog_product_mapping() -> dict[str, object]:
    return {
        "mappings": {
            "properties": {
                "product_id": {"type": "keyword"},
                "merchant_id": {"type": "keyword"},
                "store_id": {"type": "keyword"},
                "merchant_name": {"type": "text"},
                "store_name": {"type": "text"},
                "store_slug": {"type": "keyword"},
                "category_id": {"type": "keyword"},
                "category_path": {"type": "keyword"},
                "name": {"type": "text"},
                "description": {"type": "text"},
                "min_price_minor": {"type": "integer"},
                "currency": {"type": "keyword"},
                "active_skus": {
                    "type": "nested",
                    "properties": {
                        "sku_id": {"type": "keyword"},
                        "sku_name": {"type": "text"},
                        "variant_attributes": {"type": "object"},
                        "price_minor": {"type": "integer"},
                        "currency": {"type": "keyword"},
                    },
                },
            }
        }
    }
