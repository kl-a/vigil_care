"""Users (design doc §6.3). A User logs in; a Provider is a clinician in the directory."""

import uuid
from datetime import datetime

from sqlalchemy import Text, UniqueConstraint, text
from sqlalchemy.dialects.postgresql import BYTEA
from sqlalchemy.orm import Mapped, mapped_column

from app.core.base_model import PracticeEntity, allowed, practice_fk
from app.core.vocabulary import JOB_TITLES, JobTitle


class User(PracticeEntity):
    __tablename__ = "user"
    __extra_args__ = (
        UniqueConstraint("practice_id", "username"),
        practice_fk("provider_id", "provider", ondelete="SET NULL"),
    )

    username: Mapped[str]
    display_name: Mapped[str]
    password_hash: Mapped[str]
    totp_secret_encrypted: Mapped[bytes | None] = mapped_column(BYTEA)
    totp_enrolled_at: Mapped[datetime | None]
    job_title: Mapped[JobTitle] = mapped_column(Text, info=allowed(*JOB_TITLES))
    provider_id: Mapped[uuid.UUID | None] = mapped_column(index=True)
    is_active: Mapped[bool] = mapped_column(server_default=text("true"))
    last_login_at: Mapped[datetime | None]
