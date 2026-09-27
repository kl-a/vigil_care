"""Oncology's API (#37, #38, #39, #40, #43, #44): Cancer Types and Cancer Diagnoses and what hangs off them. Mounted through the module contract; the services
refuse (403) Practices where Oncology isn't active, and anyone whose Job Title can't do it."""

import uuid

from fastapi import APIRouter, HTTPException, Response, status

from app.audit.schemas import Removal
from app.modules.accounts.dependencies import Db, SignedIn
from app.modules.clinical import entry
from app.specialties.oncology import biomarkers, cancer_diagnoses, lines_of_therapy, observations, recurrences, response_assessments
from app.specialties.oncology.schemas import (
    Attribution, BestResponse, BiomarkerMove, BiomarkerRow, CancerDiagnosisChange, CancerDiagnosisRow, CancerTypeOption, CnsStatusChange, CnsStatusRow,
    LineOfTherapy, LineOverride, NewBiomarker, NewCancerDiagnosis, NewCnsStatus, NewPerformanceStatus, NewRecurrence,
    NewResponseAssessment, PerformanceStatusRow, RecurrenceRow, ResponseAssessmentRow, ResponseOverride, RuleOut,
)

router = APIRouter(tags=["oncology"])
_MISSING = (entry.PatientNotFound, entry.RecordNotFound)


def _not_found() -> HTTPException:
    return HTTPException(status.HTTP_404_NOT_FOUND, "Not found for this Patient.")


@router.get("/cancer-types")
def cancer_types(actor: SignedIn, db: Db) -> list[CancerTypeOption]:
    return cancer_diagnoses.cancer_types(db, actor)


@router.get("/patients/{patient_id}/cancer-diagnoses")
def list_cancer_diagnoses(patient_id: uuid.UUID, actor: SignedIn, db: Db) -> list[CancerDiagnosisRow]:
    try:
        return cancer_diagnoses.cancer_diagnoses(db, actor, patient_id)
    except _MISSING:
        raise _not_found() from None


@router.post("/patients/{patient_id}/cancer-diagnoses", status_code=status.HTTP_201_CREATED)
def record_cancer_diagnosis(patient_id: uuid.UUID, new: NewCancerDiagnosis, actor: SignedIn, db: Db) -> CancerDiagnosisRow:
    try:
        return cancer_diagnoses.record_cancer_diagnosis(db, actor, patient_id, new)
    except _MISSING:
        raise _not_found() from None
    except cancer_diagnoses.UnknownCancerType as error:
        raise HTTPException(status.HTTP_422_UNPROCESSABLE_CONTENT, str(error)) from None


@router.patch("/patients/{patient_id}/cancer-diagnoses/{diagnosis_id}")
def correct_cancer_diagnosis(
    patient_id: uuid.UUID, diagnosis_id: uuid.UUID, change: CancerDiagnosisChange, actor: SignedIn, db: Db
) -> CancerDiagnosisRow:
    try:
        return cancer_diagnoses.correct_cancer_diagnosis(db, actor, patient_id, diagnosis_id, change)
    except _MISSING:
        raise _not_found() from None


@router.delete("/patients/{patient_id}/cancer-diagnoses/{diagnosis_id}", status_code=status.HTTP_204_NO_CONTENT)
def remove_cancer_diagnosis(patient_id: uuid.UUID, diagnosis_id: uuid.UUID, removal: Removal, actor: SignedIn, db: Db) -> Response:
    try:
        cancer_diagnoses.remove_cancer_diagnosis(db, actor, patient_id, diagnosis_id, removal.reason)
    except _MISSING:
        raise _not_found() from None
    return Response(status_code=status.HTTP_204_NO_CONTENT)


# --- ECOG and CNS status (#44) ----------------------------------------------------------------------------


@router.get("/patients/{patient_id}/performance-status")
def list_performance_status(patient_id: uuid.UUID, actor: SignedIn, db: Db) -> list[PerformanceStatusRow]:
    """Newest first: the first is the current one."""
    try:
        return observations.performance_statuses(db, actor, patient_id)
    except _MISSING:
        raise _not_found() from None


