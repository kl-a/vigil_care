# Changes for Design Doc v1.2

> **Status: applied in [Vigil_Design_Document.md](Vigil_Design_Document.md) v1.2 (2026-09-24).** Kept as the change record against [v1.1](archive/Vigil_Design_Document_v1.1.md).

Decisions from the design-grilling sessions. Terms follow [CONTEXT.md](../CONTEXT.md).

## Privacy & ingestion
- **The privacy boundary is the Practice Boundary (the practice's own machines), not a single device** ([ADR 0001](adr/0001-deidentify-before-leaving-practice.md)). Rewrite §4 invariant 4 and the §7 flow as follows:
  1. Local OCR runs first.
  2. PII is located and the page is masked.
  3. Only masked pages go to the cloud VLM, tagged with a one-off request ID.
  4. A local ledger maps each request ID back to its Document.
- **Cloud escalation starts in on-click mode** ([revisit-later.md](revisit-later.md) #2).
- **No PyMuPDF.** Use pypdfium2 + pikepdf, and burn in redactions by rendering each page to an image ([ADR 0002](adr/0002-no-agpl-pdf-libraries.md)).
- **Keep the Original, encrypted; OCR and display use the Working Copy** (at most 300 dpi, greyscale, deskewed).
- **Add Held Documents** as a Document state, shown in the Patient Summary's Open Items.
- **Build our own redaction UI:** react-pdf + react-konva on the frontend, burn-in on the server. The same component serves Redaction QA and Extraction Review.

## Review & Verification
- **The unit of review is the Extracted Fact, not the Extraction.** Move `review_status` down to the fact level.
- **Verification is human only**, recorded with User, Job Title and time. Who can verify what:

| Value | Clinician | Trial coordinator | Secretary |
|---|---|---|---|
| Patient Identity, Care Team, Document Type, redaction review | ✅ | ✅ | ✅ |
| Labs, Medications, Comorbidities, Findings | ✅ | ✅ | ❌ |
| Biomarkers, Treatment Courses | ✅ | ✅ | ❌ |
| Diagnosis, Stage, Recurrence attribution, Response Assessment overrides | ✅ | ❌ | ❌ |

- **Separate User from Provider.** Add a `user` table with Job Title (fixed list in v1), optionally linked to a Provider record. Replace the `trial_coordinator` Care Team role with a "trial-site contact" role (an external Provider).
- **Numeric facts read by a VLM** are cross-checked against the classic OCR text for the same region. If they disagree, the fact is forced to low confidence.

## Clinical model
- **Diagnosis:** one per primary cancer, with Stage fixed at diagnosis, a current Disease Extent, and Recurrences. Each Recurrence records its site and linked biopsy report, and is attributed to its Diagnosis by a clinician.
- **Cancer Type** carries no subtype. Biomarkers are kept in full history with specimen and date; the latest is current, and disagreements between results are flagged.
- **Treatment Course** (systemic, surgery or radiation) replaces `therapy_line` as the umbrella. A Line of Therapy number applies only to advanced/metastatic systemic courses. A Regimen belongs to a systemic Course; each cancer-drug Medication points to its Course.
- **Remove `lesion` and `lesion_measurement`.** Replace them with Finding (per imaging study) and Response Assessment (per Diagnosis, from the radiology report or clinician-entered).
- **Rename the match states:** trial level = Potentially Eligible / Needs Information / Excluded; criterion level = Met / Not Met / Unknown.
- **Comorbidities** are extracted from all letters, GP letters included, with active or resolved status, and reconciled like Medications.
- **Management Plan** is quoted verbatim, plus Next Steps entered by hand (§19.2 closed). **Letter drafting is out of v1** (§19.3 closed). **eviQ is checked weekly**, and every protocol shows its version date (§19.4 closed).
- **Replace the §10.3 matching rule** with: Cancer Type + Disease Extent/intent + *next* Line of Therapy + Biomarkers. A match is a Treatment Option.
- **Pseudonym is only the reference printed on de-identified exports.** The local UI shows real names, so drop `patient.display_name` as a pseudonym.
- **Replace §9.1.1 standalone de-identification with Redaction Jobs**, which keep the Originals, the redacted outputs and the audit trail, with an optional link to a Patient.
- **A Match Run targets one Diagnosis**, preselected when the Patient has only one active. Whole-person criteria use the full Clinical Record.
- **Match Runs never change once made.** A run becomes Stale when the Clinical Record changes, the trial data refreshes, or it is more than a month old. Stale runs stay viewable, with a re-run prompt.
- **§8 schema induction is out of v1.** Unrecognised Documents are held.
- **Drop the generic `observation` table.** PET and bone-scan facts become Findings; surgical and radiation details go on the Treatment Course; anything else that doesn't fit makes the Document Held.
- **Open Items** appear per Patient on the Patient Summary and practice-wide on the Dashboard, filterable by type and by who can act on them.
- **Exports:** every export is either Identified or De-identified, chosen explicitly with no default. The User signs off on it and sends it themselves; the log records User, recipient, time and kind.
- **PBS terms:** per-drug, per-indication PBS Listing (Unrestricted / Restricted / Authority Required / Not Listed); per-option PBS Coverage (Fully / Partially / Not Covered).

- **No hard deletes by Users.** Soft delete with a reason, recorded like a Verification. A misfiled Document is moved to the right Patient, and its Extracted Facts are withdrawn and re-reviewed there. Retention periods: [revisit-later.md](revisit-later.md) #15.

## Environments
- **dev:** development work; synthetic data only.
- **test:** runs only the unit tests and end-to-end tests against the Reference Set.
- **prod:** real use by the practice. **Not part of v1**, which ships dev and test only.
- v1 runs the full set of guardrails even though its data is synthetic.
- Synthetic patients live only in dev and test, so the `is_synthetic` flag in prod is dropped.

## Deployment & access
- **The MVP is built local but ready to move to Azure** ([ADR 0003](adr/0003-local-mvp-with-cloud-seams.md)): storage, database, OCR/VLM worker, job queue, keys and login each sit behind a swappable interface. No multi-tenancy.
- **Every Patient, User and Document belongs to a Practice** in the MVP data model, even though there's only one. Access Grants and the Combined View are deferred ([revisit-later.md](revisit-later.md) #13).
- **Within a Practice, every User sees all its Patients** (keeps §18.3).
- **Logins:** local accounts with 2FA (authenticator app), a 10-minute inactivity lock, and re-authentication before clinician-only Verifications. There is also a **dev login** that bypasses all of this; it exists **only in the dev environment** and must be impossible to enable in test or prod (compiled out or refused at startup). End-to-end tests in test use the real login.
- **Backups:** local encrypted backup with a tested restore in the MVP. The offsite copy comes with the Azure move.
- **G7 offline** is kept for the MVP only because it comes free with running locally; don't design for it.

## Quality
- **Add the Reference Set and the gates** in [quality-gates.md](quality-gates.md).
- **Hardware options** are in [hardware-options.md](hardware-options.md).
