# Vigil

A local-first clinical decision support tool for a single oncology practice. It turns patient documents into a structured clinical record and surfaces standard-of-care treatments, PBS drug information and clinical trials for the clinician to review. The clinician decides.

## Language

### Patients & privacy

**Practice**:
A clinical practice using Vigil; the organisation that holds its Patients' records. The MVP serves one Practice.
_Avoid_: Tenant, clinic, customer (in domain language)

**Patient**:
The actual person under the practice's care; the root of every clinical record.
_Avoid_: Pseudonymous profile, subject, case

**Patient Identity**:
The details that identify a Patient (name, DOB, Medicare number, MRN, address, contact details). Never leaves the Practice Boundary; shown freely inside it.
_Avoid_: PII record, demographics

**Pseudonym**:
The stable reference for a Patient printed on de-identified exports (e.g. "VG-0042"), so a receiving centre can quote it back. Not used inside Vigil, where the real name is shown.
_Avoid_: Display name, alias, token

**Practice Boundary**:
The privacy boundary: infrastructure the practice controls. Today that's its own machines on its own network (workstation, GPU worker, local server); later, its own Azure tenant in an Australian region. Identifiable data may move within it but never beyond it. Third-party processing (e.g. a cloud VLM) is always outside.
_Avoid_: The device, local machine, on-prem, Practice Environment

### People

**User**:
A person who operates Vigil: a clinician, trial coordinator, secretary or developer admin. Every action in Vigil is attributed to a User.
_Avoid_: Account, operator

**Job Title**:
A User's role: clinician, trial coordinator, secretary or developer admin. Recorded as it stood at the time of every Verification. A developer admin configures and supports Vigil (Users, settings, troubleshooting) but can never see Patient data or verify anything.
_Avoid_: Role (reserved for Care Team roles), permission level

**Provider**:
A clinician involved in a Patient's care, whether at the practice or external (e.g. referring GP, surgeon, trial-site contact). A User may also be a Provider.
_Avoid_: Doctor (as the general term), clinician (for the record)

**Care Team**:
The Providers involved with one Patient, each in a role (treating oncologist, referring GP, surgeon, trial-site contact, …).
_Avoid_: Patient providers, contacts

**Verification**:
A User's sign-off that a value is correct, recorded with their name, Job Title and time. Only a human can verify; some values (Diagnosis, Stage, Recurrence attribution, Response Assessment overrides) need a clinician.
_Avoid_: Validation, approval, adversarial check

### Documents & extraction

**Document**:
One uploaded file belonging to a Patient.
_Avoid_: File, upload, record

**Original**:
The Document exactly as uploaded, kept encrypted as the source of truth.
_Avoid_: Raw file, master

**Working Copy**:
A normalised version of the Original (deskewed, greyscale, at most 300 dpi) used for OCR and display.
_Avoid_: Processed file, thumbnail

**Document Type**:
The classified kind of a Document (e.g. CT report, histopathology report, GP letter), which determines what can be extracted from it.
_Avoid_: Test type, doc class

**Extraction**:
One run of the extractor over a Document.
_Avoid_: Parse, extraction result (for a single value)

**Extracted Fact**:
One candidate clinical statement produced by an Extraction, with its source location and confidence. The unit of review: each is accepted, edited or rejected on its own.
_Avoid_: Field, extracted value, extraction (for a single value)

**Clinical Record**:
The accepted facts about a Patient. Only accepted Extracted Facts and directly entered data are in it.
_Avoid_: Profile, chart, EMR

**Redaction Job**:
A standalone de-identification of one or more files (e.g. results for a trial portal) outside the normal Document pipeline. Keeps the Originals, the redacted outputs and the audit trail, and may be linked to a Patient. Unlinked jobs wait in a list to be filed.
_Avoid_: Export, standalone document

**Held Document**:
A Document kept only as its image, with no Extracted Facts, awaiting manual review or manual data entry. Either the pipeline holds it when it can't read the Document reliably, or a User holds it on purpose.
_Avoid_: Failed document, unprocessed scan

### Exports

**Identified Export**:
A report carrying full Patient Identity (e.g. a referral or Patient Summary printout for another clinician), signed off by the User who then sends or prints it. Vigil never sends it.
_Avoid_: Report (unqualified), referral pack

**De-identified Export**:
A report or file with Patient Identity removed and labelled with the Pseudonym (e.g. a trial-portal submission), signed off by the User who sends it.
_Avoid_: Redacted report, anonymised export

### Disease

**Diagnosis**:
One primary cancer in a Patient. A Patient may have several.
_Avoid_: Condition, disease (unqualified)

**Recurrence**:
A return of an existing Diagnosis's cancer at a recorded site (local, regional or distant), attributed to that Diagnosis by a clinician, usually on the strength of a biopsy report. Until attributed it is a Suspected Recurrence; if the biopsy shows a different cancer, it is a new Diagnosis instead.
_Avoid_: Relapse (as a separate record)

**Stage**:
The formal staging of a Diagnosis at the time of diagnosis. Never changes afterwards.
_Avoid_: Current stage

**Disease Extent**:
Where a Diagnosis stands now: localised, locally advanced or metastatic. Changes with Recurrences and Response Assessments.
_Avoid_: Current stage, status

**Cancer Type**:
The site-and-histology category of a Diagnosis (e.g. breast, NSCLC, melanoma). Carries no molecular subtype.
_Avoid_: Tumour type, subtype

