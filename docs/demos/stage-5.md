# Stage 5 demo: the Patient Summary and Open Items

**Audience:** Dr De Souza, practice staff, anyone we're presenting Vigil to. **Runs on:** your laptop, dev environment, synthetic Patients only (design doc §15).

**Before the demo**
1. `scripts/run-local.sh` (it migrates the database, loads the demo data and starts everything). Or, with the stack already up: `make demo-data`. The demo data gives **Robin Sample** a full Clinical Record, entered through the same services as the screens, so every value has who entered it.
2. For Robin's Medications to link to the PBS Drug Lookup, the drug reference must be built first: as the developer admin, start a **PBS Refresh** (System status → Refreshes), then load the demo data. Loaded before a Refresh, they're recorded as "Not in the drug reference".
3. Stage 5 has shipped (`SHIPPED_STAGE = 5`): the Dashboard, the Summary tab and Open Items show to everyone. Oncology is on (Settings → Specialty Modules).

**The story:** in a consultation, the clinician opens one page and sees the whole Patient, with every fact traceable to who entered it. Between consultations, the practice works one queue of what needs doing, and nothing leaves the queue until someone has acted on it.

| # | Do | Point out | Ticket |
|---|---|---|---|
| 1 | Sign in as **Dr Alex Rivera (synthetic), Clinician**. **Patients**. | The **Open Items** column: Robin Sample has five. | #48 |
| 2 | Open **Robin Sample** → **Summary**. | One page in order: Registration, Diagnosis (colorectal cancer, Stage IIIB at diagnosis, metastatic now; KRAS wild-type, MSI stable, BRAF V600E **Results differ**; the 2019 melanoma with a suspected lung recurrence), Most Recent Results (flagged bloods with sparklines; the June CT with its **Responding** badge), Recent Treatment (FOLFOX + bevacizumab: **1st line**, **Best Response: Responding**), Clinical Notes, Management (the plan verbatim, Next Steps), Medical History (diabetes, hypertension, the resolved DVT; current Medications), Open Items. Registration and Diagnosis come first, side by side on a wide screen. | #46, #47 |
| 3 | On **Most Recent Results**, open **Last updated** → **See it in the record**. | It says who last changed the section, in what Job Title and when (Sam Lee, Trial coordinator); the link opens the Labs sub-tab, where each value shows who entered it. | #47 |
| 4 | **Print**. | The print layout: no navigation or buttons, sections kept whole. | #47 |
| 5 | Sign in as **Jordan Park (synthetic), Secretary**. Open the **Dashboard**. | The Practice's queue, each item with its Patient. The secretary can **Mark done** the MDT Next Step; the clinician-only items show **Needs clinician**. Filter **I can act**, then **Clinician only**. | #48 |
| 6 | As the secretary, **Mark done** on "Discuss lung nodule at MDT". | It leaves the queue: acted on, not dismissed. There is no dismiss or snooze anywhere. | #48 |
| 7 | Sign in as the clinician. On the Dashboard: **Seen** on "BRAF V600E results differ", with the note "Discussed at MDT". | One click, the note optional, recorded as a Verification. It clears; a later BRAF result that differs raises it again. | #48 |
| 8 | "Response Assessment not attributed: stable" → **Attribute to** Colorectal cancer. "New Finding not attributed: Nodule, Right lower lobe, right" → **Attribute to** Melanoma, left forearm. | Each clears as soon as it's attributed. The Response Assessment now counts towards FOLFOX's Best Response. | #48 |
| 9 | "Suspected Recurrence of Melanoma, left forearm" → **Open**, then on Clinical Data **Confirm**, **New primary instead** or **Rule out** (with why). | Resolving it in any of the three ways clears it. | #39, #48 |
| 10 | As the developer admin, open the Dashboard link. | The developer admin lands on System status: never Patient data, never Open Items. | #48 |
| 11 | Switch **Oncology** off; reopen Robin's Summary as the clinician. | The Diagnosis section becomes the module's read-only view in plain words; Oncology's Open Items leave the queue (the module owns them), the Next Steps stay. Switch Oncology back on. | #47, #48 |

**If something goes wrong:** Robin has no record → run `make demo-data` (it only adds what's missing). Robin's Medications have no PBS links → run a PBS Refresh first; a record already loaded keeps its free-text Medications (reset the dev database to reload them).
