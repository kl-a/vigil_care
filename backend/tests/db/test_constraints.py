"""The database itself rejects invalid states (design doc §6.2): CHECKs, registries, uniques, Line of Therapy."""

import uuid
from typing import Any

import pytest
from psycopg.errors import CheckViolation, ForeignKeyViolation, NotNullViolation, UniqueViolation

from tests.db.conftest import Rejects
from tests.db.seed import Seed


def test_every_job_title_is_accepted_including_developer_admin(seed: Seed) -> None:
    practice = seed.practice()
    for job_title in ("clinician", "trial_coordinator", "secretary", "developer_admin"):
        seed.user(practice, job_title=job_title)


def test_an_unknown_job_title_is_rejected(seed: Seed, rejects: Rejects) -> None:
    practice = seed.practice()
    with rejects(CheckViolation):
        seed.user(practice, job_title="superuser")


def test_a_care_team_role_outside_the_list_is_rejected(seed: Seed, rejects: Rejects) -> None:
    ids = seed.everyone()
    provider = seed.provider(ids["practice"])
    care_team = dict(practice_id=ids["practice"], patient_id=ids["patient"], provider_id=provider)
    seed.insert("care_team_member", role="trial_site_contact", **care_team)
    with rejects(CheckViolation):
        # Retired in v1.2: trial coordinators are Users, not Care Team roles.
        seed.insert("care_team_member", role="trial_coordinator", **care_team)


def test_match_state_uses_the_three_states(seed: Seed, rejects: Rejects) -> None:
    ids = seed.everyone()
    run = seed.match_run(ids)
    for state in ("POTENTIALLY_ELIGIBLE", "NEEDS_INFORMATION", "EXCLUDED"):
        seed.insert("match_result", practice_id=ids["practice"], match_run_id=run, trial_id=seed.trial(), match_state=state)
    with rejects(CheckViolation):
        seed.insert("match_result", practice_id=ids["practice"], match_run_id=run, trial_id=seed.trial(), match_state="ELIGIBLE")


def test_criterion_result_is_met_not_met_or_unknown(seed: Seed, rejects: Rejects) -> None:
    ids = seed.everyone()
    result = seed.match_result(ids)
    criterion = seed.insert("trial_criterion", trial_id=seed.trial(), kind="exclusion", raw_text="x", scope="target_condition")
    row = dict(practice_id=ids["practice"], match_result_id=result, trial_criterion_id=criterion)
    seed.insert("criterion_evaluation", result="NOT_MET", **row)
    with rejects(CheckViolation):
        seed.insert("criterion_evaluation", result="FAIL", **row)


def cancer_diagnosis_row(seed: Seed, ids: dict[str, uuid.UUID]) -> dict[str, Any]:
    cancer_type = seed.insert("cancer_type", key=f"type-{uuid.uuid4().hex[:6]}", display_name="Synthetic cancer")
    return dict(
        practice_id=ids["practice"],
        condition_id=seed.condition(ids, extended_by_module="oncology"),
        cancer_type_id=cancer_type,
        entered_by_user_id=ids["user"],
    )


def test_disease_extent_is_one_of_the_listed_values(seed: Seed, rejects: Rejects) -> None:
    ids = seed.everyone()
    seed.insert("cancer_diagnosis", disease_extent="locally_advanced", **cancer_diagnosis_row(seed, ids))
    with rejects(CheckViolation):
        seed.insert("cancer_diagnosis", disease_extent="stage_iv", **cancer_diagnosis_row(seed, ids))