**Biomarker**:
A molecular, genomic or IHC result for a Diagnosis, tied to its specimen and date (e.g. EGFR exon 19 deletion, HER2 3+, PD-L1 TPS 60%). Every result is kept; the most recent is current, and disagreements between results are surfaced, never silently resolved. Subtypes are derived from Biomarkers.
_Avoid_: Molecular result, marker, mutation (as the general term)

**Comorbidity**:
Any non-cancer condition a Patient has or has had, marked active or resolved. Includes past procedures only when clinically relevant.
_Avoid_: PMHx, past medical history (as a record name), condition (unqualified)

### Treatment

**Treatment Course**:
Any course of systemic, surgical or radiation treatment given for a Diagnosis.
_Avoid_: Therapy line (as the umbrella term), treatment episode

**Regimen**:
The planned set of drugs of a systemic Treatment Course (e.g. carboplatin + pemetrexed). May be modified during the Course.
_Avoid_: Protocol (unless meaning an eviQ Treatment Protocol)

**Medication**:
One drug a Patient takes or has taken, from any source. A cancer drug's Medication points to its Treatment Course; stopping one drug changes the Medication, not the Course.
_Avoid_: Drug (for the patient-specific record), prescription

**Treatment Protocol**:
A standard-of-care protocol published by eviQ, with its intent, line, drugs and Biomarker requirements, and the eviQ version it was taken from.
_Avoid_: Regimen (for the published protocol), guideline

**Treatment Option**:
A Treatment Protocol that matches a Diagnosis on Cancer Type, Disease Extent and intent, next Line of Therapy, and Biomarkers. Shown for the clinician to consider, never as a recommendation.
_Avoid_: Recommendation, suggested treatment

**Management Plan**:
The treating clinician's stated plan for a Patient, quoted verbatim from the most recent letter with a link to its source. Vigil never rewrites it.
_Avoid_: Care plan, treatment plan

**Next Step**:
A dated item a User adds alongside the Management Plan (e.g. re-scan date, MDT date, trial window). Feeds Open Items.
_Avoid_: Task, action item

**Line of Therapy**:
The ordinal given only to systemic Treatment Courses in the advanced or metastatic setting. Adjuvant and neoadjuvant courses, surgery and radiation get no line number.
_Avoid_: Surgical line, radiation line

### Imaging

**Finding**:
One observation reported in a single imaging study, including PET and bone scans (e.g. "segment VI liver lesion, 23 mm", "SUVmax 8.2 right hilum"). Not linked across studies.
_Avoid_: Lesion (as a tracked entity), target lesion, Observation

**Response Assessment**:
The stated direction of a Diagnosis at a point in time: responding, stable or progressing. Taken from the radiology impression by default; a clinician may record or override it. Not attributed when the source doesn't say which Diagnosis it concerns.
_Avoid_: Trend, status

**PBS Listing**:
A drug's PBS status for a specific indication: Unrestricted, Restricted, Authority Required or Not Listed.
_Avoid_: PBS-listed (without an indication), PBS status

**PBS Coverage**:
How much of a Treatment Option the PBS subsidises: Fully Covered, Partially Covered (naming the drugs that aren't) or Not Covered.
_Avoid_: PBS-covered (unqualified)

### Trial matching

**Match Run**:
One evaluation of a Patient against the current trial data for a chosen target Diagnosis, as a snapshot that never changes once made. Criteria about "the cancer" use the target Diagnosis; whole-person criteria (other cancers, Comorbidities, ECOG, organ function) use the whole Clinical Record.
_Avoid_: Match, search

**Stale**:
A Match Run that needs re-running because its Patient's Clinical Record has changed, the trial data has refreshed, or it is more than a month old. Still viewable.
_Avoid_: Expired, outdated

**Match State**:
The trial-level outcome for a Patient: **Potentially Eligible**, **Needs Information** or **Excluded**.
_Avoid_: Eligible, Ineligible, Uncertain, Eligible-looking

**Criterion Result**:
The outcome of one eligibility criterion for a Patient: **Met**, **Not Met** or **Unknown**.
_Avoid_: PASS/FAIL, Uncertain criterion

### Work

**Open Item**:
Anything about a Patient that needs a User's attention: a Held Document, an Extracted Fact awaiting review, a Needs Information criterion, a Next Step, a Stale Match Run, conflicting Biomarker results. Shown per Patient and practice-wide.
_Avoid_: Task, alert, to-do

### Sharing across Practices (post-MVP)

**Holding Practice**:
The Practice that recorded a given fact or Document. Only it can edit or correct that item.
_Avoid_: Owner, source practice

**Access Grant**:
Read-only permission for another Practice to see a Patient's items from the Holding Practice, within a chosen scope, backed by Sharing Consent. Expires and can be revoked.
_Avoid_: Share, permission, link

**Sharing Consent**:
The Patient's written, signed consent to an Access Grant, uploaded and logged in Vigil.
_Avoid_: Verbal consent, implied consent

**Combined View**:
One view of a Patient across all Practices that hold records about them, where every item shows its Holding Practice and is read-only to the others. Conflicting items are shown side by side, never merged silently.
_Avoid_: Merged record, master record, shared profile

### Quality

**Reference Set**:
A fixed collection of synthetic documents with known correct Extracted Facts and known PII, used to check that any change of model, prompt or pipeline still performs to standard.
_Avoid_: Test set, benchmark (unqualified), golden data
