# Vigil: Frontend Design Brief

> **For Claude Design.** Produce a clickable **HTML/JS scaffold** of the Vigil web app from this brief. It will later be ported into the real frontend (Next.js 14 App Router + TypeScript + Tailwind CSS + shadcn/ui), so build with those conventions in mind (see §9).
>
> **Companion docs:** [Vigil_Design_Document.md](Vigil_Design_Document.md) v1.3 (the full product spec; §5 is the screen inventory) and [CONTEXT.md](../CONTEXT.md) (the glossary). **Use glossary terms exactly** in all UI copy.

---

## 1. What Vigil is

Vigil is a clinical decision support tool for medical practices. It's built as a general **Core** plus pluggable **Specialty Modules**, and **Oncology** is the first and only module in the MVP (design doc §4.1). It turns patient documents (scans, faxes, phone photos, PDFs) into a verified, structured **Clinical Record**, and shows the clinician standard-of-care **Treatment Options**, PBS drug information and clinical trials to consider. **The clinician decides; Vigil only informs.** This rule shapes every word and colour in the UI (§6).

Its most-used screen is the **Patient Summary**: the one page an oncologist opens before walking into a consultation.

## 2. Who uses it

Every person logs in individually. What they see depends on their **Job Title**:

| Job Title | Typical tasks | Sees Patient data? |
|---|---|---|
| **Clinician** (oncologist) | Reads Patient Summaries, reviews and signs off facts (only a clinician can sign off a Cancer Diagnosis, Stage, Recurrence), runs trial matches, signs off exports | Yes |
| **Trial coordinator** | Uploads documents, reviews lab/medication/biomarker facts, runs trial matches, prepares trial-portal redactions | Yes |
| **Secretary** | Registers Patients, manages Providers and Care Teams, uploads and redacts documents, manages Users | Yes (can't sign off clinical values) |
| **Developer admin** | Configures Vigil, manages Users, troubleshoots via system status | **Never.** Patient screens don't exist for this role. |

Primary device: a **desktop** at the practice (1366–1920 px wide). Document Upload must also work on a **tablet** (photographing letters). Phones are out of scope for the MVP.

## 3. Design principles

1. **Consultation-ready at a glance.** Dense, scannable, calm. Paycalculator.com.au-level information density, with better typography. No marketing gloss, illustrations or playfulness.
2. **Every value shows where it came from.** Clinical values carry a source link (the Document and page it came from) and a verification mark (who signed it off, their Job Title, when).
3. **State is always explicit.** Pending vs verified, current vs Stale, masked vs unmasked, Identified vs De-identified. Never leave the user guessing.
4. **Never imply a recommendation.** "Potentially Eligible", never "Eligible". "Treatment Option", never "Recommended treatment" (§6).
5. **Privacy is visible.** Anything leaving the practice (cloud reads, exports) is previewed first and clearly labelled.
6. **Colour never works alone.** Every state uses colour **plus** an icon **plus** a text label (accessibility and printing).
7. **Fail loudly, safely.** Held Documents, Unknown criteria and disagreements are surfaced as Open Items, not hidden.

## 4. Visual language

### 4.1 Design tokens

Define tokens as CSS custom properties (shadcn/ui convention: HSL values, `--background`, `--foreground`, `--primary`, `--muted`, `--border`, `--ring`, …). Provide a **light theme (default)** and a **dark theme**.

| Token group | Direction |
|---|---|
| Brand / primary | A calm clinical **teal/blue** (e.g. teal-700 range). Used for primary actions and focus rings only. |
| Neutrals | Cool greys; white or near-white surfaces; subtle 1px borders. |
| **State: positive** | Green: Potentially Eligible, Met, Fully Covered, Unrestricted, Verified, leak check passed |
| **State: caution** | Amber: Needs Information, Unknown, Partially Covered, Restricted, Authority Required, pending review, Stale, low confidence |
| **State: negative** | Red: Excluded, Not Met, Not Covered, Not Listed, numbers disagree, leak check failed, Held |
| **State: neutral** | Grey: not assessed, context, withdrawn, soft-deleted |
| **Privacy** | Violet: anything about data leaving the Practice Boundary (cloud pre-flight, De-identified Export, Pseudonym) |
| **Environment** | DEV = orange badge; TEST = purple badge; always visible in the top bar |

Contrast must meet **WCAG 2.2 AA** in both themes.

### 4.2 Typography
- A UI sans with **tabular numerals** for all clinical values (e.g. Inter with `font-variant-numeric: tabular-nums`, or IBM Plex Sans).
- Monospace (e.g. JetBrains Mono / IBM Plex Mono) for identifiers: Medicare numbers, MRNs, Pseudonyms, request IDs, item codes.
- Base size 14px for dense screens; 13px in data tables; headings restrained (max 20–24px).

### 4.3 Density & layout
- 4px spacing grid. Compact table rows (32–36px).
- 12-column content grid inside the app shell; content max-width ~1600px.
- Cards with small radius (6px), 1px borders, minimal shadow.

### 4.4 Iconography
- **Lucide** icons (the shadcn/ui default). Each state has one fixed icon, e.g. `check-circle` Met, `help-circle` Unknown, `x-circle` Not Met, `alert-triangle` numbers disagree, `lock` masked, `cloud-upload` leaves the practice, `pause-circle` Held.

## 5. App shell & navigation

```
┌──────────────────────────────────────────────────────────────────────────┐
│ [Vigil]  🔍 Search patients…      [DEV]   ● VLM worker ok   Dr A (Clinician) ▾ │  ← top bar
├───────────────┬──────────────────────────────────────────────────────────┤
│ Dashboard     │  Breadcrumb: Patients / Jane Citizen / Summary            │
│ Patients      │ ┌──────────────────────────────────────────────────────┐ │
│ Review queue ⑫│ │ Patient header (when inside a Patient)               │ │
│ Documents     │ ├──────────────────────────────────────────────────────┤ │
│ Redaction     │ │ Tabs: Summary · Clinical Data · Documents ·          │ │
│  └ Jobs       │ │       Medications · Treatment Options · Trials ·      │ │
│ Trials        │ │       Exports                                        │ │
│ PBS lookup    │ │                                                      │ │
│ ───────────   │ │ Content                                              │ │
│ Providers     │ │                                                      │ │
│ Users         │ └──────────────────────────────────────────────────────┘ │
│ Settings      │                                                          │
│ System status │                                                          │
└───────────────┴──────────────────────────────────────────────────────────┘
```

- **Left sidebar**, collapsible to icons. Counts on Review queue and Dashboard (Open Items).
- **Top bar:** global Patient search, **environment badge**, VLM worker status dot, the current User with Job Title, and a menu with Lock now, Re-authenticate and Log out.
- **Patient context:** inside a Patient, a sticky **Patient header** shows name, DOB/age, MRN, Pseudonym (small, violet, mono), Conditions in focus as chips (Oncology: Cancer Diagnoses with Stage), Open Items count, and Care Team primary.

**Navigation by Job Title:**

| Item | Clinician | Trial coord. | Secretary | Dev admin |
|---|---|---|---|---|
| Dashboard (Open Items) | ✅ | ✅ | ✅ | ❌ (sees System status instead) |
| Patients, Review queue, Documents, Redaction, Redaction Jobs, Trials, PBS | ✅ | ✅ | ✅ | ❌ hidden |
| Providers | ✅ | ✅ | ✅ | ❌ |
| Users | ✅ | ❌ | ✅ | ✅ |
| Settings | ✅ | ❌ | ❌ | ✅ |
| System status | ✅ | ✅ | ✅ | ✅ (their home page) |

The scaffold should include a **role switcher** (dev-only affordance in the top bar) to preview each Job Title's navigation. *From Stage 1 this becomes the dev login: you pick a seeded User, so permissions are real, not previewed.*

**Growing the UI stage by stage (design doc §15):**
- **Stage flags.** Each screen and Patient tab has the build stage that ships it and a `built` flag. The navigation shows a screen only when it is **built** (no longer a placeholder) **and** its stage has shipped (`SHIPPED_STAGE` in `frontend/lib/stages.ts`, raised when that stage's demo is ready). Everything else is reachable only through the toggle below. In dev, a **"Show upcoming screens"** toggle reveals the rest as placeholders labelled with their stage. The table above is the end state.
- **Section by section.** Screens with sections (Patient Summary, Patient Overview, Clinical Data, the Dashboard) render only the sections whose data exists. The Patient Summary in Stage 5, for example, has Registration, Diagnosis, Treatment and Medical History; Most Recent Results arrive with labs. Sections come from the section registry, so the Oncology module adds its own.
- **Stage demos.** Each stage ends with a scripted demo against the synthetic demo Practice (§10), so every screen needs realistic empty, loading and populated states from the start.

## 6. Voice & terminology

Use the glossary terms exactly, with capitalisation as shown.

| Use | Never use |
|---|---|
| Potentially Eligible / Needs Information / Excluded | Eligible, Ineligible, Uncertain, Match, Qualifies |
| Met / Not Met / Unknown | Pass / Fail |
| Treatment Option | Recommendation, Suggested treatment, Best treatment |
| Extracted Fact (pending) / Verified | Approved, Validated, Confirmed by AI |
| Held Document | Failed, Error document |
| Response Assessment: Responding / Stable / Progressing | Trend, Improving/Worsening |
| Stage (at diagnosis) and Disease Extent (now) | Current stage |
| Identified Export / De-identified Export | Report (on its own), Anonymised |
| PBS Listing (per indication) / PBS Coverage | PBS-listed (with no indication) |

- **Tone:** plain, factual, clinical, Australian English (e.g. "tumour", "haematology", "anaesthetic").
- **Buttons are verbs:** "Accept fact", "Run match", "Sign off and export", "Enhance with cloud".
- **Disclaimers:** Treatment Options and the Match Board carry a persistent one-line note: "For clinician review. Vigil does not make treatment decisions."

## 7. Component inventory

Build each as a reusable component in the scaffold, with a **component gallery page** showing every variant and state.

| Component | Variants / notes |
|---|---|
| **StateBadge** | One component driven by a `kind` + `value` map: MatchState, CriterionResult, PbsListing, PbsCoverage, ConfidenceBand (high/medium/low), ReviewStatus (pending/accepted/edited/rejected/withdrawn), Stale, Held (with reason), LeakCheck (pass/fail), ResponseDirection. Always icon + label + colour. |
| **VerificationMark** | Small tick with tooltip: "Verified by Dr A Smith (Clinician), 24 Sep 2026 10:14". Pending variant is an amber dot. |
| **SourceLink** | "📄 CT chest 02 Sep · p2", opening the page viewer at the exact region. |
| **BiomarkerChip** | Name + result (e.g. `EGFR ex19del +`, `PD-L1 60%`). A discordance flag (amber ⚠) opens the history. |
| **CancerDiagnosisBlock** *(Oncology section)* | Cancer Type, histology, Stage (at dx), Disease Extent (now), BiomarkerChips, Recurrences (confirmed/suspected). |
| **PageViewer** ⭐ | **The most important component.** A page image with zoom/pan, rotate, page thumbnails, and an overlay of **boxes**. Box types: PII (coloured by entity type, auto/manual) and source highlights for Extracted Facts. Tools: draw rectangle, select OCR words, delete/restore box, relabel. Shared by Redaction QA and Extraction Review. |
| **StatusStepper** | Document pipeline: Uploaded → OCR → PII masked → Classified → Extracted → In review → Complete; or **Held** (red branch with reason). |
| **FactCard / FactRow** | Fact kind, value, unit, date, ConfidenceBand, "numbers disagree" flag, "needs clinician" lock, SourceLink, and Accept / Edit / Reject actions. Keyboard: `A` accept, `E` edit, `R` reject, `J/K` next/previous. |
| **OpenItemRow** | Icon by type, Patient, description, due/age, "who can act" chip, action button. |
| **DataTable** | TanStack-style: sortable, filterable, column visibility, sticky header, compact rows, row-level SourceLink. |
| **Sparkline / TrendChart** | Lab trends with reference-range band and flagged points; minimal axes. |
| **Timeline** | Treatment Courses as horizontal bars (systemic/surgery/radiation) with Line of Therapy markers; Recurrences and Response Assessments as markers. |
| **ReauthDialog** | "Confirm it's you": password or 6-digit code. Shown before clinician-only sign-offs. |
| **SignOffDialog** | For exports and Job Title changes: summary of what's being signed, recipient, kind (Identified / De-identified, **no default**), a checkbox confirmation, then Sign off. |
| **ReasonDialog** | Required free-text reason for soft delete, move and hold. |
| **PreflightPanel** | Violet panel showing exactly what would leave the practice: masked page thumbnails, pseudonymised text, request ID, destination model. "Send" / "Cancel". |
| **StaleBanner** | Amber banner with the reason (record changed / new trial data / older than 30 days) and a Re-run button. |
| **EnvironmentBadge** | DEV / TEST. |
| **LockScreen** | Full-screen blur over the current page with an unlock form; preserves state. |
| **EmptyState / LoadingSkeleton / ErrorState** | For every list and panel. |

## 8. Screens

Numbering follows design doc §5. For each screen: purpose, layout, key content, actions, and states the scaffold must show. **Use the synthetic data in §10.**

### Account screens (the Login screen's real 2FA flow ships in Stage 13; until then only the dev login is used)

**1. Login**
- Centred card: username, password → then the 6-digit 2FA code.
- First-login variant: 2FA enrolment with a QR code placeholder and a manual key.
- DEV only: an orange "Dev login" button with a role picker.
- States: wrong password, wrong code, rate-limited ("Try again in 60s"), account deactivated.

**18. User Management**
- Table: name, username, Job Title (badge), linked Provider, 2FA status, active, last login.
- Actions: New User (drawer form), Deactivate (ReasonDialog), Reset password, Reset 2FA, Change Job Title (SignOffDialog).
- A trial coordinator sees a 403 empty state.

**17. Provider Management**
- Table with filters (specialty, internal/external), search.
- Provider drawer: details, and "Patients involved with" (role, dates).
- Actions: New Provider, Edit, Soft delete (ReasonDialog).

**3. Patient List**
- Search, Cancer Type filter.
- Table: name, DOB/age, MRN, Cancer Type(s), Disease Extent, #Documents, #Open Items, last updated.
- "New patient" opens the Patient form: Patient Identity fields (name, DOB, Medicare + IRN, IHI, MRN, address, phone, mobile, email, next of kin). The Pseudonym is auto-generated and shown read-only after save.

**4. Patient Overview**
- Patient header plus tabs.
- Overview content: Conditions list, then **sections from active Specialty Modules** (Oncology: CancerDiagnosisBlocks, ECOG badge, CNS status panel), plus Core sections: Treatment Course Timeline, key lab sparklines, **Care Team** card (role, Provider, dates, primary), Open Items.

**Developer admin home: System status** *(from design doc §6.4)*
- Tiles: DB, VLM worker, job queue depth, last PBS/eviQ/trial refresh, last backup + restore test.
- Tables: pipeline runs (status, kind, timings, error, **IDs only**) and refresh logs.
- **No Patient names anywhere.**

### Core clinical screens

**15. Patient Summary (★ primary screen)**
- A single scrolling page in a 2- or 3-column grid, with a print stylesheet.
- Sections in this order, each with "Last updated · SourceLink":
  1. Registration: identity block.
  2. Diagnosis *(Oncology section)*: one CancerDiagnosisBlock per Cancer Diagnosis.
  3. Most Recent Results: bloods table with flagged values and sparklines; latest scans with Response Assessment badge and key Findings.
  4. Recent Treatment: Treatment Courses in the last 6 months, current Regimen, Line of Therapy, best response.
  5. Clinical Notes: latest note, latest letter to referrer.
  6. Management: the Management Plan quoted verbatim (blockquote style, "Quoted from letter 12 Sep" link) plus Next Steps with due dates.
  7. Medical History: Comorbidities (the other Conditions, active/resolved), current Medications.
  8. Open Items.
- Must fit the key facts **above the fold on a 1440×900 screen**.

**9. Clinical Data Viewer**
- Core sub-tabs: Conditions / Labs / Imaging & Findings / Treatment Courses. Oncology module sub-tabs: Response Assessments / Biomarkers / Performance Status / CNS.
- Labs: analyte picker, TrendChart with reference band, DataTable.
- Biomarkers: full history grouped by marker, specimen (primary / metastasis / liquid biopsy) and date, with a discordance callout.
- Every row has a VerificationMark and a SourceLink.

**5. Document Upload**
- Drag-drop zone, "Take photo" (tablet), batch list.
- Per Document: thumbnail, StatusStepper, Document Type badge, actions ("Process", "Hold", "Enhance with cloud" → PreflightPanel).
- States: in progress, Held (each reason: unreadable / unknown type / PII uncertain / held by User), complete.

**7. Redaction QA**
- Split: PageViewer (left, ~65%), entity list (right) grouped by type with auto/manual and confidence.
- Toolbar: Draw box, Select words, Relabel, Delete/Restore, Rotate, Zoom.
- Footer: "Burn in", then a leak-check result (pass ✓ / fail with reasons).
- **Pre-flight tab:** PreflightPanel.

**8. Redaction Jobs**
- Job list with an "Unlinked" filter chip, status and file count.
- Job detail: files (each opens Redaction QA), "Link to Patient" picker, "Download De-identified Export" (SignOffDialog).

**6. Extraction Review**
- Split: PageViewer with source highlights (left); FactRows grouped by fact kind (right).
- Filters: pending only, low confidence, numbers disagree, needs clinician.
- "Accept all high-confidence" is disabled for any fact with numbers disagree.
- Clinician-only facts trigger the ReauthDialog.
- A secretary sees clinical facts read-only with a "Needs clinician/coordinator" lock.

**Review queue**
- Practice-wide pending Extracted Facts grouped by Document, filterable by fact kind and by required Job Title.

**10. Medication Manager**
- Tabs: Active / Discontinued / Reconciliation / Change log.
- Active table: generic + brand, dose, frequency, route, indication, category badge, source badge, confidence, VerificationMark, linked Treatment Course.
- Reconciliation cards: "Is 'Norvasc 5mg' the same as 'Amlodipine 5mg'?", with Same / Different / Update existing / Reject. The same pattern is used for Conditions.

**11. Treatment Options**
- Condition selector (Cancer Diagnoses in the MVP). This screen comes from the Oncology module; a module without a Treatment Option source shows no tab.
- Disclaimer line.
- Cards per Treatment Option: protocol name, intent, Line of Therapy, drug list with a PBS Listing badge per drug, a PBS Coverage badge (naming the gap), co-payments, "eviQ ↗", "as of <date>".
- Flags: "Biomarker needed", "Biomarker discordance".
- A stale-data banner when the eviQ refresh failed.

**12. Trial Browser**
- Filters (phase, status, site, condition, drug, distance).
- Trial detail: criteria list, each tagged "Target cancer" or "Whole person"; sites with distance; registry link; last refreshed.

**13. Match Board**
- Target Condition selector (preselected if only one) and "Run match".
- StaleBanner when applicable.
- Three columns: **Potentially Eligible** (green) / **Needs Information** (amber) / **Excluded** (red), with counts.
- Trial card: title, phase, nearest site + distance. Expanding it shows each criterion with a CriterionResult badge, rationale and evidence SourceLink.
- "Diff vs previous run" toggle.
- Disclaimer line.

**14. PBS Drug Lookup**
- Search, then a drug detail: item code (mono), PBS Listing per indication (table), co-payments, prescribing conditions, Safety Net, schedule date.

**16. Exports**
- Template picker, then a **Kind** selector with two large radio cards and no default: "Identified Export: full patient details, for a clinician" and "De-identified Export: Pseudonym only, masked (violet)".
- Live preview (print layout), then the SignOffDialog (recipient, confirmation).
- History table: kind, recipient, signed off by (Job Title), date.

**2. Dashboard**
- Open Items table (practice-wide), filter chips by type and "who can act".
- Side tiles: recent activity, next refreshes, VLM worker status.

**19. Settings**
- **Specialty Modules** section (developer admin only): installed modules with an on/off switch (turning one off opens a SignOffDialog and a note that data is kept, not deleted).
- Sections: Practice details, VLM worker (URL, test connection), Cloud escalation (**On-click only**; automatic mode shown but disabled, marked "Not enabled in this build"), LLM model, confidence thresholds, refresh schedules, trial geographic scope (AU / AU+US+UK+EU / custom), backup status + last restore test.

## 9. Scaffold requirements (the output we want)

- **Stack for the scaffold:** static HTML + vanilla JS (ES modules) + **Tailwind CSS** (CDN build is fine), with shadcn/ui-style tokens and component markup, and Lucide icons. **No backend.** It must open from a local static server.
- **Routing:** a single-page app with hash routes mirroring the future Next.js routes: `#/login`, `#/dashboard`, `#/system`, `#/patients`, `#/patients/:id/summary`, `…/clinical-data`, `…/documents`, `…/medications`, `…/treatment-options`, `…/trials`, `…/exports`, `#/review`, `#/redaction/:docId`, `#/redaction-jobs`, `#/trials`, `#/pbs`, `#/providers`, `#/users`, `#/settings`, `#/components` (the gallery).
- **Section registry (important):** Specialty-specific UI (Oncology blocks, tabs, Summary sections, Clinical Data tabs, Treatment Options) must be **registered by a module manifest**, not hard-coded into Core screens. Core screens render "sections from active modules" slots. Put all Oncology UI in an `oncology/` folder with its own manifest, and include a Settings toggle that switches Oncology off to prove the Core screens still render without it.
- **Structure:** one module per screen and one per component (so each maps 1:1 to a React component later); a single `tokens.css`; a `mock-data/` folder of JSON fixtures (§10); a `state.js` holding the current User and Job Title, with the role switcher.
- **Role-aware:** nav and screens respect §5's visibility table. The developer admin gets a 403 empty state on any Patient route.
- **Interactive enough to review:** drawers, dialogs (Reauth, SignOff, Reason, Preflight), tab switching, the PageViewer drawing boxes on a sample page image, Accept/Reject updating a fact's badge, and the LockScreen triggerable from the user menu.
- **Print stylesheet** for the Patient Summary and the Export preview.
- **Accessibility:** semantic HTML, labelled controls, visible focus rings, keyboard access for the review shortcuts, `aria-live` for status changes.
- **Light + dark theme** toggle.

## 10. Synthetic sample data (use only this; no real people)

- **Practice:** Harbourside Oncology, 1 Example St, Sydney NSW 2000.
- **Users:** Dr Alex Rivera (Clinician), Sam Lee (Trial coordinator), Jordan Park (Secretary), Casey Dev (Developer admin).
- **Patients:**
  1. **Jane Citizen**, DOB 03/04/1962, MRN 1002003, Pseudonym `VG-0042`.
     - Cancer Diagnosis: NSCLC adenocarcinoma, Stage IIIA (dx 2024), Disease Extent **metastatic**.
     - Biomarkers: EGFR exon 19 deletion (2024, primary), **T790M positive (2026, liver met, discordant with 2024 result)**, PD-L1 TPS 5%.
     - Treatment Courses: surgery 2024; adjuvant chemo 2024; Line 1 osimertinib 2025–2026 (best response PR); Line 2 planned.
     - Response Assessment: Progressing (Aug 2026).
     - Other Conditions (shown as Comorbidities): type 2 diabetes (active), knee OA (active), DVT 2019 (resolved).
     - ECOG 1.
     - Match Board: 3 Potentially Eligible, 5 Needs Information, 12 Excluded.
  2. **Sam Example**, DOB 17/09/1975, MRN 1002017, Pseudonym `VG-0043`.
     - Cancer Diagnosis 1: breast, Stage IIA, localised, ER+/PR+/HER2−; adjuvant letrozole ongoing.
     - Cancer Diagnosis 2: melanoma 2023, no evidence of disease (this is the other-malignancy exclusion case).
  3. **Robin Sample**, DOB 29/01/1958, MRN 1002031, Pseudonym `VG-0044`.
     - Colorectal, metastatic, KRAS wild-type, MSI-stable.
     - One **Held Document** (unreadable fax) and 7 pending Extracted Facts, one with "numbers disagree": creatinine 18 vs 1.8.
- **Providers:** Dr Morgan Grey (GP, referring), Dr Taylor Quinn (surgeon), Riley Hart (trial-site contact, Example Cancer Centre).
- **Sample page images:** use grey placeholder "document" images with fake text lines. Draw PII boxes over the name, DOB and Medicare lines.

## 11. Out of scope for the scaffold

Real data or API calls, authentication logic, a PDF rendering engine (use images), charts beyond simple SVG sparklines/trends, and mobile phone layouts.