def test_recurrence_status_and_its_rules(seed: Seed, rejects: Rejects) -> None:
    ids = seed.everyone()
    diagnosis = seed.insert("cancer_diagnosis", **cancer_diagnosis_row(seed, ids))
    row = dict(practice_id=ids["practice"], cancer_diagnosis_id=diagnosis, entered_by_user_id=ids["user"])
    seed.insert("recurrence", status="suspected", **row)
    with rejects(CheckViolation):
        seed.insert("recurrence", status="relapsed", **row)
    with rejects(CheckViolation):
        # Confirmed means a clinician attributed it.
        seed.insert("recurrence", status="confirmed", **row)
    with rejects(CheckViolation):
        # Reclassified means it points at the new Cancer Diagnosis.
        seed.insert("recurrence", status="reclassified_as_new_primary", attributed_by_user_id=ids["user"], attributed_at="2026-09-01T00:00:00Z", **row)


def test_export_kind_must_be_chosen_explicitly(seed: Seed, rejects: Rejects) -> None:
    ids = seed.everyone()
    row = dict(
        practice_id=ids["practice"],
        patient_id=ids["patient"],
        recipient_description="Synthetic trial site",
        file_uri="file:///export.pdf",
        file_sha256="abc",
        signed_off_by_user_id=ids["user"],
        job_title_at_time="secretary",
        signed_off_at="2026-09-01T00:00:00Z",
    )
    seed.insert("export", kind="deidentified", **row)
    with rejects(CheckViolation):
        seed.insert("export", kind="anonymised", **row)
    with rejects(NotNullViolation):
        seed.insert("export", **row)


def test_verification_actions_include_module_activation(seed: Seed, rejects: Rejects) -> None:
    ids = seed.everyone()
    for action in ("accept", "delete", "hold", "activate_module", "deactivate_module"):
        seed.verification(ids, action=action)
    with rejects(CheckViolation):
        seed.verification(ids, action="approve")


def test_a_developer_admin_is_never_required_to_verify_a_fact(seed: Seed, rejects: Rejects) -> None:
    ids = seed.everyone()
    document = seed.document(ids)
    document_type = seed.insert("document_type", key="synthetic_letter", display_name="Letter", version="1")
    extraction = seed.insert("extraction", practice_id=ids["practice"], document_id=document, document_type_id=document_type, reader="text_layer")
    row = dict(
        practice_id=ids["practice"],
        extraction_id=extraction,
        patient_id=ids["patient"],
        fact_kind="lab_result",
        payload={},
        confidence=0.9,
        confidence_band="high",
    )
    seed.insert("extracted_fact", required_job_title="secretary", **row)
    with rejects(CheckViolation):
        seed.insert("extracted_fact", required_job_title="developer_admin", **row)


# --- Line of Therapy rule (constraint trigger across two tables) --------------------------


def test_line_of_therapy_is_allowed_on_a_systemic_palliative_course(seed: Seed, app_db: Any) -> None:
    ids = seed.everyone()
    course = seed.treatment_course(ids, modality="systemic", intent="palliative")
    seed.insert("oncology_course_detail", practice_id=ids["practice"], treatment_course_id=course, line_of_therapy=2, entered_by_user_id=ids["user"])
    app_db.execute("SET CONSTRAINTS ALL IMMEDIATE")


@pytest.mark.parametrize(
    ("modality", "intent"),
    [("systemic", "adjuvant"), ("systemic", "neoadjuvant"), ("systemic", "curative"), ("systemic", None), ("surgery", "palliative"), ("radiation", "palliative")],
)
def test_line_of_therapy_is_rejected_on_any_other_course(seed: Seed, rejects: Rejects, modality: str, intent: str | None) -> None:
    ids = seed.everyone()
    course = seed.treatment_course(ids, modality=modality, intent=intent)
    with rejects(CheckViolation):
        seed.insert("oncology_course_detail", practice_id=ids["practice"], treatment_course_id=course, line_of_therapy=1, entered_by_user_id=ids["user"])


def test_a_course_detail_without_a_line_is_fine_on_any_course(seed: Seed, app_db: Any) -> None:
    ids = seed.everyone()
    course = seed.treatment_course(ids, modality="surgery", intent="curative")
    seed.insert("oncology_course_detail", practice_id=ids["practice"], treatment_course_id=course, best_response="CR", entered_by_user_id=ids["user"])
    app_db.execute("SET CONSTRAINTS ALL IMMEDIATE")


