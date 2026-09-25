"""Reports and signed-off Identified / De-identified Exports (design doc §6.3). Vigil never sends a file."""

import uuid
from datetime import datetime
from typing import Any

from sqlalchemy import CheckConstraint, text
from sqlalchemy.orm import Mapped, mapped_column

from app.core.base_model import PracticeEntity, allowed, practice_fk
from app.core.vocabulary import VERIFYING_JOB_TITLES

REPORT_TYPES = ("treatment_summary", "trial_match", "patient_summary_snapshot", "combined")
EXPORT_KINDS = ("identified", "deidentified")


class Report(PracticeEntity):
    __tablename__ = "report"
    __extra_args__ = (
        practice_fk("patient_id", "patient"),
        practice_fk("match_run_id", "match_run"),
    )

    patient_id: Mapped[uuid.UUID] = mapped_column(index=True)
    match_run_id: Mapped[uuid.UUID | None] = mapped_column(index=True)
    report_type: Mapped[str] = mapped_column(info=allowed(*REPORT_TYPES))
    template_version: Mapped[str]
    manifest: Mapped[dict[str, Any]] = mapped_column(server_default=text("'{}'::jsonb"))
    file_uri: Mapped[str | None]


class Export(PracticeEntity):
    """Kind is chosen explicitly (no default) and signed off by the User who sends it."""

    __tablename__ = "export"
    __extra_args__ = (
        practice_fk("patient_id", "patient"),
        practice_fk("report_id", "report"),
        practice_fk("redaction_job_id", "redaction_job"),
        practice_fk("recipient_provider_id", "provider", ondelete="SET NULL"),
        practice_fk("signed_off_by_user_id", "user"),
        CheckConstraint("num_nonnulls(patient_id, redaction_job_id) >= 1", name="has_subject"),
    )

    # Null only for an export of an unlinked Redaction Job.
    patient_id: Mapped[uuid.UUID | None] = mapped_column(index=True)
    report_id: Mapped[uuid.UUID | None] = mapped_column(index=True)
    redaction_job_id: Mapped[uuid.UUID | None] = mapped_column(index=True)
    kind: Mapped[str] = mapped_column(info=allowed(*EXPORT_KINDS))
    recipient_description: Mapped[str]
    recipient_provider_id: Mapped[uuid.UUID | None] = mapped_column(index=True)
    file_uri: Mapped[str]
    file_sha256: Mapped[str]
    signed_off_by_user_id: Mapped[uuid.UUID] = mapped_column(index=True)
    job_title_at_time: Mapped[str] = mapped_column(info=allowed(*VERIFYING_JOB_TITLES))
    signed_off_at: Mapped[datetime]
