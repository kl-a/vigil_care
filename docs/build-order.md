# Build Order

> **As of 2026-09-27.** Where the build stands and what comes next. The plan and its rules are in [Vigil_Design_Document.md](Vigil_Design_Document.md) §15. Tickets live in [GitHub Issues](https://github.com/kl-a/vigil_care/issues), grouped into one milestone per stage. Update this file whenever a ticket finishes or the order changes.

**Showing screens:** a screen appears for everyone once it's marked `built` in `frontend/lib/screens.ts` (or its Patient tab) and its stage has shipped. Raise `SHIPPED_STAGE` in `frontend/lib/stages.ts` when a stage's demo is ready, and mark it here.

**How the build is ordered**
- Every stage ends with a **stage demo**: a scripted walkthrough in dev, on synthetic data, for stakeholders ([docs/demos/](demos/)).
- The **Clinical Record is entered by hand first**. The document pipeline fills the same record later.
- Screens appear only once built, and grow section by section.
- **Patients' Documents come straight after the Patient Summary** (Stages 6–9), so the Practice can track Patients and their Documents before any trial or treatment matching.
- **Login hardening comes last** (Stage 13) and is required before prod or any real Patient data.

## Where we are

| Status | Meaning |
|---|---|
| ✅ Done | Merged to `main` |
| 🔨 Built | Committed on its branch, awaiting PR/merge |
| ⏭️ Ready | All blockers done, so it can start now |
| ⏳ Blocked | Waiting on the tickets listed |
| 📋 Outline | Stage planned; tickets written when we get close |

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

### Stage 4 · Clinical Record by hand

**Demo** (in three parts, each shipped as it's built): build Jane Citizen's record by hand. 4a: breast cancer with Stage, HER2 3+ and ER+ history, a Recurrence. 4b: adjuvant then palliative first-line courses (Line of Therapy derived) and current Medications with PBS links. 4c: the latest bloods, a CT with its Response Assessment, the Management Plan and a Next Step. Show that a secretary can't record a Stage, and that with Oncology switched off the cancer details stay visible read-only. Plan: design doc §15 Stage 4.

| Order | Ticket | What | Blocked by | Status |
|---|---|---|---|---|
| 1 | [#35](https://github.com/kl-a/vigil_care/issues/35) | Entering the Clinical Record by hand (provenance, Verification, reason once per save), and Conditions | none | ⏭️ Ready |
| 1 | [#36](https://github.com/kl-a/vigil_care/issues/36) | Drug reference built from the PBS Schedule (4b) | none | ⏭️ Ready |
| 2 | [#37](https://github.com/kl-a/vigil_care/issues/37) | Cancer Types (MeSH) and Cancer Diagnosis (4a) | #35 | ⏳ Blocked |
| 3 | [#38](https://github.com/kl-a/vigil_care/issues/38) | Biomarkers and Differing Biomarker Results (4a) | #37 | ⏳ Blocked |
| 3 | [#39](https://github.com/kl-a/vigil_care/issues/39) | Recurrences, and **ship 4a** (4a) | #37 | ⏳ Blocked |
| 3 | [#40](https://github.com/kl-a/vigil_care/issues/40) | Treatment Courses and Line of Therapy (4b) | #37 | ⏳ Blocked |
| 4 | [#41](https://github.com/kl-a/vigil_care/issues/41) | Medication Manager, and **ship 4b** (4b) | #40, #36 | ⏳ Blocked |
| 2 | [#42](https://github.com/kl-a/vigil_care/issues/42) | Bloods and other labs (4c) | #35 | ⏳ Blocked |
| 4 | [#43](https://github.com/kl-a/vigil_care/issues/43) | Imaging, Findings and Response Assessments (4c) | #37, #40 | ⏳ Blocked |
| 3 | [#44](https://github.com/kl-a/vigil_care/issues/44) | ECOG and CNS status (4c) | #37 | ⏳ Blocked |
| 2 | [#45](https://github.com/kl-a/vigil_care/issues/45) | Plan and notes, and **ship 4c** (4c) | #35 | ⏳ Blocked |

### Stage 5 · Patient Summary

**Demo:** open the fully recorded demo Patient's Summary as it would look in a consultation, follow a value back to who entered it, then work the Open Items on the Dashboard. Plan: design doc §15 Stage 5.

| Order | Ticket | What | Blocked by | Status |
|---|---|---|---|---|
| 1 | [#46](https://github.com/kl-a/vigil_care/issues/46) | A fully recorded demo Patient | #38, #39, #41, #42, #43, #44, #45 | ⏳ Blocked |
| 2 | [#47](https://github.com/kl-a/vigil_care/issues/47) | Patient Summary v1 | #46 | ⏳ Blocked |
| 1 | [#48](https://github.com/kl-a/vigil_care/issues/48) | Open Items and the Dashboard, and **ship Stage 5** | #38, #39, #43, #45 | ⏳ Blocked |

After each stage ships, Dr De Souza tries it hands-on in dev ([revisit-later.md](revisit-later.md), "For Dr De Souza").

### Stages 6–13 (outlines)

| Stage | Shows stakeholders | Depends on | Status |
|---|---|---|---|
| 6 · Document filing | Upload a Patient's Documents (Original encrypted), view them, set Type and date by hand, Hold, move; nothing leaves the Practice | 5 | 📋 Outline |
| 7 · Redaction Jobs | De-identification trust gate: OCR, masking, Redaction QA, leak check | 6 | 📋 Outline |
| 8 · Document pipeline | Processes filed Documents: OCR, VLM worker, classification, cloud ledger, Held Documents | 7, [#31](https://github.com/kl-a/vigil_care/issues/31) (long Jobs keep their claim) | 📋 Outline |
| 9 · Extraction Review | Extracted Facts reviewed into the same Clinical Record | 8 | 📋 Outline |
| 10 · Trials | 10a Trial Browser (public data; can start any time after Stage 3), 10b Match Board | 9 | 📋 Outline |
| 11 · Treatment Options | eviQ + PBS Coverage. **Blocked on eviQ terms of use** ([revisit-later.md](revisit-later.md) #9) | 3, 4 | 📋 Outline |
| 12 · Exports | Identified and De-identified Exports with sign-off | 5, 7, 9 (10 for trial reports) | 📋 Outline |
| 13 · Login hardening & polish | 2FA, inactivity lock, re-authentication, bootstrap, onboarding, backup, polish. Tickets so far: [#4](https://github.com/kl-a/vigil_care/issues/4), [#5](https://github.com/kl-a/vigil_care/issues/5), [#32](https://github.com/kl-a/vigil_care/issues/32) (runbook) | all | 📋 Outline |

## Critical path

```mermaid
flowchart LR
    T2[#2 schema ✅] --> T13[#13 dev login ✅]
    T13 --> T6[#6 permissions + Users ✅]
    T6 --> T14[#14 Practice details ✅]
    T6 --> T15[#15 Specialty Modules ✅]
    T14 --> T24[#24 Practice Memberships ✅]
    T15 --> T24
    T24 --> S1
    T16[#16 built screens only ✅] --> S1((Stage 1 demo))
    T14 --> S1
    T15 --> S1
    T24 --> T8[#8 Patients ✅] --> T17[#17 soft delete ✅]
    T24 --> T7[#7 Providers ✅]
    T24 --> T25[#25 Sites ✅] --> S2
    T8 --> T9[#9 Care Team ✅]
    T7 --> T9
    T17 --> S2((Stage 2 demo))
    T9 --> S2
    T24 --> T18[#18 job queue ✅] --> T19[#19 PBS Refresh ✅] --> T20[#20 PBS Lookup ✅] --> T30[#30 whole PBS Schedule ✅]
    T18 --> T10[#10 Support Views ✅]
    T19 --> T31[#31 long Jobs keep their claim ✅]
    T20 --> S3((Stage 3 demo))
    S3 --> T35[#35 Clinical Record entry + Conditions] --> T37[#37 Cancer Diagnosis]
    T19 --> T36[#36 drug reference]
    T37 --> T38[#38 Biomarkers] & T39[#39 Recurrences] & T40[#40 Treatment Courses] & T44[#44 ECOG/CNS]
    T39 --> S4a((4a demo))
    T38 --> S4a
    T40 --> T41[#41 Medication Manager] --> S4b((4b demo))
    T36 --> T41
    T35 --> T42[#42 labs] & T45[#45 plan and notes]
    T40 --> T43[#43 imaging + Response]
    T45 --> S4c((4c demo))
    T42 --> S4c
    T43 --> S4c
    T44 --> S4c
    S4a & S4b & S4c --> T46[#46 demo Patient] --> T47[#47 Patient Summary]
    T43 --> T48[#48 Open Items + Dashboard]
    T47 --> S5((Stage 5 demo))
    T48 --> S5
    T10 --> S3
```

**Next up:**
1. Stage 4: start #35 (the entry pattern every Stage 4 ticket copies) and, in parallel, #36 (drug reference). Then 4a (#37 → #38, #39), 4b (#40 → #41) and 4c (#42, #43, #44, #45) as their blockers clear.
2. Stage 5 once Stage 4's parts are in: #46 → #47, and #48.

**Provisional decisions:** [docs/revisit-later.md](revisit-later.md) lists them with their triggers; working through them is tracked in [#33](https://github.com/kl-a/vigil_care/issues/33).

**After Stage 5:** Stages 6 → 7 → 8 → 9 in order, then Trials, Treatment Options (once eviQ is cleared), Exports and Login hardening.
