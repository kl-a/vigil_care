"""The Clinical Record entered by hand (#35, #40, #42, #45; design doc §5 screen 9). Refusals (403) come from the services."""

import uuid

from fastapi import APIRouter, HTTPException, Response, status

from app.audit.schemas import Removal
from app.modules.accounts.dependencies import Db, SignedIn
from app.modules.clinical import conditions, entry, imaging, labs, plan_and_notes, treatment_courses
from app.modules.clinical.schemas import (
    ClinicalNoteChange, ClinicalNoteRow, ConditionChange, ConditionRow, FindingChange, FindingRow, ImagingStudyChange,
    ImagingStudyRow, LabPanelRow, LabResultChange, LabResultRow,
    ManagementPlanChange, ManagementPlanRow, ModuleFacts, NewClinicalNote, NewCondition, NewFinding, NewImagingStudy, NewLabPanel, NewManagementPlan,
    NewNextStep, NewTreatmentCourse, NextStepChange, NextStepRow, TreatmentCourseChange, TreatmentCourseRow,
)

router = APIRouter(tags=["clinical record"])


_MISSING: dict[type[LookupError], str] = {
    entry.PatientNotFound: "No such Patient.",
    entry.RecordNotFound: "Not found for this Patient.",
}


def _missing(error: LookupError) -> HTTPException:
    return HTTPException(status.HTTP_404_NOT_FOUND, _MISSING[type(error)])


@router.get("/clinical/entry-rights")
def entry_rights(actor: SignedIn, db: Db) -> dict[str, bool]:
    """Which kinds of Clinical Record value the signed-in User may enter by hand."""
    return entry.entry_rights(db, actor)


@router.get("/patients/{patient_id}/inactive-module-facts")
def inactive_module_facts(patient_id: uuid.UUID, actor: SignedIn, db: Db) -> list[ModuleFacts]:
    try:
        return entry.inactive_module_facts(db, actor, patient_id)
    except tuple(_MISSING) as error:
        raise _missing(error) from None


@router.get("/patients/{patient_id}/conditions")
def list_conditions(patient_id: uuid.UUID, actor: SignedIn, db: Db) -> list[ConditionRow]:
    try:
        return conditions.conditions(db, actor, patient_id)
    except tuple(_MISSING) as error:
        raise _missing(error) from None


@router.post("/patients/{patient_id}/conditions", status_code=status.HTTP_201_CREATED)
def add_condition(patient_id: uuid.UUID, new: NewCondition, actor: SignedIn, db: Db) -> ConditionRow:
    try:
        return conditions.add_condition(db, actor, patient_id, new)
    except tuple(_MISSING) as error:
        raise _missing(error) from None


@router.patch("/patients/{patient_id}/conditions/{condition_id}")
def change_condition(patient_id: uuid.UUID, condition_id: uuid.UUID, change: ConditionChange, actor: SignedIn, db: Db) -> ConditionRow:
    try:
        return conditions.change_condition(db, actor, patient_id, condition_id, change)
    except tuple(_MISSING) as error:
        raise _missing(error) from None


@router.delete("/patients/{patient_id}/conditions/{condition_id}", status_code=status.HTTP_204_NO_CONTENT)
def remove_condition(patient_id: uuid.UUID, condition_id: uuid.UUID, removal: Removal, actor: SignedIn, db: Db) -> Response:
    try:
        conditions.remove_condition(db, actor, patient_id, condition_id, removal.reason)
    except tuple(_MISSING) as error:
        raise _missing(error) from None
    return Response(status_code=status.HTTP_204_NO_CONTENT)


# --- Plan and notes (#45) -----------------------------------------------------------------------------------


def _invalid(error: ValueError) -> HTTPException:
    code = status.HTTP_409_CONFLICT if isinstance(error, plan_and_notes.AlreadyDone) else status.HTTP_422_UNPROCESSABLE_CONTENT
    return HTTPException(code, str(error))


@router.get("/patients/{patient_id}/management-plans")
def list_management_plans(patient_id: uuid.UUID, actor: SignedIn, db: Db) -> list[ManagementPlanRow]:
    """Newest first: the first is the current plan."""
    try:
        return plan_and_notes.management_plans(db, actor, patient_id)
    except tuple(_MISSING) as error:
        raise _missing(error) from None


