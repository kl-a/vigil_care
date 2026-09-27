"""Oncology's registration through the Specialty Module contract (design doc §4.1). Stage 4 adds its entry by
hand (Cancer Diagnosis in #37, more to come); Document Types, trial vocabulary and the eviQ source arrive with
Stages 9, 10 and 11."""

from app.modules.registry.contract import PatientTab, SpecialtyModule, UiSection
from app.specialties.oncology.read_only import plain_facts
from app.specialties.oncology.router import router
from app.specialties.oncology.verification_rights import ONCOLOGY_FACT_RIGHTS

MODULE = SpecialtyModule(
    key="oncology",
    display_name="Oncology",
    version="0.1.0",
    condition_extension="cancer_diagnosis",
    verification_rights=ONCOLOGY_FACT_RIGHTS,
    ui_sections=(
        UiSection("cancer-diagnoses", "patient-overview", "Cancer Diagnoses", 10),
        UiSection("diagnosis", "patient-summary", "Diagnosis", 20),
        UiSection("cancer-diagnosis", "clinical-data-tabs", "Cancer Diagnosis", 5),
        UiSection("response-assessments", "clinical-data-tabs", "Response Assessments", 10),
        UiSection("biomarkers", "clinical-data-tabs", "Biomarkers", 20),
        UiSection("performance-status", "clinical-data-tabs", "Performance Status", 30),
        UiSection("cns", "clinical-data-tabs", "CNS", 40),
    ),
    patient_tabs=(PatientTab("treatment-options", "Treatment Options"),),
    read_only_view=plain_facts,
    router=router,
)
