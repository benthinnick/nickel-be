from decimal import Decimal
from uuid import uuid4

from app.core.constants import DEFAULT_CURRENCY, DEFAULT_SEED_STOCK
from app.domain.models.product import Product, ProductStatus
from app.repositories.product_repository import (
    ARCHIVED_ID,
    COFFEE_ID,
    DEMO_SELLER_ID,
    HONEY_ID,
    TEA_ID,
)


def make_product(
    *,
    sku: str = "SKU-TEST",
    name: str = "Test Product",
    status: ProductStatus = ProductStatus.ACTIVE,
    price: Decimal = Decimal("10.00"),
    seller_id=DEMO_SELLER_ID,
    stock: int = DEFAULT_SEED_STOCK,
) -> Product:
    return Product(
        id=uuid4(),
        seller_id=seller_id,
        sku=sku,
        name=name,
        description="Test description",
        price=price,
        currency=DEFAULT_CURRENCY,
        status=status,
        stock=stock,
        image_url=None,
    )


__all__ = [
    "ARCHIVED_ID",
    "COFFEE_ID",
    "DEMO_SELLER_ID",
    "HONEY_ID",
    "TEA_ID",
    "make_product",
]