@router.post("/patients/{patient_id}/performance-status", status_code=status.HTTP_201_CREATED)
def add_performance_status(patient_id: uuid.UUID, new: NewPerformanceStatus, actor: SignedIn, db: Db) -> PerformanceStatusRow:
    try:
        return observations.add_performance_status(db, actor, patient_id, new)
    except _MISSING:
        raise _not_found() from None


@router.delete("/patients/{patient_id}/performance-status/{row_id}", status_code=status.HTTP_204_NO_CONTENT)
def remove_performance_status(patient_id: uuid.UUID, row_id: uuid.UUID, removal: Removal, actor: SignedIn, db: Db) -> Response:
    try:
        observations.remove_performance_status(db, actor, patient_id, row_id, removal.reason)
    except _MISSING:
        raise _not_found() from None
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.get("/patients/{patient_id}/cns-status")
def list_cns_status(patient_id: uuid.UUID, actor: SignedIn, db: Db) -> list[CnsStatusRow]:
    try:
        return observations.cns_statuses(db, actor, patient_id)
    except _MISSING:
        raise _not_found() from None


@router.post("/patients/{patient_id}/cns-status", status_code=status.HTTP_201_CREATED)
def add_cns_status(patient_id: uuid.UUID, new: NewCnsStatus, actor: SignedIn, db: Db) -> CnsStatusRow:
    try:
        return observations.add_cns_status(db, actor, patient_id, new)
    except _MISSING:
        raise _not_found() from None


@router.patch("/patients/{patient_id}/cns-status/{row_id}")
def correct_cns_status(patient_id: uuid.UUID, row_id: uuid.UUID, change: CnsStatusChange, actor: SignedIn, db: Db) -> CnsStatusRow:
    try:
        return observations.correct_cns_status(db, actor, patient_id, row_id, change)
    except _MISSING:
        raise _not_found() from None


@router.delete("/patients/{patient_id}/cns-status/{row_id}", status_code=status.HTTP_204_NO_CONTENT)
def remove_cns_status(patient_id: uuid.UUID, row_id: uuid.UUID, removal: Removal, actor: SignedIn, db: Db) -> Response:
    try:
        observations.remove_cns_status(db, actor, patient_id, row_id, removal.reason)
    except _MISSING:
        raise _not_found() from None
    return Response(status_code=status.HTTP_204_NO_CONTENT)


# --- Biomarkers (#38) -------------------------------------------------------------------------------------

BIOMARKERS = "/patients/{patient_id}/cancer-diagnoses/{diagnosis_id}/biomarkers"


@router.get(BIOMARKERS)
def list_biomarkers(patient_id: uuid.UUID, diagnosis_id: uuid.UUID, actor: SignedIn, db: Db) -> list[BiomarkerRow]:
    """Full history, newest first, each marked current and whether its results differ."""
    try:
        return biomarkers.biomarkers(db, actor, patient_id, diagnosis_id)
    except _MISSING:
        raise _not_found() from None


@router.post(BIOMARKERS, status_code=status.HTTP_201_CREATED)
def add_biomarker(patient_id: uuid.UUID, diagnosis_id: uuid.UUID, new: NewBiomarker, actor: SignedIn, db: Db) -> BiomarkerRow:
    try:
        return biomarkers.add_biomarker(db, actor, patient_id, diagnosis_id, new)
    except _MISSING:
        raise _not_found() from None


@router.delete(BIOMARKERS + "/{biomarker_id}", status_code=status.HTTP_204_NO_CONTENT)
def remove_biomarker(
    patient_id: uuid.UUID, diagnosis_id: uuid.UUID, biomarker_id: uuid.UUID, removal: Removal, actor: SignedIn, db: Db
) -> Response:
    """Never overwritten: a wrong result is removed (with why) and entered again."""
    try:
        biomarkers.remove_biomarker(db, actor, patient_id, diagnosis_id, biomarker_id, removal.reason)
    except _MISSING:
        raise _not_found() from None
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.post(BIOMARKERS + "/{biomarker_id}/move")
def move_biomarker(
    patient_id: uuid.UUID, diagnosis_id: uuid.UUID, biomarker_id: uuid.UUID, move: BiomarkerMove, actor: SignedIn, db: Db
) -> BiomarkerRow:
    try:
        return biomarkers.move_biomarker(db, actor, patient_id, diagnosis_id, biomarker_id, move)
    except _MISSING:
        raise _not_found() from None


