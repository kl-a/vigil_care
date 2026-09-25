"""The database job queue: the `job`, `job_step` and `job_kind` tables (design doc §3, §6.3).

Workers claim with `SELECT … FOR UPDATE SKIP LOCKED`, so two never take the same Job. Each call is its own
short transaction.
"""

import uuid
from collections.abc import Iterable, Mapping, Sequence
from datetime import timedelta
from typing import Any

from sqlalchemy import ColumnElement, func, or_, select
from sqlalchemy.orm import Session, sessionmaker

from app.core.seams.queue import (
    DEFAULT_LEASE,
    ClaimedJob,
    JobStatus,
    ModuleInactive,
    NewJob,
    QueueDepth,
    StepStatus,
    UnknownJob,
    UnknownJobKind,
    check_code,
    ids_only,
)
from app.modules.registry.service import active_module_keys
from app.orchestrator.models import Job, JobKind, JobStep


class DbJobQueue:
    def __init__(self, sessions: sessionmaker[Session]) -> None:
        self._sessions = sessions

    def enqueue(self, job: NewJob) -> uuid.UUID:
        ids_only(job.payload)
        with self._sessions.begin() as db:
            kind = db.scalars(select(JobKind).where(JobKind.key == job.kind)).one_or_none()
            if kind is None:
                raise UnknownJobKind(job.kind)
            if not _may_run(db, kind.module_key, job.practice_id):
                raise ModuleInactive(f"{job.kind} needs the {kind.module_key} module")
            row = Job(
                kind=job.kind,
                practice_id=job.practice_id,
                payload=dict(job.payload),
                priority=job.priority,
                max_attempts=job.max_attempts,
                run_after=func.now() + timedelta(seconds=job.run_after_seconds),
            )
            db.add(row)
            db.flush()
            return row.id

    def claim(self, worker_id: str, kinds: Sequence[str], lease: timedelta = DEFAULT_LEASE) -> ClaimedJob | None:
        with self._sessions.begin() as db:
            while True:
                job = db.scalars(
                    select(Job)
                    .where(
                        Job.kind.in_(kinds),
                        or_(
                            (Job.status == "queued") & (Job.run_after <= func.now()),
                            # Still running after its lease: its worker died.
                            (Job.status == "running") & (Job.locked_at <= func.now() - lease),
                        ),
                    )
                    .order_by(Job.priority.desc(), Job.run_after, Job.created_at)
                    .limit(1)
                    .with_for_update(skip_locked=True)
                ).first()
                if job is None:
                    return None
                module_key = db.scalar(select(JobKind.module_key).where(JobKind.key == job.kind))
                if not _may_run(db, module_key, job.practice_id):
                    job.status, job.last_error, job.finished_at = "cancelled", "module_inactive", func.now()
                    db.flush()
                    continue
                if job.attempts >= job.max_attempts:
                    # A worker died on its last attempt.
                    job.status, job.last_error, job.finished_at = "failed", job.last_error or "worker_lost", func.now()
                    db.flush()
                    continue
                job.status, job.attempts, job.locked_at, job.locked_by = "running", job.attempts + 1, func.now(), worker_id
                db.flush()
                done = db.scalars(
                    select(JobStep).where(JobStep.job_id == job.id, JobStep.status == "succeeded").order_by(JobStep.sequence)
                )
                return ClaimedJob(
                    id=job.id,
                    kind=job.kind,
                    practice_id=job.practice_id,
                    payload=dict(job.payload),
                    attempt=job.attempts,
                    completed_steps={step.name: dict(step.output) for step in done},
                )

    def step_done(self, job_id: uuid.UUID, name: str, output: Mapping[str, Any]) -> None:
        check_code(name)
        ids_only(output)
        with self._sessions.begin() as db:
            step = db.scalars(select(JobStep).where(JobStep.job_id == job_id, JobStep.name == name)).one_or_none()
            if step is None:
                sequence = db.scalar(select(func.count()).select_from(JobStep).where(JobStep.job_id == job_id)) or 0
                step = JobStep(job_id=job_id, sequence=sequence, name=name, started_at=func.now())
                db.add(step)
            step.status, step.output, step.finished_at, step.error_detail = "succeeded", dict(output), func.now(), None

    def succeed(self, job_id: uuid.UUID) -> None:
        with self._sessions.begin() as db:
            job = db.get_one(Job, job_id)
            job.status, job.finished_at, job.locked_at, job.locked_by, job.last_error = "succeeded", func.now(), None, None, None

    def fail(self, job_id: uuid.UUID, error: str, retry_after_seconds: int = 30) -> None:
        check_code(error)
        with self._sessions.begin() as db:
            job = db.get_one(Job, job_id)
            job.last_error, job.locked_at, job.locked_by = error, None, None
            if job.attempts < job.max_attempts:
                job.status, job.run_after = "queued", func.now() + timedelta(seconds=retry_after_seconds)
            else:
                job.status, job.finished_at = "failed", func.now()

    def status(self, job_id: uuid.UUID) -> JobStatus:
        with self._sessions() as db:
            job = db.get(Job, job_id)
            if job is None:
                raise UnknownJob(str(job_id))
            return _status(db, job)

    def latest(self, kind: str) -> JobStatus | None:
        with self._sessions() as db:
            job = db.scalars(select(Job).where(Job.kind == kind).order_by(Job.created_at.desc(), Job.id).limit(1)).first()
            return _status(db, job) if job else None

    def recent(self, practice_id: uuid.UUID | None, kinds: Sequence[str] | None = None, limit: int = 100) -> list[JobStatus]:
        with self._sessions() as db:
            query = select(Job).where(_visible_to(practice_id)).order_by(Job.created_at.desc(), Job.id).limit(limit)
            if kinds is not None:
                query = query.where(Job.kind.in_(kinds))
            jobs = list(db.scalars(query))
            steps: dict[uuid.UUID, list[JobStep]] = {job.id: [] for job in jobs}
            for step in db.scalars(select(JobStep).where(JobStep.job_id.in_(steps)).order_by(JobStep.sequence)):
                steps[step.job_id].append(step)
            return [_status_of(job, steps[job.id]) for job in jobs]

    def depth(self, practice_id: uuid.UUID | None, kinds: Sequence[str] | None = None) -> QueueDepth:
        with self._sessions() as db:
            since = func.now() - timedelta(days=1)
            query = select(
                func.count().filter(Job.status == "queued"),
                func.count().filter(Job.status == "running"),
                func.count().filter((Job.status == "failed") & (Job.finished_at >= since)),
            ).where(_visible_to(practice_id))
            if kinds is not None:
                query = query.where(Job.kind.in_(kinds))
            queued, running, failed = db.execute(query).one()
            return QueueDepth(queued=queued, running=running, failed_last_day=failed)


