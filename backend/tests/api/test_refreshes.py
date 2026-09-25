"""Starting a Refresh (#18, design doc §6.4): developer admins only; everyone can follow a Job's progress."""

import uuid

import pytest

from tests.api.conftest import SignIn
from tests.db.seed import Seed


def test_a_developer_admin_starts_a_refresh_and_follows_the_job(sign_in: SignIn) -> None:
    client, _ = sign_in("developer_admin")
    started = client.post("/refreshes", json={"kind": "refresh_pbs"})
    assert started.status_code == 201
    job = started.json()
    assert (job["kind"], job["status"], job["attempts"], job["steps"]) == ("refresh_pbs", "queued", 0, [])

    followed = client.get(f"/jobs/{job['id']}")
    assert followed.status_code == 200 and followed.json()["id"] == job["id"]
    refreshes = {r["kind"]: r for r in client.get("/refreshes").json()}
    assert refreshes["refresh_pbs"]["description"].startswith("Refresh the PBS Schedule")
    assert refreshes["refresh_pbs"]["last_job"]["id"] == job["id"]


@pytest.mark.parametrize("job_title", ["clinician", "trial_coordinator", "secretary"])
def test_only_developer_admins_start_a_refresh(sign_in: SignIn, job_title: str) -> None:
    client, _ = sign_in(job_title)
    assert client.post("/refreshes", json={"kind": "refresh_pbs"}).status_code == 403
    assert "refresh_pbs" in {r["kind"] for r in client.get("/refreshes").json()}


def test_only_refresh_job_kinds_can_be_started(sign_in: SignIn, committed: Seed) -> None:
    client, _ = sign_in("developer_admin")
    other = f"test_not_refresh_{uuid.uuid4().hex[:8]}"
    committed.insert("job_kind", key=other, description="Not a Refresh")
    for kind in (other, "no_such_kind"):
        refused = client.post("/refreshes", json={"kind": kind})
        assert refused.status_code == 422
        assert refused.json()["detail"] == f"{kind} isn't a Refresh."


def test_another_practices_jobs_are_invisible(sign_in: SignIn, committed: Seed) -> None:
    client, _ = sign_in("clinician")
    kind = f"test_practice_job_{uuid.uuid4().hex[:8]}"
    committed.insert("job_kind", key=kind, description="Test")
    theirs = committed.insert("job", kind=kind, practice_id=committed.practice())
    assert client.get(f"/jobs/{theirs}").status_code == 404
    assert client.get(f"/jobs/{uuid.uuid4()}").status_code == 404
