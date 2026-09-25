"""Patient Pseudonyms (#8): a sequence, so each Patient gets a new one and none is ever reused.

Pseudonyms read `VG-0100`, `VG-0101`, … The sequence starts at 100: the synthetic demo Patients keep the
frontend brief's VG-0042 to VG-0044.

Design doc §6.3, §9.3.

Revision ID: 0005_patient_pseudonyms
Revises: 0004_sites
Create Date: 2026-09-25
"""

from alembic import op

revision = "0005_patient_pseudonyms"
down_revision = "0004_sites"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute("CREATE SEQUENCE patient_pseudonym_seq START 100 NO CYCLE")
    op.execute("GRANT USAGE ON SEQUENCE patient_pseudonym_seq TO vigil_app")


def downgrade() -> None:
    op.execute("DROP SEQUENCE patient_pseudonym_seq")