def test_changing_a_numbered_course_to_adjuvant_is_rejected(seed: Seed, rejects: Rejects, app_db: Any) -> None:
    ids = seed.everyone()
    course = seed.treatment_course(ids)
    seed.insert("oncology_course_detail", practice_id=ids["practice"], treatment_course_id=course, line_of_therapy=1, entered_by_user_id=ids["user"])
    app_db.execute("SET CONSTRAINTS ALL IMMEDIATE")
    with rejects(CheckViolation):
        app_db.execute("UPDATE treatment_course SET intent = 'adjuvant' WHERE id = %s", [course])


# --- Registries ----------------------------------------------------------------------------


def test_the_oncology_module_and_fact_kinds_are_registered(app_db: Any) -> None:
    modules = app_db.execute("SELECT key FROM specialty_module").fetchall()
    assert [m["key"] for m in modules] == ["oncology"]
    kinds = {r["key"]: r["module_key"] for r in app_db.execute("SELECT key, module_key FROM fact_kind")}
    assert kinds["lab_result"] is None
    assert kinds["biomarker"] == "oncology"


def test_a_job_of_an_unknown_kind_is_rejected(seed: Seed, rejects: Rejects) -> None:
    seed.insert("job_kind", key="refresh_pbs", description="Refresh the PBS Schedule")
    seed.insert("job", kind="refresh_pbs")
    with rejects(ForeignKeyViolation):
        seed.insert("job", kind="mine_bitcoin")


def test_an_extracted_fact_of_an_unknown_kind_is_rejected(seed: Seed, rejects: Rejects) -> None:
    ids = seed.everyone()
    document_type = seed.insert("document_type", key="another_letter", display_name="Letter", version="1")
    extraction = seed.insert("extraction", practice_id=ids["practice"], document_id=seed.document(ids), document_type_id=document_type, reader="classic_ocr")
    with rejects(ForeignKeyViolation):
        seed.insert(
            "extracted_fact",
            practice_id=ids["practice"],
            extraction_id=extraction,
            patient_id=ids["patient"],
            fact_kind="horoscope",
            payload={},
            confidence=0.5,
            confidence_band="medium",
            required_job_title="clinician",
        )


def test_only_an_installed_module_can_be_activated(seed: Seed, rejects: Rejects) -> None:
    ids = seed.everyone()
    seed.insert("practice_module", practice_id=ids["practice"], module_key="oncology", changed_by_user_id=ids["user"])
    with rejects(ForeignKeyViolation):
        seed.insert("practice_module", practice_id=ids["practice"], module_key="cardiology", changed_by_user_id=ids["user"])


# --- Uniques --------------------------------------------------------------------------------


def test_pseudonyms_are_unique_across_practices(seed: Seed, rejects: Rejects) -> None:
    seed.patient(seed.practice(), pseudonym="VG-0042")
    with rejects(UniqueViolation):
        seed.patient(seed.practice(), pseudonym="VG-0042")


def test_usernames_are_unique_across_vigil(seed: Seed, rejects: Rejects) -> None:
    first, second = seed.practice(), seed.practice()
    seed.user(first, username="kim")
    with rejects(UniqueViolation):
        seed.user(second, username="kim")


def test_a_user_has_one_membership_per_practice(seed: Seed, rejects: Rejects) -> None:
    practice = seed.practice()
    user = seed.user(practice)
    seed.member(seed.practice(), user)
    with rejects(UniqueViolation):
        seed.member(practice, user, job_title="secretary")


def test_provider_numbers_are_unique_per_practice_when_present(seed: Seed, rejects: Rejects) -> None:
    practice = seed.practice()
    seed.provider(practice, provider_number="1234567A")
    seed.provider(practice)
    seed.provider(practice)
    with rejects(UniqueViolation):
        seed.provider(practice, provider_number="1234567A")


