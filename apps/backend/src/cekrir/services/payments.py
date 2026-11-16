from dataclasses import dataclass
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.orm import Session

from cekrir.db.model import Payment
from cekrir.validation.payments import PaymentCreate


class IdempotencyConflict(Exception):
    """The same user's key was used for different payment details."""


class PaymentNotFound(Exception):
    pass


@dataclass(frozen=True)
class PaymentDetails:
    reference: str
    amount: int
    currency: str = "IDR"


def create_payment(
    session: Session, user_id: UUID, key: str, details: PaymentDetails
) -> tuple[Payment, bool]:
    with session.begin():
        payment_id = session.scalar(
            insert(Payment)
            .values(
                user_id=user_id,
                idempotency_key=key,
                reference=details.reference,
                amount=details.amount,
                currency=details.currency,
                status="draft",
            )
            .on_conflict_do_nothing(index_elements=["user_id", "idempotency_key"])
            .returning(Payment.id)
        )
        created = payment_id is not None
        payment = (
            session.get(Payment, payment_id)
            if created
            else session.scalar(
                select(Payment).where(Payment.user_id == user_id, Payment.idempotency_key == key)
            )
        )
        if payment is None:
            raise RuntimeError("Payment could not be loaded")
        if (payment.reference, payment.amount, payment.currency) != (
            details.reference,
            details.amount,
            details.currency,
        ):
            raise IdempotencyConflict("Idempotency key was already used for different details")
    return payment, created


def get_payment(session: Session, user_id: UUID, payment_id: UUID) -> Payment | None:
    return session.scalar(
        select(Payment).where(Payment.id == payment_id, Payment.user_id == user_id)
    )


def submit_payment(
    session: Session, user_id: UUID, key: str, payload: PaymentCreate
) -> tuple[Payment, bool]:
    return create_payment(session, user_id, key, PaymentDetails(**payload.model_dump()))


def read_payment(session: Session, user_id: UUID, payment_id: UUID) -> Payment:
    payment = get_payment(session, user_id, payment_id)
    if payment is None:
        raise PaymentNotFound("Payment not found")
    return payment
