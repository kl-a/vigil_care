"""PBS Refresh (#19): each item points at the Refresh that loaded it; a Refresh records its source (the PBS
Schedule API or the bundled sample) and the schedule's Safety Net thresholds; items keep their form, program
and, for infusions, the maximum amount.

Nothing wrote to these tables before #19, so the new required columns need no default.

Design doc §6.3.

Revision ID: 0008_pbs_refresh
Revises: 0007_core_job_kinds
Create Date: 2026-09-25
"""

import sqlalchemy as sa
from alembic import op

revision = "0008_pbs_refresh"
down_revision = "0007_core_job_kinds"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("pbs_refresh_log", sa.Column("source", sa.Text(), nullable=False))
    op.add_column("pbs_refresh_log", sa.Column("safety_net_general", sa.Numeric(), nullable=True))
    op.add_column("pbs_refresh_log", sa.Column("safety_net_concessional", sa.Numeric(), nullable=True))
    op.create_check_constraint(op.f("ck_pbs_refresh_log_source_allowed"), "pbs_refresh_log", "source IN ('pbs_api', 'sample')")

    op.add_column("pbs_item", sa.Column("form", sa.Text(), nullable=True))
    op.add_column("pbs_item", sa.Column("program_code", sa.Text(), nullable=True))
    op.add_column("pbs_item", sa.Column("max_amount", sa.Numeric(), nullable=True))
    op.add_column("pbs_item", sa.Column("amount_unit", sa.Text(), nullable=True))
    op.add_column("pbs_item", sa.Column("refresh_log_id", sa.UUID(), nullable=False))
    op.create_foreign_key(
        op.f("fk_pbs_item_refresh_log_id"), "pbs_item", "pbs_refresh_log", ["refresh_log_id"], ["id"], ondelete="RESTRICT"
    )
    op.create_index(op.f("ix_pbs_item_refresh_log_id"), "pbs_item", ["refresh_log_id"], unique=False)


def downgrade() -> None:
    op.drop_index(op.f("ix_pbs_item_refresh_log_id"), table_name="pbs_item")
    op.drop_constraint(op.f("fk_pbs_item_refresh_log_id"), "pbs_item", type_="foreignkey")
    for column in ("refresh_log_id", "amount_unit", "max_amount", "program_code", "form"):
        op.drop_column("pbs_item", column)
    op.drop_constraint("ck_pbs_refresh_log_source_allowed", "pbs_refresh_log", type_="check")
    for column in ("safety_net_concessional", "safety_net_general", "source"):
        op.drop_column("pbs_refresh_log", column)
