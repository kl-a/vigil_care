"""Lab panels (#42): bloods are entered by hand as a panel, one save with one Verification, so each result
says which panel it came in (`panel_id`, the Verification's subject for the panel).

Design doc §6.3.

Revision ID: 0011_lab_panels
Revises: 0010_drug_reference_from_pbs
Create Date: 2026-09-27
"""

import sqlalchemy as sa
from alembic import op

revision = "0011_lab_panels"
down_revision = "0010_drug_reference_from_pbs"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("lab_result", sa.Column("panel_id", sa.UUID(), nullable=True))
    op.create_index(op.f("ix_lab_result_panel_id"), "lab_result", ["panel_id"], unique=False)


def downgrade() -> None:
    op.drop_index(op.f("ix_lab_result_panel_id"), table_name="lab_result")
    op.drop_column("lab_result", "panel_id")
