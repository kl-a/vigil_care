"""Support Views (#10, design doc §6.4): Jobs, the queue, pipeline runs and Refresh history, for every Job Title.
IDs, Job Kinds, states, counts and timings only; system-wide rows plus the actor's own Practice's.
"""

import uuid
from collections.abc import Callable

import pytest
from fastapi.testclient import TestClient

from tests.api.conftest import SignIn
from tests.db.seed import Seed

JOB_TITLES = ["clinician", "trial_coordinator", "secretary", "developer_admin"]
SUPPORT_LISTS = ["/jobs", "/queue", "/refreshes", "/refreshes/history", "/pipeline-runs"]


def job_kind(committed: Seed) -> str:
    key = f"test_support_{uuid.uuid4().hex[:8]}"
    committed.insert("job_kind", key=key, description="Test Job Kind")
    return key


@pytest.mark.parametrize("job_title", JOB_TITLES)
def test_every_job_title_reads_the_support_views(sign_in: SignIn, job_title: str) -> None:
    client, _ = sign_in(job_title)
    for path in SUPPORT_LISTS:
        assert client.get(path).status_code == 200, path


def test_signed_out_users_get_nothing(api: Callable[..., TestClient]) -> None:
    client = api()
    for path in SUPPORT_LISTS:
        assert client.get(path).status_code == 401, path


def test_jobs_are_system_wide_and_this_practices_own(sign_in: SignIn, committed: Seed) -> None:
    client, ids = sign_in("developer_admin")
    kind = job_kind(committed)
    document = str(uuid.uuid4())
    system = committed.insert("job", kind=kind)
    ours = committed.insert("job", kind=kind, practice_id=ids["practice"], payload={"document_id": document})
    committed.insert("job", kind=kind, practice_id=committed.practice())

    jobs = client.get("/jobs", params={"kind": kind}).json()
    assert {job["id"] for job in jobs} == {str(system), str(ours)}
    mine = next(job for job in jobs if job["id"] == str(ours))
    assert (mine["kind"], mine["status"], mine["system_wide"], mine["payload"]) == (kind, "queued", False, {"document_id": document})
    assert next(job for job in jobs if job["id"] == str(system))["system_wide"] is True


def test_a_jobs_steps_show_their_outputs(sign_in: SignIn, committed: Seed) -> None:
    client, ids = sign_in("clinician")
    kind = job_kind(committed)
    job = committed.insert("job", kind=kind, practice_id=ids["practice"], status="running", attempts=1)
    committed.insert("job_step", job_id=job, sequence=0, name="fetch", status="succeeded", output={"item_count": 12})
    [shown] = client.get("/jobs", params={"kind": kind}).json()
    assert [(s["name"], s["status"], s["output"]) for s in shown["steps"]] == [("fetch", "succeeded", {"item_count": 12})]


def test_the_queues_depth_counts_this_practices_jobs_and_system_wide_ones(sign_in: SignIn, committed: Seed) -> None:
    client, ids = sign_in("secretary")
    kind = job_kind(committed)
    before = client.get("/queue").json()
    committed.insert("job", kind=kind, practice_id=ids["practice"])
    committed.insert("job", kind=kind)
    committed.insert("job", kind=kind, practice_id=committed.practice())
    committed.insert("job", kind=kind, status="running", attempts=1)
    after = client.get("/queue").json()
    assert after["queued"] - before["queued"] == 2
    assert after["running"] - before["running"] == 1
    assert set(after) == {"queued", "running", "failed_last_day"}


def test_refresh_history_lists_refresh_jobs_newest_first(sign_in: SignIn) -> None:
    client, _ = sign_in("developer_admin")
    first = client.post("/refreshes", json={"kind": "refresh_pbs"}).json()
    second = client.post("/refreshes", json={"kind": "refresh_pbs"}).json()
    history = client.get("/refreshes/history").json()
    assert all(job["kind"].startswith("refresh_") for job in history)
    ids = [job["id"] for job in history]
    assert ids.index(second["id"]) < ids.index(first["id"])


def test_pipeline_runs_are_system_wide_and_this_practices_own(sign_in: SignIn, committed: Seed) -> None:
    client, ids = sign_in("trial_coordinator")
    document = str(uuid.uuid4())
    ours = committed.insert(
        "pipeline_run", practice_id=ids["practice"], kind="ocr", status="failed", inputs={"document_id": document, "pages": [1, 2]},
        started_at="2026-09-01T10:00:00Z", finished_at="2026-09-01T10:00:42Z", error_detail="vlm_timeout",
    )
    system = committed.insert("pipeline_run", kind="pbs_refresh", status="succeeded")
    theirs = committed.insert("pipeline_run", practice_id=committed.practice(), kind="ocr")

    listed = {run["id"] for run in client.get("/pipeline-runs").json()}
    assert {str(ours), str(system)} <= listed and str(theirs) not in listed
    run = client.get(f"/pipeline-runs/{ours}").json()
    assert (run["kind"], run["status"], run["inputs"], run["error_detail"], run["system_wide"]) == (
        "ocr", "failed", {"document_id": document, "pages": [1, 2]}, "vlm_timeout", False,
    )
    assert (run["started_at"], run["finished_at"]) == ("2026-09-01T10:00:00Z", "2026-09-01T10:00:42Z")
    assert client.get(f"/pipeline-runs/{theirs}").status_code == 404
    assert client.get(f"/pipeline-runs/{uuid.uuid4()}").status_code == 404


def test_anything_in_a_pipeline_run_that_isnt_ids_only_is_withheld(sign_in: SignIn, committed: Seed) -> None:
    """Belt and braces: whatever wrote the run, the Support Views show only IDs, counts, flags, dates and codes."""
    client, ids = sign_in("developer_admin")
    run = committed.insert(
        "pipeline_run", practice_id=ids["practice"], kind="extract", status="failed",
        inputs={"document_id": str(uuid.uuid4()), "patient_name": "Jane Citizen", "Jane Citizen": 1},
        versions={"prompt": "extraction-v3"}, error_detail="Could not read Jane Citizen's letter",
    )
    shown = client.get(f"/pipeline-runs/{run}").json()
    assert "Jane" not in str(shown)
    assert shown["inputs"]["patient_name"] == "withheld" and shown["error_detail"] == "withheld"
    assert shown["versions"] == {"prompt": "extraction-v3"}
