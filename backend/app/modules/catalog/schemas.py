from pydantic import BaseModel, ConfigDict, Field, field_validator

type JsonScalar = str | int | float | bool | None


class StoreCreate(BaseModel):
    name: str = Field(min_length=1, max_length=160)
    slug: str = Field(min_length=1, max_length=160, pattern=r"^[a-z0-9]+(?:-[a-z0-9]+)*$")


class StoreUpdate(BaseModel):
    name: str | None = Field(default=None, min_length=1, max_length=160)
    is_active: bool | None = None


class StoreResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    merchant_id: int
    name: str
    slug: str
    is_active: bool


class ProductCreate(BaseModel):
    store_id: int = Field(gt=0)
    category_id: int = Field(gt=0)
    name: str = Field(min_length=1, max_length=200)
    description: str = Field(default="", max_length=4000)


class ProductUpdate(BaseModel):
    category_id: int | None = Field(default=None, gt=0)
    name: str | None = Field(default=None, min_length=1, max_length=200)
    description: str | None = Field(default=None, max_length=4000)


class ProductResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    merchant_id: int
    store_id: int
    category_id: int
    name: str
    description: str
    status: str


class SKUCreate(BaseModel):
    product_id: int = Field(gt=0)
    sku_code: str = Field(min_length=1, max_length=120)
    sku_name: str = Field(min_length=1, max_length=200)
    variant_attributes: dict[str, JsonScalar] = Field(default_factory=dict)
    price_minor: int = Field(ge=0)
    currency: str = Field(default="CNY", min_length=3, max_length=3)

    @field_validator("currency", mode="before")
    @classmethod
    def normalize_currency(cls, value: str) -> str:
        return str(value).upper()


class SKUUpdate(BaseModel):
    sku_name: str | None = Field(default=None, min_length=1, max_length=200)
    variant_attributes: dict[str, JsonScalar] | None = None
    price_minor: int | None = Field(default=None, ge=0)
    is_active: bool | None = None


class SKUResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    merchant_id: int
    product_id: int
    sku_code: str
    sku_name: str
    variant_attributes: dict[str, JsonScalar]
    price_minor: int
    currency: str
    is_active: bool


class PublicSKUResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    sku_code: str
    sku_name: str
    variant_attributes: dict[str, JsonScalar]
    price_minor: int
    currency: str


class PublicProductResponse(BaseModel):
    id: int
    merchant_id: int
    merchant_name: str
    store_id: int
    store_name: str
    store_slug: str
    category_id: int
    category_name: str
    name: str
    description: str
    skus: list[PublicSKUResponse]


class CategoryResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    parent_id: int | None
    slug: str
    name: str
    sort_order: int