# --- Recurrences (#39) ------------------------------------------------------------------------------------


def _conflict(error: ValueError) -> HTTPException:
    return HTTPException(status.HTTP_409_CONFLICT, str(error))


@router.get("/patients/{patient_id}/recurrences")
def list_recurrences(patient_id: uuid.UUID, actor: SignedIn, db: Db) -> list[RecurrenceRow]:
    try:
        return recurrences.recurrences(db, actor, patient_id)
    except _MISSING:
        raise _not_found() from None


@router.post("/patients/{patient_id}/cancer-diagnoses/{diagnosis_id}/recurrences", status_code=status.HTTP_201_CREATED)
def suspect_recurrence(patient_id: uuid.UUID, diagnosis_id: uuid.UUID, new: NewRecurrence, actor: SignedIn, db: Db) -> RecurrenceRow:
    """Recorded as a Suspected Recurrence; a clinician resolves it."""
    try:
        return recurrences.suspect(db, actor, patient_id, diagnosis_id, new)
    except _MISSING:
        raise _not_found() from None


@router.post("/patients/{patient_id}/recurrences/{recurrence_id}/confirm")
def confirm_recurrence(patient_id: uuid.UUID, recurrence_id: uuid.UUID, actor: SignedIn, db: Db) -> RecurrenceRow:
    try:
        return recurrences.confirm(db, actor, patient_id, recurrence_id)
    except _MISSING:
        raise _not_found() from None
    except recurrences.NotSuspected as error:
        raise _conflict(error) from None


@router.post("/patients/{patient_id}/recurrences/{recurrence_id}/new-primary")
def new_primary_instead(patient_id: uuid.UUID, recurrence_id: uuid.UUID, new: NewCancerDiagnosis, actor: SignedIn, db: Db) -> RecurrenceRow:
    try:
        return recurrences.new_primary_instead(db, actor, patient_id, recurrence_id, new)
    except _MISSING:
        raise _not_found() from None
    except recurrences.NotSuspected as error:
        raise _conflict(error) from None
    except cancer_diagnoses.UnknownCancerType as error:
        raise HTTPException(status.HTTP_422_UNPROCESSABLE_CONTENT, str(error)) from None


@router.post("/patients/{patient_id}/recurrences/{recurrence_id}/rule-out")
def rule_out_recurrence(patient_id: uuid.UUID, recurrence_id: uuid.UUID, body: RuleOut, actor: SignedIn, db: Db) -> RecurrenceRow:
    try:
        return recurrences.rule_out(db, actor, patient_id, recurrence_id, body.reason)
    except _MISSING:
        raise _not_found() from None
    except recurrences.NotSuspected as error:
        raise _conflict(error) from None


@router.delete("/patients/{patient_id}/recurrences/{recurrence_id}", status_code=status.HTTP_204_NO_CONTENT)
def remove_recurrence(patient_id: uuid.UUID, recurrence_id: uuid.UUID, removal: Removal, actor: SignedIn, db: Db) -> Response:
    try:
        recurrences.remove(db, actor, patient_id, recurrence_id, removal.reason)
    except _MISSING:
        raise _not_found() from None
    return Response(status_code=status.HTTP_204_NO_CONTENT)


# --- Line of Therapy (#40) --------------------------------------------------------------------------------


@router.get("/patients/{patient_id}/lines-of-therapy")
def list_lines_of_therapy(patient_id: uuid.UUID, actor: SignedIn, db: Db) -> list[LineOfTherapy]:
    """The Line of Therapy of each palliative systemic course, derived by start date unless a clinician set it."""
    try:
        return lines_of_therapy.lines_of_therapy(db, actor, patient_id)
    except _MISSING:
        raise _not_found() from None


