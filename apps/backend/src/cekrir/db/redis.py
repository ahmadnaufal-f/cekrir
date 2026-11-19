import logging

from redis import Redis
from redis.asyncio import Redis as AsyncRedis
from redis.exceptions import RedisError

logger = logging.getLogger(__name__)


class RedisConnections:
    def __init__(self, url: str):
        options = {"decode_responses": True, "socket_connect_timeout": 1}
        self.client = Redis.from_url(url, socket_timeout=1, **options)
        self.async_client = AsyncRedis.from_url(url, socket_timeout=5, **options)
        self.available = False

    def check(self) -> None:
        try:
            self.client.ping()
            self.available = True
        except RedisError:
            logger.warning("Redis is unavailable; live notifications are disabled")

    async def close(self) -> None:
        self.client.close()
        await self.async_client.aclose()
