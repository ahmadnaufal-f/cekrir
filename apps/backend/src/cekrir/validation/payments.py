from typing import Annotated, Literal

from fastapi import Header
from pydantic import BaseModel, ConfigDict, Field


class PaymentCreate(BaseModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)

    reference: str = Field(min_length=1, max_length=128)
    amount: int = Field(strict=True, gt=0, le=10_000_000)
    currency: Literal["IDR"] = "IDR"


IdempotencyKey = Annotated[
    str, Header(alias="Idempotency-Key", min_length=1, max_length=128, pattern=r"^[!-~]+$")
]
