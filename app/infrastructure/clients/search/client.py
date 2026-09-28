from decimal import Decimal
from typing import Protocol
from uuid import UUID

from app.core.config import Settings
from app.core.constants import PRODUCTS_SEARCH_INDEX
from app.domain.models.product import Product, ProductStatus


class SearchIndex(Protocol):
    async def ensure_index(self) -> None: ...

    async def index(self, product: Product) -> None: ...

    async def delete(self, product_id: UUID) -> None: ...

    async def search_by_name(
        self,
        query: str,
        *,
        limit: int,
        offset: int,
    ) -> tuple[list[Product], int]: ...

    async def suggest_names(self, query: str, *, limit: int) -> list[str]: ...

    async def aclose(self) -> None: ...


class InMemorySearchIndex:
    def __init__(self) -> None:
        self._products: dict[UUID, Product] = {}

    async def ensure_index(self) -> None:
        return

    async def index(self, product: Product) -> None:
        self._products[product.id] = product

    async def delete(self, product_id: UUID) -> None:
        self._products.pop(product_id, None)

    async def search_by_name(
        self,
        query: str,
        *,
        limit: int,
        offset: int,
    ) -> tuple[list[Product], int]:
        needle = query.casefold().strip()
        hits = [product for product in self._products.values() if needle in product.name.casefold()]
        hits.sort(key=lambda product: product.name.casefold())
        return hits[offset : offset + limit], len(hits)

    async def suggest_names(self, query: str, *, limit: int) -> list[str]:
        needle = query.casefold().strip()
        if not needle:
            return []
        names = {product.name for product in self._products.values()}
        prefix = sorted(
            (name for name in names if name.casefold().startswith(needle)),
            key=str.casefold,
        )
        contains = sorted(
            (
                name
                for name in names
                if needle in name.casefold() and not name.casefold().startswith(needle)
            ),
            key=str.casefold,
        )
        return (prefix + contains)[:limit]

    async def aclose(self) -> None:
        return


class ElasticsearchSearchIndex:
    def __init__(self, url: str) -> None:
        from elasticsearch import AsyncElasticsearch

        self._client = AsyncElasticsearch(url)

    async def ensure_index(self) -> None:
        exists = await self._client.indices.exists(index=PRODUCTS_SEARCH_INDEX)
        if exists:
            return
        await self._client.indices.create(
            index=PRODUCTS_SEARCH_INDEX,
            mappings={
                "properties": {
                    "id": {"type": "keyword"},
                    "seller_id": {"type": "keyword"},
                    "sku": {"type": "keyword"},
                    "name": {"type": "text"},
                    "description": {"type": "text"},
                    "price": {"type": "keyword"},
                    "currency": {"type": "keyword"},
                    "status": {"type": "keyword"},
                    "stock": {"type": "integer"},
                    "image_url": {"type": "keyword"},
                }
            },
        )

    async def index(self, product: Product) -> None:
        await self._client.index(
            index=PRODUCTS_SEARCH_INDEX,
            id=str(product.id),
            document=_to_document(product),
            refresh=True,
        )

    async def delete(self, product_id: UUID) -> None:
        from elasticsearch import NotFoundError

        try:
            await self._client.delete(
                index=PRODUCTS_SEARCH_INDEX,
                id=str(product_id),
                refresh=True,
            )
        except NotFoundError:
            return

    async def search_by_name(
        self,
        query: str,
        *,
        limit: int,
        offset: int,
    ) -> tuple[list[Product], int]:
        response = await self._client.search(
            index=PRODUCTS_SEARCH_INDEX,
            from_=offset,
            size=limit,
            query={"match": {"name": {"query": query}}},
        )
        hits = response["hits"]["hits"]
        total = int(response["hits"]["total"]["value"])
        return [_from_document(hit["_source"]) for hit in hits], total

    async def suggest_names(self, query: str, *, limit: int) -> list[str]:
        needle = query.strip()
        if not needle:
            return []
        response = await self._client.search(
            index=PRODUCTS_SEARCH_INDEX,
            size=max(limit * 10, 50),
            query={"match_phrase_prefix": {"name": {"query": needle}}},
            _source=["name"],
        )
        suggestions: list[str] = []
        seen: set[str] = set()
        for hit in response["hits"]["hits"]:
            name = hit["_source"]["name"]
            if name in seen:
                continue
            seen.add(name)
            suggestions.append(name)
            if len(suggestions) >= limit:
                break
        return suggestions

    async def aclose(self) -> None:
        await self._client.close()


def create_search_index(settings: Settings) -> SearchIndex:
    if settings.elasticsearch_url.startswith("memory://"):
        return InMemorySearchIndex()
    return ElasticsearchSearchIndex(settings.elasticsearch_url)


def _to_document(product: Product) -> dict:
    return {
        "id": str(product.id),
        "seller_id": str(product.seller_id),
        "sku": product.sku,
        "name": product.name,
        "description": product.description,
        "price": str(product.price),
        "currency": product.currency,
        "status": product.status.value,
        "stock": product.stock,
        "image_url": product.image_url,
    }


def _from_document(document: dict) -> Product:
    return Product(
        id=UUID(document["id"]),
        seller_id=UUID(document["seller_id"]),
        sku=document["sku"],
        name=document["name"],
        description=document["description"],
        price=Decimal(document["price"]),
        currency=document["currency"],
        status=ProductStatus(document["status"]),
        stock=int(document["stock"]),
        image_url=document.get("image_url"),
    )
