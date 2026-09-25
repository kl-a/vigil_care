"""No Patient data in support data (#10, design doc §6.4). Also a quality gate: `make gates` runs this file.

A synthetic Patient with a distinctive name and identifiers goes through the Patient flows (create, edit identity,
Care Team, remove), a Job about them fails with their name in the error, and a Refresh runs. Then every support
endpoint (every route tagged "support", so a new one is covered as soon as it's tagged) is read as a staff
member and as a developer admin, and none of those values may appear there or in the application logs.
"""

import logging
import uuid
from typing import Any

import pytest
from fastapi.testclient import TestClient

from app.core.database import session_factory
from app.core.seams.queue import NewJob
from app.db.provision import APP_ROLE, DatabaseSettings
from app.orchestrator.handlers import JobContext, JobHandler, JobRegistry
from app.orchestrator.queue import DbJobQueue
from app.orchestrator.router import SUPPORT
from app.orchestrator.worker import Worker
from tests.api.conftest import SignIn
from tests.conftest import make_settings
from tests.db.seed import Seed

# Obviously fake (frontend brief §10): Medicare numbers and IHIs starting with zeros are never issued, and
# 02 5550 / 0491 570 numbers are reserved for fiction.
ZEBEDEE = {
    "given_name": "Zebedee",
    "family_name": "Quux-Synthetic",
    "dob": "1931-07-19",
    "medicare_number": "0000 77777 1",
    "medicare_irn": "3",
    "ihi": "0000 0000 0077 7771",
    "mrn": "QX-7777771",
    "address": "7 Quuxwold Lane, Nowhere NSW 2999",
    "phone": "02 5550 0177",
    "mobile": "0491 570 177",
    "email": "zebedee.quux@example.com",
    "next_of_kin_name": "Ysolde Quux-Synthetic (sister)",
    "next_of_kin_phone": "0491 570 178",
}
EDITED = {"address": "9 Quuxwold Lane, Nowhere NSW 2999", "mobile": "0491 570 179"}
CARE_TEAM_NOTES = "Quuxwold family GP since 1990"
REMOVAL_REASON = "Duplicate of Zebedee Quux-Synthetic"

# Support routes the test can't simply GET, and how it exercises them instead.
EXERCISED_OTHERWISE = {("POST", "/refreshes")}


def patient_values(pseudonym: str) -> list[str]:
    """Every value that identifies the Patient, as they could appear in text."""
    values = [v for k, v in {**ZEBEDEE, **EDITED}.items() if k != "medicare_irn"]
    values += ["Zebedee", "Quux", "Quuxwold", "19/07/1931", "0000777771", CARE_TEAM_NOTES, REMOVAL_REASON, pseudonym]
    return values


def support_operations(client: TestClient) -> list[tuple[str, str, list[str]]]:
    """(method, path, path parameters) of every operation tagged "support", from the OpenAPI schema."""
    spec = client.app.openapi()  # type: ignore[attr-defined]
    return [
        (method.upper(), path, [p["name"] for p in operation.get("parameters", []) if p["in"] == "path"])
        for path, operations in spec["paths"].items()
        for method, operation in operations.items()
        if SUPPORT in operation.get("tags", [])
    ]


def leaks(text: str, values: list[str]) -> list[str]:
    return [value for value in values if value.lower() in text.lower()]


