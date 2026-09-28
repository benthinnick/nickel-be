from app.infrastructure.clients.search.client import InMemorySearchIndex
from app.services.search_service import SearchService
from tests.fixtures.products import make_product


async def test_search_by_name_finds_matching_products() -> None:
    index = InMemorySearchIndex()
    search = SearchService(index)
    coffee = make_product(name="Ethiopian Coffee Beans", sku="SKU-A")
    tea = make_product(name="Earl Grey Tea", sku="SKU-B")
    await search.index_product(coffee)
    await search.index_product(tea)

    hits, total = await search.search_by_name("coffee", limit=10, offset=0)

    assert total == 1
    assert hits[0].id == coffee.id


async def test_delete_removes_product_from_search() -> None:
    index = InMemorySearchIndex()
    search = SearchService(index)
    product = make_product(name="Zaatar Blend")
    await search.index_product(product)
    await search.delete_product(product.id)

    hits, total = await search.search_by_name("Zaatar", limit=10, offset=0)

    assert total == 0
    assert hits == []


async def test_reindex_after_delete_restores_hit() -> None:
    index = InMemorySearchIndex()
    search = SearchService(index)
    product = make_product(name="Sumac")
    await search.index_product(product)
    await search.delete_product(product.id)
    await search.index_product(product)

    hits, total = await search.search_by_name("sumac", limit=10, offset=0)

    assert total == 1
    assert hits[0].id == product.id


async def test_duplicate_index_does_not_duplicate_hits() -> None:
    index = InMemorySearchIndex()
    search = SearchService(index)
    product = make_product(name="Honey")
    await search.index_product(product)
    await search.index_product(product)

    hits, total = await search.search_by_name("Honey", limit=10, offset=0)

    assert total == 1
    assert hits[0].id == product.id


async def test_suggest_names_prefers_prefix_and_limits() -> None:
    index = InMemorySearchIndex()
    search = SearchService(index)
    coffee = make_product(name="Ethiopian Coffee Beans", sku="SKU-A")
    cocoa = make_product(name="Cocoa Nibs", sku="SKU-B")
    tea = make_product(name="Earl Grey Tea", sku="SKU-C")
    await search.index_product(coffee)
    await search.index_product(cocoa)
    await search.index_product(tea)

    suggestions = await search.suggest_names("cof")

    assert suggestions == ["Ethiopian Coffee Beans"]


async def test_suggest_names_prefers_prefix_then_contains_and_caps_limit() -> None:
    index = InMemorySearchIndex()
    search = SearchService(index)
    names = [
        "Coffee Blend",
        "Coffee Cake",
        "Coffee Filter",
        "Coffee Grounds",
        "Coffee Mug",
        "Ethiopian Coffee Beans",
        "Instant Coffee Mix",
    ]
    for i, name in enumerate(names):
        await search.index_product(make_product(name=name, sku=f"SKU-{i}"))

    suggestions = await search.suggest_names("cof", limit=5)

    assert suggestions == [
        "Coffee Blend",
        "Coffee Cake",
        "Coffee Filter",
        "Coffee Grounds",
        "Coffee Mug",
    ]
    assert "Ethiopian Coffee Beans" not in suggestions


async def test_suggest_names_omits_deleted_products() -> None:
    index = InMemorySearchIndex()
    search = SearchService(index)
    product = make_product(name="Ethiopian Coffee Beans")
    await search.index_product(product)
    await search.delete_product(product.id)

    suggestions = await search.suggest_names("cof")

    assert suggestions == []
