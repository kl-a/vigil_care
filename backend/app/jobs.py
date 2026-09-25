"""Every Job Kind's handler and schedule (design doc §3). Tooling, like app/db/metadata: it imports each module's
jobs so the worker can run them. Each Job Kind here is also registered by a migration (`job_kind`).
"""

from app.orchestrator.handlers import JobRegistry


def registry() -> JobRegistry:
    jobs = JobRegistry()
    # Modules register their handlers and schedules here, e.g. the PBS Refresh (#19).
    return jobs
