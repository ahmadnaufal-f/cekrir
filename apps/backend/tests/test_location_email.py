from datetime import UTC, datetime
from unittest.mock import Mock, patch
from uuid import uuid4

import pytest
from sqlalchemy import select
from sqlalchemy.orm import Session

from cekrir.config import Settings
from cekrir.db.model import CameraDevice, Location, LocationMember, Role, Shipment, User
from cekrir.db.repository import ShipmentRepository
from cekrir.db.session import build_engine
from cekrir.schemas import NotificationRead
from cekrir.services.location_management import (
    CameraAlreadyAssigned,
    LocationResourceNotFound,
    add_camera,
    remove_member,
)
from cekrir.services.notifications import (
    EmailRecipientNotFound,
    NotificationPublisher,
    send_individual_email,
)


def test_location_email_recipients_and_single_user_authorization(database_url):
    engine = build_engine(database_url)
    suffix = uuid4().hex
    settings = Settings(
        _env_file=None,
        email_provider="resend",
        resend_api_key="test-key",
        resend_from="mail@example.test",
    )
    try:
        with engine.connect() as connection:
            transaction = connection.begin()
            try:
                with Session(bind=connection) as session:
                    roles = {r.code: r for r in session.scalars(select(Role))}

                    def user(name, role, *, verified=True, active=True):
                        result = User(
                            email=f"{name}-{suffix}@example.test",
                            full_name=name,
                            password_hash="unused",
                            role_record=roles[role],
                            is_active=active,
                            email_verified_at=datetime.now(UTC) if verified else None,
                        )
                        session.add(result)
                        return result

                    admin = user("admin", "admin")
                    member = user("member", "member")
                    other = user("other", "member")
                    unverified = user("unverified", "member", verified=False)
                    inactive = user("inactive", "member", active=False)
                    session.flush()
                    location = Location(name=f"Location {suffix}", admin=admin)
                    session.add(location)
                    session.flush()
                    camera_id = f"camera-{suffix}"
                    session.add(CameraDevice(camera_id=camera_id, location_id=location.id))
                    for person in (admin, member, unverified, inactive):
                        session.add(LocationMember(location_id=location.id, user_id=person.id))
                    session.flush()
                    shipment = Shipment(
                        resi_number=f"R{suffix}",
                        courier="jne",
                        source="camera",
                        camera_id=camera_id,
                        status="pending",
                        summary="Package detected",
                        provider="test",
                        history=[],
                    )
                    session.add(shipment)
                    session.flush()
                    notification = ShipmentRepository(session)._notify(shipment, "Package detected")
                    assert notification.location_id == location.id
                    payload = NotificationRead.model_validate(notification)
                    publisher = NotificationPublisher(
                        Mock(),
                        settings,
                        lambda: Session(bind=connection, join_transaction_mode="create_savepoint"),
                    )
                    with patch("cekrir.services.notifications.send_email") as send:
                        publisher.publish(payload)
                        recipients = {call.args[1] for call in send.call_args_list}
                        assert recipients == {admin.email, member.email}
                        assert len(send.call_args_list) == 2
                        assert all(call.kwargs["idempotency_key"] for call in send.call_args_list)

                    shipment.camera_id = f"unassigned-{suffix}"
                    unassigned = ShipmentRepository(session)._notify(shipment, "Package detected")
                    assert unassigned.location_id is None
                    with patch("cekrir.services.notifications.send_email") as send:
                        publisher.publish(NotificationRead.model_validate(unassigned))
                        send.assert_not_called()

                    with patch("cekrir.services.notifications.send_email") as send:
                        with Session(
                            bind=connection, join_transaction_mode="create_savepoint"
                        ) as other_session:
                            send_individual_email(
                                other_session,
                                settings,
                                admin.id,
                                member.id,
                                "Hello",
                                "A private message",
                                "request-1",
                            )
                        assert send.call_args.args[1] == member.email
                        with Session(
                            bind=connection, join_transaction_mode="create_savepoint"
                        ) as other_session:
                            with pytest.raises(EmailRecipientNotFound):
                                send_individual_email(
                                    other_session,
                                    settings,
                                    admin.id,
                                    other.id,
                                    "Hello",
                                    "Message",
                                    "request-2",
                                )
                    second_location = Location(name=f"Other location {suffix}", admin=admin)
                    session.add(second_location)
                    session.flush()
                    with Session(
                        bind=connection, join_transaction_mode="create_savepoint"
                    ) as other_session:
                        with pytest.raises(CameraAlreadyAssigned):
                            add_camera(other_session, second_location.id, admin.id, camera_id)
                    with Session(
                        bind=connection, join_transaction_mode="create_savepoint"
                    ) as other_session:
                        with pytest.raises(LocationResourceNotFound):
                            remove_member(other_session, location.id, other.id, member.id)
                    with Session(
                        bind=connection, join_transaction_mode="create_savepoint"
                    ) as other_session:
                        remove_member(other_session, location.id, admin.id, member.id)
                    with patch("cekrir.services.notifications.send_email") as send:
                        publisher.publish(payload)
                        assert [call.args[1] for call in send.call_args_list] == [admin.email]
            finally:
                transaction.rollback()
    finally:
        engine.dispose()
