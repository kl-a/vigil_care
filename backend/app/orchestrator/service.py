"""Refreshes, Job progress and the Support Views (#18, #10). Everyone signed in may read them ("support_views");
only developer admins start a Refresh ("start_refresh", design doc §6.4). A Refresh is a system-wide Job whose
Job Kind's key starts with "refresh_".

Support Views show system-wide rows and the actor's own Practice's, never another Practice's, and carry IDs,
Job Kinds, states, counts and timings only.
"""

import uuid
from dataclasses import asdict

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.audit import pipeline_runs
from app.audit.schemas import PipelineRunView
from app.audit.service import Actor
from app.core.permissions import require
from app.core.seams.queue import JobQueue, JobStatus, NewJob, UnknownJob
from app.orchestrator.models import JobKind
from app.orchestrator.schemas import JobView, QueueDepthView, RefreshView

REFRESH_PREFIX = "refresh_"
RECENT = 100


class JobNotFound(LookupError):
    """No such Job, or it belongs to another Practice."""


class PipelineRunNotFound(LookupError):
    """No such pipeline run, or it belongs to another Practice."""


class NotARefresh(ValueError):
    """Only a Refresh Job Kind can be started from the Support Views."""


def _view(status: JobStatus) -> JobView:
    fields = asdict(status)
    return JobView.model_validate({**fields, "system_wide": fields.pop("practice_id") is None})


def _refresh_kinds(db: Session) -> list[JobKind]:
    return list(db.scalars(select(JobKind).where(JobKind.key.startswith(REFRESH_PREFIX)).order_by(JobKind.key)))


def list_refreshes(db: Session, queue: JobQueue, actor: Actor) -> list[RefreshView]:
    require(actor.job_title, "support_views")
    views = []
    for kind in _refresh_kinds(db):
        latest = queue.latest(kind.key)
        views.append(RefreshView(kind=kind.key, description=kind.description, last_job=_view(latest) if latest else None))
    return views


def refresh_history(db: Session, queue: JobQueue, actor: Actor) -> list[JobView]:
    """Every Refresh's recent Jobs, newest first. Their steps' outputs carry the counts (e.g. items stored)."""
    require(actor.job_title, "support_views")
    kinds = [kind.key for kind in _refresh_kinds(db)]
    return [_view(status) for status in queue.recent(actor.practice_id, kinds=kinds, limit=RECENT)]


def start_refresh(db: Session, queue: JobQueue, actor: Actor, kind: str) -> JobView:
    require(actor.job_title, "start_refresh")
    if kind not in {k.key for k in _refresh_kinds(db)}:
        raise NotARefresh(f"{kind} isn't a Refresh.")
    return _view(queue.status(queue.enqueue(NewJob(kind=kind))))


def list_jobs(queue: JobQueue, actor: Actor, kind: str | None = None) -> list[JobView]:
    require(actor.job_title, "support_views")
    kinds = [kind] if kind else None
    return [_view(status) for status in queue.recent(actor.practice_id, kinds=kinds, limit=RECENT)]


def queue_depth(queue: JobQueue, actor: Actor) -> QueueDepthView:
    require(actor.job_title, "support_views")
    return QueueDepthView.model_validate(asdict(queue.depth(actor.practice_id)))


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


def list_pipeline_runs(db: Session, actor: Actor) -> list[PipelineRunView]:
    require(actor.job_title, "support_views")
    return pipeline_runs.recent(db, actor.practice_id, limit=RECENT)


def pipeline_run(db: Session, actor: Actor, run_id: uuid.UUID) -> PipelineRunView:
    require(actor.job_title, "support_views")
    run = pipeline_runs.one(db, actor.practice_id, run_id)
    if run is None:
        raise PipelineRunNotFound()
    return run
