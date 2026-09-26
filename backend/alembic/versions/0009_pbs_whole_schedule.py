"""The whole PBS Schedule (#30): a Refresh keeps every PBS Item, not just cancer drugs, so the PBS Drug Lookup
can filter them. Each item keeps its WHO ATC codes (their first letter is the therapeutic group), its PBS
program's title, and its pack size and maximum packs per prescription (so quantities are shown with units).

Design doc §6.3.

Revision ID: 0009_pbs_whole_schedule
Revises: 0008_pbs_refresh
Create Date: 2026-09-26
"""

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision = "0009_pbs_whole_schedule"
down_revision = "0008_pbs_refresh"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("pbs_item", sa.Column("program_title", sa.Text(), nullable=True))
    op.add_column(
        "pbs_item",
        sa.Column("atc_codes", postgresql.JSONB(astext_type=sa.Text()), server_default=sa.text("'[]'::jsonb"), nullable=False),
    )
    op.add_column("pbs_item", sa.Column("max_packs", sa.Integer(), nullable=True))
    op.add_column("pbs_item", sa.Column("pack_size", sa.Integer(), nullable=True))


def downgrade() -> None:
    for column in ("pack_size", "max_packs", "atc_codes", "program_title"):
        op.drop_column("pbs_item", column)
