from datetime import UTC, datetime
from uuid import UUID

from psycopg import Connection
from psycopg.types.json import Jsonb

from cekrir.db import DatabaseRow
from cekrir.schemas import (
    DetectionInput,
    NotificationRead,
    ResiInput,
    ShipmentRead,
    TrackingSnapshot,
)


class ShipmentRepository:
    def __init__(self, connection: Connection[DatabaseRow]):
        self.connection = connection

    def list_shipments(self, limit: int, offset: int) -> list[ShipmentRead]:
        rows = self.connection.execute(
            "SELECT * FROM shipment ORDER BY created_at DESC, id DESC LIMIT %s OFFSET %s",
            (limit, offset),
        ).fetchall()
        return [ShipmentRead.model_validate(row) for row in rows]

    def list_notifications(self, limit: int, offset: int) -> list[NotificationRead]:
        rows = self.connection.execute(
            "SELECT * FROM notification ORDER BY created_at DESC, id DESC LIMIT %s OFFSET %s",
            (limit, offset),
        ).fetchall()
        return [NotificationRead.model_validate(row) for row in rows]

    def find_shipment(self, payload: ResiInput) -> ShipmentRead | None:
        row = self.connection.execute(
            "SELECT * FROM shipment WHERE courier = %s AND resi_number = %s",
            (payload.courier, payload.resi_number),
        ).fetchone()
        return ShipmentRead.model_validate(row) if row else None

    def get_shipment(self, shipment_id: str) -> ShipmentRead | None:
        try:
            identifier = UUID(shipment_id)
        except ValueError:
            return None
        row = self.connection.execute(
            "SELECT * FROM shipment WHERE id = %s", (identifier,)
        ).fetchone()
        return ShipmentRead.model_validate(row) if row else None

    def record_detection(self, shipment: ShipmentRead, payload: DetectionInput) -> ShipmentRead:
        row = self.connection.execute(
            """UPDATE shipment SET camera_id = %s, last_detected_at = CURRENT_TIMESTAMP
               WHERE id = %s RETURNING *""",
            (payload.camera_id, shipment.id),
        ).fetchone()
        return ShipmentRead.model_validate(row)

    def register(
        self, payload: ResiInput, snapshot: TrackingSnapshot, provider: str
    ) -> tuple[ShipmentRead, bool]:
        camera = isinstance(payload, DetectionInput)
        with self.connection.transaction():
            row = self.connection.execute(
                """INSERT INTO shipment
                   (resi_number, courier, source, camera_id, status, summary, provider,
                    history, last_detected_at)
                   VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
                   ON CONFLICT (courier, resi_number) DO NOTHING RETURNING *""",
                (
                    payload.resi_number,
                    payload.courier,
                    "camera" if camera else "manual",
                    payload.camera_id if camera else None,
                    snapshot.status,
                    snapshot.summary,
                    provider,
                    Jsonb([event.model_dump(mode="json") for event in snapshot.history]),
                    datetime.now(UTC) if camera else None,
                ),
            ).fetchone()
            if row:
                shipment = ShipmentRead.model_validate(row)
                self._notify(shipment, "Package detected" if camera else "Package added")
                return shipment, True

            # ON CONFLICT waits for the competing transaction. This new statement
            # sees its committed row under PostgreSQL's READ COMMITTED isolation.
            existing = self.find_shipment(payload)
            if existing is None:
                raise RuntimeError("Conflicting shipment could not be found")
            if camera:
                existing = self.record_detection(existing, payload)
            return existing, False

    def refresh(
        self, shipment: ShipmentRead, snapshot: TrackingSnapshot, provider: str
    ) -> ShipmentRead:
        with self.connection.transaction():
            # Serialize concurrent refreshes, including the status-change event.
            current = self.connection.execute(
                "SELECT status FROM shipment WHERE id = %s FOR UPDATE", (shipment.id,)
            ).fetchone()
            row = self.connection.execute(
                """UPDATE shipment SET status = %s, summary = %s, provider = %s,
                   history = %s, checked_at = CURRENT_TIMESTAMP WHERE id = %s RETURNING *""",
                (
                    snapshot.status,
                    snapshot.summary,
                    provider,
                    Jsonb([event.model_dump(mode="json") for event in snapshot.history]),
                    shipment.id,
                ),
            ).fetchone()
            updated = ShipmentRead.model_validate(row)
            if current["status"] != updated.status:
                self._notify(updated, "Package status changed")
            return updated

    def _notify(self, shipment: ShipmentRead, title: str) -> None:
        self.connection.execute(
            "INSERT INTO notification (shipment_id, title, message) VALUES (%s, %s, %s)",
            (
                shipment.id,
                title,
                f"{shipment.courier.upper()} · {shipment.resi_number}: {shipment.summary}",
            ),
        )
