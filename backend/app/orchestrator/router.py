"""Support Views (#10) and Refreshes (#18). Refusals (403) come from the service.

Every route here is tagged "support": it may be opened by a developer admin, so it carries IDs only. The
no-Patient-data test (tests/api/test_no_patient_data_in_support.py) checks every route with that tag.
"""

import uuid
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Request, status

from app.audit.schemas import PipelineRunView
from app.core.permissions import SUPPORT_TAG
from app.core.seams.queue import JobQueue
from app.modules.accounts.dependencies import Db, SignedIn
from app.orchestrator import service
from app.orchestrator.schemas import JobView, QueueDepthView, RefreshView, StartRefresh

router = APIRouter(tags=[SUPPORT_TAG])


def job_queue(request: Request) -> JobQueue:
    queue: JobQueue = request.app.state.job_queue
    return queue


Queue = Annotated[JobQueue, Depends(job_queue)]


@router.get("/refreshes")
def list_refreshes(actor: SignedIn, db: Db, queue: Queue) -> list[RefreshView]:
    return service.list_refreshes(db, queue, actor)


@router.get("/refreshes/history")
def refresh_history(actor: SignedIn, db: Db, queue: Queue) -> list[JobView]:
    return service.refresh_history(db, queue, actor)


@router.post("/refreshes", status_code=status.HTTP_201_CREATED)
def start_refresh(body: StartRefresh, actor: SignedIn, db: Db, queue: Queue) -> JobView:
    try:
        return service.start_refresh(db, queue, actor, body.kind)
    except service.NotARefresh as error:
        raise HTTPException(status.HTTP_422_UNPROCESSABLE_CONTENT, str(error)) from None
    except service.RefreshAlreadyRunning as error:
        raise HTTPException(status.HTTP_409_CONFLICT, str(error)) from None


@router.get("/jobs")
def list_jobs(actor: SignedIn, queue: Queue, kind: str | None = None) -> list[JobView]:
    """The most recent Jobs, newest first; `kind` narrows them to one Job Kind."""
    return service.list_jobs(queue, actor, kind)


@router.get("/jobs/{job_id}")
def job_status(job_id: uuid.UUID, actor: SignedIn, queue: Queue) -> JobView:
    try:
        return service.job_status(queue, actor, job_id)
    except service.JobNotFound:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "No such Job.") from None


@router.get("/queue")
def queue_depth(actor: SignedIn, queue: Queue) -> QueueDepthView:
    return service.queue_depth(queue, actor)


@router.get("/pipeline-runs")
def list_pipeline_runs(actor: SignedIn, db: Db) -> list[PipelineRunView]:
    return service.list_pipeline_runs(db, actor)


@router.get("/pipeline-runs/{run_id}")
def pipeline_run(run_id: uuid.UUID, actor: SignedIn, db: Db) -> PipelineRunView:
    try:
        return service.pipeline_run(db, actor, run_id)
    except service.PipelineRunNotFound:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "No such pipeline run.") from None
