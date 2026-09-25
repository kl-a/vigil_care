"""The code registry and the database registry agree (design doc §4.1: migrations register modules)."""

from typing import Any

from app.jobs import registry
from app.modules.registry.registry import installed_modules


def test_every_installed_module_is_registered_by_a_migration_and_vice_versa(owner_db: Any) -> None:
    rows = owner_db.execute("SELECT key, display_name, version FROM specialty_module").fetchall()
    assert {r["key"]: (r["display_name"], r["version"]) for r in rows} == {
        m.key: (m.display_name, m.version) for m in installed_modules().values()
    }


def test_each_modules_verification_rows_cover_its_registered_fact_kinds(owner_db: Any) -> None:
    for module in installed_modules().values():
        rows = owner_db.execute("SELECT key FROM fact_kind WHERE module_key = %s", [module.key]).fetchall()
        assert {r["key"] for r in rows} <= set(module.verification_rights)


def test_a_registered_handler_needs_its_job_kind_registered_by_a_migration(owner_db: Any) -> None:
    registered = {r["key"] for r in owner_db.execute("SELECT key FROM job_kind").fetchall()}
    assert set(registry().kinds) <= registered
    assert "refresh_pbs" in registered
