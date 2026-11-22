from datetime import UTC, datetime
from unittest.mock import Mock, patch
from uuid import uuid4

from redis.exceptions import RedisError

from cekrir.config import Settings
from cekrir.schemas import NotificationRead
from cekrir.services.email import EmailUnavailable
from cekrir.services.notifications import NotificationPublisher


def event():
    return NotificationRead(
        id=uuid4(),
        shipment_id=uuid4(),
        title="Package",
        message="Arrived",
        created_at=datetime.now(UTC),
    )


def test_redis_failure_does_not_stop_email_channel():
    redis = Mock()
    redis.publish.side_effect = RedisError("unavailable")
    publisher = NotificationPublisher(redis)
    notification = event()
    with patch.object(publisher.email, "publish") as email:
        publisher.publish(notification)
    email.assert_called_once_with(notification)


def test_email_failure_does_not_stop_frontend_channel():
    redis = Mock()
    settings = Settings(
        _env_file=None,
        email_provider="resend",
        resend_api_key="re_test",
        resend_from="a@example.test",
    )
    session = Mock()
    session.scalar.return_value = uuid4()
    session.get.return_value = Mock(admin_user_id=uuid4())
    session.execute.return_value.all.return_value = [(uuid4(), "recipient@example.test")]
    factory = Mock()
    factory.return_value.__enter__ = Mock(return_value=session)
    factory.return_value.__exit__ = Mock(return_value=False)
    notification = event()
    with patch("cekrir.services.email_notifications.send_email", side_effect=EmailUnavailable):
        NotificationPublisher(redis, settings, factory).publish(notification)
    redis.publish.assert_called_once()
