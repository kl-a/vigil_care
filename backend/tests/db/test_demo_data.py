"""`make demo-data` loads the synthetic demo Practice (dev only), and running it again changes nothing."""

from typing import Any

import psycopg
import pytest

from app.db import demo_data
from app.db.provision import APP_ROLE, DatabaseSettings
from tests.conftest import make_settings

MEMBERS = (
    'SELECT array_agg(u.display_name || \': \' || m.job_title ORDER BY u.display_name) FROM practice_membership m'
    ' JOIN "user" u ON u.id = m.user_id WHERE m.practice_id = %s'
)


def _counts(database: DatabaseSettings) -> dict[str, Any]:
    with psycopg.connect(database.role_url(APP_ROLE)) as conn:
        practice = demo_data.PRACTICE_ID
        return {
            "all_practices": conn.execute(
                "SELECT array_agg(name ORDER BY name) FROM practice WHERE id = ANY(%s)", [[practice, demo_data.NORTHSIDE_ID]]
            ).fetchone(),
            "northside_members": conn.execute(MEMBERS, [demo_data.NORTHSIDE_ID]).fetchone(),
            "practices": conn.execute("SELECT count(*) FROM practice WHERE id = %s", [practice]).fetchone(),
            "located": conn.execute("SELECT phone IS NOT NULL FROM practice WHERE id = %s", [practice]).fetchone(),
            "sites": conn.execute(
                "SELECT array_agg(name || CASE WHEN is_primary THEN ' (primary)' ELSE '' END ORDER BY name) FROM site"
                " WHERE practice_id = %s AND lat IS NOT NULL",
                [practice],
            ).fetchone(),
            "unmarked_names": conn.execute(
                "SELECT count(*) FROM \"user\" u JOIN practice_membership m ON m.user_id = u.id"
                " WHERE m.practice_id = ANY(%s) AND u.display_name NOT LIKE '%%(synthetic)'",
                [[practice, demo_data.NORTHSIDE_ID]],
            ).fetchone(),
            "job_titles": conn.execute(
                "SELECT array_agg(job_title ORDER BY job_title) FROM practice_membership WHERE practice_id = %s", [practice]
            ).fetchone(),
            "oncology": conn.execute("SELECT is_active FROM practice_module WHERE practice_id = %s AND module_key = 'oncology'", [practice]).fetchone(),
            "activations": conn.execute("SELECT count(*) FROM verification WHERE practice_id = %s AND action = 'activate_module'", [practice]).fetchone(),
        }


def test_demo_data_loads_two_practices_one_user_per_job_title_and_oncology(database: DatabaseSettings) -> None:
    settings = make_settings(environment="dev", database_url=database.role_url(APP_ROLE))
    demo_data.load(settings)
    counts = _counts(database)
    assert counts["practices"] == (1,)
    assert counts["all_practices"] == (["Harbourside Oncology (synthetic)", "Northside Oncology (synthetic)"],)
    # Dr Alex Rivera works at both: one login, a Membership at each.
    assert counts["northside_members"] == (["Dr Alex Rivera (synthetic): clinician"],)
    assert counts["located"] == (True,)
    assert counts["sites"] == (["Example Hospital clinic", "Harbourside rooms (primary)"],)
    assert counts["unmarked_names"] == (0,)
    assert counts["job_titles"] == (["clinician", "developer_admin", "secretary", "trial_coordinator"],)
    assert counts["oncology"] == (True,)
    assert counts["activations"] == (1,)

    demo_data.load(settings)
    assert _counts(database) == counts


def test_demo_data_is_refused_outside_dev(database: DatabaseSettings) -> None:
    with pytest.raises(demo_data.DemoDataRefused):
        demo_data.load(make_settings(environment="test", database_url=database.role_url(APP_ROLE)))
