"""Publish in-app notifications to the frontend over Redis."""

import logging

from redis import Redis
from redis.exceptions import RedisError

from cekrir.schemas import NotificationRead

logger = logging.getLogger(__name__)
NOTIFICATION_CHANNEL = "cekrir:notifications"


class FrontendNotificationPublisher:
    def __init__(self, client: Redis):
        self.client = client

    def publish(self, notification: NotificationRead) -> None:
        try:
            self.client.publish(NOTIFICATION_CHANNEL, notification.model_dump_json())
        except RedisError:
            # The database row remains available through the REST endpoint.
            logger.warning("Could not publish live notification event")
