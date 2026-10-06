from decimal import Decimal
from uuid import uuid4

import pytest

from app.core.exceptions import InvalidProductError, ProductNotFoundError
from app.infrastructure.kafka.schemas.events import ProductCreatedPayload
from app.repositories.product_repository import (
    ARCHIVED_ID,
    COFFEE_ID,
    DEMO_SELLER_ID,
    InMemoryProductRepository,
)
from app.services.product_service import ProductService
from tests.fixtures.products import make_product


async def test_list_products_returns_only_active() -> None:
    service = ProductService(InMemoryProductRepository.with_seed_data())

    products, total = await service.list_products(limit=20, offset=0)

    assert total == 6
    assert all(product.id != ARCHIVED_ID for product in products)


async def test_get_product_returns_active_product() -> None:
    service = ProductService(InMemoryProductRepository.with_seed_data())

    product = await service.get_product(COFFEE_ID)

    assert product.id == COFFEE_ID
    assert product.name == "Ethiopian Coffee Beans"


async def test_get_product_raises_when_missing() -> None:
    service = ProductService(InMemoryProductRepository.with_seed_data())

    with pytest.raises(ProductNotFoundError):
        await service.get_product(uuid4())


async def test_get_product_raises_when_inactive() -> None:
    service = ProductService(InMemoryProductRepository.with_seed_data())

    with pytest.raises(ProductNotFoundError):
        await service.get_product(ARCHIVED_ID)


async def test_list_products_uses_injected_repository() -> None:
    extra = make_product(name="Zaatar Blend")
    service = ProductService(InMemoryProductRepository([extra]))

    products, total = await service.list_products(limit=10, offset=0)

    assert total == 1
    assert products[0].name == "Zaatar Blend"


async def test_apply_created_sanitizes_text_fields() -> None:
    service = ProductService(InMemoryProductRepository([]))
    payload = ProductCreatedPayload(
        product_id=uuid4(),
        seller_id=DEMO_SELLER_ID,
        sku="SKU-XSS",
        name="<script>alert(1)</script>Coffee",
        description="<b>Rich</b>",
        price=Decimal("10.00"),
        currency="ILS",
        stock=3,
        image_url=None,
        created_by_customer_id=uuid4(),
    )

    product = await service.apply_created(payload)

    assert "<" not in product.name
    assert "script" not in product.name.lower()
    assert "Coffee" in product.name
    assert product.description == "Rich"


async def test_apply_created_rejects_javascript_image_url() -> None:
    service = ProductService(InMemoryProductRepository([]))
    payload = ProductCreatedPayload(
        product_id=uuid4(),
        seller_id=DEMO_SELLER_ID,
        sku="SKU-BAD-IMG",
        name="Coffee",
        description="Safe",
        price=Decimal("10.00"),
        currency="ILS",
        stock=3,
        image_url="javascript:alert(1)",
        created_by_customer_id=uuid4(),
    )

    with pytest.raises(InvalidProductError):
        await service.apply_created(payload)
