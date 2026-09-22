from dataclasses import dataclass
from uuid import UUID


def session_cart_key(session_id: str) -> str:
    return f"session:{session_id}"


def user_cart_key(user_id: UUID) -> str:
    return f"user:{user_id}"


@dataclass(frozen=True)
class CartOwner:
    key: str
    session_id: str
    user_id: UUID | None = None


@dataclass(frozen=True)
class CartItem:
    product_id: UUID
    quantity: int


@dataclass(frozen=True)
class Cart:
    owner_key: str
    items: tuple[CartItem, ...]
