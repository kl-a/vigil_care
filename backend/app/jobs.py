"""Every Job Kind's handler and schedule (design doc §3). Tooling, like app/db/metadata: it imports each module's
jobs so the worker can run them. Each Job Kind here is also registered by a migration (`job_kind`).
"""

from app.db import metadata  # noqa: F401  (every table, so the worker's rows resolve their foreign keys)
from app.modules.pbs import refresh as pbs_refresh
from app.core.jobs import JobRegistry


def registry() -> JobRegistry:
    jobs = JobRegistry()
    jobs.register(pbs_refresh.handler())
    jobs.schedule(pbs_refresh.MONTHLY)
    return jobs