@router.put("/patients/{patient_id}/treatment-courses/{course_id}/line-of-therapy")
def override_line_of_therapy(patient_id: uuid.UUID, course_id: uuid.UUID, change: LineOverride, actor: SignedIn, db: Db) -> list[LineOfTherapy]:
    """Set a course's line, or derive it again (`line: null`), with a reason. Clinicians only."""
    try:
        return lines_of_therapy.override(db, actor, patient_id, course_id, change)
    except _MISSING:
        raise _not_found() from None
    except lines_of_therapy.NotAPalliativeSystemicCourse as error:
        raise HTTPException(status.HTTP_422_UNPROCESSABLE_CONTENT, str(error)) from None


# --- Response Assessments and best response (#43) --------------------------------------------------------

ASSESSMENT = "/patients/{patient_id}/response-assessments/{assessment_id}"


def _assessment_refused(error: Exception) -> HTTPException:
    if isinstance(error, _MISSING):
        return _not_found()
    if isinstance(error, response_assessments.AlreadyDone):
        return _conflict(error)
    return HTTPException(status.HTTP_422_UNPROCESSABLE_CONTENT, str(error))


_ASSESSMENT_REFUSED = (*_MISSING, response_assessments.AlreadyDone, response_assessments.InvalidAssessment)


@router.get("/patients/{patient_id}/response-assessments")
def list_response_assessments(patient_id: uuid.UUID, actor: SignedIn, db: Db) -> list[ResponseAssessmentRow]:
    """Newest first; an overridden one names the clinician's assessment that counts instead."""
    try:
        return response_assessments.response_assessments(db, actor, patient_id)
    except _ASSESSMENT_REFUSED as error:
        raise _assessment_refused(error) from None


@router.post("/patients/{patient_id}/response-assessments", status_code=status.HTTP_201_CREATED)
def record_response_assessment(patient_id: uuid.UUID, new: NewResponseAssessment, actor: SignedIn, db: Db) -> ResponseAssessmentRow:
    """Without a Cancer Diagnosis: not sure which (a clinician attributes it later)."""
    try:
        return response_assessments.record(db, actor, patient_id, new)
    except _ASSESSMENT_REFUSED as error:
        raise _assessment_refused(error) from None


@router.post(ASSESSMENT + "/attribute")
def attribute_response_assessment(
    patient_id: uuid.UUID, assessment_id: uuid.UUID, attribution: Attribution, actor: SignedIn, db: Db
) -> ResponseAssessmentRow:
    """Clinicians only."""
    try:
        return response_assessments.attribute(db, actor, patient_id, assessment_id, attribution)
    except _ASSESSMENT_REFUSED as error:
        raise _assessment_refused(error) from None


@router.post(ASSESSMENT + "/override", status_code=status.HTTP_201_CREATED)
def override_response_assessment(
    patient_id: uuid.UUID, assessment_id: uuid.UUID, change: ResponseOverride, actor: SignedIn, db: Db
) -> ResponseAssessmentRow:
    """Clinicians only: their direction counts instead, with why."""
    try:
        return response_assessments.override(db, actor, patient_id, assessment_id, change)
    except _ASSESSMENT_REFUSED as error:
        raise _assessment_refused(error) from None


@router.delete(ASSESSMENT, status_code=status.HTTP_204_NO_CONTENT)
def remove_response_assessment(patient_id: uuid.UUID, assessment_id: uuid.UUID, removal: Removal, actor: SignedIn, db: Db) -> Response:
    try:
        response_assessments.remove(db, actor, patient_id, assessment_id, removal.reason)
    except _ASSESSMENT_REFUSED as error:
        raise _assessment_refused(error) from None
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.get("/patients/{patient_id}/best-responses")
def list_best_responses(patient_id: uuid.UUID, actor: SignedIn, db: Db) -> list[BestResponse]:
    """Each course's best response, derived from the Response Assessments dated during it."""
    try:
        return response_assessments.best_responses(db, actor, patient_id)
    except _ASSESSMENT_REFUSED as error:
        raise _assessment_refused(error) from None
