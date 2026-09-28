from dataclasses import dataclass
from uuid import UUID


def session_cart_key(session_id: str) -> str:
    return f"session:{session_id}"


def customer_cart_key(customer_id: UUID) -> str:
    return f"customer:{customer_id}"


@dataclass(frozen=True)
class CartOwner:
    key: str
    session_id: str
    customer_id: UUID | None = None


@dataclass(frozen=True)
class CartItem:
    product_id: UUID
    quantity: int


@dataclass(frozen=True)
class Cart:
    owner_key: str
    items: tuple[CartItem, ...]
