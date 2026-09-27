"""A value's history (#51): its Verifications, newest first, with who (name and Job Title then), what they did,
when and why. The ✓ Verified icon shows the latest on hover and the whole history on click."""

from tests.api.conftest import SignIn
from tests.api.test_cancer_diagnoses import new_patient
from tests.db.seed import Seed


def test_a_values_history_newest_first_with_who_and_why(sign_in: SignIn, committed: Seed) -> None:
    client, ids = sign_in()
    patient = new_patient(client)
    condition = client.post(f"/patients/{patient}/conditions", json={"name": "Type 2 diabetes"}).json()
    coordinator, _ = sign_in("trial_coordinator", practice=ids["practice"], display_name="Sam Lee")
    coordinator.patch(f"/patients/{patient}/conditions/{condition['id']}", json={"notes": "On metformin", "reason": "From the GP letter"})
    history = client.get(f"/verifications/condition/{condition['id']}").json()
    assert [(h["action"], h["job_title"], h["reason"]) for h in history] == [
        ("edit", "trial_coordinator", "From the GP letter"), ("edit", "clinician", None),
    ]
    assert history[0]["by"] == "Sam Lee" and history[0]["before"] == {"notes": None}


def test_only_this_practices_history_and_never_for_the_developer_admin(sign_in: SignIn, committed: Seed) -> None:
    client, ids = sign_in()
    patient = new_patient(client)
    condition = client.post(f"/patients/{patient}/conditions", json={"name": "Asthma"}).json()
    elsewhere, _ = sign_in()
    assert elsewhere.get(f"/verifications/condition/{condition['id']}").json() == []
    admin, _ = sign_in("developer_admin", practice=ids["practice"])
    assert admin.get(f"/verifications/condition/{condition['id']}").status_code == 403
