"""Base model for every table (design doc §6.2).

Every table gets a UUID `id`, `created_at`/`updated_at` and the soft-delete columns. Each table then
belongs to exactly one Practice-scoping group:

- `PracticeEntity`: Practice data. Non-null `practice_id`, and every FK to another Practice-data
  table is composite `(parent_id, practice_id)`, so a row can never point at another Practice's row.
- `SupportEntity`: Support data (Jobs, pipeline runs, model call logs). Nullable `practice_id`;
  null means system-wide (e.g. a Refresh). IDs only, never Patient data.
- `SharedEntity`: Shared reference data (registries, PBS, trials). No `practice_id`.

Enum-like columns declare their allowed values with `allowed(...)`; a CHECK constraint is added
automatically, so the database rejects anything else.
"""

import uuid
from collections.abc import Iterable
from datetime import datetime
from decimal import Decimal
from typing import Any, Literal

from sqlalchemy import (
    CheckConstraint,
    Column,
    DateTime,
    Numeric,
    ForeignKey,
    ForeignKeyConstraint,
    MetaData,
    Table,
    Text,
    UniqueConstraint,
    event,
    func,
    text,
)
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.dialects.postgresql import UUID as PG_UUID
from sqlalchemy.orm import DeclarativeBase, Mapped, declared_attr, mapped_column

NAMING_CONVENTION = {
    "ix": "ix_%(table_name)s_%(column_0_N_name)s",
    "uq": "uq_%(table_name)s_%(column_0_N_name)s",
    "ck": "ck_%(table_name)s_%(constraint_name)s",
    "fk": "fk_%(table_name)s_%(column_0_N_name)s",
    "pk": "pk_%(table_name)s",
}

IDENTITY_SCHEMA = "identity"


class Base(DeclarativeBase):
    metadata = MetaData(naming_convention=NAMING_CONVENTION)
    type_annotation_map = {
        str: Text(),
        Decimal: Numeric(),
        uuid.UUID: PG_UUID(as_uuid=True),
        datetime: DateTime(timezone=True),
        dict[str, Any]: JSONB,
        list[Any]: JSONB,
    }


def allowed(*values: str) -> dict[str, Any]:
    """Column `info` declaring the column's allowed values; becomes a CHECK constraint."""
    return {"allowed": tuple(values)}


def sql_list(values: Iterable[str]) -> str:
    return ", ".join("'" + v.replace("'", "''") + "'" for v in values)


@event.listens_for(Column, "after_parent_attach")
def _check_allowed_values(column: Column[Any], table: Table) -> None:
    values = column.info.get("allowed")
    # Only on the models' own metadata: tooling that copies tables (e.g. Alembic) copies the CHECK too.
    if values and isinstance(table, Table) and table.metadata is Base.metadata:
        table.append_constraint(
            CheckConstraint(f"{column.name} IN ({sql_list(values)})", name=f"{column.name}_allowed")
        )


OnDelete = Literal["RESTRICT", "CASCADE", "SET NULL"]


def practice_fk(column: str, parent: str, ondelete: OnDelete = "RESTRICT") -> ForeignKeyConstraint:
    """Composite FK from a Practice-data table to another: the parent must be in the same Practice.

    `SET NULL` nulls only the referencing column, never `practice_id`.
    """
    action = f"SET NULL ({column})" if ondelete == "SET NULL" else ondelete
    return ForeignKeyConstraint(
        [column, "practice_id"], [f"{parent}.id", f"{parent}.practice_id"], ondelete=action
    )


def member_fk(column: str) -> ForeignKeyConstraint:
    """Composite FK from a Practice-data row to the User who acted: they must be a member of its Practice."""
    return ForeignKeyConstraint(
        [column, "practice_id"],
        ["practice_membership.user_id", "practice_membership.practice_id"],
        ondelete="RESTRICT",
    )


SOFT_DELETE_CHECK = (
    "(deleted_at IS NULL AND deleted_by_user_id IS NULL AND deleted_reason IS NULL)"
    " OR (deleted_at IS NOT NULL AND deleted_by_user_id IS NOT NULL"
    " AND length(btrim(deleted_reason)) > 0)"
)


