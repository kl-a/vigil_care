"""Job queue interface (ADR 0003): contract tests any JobQueue must pass. The database queue today; a managed
queue later joins by adding a factory to QUEUES.

Each test registers its own Job Kinds, and every claim names the kinds it can run, so tests never take each
other's Jobs from the shared test database.
"""

import uuid
from collections.abc import Callable, Iterator
from datetime import timedelta
from typing import Any

import psycopg
import pytest

from app.core.database import session_factory
from app.core.seams.queue import (
    DEFAULT_LEASE,
    JobQueue,
    NewJob,
    NotIdsOnly,
    QueueDepth,
    UnknownJobKind,
    ModuleInactive,
)
from app.db.provision import APP_ROLE, DatabaseSettings
from app.orchestrator.queue import DbJobQueue
from tests.db.seed import Seed

QUEUES: dict[str, Callable[[DatabaseSettings], JobQueue]] = {
    "database": lambda database: DbJobQueue(session_factory(database.role_url(APP_ROLE))),
}


@pytest.fixture(params=QUEUES)
def queue(request: pytest.FixtureRequest, database: DatabaseSettings) -> JobQueue:
    return QUEUES[request.param](database)


@pytest.fixture
def seeded(database: DatabaseSettings) -> Iterator[Seed]:
    with psycopg.connect(database.role_url(APP_ROLE), autocommit=True) as conn:
        yield Seed(conn)


@pytest.fixture
def kind(seeded: Seed) -> str:
    """A Core Job Kind of this test's own."""
    key = f"test_core_{uuid.uuid4().hex[:8]}"
    seeded.insert("job_kind", key=key, description="Test Job Kind")
    return key


@pytest.fixture
def oncology_kind(seeded: Seed) -> str:
    """A Job Kind registered by the Oncology module."""
    key = f"test_oncology_{uuid.uuid4().hex[:8]}"
    seeded.insert("job_kind", key=key, module_key="oncology", description="Test Oncology Job Kind")
    return key


def test_an_enqueued_job_is_claimed_once(queue: JobQueue, kind: str) -> None:
    job_id = queue.enqueue(NewJob(kind=kind, payload={"document_id": str(uuid.uuid4())}))
    claimed = queue.claim("worker-a", kinds=[kind])
    assert claimed is not None and claimed.id == job_id
    assert (claimed.kind, claimed.attempt, claimed.completed_steps) == (kind, 1, {})
    assert queue.claim("worker-b", kinds=[kind]) is None
    assert queue.status(job_id).status == "running"


def test_two_workers_claim_different_jobs(queue: JobQueue, kind: str) -> None:
    first, second = queue.enqueue(NewJob(kind=kind)), queue.enqueue(NewJob(kind=kind))
    a, b = queue.claim("worker-a", kinds=[kind]), queue.claim("worker-b", kinds=[kind])
    assert a is not None and b is not None
    assert {a.id, b.id} == {first, second}


def test_higher_priority_first_and_nothing_before_it_is_due(queue: JobQueue, kind: str) -> None:
    later = queue.enqueue(NewJob(kind=kind, run_after_seconds=3600))
    low = queue.enqueue(NewJob(kind=kind, priority=0))
    high = queue.enqueue(NewJob(kind=kind, priority=5))
    claimed = [queue.claim("w", kinds=[kind]), queue.claim("w", kinds=[kind]), queue.claim("w", kinds=[kind])]
    assert [c.id if c else None for c in claimed] == [high, low, None]
    assert queue.status(later).status == "queued"


def test_an_unknown_job_kind_is_refused(queue: JobQueue) -> None:
    with pytest.raises(UnknownJobKind):
        queue.enqueue(NewJob(kind="no_such_kind"))


def test_a_modules_job_kind_needs_the_module_active_for_its_practice(queue: JobQueue, oncology_kind: str, seeded: Seed) -> None:
    inactive = seeded.practice()
    with pytest.raises(ModuleInactive):
        queue.enqueue(NewJob(kind=oncology_kind, practice_id=inactive))

    active = seeded.practice()
    user = seeded.user(active)
    activation = seeded.insert("practice_module", practice_id=active, module_key="oncology", changed_by_user_id=user)
    job_id = queue.enqueue(NewJob(kind=oncology_kind, practice_id=active))
    # Switched off before the Job runs: it doesn't run.
    seeded.conn.execute("UPDATE practice_module SET is_active = false WHERE id = %s", [activation])
    assert queue.claim("w", kinds=[oncology_kind]) is None
    status = queue.status(job_id)
    assert (status.status, status.last_error) == ("cancelled", "module_inactive")


