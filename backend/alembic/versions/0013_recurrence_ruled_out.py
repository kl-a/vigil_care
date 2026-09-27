"""Recurrences can be ruled out (#39): a clinician resolves a Suspected Recurrence by confirming it, recording a
new primary instead, or ruling it out with a reason.

Design doc §6.2.

Revision ID: 0013_recurrence_ruled_out
Revises: 0012_cancer_types_mesh
Create Date: 2026-09-27
"""

from alembic import op

revision = "0013_recurrence_ruled_out"
down_revision = "0012_cancer_types_mesh"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.drop_constraint(op.f("ck_recurrence_status_allowed"), "recurrence", type_="check")
    op.create_check_constraint(
        op.f("ck_recurrence_status_allowed"), "recurrence",
        "status IN ('suspected', 'confirmed', 'reclassified_as_new_primary', 'ruled_out')",
    )


def downgrade() -> None:
    op.drop_constraint(op.f("ck_recurrence_status_allowed"), "recurrence", type_="check")
    op.create_check_constraint(
        op.f("ck_recurrence_status_allowed"), "recurrence", "status IN ('suspected', 'confirmed', 'reclassified_as_new_primary')"
    )
