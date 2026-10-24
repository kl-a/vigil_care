"""Oncology's Open Items (#48, design doc §6.3), raised through the module contract only while Oncology is active:

- **Differing Biomarker Results** no clinician has marked Seen since the newest of them ("Seen", clinicians; or
  record a new primary on the Clinical Data tab).
- **Unattributed Response Assessments** ("Attribute", clinicians).
- **New unattributed Findings** in a Patient with a Cancer Diagnosis ("Attribute", clinicians).
- **Suspected Recurrences** ("Confirm" or "Rule out" with why, here; new primary instead on the Clinical Data tab; clinicians).
"""

import uuid
from collections import defaultdict
from collections.abc import Collection
from datetime import date

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.modules.clinical.conditions import condition_summaries
from app.modules.clinical.imaging import new_unattributed_findings
from app.modules.summary.schemas import Choice, OpenItem, OpenItemAction
from app.specialties.oncology import biomarkers, response_assessments
from app.specialties.oncology.access import MODULE_KEY
from app.specialties.oncology.models import CancerDiagnosis, Recurrence, ResponseAssessment

TYPES = ("differing_biomarker_results", "unattributed_response_assessment", "unattributed_finding", "suspected_recurrence")


def _when(day: date | None) -> str:
    return f"{day.day} {day:%b %Y}" if day else "date not recorded"


def open_items(db: Session, practice_id: uuid.UUID, patient_ids: Collection[uuid.UUID] | None) -> list[OpenItem]:
    conditions = condition_summaries(db, practice_id, patient_ids)
    conditions_of: dict[uuid.UUID, list[Choice]] = defaultdict(list)
    for c in conditions:
        conditions_of[c.patient_id].append(Choice(id=c.id, name=c.name))
    cancers = {c.id: c for c in conditions if c.extended_by_module == MODULE_KEY}
    diagnoses = list(db.scalars(
        select(CancerDiagnosis).where(CancerDiagnosis.practice_id == practice_id, CancerDiagnosis.condition_id.in_(cancers))
    )) if cancers else []
    patient_of = {d.id: cancers[d.condition_id].patient_id for d in diagnoses}
    name_of = {d.id: cancers[d.condition_id].name for d in diagnoses}
    diagnoses_of: dict[uuid.UUID, list[Choice]] = defaultdict(list)
    for d in diagnoses:
        diagnoses_of[patient_of[d.id]].append(Choice(id=d.id, name=name_of[d.id]))
    return (
        _differing(db, practice_id, patient_of, name_of)
        + _unattributed_assessments(db, practice_id, patient_ids, diagnoses_of)
        + _new_findings(db, practice_id, patient_ids, set(diagnoses_of), conditions_of)
        + _suspected(db, practice_id, patient_of, name_of)
    )


def _differing(db: Session, practice_id: uuid.UUID, patient_of: dict[uuid.UUID, uuid.UUID], name_of: dict[uuid.UUID, str]) -> list[OpenItem]:
    found = []
    for group in biomarkers.unseen_differing(db, practice_id, patient_of):
        newest = group[-1]
        marker = " ".join(part for part in (newest.name, newest.variant) if part)
        patient = patient_of[newest.cancer_diagnosis_id]
        results = "; ".join(f"{b.result or 'no result'} ({_when(b.collected_on)})" for b in group)
        found.append(OpenItem(
            type="differing_biomarker_results", type_label="Differing Biomarker Results", patient_id=patient,
            title=f"{marker} results differ", detail=f"{name_of[newest.cancer_diagnosis_id]}: {results}", dated=newest.collected_on,
            who="clinician", icon="compare", subject_table="biomarker", subject_id=newest.id,
            actions=[OpenItemAction(
                label="Seen", input="note",
                path=f"/patients/{patient}/cancer-diagnoses/{newest.cancer_diagnosis_id}/biomarkers/{newest.id}/seen",
            )],
        ))
    return found


def _unattributed_assessments(
    db: Session, practice_id: uuid.UUID, patient_ids: Collection[uuid.UUID] | None, diagnoses_of: dict[uuid.UUID, list[Choice]]
) -> list[OpenItem]:
    query = select(ResponseAssessment).where(ResponseAssessment.practice_id == practice_id)
    if patient_ids is not None:
        query = query.where(ResponseAssessment.patient_id.in_(patient_ids))
    counted = response_assessments.counted(list(db.scalars(query)))
    return [
        OpenItem(
            type="unattributed_response_assessment", type_label="Unattributed Response Assessment", patient_id=a.patient_id,
            title=f"Response Assessment not attributed: {a.direction}", detail=f"{response_assessments.SOURCE_WORDS[a.source].capitalize()}, {_when(a.assessed_on)}",
            dated=a.assessed_on, who="clinician", icon="help", subject_table="response_assessment", subject_id=a.id,
            actions=[OpenItemAction(
                label="Attribute", input="choose", field="cancer_diagnosis_id", choices=diagnoses_of.get(a.patient_id, []),
                path=f"/patients/{a.patient_id}/response-assessments/{a.id}/attribute",
            )],
        )
        for a in counted if a.cancer_diagnosis_id is None
    ]


def _new_findings(
    db: Session, practice_id: uuid.UUID, patient_ids: Collection[uuid.UUID] | None, with_cancer: set[uuid.UUID],
    conditions_of: dict[uuid.UUID, list[Choice]],
) -> list[OpenItem]:
    return [
        OpenItem(
            type="unattributed_finding", type_label="New unattributed Finding", patient_id=f.patient_id,
            title="New Finding not attributed: " + ", ".join(part for part in (f.description, f.site, f.laterality) if part),
            detail=f"{f.modality} of {_when(f.study_date)}", dated=f.study_date, who="clinician", icon="scan", subject_table="finding", subject_id=f.id,
            actions=[OpenItemAction(
                label="Attribute", input="choose", field="condition_id", choices=conditions_of.get(f.patient_id, []),
                path=f"/patients/{f.patient_id}/imaging-studies/{f.imaging_study_id}/findings/{f.id}/attribute",
            )],
        )
        for f in new_unattributed_findings(db, practice_id, patient_ids) if f.patient_id in with_cancer
    ]


def _suspected(db: Session, practice_id: uuid.UUID, patient_of: dict[uuid.UUID, uuid.UUID], name_of: dict[uuid.UUID, str]) -> list[OpenItem]:
    if not patient_of:
        return []
    found = db.scalars(
        select(Recurrence).where(Recurrence.practice_id == practice_id, Recurrence.status == "suspected", Recurrence.cancer_diagnosis_id.in_(patient_of))
    )
    items = []
    for r in found:
        patient = patient_of[r.cancer_diagnosis_id]
        where = f"{r.extent.capitalize() if r.extent else 'Extent not recorded'}{': ' + ', '.join(str(s) for s in r.sites) if r.sites else ''}"
        items.append(OpenItem(
            type="suspected_recurrence", type_label="Suspected Recurrence", patient_id=patient,
            title=f"Suspected Recurrence of {name_of[r.cancer_diagnosis_id]}", detail=f"{where}, detected {_when(r.detected_on)}",
            dated=r.detected_on, who="clinician", icon="alert", subject_table="recurrence", subject_id=r.id,
            # "New primary instead" needs the Cancer Diagnosis form: on the Clinical Data tab.
            actions=[
                OpenItemAction(label="Confirm", path=f"/patients/{patient}/recurrences/{r.id}/confirm"),
                OpenItemAction(label="Rule out", input="reason", path=f"/patients/{patient}/recurrences/{r.id}/rule-out"),
            ],
        ))
    return items
