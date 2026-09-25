"""The worker (#18): runs each Job Kind's steps, resumes after the last completed step, retries, and enqueues
scheduled Jobs (e.g. the monthly PBS Refresh) when they fall due.
"""

import logging
import uuid
from collections.abc import Iterator
from datetime import UTC, datetime
from typing import Any

import psycopg
import pytest

from app.core.database import session_factory
from app.core.seams.queue import NewJob
from app.db.provision import APP_ROLE, DatabaseSettings
from app.orchestrator.handlers import JobContext, JobFailed, JobHandler, JobRegistry, Schedule, monthly
from app.orchestrator.queue import DbJobQueue
from app.orchestrator.worker import Worker
from tests.conftest import make_settings
from tests.db.seed import Seed


@pytest.fixture
def seeded(database: DatabaseSettings) -> Iterator[Seed]:
    with psycopg.connect(database.role_url(APP_ROLE), autocommit=True) as conn:
        yield Seed(conn)


@pytest.fixture
def kind(seeded: Seed) -> str:
    key = f"test_worker_{uuid.uuid4().hex[:8]}"
    seeded.insert("job_kind", key=key, description="Test Job Kind")
    return key


@pytest.fixture
def queue(database: DatabaseSettings) -> DbJobQueue:
    return DbJobQueue(session_factory(database.role_url(APP_ROLE)))


def worker(queue: DbJobQueue, registry: JobRegistry, database: DatabaseSettings) -> Worker:
    settings = make_settings(database_url=database.role_url(APP_ROLE))
    return Worker(queue, registry, settings, worker_id="test-worker")


def test_a_job_runs_its_steps_in_order_passing_outputs_on(queue: DbJobQueue, kind: str, database: DatabaseSettings) -> None:
    seen: list[str] = []

    def fetch(ctx: JobContext) -> dict[str, Any]:
        seen.append(f"fetch {ctx.job.payload['source']}")
        return {"item_count": 3}

    def store(ctx: JobContext) -> dict[str, Any]:
        seen.append(f"store {ctx.outputs['fetch']['item_count']}")
        return {}

    registry = JobRegistry()
    registry.register(JobHandler(kind, steps=(("fetch", fetch), ("store", store))))
    job_id = queue.enqueue(NewJob(kind=kind, payload={"source": "sample"}))

    assert worker(queue, registry, database).run_once() is True
    assert seen == ["fetch sample", "store 3"]
    assert queue.status(job_id).status == "succeeded"
    assert worker(queue, registry, database).run_once() is False  # nothing left


def test_a_failed_step_is_retried_and_the_job_resumes_after_the_steps_already_done(
    queue: DbJobQueue, kind: str, database: DatabaseSettings
) -> None:
    runs: list[str] = []
    fail_store = [True]

    def fetch(ctx: JobContext) -> dict[str, Any]:
        runs.append("fetch")
        return {}

    def store(ctx: JobContext) -> dict[str, Any]:
        runs.append("store")
        if fail_store.pop(0) if fail_store else False:
            raise JobFailed("database_busy", retry_after_seconds=0)
        return {}

    registry = JobRegistry()
    registry.register(JobHandler(kind, steps=(("fetch", fetch), ("store", store))))
    job_id = queue.enqueue(NewJob(kind=kind))
    w = worker(queue, registry, database)
    w.run_once()
    assert (queue.status(job_id).status, queue.status(job_id).last_error) == ("queued", "database_busy")
    w.run_once()
    assert runs == ["fetch", "store", "store"]  # fetch isn't run again
    assert queue.status(job_id).status == "succeeded"


def test_an_unexpected_error_is_recorded_by_type_never_by_message(
    queue: DbJobQueue, kind: str, database: DatabaseSettings, caplog: pytest.LogCaptureFixture
) -> None:
    def leaky(ctx: JobContext) -> dict[str, Any]:
        raise ValueError("Could not parse the letter for Jane Citizen")

    registry = JobRegistry()
    registry.register(JobHandler(kind, steps=(("parse", leaky),)))
    job_id = queue.enqueue(NewJob(kind=kind, max_attempts=1))
    with caplog.at_level(logging.INFO):
        worker(queue, registry, database).run_once()
    status = queue.status(job_id)
    assert (status.status, status.last_error) == ("failed", "unexpected_error:valueerror")
    assert "Jane Citizen" not in caplog.text
    assert str(job_id) in caplog.text


def test_a_scheduled_job_is_enqueued_once_when_due(queue: DbJobQueue, kind: str, database: DatabaseSettings) -> None:
    registry = JobRegistry()
    registry.register(JobHandler(kind, steps=(("noop", lambda ctx: {}),)))
    registry.schedule(Schedule(kind, due=monthly(day=1)))
    w = worker(queue, registry, database)

    assert w.enqueue_due() == [kind]  # never run: due now
    assert w.enqueue_due() == []  # already enqueued this month
    latest = queue.latest(kind)
    assert latest is not None and latest.status == "queued"


def test_monthly_is_the_most_recent_first_of_the_month() -> None:
    due = monthly(day=1)
    assert due(datetime(2026, 9, 25, 10, tzinfo=UTC)) == datetime(2026, 9, 1, tzinfo=UTC)
    assert due(datetime(2026, 9, 1, 0, 0, tzinfo=UTC)) == datetime(2026, 9, 1, tzinfo=UTC)
    assert due(datetime(2026, 1, 15, tzinfo=UTC)) == datetime(2026, 1, 1, tzinfo=UTC)
    assert monthly(day=15)(datetime(2026, 1, 10, tzinfo=UTC)) == datetime(2025, 12, 15, tzinfo=UTC)

