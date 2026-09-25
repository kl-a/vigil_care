"""Which PBS Refresh the PBS module shows (internal to the module: returns models, not schemas)."""

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.modules.pbs.models import PbsRefreshLog


def current_log(db: Session) -> PbsRefreshLog | None:
    """The latest Refresh that loaded any items: its items are the schedule Vigil shows."""
    query = (
        select(PbsRefreshLog)
        .where(PbsRefreshLog.status.in_(("succeeded", "partial")), PbsRefreshLog.item_count > 0)
        .order_by(PbsRefreshLog.refreshed_at.desc())
        .limit(1)
    )
    return db.scalars(query).first()


def last_log(db: Session) -> PbsRefreshLog | None:
    """The latest attempt, whatever its outcome."""
    return db.scalars(select(PbsRefreshLog).order_by(PbsRefreshLog.refreshed_at.desc()).limit(1)).first()


def has_api_schedule(db: Session) -> bool:
    """Whether the schedule shown came from the PBS API (not the bundled sample)."""
    current = current_log(db)
    return current is not None and current.source == "pbs_api"
