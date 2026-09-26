"""The worker (#18): claims Jobs from the queue and runs them; enqueues scheduled Jobs when they fall due.

    python -m app.orchestrator.worker      # its own service in Docker Compose and run-local.sh --dev

While it runs a Job, the worker renews its claim in the background (#31), so a long step (e.g. a PBS Refresh
waiting on the API) isn't taken over by another worker when the lease runs out. Before recording a step, success
or failure it renews once more; if another worker has taken the Job over, it stops and records nothing.

Logs carry Job ids, Job Kinds and error codes only (design doc §6.4).
"""

import logging
import socket
import threading
import time
import uuid
from collections.abc import Iterator, Mapping
from contextlib import contextmanager
from datetime import UTC, datetime
from typing import Any

from app.core.config import Settings
from app.core.database import session_factory
from app.core.seams.queue import DEFAULT_LEASE, ClaimedJob, JobQueue, NewJob
from app.core.jobs import JobContext, JobFailed, JobRegistry
from app.orchestrator.queue import DbJobQueue

log = logging.getLogger("vigil.worker")
POLL_SECONDS = 5
RETRY_BASE_SECONDS = 30
# Renewed well within the lease, so a slow renewal or two never lets it lapse.
RENEW_EVERY_SECONDS = DEFAULT_LEASE.total_seconds() / 3


class Worker:
    def __init__(
        self,
        queue: JobQueue,
        registry: JobRegistry,
        settings: Settings,
        worker_id: str | None = None,
        renew_every: float = RENEW_EVERY_SECONDS,
    ) -> None:
        self._queue = queue
        self._registry = registry
        self._settings = settings
        self._sessions = session_factory(settings.database_url)
        self.worker_id = worker_id or f"{socket.gethostname()}:{uuid.uuid4().hex[:6]}"
        self._renew_every = renew_every

    def run_once(self) -> bool:
        """Runs the next due Job, if any. True if there was one."""
        job = self._queue.claim(self.worker_id, kinds=self._registry.kinds)
        if job is None:
            return False
        with self._keeping_claim(job.id, job.kind):
            self._run(job)
        return True

    def _run(self, job: ClaimedJob) -> None:
        handler = self._registry.handlers[job.kind]
        outputs: dict[str, Mapping[str, Any]] = dict(job.completed_steps)
        context = JobContext(job=job, sessions=self._sessions, settings=self._settings, outputs=outputs)
        log.info("job %s %s: attempt %d", job.id, job.kind, job.attempt)
        backoff = RETRY_BASE_SECONDS * 2 ** (job.attempt - 1)
        for name, step in handler.steps:
            if name in job.completed_steps:
                continue
            try:
                output = step(context)
            except JobFailed as failure:
                log.warning("job %s %s: step %s failed: %s", job.id, job.kind, name, failure.code)
                retry = backoff if failure.retry_after_seconds is None else failure.retry_after_seconds
                if self._still_ours(job):
                    self._queue.fail(job.id, failure.code, retry_after_seconds=retry)
                return
            except Exception as error:  # noqa: BLE001  (recorded by type only: a message may hold Patient data)
                code = f"unexpected_error:{type(error).__name__.lower()}"
                log.error("job %s %s: step %s failed: %s", job.id, job.kind, name, code)
                if self._still_ours(job):
                    self._queue.fail(job.id, code, retry_after_seconds=backoff)
                return
            if not self._still_ours(job):
                return
            self._queue.step_done(job.id, name, output)
            outputs[name] = output
        if self._still_ours(job):
            self._queue.succeed(job.id)
            log.info("job %s %s: succeeded", job.id, job.kind)

    def _still_ours(self, job: ClaimedJob) -> bool:
        """Renews the claim before recording anything: if another worker has taken the Job over (this one's claim
        lapsed), this worker stops and leaves the Job to it."""
        if self._queue.renew(job.id, self.worker_id):
            return True
        log.warning("job %s %s: claim lost to another worker; stopping", job.id, job.kind)
        return False

    @contextmanager
    def _keeping_claim(self, job_id: uuid.UUID, kind: str) -> Iterator[None]:
        """Renews this worker's claim on the Job every `renew_every` seconds until the block ends."""
        done = threading.Event()

        def renew() -> None:
            while not done.wait(self._renew_every):
                try:
                    if not self._queue.renew(job_id, self.worker_id):
                        return  # lost: the Job's next write finds out and stops
                except Exception as error:  # noqa: BLE001  (e.g. the database briefly unreachable: try again next time)
                    log.warning("job %s %s: claim not renewed: %s", job_id, kind, type(error).__name__.lower())

        renewer = threading.Thread(target=renew, name=f"renew-{job_id}", daemon=True)
        renewer.start()
        try:
            yield
        finally:
            done.set()
            renewer.join(timeout=self._renew_every)

    def enqueue_due(self, now: datetime | None = None) -> list[str]:
        """Enqueues each scheduled Job Kind not yet enqueued since it last fell due. Returns the kinds enqueued."""
        now = now or datetime.now(UTC)
        enqueued = []
        for schedule in self._registry.schedules:
            latest = self._queue.latest(schedule.kind)
            if latest is not None and latest.status in ("queued", "running"):
                continue  # still waiting or running: no second copy
            if latest is None or latest.created_at < schedule.due(now):
                self._queue.enqueue(NewJob(kind=schedule.kind))
                enqueued.append(schedule.kind)
                log.info("scheduled %s enqueued", schedule.kind)
        return enqueued

    def run_forever(self, poll_seconds: int = POLL_SECONDS) -> None:
        log.info("worker %s: running %s", self.worker_id, ", ".join(self._registry.kinds) or "no Job Kinds")
        while True:
            self.enqueue_due()
            while self.run_once():
                pass
            time.sleep(poll_seconds)


def main() -> None:
    from app.jobs import registry

    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(name)s %(levelname)s %(message)s")
    settings = Settings()
    Worker(DbJobQueue(session_factory(settings.database_url)), registry(), settings).run_forever()


if __name__ == "__main__":
    main()
