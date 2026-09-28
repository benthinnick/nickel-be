from decimal import Decimal
from uuid import UUID

from pydantic import BaseModel, ConfigDict

from app.domain.models.product import Product, ProductStatus


class ProductResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    seller_id: UUID
    sku: str
    name: str
    description: str
    price: Decimal
    currency: str
    status: ProductStatus
    stock: int
    image_url: str | None = None


class ProductListResponse(BaseModel):
    items: list[ProductResponse]
    total: int
    limit: int
    offset: int


class ProductAutocompleteResponse(BaseModel):
    queries: list[str]


def product_to_response(product: Product) -> ProductResponse:
    return ProductResponse(
        id=product.id,
        seller_id=product.seller_id,
        sku=product.sku,
        name=product.name,
        description=product.description,
        price=product.price,
        currency=product.currency,
        status=product.status,
        stock=product.stock,
        image_url=product.image_url,
    )


def product_list_to_response(
    products: list[Product],
    *,
    total: int,
    limit: int,
    offset: int,
) -> ProductListResponse:
    return ProductListResponse(
        items=[product_to_response(product) for product in products],
        total=total,
        limit=limit,
        offset=offset,
    )
