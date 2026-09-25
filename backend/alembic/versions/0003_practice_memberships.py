"""Practice Memberships: one login, several Practices (#24).

A User becomes the person (username unique across Vigil). Their Job Title, active status, own Provider
entry and last login move to a Practice Membership, one per Practice. Every Practice-scoped reference to
a User now points at the Membership `(user_id, practice_id)`, so only a member can act in a Practice.
Existing Users get one Membership each, in the Practice they belonged to.

Design doc §6.2–§6.3.

Revision ID: 0003_practice_memberships
Revises: 0002_oncology
Create Date: 2026-09-25
"""

import sqlalchemy as sa
from alembic import op

revision = "0003_practice_memberships"
down_revision = "0002_oncology"
branch_labels = None
depends_on = None

MEMBERSHIP_COLUMNS = "practice_id, user_id, job_title, provider_id, is_active, last_login_at"
SOFT_DELETE_CHECK = (
    "(deleted_at IS NULL AND deleted_by_user_id IS NULL AND deleted_reason IS NULL)"
    " OR (deleted_at IS NOT NULL AND deleted_by_user_id IS NOT NULL AND length(btrim(deleted_reason)) > 0)"
)
# Support data with a practice_id: deleting a Practice's row also takes a member of that Practice.
SUPPORT_TABLES = ("job", "pipeline_run", "llm_call_log", "cloud_request")
JOB_TITLE_CHECK = "job_title IN ('clinician', 'trial_coordinator', 'secretary', 'developer_admin')"


def _user_references(target: str) -> list[tuple[str, str, str]]:
    """(table, constraint, column) for every composite `(column, practice_id)` FK pointing at `target`."""
    rows = op.get_bind().execute(
        sa.text(
            "SELECT c.conrelid::regclass::text, c.conname, a.attname FROM pg_constraint c"
            " JOIN pg_attribute a ON a.attrelid = c.conrelid AND a.attnum = c.conkey[1]"
            " WHERE c.contype = 'f' AND c.confrelid = CAST(:target AS regclass) AND cardinality(c.conkey) = 2"
            " AND c.conrelid <> CAST(:target AS regclass) ORDER BY 1, 2"
        ),
        {"target": target},
    )
    return [(table, name, column) for table, name, column in rows]


def _repoint(references: list[tuple[str, str, str]], parent: str) -> None:
    for table, name, column in references:
        op.execute(f"ALTER TABLE {table} DROP CONSTRAINT {name}")
        op.execute(
            f"ALTER TABLE {table} ADD CONSTRAINT {name} FOREIGN KEY ({column}, practice_id)"
            f" REFERENCES {parent} ON DELETE RESTRICT"
        )


