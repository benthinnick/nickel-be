from redis.asyncio import Redis

from app.core.config import Settings


def create_redis_client(settings: Settings) -> Redis:
    if settings.redis_url.startswith("fakeredis://"):
        from fakeredis import FakeAsyncRedis

        return FakeAsyncRedis(decode_responses=True)
    return Redis.from_url(settings.redis_url, decode_responses=True)
