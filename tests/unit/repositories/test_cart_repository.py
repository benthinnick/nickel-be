from uuid import UUID

from fakeredis import FakeAsyncRedis

from app.domain.models.cart import Cart, CartItem, session_cart_key
from app.repositories.cart_repository import RedisCartRepository
from app.repositories.product_repository import COFFEE_ID, TEA_ID


async def test_redis_cart_round_trip_and_pop() -> None:
    redis = FakeAsyncRedis(decode_responses=True)
    repository = RedisCartRepository(redis, ttl_seconds=60)
    owner_key = session_cart_key("session-a")
    cart = Cart(
        owner_key=owner_key,
        items=(
            CartItem(product_id=COFFEE_ID, quantity=2),
            CartItem(product_id=TEA_ID, quantity=1),
        ),
    )

    await repository.save(cart)
    loaded = await repository.get(owner_key)
    popped = await repository.pop(owner_key)
    missing = await repository.get(owner_key)

    assert loaded is not None
    assert loaded.items[0].product_id == UUID(str(COFFEE_ID))
    assert popped is not None
    assert popped.items[0].quantity == 2
    assert missing is None
    await redis.aclose()
