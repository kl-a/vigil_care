# Build Order

> **As of 2026-10-23.** Where the build stands and what comes next. The plan and its rules are in [Vigil_Design_Document.md](Vigil_Design_Document.md) §15. Tickets live in [GitHub Issues](https://github.com/kl-a/vigil_care/issues), grouped into one milestone per stage. Update this file whenever a ticket finishes or the order changes.

**Showing screens:** a screen appears for everyone once it's marked `built` in `frontend/lib/screens.ts` (or its Patient tab) and its stage has shipped. Raise `SHIPPED_STAGE` in `frontend/lib/stages.ts` when a stage's demo is ready, and mark it here.

**How the build is ordered (re-planned 2026-10-23)**
- **The MVP is documents in, Trial Briefing out.** A Patient's documents go in; a Trial Briefing comes out listing the trials that surface, why, and what each matches to (Match State, Site Access, Mechanism, Washout, each Criterion Result with its reason). Everything else (Patient Summary, Open Items, polish, Exports, login hardening) is an addition on top of that core.
- **Agile, not waterfall.** Build the thinnest version that works end to end, then reinforce it iteration by iteration. No stage builds a whole layer to production depth before the next layer exists.
- **Milestones are named after what the demo can do** (MVP-1, MVP-2, …), not after a layer. Every ticket says which step of the MVP it moves.
- **Batches, not stages.** Pick 2–4 tickets, build them on one branch (TDD, CI), one review per batch, a short demo at the end. Playwright screenshots only for UI-heavy tickets; design-doc updates only when a decision changes.
- **No frontend polish or security ceremony on MVP code paths** until the Briefing works: no new Job Title checks, Verification reasons, audit wiring or grants; everything runs as the one dev User. **Kept:** the privacy invariant (nothing patient-derived leaves unpseudonymised; every cloud call is ledgered and User-initiated), synthetic data only, `.env` never committed, the host Postgres never touched.
- **The trial engine is the design doc's, at full tier** (§11): refreshed trial snapshots, criteria parsed into the attribute vocabulary with scope, deterministic pre-filters, LLM adjudication of the rest, three Match States, Stale runs.
- **Login hardening is still required before prod or any real Patient data.**

## Where we are

| Status | Meaning |
|---|---|
| ✅ Done | Merged to `main` |
| 🔨 Built | Committed on its branch, awaiting PR/merge |
| ⏭️ Ready | All blockers done, so it can start now |
| ⏳ Blocked | Waiting on the tickets listed |
| 📋 Outline | Stage planned; tickets written when we get close |
| 🅿️ Parked | Deferred to the backlog |

### Foundation

| Ticket | What | Status |
|---|---|---|
| [#11](https://github.com/kl-a/vigil_care/issues/11) | Walking skeleton: stack, environments, health, app shell, gates harness | ✅ Done ([PR #12](https://github.com/kl-a/vigil_care/pull/12)) |
| [#2](https://github.com/kl-a/vigil_care/issues/2) | Baseline schema, database guardrails, clickable data model | ✅ Done ([PR #21](https://github.com/kl-a/vigil_care/pull/21)) |

### Stage 1 · Front door

**Demo:** sign in as each Job Title and watch the screens change. Add a User and show the audit entry, edit the Practice details, and switch Oncology off and on.

| Order | Ticket | What | Blocked by | Status |
|---|---|---|---|---|
| 1 | [#13](https://github.com/kl-a/vigil_care/issues/13) | Dev login as a seeded User, and demo data | #2 | ✅ Done ([PR #22](https://github.com/kl-a/vigil_care/pull/22)) |
| 2 | [#6](https://github.com/kl-a/vigil_care/issues/6) | Permissions, Verification and User Management basics | #13 | ✅ Done ([PR #23](https://github.com/kl-a/vigil_care/pull/23)) |
| 3 | [#14](https://github.com/kl-a/vigil_care/issues/14) | Practice details in Settings (location moves to the primary Site in #25) | #6 | ✅ Done ([PR #26](https://github.com/kl-a/vigil_care/pull/26)) |
| 3 | [#15](https://github.com/kl-a/vigil_care/issues/15) | Specialty Modules: contract, registry and Settings toggle | #6 | ✅ Done ([PR #26](https://github.com/kl-a/vigil_care/pull/26)) |
| any | [#16](https://github.com/kl-a/vigil_care/issues/16) | Show only built screens, and System status | none | ✅ Done ([PR #23](https://github.com/kl-a/vigil_care/pull/23)) |
| 4 | [#24](https://github.com/kl-a/vigil_care/issues/24) | Practice Memberships: one login, several Practices (data model + dev login; no switcher yet) | #14, #15 | ✅ Done ([PR #27](https://github.com/kl-a/vigil_care/pull/27)) |

### Stage 2 · Patients (shipped: `SHIPPED_STAGE = 2`)

**Demo:** find Jane Citizen and edit her details, then show the audit entry and the encrypted fields in the database. Add her treating oncologist and referring GP. Script so far: [docs/demos/stage-2.md](demos/stage-2.md).

| Order | Ticket | What | Blocked by | Status |
|---|---|---|---|---|
| 1 | [#8](https://github.com/kl-a/vigil_care/issues/8) | Patients with encrypted Patient Identity (includes the key interface) | #6, #24 | ✅ Done ([PR #28](https://github.com/kl-a/vigil_care/pull/28)) |
| 1 | [#7](https://github.com/kl-a/vigil_care/issues/7) | Provider directory | #6, #24 | ✅ Done ([PR #28](https://github.com/kl-a/vigil_care/pull/28)) |
| 1 | [#25](https://github.com/kl-a/vigil_care/issues/25) | Sites: where a Practice sees Patients | #14, #24 | ✅ Done ([PR #28](https://github.com/kl-a/vigil_care/pull/28)) |
| 2 | [#17](https://github.com/kl-a/vigil_care/issues/17) | Soft-delete a Patient | #8 | ✅ Done ([PR #29](https://github.com/kl-a/vigil_care/pull/29)) |
| 2 | [#9](https://github.com/kl-a/vigil_care/issues/9) | Care Team | #8, #7 | ✅ Done ([PR #29](https://github.com/kl-a/vigil_care/pull/29)) |

### Stage 3 · PBS & Support Views (shipped: `SHIPPED_STAGE = 3`)

**Demo:** look up pembrolizumab's PBS Listing per indication. As the developer admin, start a PBS Refresh and follow it in the Support Views. Script: [docs/demos/stage-3.md](demos/stage-3.md).

This stage can run alongside Stage 2.

| Order | Ticket | What | Blocked by | Status |
|---|---|---|---|---|
| 1 | [#18](https://github.com/kl-a/vigil_care/issues/18) | Job queue and Refresh Jobs | #6, #24 | ✅ Done ([PR #34](https://github.com/kl-a/vigil_care/pull/34)) |
| 2 | [#19](https://github.com/kl-a/vigil_care/issues/19) | PBS Refresh | #18 | ✅ Done ([PR #34](https://github.com/kl-a/vigil_care/pull/34)) |
| 2 | [#10](https://github.com/kl-a/vigil_care/issues/10) | Support Views without Patient data (+ no-Patient-data gate) | #18 | ✅ Done ([PR #34](https://github.com/kl-a/vigil_care/pull/34)) |
| 3 | [#20](https://github.com/kl-a/vigil_care/issues/20) | PBS Drug Lookup screen | #19 | ✅ Done ([PR #34](https://github.com/kl-a/vigil_care/pull/34)) |
| 3 | [#30](https://github.com/kl-a/vigil_care/issues/30) | PBS Drug Lookup: the whole PBS Schedule, browsable and clearer | #20 | ✅ Done ([PR #34](https://github.com/kl-a/vigil_care/pull/34)) |
| 4 | [#31](https://github.com/kl-a/vigil_care/issues/31) | Long-running Jobs keep their claim; PBS Refresh logs each API request. Doesn't block the Stage 3 merge; must land before Stage 8 | #18, #19 | ✅ Done ([PR #34](https://github.com/kl-a/vigil_care/pull/34)) |

### Stage 4 · Clinical Record by hand (shipped)

**Demo** (in three parts, each shipped as it's built): build Jane Citizen's record by hand. 4a: breast cancer with Stage, HER2 3+ and ER+ history, a Recurrence. 4b: adjuvant then palliative first-line courses (Line of Therapy derived) and current Medications with PBS links. 4c: the latest bloods, a CT with its Response Assessment, the Management Plan and a Next Step. Show that a secretary can't record a Stage, and that with Oncology switched off the cancer details stay visible read-only. Plan: design doc §15 Stage 4. Script: [docs/demos/stage-4.md](demos/stage-4.md).

| Order | Ticket | What | Blocked by | Status |
|---|---|---|---|---|
| 1 | [#35](https://github.com/kl-a/vigil_care/issues/35) | Entering the Clinical Record by hand (provenance, Verification, reason once per save), and Conditions | none | ✅ Done ([PR #49](https://github.com/kl-a/vigil_care/pull/49)) |
| 1 | [#36](https://github.com/kl-a/vigil_care/issues/36) | Drug reference built from the PBS Schedule (4b) | none | ✅ Done ([PR #49](https://github.com/kl-a/vigil_care/pull/49)) |
| 2 | [#37](https://github.com/kl-a/vigil_care/issues/37) | Cancer Types (MeSH) and Cancer Diagnosis (4a) | #35 | ✅ Done ([PR #49](https://github.com/kl-a/vigil_care/pull/49)) |
| 3 | [#38](https://github.com/kl-a/vigil_care/issues/38) | Biomarkers and Differing Biomarker Results (4a) | #37 | ✅ Done ([PR #49](https://github.com/kl-a/vigil_care/pull/49)) |
| 3 | [#39](https://github.com/kl-a/vigil_care/issues/39) | Recurrences, and **ship 4a** (4a) | #37 | ✅ Done ([PR #49](https://github.com/kl-a/vigil_care/pull/49)) |
| 3 | [#40](https://github.com/kl-a/vigil_care/issues/40) | Treatment Courses and Line of Therapy (4b) | #37 | ✅ Done ([PR #49](https://github.com/kl-a/vigil_care/pull/49)) |
| 4 | [#41](https://github.com/kl-a/vigil_care/issues/41) | Medication Manager, and **ship 4b** (4b) | #40, #36 | ✅ Done ([PR #49](https://github.com/kl-a/vigil_care/pull/49)) |
| 2 | [#42](https://github.com/kl-a/vigil_care/issues/42) | Bloods and other labs (4c) | #35 | ✅ Done ([PR #49](https://github.com/kl-a/vigil_care/pull/49)) |
| 4 | [#43](https://github.com/kl-a/vigil_care/issues/43) | Imaging, Findings and Response Assessments, and **ship 4c** (4c) | #37, #40 | ✅ Done ([PR #49](https://github.com/kl-a/vigil_care/pull/49)) |
| 3 | [#44](https://github.com/kl-a/vigil_care/issues/44) | ECOG and CNS status (4c); ships 4c if #43 is in | #37 | ✅ Done ([PR #49](https://github.com/kl-a/vigil_care/pull/49)) |
| 2 | [#45](https://github.com/kl-a/vigil_care/issues/45) | Plan and notes (4c). 4c ships with the last of #43 and #44, which its demo needs | #35 | ✅ Done ([PR #49](https://github.com/kl-a/vigil_care/pull/49)) |

### Stage 5 · Patient Summary (shipped: `SHIPPED_STAGE = 5`, merged in PR #60)

**Demo:** open the fully recorded demo Patient's Summary as it would look in a consultation, follow a value back to who entered it, then work the Open Items on the Dashboard. Plan: design doc §15 Stage 5. Script: [docs/demos/stage-5.md](demos/stage-5.md).

| Order | Ticket | What | Blocked by | Status |
|---|---|---|---|---|
| 1 | [#46](https://github.com/kl-a/vigil_care/issues/46) | A fully recorded demo Patient (Robin Sample) | #38, #39, #41, #42, #43, #44, #45 | ✅ Done ([PR #60](https://github.com/kl-a/vigil_care/pull/60)) |
| 2 | [#47](https://github.com/kl-a/vigil_care/issues/47) | Patient Summary v1 | #46 | ✅ Done ([PR #60](https://github.com/kl-a/vigil_care/pull/60)) |
| 1 | [#48](https://github.com/kl-a/vigil_care/issues/48) | Open Items and the Dashboard, and **ship Stage 5** | #38, #39, #43, #45 | ✅ Done ([PR #60](https://github.com/kl-a/vigil_care/pull/60)) |

After each stage ships, Dr De Souza tries it hands-on in dev ([revisit-later.md](revisit-later.md), "For Dr De Souza").

### Stage 5b · Visual refresh

The design language of the Claude Design MVP (`temp/Vigil Care UI design/`), adopted where it reads better, not copied screen for screen: a Patient header band, an at-a-glance Summary, quiet provenance (a ✓ Verified icon with the latest Verification on hover), dense tables and segmented sub-tabs, and a clinical Overview with a Treatment Course timeline. Planned in the visual-refresh grilling of 2026-09-27, comparing screenshots of both apps (Playwright, 1440×900).

**Branches:** each ticket is its own branch cut from `stage-5` and merged back into `stage-5`; `stage-5` goes to `main` as one PR once 5b is done.

**Demo:** open Robin Sample's Overview, Summary and the Dashboard, side by side with the MVP's; show that the Summary's key facts sit above the fold and that each value's ✓ shows who verified it.

| Order | Ticket | What | Blocked by | Status |
|---|---|---|---|---|
| 1 | [#50](https://github.com/kl-a/vigil_care/issues/50) | Visual bug fixes: sidebar height, breadcrumb, dates, ranges and units, sub-tab links | none | ✅ Done ([PR #60](https://github.com/kl-a/vigil_care/pull/60)) |
| 2 | [#51](https://github.com/kl-a/vigil_care/issues/51) | Design primitives: formats, section card, table toolbar, sub-tabs, Verified icon, value states | #50 | ✅ Done ([PR #60](https://github.com/kl-a/vigil_care/pull/60)) |
| 3 | [#52](https://github.com/kl-a/vigil_care/issues/52) | Patient header band | #51 | ✅ Done ([PR #60](https://github.com/kl-a/vigil_care/pull/60)) |
| 3 | [#54](https://github.com/kl-a/vigil_care/issues/54) | Open Items as a table with popover actions; Dashboard rail and count badge | #51 | ✅ Done ([PR #60](https://github.com/kl-a/vigil_care/pull/60)) |
| 3 | [#57](https://github.com/kl-a/vigil_care/issues/57) | Tables, sub-tabs and row actions (Patients, Clinical Data, Medications); Labs trend view | #51 | ✅ Done ([PR #60](https://github.com/kl-a/vigil_care/pull/60)) |
| 4 | [#53](https://github.com/kl-a/vigil_care/issues/53) | Patient Summary redesign: glance strip, Open Items cards, flagged-first results | #51, #52, #54 | ✅ Done ([PR #60](https://github.com/kl-a/vigil_care/pull/60)) |
| 4 | [#55](https://github.com/kl-a/vigil_care/issues/55) | Patient Overview redesign: Diagnoses, Key labs, Care Team and Open Items cards | #52, #54 | 🅿️ Parked (backlog 9) |
| 4 | [#58](https://github.com/kl-a/vigil_care/issues/58) | Sex at birth on Patient Identity and the header band | #52 | ➡️ Moved to MVP-1 |
| 5 | [#56](https://github.com/kl-a/vigil_care/issues/56) | Treatment Course timeline on the Overview | #55 | 🅿️ Parked (backlog 9) |

Later, not in 5b: [#59](https://github.com/kl-a/vigil_care/issues/59) Dashboard Recent activity feed (once Documents and extraction give it enough to show).

### MVP-1 · Briefing round trip

Extraction and matching run in a **Claude Project** (claude.ai chat) on synthetic documents, following the design doc's §11 method; Vigil stores the trials, imports the result and shows it. Vigil makes no LLM calls of its own yet, so the privacy gateway arrives in MVP-2.

```
Vigil: ClinicalTrials.gov Refresh → trial snapshot → per-Patient trial export
Claude Project: documents + trial export + prompt → run JSON → Trial Briefing PDF (rendered from the JSON)
Vigil: import run JSON → Clinical Record (imported, unverified) + Match Run → Trials tab (Briefing · Data · Raw JSON)
```

**Demo:** for each of the 3 synthetic lung Patients, run the Claude Project, import the JSON, and walk the Trials tab: the Briefing, the Clinical Record rows it wrote with their quotes, and the raw JSON.

| Order | Ticket | What | Blocked by | Status |
|---|---|---|---|---|
| 0 | `stage-5` merge | Merge Stage 5 and 5b to `main`; park #55, #56, #59 | none | ✅ Done ([PR #60](https://github.com/kl-a/vigil_care/pull/60)) |
| 1 | [#61](https://github.com/kl-a/vigil_care/issues/61) | ClinicalTrials.gov Refresh Job: trial snapshots (`trial`, `trial_site`, `trial_snapshot`), Australian sites, and a per-Patient trial export | none | ⏭️ Ready |
| 1 | [#62](https://github.com/kl-a/vigil_care/issues/62) | Claude Project kit: run schema, Project instructions, prompt, 3 synthetic lung Patients' documents, expected outcomes ([claude-project/](../claude-project/)) | none (trial exports come from #61) | 🔨 Drafted |
| 2 | [#63](https://github.com/kl-a/vigil_care/issues/63) | Import a run: JSON → the 14 Clinical Record fact kinds (provenance "imported from run", unverified; re-import replaces only imported rows) + Match Run, results, parsed criteria and evaluations; refuses on an identity mismatch | #61, #62 | ⏳ Blocked |
| 3 | [#64](https://github.com/kl-a/vigil_care/issues/64) | Trials tab on the Patient: Import run; Briefing, Data and Raw JSON views; earlier runs | [#63](https://github.com/kl-a/vigil_care/issues/63) | ⏳ Blocked |
| 1 | [#58](https://github.com/kl-a/vigil_care/issues/58) | Sex at birth (moved from 5b: trial criteria use it) | none | ⏭️ Ready |

### MVP-2 · In-app pipeline (outline)

Vigil does what the Claude Project did, step by step, each measured against the Claude Project's runs on the same 3 Patients (the baseline):
1. Upload a Patient's Documents (text PDFs and pasted text); Originals encrypted.
2. The thin privacy gate: Presidio + AU recognisers → pseudonymised text; an LLM gateway that refuses anything else; the `cloud_request` ledger written before sending; pre-flight view; every call authorised by a User action ("Process", "Find trials").
3. In-app extraction into the same Clinical Record.
4. The in-app engine: criteria parsing (public text), deterministic pre-filters, LLM adjudication through the gate.
5. The Briefing rendered by Vigil.

### Backlog, in order (reinforcement after MVP-2)

1. Briefing quality to the example's depth for lung, from Dr De Souza's feedback.
2. Scans, photos and faxes: local OCR into the same pseudonymiser.
3. Per-fact Extraction Review (the web review screen) turning imported rows into verified ones.
4. Treatment Options (eviQ terms permitting, [revisit-later.md](revisit-later.md) #9).
5. More Cancer Types: breast, colorectal, melanoma.
6. GP referral letters and medication reconciliation; then other specialties' reports (surgical, radiation oncology, discharge summaries, research and other lab reports, allied health).
7. ANZCTR, staleness and Unknown criteria as Open Items.
8. The full trust gate: image burn-in, leak checks, Redaction QA, Redaction Jobs, cloud VLM, Held Documents.
9. Parked: Stage 5b polish ([#55](https://github.com/kl-a/vigil_care/issues/55), [#56](https://github.com/kl-a/vigil_care/issues/56), [#59](https://github.com/kl-a/vigil_care/issues/59)), Exports, login hardening ([#4](https://github.com/kl-a/vigil_care/issues/4), [#5](https://github.com/kl-a/vigil_care/issues/5), [#32](https://github.com/kl-a/vigil_care/issues/32)).

The old Stage 6–13 outlines (filing → Redaction Jobs → pipeline → Extraction Review → Trials → …) are superseded by this order; their content returns in the items above.

**Provisional decisions:** [docs/revisit-later.md](revisit-later.md) lists them with their triggers; working through them is tracked in [#33](https://github.com/kl-a/vigil_care/issues/33).
