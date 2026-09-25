"""Users and Practice Memberships (design doc §6.3).

A User is a person with one login across Vigil. Their standing at each Practice they work at (Job Title,
active or not, their own Provider entry) is a Practice Membership. A Provider is a clinician in a
Practice's directory.
"""

import uuid
from datetime import datetime

from sqlalchemy import ForeignKey, Text, UniqueConstraint, text
from sqlalchemy.dialects.postgresql import BYTEA
from sqlalchemy.orm import Mapped, mapped_column

from app.core.base_model import PracticeEntity, SharedEntity, allowed, practice_fk
from app.core.vocabulary import JOB_TITLES, JobTitle


class User(SharedEntity):
    __tablename__ = "user"
    __extra_args__ = (UniqueConstraint("username"),)

    username: Mapped[str]
    display_name: Mapped[str]
    password_hash: Mapped[str]
    totp_secret_encrypted: Mapped[bytes | None] = mapped_column(BYTEA)
    totp_enrolled_at: Mapped[datetime | None]


class PracticeMembership(PracticeEntity):
    __tablename__ = "practice_membership"
    __extra_args__ = (
        UniqueConstraint("user_id", "practice_id"),  # what every `member_fk` references; indexes user_id too
        practice_fk("provider_id", "provider", ondelete="SET NULL"),
    )

    user_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("user.id", ondelete="RESTRICT"))
    job_title: Mapped[JobTitle] = mapped_column(Text, info=allowed(*JOB_TITLES))
    provider_id: Mapped[uuid.UUID | None] = mapped_column(index=True)
    is_active: Mapped[bool] = mapped_column(server_default=text("true"))
    last_login_at: Mapped[datetime | None]