def test_no_patient_data_in_support_endpoints_or_logs(
    sign_in: SignIn, committed: Seed, database: DatabaseSettings, caplog: pytest.LogCaptureFixture
) -> None:
    caplog.set_level(logging.DEBUG)
    staff, ids = sign_in("secretary")
    admin, _ = sign_in("developer_admin", practice=ids["practice"])

    # --- The Patient flows, through the API ---------------------------------------------------------
    created = staff.post("/patients", json=ZEBEDEE)
    assert created.status_code == 201, created.text
    patient = created.json()
    patient_id, values = patient["id"], patient_values(patient["pseudonym"])
    assert staff.patch(f"/patients/{patient_id}/identity", json=EDITED).status_code == 200
    # The detector works: the Patient's own screen does show them.
    assert set(leaks(staff.get(f"/patients/{patient_id}").text, values)) >= {"Zebedee", EDITED["address"]}

    provider = committed.provider(ids["practice"], title="Dr", first_name="Alex", last_name="Rivera")
    member = staff.post(f"/patients/{patient_id}/care-team", json={"provider_id": str(provider), "role": "referring_gp"})
    assert member.status_code == 201, member.text
    changed = staff.patch(f"/patients/{patient_id}/care-team/{member.json()['id']}", json={"notes": CARE_TEAM_NOTES})
    assert changed.status_code == 200

    # --- Background work about the Patient, and a Refresh -------------------------------------------
    kind = f"test_patient_job_{uuid.uuid4().hex[:8]}"
    committed.insert("job_kind", key=kind, description="Test Job about a Patient")
    queue = DbJobQueue(session_factory(database.role_url(APP_ROLE)))
    patient_job = queue.enqueue(NewJob(kind=kind, practice_id=ids["practice"], payload={"patient_id": patient_id}, max_attempts=1))
    started = admin.post("/refreshes", json={"kind": "refresh_pbs"})
    assert started.status_code == 201

    def look_up(ctx: JobContext) -> dict[str, Any]:
        return {"patient_id": ctx.job.payload["patient_id"], "document_count": 0}

    def read_letter(ctx: JobContext) -> dict[str, Any]:
        raise ValueError(f"Could not read the letter for {ZEBEDEE['given_name']} {ZEBEDEE['family_name']}, {ZEBEDEE['medicare_number']}")

    registry = JobRegistry()
    registry.register(JobHandler(kind, steps=(("look_up", look_up), ("read_letter", read_letter))))
    # A stand-in for the PBS Refresh: this test is about what reaches support data, not about the PBS.
    registry.register(JobHandler("refresh_pbs", steps=(("fetch", lambda ctx: {"item_count": 3, "schedule_date": "2026-09-01"}),)))
    worker = Worker(queue, registry, make_settings(database_url=database.role_url(APP_ROLE)), worker_id="gate-worker")
    while worker.run_once():
        pass
    assert queue.status(patient_job).status == "failed"

    run = committed.insert(
        "pipeline_run", practice_id=ids["practice"], kind="ingest", status="failed",
        inputs={"patient_id": patient_id, "pages": [1]}, error_detail="Letter for Zebedee Quux-Synthetic unreadable",
    )

    assert staff.request("DELETE", f"/patients/{patient_id}", json={"reason": REMOVAL_REASON}).status_code == 204

    # --- Every support endpoint, as staff and as a developer admin ----------------------------------
    path_ids = {"job_id": [str(patient_job), started.json()["id"]], "run_id": [str(run)]}
    outputs = [started.text]
    covered = set()
    for method, route, params in support_operations(admin):
        covered.add((method, route))
        if (method, route) in EXERCISED_OTHERWISE:
            continue
        assert method == "GET", f"Say how the no-Patient-data test exercises {method} {route}"
        assert len(params) <= 1 and set(params) <= set(path_ids), f"Give the no-Patient-data test ids for {route}"
        paths = [route.format(**{params[0]: value}) for value in path_ids[params[0]]] if params else [route]
        for path in paths:
            for client in (staff, admin):
                response = client.get(path)
                assert response.status_code == 200, f"{path}: {response.status_code}"
                outputs.append(response.text)

    assert {("GET", "/jobs"), ("GET", "/pipeline-runs"), ("GET", "/health")} <= covered
    assert covered >= EXERCISED_OTHERWISE
    # The Job about the Patient did reach the Support Views, by id only.
    assert any(str(patient_job) in text and patient_id in text for text in outputs)

    assert leaks("\n".join(outputs), values) == [], "Patient data in a support endpoint's output"
    assert leaks(caplog.text, values) == [], "Patient data in the application logs"