def upgrade() -> None:
    op.execute(
        "DO $$ BEGIN IF EXISTS (SELECT 1 FROM \"user\" GROUP BY username HAVING count(*) > 1) THEN"
        " RAISE EXCEPTION 'Two Practices have a User with the same username; rename one before migrating.';"
        " END IF; END $$"
    )
    op.create_table(
        "practice_membership",
        sa.Column("id", sa.UUID(), server_default=sa.text("gen_random_uuid()"), nullable=False),
        sa.Column("practice_id", sa.UUID(), nullable=False),
        sa.Column("user_id", sa.UUID(), nullable=False),
        sa.Column("job_title", sa.Text(), nullable=False),
        sa.Column("provider_id", sa.UUID(), nullable=True),
        sa.Column("is_active", sa.Boolean(), server_default=sa.text("true"), nullable=False),
        sa.Column("last_login_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("deleted_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("deleted_by_user_id", sa.UUID(), nullable=True),
        sa.Column("deleted_reason", sa.Text(), nullable=True),
        sa.CheckConstraint(JOB_TITLE_CHECK, name=op.f("ck_practice_membership_job_title_allowed")),
        sa.CheckConstraint(SOFT_DELETE_CHECK, name=op.f("ck_practice_membership_soft_delete")),
        sa.ForeignKeyConstraint(["practice_id"], ["practice.id"], name=op.f("fk_practice_membership_practice_id"), ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(["user_id"], ["user.id"], name=op.f("fk_practice_membership_user_id"), ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(
            ["provider_id", "practice_id"],
            ["provider.id", "provider.practice_id"],
            name=op.f("fk_practice_membership_provider_id_practice_id"),
            ondelete="SET NULL (provider_id)",
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_practice_membership")),
        sa.UniqueConstraint("id", "practice_id", name=op.f("uq_practice_membership_id_practice_id")),
        sa.UniqueConstraint("user_id", "practice_id", name=op.f("uq_practice_membership_user_id_practice_id")),
    )
    op.create_index(op.f("ix_practice_membership_deleted_by_user_id"), "practice_membership", ["deleted_by_user_id"])
    op.create_index(op.f("ix_practice_membership_practice_id"), "practice_membership", ["practice_id"])
    op.create_index(op.f("ix_practice_membership_provider_id"), "practice_membership", ["provider_id"])
    op.execute(
        "CREATE TRIGGER set_updated_at BEFORE UPDATE ON practice_membership"
        " FOR EACH ROW EXECUTE FUNCTION set_updated_at()"
    )

    # One Membership per existing User, in the Practice they belonged to. A soft-deleted User stays deleted there.
    op.execute(
        f"INSERT INTO practice_membership ({MEMBERSHIP_COLUMNS}, created_at, deleted_at, deleted_by_user_id, deleted_reason)"
        f' SELECT practice_id, id, job_title, provider_id, is_active, last_login_at, created_at,'
        f' deleted_at, deleted_by_user_id, deleted_reason FROM "user"'
    )
    _repoint(_user_references('"user"'), "practice_membership (user_id, practice_id)")
    op.create_foreign_key(
        op.f("fk_practice_membership_deleted_by_user_id_practice_id"),
        "practice_membership",
        "practice_membership",
        ["deleted_by_user_id", "practice_id"],
        ["user_id", "practice_id"],
        ondelete="RESTRICT",
    )

    for table in SUPPORT_TABLES:
        op.create_foreign_key(
            op.f(f"fk_{table}_deleted_by_user_id_practice_id"),
            table,
            "practice_membership",
            ["deleted_by_user_id", "practice_id"],
            ["user_id", "practice_id"],
            ondelete="RESTRICT",
        )

    # The User is now the person: one login across Vigil.
    op.drop_constraint("fk_user_deleted_by_user_id_practice_id", "user", type_="foreignkey")
    op.drop_constraint("uq_user_id_practice_id", "user", type_="unique")
    op.drop_constraint("uq_user_practice_id_username", "user", type_="unique")
    for column in ("practice_id", "job_title", "provider_id", "is_active", "last_login_at"):
        op.drop_column("user", column)
    op.create_unique_constraint(op.f("uq_user_username"), "user", ["username"])
    op.create_foreign_key(
        op.f("fk_user_deleted_by_user_id"), "user", "user", ["deleted_by_user_id"], ["id"], ondelete="RESTRICT"
    )


def downgrade() -> None:
    """Only possible while every User has exactly one Membership; otherwise it refuses rather than lose one."""
    op.execute(
        "DO $$ BEGIN IF EXISTS (SELECT 1 FROM practice_membership GROUP BY user_id HAVING count(*) > 1) THEN"
        " RAISE EXCEPTION 'A User belongs to several Practices; downgrading would lose a Practice Membership.';"
        " END IF; END $$"
    )
    for table in SUPPORT_TABLES:
        op.drop_constraint(f"fk_{table}_deleted_by_user_id_practice_id", table, type_="foreignkey")
    op.drop_constraint("fk_user_deleted_by_user_id", "user", type_="foreignkey")
    op.drop_constraint("uq_user_username", "user", type_="unique")
    op.add_column("user", sa.Column("practice_id", sa.UUID(), nullable=True))
    op.add_column("user", sa.Column("job_title", sa.Text(), nullable=True))
    op.add_column("user", sa.Column("provider_id", sa.UUID(), nullable=True))
    op.add_column("user", sa.Column("is_active", sa.Boolean(), server_default=sa.text("true"), nullable=False))
    op.add_column("user", sa.Column("last_login_at", sa.DateTime(timezone=True), nullable=True))
    op.execute(
        'UPDATE "user" u SET practice_id = m.practice_id, job_title = m.job_title, provider_id = m.provider_id,'
        " is_active = m.is_active, last_login_at = m.last_login_at FROM practice_membership m WHERE m.user_id = u.id"
    )
    op.alter_column("user", "practice_id", nullable=False)
    op.alter_column("user", "job_title", nullable=False)
    op.create_check_constraint(op.f("ck_user_job_title_allowed"), "user", JOB_TITLE_CHECK)
    op.create_foreign_key(op.f("fk_user_practice_id"), "user", "practice", ["practice_id"], ["id"], ondelete="RESTRICT")
    op.create_foreign_key(
        op.f("fk_user_provider_id_practice_id"),
        "user",
        "provider",
        ["provider_id", "practice_id"],
        ["id", "practice_id"],
        ondelete="SET NULL (provider_id)",
    )
    op.create_unique_constraint(op.f("uq_user_id_practice_id"), "user", ["id", "practice_id"])
    op.create_unique_constraint(op.f("uq_user_practice_id_username"), "user", ["practice_id", "username"])
    op.create_index(op.f("ix_user_practice_id"), "user", ["practice_id"])
    op.create_index(op.f("ix_user_provider_id"), "user", ["provider_id"])
    op.create_foreign_key(
        op.f("fk_user_deleted_by_user_id_practice_id"),
        "user",
        "user",
        ["deleted_by_user_id", "practice_id"],
        ["id", "practice_id"],
        ondelete="RESTRICT",
    )

    op.drop_constraint("fk_practice_membership_deleted_by_user_id_practice_id", "practice_membership", type_="foreignkey")
    _repoint(_user_references("practice_membership"), '"user" (id, practice_id)')
    op.drop_table("practice_membership")
