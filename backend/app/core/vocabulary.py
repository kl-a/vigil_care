"""Value sets shared by more than one module (design doc §6.2). Module-only sets live with their models."""

JOB_TITLES = ("clinician", "trial_coordinator", "secretary", "developer_admin")
# Job Titles that may verify anything; a developer admin never verifies (design doc §6.4).
VERIFYING_JOB_TITLES = ("clinician", "trial_coordinator", "secretary")

TREATMENT_INTENTS = ("curative", "neoadjuvant", "adjuvant", "palliative")
RUN_STATUSES = ("queued", "running", "succeeded", "failed", "cancelled")
REFRESH_STATUSES = ("succeeded", "partial", "failed")
CONFIDENCE_LEVELS = ("high", "medium", "low")
