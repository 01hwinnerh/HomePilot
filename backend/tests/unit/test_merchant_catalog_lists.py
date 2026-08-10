from app.main import app


def test_merchant_catalog_exposes_scoped_collection_routes() -> None:
    paths = app.openapi()["paths"]

    assert "get" in paths["/api/v1/merchants/{merchant_id}/stores"]
    assert "get" in paths["/api/v1/merchants/{merchant_id}/products"]
    assert "get" in paths["/api/v1/merchants/{merchant_id}/products/{product_id}/skus"]
