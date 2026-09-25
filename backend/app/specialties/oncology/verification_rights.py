"""Oncology's rows of design doc §6.4, contributed to the Core's VerificationRights through the registry (#15)."""

from collections.abc import Mapping

from app.core.permissions import CLINICAL, CLINICIAN_ONLY, FactRight

ONCOLOGY_FACT_RIGHTS: Mapping[str, FactRight] = {
    # Row 2.
    "performance_status": CLINICAL,
    "cns_status": CLINICAL,
    # A Response Assessment as stated in a radiology report; an override is clinician-only (row 4).
    "response_assessment": CLINICAL,
    # Row 3.
    "biomarker": CLINICAL,
    # Row 4: Cancer Diagnosis (incl. Stage and Disease Extent), Recurrence attribution, overrides.
    "cancer_diagnosis": CLINICIAN_ONLY,
    "recurrence": CLINICIAN_ONLY,
    "response_assessment_override": CLINICIAN_ONLY,
}
