import uuid
from datetime import datetime
from typing import Any

from pydantic import BaseModel


class VerificationEntry(BaseModel):
    """One sign-off, as recorded: who (id and Job Title at the time), what, and when."""

    action: str
    user_id: uuid.UUID
    job_title_at_time: str
    before: dict[str, Any] | None
    after: dict[str, Any] | None
    reason: str | None
    reauthenticated: bool
    at: datetime