class Entity(Base):
    """Columns and constraints every table has. Subclass one of the three scoping groups below."""

    __abstract__ = True
    # Model-specific constraints and indexes. Subclasses set this instead of __table_args__.
    __extra_args__: tuple[Any, ...] = ()
    # Tables that never change once written (design doc §6.2); a migration trigger enforces it.
    __immutable__: bool = False
    __schema__: str | None = None

    id: Mapped[uuid.UUID] = mapped_column(
        primary_key=True, server_default=text("gen_random_uuid()"), sort_order=-100
    )
    created_at: Mapped[datetime] = mapped_column(server_default=func.now(), sort_order=100)
    updated_at: Mapped[datetime] = mapped_column(server_default=func.now(), sort_order=101)
    deleted_at: Mapped[datetime | None] = mapped_column(sort_order=102)
    deleted_by_user_id: Mapped[uuid.UUID | None] = mapped_column(index=True, sort_order=103)
    deleted_reason: Mapped[str | None] = mapped_column(Text, sort_order=104)

    @classmethod
    def _scope_args(cls) -> tuple[Any, ...]:
        return (
            ForeignKeyConstraint(
                ["deleted_by_user_id"], ["user.id"], ondelete="RESTRICT", use_alter=True
            ),
        )

    @declared_attr.directive
    def __table_args__(cls) -> tuple[Any, ...]:
        options: dict[str, Any] = {"info": {"immutable": True}} if cls.__immutable__ else {}
        if cls.__schema__:
            options["schema"] = cls.__schema__
        return (
            CheckConstraint(SOFT_DELETE_CHECK, name="soft_delete"),
            *cls._scope_args(),
            *cls.__extra_args__,
            options,
        )


class SharedEntity(Entity):
    """Shared reference data: no Practice."""

    __abstract__ = True


class SupportEntity(Entity):
    """Support data: IDs only; `practice_id` is null for system-wide rows."""

    __abstract__ = True

    @classmethod
    def _scope_args(cls) -> tuple[Any, ...]:
        # A system-wide row (null practice_id) may be deleted by any User; a Practice's row only by a member.
        return (
            *super()._scope_args(),
            ForeignKeyConstraint(
                ["deleted_by_user_id", "practice_id"],
                ["practice_membership.user_id", "practice_membership.practice_id"],
                ondelete="RESTRICT",
                use_alter=True,
            ),
        )

    @declared_attr
    def practice_id(cls) -> Mapped[uuid.UUID | None]:
        return mapped_column(
            ForeignKey("practice.id", ondelete="RESTRICT"), index=True, sort_order=-90
        )


class PracticeEntity(Entity):
    """Practice data: non-null `practice_id`; FKs to other Practice data are composite."""

    __abstract__ = True

    @declared_attr
    def practice_id(cls) -> Mapped[uuid.UUID]:
        return mapped_column(
            ForeignKey("practice.id", ondelete="RESTRICT"), index=True, sort_order=-90
        )

    @classmethod
    def _scope_args(cls) -> tuple[Any, ...]:
        return (
            UniqueConstraint("id", "practice_id"),
            ForeignKeyConstraint(
                ["deleted_by_user_id", "practice_id"],
                ["practice_membership.user_id", "practice_membership.practice_id"],
                ondelete="RESTRICT",
                use_alter=True,
            ),
        )


class Provenance:
    """Provenance columns for Clinical Record tables (design doc §6.2).

    A row is either from an accepted Extracted Fact or entered directly by a User; never neither.
    Add `*provenance_args()` to the model's `__extra_args__`.
    """

    source_fact_id: Mapped[uuid.UUID | None] = mapped_column(index=True)
    source_document_id: Mapped[uuid.UUID | None] = mapped_column(index=True)
    entered_by_user_id: Mapped[uuid.UUID | None] = mapped_column(index=True)


def provenance_args() -> tuple[Any, ...]:
    return (
        practice_fk("source_fact_id", "extracted_fact"),
        practice_fk("source_document_id", "document"),
        member_fk("entered_by_user_id"),
        CheckConstraint(
            "source_fact_id IS NOT NULL OR entered_by_user_id IS NOT NULL", name="provenance"
        ),
    )
