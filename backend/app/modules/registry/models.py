"""Installed Specialty Modules and their per-Practice activation (design doc §4.1, §6.3)."""

import uuid

from sqlalchemy import ForeignKey, UniqueConstraint, text
from sqlalchemy.orm import Mapped, mapped_column

from app.core.base_model import PracticeEntity, SharedEntity, practice_fk


class SpecialtyModule(SharedEntity):
    """An installed Specialty Module: its code ships with this build; a migration adds its row."""

    __tablename__ = "specialty_module"
    __extra_args__ = (UniqueConstraint("key"),)

    key: Mapped[str]
    display_name: Mapped[str]
    version: Mapped[str]


class PracticeModule(PracticeEntity):
    """Whether a module is active for a Practice. Changed only by a developer admin (with a Verification)."""

    __tablename__ = "practice_module"
    __extra_args__ = (
        UniqueConstraint("practice_id", "module_key"),
        practice_fk("changed_by_user_id", "user"),
    )

    module_key: Mapped[str] = mapped_column(
        ForeignKey("specialty_module.key", ondelete="RESTRICT"), index=True
    )
    is_active: Mapped[bool] = mapped_column(server_default=text("true"))
    changed_by_user_id: Mapped[uuid.UUID] = mapped_column(index=True)
