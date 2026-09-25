"""Value sets shared by more than one module (design doc §6.2). Module-only sets live with their models."""

from typing import Literal, get_args

JobTitle = Literal["clinician", "trial_coordinator", "secretary", "developer_admin"]
JOB_TITLES: tuple[str, ...] = get_args(JobTitle)
# As people read them (the frontend's JOB_TITLE_LABEL says the same).
JOB_TITLE_LABEL: dict[str, str] = {
    "clinician": "Clinician",
    "trial_coordinator": "Trial coordinator",
    "secretary": "Secretary",
    "developer_admin": "Developer admin",
}
# Job Titles that may verify anything; a developer admin never verifies (design doc §6.4).
VERIFYING_JOB_TITLES = ("clinician", "trial_coordinator", "secretary")

TREATMENT_INTENTS = ("curative", "neoadjuvant", "adjuvant", "palliative")
RUN_STATUSES = ("queued", "running", "succeeded", "failed", "cancelled")
REFRESH_STATUSES = ("succeeded", "partial", "failed")
CONFIDENCE_LEVELS = ("high", "medium", "low")
