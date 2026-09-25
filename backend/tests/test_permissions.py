"""One test per row of design doc §6.4, through the permission check's public interface."""

import pytest

from app.core.permissions import CORE_FACT_RIGHTS, VerificationRights, may
from app.core.vocabulary import JobTitle
from app.specialties.oncology.verification_rights import ONCOLOGY_FACT_RIGHTS

ALL: tuple[JobTitle, ...] = ("clinician", "trial_coordinator", "secretary", "developer_admin")
RIGHTS = VerificationRights({**CORE_FACT_RIGHTS, **ONCOLOGY_FACT_RIGHTS})


def allowed(check: object) -> set[str]:
    return {job_title for job_title in ALL if check(job_title)}  # type: ignore[operator]


@pytest.mark.parametrize(
    "permission", ["verify_patient_identity", "verify_care_team", "verify_document_type", "review_redaction", "hold_document"]
)
def test_row_1_identity_care_team_document_type_redaction_and_holding(permission: str) -> None:
    assert allowed(lambda jt: may(jt, permission)) == {"clinician", "trial_coordinator", "secretary"}


@pytest.mark.parametrize(
    "fact_kind",
    ["lab_result", "medication", "condition", "imaging_study", "finding", "performance_status", "cns_status", "clinical_note", "management_plan"],
)
def test_row_2_results_medications_conditions_imaging_notes_plans(fact_kind: str) -> None:
    assert allowed(lambda jt: RIGHTS.can_verify(jt, fact_kind)) == {"clinician", "trial_coordinator"}
    assert RIGHTS.required_job_title(fact_kind) == "trial_coordinator"
    assert not RIGHTS.needs_reauthentication(fact_kind)


@pytest.mark.parametrize("fact_kind", ["treatment_course", "biomarker"])
def test_row_3_treatment_courses_and_biomarkers(fact_kind: str) -> None:
    assert allowed(lambda jt: RIGHTS.can_verify(jt, fact_kind)) == {"clinician", "trial_coordinator"}


@pytest.mark.parametrize("fact_kind", ["cancer_diagnosis", "recurrence", "response_assessment_override"])
def test_row_4_cancer_diagnosis_stage_extent_recurrence_and_overrides_are_clinician_only(fact_kind: str) -> None:
    assert allowed(lambda jt: RIGHTS.can_verify(jt, fact_kind)) == {"clinician"}
    assert RIGHTS.required_job_title(fact_kind) == "clinician"
    assert RIGHTS.needs_reauthentication(fact_kind)


@pytest.mark.parametrize("permission", ["sign_off_identified_export", "sign_off_deidentified_export"])
def test_rows_5_and_6_export_sign_off(permission: str) -> None:
    assert allowed(lambda jt: may(jt, permission)) == {"clinician", "trial_coordinator", "secretary"}


def test_row_7_manage_users() -> None:
    assert allowed(lambda jt: may(jt, "manage_users")) == {"clinician", "secretary", "developer_admin"}


def test_row_7b_manage_the_provider_directory() -> None:
    assert allowed(lambda jt: may(jt, "manage_providers")) == {"clinician", "trial_coordinator", "secretary"}


def test_row_8_activate_specialty_modules() -> None:
    assert allowed(lambda jt: may(jt, "activate_modules")) == {"developer_admin"}


def test_row_9_change_settings() -> None:
    assert allowed(lambda jt: may(jt, "change_settings")) == {"clinician", "developer_admin"}


def test_row_10_view_patient_data_never_developer_admin() -> None:
    assert allowed(lambda jt: may(jt, "view_patient_data")) == {"clinician", "trial_coordinator", "secretary"}


def test_row_11_support_views() -> None:
    assert allowed(lambda jt: may(jt, "support_views")) == set(ALL)


def test_row_12_start_a_refresh() -> None:
    assert allowed(lambda jt: may(jt, "start_refresh")) == {"developer_admin"}


def test_row_13_pbs_drug_lookup_never_developer_admin() -> None:
    assert allowed(lambda jt: may(jt, "pbs_lookup")) == {"clinician", "trial_coordinator", "secretary"}


def test_a_developer_admin_can_verify_no_fact_kind() -> None:
    assert not any(RIGHTS.can_verify("developer_admin", kind) for kind in RIGHTS.fact_kinds())


def test_a_fact_kind_nobody_registered_is_refused() -> None:
    with pytest.raises(KeyError):
        RIGHTS.can_verify("clinician", "horoscope")


def test_the_core_alone_knows_no_oncology_fact_kinds() -> None:
    assert "cancer_diagnosis" not in VerificationRights(CORE_FACT_RIGHTS).fact_kinds()
