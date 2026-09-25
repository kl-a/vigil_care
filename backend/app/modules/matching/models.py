"""Match Runs and their results (design doc §6.3, §11). Never change once made; Stale is computed."""

import uuid
from datetime import datetime
from decimal import Decimal
from typing import Any

from sqlalchemy import ForeignKey, Index, UniqueConstraint, text
from sqlalchemy.orm import Mapped, mapped_column

from app.core.base_model import PracticeEntity, allowed, member_fk, practice_fk

MATCH_STATES = ("POTENTIALLY_ELIGIBLE", "NEEDS_INFORMATION", "EXCLUDED")
CRITERION_RESULTS = ("MET", "NOT_MET", "UNKNOWN")


class MatchRun(PracticeEntity):
    __tablename__ = "match_run"
    __immutable__ = True
    __extra_args__ = (
        practice_fk("patient_id", "patient"),
        practice_fk("target_condition_id", "condition"),
        member_fk("run_by_user_id"),
        Index("ix_match_run_latest", "patient_id", "target_condition_id", text("created_at DESC")),
    )

    patient_id: Mapped[uuid.UUID] = mapped_column(index=True)
    target_condition_id: Mapped[uuid.UUID] = mapped_column(index=True)
    snapshot_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("trial_snapshot.id", ondelete="RESTRICT"), index=True
    )
    clinical_record_as_of: Mapped[datetime]
    ruleset_version: Mapped[str]
    model_version: Mapped[str | None]
    run_by_user_id: Mapped[uuid.UUID] = mapped_column(index=True)


class MatchResult(PracticeEntity):
    __tablename__ = "match_result"
    __immutable__ = True
    __extra_args__ = (
        practice_fk("match_run_id", "match_run", ondelete="CASCADE"),
        UniqueConstraint("match_run_id", "trial_id"),
    )

    match_run_id: Mapped[uuid.UUID] = mapped_column(index=True)
    trial_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("trial.id", ondelete="RESTRICT"), index=True
    )
    match_state: Mapped[str] = mapped_column(info=allowed(*MATCH_STATES))
    score: Mapped[Decimal | None]


class CriterionEvaluation(PracticeEntity):
    __tablename__ = "criterion_evaluation"
    __immutable__ = True
    __extra_args__ = (practice_fk("match_result_id", "match_result", ondelete="CASCADE"),)

    match_result_id: Mapped[uuid.UUID] = mapped_column(index=True)
    trial_criterion_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("trial_criterion.id", ondelete="RESTRICT"), index=True
    )
    result: Mapped[str] = mapped_column(info=allowed(*CRITERION_RESULTS))
    rationale: Mapped[str | None]
    # Clinical Record row + criterion text.
    evidence_ref: Mapped[dict[str, Any]] = mapped_column(server_default=text("'{}'::jsonb"))
