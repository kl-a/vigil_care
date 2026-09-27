# Stage 4 demo: the Clinical Record, entered by hand

**Audience:** Dr De Souza, practice staff, anyone we're presenting Vigil to. **Runs on:** your laptop, dev environment, synthetic Patients only (design doc §15).

**Before the demo**
1. `scripts/run-local.sh` (it migrates the database, loads the demo data and starts everything). Or, with the stack already up: `make demo-data`.
2. All of Stage 4 has shipped (`SHIPPED_STAGE = 4`, `SHIPPED_PARTS = ["4a", "4b", "4c"]`): the Clinical Data sub-tabs and the Medications tab show to everyone.
3. If the dev database has never had a **PBS Refresh**, start one as the developer admin (System status → Refreshes): the Medication Manager picks drugs from the drug reference it builds.
4. As **Casey Dev (synthetic), Developer admin**, make sure **Oncology** is on in Settings → Specialty Modules.

**The story:** before any Document is read automatically, the clinician can build a Patient's record by hand. Every value says who entered it; every correction says why; and who may enter what follows their Job Title.

All built: 4a (#35, #37, #38, #39), 4b (#36, #40, #41) and 4c (#42, #43, #44, #45).

## 4a · Conditions and cancer

| # | Do | Point out | Ticket |
|---|---|---|---|
| 1 | Sign in as **Dr Alex Rivera (synthetic), Clinician**. Open **Jane Citizen** → **Clinical Data** → Conditions → **Add Condition**: "Type 2 diabetes", active. | It's recorded as entered by Dr Rivera (Clinician), with the time. | #35 |
| 2 | **Add Condition** again, tick **This is a primary cancer**: Breast cancer, left, diagnosed 1 Mar 2024, Stage IIA (TNM), Disease Extent localised. | The Cancer Type shows its MeSH term (the trial registries' vocabulary). Stage is labelled "at diagnosis"; Disease Extent is "now". The Overview shows a block for it. | #37 |
| 3 | On the **Cancer Diagnosis** sub-tab, **Correct**: Disease Extent → metastatic, as of today. Save. | A reason is asked for once, for the whole save. | #35, #37 |
| 4 | Sign in as **Jordan Park (synthetic), Secretary** and open the same tab. | Everything is visible, read-only, with a "Needs clinician" lock. A secretary can't record a Stage. | #35, #37 |
| 5 | **Biomarkers** sub-tab: add HER2 positive (3, IHC) on the primary, collected 1 Mar 2024; then HER2 negative (0, IHC) on a liver biopsy, 10 Feb 2026. | Both are kept; the newer is current. Its chip on the Cancer Diagnosis says **Results differ**: side by side, never a cause or an action. | #38 |
| 6 | Sign in as **Sam Lee (synthetic), Trial coordinator**: on the Cancer Diagnosis, **Record a suspected recurrence**: distant, liver, 10 Feb 2026. | A trial coordinator records it; only a clinician resolves it. | #39 |
| 7 | As the clinician: **New primary instead**. | The Cancer Diagnosis form opens with the date and site filled in; save it. Jane now has two primaries, and the liver HER2 result can be **moved** to the new one. | #38, #39 |
| 8 | As the developer admin, switch **Oncology** off; as the clinician, reopen Jane. | The Oncology tabs are gone, but her cancers, recurrence, ECOG and CNS status still show, read-only in plain words. Switch Oncology back on. | #35 |

## 4b · Treatment and Medications

| # | Do | Point out | Ticket |
|---|---|---|---|
| 1 | **Treatment Courses** → **Add course**: breast cancer, systemic, adjuvant, "AC-T" (doxorubicin 60 mg/m2, cyclophosphamide 600 mg/m2), Apr–Sep 2024. Then a surgery (left mastectomy) and radiation (chest wall, 50 Gy). | Each course belongs to one Condition; only systemic courses carry a Regimen. The adjuvant course has no Line of Therapy. | #40 |
| 2 | Add a palliative systemic course (paclitaxel, Mar 2025), then another (capecitabine, Nov 2025). | They show **1st line** and **2nd line**, each saying why ("2nd line: 2nd palliative systemic course of Breast cancer"). | #40 |
| 3 | As the clinician, **Change line** on a maintenance course between them: 1, "Maintenance of 1st line". | The override says it was set by a clinician and why; the next course counts on from it. A trial coordinator can't override. | #40 |
| 4 | **End course** on paclitaxel: 1 Nov 2025, progression. | Ending is a correction: the date, why it stopped, and a reason. | #40 |
| 5 | Sign in as the trial coordinator. **Medications** tab → **Add medication**: search "capecitabine", pick it; 1500 mg, oral, twice daily, category Cancer treatment, part of the capecitabine course, prescribed by Dr Rivera. | It's picked from the drug reference (built from the PBS Schedule); **PBS Drug Lookup** opens the drug's PBS page. A cancer drug links to its Treatment Course. | #36, #41 |
| 6 | **Add medication** again: tick **It's not in the drug reference**, "Turmeric capsules", Supplement. | It says "Not in the drug reference" instead of a PBS link. | #41 |
| 7 | **Change** capecitabine's dose to 1000 mg; then **Stop** it: today, "Hand-foot syndrome". | A reason is asked once per save. Stopping moves it to **Discontinued**; on Clinical Data, the capecitabine course is still ongoing. | #41 |
| 8 | Open **Change log**, then **Print**. | Every change: what changed, who, when and why. The printout drops the buttons and navigation. | #41 |
| 9 | Sign in as the secretary and open Medications. | Readable, with a lock instead of Add, Change and Stop. | #41 |

## 4c · Results and plan

| # | Do | Point out | Ticket |
|---|---|---|---|
| 1 | As the clinician, **Labs** → **Enter results**, panel **FBC**: Haemoglobin 98 (ref 115–165), Platelets 480 (ref 150–400); leave the rest empty. Save. | One save, one sign-off for the panel. Haemoglobin is flagged L and platelets H, from the report's own ranges; empty analytes are skipped. | #42 |
| 2 | Enter another FBC a week later with Haemoglobin 105. | The trend chart shows Haemoglobin over time with its reference range shaded. | #42 |
| 3 | **Plan & notes** → **Record new plan**: paste the plan from the letter, written by Dr Rivera. | It's quoted exactly as typed, line breaks and all, with its author and date; a new plan keeps the earlier ones. | #45 |
| 4 | **Add Next Step**: MDT, "Discuss at breast MDT", due next week. Sign in as the secretary and **Mark done**. | A secretary manages Next Steps (booking the MDT is often their job), but can't write a note or a plan. | #45 |
| 5 | **Add note**: a letter to the referring GP. | Author and recipient come from the Provider directory. | #45 |
| 6 | **Performance Status**: ECOG 1 in June, ECOG 2 today. **CNS**: present, 2 lesions (left frontal, cerebellum), treated with SRS. | The latest ECOG shows as a badge on the Overview with its date, and the CNS line beside it. | #44 |
| 7 | As the trial coordinator, **Imaging & Findings** → **Add scan**: CT, chest, abdomen and pelvis, 14 Aug 2025, compared with May 2025; paste the impression; two Findings (liver segment VII metastasis, 18 mm, measurable; new 4 mm right lung nodule). | The impression is quoted exactly as pasted. A Finding is attributed to a Condition only when the report says so. | #43 |
| 8 | **Response Assessments** → **Record assessment**: Breast cancer, responding, from that CT (radiology report). | The scan now carries a **Responding** badge; on Treatment Courses, paclitaxel (running then) shows **Best Response: Responding**, derived and saying which scan it came from. | #43 |
| 9 | Record another: Cancer Diagnosis **Not sure which**, progressing, today. Sign in as the clinician. | It shows "Not sure which Cancer Diagnosis"; only the clinician can **Attribute to** one (or **Override** a report, with why). The trial coordinator can't. | #43 |
| 10 | Switch Oncology off again (as the developer admin); reopen Jane as the clinician. | The Response Assessments and best responses stay visible, read-only in plain words; the scan and its Findings (Core) are unchanged. | #43 |

**If something goes wrong:** no drugs found when adding a Medication → start a PBS Refresh as the developer admin (the drug reference is built at its end). "Oncology isn't active at this Practice" → switch it on as the developer admin.
