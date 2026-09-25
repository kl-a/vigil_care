"""Practice scoping, database roles, tables that never change, and soft delete (design doc §6.2)."""

from collections.abc import Callable
from typing import Any

import pytest
from psycopg.errors import (
    CheckViolation,
    ForeignKeyViolation,
    InsufficientPrivilege,
    RestrictViolation,
)
from sqlalchemy import select, update

from app.core.database import INCLUDE_DELETED, session_factory
from app.db.provision import APP_ROLE, DatabaseSettings
from app.modules.patients.models import Patient
from tests.db.conftest import Rejects, rejects_on
from tests.db.seed import Seed

# --- Practice scoping ------------------------------------------------------------------------


def test_a_row_cant_point_at_another_practices_patient(seed: Seed, rejects: Rejects) -> None:
    ours = seed.everyone()
    theirs = seed.everyone()
    with rejects(ForeignKeyViolation):
        seed.insert("condition", practice_id=ours["practice"], patient_id=theirs["patient"], name="x", entered_by_user_id=ours["user"])


def test_a_verification_cant_be_signed_by_another_practices_user(seed: Seed, rejects: Rejects) -> None:
    ours = seed.everyone()
    theirs = seed.everyone()
    with rejects(ForeignKeyViolation):
        seed.verification({**ours, "user": theirs["user"]})


def test_only_a_member_can_act_in_a_practice(seed: Seed, rejects: Rejects) -> None:
    ours = seed.everyone()
    outsider = seed.user(seed.practice())
    with rejects(ForeignKeyViolation):
        seed.insert("condition", practice_id=ours["practice"], patient_id=ours["patient"], name="x", entered_by_user_id=outsider)
    seed.member(ours["practice"], outsider, job_title="clinician")
    seed.insert("condition", practice_id=ours["practice"], patient_id=ours["patient"], name="x", entered_by_user_id=outsider)


def test_a_membership_cant_link_another_practices_provider(seed: Seed, rejects: Rejects) -> None:
    ours, theirs = seed.practice(), seed.practice()
    with rejects(ForeignKeyViolation):
        seed.user(ours, provider_id=seed.provider(theirs))
    seed.user(ours, provider_id=seed.provider(ours))


def test_patient_identity_belongs_to_its_patients_practice(seed: Seed, rejects: Rejects) -> None:
    ours = seed.everyone()
    theirs = seed.everyone()
    with rejects(ForeignKeyViolation):
        seed.insert("identity.patient_identity", practice_id=ours["practice"], patient_id=theirs["patient"], given_name="J", family_name="C")


def test_removing_a_provider_clears_the_reference_but_keeps_the_practice(owner_seed: Seed, owner_db: Any) -> None:
    ids = owner_seed.everyone()
    provider = owner_seed.provider(ids["practice"])
    plan = owner_seed.insert(
        "management_plan", practice_id=ids["practice"], patient_id=ids["patient"], plan_text="Continue.", authored_by_provider_id=provider, entered_by_user_id=ids["user"]
    )
    owner_db.execute("DELETE FROM provider WHERE id = %s", [provider])
    row = owner_db.execute("SELECT authored_by_provider_id, practice_id FROM management_plan WHERE id = %s", [plan]).fetchone()
    assert row == {"authored_by_provider_id": None, "practice_id": ids["practice"]}


# --- Roles and grants ------------------------------------------------------------------------


def test_the_app_reads_and_writes_patient_identity(seed: Seed, app_db: Any) -> None:
    ids = seed.everyone()
    seed.insert("identity.patient_identity", practice_id=ids["practice"], patient_id=ids["patient"], given_name="Jane", family_name="Citizen")
    row = app_db.execute("SELECT given_name FROM identity.patient_identity WHERE patient_id = %s", [ids["patient"]]).fetchone()
    assert row == {"given_name": "Jane"}


def test_a_role_without_identity_access_cant_read_patient_identity(support_db: Any) -> None:
    with rejects_on(support_db)(InsufficientPrivilege):
        support_db.execute("SELECT * FROM identity.patient_identity")


def test_public_has_no_access_to_the_identity_schema(owner_db: Any) -> None:
    grants = owner_db.execute(
        "SELECT has_schema_privilege('public', 'identity', 'USAGE') AS usage"
    ).fetchone()
    assert grants == {"usage": False}


@pytest.mark.parametrize("table", ["patient", "condition", "document", "verification", "identity.patient_identity"])
def test_the_app_cant_hard_delete_patient_data(app_db: Any, table: str) -> None:
    with rejects_on(app_db)(InsufficientPrivilege):
        app_db.execute(f"DELETE FROM {table}")


def test_the_app_may_hard_delete_only_caches_and_the_job_queue(owner_db: Any) -> None:
    rows = owner_db.execute(
        "SELECT table_name FROM information_schema.role_table_grants"
        " WHERE grantee = %s AND privilege_type = 'DELETE' ORDER BY table_name",
        [APP_ROLE],
    ).fetchall()
    assert [r["table_name"] for r in rows] == ["job", "job_step", "llm_cache"]


