"""Every Job Kind's handler and schedule (design doc §3). Tooling, like app/db/metadata: it imports each module's
jobs so the worker can run them, and composes steps from several modules where a Job spans them (design doc §14:
modules don't call each other's workflows). Each Job Kind here is also registered by a migration (`job_kind`).
"""

from app.db import metadata  # noqa: F401  (every table, so the worker's rows resolve their foreign keys)
from app.core.jobs import JobHandler, JobRegistry
from app.modules.medications import drug_reference
from app.modules.pbs import refresh as pbs_refresh


def pbs_refresh_handler(kind: str = pbs_refresh.KIND, api: pbs_refresh.SourceFactory = pbs_refresh.api_source) -> JobHandler:
    """The PBS Refresh (#19), then the drug reference rebuilt from the schedule it loaded (#36). Tests pass a
    `kind` of their own and an `api` replaying the recorded fixture."""
    steps = pbs_refresh.handler(api=api).steps
    return JobHandler(kind, steps=(*steps, (drug_reference.STEP, drug_reference.step)))


def registry() -> JobRegistry:
    jobs = JobRegistry()
    jobs.register(pbs_refresh_handler())
    jobs.schedule(pbs_refresh.MONTHLY)
    return jobs
