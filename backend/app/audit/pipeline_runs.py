"""Reading pipeline runs for the Support Views (design doc §6.3, §6.4): system-wide runs and one Practice's own.

Runs hold IDs only. Whatever wrote one, anything else in `inputs`, `versions` or `error_detail` is shown as
"withheld", so a Support View never passes Patient data on to a developer admin.
"""

import uuid

from sqlalchemy import ColumnElement, or_, select
from sqlalchemy.orm import Session

from app.audit.models import PipelineRun
from app.audit.schemas import PipelineRunView
from app.core.seams.queue import code_or_withheld, withhold_non_ids


def recent(db: Session, practice_id: uuid.UUID, limit: int = 100) -> list[PipelineRunView]:
    """Newest first."""
    rows = db.scalars(
        select(PipelineRun)
        .where(_visible_to(practice_id))
        .order_by(PipelineRun.created_at.desc(), PipelineRun.id)
        .limit(limit)
    )
    return [_view(run) for run in rows]


def one(db: Session, practice_id: uuid.UUID, run_id: uuid.UUID) -> PipelineRunView | None:
    """None for a run that doesn't exist or is another Practice's."""
    run = db.scalars(select(PipelineRun).where(PipelineRun.id == run_id, _visible_to(practice_id))).one_or_none()
    return _view(run) if run else None


def _visible_to(practice_id: uuid.UUID) -> ColumnElement[bool]:
    scope = or_(PipelineRun.practice_id.is_(None), PipelineRun.practice_id == practice_id)
    return scope & PipelineRun.deleted_at.is_(None)


def _view(run: PipelineRun) -> PipelineRunView:
    return PipelineRunView(
        id=run.id,
        kind=run.kind,
        status=run.status,
        system_wide=run.practice_id is None,
        inputs=withhold_non_ids(run.inputs),
        versions=withhold_non_ids(run.versions),
        created_at=run.created_at,
        started_at=run.started_at,
        finished_at=run.finished_at,
        error_detail=code_or_withheld(run.error_detail),
    )
