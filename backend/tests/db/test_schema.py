"""The migrated database matches the models and the §6.2 conventions, table by table."""

from typing import Any

import pytest
from alembic.autogenerate import compare_metadata
from alembic.migration import MigrationContext
from sqlalchemy import CheckConstraint, ForeignKeyConstraint, Table, create_engine

from app.core.base_model import Entity, PracticeEntity, SharedEntity, SupportEntity
from app.db.metadata import metadata
from app.db.provision import OWNER_ROLE, DatabaseSettings
from app.specialties.oncology import models as oncology_models

RETIRED_TABLES = {
    "therapy_line",
    "molecular_result",
    "lesion",
    "lesion_measurement",
    "observation",
    "patient_provider",
    "diagnosis",
    "comorbidity",
}
TABLES = list(metadata.tables.values())
ONCOLOGY_TABLES = {
    m.__table__.name
    for m in vars(oncology_models).values()
    if isinstance(m, type) and issubclass(m, Entity) and m.__module__ == oncology_models.__name__
}
MODELS = {mapper.class_.__table__.name: mapper.class_ for mapper in Entity.registry.mappers}


def test_the_migrated_database_matches_the_models(database: DatabaseSettings) -> None:
    """Drift test: fails if a model and the migrations disagree (columns, types, keys, indexes)."""
    engine = create_engine(database.role_url(OWNER_ROLE, driver="postgresql+psycopg"))
    with engine.connect() as conn:
        context = MigrationContext.configure(
            conn,
            opts={
                "include_schemas": True,
                "include_name": lambda name, type_, _: name in (None, "public", "identity") if type_ == "schema" else True,
            },
        )
        diff = [d for d in compare_metadata(context, metadata) if not _is_alembic_version(d)]
    assert diff == []


def _is_alembic_version(diff: Any) -> bool:
    return diff[0] == "remove_table" and diff[1].name == "alembic_version"


def test_every_check_constraint_in_the_models_is_in_the_database(owner_db: Any) -> None:
    rows = owner_db.execute(
        "SELECT conname, pg_get_constraintdef(oid) AS definition FROM pg_constraint WHERE contype = 'c'"
    ).fetchall()
    in_db = {r["conname"]: r["definition"] for r in rows}
    for table in TABLES:
        for check in (c for c in table.constraints if isinstance(c, CheckConstraint)):
            assert check.name in in_db, f"{table.name}: {check.name} missing"
        for column in table.columns:
            for value in column.info.get("allowed", ()):
                assert f"'{value}'" in in_db[f"ck_{table.name}_{column.name}_allowed"]


def test_no_retired_v11_table_exists(owner_db: Any) -> None:
    rows = owner_db.execute("SELECT table_name FROM information_schema.tables WHERE table_schema IN ('public', 'identity')").fetchall()
    assert RETIRED_TABLES.isdisjoint({r["table_name"] for r in rows})


def test_patient_identity_is_in_its_own_schema() -> None:
    assert "identity.patient_identity" in metadata.tables
    assert all(t.schema is None for t in TABLES if t.name != "patient_identity")


@pytest.mark.parametrize("table", TABLES, ids=lambda t: t.name)
def test_every_table_has_the_standard_columns(table: Table) -> None:
    for column in ("id", "created_at", "updated_at", "deleted_at", "deleted_by_user_id", "deleted_reason"):
        assert column in table.columns
    assert str(table.columns["id"].server_default.arg) == "gen_random_uuid()"  # type: ignore[union-attr]


def test_every_table_updates_updated_at_by_trigger(owner_db: Any) -> None:
    rows = owner_db.execute(
        "SELECT event_object_schema AS schema, event_object_table AS name FROM information_schema.triggers"
        " WHERE trigger_name = 'set_updated_at' AND event_manipulation = 'UPDATE'"
    ).fetchall()
    with_trigger = {f"{r['schema']}.{r['name']}" if r["schema"] != "public" else r["name"] for r in rows}
    assert with_trigger == set(metadata.tables)


def test_immutable_tables_match_the_models(owner_db: Any) -> None:
    rows = owner_db.execute(
        "SELECT DISTINCT event_object_table AS name FROM information_schema.triggers WHERE trigger_name = 'reject_change'"
    ).fetchall()
    assert {r["name"] for r in rows} == {t.name for t in TABLES if t.info.get("immutable")}


@pytest.mark.parametrize("table", TABLES, ids=lambda t: t.name)
def test_every_foreign_key_is_indexed(table: Table) -> None:
    leading = {idx.columns[0].name for idx in table.indexes if idx.columns}
    leading |= {c.columns[0].name for c in table.constraints if hasattr(c, "columns") and c.columns and not isinstance(c, ForeignKeyConstraint)}
    for fk in table.foreign_key_constraints:
        assert fk.column_keys[0] in leading, f"{table.name}.{fk.column_keys[0]} has no index"


@pytest.mark.parametrize("table", TABLES, ids=lambda t: t.name)
def test_every_foreign_key_has_explicit_on_delete(table: Table) -> None:
    for fk in table.foreign_key_constraints:
        assert fk.ondelete, f"{table.name}.{fk.column_keys} has no ON DELETE"


def test_core_tables_never_reference_oncology_tables() -> None:
    for table in TABLES:
        if table.name in ONCOLOGY_TABLES:
            continue
        for fk in table.foreign_key_constraints:
            assert fk.referred_table.name not in ONCOLOGY_TABLES, f"Core {table.name} references {fk.referred_table.name}"


def test_every_table_is_in_exactly_one_practice_scoping_group() -> None:
    groups = (PracticeEntity, SupportEntity, SharedEntity)
    for name, model in MODELS.items():
        assert sum(issubclass(model, g) for g in groups) == 1, name


@pytest.mark.parametrize("name", [n for n, m in MODELS.items() if issubclass(m, PracticeEntity)])
def test_practice_data_is_scoped_and_references_are_composite(name: str) -> None:
    table = MODELS[name].__table__
    assert isinstance(table, Table)
    assert table.columns["practice_id"].nullable is False
    for fk in table.foreign_key_constraints:
        parent = MODELS.get(fk.referred_table.name)
        if parent is not None and issubclass(parent, PracticeEntity) and fk.column_keys != ["practice_id"]:
            assert fk.column_keys[-1] == "practice_id", f"{name}.{fk.column_keys} isn't composite"
