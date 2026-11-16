from datetime import datetime
from typing import Annotated, Literal
from uuid import UUID

from fastapi import APIRouter, Depends, Header, HTTPException, Request, Response
from pydantic import BaseModel, ConfigDict, Field
from sqlalchemy.orm import Session

from cekrir.db.session import get_session
from cekrir.services.payments import (
    IdempotencyConflict,
    PaymentDetails,
    create_payment,
    get_payment,
)

router = APIRouter(prefix="/api/v1/payments", tags=["payments"])


class PaymentCreate(BaseModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)

    reference: str = Field(min_length=1, max_length=128)
    amount: int = Field(strict=True, gt=0, le=10_000_000)
    currency: Literal["IDR"] = "IDR"


class PaymentRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    reference: str
    amount: int
    currency: Literal["IDR"]
    status: Literal["draft"]
    created_at: datetime


@router.post("", response_model=PaymentRead, status_code=201)
def create_payment_draft(
    payload: PaymentCreate,
    request: Request,
    response: Response,
    idempotency_key: Annotated[
        str, Header(alias="Idempotency-Key", min_length=1, max_length=128, pattern=r"^[!-~]+$")
    ],
    session: Session = Depends(get_session),
):
    try:
        payment, created = create_payment(
            session,
            UUID(request.state.principal["id"]),
            idempotency_key,
            PaymentDetails(**payload.model_dump()),
        )
    except IdempotencyConflict as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc
    response.status_code = 201 if created else 200
    return payment


@router.get("/{payment_id}", response_model=PaymentRead)
def read_payment(payment_id: UUID, request: Request, session: Session = Depends(get_session)):
    payment = get_payment(session, UUID(request.state.principal["id"]), payment_id)
    if payment is None:
        raise HTTPException(status_code=404, detail="Payment not found")
    return payment
