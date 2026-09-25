"""The PBS Schedule Vigil shows: the items loaded by the latest Refresh that loaded any, so a failed Refresh
leaves the previous schedule visible.
"""

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.modules.pbs.models import PbsRefreshLog


def current_refresh(db: Session) -> PbsRefreshLog | None:
    """The latest Refresh that loaded any items: its items are the schedule Vigil shows."""
    query = (
        select(PbsRefreshLog)
        .where(PbsRefreshLog.status.in_(("succeeded", "partial")), PbsRefreshLog.item_count > 0)
        .order_by(PbsRefreshLog.refreshed_at.desc())
        .limit(1)
    )
    return db.scalars(query).first()
