"""Sites: where a Practice sees Patients (#25).

Adds `site`, with at most one primary Site per Practice (the service keeps it at exactly one). Each
Practice gets a primary Site at its registered address, and the Practice's `lat`/`lng` move onto it.

Design doc §6.3.

Revision ID: 0004_sites
Revises: 0003_practice_memberships
Create Date: 2026-09-25
"""

import sqlalchemy as sa
from alembic import op

revision = "0004_sites"
down_revision = "0003_practice_memberships"
branch_labels = None
depends_on = None

SOFT_DELETE_CHECK = (
    "(deleted_at IS NULL AND deleted_by_user_id IS NULL AND deleted_reason IS NULL)"
    " OR (deleted_at IS NOT NULL AND deleted_by_user_id IS NOT NULL AND length(btrim(deleted_reason)) > 0)"
)


def upgrade() -> None:
    op.create_table(
        "site",
        sa.Column("id", sa.UUID(), server_default=sa.text("gen_random_uuid()"), nullable=False),
        sa.Column("practice_id", sa.UUID(), nullable=False),
        sa.Column("name", sa.Text(), nullable=False),
        sa.Column("address", sa.Text(), nullable=True),
        sa.Column("lat", sa.Numeric(), nullable=True),
        sa.Column("lng", sa.Numeric(), nullable=True),
        sa.Column("is_primary", sa.Boolean(), server_default=sa.text("false"), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("deleted_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("deleted_by_user_id", sa.UUID(), nullable=True),
        sa.Column("deleted_reason", sa.Text(), nullable=True),
        sa.CheckConstraint(SOFT_DELETE_CHECK, name=op.f("ck_site_soft_delete")),
        sa.ForeignKeyConstraint(["practice_id"], ["practice.id"], name=op.f("fk_site_practice_id"), ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(
            ["deleted_by_user_id", "practice_id"],
            ["practice_membership.user_id", "practice_membership.practice_id"],
            name=op.f("fk_site_deleted_by_user_id_practice_id"),
            ondelete="RESTRICT",
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_site")),
        sa.UniqueConstraint("id", "practice_id", name=op.f("uq_site_id_practice_id")),
    )
    op.create_index(op.f("ix_site_deleted_by_user_id"), "site", ["deleted_by_user_id"])
    op.create_index(op.f("ix_site_practice_id"), "site", ["practice_id"])
    op.create_index(
        "uq_site_practice_id_primary",
        "site",
        ["practice_id"],
        unique=True,
        postgresql_where=sa.text("is_primary AND deleted_at IS NULL"),
    )
    op.execute(
        "CREATE TRIGGER set_updated_at BEFORE UPDATE ON site FOR EACH ROW EXECUTE FUNCTION set_updated_at()"
    )

    # Each Practice's location moves to a primary Site at its registered address.
    op.execute(
        "INSERT INTO site (practice_id, name, address, lat, lng, is_primary)"
        " SELECT id, name, address, lat, lng, true FROM practice WHERE deleted_at IS NULL"
    )
    op.drop_column("practice", "lat")
    op.drop_column("practice", "lng")


def downgrade() -> None:
    op.add_column("practice", sa.Column("lat", sa.Numeric(), nullable=True))
    op.add_column("practice", sa.Column("lng", sa.Numeric(), nullable=True))
    op.execute(
        "UPDATE practice p SET lat = s.lat, lng = s.lng FROM site s"
        " WHERE s.practice_id = p.id AND s.is_primary AND s.deleted_at IS NULL"
    )
    op.drop_table("site")
