"""The single permission check (design doc §6.4). Used by the service layer, not only the UI.

Two kinds of right:
- `may(job_title, permission)`: administrative and Core sign-off actions (manage Users, Settings,
  view Patient data, sign off exports, ...).
- `VerificationRights.can_verify(job_title, fact_kind)`: who may verify each kind of Extracted Fact.
  The Core lists its fact kinds; each Specialty Module contributes its own (the module registry
  combines them, #15).

A developer admin never views Patient data and never verifies anything.
"""

from collections.abc import Mapping
from dataclasses import dataclass
from typing import Literal

from app.core.vocabulary import JobTitle

Permission = Literal[
    "verify_patient_identity",
    "verify_care_team",
    "verify_document_type",
    "review_redaction",
    "hold_document",
    "sign_off_identified_export",
    "sign_off_deidentified_export",
    "manage_users",
    "manage_providers",
    "activate_modules",
    "change_settings",
    "view_patient_data",
    "support_views",
    "start_refresh",
]

_STAFF: frozenset[JobTitle] = frozenset({"clinician", "trial_coordinator", "secretary"})

PERMISSIONS: Mapping[Permission, frozenset[JobTitle]] = {
    # Row 1: Patient Identity, Care Team, Document Type, redaction review, holding a Document.
    "verify_patient_identity": _STAFF,
    "verify_care_team": _STAFF,
    "verify_document_type": _STAFF,
    "review_redaction": _STAFF,
    "hold_document": _STAFF,
    # Rows 5–6: export sign-off.
    "sign_off_identified_export": _STAFF,
    "sign_off_deidentified_export": _STAFF,
    # Rows 7–12.
    "manage_users": frozenset({"clinician", "secretary", "developer_admin"}),
    # The Provider directory is read by everyone signed in (so User Management can link a User to theirs);
    # the staff who work with referrers keep it up to date.
    "manage_providers": _STAFF,
    "activate_modules": frozenset({"developer_admin"}),
    "change_settings": frozenset({"clinician", "developer_admin"}),
    "view_patient_data": _STAFF,
    "support_views": frozenset({"clinician", "trial_coordinator", "secretary", "developer_admin"}),
    "start_refresh": frozenset({"developer_admin"}),
}


def may(job_title: JobTitle, permission: Permission) -> bool:
    return job_title in PERMISSIONS[permission]


class NotAllowed(PermissionError):
    """The actor's Job Title doesn't have the permission. The API answers 403 with the message."""


def require(job_title: JobTitle, permission: Permission, message: str = "Not available for your Job Title.") -> None:
    """Services call this before acting (design doc §6.4: enforced in the service layer)."""
    if not may(job_title, permission):
        raise NotAllowed(message)


@dataclass(frozen=True)
class FactRight:
    """Who may verify one fact kind, and whether they must re-authenticate first (clinician-only rows)."""

    job_titles: frozenset[JobTitle]
    reauthenticate: bool = False


CLINICAL = FactRight(frozenset({"clinician", "trial_coordinator"}))
CLINICIAN_ONLY = FactRight(frozenset({"clinician"}), reauthenticate=True)

# Rows 2–3, Core fact kinds. Oncology's rows live in the Oncology module.
CORE_FACT_RIGHTS: Mapping[str, FactRight] = {
    "lab_result": CLINICAL,
    "medication": CLINICAL,
    "condition": CLINICAL,
    "imaging_study": CLINICAL,
    "finding": CLINICAL,
    "clinical_note": CLINICAL,
    "management_plan": CLINICAL,
    "treatment_course": CLINICAL,
}

# Least to most senior: the minimum Job Title that may verify a fact (extracted_fact.required_job_title).
_SENIORITY: tuple[JobTitle, ...] = ("secretary", "trial_coordinator", "clinician")


class VerificationRights:
    def __init__(self, rights: Mapping[str, FactRight]) -> None:
        self._rights = dict(rights)

    def fact_kinds(self) -> set[str]:
        return set(self._rights)

    def can_verify(self, job_title: JobTitle, fact_kind: str) -> bool:
        """Raises KeyError for a fact kind no active module declared: refuse rather than guess."""
        return job_title in self._rights[fact_kind].job_titles

    def required_job_title(self, fact_kind: str) -> JobTitle:
        return next(title for title in _SENIORITY if title in self._rights[fact_kind].job_titles)

    def needs_reauthentication(self, fact_kind: str) -> bool:
        """True for clinician-only rows. Until Stage 13 the Verification records reauthenticated = false."""
        return self._rights[fact_kind].reauthenticate
