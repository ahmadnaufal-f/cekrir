from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field


class EmailNotificationInput(BaseModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)

    user_id: UUID
    subject: str = Field(min_length=1, max_length=200, pattern=r"^[^\r\n]+$")
    message: str = Field(min_length=1, max_length=5000)