@pytest.mark.parametrize("table", ["patient", "condition", "document", "extracted_fact", "user", "practice_membership", "cancer_diagnosis"])
def test_support_tooling_cant_read_patient_data(support_db: Any, table: str) -> None:
    with rejects_on(support_db)(InsufficientPrivilege):
        support_db.execute(f'SELECT * FROM "{table}"')


@pytest.mark.parametrize("table", ["job", "pipeline_run", "cloud_request", "pbs_refresh_log", "eviq_refresh_log", "practice_module"])
def test_support_tooling_reads_support_data(support_db: Any, table: str) -> None:
    support_db.execute(f"SELECT count(*) FROM {table}")


def test_support_tooling_cant_change_support_data(support_db: Any) -> None:
    with rejects_on(support_db)(InsufficientPrivilege):
        support_db.execute("UPDATE job SET status = 'cancelled'")


# --- Tables that never change -----------------------------------------------------------------

IMMUTABLE: dict[str, Callable[[Seed, dict[str, Any]], Any]] = {
    "verification": lambda s, ids: s.verification(ids),
    "medication_change_log": lambda s, ids: s.medication_change_log(ids),
    "llm_call_log": lambda s, ids: s.llm_call_log(ids),
    "match_run": lambda s, ids: s.match_run(ids),
    "match_result": lambda s, ids: s.match_result(ids),
    "criterion_evaluation": lambda s, ids: s.criterion_evaluation(ids),
    "trial_snapshot": lambda s, ids: s.trial_snapshot(),
}


@pytest.mark.parametrize("table", IMMUTABLE)
def test_rows_never_change_once_written(owner_seed: Seed, owner_db: Any, table: str) -> None:
    ids = owner_seed.everyone()
    row = IMMUTABLE[table](owner_seed, ids)
    rejects = rejects_on(owner_db)
    with rejects(RestrictViolation):
        owner_db.execute(f"UPDATE {table} SET deleted_at = now(), deleted_by_user_id = %s, deleted_reason = 'x' WHERE id = %s", [ids["user"], row])
    with rejects(RestrictViolation):
        owner_db.execute(f"DELETE FROM {table} WHERE id = %s", [row])
    with rejects(RestrictViolation):
        owner_db.execute(f"TRUNCATE {table} CASCADE")


def test_the_cloud_ledger_records_only_the_reply(owner_seed: Seed, owner_db: Any) -> None:
    ids = owner_seed.everyone()
    request = owner_seed.cloud_request(ids)
    owner_db.execute("UPDATE cloud_request SET status = 'sent', sent_at = now() WHERE id = %s", [request])
    owner_db.execute("UPDATE cloud_request SET status = 'received', response_received_at = now() WHERE id = %s", [request])
    rejects = rejects_on(owner_db)
    with rejects(RestrictViolation):
        owner_db.execute("UPDATE cloud_request SET payload_sha256 = 'tampered' WHERE id = %s", [request])
    with rejects(RestrictViolation):
        owner_db.execute("DELETE FROM cloud_request WHERE id = %s", [request])


# --- Timestamps and soft delete ---------------------------------------------------------------


def test_updated_at_moves_on_every_update(seed: Seed, app_db: Any) -> None:
    ids = seed.everyone()
    app_db.execute("UPDATE patient SET updated_at = '2000-01-01' WHERE id = %s", [ids["patient"]])
    row = app_db.execute("SELECT updated_at > '2000-01-02' AS moved FROM patient WHERE id = %s", [ids["patient"]]).fetchone()
    assert row == {"moved": True}


def test_a_soft_delete_needs_who_and_why(seed: Seed, rejects: Rejects, app_db: Any) -> None:
    ids = seed.everyone()
    with rejects(CheckViolation):
        app_db.execute("UPDATE patient SET deleted_at = now() WHERE id = %s", [ids["patient"]])
    with rejects(CheckViolation):
        app_db.execute("UPDATE patient SET deleted_at = now(), deleted_by_user_id = %s, deleted_reason = '  ' WHERE id = %s", [ids["user"], ids["patient"]])
    app_db.execute(
        "UPDATE patient SET deleted_at = now(), deleted_by_user_id = %s, deleted_reason = 'Duplicate record' WHERE id = %s",
        [ids["user"], ids["patient"]],
    )


def test_default_queries_exclude_soft_deleted_rows(database: DatabaseSettings) -> None:
    make_session = session_factory(database.role_url(APP_ROLE))
    with make_session() as session:
        seed_conn = session.connection().connection.driver_connection
        assert seed_conn is not None
        seed = Seed(seed_conn)
        ids = seed.everyone()
        kept = seed.patient(ids["practice"])
        session.execute(
            update(Patient)
            .where(Patient.id == ids["patient"])
            .values(deleted_at=Patient.created_at, deleted_by_user_id=ids["user"], deleted_reason="Duplicate record")
        )
        in_practice = select(Patient.id).where(Patient.practice_id == ids["practice"])

        assert set(session.scalars(in_practice)) == {kept}
        assert set(session.scalars(in_practice.execution_options(**{INCLUDE_DELETED: True}))) == {kept, ids["patient"]}
        session.rollback()
