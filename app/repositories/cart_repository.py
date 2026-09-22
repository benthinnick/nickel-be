import json
from typing import Protocol
from uuid import UUID

from redis.asyncio import Redis

from app.domain.models.cart import Cart, CartItem


class CartRepository(Protocol):
    async def get(self, owner_key: str) -> Cart | None: ...

    async def save(self, cart: Cart) -> None: ...

    async def pop(self, owner_key: str) -> Cart | None: ...


class InMemoryCartRepository:
    def __init__(self) -> None:
        self._carts: dict[str, Cart] = {}

    async def get(self, owner_key: str) -> Cart | None:
        return self._carts.get(owner_key)

    async def save(self, cart: Cart) -> None:
        self._carts[cart.owner_key] = cart

    async def pop(self, owner_key: str) -> Cart | None:
        return self._carts.pop(owner_key, None)


class RedisCartRepository:
    def __init__(self, redis: Redis, *, ttl_seconds: int) -> None:
        self._redis = redis
        self._ttl_seconds = ttl_seconds

    def _key(self, owner_key: str) -> str:
        return f"cart:{owner_key}"

    async def get(self, owner_key: str) -> Cart | None:
        raw = await self._redis.get(self._key(owner_key))
        if raw is None:
            return None
        return _cart_from_payload(owner_key, raw)

    async def save(self, cart: Cart) -> None:
        payload = json.dumps(
            {
                "items": [
                    {"product_id": str(item.product_id), "quantity": item.quantity}
                    for item in cart.items
                ]
            }
        )
        await self._redis.set(self._key(cart.owner_key), payload, ex=self._ttl_seconds)

    async def pop(self, owner_key: str) -> Cart | None:
        raw = await self._redis.getdel(self._key(owner_key))
        if raw is None:
            return None
        return _cart_from_payload(owner_key, raw)


def _cart_from_payload(owner_key: str, raw: str | bytes) -> Cart:
    if isinstance(raw, bytes):
        raw = raw.decode("utf-8")
    data = json.loads(raw)
    items = tuple(
        CartItem(product_id=UUID(item["product_id"]), quantity=int(item["quantity"]))
        for item in data.get("items", [])
    )
    return Cart(owner_key=owner_key, items=items)