@router.post("/patients/{patient_id}/management-plans", status_code=status.HTTP_201_CREATED)
def add_management_plan(patient_id: uuid.UUID, new: NewManagementPlan, actor: SignedIn, db: Db) -> ManagementPlanRow:
    try:
        return plan_and_notes.add_management_plan(db, actor, patient_id, new)
    except tuple(_MISSING) as error:
        raise _missing(error) from None
    except plan_and_notes.NoSuchProvider as error:
        raise _invalid(error) from None


@router.patch("/patients/{patient_id}/management-plans/{plan_id}")
def change_management_plan(patient_id: uuid.UUID, plan_id: uuid.UUID, change: ManagementPlanChange, actor: SignedIn, db: Db) -> ManagementPlanRow:
    try:
        return plan_and_notes.change_management_plan(db, actor, patient_id, plan_id, change)
    except tuple(_MISSING) as error:
        raise _missing(error) from None
    except plan_and_notes.NoSuchProvider as error:
        raise _invalid(error) from None


@router.delete("/patients/{patient_id}/management-plans/{plan_id}", status_code=status.HTTP_204_NO_CONTENT)
def remove_management_plan(patient_id: uuid.UUID, plan_id: uuid.UUID, removal: Removal, actor: SignedIn, db: Db) -> Response:
    try:
        plan_and_notes.remove_management_plan(db, actor, patient_id, plan_id, removal.reason)
    except tuple(_MISSING) as error:
        raise _missing(error) from None
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.get("/patients/{patient_id}/clinical-notes")
def list_clinical_notes(patient_id: uuid.UUID, actor: SignedIn, db: Db) -> list[ClinicalNoteRow]:
    try:
        return plan_and_notes.clinical_notes(db, actor, patient_id)
    except tuple(_MISSING) as error:
        raise _missing(error) from None


@router.post("/patients/{patient_id}/clinical-notes", status_code=status.HTTP_201_CREATED)
def add_clinical_note(patient_id: uuid.UUID, new: NewClinicalNote, actor: SignedIn, db: Db) -> ClinicalNoteRow:
    try:
        return plan_and_notes.add_clinical_note(db, actor, patient_id, new)
    except tuple(_MISSING) as error:
        raise _missing(error) from None
    except plan_and_notes.NoSuchProvider as error:
        raise _invalid(error) from None


@router.patch("/patients/{patient_id}/clinical-notes/{note_id}")
def change_clinical_note(patient_id: uuid.UUID, note_id: uuid.UUID, change: ClinicalNoteChange, actor: SignedIn, db: Db) -> ClinicalNoteRow:
    try:
        return plan_and_notes.change_clinical_note(db, actor, patient_id, note_id, change)
    except tuple(_MISSING) as error:
        raise _missing(error) from None
    except plan_and_notes.NoSuchProvider as error:
        raise _invalid(error) from None


@router.delete("/patients/{patient_id}/clinical-notes/{note_id}", status_code=status.HTTP_204_NO_CONTENT)
def remove_clinical_note(patient_id: uuid.UUID, note_id: uuid.UUID, removal: Removal, actor: SignedIn, db: Db) -> Response:
    try:
        plan_and_notes.remove_clinical_note(db, actor, patient_id, note_id, removal.reason)
    except tuple(_MISSING) as error:
        raise _missing(error) from None
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.get("/patients/{patient_id}/next-steps")
def list_next_steps(patient_id: uuid.UUID, actor: SignedIn, db: Db) -> list[NextStepRow]:
    """Open ones first, soonest due first."""
    try:
        return plan_and_notes.next_steps(db, actor, patient_id)
    except tuple(_MISSING) as error:
        raise _missing(error) from None


@router.post("/patients/{patient_id}/next-steps", status_code=status.HTTP_201_CREATED)
def add_next_step(patient_id: uuid.UUID, new: NewNextStep, actor: SignedIn, db: Db) -> NextStepRow:
    try:
        return plan_and_notes.add_next_step(db, actor, patient_id, new)
    except tuple(_MISSING) as error:
        raise _missing(error) from None


