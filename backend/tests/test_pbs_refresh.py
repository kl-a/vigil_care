"""The PBS Refresh (#19, design doc §10.2): fetches the current schedule from the PBS Schedule API (a recorded
fixture here, never the live service) into `pbs_item`, logs each attempt, keeps the previous schedule when a
Refresh fails, and falls back to the bundled sample when there's nothing else. Runs monthly on the 1st.
"""

import uuid
from collections.abc import Iterator
from datetime import UTC, date, datetime
from decimal import Decimal
from typing import Any

import psycopg
import pytest
from psycopg.rows import dict_row

from app.db.provision import APP_ROLE, DatabaseSettings
from app.jobs import registry
from tests.fixtures.pbs import PbsRefresher, RecordedPbsApi, clear_pbs


@pytest.fixture
def db(database: DatabaseSettings) -> Iterator[psycopg.Connection[dict[str, Any]]]:
    clear_pbs(database)
    with psycopg.connect(database.role_url(APP_ROLE), autocommit=True, row_factory=dict_row) as conn:
        yield conn


@pytest.fixture
def kind(db: psycopg.Connection[dict[str, Any]]) -> str:
    key = f"test_refresh_pbs_{uuid.uuid4().hex[:8]}"
    db.execute("INSERT INTO job_kind (key, description) VALUES (%s, 'Test PBS Refresh')", [key])
    return key


def refresher(database: DatabaseSettings, kind: str, down: tuple[str, ...] = ()) -> PbsRefresher:
    return PbsRefresher(database, kind, RecordedPbsApi(down=down))


def logs(db: psycopg.Connection[dict[str, Any]]) -> list[dict[str, Any]]:
    return db.execute("SELECT * FROM pbs_refresh_log ORDER BY refreshed_at").fetchall()


def items(db: psycopg.Connection[dict[str, Any]], log_id: Any) -> dict[str, dict[str, Any]]:
    rows = db.execute("SELECT * FROM pbs_item WHERE refresh_log_id = %s", [log_id]).fetchall()
    return {row["item_code"]: row for row in rows}


def test_a_refresh_stores_the_oncology_items_of_the_current_schedule(
    database: DatabaseSettings, db: psycopg.Connection[dict[str, Any]], kind: str
) -> None:
    job = refresher(database, kind).run()
    assert job.status == "succeeded"
    assert [step.name for step in job.steps] == ["fetch", "store"]

    [log] = logs(db)
    assert (log["status"], log["source"], log["schedule_date"], log["error_detail"]) == ("succeeded", "pbs_api", date(2026, 9, 1), None)
    assert (log["safety_net_general"], log["safety_net_concessional"]) == (Decimal("1748.2"), Decimal("277.2"))
    stored = items(db, log["id"])
    assert log["item_count"] == len(stored) == 18
    assert {row["drug_name"] for row in stored.values()} == {"Pembrolizumab", "Letrozole", "Carboplatin"}
    assert "10001J" not in stored  # rifaximin: not an oncology drug (ATC L01/L02)

    pembrolizumab = stored["12120X"]
    assert pembrolizumab["brand_names"] == ["Keytruda"]
    assert pembrolizumab["form"] == "pembrolizumab 100 mg/4 mL injection, 4 mL vial"
    assert pembrolizumab["restriction_level"] == "authority_required"
    assert (pembrolizumab["max_amount"], pembrolizumab["amount_unit"], pembrolizumab["repeats"]) == (Decimal("200"), "mg", 7)
    assert (pembrolizumab["patient_copay_general"], pembrolizumab["patient_copay_concessional"]) == (Decimal("25"), Decimal("7.7"))
    first = pembrolizumab["indications"][0]
    assert first["indication"] == "Stage IIIB, Stage IIIC or Stage IIID malignant melanoma"
    assert first["treatment_phase"] == "Initial treatment - 3 weekly treatment regimen"
    assert first["level"] == "authority_required"
    assert first["conditions"][0] == "The treatment must be in addition to complete surgical resection; AND"
    streamlined = stored["13739D"]["indications"][0]
    assert (streamlined["indication"], streamlined["level"]) == ("Stage II or Stage III triple negative breast cancer", "authority_required_streamlined")

    letrozole = next(row for row in stored.values() if row["drug_name"] == "Letrozole")
    assert letrozole["restriction_level"] == "restricted" and len(letrozole["brand_names"]) > 1
    carboplatin = next(row for row in stored.values() if row["drug_name"] == "Carboplatin")
    assert (carboplatin["restriction_level"], carboplatin["indications"]) == ("unrestricted", [])


def test_a_refresh_is_safe_to_run_again(database: DatabaseSettings, db: psycopg.Connection[dict[str, Any]], kind: str) -> None:
    runner = refresher(database, kind)
    runner.run()
    assert runner.run().status == "succeeded"
    first, second = logs(db)
    assert len(items(db, first["id"])) == 0  # every item moved to the newer Refresh
    assert len(items(db, second["id"])) == 18
    assert db.execute("SELECT count(*) AS n FROM pbs_item").fetchone() == {"n": 18}


def test_with_the_api_unreachable_and_no_schedule_the_bundled_sample_loads_marked_as_sample(
    database: DatabaseSettings, db: psycopg.Connection[dict[str, Any]], kind: str
) -> None:
    job = refresher(database, kind, down=("*",)).run()
    assert job.status == "succeeded"
    [log] = logs(db)
    assert (log["status"], log["source"], log["error_detail"]) == ("partial", "sample", "pbs_api_unreachable")
    stored = items(db, log["id"])
    assert log["item_count"] == len(stored) > 0
    pembrolizumab = [row for row in stored.values() if row["drug_name"] == "Pembrolizumab"]
    assert pembrolizumab and all(row["indications"] for row in pembrolizumab)


def test_a_failed_refresh_keeps_the_previous_schedule(
    database: DatabaseSettings, db: psycopg.Connection[dict[str, Any]], kind: str
) -> None:
    refresher(database, kind).run()
    job = refresher(database, kind, down=("*",)).run()
    assert (job.status, job.last_error) == ("queued", "pbs_api_unreachable")  # retried later

    loaded, failed = logs(db)
    assert (failed["status"], failed["source"], failed["error_detail"], failed["item_count"]) == ("failed", "pbs_api", "pbs_api_unreachable", None)
    assert len(items(db, loaded["id"])) == 18  # the sample didn't replace the real schedule


def test_a_refresh_that_fails_while_storing_logs_the_failure_with_its_schedule_date(
    database: DatabaseSettings, db: psycopg.Connection[dict[str, Any]], kind: str
) -> None:
    job = refresher(database, kind, down=("/items",)).run()
    assert (job.status, job.last_error) == ("queued", "pbs_api_unreachable")
    assert [(step.name, step.status) for step in job.steps][0] == ("fetch", "succeeded")
    [failed] = logs(db)
    assert (failed["status"], failed["schedule_date"]) == ("failed", date(2026, 9, 1))
    assert db.execute("SELECT count(*) AS n FROM pbs_item").fetchone() == {"n": 0}


def test_the_pbs_refresh_runs_monthly_on_the_first() -> None:
    jobs = registry()
    assert "refresh_pbs" in jobs.kinds
    [monthly] = [s for s in jobs.schedules if s.kind == "refresh_pbs"]
    assert monthly.due(datetime(2026, 9, 25, 10, tzinfo=UTC)) == datetime(2026, 9, 1, tzinfo=UTC)
