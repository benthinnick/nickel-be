from app.domain.models.product import ProductStatus
from app.repositories.product_repository import (
    ARCHIVED_ID,
    COFFEE_ID,
    InMemoryProductRepository,
)
from tests.fixtures.products import make_product


async def test_list_active_excludes_inactive() -> None:
    repository = InMemoryProductRepository.with_seed_data()

    products, total = await repository.list_active(limit=10, offset=0)

    ids = {product.id for product in products}
    assert ARCHIVED_ID not in ids
    assert COFFEE_ID in ids
    assert total == 3
    assert all(product.status == ProductStatus.ACTIVE for product in products)


async def test_list_active_applies_limit_and_offset() -> None:
    repository = InMemoryProductRepository.with_seed_data()

    first_page, total = await repository.list_active(limit=1, offset=0)
    second_page, _ = await repository.list_active(limit=1, offset=1)

    assert total == 3
    assert len(first_page) == 1
    assert len(second_page) == 1
    assert first_page[0].id != second_page[0].id


async def test_get_by_id_returns_product() -> None:
    repository = InMemoryProductRepository.with_seed_data()

    product = await repository.get_by_id(COFFEE_ID)

    assert product is not None
    assert product.sku == "SKU-COFFEE-250"


async def test_get_by_id_returns_none_for_unknown() -> None:
    repository = InMemoryProductRepository.with_seed_data()

    product = await repository.get_by_id(make_product().id)

    assert product is None