def test_the_same_file_cant_be_uploaded_twice_for_a_patient(seed: Seed, rejects: Rejects) -> None:
    ids = seed.everyone()
    seed.document(ids, original_sha256="same-hash")
    seed.document(ids, original_sha256="same-hash", patient_id=seed.patient(ids["practice"]))
    with rejects(UniqueViolation):
        seed.document(ids, original_sha256="same-hash")


def test_one_identity_per_patient(seed: Seed, rejects: Rejects) -> None:
    ids = seed.everyone()
    identity = dict(practice_id=ids["practice"], patient_id=ids["patient"], given_name="Jane", family_name="Citizen")
    seed.insert("identity.patient_identity", **identity)
    with rejects(UniqueViolation):
        seed.insert("identity.patient_identity", **identity)


# --- Other domain rules ---------------------------------------------------------------------


def test_a_held_document_needs_a_hold_reason_and_only_then(seed: Seed, rejects: Rejects) -> None:
    ids = seed.everyone()
    seed.document(ids, status="held", hold_reason="unreadable")
    with rejects(CheckViolation):
        seed.document(ids, status="held")
    with rejects(CheckViolation):
        seed.document(ids, status="complete", hold_reason="user_held")


def test_ocr_pages_belong_to_exactly_one_parent(seed: Seed, rejects: Rejects) -> None:
    ids = seed.everyone()
    page = dict(practice_id=ids["practice"], page_number=1, engine="doctr", engine_version="1", words=[])
    seed.insert("ocr_page", document_id=seed.document(ids), **page)
    with rejects(CheckViolation):
        seed.insert("ocr_page", **page)


def test_clinical_record_rows_need_provenance(seed: Seed, rejects: Rejects) -> None:
    ids = seed.everyone()
    with rejects(CheckViolation):
        seed.insert("condition", practice_id=ids["practice"], patient_id=ids["patient"], name="No source")


def test_performance_status_stays_within_its_scale(seed: Seed, rejects: Rejects) -> None:
    ids = seed.everyone()
    row = dict(practice_id=ids["practice"], patient_id=ids["patient"], assessed_on="2026-09-01", entered_by_user_id=ids["user"])
    seed.insert("performance_status", scale="ECOG", value=2, **row)
    seed.insert("performance_status", scale="KPS", value=70, **row)
    with rejects(CheckViolation):
        seed.insert("performance_status", scale="ECOG", value=6, **row)
    with rejects(CheckViolation):
        seed.insert("performance_status", scale="KPS", value=75, **row)


def test_patient_payloads_to_the_cloud_name_their_document(seed: Seed, rejects: Rejects) -> None:
    ids = seed.everyone()
    seed.cloud_request(ids)
    with rejects(CheckViolation):
        seed.insert("cloud_request", practice_id=ids["practice"], purpose="extract", payload_kind="pseudonymised_text", payload_sha256="x", model_id="m")
    seed.insert("cloud_request", purpose="parse_criteria", payload_kind="public_text", payload_sha256="x", model_id="m")


def test_a_practice_has_at_most_one_primary_site(seed: Seed, rejects: Rejects) -> None:
    practice = seed.practice()
    seed.site(practice, is_primary=True)
    seed.site(practice, name="Hospital clinic")
    seed.site(seed.practice(), is_primary=True)
    with rejects(UniqueViolation):
        seed.site(practice, name="Second rooms", is_primary=True)


def test_a_patient_has_at_most_one_primary_care_team_member(seed: Seed, rejects: Rejects) -> None:
    ids = seed.everyone()
    oncologist, gp = seed.provider(ids["practice"]), seed.provider(ids["practice"], specialty="general_practice")
    member = dict(practice_id=ids["practice"], patient_id=ids["patient"])
    seed.insert("care_team_member", provider_id=oncologist, role="treating_oncologist", is_primary=True, **member)
    seed.insert("care_team_member", provider_id=gp, role="referring_gp", **member)
    with rejects(UniqueViolation):
        seed.insert("care_team_member", provider_id=gp, role="referring_gp", is_primary=True, **member)