def test_system_wide_jobs_of_a_module_kind_run(queue: JobQueue, oncology_kind: str) -> None:
    job_id = queue.enqueue(NewJob(kind=oncology_kind))
    claimed = queue.claim("w", kinds=[oncology_kind])
    assert claimed is not None and claimed.id == job_id


@pytest.mark.parametrize(
    "payload",
    [{"patient_name": "Jane Citizen"}, {"note": "Referred by Dr Smith"}, {"ids": ["ok-id", "Jane Citizen"]}, {"nested": {"a": 1}}],
)
def test_payloads_hold_ids_only(queue: JobQueue, kind: str, payload: dict[str, Any]) -> None:
    with pytest.raises(NotIdsOnly):
        queue.enqueue(NewJob(kind=kind, payload=payload))


def test_ids_counts_and_short_codes_are_fine(queue: JobQueue, kind: str) -> None:
    payload = {"document_id": str(uuid.uuid4()), "pages": [1, 2], "force": True, "schedule_date": "2026-09-01", "source": "pbs_api"}
    job_id = queue.enqueue(NewJob(kind=kind, payload=payload))
    claimed = queue.claim("w", kinds=[kind])
    assert claimed is not None and claimed.id == job_id and claimed.payload == payload


def test_a_failed_job_is_retried_until_max_attempts(queue: JobQueue, kind: str) -> None:
    job_id = queue.enqueue(NewJob(kind=kind, max_attempts=2))
    first = queue.claim("w", kinds=[kind])
    assert first is not None
    queue.fail(job_id, "source_unreachable", retry_after_seconds=0)
    assert queue.status(job_id).status == "queued"
    second = queue.claim("w", kinds=[kind])
    assert second is not None and second.attempt == 2
    queue.fail(job_id, "source_unreachable", retry_after_seconds=0)
    status = queue.status(job_id)
    assert (status.status, status.attempts, status.last_error) == ("failed", 2, "source_unreachable")
    assert status.finished_at is not None
    assert queue.claim("w", kinds=[kind]) is None


def test_a_retry_resumes_after_the_last_completed_step(queue: JobQueue, kind: str) -> None:
    job_id = queue.enqueue(NewJob(kind=kind))
    queue.claim("w", kinds=[kind])
    queue.step_done(job_id, "fetch", {"item_count": 3})
    queue.fail(job_id, "parse_failed", retry_after_seconds=0)
    again = queue.claim("w", kinds=[kind])
    assert again is not None and again.completed_steps == {"fetch": {"item_count": 3}}
    queue.step_done(job_id, "store", {})
    queue.succeed(job_id)
    status = queue.status(job_id)
    assert status.status == "succeeded" and status.finished_at is not None
    assert [(s.name, s.status) for s in status.steps] == [("fetch", "succeeded"), ("store", "succeeded")]


def test_step_outputs_and_errors_hold_ids_only(queue: JobQueue, kind: str) -> None:
    job_id = queue.enqueue(NewJob(kind=kind))
    queue.claim("w", kinds=[kind])
    with pytest.raises(NotIdsOnly):
        queue.step_done(job_id, "read", {"text": "Jane Citizen, DOB 03/04/1962"})
    with pytest.raises(NotIdsOnly):
        queue.fail(job_id, "Could not read Jane Citizen's letter")


def test_a_job_left_running_by_a_crashed_worker_is_claimed_again(queue: JobQueue, kind: str) -> None:
    job_id = queue.enqueue(NewJob(kind=kind))
    queue.claim("crashed", kinds=[kind], lease=timedelta(seconds=0))
    reclaimed = queue.claim("w", kinds=[kind], lease=timedelta(seconds=0))
    assert reclaimed is not None and reclaimed.id == job_id and reclaimed.attempt == 2


def test_the_latest_job_of_a_kind(queue: JobQueue, kind: str) -> None:
    assert queue.latest(kind) is None
    queue.enqueue(NewJob(kind=kind))
    newest = queue.enqueue(NewJob(kind=kind))
    latest = queue.latest(kind)
    assert latest is not None and latest.id == newest


# --- What the Support Views read (#10): recent Jobs and the queue's depth, system-wide plus one Practice's ---


