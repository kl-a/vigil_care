"""Patient and the access-gated Patient Identity (design doc §6.3)."""

import uuid
from datetime import date

from sqlalchemy import Index, UniqueConstraint, text
from sqlalchemy.dialects.postgresql import BYTEA
from sqlalchemy.orm import Mapped, mapped_column

from app.core.base_model import IDENTITY_SCHEMA, PracticeEntity, practice_fk


class Patient(PracticeEntity):
    """No identifying details here; they live in `identity.patient_identity`."""

    __tablename__ = "patient"
    __extra_args__ = (
        UniqueConstraint("pseudonym"),
        Index("ix_patient_not_deleted", "id", postgresql_where=text("deleted_at IS NULL")),
    )

    # Printed only on De-identified Exports, e.g. VG-0042. Never reused.
    pseudonym: Mapped[str]
    sex: Mapped[str | None]


class PatientIdentity(PracticeEntity):
    """Lives in the `identity` schema, readable only through the `identity_access` role.

    `*_encrypted` columns hold AES-256-GCM ciphertext; the key is never in the database.
    """

    __tablename__ = "patient_identity"
    __schema__ = IDENTITY_SCHEMA
    __extra_args__ = (UniqueConstraint("patient_id"), practice_fk("patient_id", "patient"))

    patient_id: Mapped[uuid.UUID]
    given_name: Mapped[str]
    family_name: Mapped[str]
    dob: Mapped[date | None]
    medicare_number_encrypted: Mapped[bytes | None] = mapped_column(BYTEA)
    medicare_irn: Mapped[str | None]
    ihi_encrypted: Mapped[bytes | None] = mapped_column(BYTEA)
    mrn: Mapped[str | None]
    address_encrypted: Mapped[bytes | None] = mapped_column(BYTEA)
    phone_encrypted: Mapped[bytes | None] = mapped_column(BYTEA)
    mobile_encrypted: Mapped[bytes | None] = mapped_column(BYTEA)
    email_encrypted: Mapped[bytes | None] = mapped_column(BYTEA)
    next_of_kin_name: Mapped[str | None]
    next_of_kin_phone_encrypted: Mapped[bytes | None] = mapped_column(BYTEA)
