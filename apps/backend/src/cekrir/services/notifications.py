import logging

from redis import Redis
from redis.exceptions import RedisError

from cekrir.schemas import NotificationRead

logger = logging.getLogger(__name__)
NOTIFICATION_CHANNEL = "cekrir:notifications"


class NotificationPublisher:
    def __init__(self, client: Redis):
        self.client = client

    def publish(self, notification: NotificationRead) -> None:
        try:
            self.client.publish(NOTIFICATION_CHANNEL, notification.model_dump_json())
        except RedisError:
            # The database row is durable; a transient Redis failure must not lose it.
            logger.warning("Could not publish live notification event")
