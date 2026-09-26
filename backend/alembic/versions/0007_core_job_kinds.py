"""Core Job Kinds (#18): the registry the queue checks every Job against (design doc §6.3).

Specialty Modules register their own Job Kinds in their own migrations, with `module_key` set.

Revision ID: 0007_core_job_kinds
Revises: 0006_care_team_primary
Create Date: 2026-09-25
"""

from alembic import op

revision = "0007_core_job_kinds"
down_revision = "0006_care_team_primary"
branch_labels = None
depends_on = None

CORE_JOB_KINDS = {
    "refresh_pbs": "Refresh the PBS Schedule (monthly on the 1st, or on demand)",
}


def upgrade() -> None:
    for key, description in CORE_JOB_KINDS.items():
        op.execute(f"INSERT INTO job_kind (key, module_key, description) VALUES ('{key}', NULL, '{description}')")


def downgrade() -> None:
    op.execute("DELETE FROM job_kind WHERE key IN (" + ", ".join(f"'{k}'" for k in CORE_JOB_KINDS) + ")")
