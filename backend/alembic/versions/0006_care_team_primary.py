"""Care Team (#9): at most one primary member per Patient (the service moves it when another is chosen).

Design doc §6.3.

Revision ID: 0006_care_team_primary
Revises: 0005_patient_pseudonyms
Create Date: 2026-09-25
"""

import sqlalchemy as sa
from alembic import op

revision = "0006_care_team_primary"
down_revision = "0005_patient_pseudonyms"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_index(
        "uq_care_team_member_patient_id_primary",
        "care_team_member",
        ["patient_id"],
        unique=True,
        postgresql_where=sa.text("is_primary AND deleted_at IS NULL"),
    )


def downgrade() -> None:
    op.drop_index("uq_care_team_member_patient_id_primary", table_name="care_team_member")
