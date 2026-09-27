"""The drug reference built from the PBS Schedule (#36): each drug links to all its PBS Items by item code
(the single `pbs_item_id` goes: PBS Items are replaced each Refresh), and says whether it's in the current
schedule (a drug that leaves it stays, as Medications may point at it, but is no longer offered).

Nothing wrote to `drug_reference` before #36.

Design doc §6.3.

Revision ID: 0010_drug_reference_from_pbs
Revises: 0009_pbs_whole_schedule
Create Date: 2026-09-27
"""

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision = "0010_drug_reference_from_pbs"
down_revision = "0009_pbs_whole_schedule"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.drop_index(op.f("ix_drug_reference_pbs_item_id"), table_name="drug_reference")
    op.drop_constraint(op.f("fk_drug_reference_pbs_item_id"), "drug_reference", type_="foreignkey")
    op.drop_column("drug_reference", "pbs_item_id")
    op.add_column(
        "drug_reference",
        sa.Column("pbs_item_codes", postgresql.JSONB(astext_type=sa.Text()), server_default=sa.text("'[]'::jsonb"), nullable=False),
    )
    op.add_column("drug_reference", sa.Column("in_current_schedule", sa.Boolean(), server_default=sa.text("true"), nullable=False))


def downgrade() -> None:
    op.drop_column("drug_reference", "in_current_schedule")
    op.drop_column("drug_reference", "pbs_item_codes")
    op.add_column("drug_reference", sa.Column("pbs_item_id", sa.UUID(), nullable=True))
    op.create_foreign_key(
        op.f("fk_drug_reference_pbs_item_id"), "drug_reference", "pbs_item", ["pbs_item_id"], ["id"], ondelete="SET NULL"
    )
    op.create_index(op.f("ix_drug_reference_pbs_item_id"), "drug_reference", ["pbs_item_id"], unique=False)
