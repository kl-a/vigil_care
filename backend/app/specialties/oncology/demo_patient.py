"""A fully recorded demo Patient (#46): Robin Sample's Clinical Record, entered **through the same services** the
API uses, as the synthetic demo Users with Job Titles permitted to enter each fact, so every row has its
provenance and Verification. Oncology's `demo_data` (module contract), called by `make demo-data` (dev only); a
Patient that already has a Condition is left as it is, so loading again changes nothing.

The story (synthetic): colorectal cancer resected in 2024 with adjuvant CAPOX; metastatic to the liver in 2026,
on first-line FOLFOX + bevacizumab and responding; a melanoma from 2019 and a new lung nodule nobody has
attributed yet. It raises one Open Item of every Stage 5 type.
"""

import uuid
from collections.abc import Mapping
from dataclasses import dataclass
from datetime import date, timedelta
from decimal import Decimal

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.core.clock import practice_today
from app.core.vocabulary import JobTitle
from app.modules.clinical import conditions, imaging, labs, plan_and_notes, treatment_courses
from app.modules.clinical.models import Condition
from app.modules.clinical.schemas import (
    NewClinicalNote, NewCondition, NewFinding, NewImagingStudy, NewLabPanel, NewLabResult, NewManagementPlan, NewNextStep,
    NewTreatmentCourse, RegimenDrug,
)
from app.modules.medications import medications
from app.modules.medications.models import DrugReference
from app.modules.medications.schemas import NewMedication, Stop
from app.modules.registry.contract import DemoPractice
from app.specialties.oncology import biomarkers, cancer_diagnoses, observations, recurrences, response_assessments
from app.specialties.oncology.schemas import (
    NewBiomarker, NewCancerDiagnosis, NewPerformanceStatus, NewRecurrence, NewResponseAssessment,
)


@dataclass(frozen=True)
class DemoActor:
    """A demo User acting in the demo Practice, as the services expect of a signed-in User."""

    id: uuid.UUID
    practice_id: uuid.UUID
    job_title: JobTitle


PATIENT = "VG-0044"  # Robin Sample (synthetic)


def demo_data(db: Session, demo: DemoPractice) -> None:
    record(db, demo.practice_id, demo.patients[PATIENT], demo.users, oncologist=demo.providers["treating_oncologist"], gp=demo.providers["referring_gp"])


