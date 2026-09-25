"""The worker (#18): claims Jobs from the queue and runs them; enqueues scheduled Jobs when they fall due.

    python -m app.orchestrator.worker      # its own service in Docker Compose and run-local.sh --dev

Logs carry Job ids, Job Kinds and error codes only (design doc §6.4).
"""

import logging
import socket
import time
import uuid
from collections.abc import Mapping
from datetime import UTC, datetime
from typing import Any

from app.core.config import Settings
from app.core.database import session_factory
from app.core.seams.queue import JobQueue, NewJob
from app.core.jobs import JobContext, JobFailed, JobRegistry
from app.orchestrator.queue import DbJobQueue

log = logging.getLogger("vigil.worker")
POLL_SECONDS = 5
RETRY_BASE_SECONDS = 30


class Worker:
    def __init__(self, queue: JobQueue, registry: JobRegistry, settings: Settings, worker_id: str | None = None) -> None:
        self._queue = queue
        self._registry = registry
        self._settings = settings
        self._sessions = session_factory(settings.database_url)
        self.worker_id = worker_id or f"{socket.gethostname()}:{uuid.uuid4().hex[:6]}"

    def run_once(self) -> bool:
        """Runs the next due Job, if any. True if there was one."""
        job = self._queue.claim(self.worker_id, kinds=self._registry.kinds)
        if job is None:
            return False
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
                self._queue.fail(job.id, failure.code, retry_after_seconds=retry)
                return True
            except Exception as error:  # noqa: BLE001  (recorded by type only: a message may hold Patient data)
                code = f"unexpected_error:{type(error).__name__.lower()}"
                log.error("job %s %s: step %s failed: %s", job.id, job.kind, name, code)
                self._queue.fail(job.id, code, retry_after_seconds=backoff)
                return True
            self._queue.step_done(job.id, name, output)
            outputs[name] = output
        self._queue.succeed(job.id)
        log.info("job %s %s: succeeded", job.id, job.kind)
        return True

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