@router.post("/patients/{patient_id}/next-steps/{step_id}/done")
def mark_next_step_done(patient_id: uuid.UUID, step_id: uuid.UUID, actor: SignedIn, db: Db) -> NextStepRow:
    try:
        return plan_and_notes.mark_next_step_done(db, actor, patient_id, step_id)
    except tuple(_MISSING) as error:
        raise _missing(error) from None
    except plan_and_notes.AlreadyDone as error:
        raise _invalid(error) from None


@router.patch("/patients/{patient_id}/next-steps/{step_id}")
def change_next_step(patient_id: uuid.UUID, step_id: uuid.UUID, change: NextStepChange, actor: SignedIn, db: Db) -> NextStepRow:
    try:
        return plan_and_notes.change_next_step(db, actor, patient_id, step_id, change)
    except tuple(_MISSING) as error:
        raise _missing(error) from None


@router.delete("/patients/{patient_id}/next-steps/{step_id}", status_code=status.HTTP_204_NO_CONTENT)
def remove_next_step(patient_id: uuid.UUID, step_id: uuid.UUID, removal: Removal, actor: SignedIn, db: Db) -> Response:
    try:
        plan_and_notes.remove_next_step(db, actor, patient_id, step_id, removal.reason)
    except tuple(_MISSING) as error:
        raise _missing(error) from None
    return Response(status_code=status.HTTP_204_NO_CONTENT)


# --- Labs (#42) -------------------------------------------------------------------------------------------


@router.get("/patients/{patient_id}/labs")
def list_lab_results(patient_id: uuid.UUID, actor: SignedIn, db: Db) -> list[LabResultRow]:
    """Newest first."""
    try:
        return labs.lab_results(db, actor, patient_id)
    except tuple(_MISSING) as error:
        raise _missing(error) from None


@router.post("/patients/{patient_id}/lab-panels", status_code=status.HTTP_201_CREATED)
def add_lab_panel(patient_id: uuid.UUID, new: NewLabPanel, actor: SignedIn, db: Db) -> LabPanelRow:
    """A panel of results in one save, with one Verification."""
    try:
        return labs.add_panel(db, actor, patient_id, new)
    except tuple(_MISSING) as error:
        raise _missing(error) from None


@router.patch("/patients/{patient_id}/labs/{result_id}")
def change_lab_result(patient_id: uuid.UUID, result_id: uuid.UUID, change: LabResultChange, actor: SignedIn, db: Db) -> LabResultRow:
    try:
        return labs.change_result(db, actor, patient_id, result_id, change)
    except tuple(_MISSING) as error:
        raise _missing(error) from None


@router.delete("/patients/{patient_id}/labs/{result_id}", status_code=status.HTTP_204_NO_CONTENT)
def remove_lab_result(patient_id: uuid.UUID, result_id: uuid.UUID, removal: Removal, actor: SignedIn, db: Db) -> Response:
    try:
        labs.remove_result(db, actor, patient_id, result_id, removal.reason)
    except tuple(_MISSING) as error:
        raise _missing(error) from None
    return Response(status_code=status.HTTP_204_NO_CONTENT)


# --- Treatment Courses (#40) ------------------------------------------------------------------------------


@router.get("/patients/{patient_id}/treatment-courses")
def list_treatment_courses(patient_id: uuid.UUID, actor: SignedIn, db: Db) -> list[TreatmentCourseRow]:
    """Most recent start first."""
    try:
        return treatment_courses.treatment_courses(db, actor, patient_id)
    except tuple(_MISSING) as error:
        raise _missing(error) from None


@router.post("/patients/{patient_id}/treatment-courses", status_code=status.HTTP_201_CREATED)
def add_treatment_course(patient_id: uuid.UUID, new: NewTreatmentCourse, actor: SignedIn, db: Db) -> TreatmentCourseRow:
    try:
        return treatment_courses.add_course(db, actor, patient_id, new)
    except tuple(_MISSING) as error:
        raise _missing(error) from None
    except treatment_courses.NoSuchCondition as error:
        raise _invalid(error) from None


