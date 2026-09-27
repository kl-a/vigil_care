"""A Treatment Course's best response is derived (#43): the best direction among its Cancer Diagnosis's Response
Assessments dated during the course, never stored. Drops `oncology_course_detail.best_response`.

Design doc §6.2–6.3.

Revision ID: 0014_best_response_derived
Revises: 0013_recurrence_ruled_out
Create Date: 2026-09-27
"""

import sqlalchemy as sa
from alembic import op

revision = "0014_best_response_derived"
down_revision = "0013_recurrence_ruled_out"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.drop_column("oncology_course_detail", "best_response")


def downgrade() -> None:
    op.add_column("oncology_course_detail", sa.Column("best_response", sa.Text(), nullable=True))
    op.create_check_constraint(
        op.f("ck_oncology_course_detail_best_response_allowed"), "oncology_course_detail",
        "best_response IN ('CR', 'PR', 'SD', 'PD', 'NE')",
    )
