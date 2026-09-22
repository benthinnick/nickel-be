from dataclasses import dataclass
from decimal import Decimal
from enum import StrEnum
from uuid import UUID


class ProductStatus(StrEnum):
    ACTIVE = "active"
    INACTIVE = "inactive"


@dataclass(frozen=True)
class Product:
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