def test_recent_jobs_are_system_wide_and_the_practices_own(queue: JobQueue, kind: str, seeded: Seed) -> None:
    ours, theirs = seeded.practice(), seeded.practice()
    system = queue.enqueue(NewJob(kind=kind))
    document = str(uuid.uuid4())
    mine = queue.enqueue(NewJob(kind=kind, practice_id=ours, payload={"document_id": document}))
    queue.enqueue(NewJob(kind=kind, practice_id=theirs))
    recent = queue.recent(ours, kinds=[kind])
    assert [job.id for job in recent] == [mine, system]  # newest first
    assert recent[0].payload == {"document_id": document}
    assert [job.id for job in queue.recent(ours, kinds=[kind], limit=1)] == [mine]
    assert [job.id for job in queue.recent(None, kinds=[kind])] == [system]


def test_recent_jobs_carry_their_steps_outputs(queue: JobQueue, kind: str) -> None:
    job_id = queue.enqueue(NewJob(kind=kind))
    queue.claim("w", kinds=[kind])
    queue.step_done(job_id, "fetch", {"item_count": 3, "schedule_date": "2026-09-01"})
    [job] = queue.recent(None, kinds=[kind])
    assert [(s.name, s.output) for s in job.steps] == [("fetch", {"item_count": 3, "schedule_date": "2026-09-01"})]


def test_the_queues_depth(queue: JobQueue, kind: str, seeded: Seed) -> None:
    ours = seeded.practice()
    queue.enqueue(NewJob(kind=kind))
    queue.enqueue(NewJob(kind=kind, practice_id=ours))
    queue.enqueue(NewJob(kind=kind, practice_id=seeded.practice()))
    running = queue.enqueue(NewJob(kind=kind, priority=9, max_attempts=1))
    queue.claim("w", kinds=[kind])
    assert queue.depth(ours, kinds=[kind]) == QueueDepth(queued=2, running=1, failed_last_day=0)
    queue.fail(running, "source_unreachable")
    assert queue.depth(ours, kinds=[kind]) == QueueDepth(queued=2, running=0, failed_last_day=1)


# --- Lease renewal (#31): a worker still running a Job keeps its claim; one that stopped loses it ---


LEASE = DEFAULT_LEASE


def _claimed_long_ago(seeded: Seed, job_id: uuid.UUID) -> None:
    seeded.conn.execute("UPDATE job SET locked_at = now() - interval '1 hour' WHERE id = %s", [job_id])


def test_a_worker_that_renews_its_job_keeps_it_past_the_lease(queue: JobQueue, kind: str, seeded: Seed) -> None:
    job_id = queue.enqueue(NewJob(kind=kind))
    queue.claim("worker-a", kinds=[kind], lease=LEASE)
    _claimed_long_ago(seeded, job_id)
    assert queue.renew(job_id, "worker-a") is True
    assert queue.claim("worker-b", kinds=[kind], lease=LEASE) is None
    assert queue.status(job_id).attempts == 1


def test_a_job_whose_worker_stopped_renewing_is_claimed_again(queue: JobQueue, kind: str, seeded: Seed) -> None:
    job_id = queue.enqueue(NewJob(kind=kind))
    queue.claim("worker-a", kinds=[kind], lease=LEASE)
    _claimed_long_ago(seeded, job_id)
    reclaimed = queue.claim("worker-b", kinds=[kind], lease=LEASE)
    assert reclaimed is not None and reclaimed.id == job_id and reclaimed.attempt == 2


def test_renewing_a_job_another_worker_has_claimed_does_nothing(queue: JobQueue, kind: str, seeded: Seed) -> None:
    job_id = queue.enqueue(NewJob(kind=kind))
    queue.claim("worker-a", kinds=[kind], lease=LEASE)
    _claimed_long_ago(seeded, job_id)
    queue.claim("worker-b", kinds=[kind], lease=LEASE)  # worker-a stopped renewing; worker-b took over
    _claimed_long_ago(seeded, job_id)
    assert queue.renew(job_id, "worker-a") is False
    # worker-a's renewal didn't keep worker-b's stale claim alive.
    reclaimed = queue.claim("worker-c", kinds=[kind], lease=LEASE)
    assert reclaimed is not None and reclaimed.attempt == 3


def test_a_finished_job_is_not_renewed(queue: JobQueue, kind: str) -> None:
    job_id = queue.enqueue(NewJob(kind=kind))
    queue.claim("worker-a", kinds=[kind])
    queue.succeed(job_id)
    assert queue.renew(job_id, "worker-a") is False
    assert queue.status(job_id).status == "succeeded"