@router.patch("/patients/{patient_id}/treatment-courses/{course_id}")
def change_treatment_course(
    patient_id: uuid.UUID, course_id: uuid.UUID, change: TreatmentCourseChange, actor: SignedIn, db: Db
) -> TreatmentCourseRow:
    try:
        return treatment_courses.change_course(db, actor, patient_id, course_id, change)
    except tuple(_MISSING) as error:
        raise _missing(error) from None
    except treatment_courses.InvalidCourse as error:
        raise _invalid(error) from None


@router.delete("/patients/{patient_id}/treatment-courses/{course_id}", status_code=status.HTTP_204_NO_CONTENT)
def remove_treatment_course(patient_id: uuid.UUID, course_id: uuid.UUID, removal: Removal, actor: SignedIn, db: Db) -> Response:
    try:
        treatment_courses.remove_course(db, actor, patient_id, course_id, removal.reason)
    except tuple(_MISSING) as error:
        raise _missing(error) from None
    return Response(status_code=status.HTTP_204_NO_CONTENT)


# --- Imaging Studies and Findings (#43) -------------------------------------------------------------------

STUDY_PATH = "/patients/{patient_id}/imaging-studies/{study_id}"


@router.get("/patients/{patient_id}/imaging-studies")
def list_imaging_studies(patient_id: uuid.UUID, actor: SignedIn, db: Db) -> list[ImagingStudyRow]:
    """Most recent first, each with its Findings."""
    try:
        return imaging.imaging_studies(db, actor, patient_id)
    except tuple(_MISSING) as error:
        raise _missing(error) from None


@router.post("/patients/{patient_id}/imaging-studies", status_code=status.HTTP_201_CREATED)
def add_imaging_study(patient_id: uuid.UUID, new: NewImagingStudy, actor: SignedIn, db: Db) -> ImagingStudyRow:
    try:
        return imaging.add_study(db, actor, patient_id, new)
    except tuple(_MISSING) as error:
        raise _missing(error) from None
    except imaging.NoSuchCondition as error:
        raise _invalid(error) from None


@router.patch(STUDY_PATH)
def change_imaging_study(patient_id: uuid.UUID, study_id: uuid.UUID, change: ImagingStudyChange, actor: SignedIn, db: Db) -> ImagingStudyRow:
    try:
        return imaging.change_study(db, actor, patient_id, study_id, change)
    except tuple(_MISSING) as error:
        raise _missing(error) from None


@router.delete(STUDY_PATH, status_code=status.HTTP_204_NO_CONTENT)
def remove_imaging_study(patient_id: uuid.UUID, study_id: uuid.UUID, removal: Removal, actor: SignedIn, db: Db) -> Response:
    try:
        imaging.remove_study(db, actor, patient_id, study_id, removal.reason)
    except tuple(_MISSING) as error:
        raise _missing(error) from None
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.post(STUDY_PATH + "/findings", status_code=status.HTTP_201_CREATED)
def add_finding(patient_id: uuid.UUID, study_id: uuid.UUID, new: NewFinding, actor: SignedIn, db: Db) -> FindingRow:
    try:
        return imaging.add_finding(db, actor, patient_id, study_id, new)
    except tuple(_MISSING) as error:
        raise _missing(error) from None
    except imaging.NoSuchCondition as error:
        raise _invalid(error) from None


@router.patch(STUDY_PATH + "/findings/{finding_id}")
def change_finding(
    patient_id: uuid.UUID, study_id: uuid.UUID, finding_id: uuid.UUID, change: FindingChange, actor: SignedIn, db: Db
) -> FindingRow:
    try:
        return imaging.change_finding(db, actor, patient_id, study_id, finding_id, change)
    except tuple(_MISSING) as error:
        raise _missing(error) from None
    except imaging.NoSuchCondition as error:
        raise _invalid(error) from None


@router.delete(STUDY_PATH + "/findings/{finding_id}", status_code=status.HTTP_204_NO_CONTENT)
def remove_finding(patient_id: uuid.UUID, study_id: uuid.UUID, finding_id: uuid.UUID, removal: Removal, actor: SignedIn, db: Db) -> Response:
    try:
        imaging.remove_finding(db, actor, patient_id, study_id, finding_id, removal.reason)
    except tuple(_MISSING) as error:
        raise _missing(error) from None
    return Response(status_code=status.HTTP_204_NO_CONTENT)
