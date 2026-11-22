from pydantic import Field

from cekrir.validation.shipments import ResiInput


class BinderByteInput(ResiInput):
    phone_last_five: str | None = Field(default=None, pattern=r"^[0-9]{5}$")
