"""Refreshes and Job progress (#18). Refusals (403) come from the service."""

import uuid
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Request, status

from app.core.seams.queue import JobQueue
from app.modules.accounts.dependencies import Db, SignedIn
from app.orchestrator import service
from app.orchestrator.schemas import JobView, RefreshView, StartRefresh

router = APIRouter(tags=["jobs"])


def job_queue(request: Request) -> JobQueue:
    queue: JobQueue = request.app.state.job_queue
    return queue


Queue = Annotated[JobQueue, Depends(job_queue)]


@router.get("/refreshes")
def list_refreshes(actor: SignedIn, db: Db, queue: Queue) -> list[RefreshView]:
    return service.list_refreshes(db, queue, actor)


@router.post("/refreshes", status_code=status.HTTP_201_CREATED)
def start_refresh(body: StartRefresh, actor: SignedIn, db: Db, queue: Queue) -> JobView:
    try:
        return service.start_refresh(db, queue, actor, body.kind)
    except service.NotARefresh as error:
        raise HTTPException(status.HTTP_422_UNPROCESSABLE_CONTENT, str(error)) from None


@router.get("/jobs/{job_id}")
def job_status(job_id: uuid.UUID, actor: SignedIn, queue: Queue) -> JobView:
    try:
        return service.job_status(queue, actor, job_id)
    except service.JobNotFound:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "No such Job.") from None
