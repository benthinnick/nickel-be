from uuid import UUID

from app.core.exceptions import ProductNotFoundError
from app.domain.models.product import Product, ProductStatus
from app.infrastructure.kafka.schemas.events import ProductCreatedPayload
from app.infrastructure.sanitization.html import sanitize_product_fields
from app.repositories.product_repository import ProductRepository


class ProductService:
    def __init__(self, repository: ProductRepository) -> None:
        self._repository = repository

    async def list_products(self, *, limit: int, offset: int) -> tuple[list[Product], int]:
        return await self._repository.list_active(limit=limit, offset=offset)

    async def get_product(self, product_id: UUID) -> Product:
        product = await self._repository.get_by_id(product_id)
        if product is None or product.status != ProductStatus.ACTIVE:
            raise ProductNotFoundError(product_id)
        return product

    async def apply_created(self, payload: ProductCreatedPayload) -> Product:
        existing = await self._repository.get_by_id(payload.product_id)
        if existing is not None:
            return existing
        sku, name, description, image_url = sanitize_product_fields(
            sku=payload.sku,
            name=payload.name,
            description=payload.description,
            image_url=payload.image_url,
        )
        product = Product(
            id=payload.product_id,
            seller_id=payload.seller_id,
            sku=sku,
            name=name,
            description=description,
            price=payload.price,
            currency=payload.currency,
            status=ProductStatus.ACTIVE,
            stock=payload.stock,
            image_url=image_url,
        )
        await self._repository.add(product)
        return product
