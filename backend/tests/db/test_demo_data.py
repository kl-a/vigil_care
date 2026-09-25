"""`make demo-data` loads the synthetic demo Practice (dev only), and running it again changes nothing."""

from typing import Any

import psycopg
import pytest

from app.db import demo_data
from app.db.provision import APP_ROLE, DatabaseSettings
from tests.conftest import make_settings


def _counts(database: DatabaseSettings) -> dict[str, Any]:
    with psycopg.connect(database.role_url(APP_ROLE)) as conn:
        practice = demo_data.PRACTICE_ID
        return {
            "practices": conn.execute("SELECT count(*) FROM practice WHERE id = %s", [practice]).fetchone(),
            "job_titles": conn.execute('SELECT array_agg(job_title ORDER BY job_title) FROM "user" WHERE practice_id = %s', [practice]).fetchone(),
            "oncology": conn.execute("SELECT is_active FROM practice_module WHERE practice_id = %s AND module_key = 'oncology'", [practice]).fetchone(),
            "activations": conn.execute("SELECT count(*) FROM verification WHERE practice_id = %s AND action = 'activate_module'", [practice]).fetchone(),
        }


def test_demo_data_loads_the_practice_one_user_per_job_title_and_oncology(database: DatabaseSettings) -> None:
    settings = make_settings(environment="dev", database_url=database.role_url(APP_ROLE))
    demo_data.load(settings)
    counts = _counts(database)
    assert counts["practices"] == (1,)
    assert counts["job_titles"] == (["clinician", "developer_admin", "secretary", "trial_coordinator"],)
    assert counts["oncology"] == (True,)
    assert counts["activations"] == (1,)

    demo_data.load(settings)
    assert _counts(database) == counts


def test_demo_data_is_refused_outside_dev(database: DatabaseSettings) -> None:
    with pytest.raises(demo_data.DemoDataRefused):
        demo_data.load(make_settings(environment="test", database_url=database.role_url(APP_ROLE)))