def record(db: Session, practice_id: uuid.UUID, patient_id: uuid.UUID, users: Mapping[JobTitle, uuid.UUID],
           oncologist: uuid.UUID, gp: uuid.UUID) -> None:
    exists = db.scalars(select(Condition.id).where(Condition.practice_id == practice_id, Condition.patient_id == patient_id)).first()
    if exists is not None:
        return
    clinician, coordinator, secretary = (DemoActor(users[title], practice_id, title) for title in ("clinician", "trial_coordinator", "secretary"))
    p = patient_id

    # Medical history.
    diabetes = conditions.add_condition(db, clinician, p, NewCondition(name="Type 2 diabetes", onset_date=date(2015, 6, 1), notes="On metformin"))
    conditions.add_condition(db, clinician, p, NewCondition(name="Hypertension", onset_date=date(2018, 2, 1)))
    conditions.add_condition(db, clinician, p, NewCondition(name="Deep vein thrombosis", status="resolved", onset_date=date(2019, 8, 1)))

    # The cancers.
    bowel = cancer_diagnoses.record_cancer_diagnosis(db, clinician, p, NewCancerDiagnosis(
        cancer_type="colorectal", name="Colorectal cancer", histology="Adenocarcinoma", primary_site="Sigmoid colon", dx_date=date(2024, 5, 14),
        stage_system="TNM", stage="IIIB", disease_extent="metastatic", disease_extent_as_of=date(2026, 2, 5), cancer_status="active",
    ))
    melanoma = cancer_diagnoses.record_cancer_diagnosis(db, clinician, p, NewCancerDiagnosis(
        cancer_type="melanoma", name="Melanoma, left forearm", primary_site="Left forearm", laterality="left", dx_date=date(2019, 3, 20),
        stage_system="AJCC", stage="IB", disease_extent="localised", cancer_status="no_evidence_of_disease",
    ))
    for marker in (
        NewBiomarker(name="KRAS", result="wild-type", method="NGS", specimen_site="Sigmoid colon", specimen_kind="primary", collected_on=date(2024, 5, 14)),
        NewBiomarker(name="MSI", result="stable", method="PCR", specimen_site="Sigmoid colon", specimen_kind="primary", collected_on=date(2024, 5, 14)),
        NewBiomarker(name="BRAF", variant="V600E", result="negative", method="NGS", specimen_site="Sigmoid colon", specimen_kind="primary", collected_on=date(2024, 5, 14)),
        # A later result that differs: an Open Item until a clinician marks it Seen.
        NewBiomarker(name="BRAF", variant="V600E", result="positive", method="ctDNA", specimen_kind="liquid_biopsy", collected_on=date(2026, 2, 20)),
    ):
        biomarkers.add_biomarker(db, coordinator, p, bowel.id, marker)
    # The new lung nodule might be the melanoma back: suspected, for a clinician to resolve.
    recurrences.suspect(db, coordinator, p, melanoma.id, NewRecurrence(detected_on=date(2026, 6, 10), extent="distant", sites=["lung"]))

    # Treatment.
    treatment_courses.add_course(db, clinician, p, NewTreatmentCourse(
        condition_id=bowel.condition_id, modality="surgery", intent="curative", start_date=date(2024, 6, 3), end_date=date(2024, 6, 3),
        details={"procedure": "Anterior resection", "margins": "Clear"},
    ))
    capox = treatment_courses.add_course(db, clinician, p, NewTreatmentCourse(
        condition_id=bowel.condition_id, modality="systemic", intent="adjuvant", regimen_name="CAPOX",
        regimen_drugs=[RegimenDrug(drug="Capecitabine", dose="1000 mg/m2 twice daily"), RegimenDrug(drug="Oxaliplatin", dose="130 mg/m2")],
        start_date=date(2024, 7, 1), end_date=date(2024, 12, 15), reason_stopped="Completed",
    ))
    folfox = treatment_courses.add_course(db, clinician, p, NewTreatmentCourse(
        condition_id=bowel.condition_id, modality="systemic", intent="palliative", regimen_name="FOLFOX + bevacizumab",
        regimen_drugs=[RegimenDrug(drug="Oxaliplatin", dose="85 mg/m2"), RegimenDrug(drug="Fluorouracil", dose="2400 mg/m2 over 46 h"),
                       RegimenDrug(drug="Bevacizumab", dose="5 mg/kg")],
        start_date=date(2026, 3, 2),
    ))

    # Medications, from the drug reference when a PBS Refresh has built it.
    def medication(actor: DemoActor, name: str, **fields: object) -> uuid.UUID:
        drug = db.scalars(select(DrugReference.id).where(func.lower(DrugReference.generic_name) == name.lower())).first()
        picked = {"drug_reference_id": drug} if drug else {"drug_name": name}
        return medications.add_medication(db, actor, p, NewMedication.model_validate(picked | fields)).id

    capecitabine = medication(coordinator, "Capecitabine", dose_amount=Decimal("1650"), dose_unit="mg", frequency="twice_daily", route="oral",
                              category="cancer_treatment", indication="Adjuvant CAPOX", start_date=date(2024, 7, 1), treatment_course_id=capox.id,
                              prescribed_by_provider_id=oncologist)
    medications.stop_medication(db, coordinator, p, capecitabine, Stop(end_date=date(2024, 12, 15), reason="Adjuvant course completed"))
    medication(coordinator, "Oxaliplatin", dose_amount=Decimal("85"), dose_unit="mg/m2", frequency="fortnightly", route="iv",
               category="cancer_treatment", start_date=date(2026, 3, 2), treatment_course_id=folfox.id, prescribed_by_provider_id=oncologist)
    medication(coordinator, "Ondansetron", dose_amount=Decimal("8"), dose_unit="mg", frequency="prn", route="oral", category="supportive_care",
               indication="Nausea", start_date=date(2026, 3, 2), prescribed_by_provider_id=oncologist)
    medication(coordinator, "Metformin", dose_amount=Decimal("500"), dose_unit="mg", frequency="twice_daily", route="oral",
               category="comorbidity_management", indication=diabetes.name, start_date=date(2015, 6, 1), source="patient_reported")

    # Results: bloods as panels, two CTs, and what the reports say about response.
    for on, hb, neutrophils, platelets, cea in (
        (date(2026, 3, 2), "128", "4.1", "250", "48"), (date(2026, 6, 8), "112", "2.3", "190", "21"), (date(2026, 9, 14), "104", "1.4", "160", "12"),
    ):
        labs.add_panel(db, coordinator, p, NewLabPanel(collected_on=on, panel="FBC", results=[
            NewLabResult(analyte="Haemoglobin", value=Decimal(hb), unit="g/L", ref_low=Decimal("115"), ref_high=Decimal("165")),
            NewLabResult(analyte="Neutrophils", value=Decimal(neutrophils), unit="x10^9/L", ref_low=Decimal("2.0"), ref_high=Decimal("7.5")),
            NewLabResult(analyte="Platelets", value=Decimal(platelets), unit="x10^9/L", ref_low=Decimal("150"), ref_high=Decimal("400")),
        ]))
        labs.add_panel(db, coordinator, p, NewLabPanel(collected_on=on, panel="Tumour markers", results=[
            NewLabResult(analyte="CEA", value=Decimal(cea), unit="ug/L", ref_high=Decimal("5")),
        ]))
    labs.add_panel(db, coordinator, p, NewLabPanel(collected_on=date(2026, 9, 14), panel="LFT", results=[
        NewLabResult(analyte="ALT", value=Decimal("45"), unit="U/L", ref_high=Decimal("40")),
        NewLabResult(analyte="Bilirubin", value=Decimal("12"), unit="umol/L", ref_high=Decimal("20")),
    ]))
    imaging.add_study(db, coordinator, p, NewImagingStudy(
        modality="CT", body_region="Chest, abdomen and pelvis", study_date=date(2026, 2, 5), comparison_date=date(2024, 11, 20),
        impression="Multiple new hepatic metastases, the largest 32 mm in segment VI.\nNo thoracic disease.",
        findings=[NewFinding(site="Liver segment VI", description="Metastasis", size_mm=Decimal("32"), is_new=True, is_measurable=True,
                             condition_id=bowel.condition_id)],
    ))
    restaging = imaging.add_study(db, coordinator, p, NewImagingStudy(
        modality="CT", body_region="Chest, abdomen and pelvis", study_date=date(2026, 6, 10), comparison_date=date(2026, 2, 5),
        impression="Interval decrease in hepatic metastases (segment VI 21 mm, previously 32 mm).\nNew 5 mm right lower lobe nodule, indeterminate.",
        findings=[
            NewFinding(site="Liver segment VI", description="Metastasis", size_mm=Decimal("21"), is_new=False, is_measurable=True,
                       condition_id=bowel.condition_id),
            # The report doesn't say what it is: left unattributed (an Open Item).
            NewFinding(site="Right lower lobe", laterality="right", description="Nodule", size_mm=Decimal("5"), is_new=True, is_measurable=False),
        ],
    ))
    response_assessments.record(db, coordinator, p, NewResponseAssessment(
        cancer_diagnosis_id=bowel.id, assessed_on=date(2026, 6, 10), direction="responding", source="radiology_report", imaging_study_id=restaging.id,
    ))
    # A report that says "stable disease" without saying which cancer: not sure which (an Open Item).
    response_assessments.record(db, coordinator, p, NewResponseAssessment(
        assessed_on=date(2026, 9, 15), direction="stable", source="radiology_report",
    ))
    observations.add_performance_status(db, clinician, p, NewPerformanceStatus(value=1, assessed_on=date(2026, 3, 2)))
    observations.add_performance_status(db, clinician, p, NewPerformanceStatus(value=1, assessed_on=date(2026, 9, 14)))

    # Plan and notes.
    plan_and_notes.add_management_plan(db, clinician, p, NewManagementPlan(
        plan_date=date(2026, 6, 12), authored_by_provider_id=oncologist,
        plan_text="Responding to first-line FOLFOX + bevacizumab.\nContinue; restage after 6 more cycles.\n"
                  "Discuss the new lung nodule at MDT: ? melanoma recurrence vs colorectal metastasis.",
    ))
    plan_and_notes.add_clinical_note(db, clinician, p, NewClinicalNote(
        note_type="letter_to_referrer", note_date=date(2026, 6, 12), author_provider_id=oncologist, recipient_provider_id=gp,
        content="Dear Dr Grey,\nRobin's June CT shows a good response in the liver. A small new lung nodule will be discussed at MDT.",
    ))
    plan_and_notes.add_clinical_note(db, clinician, p, NewClinicalNote(
        note_type="clinical_note", note_date=date(2026, 9, 14), author_provider_id=oncologist,
        content="Cycle 12. Grade 1 peripheral neuropathy; neutrophils 1.4, proceed at reduced dose.",
    ))
    today = practice_today()
    plan_and_notes.add_next_step(db, secretary, p, NewNextStep(kind="mdt", description="Discuss lung nodule at MDT", due_date=today + timedelta(days=3)))
    plan_and_notes.add_next_step(db, secretary, p, NewNextStep(kind="rescan", description="Restaging CT chest, abdomen and pelvis", due_date=today + timedelta(days=60)))
