from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Response
from sqlalchemy.orm import Session

from cekrir.db.session import get_session
from cekrir.dependencies import get_user_id
from cekrir.schemas import PaymentRead
from cekrir.services import payments
from cekrir.validation.payments import IdempotencyKey, PaymentCreate

router = APIRouter(prefix="/api/v1/payments", tags=["payments"])


@router.post("", response_model=PaymentRead, status_code=201)
def create_payment_draft(
    payload: PaymentCreate,
    response: Response,
    idempotency_key: IdempotencyKey,
    user_id: UUID = Depends(get_user_id),
    session: Session = Depends(get_session),
):
    try:
        payment, created = payments.submit_payment(session, user_id, idempotency_key, payload)
    except payments.IdempotencyConflict as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc
    response.status_code = 201 if created else 200
    return payment


@router.get("/{payment_id}", response_model=PaymentRead)
def read_payment(
    payment_id: UUID,
    user_id: UUID = Depends(get_user_id),
    session: Session = Depends(get_session),
):
    try:
        return payments.read_payment(session, user_id, payment_id)
    except payments.PaymentNotFound as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
