"""Practice, its Sites, Provider directory and Care Team (design doc §6.3)."""

import uuid
from datetime import date
from decimal import Decimal
from typing import Literal, get_args

from sqlalchemy import Index, Text, text
from sqlalchemy.orm import Mapped, mapped_column

from app.core.base_model import PracticeEntity, SharedEntity, allowed, practice_fk

ProviderSpecialty = Literal[
    "medical_oncology",
    "radiation_oncology",
    "surgery",
    "general_practice",
    "haematology",
    "pathology",
    "radiology",
    "other",
]
PROVIDER_SPECIALTIES: tuple[str, ...] = get_args(ProviderSpecialty)
CareTeamRole = Literal[
    "treating_oncologist",
    "referring_gp",
    "referring_specialist",
    "surgeon",
    "radiation_oncologist",
    "trial_site_contact",
]
CARE_TEAM_ROLES: tuple[str, ...] = get_args(CareTeamRole)


class Practice(SharedEntity):
    """A Practice using Vigil. The root of Practice scoping, so it has no `practice_id` itself."""

    __tablename__ = "practice"

    name: Mapped[str]
    address: Mapped[str | None]
    phone: Mapped[str | None]
    fax: Mapped[str | None]
    email: Mapped[str | None]
    abn: Mapped[str | None]


class Site(PracticeEntity):
    """A place where the Practice sees Patients. Trial-site distances are measured from each Site."""

    __tablename__ = "site"
    __extra_args__ = (
        # At most one primary Site per Practice; the service keeps it at exactly one once a Site exists.
        Index(
            "uq_site_practice_id_primary",
            "practice_id",
            unique=True,
            postgresql_where=text("is_primary AND deleted_at IS NULL"),
        ),
    )

    name: Mapped[str]
    address: Mapped[str | None]
    lat: Mapped[Decimal | None]
    lng: Mapped[Decimal | None]
    is_primary: Mapped[bool] = mapped_column(server_default=text("false"))


class Provider(PracticeEntity):
    __tablename__ = "provider"
    __extra_args__ = (
        Index(
            "uq_provider_practice_id_provider_number",
            "practice_id",
            "provider_number",
            unique=True,
            postgresql_where=text("provider_number IS NOT NULL"),
        ),
    )

    title: Mapped[str | None]
    first_name: Mapped[str]
    last_name: Mapped[str]
    provider_number: Mapped[str | None]
    specialty: Mapped[ProviderSpecialty] = mapped_column(Text, info=allowed(*PROVIDER_SPECIALTIES))
    is_internal: Mapped[bool] = mapped_column(server_default=text("false"))
    organisation: Mapped[str | None]
    phone: Mapped[str | None]
    email: Mapped[str | None]
    fax: Mapped[str | None]
    notes: Mapped[str | None]


class CareTeamMember(PracticeEntity):
    __tablename__ = "care_team_member"
    __extra_args__ = (
        practice_fk("patient_id", "patient"),
        # Required, so RESTRICT rather than SET NULL.
        practice_fk("provider_id", "provider"),
        # At most one primary member per Patient; the service moves it when another is chosen.
        Index(
            "uq_care_team_member_patient_id_primary",
            "patient_id",
            unique=True,
            postgresql_where=text("is_primary AND deleted_at IS NULL"),
        ),
    )

    patient_id: Mapped[uuid.UUID] = mapped_column(index=True)
    provider_id: Mapped[uuid.UUID] = mapped_column(index=True)
    role: Mapped[CareTeamRole] = mapped_column(Text, info=allowed(*CARE_TEAM_ROLES))
    is_primary: Mapped[bool] = mapped_column(server_default=text("false"))
    start_date: Mapped[date | None]
    end_date: Mapped[date | None]
    notes: Mapped[str | None]
