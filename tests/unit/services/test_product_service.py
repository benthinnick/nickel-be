from uuid import uuid4

import pytest

from app.core.exceptions import ProductNotFoundError
from app.repositories.product_repository import (
    ARCHIVED_ID,
    COFFEE_ID,
    InMemoryProductRepository,
)
from app.services.product_service import ProductService
from tests.fixtures.products import make_product


async def test_list_products_returns_only_active() -> None:
    service = ProductService(InMemoryProductRepository.with_seed_data())

    products, total = await service.list_products(limit=20, offset=0)

    assert total == 3
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