def _visible_to(practice_id: uuid.UUID | None) -> ColumnElement[bool]:
    """System-wide Jobs, and `practice_id`'s own."""
    return or_(Job.practice_id.is_(None), Job.practice_id == practice_id)


def _may_run(db: Session, module_key: str | None, practice_id: uuid.UUID | None) -> bool:
    """Core Job Kinds always may; a module's may for system-wide Jobs, or where the module is active."""
    if module_key is None or practice_id is None:
        return True
    return module_key in active_module_keys(db, practice_id)


def _status(db: Session, job: Job) -> JobStatus:
    return _status_of(job, db.scalars(select(JobStep).where(JobStep.job_id == job.id).order_by(JobStep.sequence)))


def _status_of(job: Job, steps: Iterable[JobStep]) -> JobStatus:
    return JobStatus(
        id=job.id,
        kind=job.kind,
        practice_id=job.practice_id,
        status=job.status,
        attempts=job.attempts,
        max_attempts=job.max_attempts,
        created_at=job.created_at,
        finished_at=job.finished_at,
        last_error=job.last_error,
        steps=[
            StepStatus(name=s.name, status=s.status, started_at=s.started_at, finished_at=s.finished_at, output=dict(s.output))
            for s in steps
        ],
        payload=dict(job.payload),
    )
