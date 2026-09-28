from uuid import UUID

from app.core.constants import PRODUCT_AUTOCOMPLETE_LIMIT
from app.domain.models.product import Product
from app.infrastructure.clients.search.client import SearchIndex


class SearchService:
    def __init__(self, search_index: SearchIndex) -> None:
        self._index = search_index

    async def search_by_name(
        self,
        query: str,
        *,
        limit: int,
        offset: int,
    ) -> tuple[list[Product], int]:
        return await self._index.search_by_name(query, limit=limit, offset=offset)

    async def suggest_names(
        self,
        query: str,
        *,
        limit: int = PRODUCT_AUTOCOMPLETE_LIMIT,
    ) -> list[str]:
        return await self._index.suggest_names(query, limit=limit)

    async def index_product(self, product: Product) -> None:
        await self._index.index(product)

    async def delete_product(self, product_id: UUID) -> None:
        await self._index.delete(product_id)
