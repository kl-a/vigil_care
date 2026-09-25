"""Refreshes and Job progress (#18). Everyone signed in may follow them ("support_views"); only developer
admins start a Refresh ("start_refresh", design doc §6.4). A Refresh is a system-wide Job whose Job Kind's key
starts with "refresh_".
"""

import uuid
from dataclasses import asdict

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.audit.service import Actor
from app.core.permissions import require
from app.core.seams.queue import JobQueue, JobStatus, NewJob, UnknownJob
from app.orchestrator.models import JobKind
from app.orchestrator.schemas import JobView, RefreshView

REFRESH_PREFIX = "refresh_"


class JobNotFound(LookupError):
    """No such Job, or it belongs to another Practice."""


class NotARefresh(ValueError):
    """Only a Refresh Job Kind can be started from the Support Views."""


def _view(status: JobStatus) -> JobView:
    return JobView.model_validate(asdict(status))


def _refresh_kinds(db: Session) -> list[JobKind]:
    return list(db.scalars(select(JobKind).where(JobKind.key.startswith(REFRESH_PREFIX)).order_by(JobKind.key)))


def list_refreshes(db: Session, queue: JobQueue, actor: Actor) -> list[RefreshView]:
    require(actor.job_title, "support_views")
    views = []
    for kind in _refresh_kinds(db):
        latest = queue.latest(kind.key)
        views.append(RefreshView(kind=kind.key, description=kind.description, last_job=_view(latest) if latest else None))
    return views


def start_refresh(db: Session, queue: JobQueue, actor: Actor, kind: str) -> JobView:
    require(actor.job_title, "start_refresh")
    if kind not in {k.key for k in _refresh_kinds(db)}:
        raise NotARefresh(f"{kind} isn't a Refresh.")
    return _view(queue.status(queue.enqueue(NewJob(kind=kind))))


def job_status(queue: JobQueue, actor: Actor, job_id: uuid.UUID) -> JobView:
    """System-wide Jobs and the actor's own Practice's; never another Practice's."""
    require(actor.job_title, "support_views")
    try:
        status = queue.status(job_id)
    except UnknownJob:
        raise JobNotFound() from None
    if status.practice_id is not None and status.practice_id != actor.practice_id:
        raise JobNotFound()
    return _view(status)
