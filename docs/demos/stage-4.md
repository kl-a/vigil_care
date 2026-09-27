# Stage 4 demo: the Clinical Record, entered by hand

**Audience:** Dr De Souza, practice staff, anyone we're presenting Vigil to. **Runs on:** your laptop, dev environment, synthetic Patients only (design doc §15).

**Before the demo**
1. `scripts/run-local.sh` (it migrates the database, loads the demo data and starts everything). Or, with the stack already up: `make demo-data`.
2. 4a has shipped (`SHIPPED_STAGE = 4`, `SHIPPED_PARTS = ["4a"]`): the Clinical Data tab shows 4a's sub-tabs to everyone. 4b and 4c ship with #41 and #43; until then, turn on **Show upcoming screens** (dev) to demo what's built of them.
3. As **Casey Dev (synthetic), Developer admin**, make sure **Oncology** is on in Settings → Specialty Modules.

**The story:** before any Document is read automatically, the clinician can build a Patient's record by hand. Every value says who entered it; every correction says why; and who may enter what follows their Job Title.

Built so far: all of 4a (#35, #37, #38, #39), Treatment Courses and the drug reference in 4b (#36, #40), and labs, plan & notes and ECOG/CNS in 4c (#42, #44, #45). Still to come: Medications (#41) and imaging with Response Assessments (#43).

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
| 4 | **End course** on the ongoing one. | Ending is a correction: the date, why it stopped, and a reason. | #40 |

To come with #41: current Medications from the drug reference with their PBS links (#36 builds that reference after each PBS Refresh).

## 4c · Results and plan

| # | Do | Point out | Ticket |
|---|---|---|---|
| 1 | As the clinician, **Labs** → **Enter results**, panel **FBC**: Haemoglobin 98 (ref 115–165), Platelets 480 (ref 150–400); leave the rest empty. Save. | One save, one sign-off for the panel. Haemoglobin is flagged L and platelets H, from the report's own ranges; empty analytes are skipped. | #42 |
| 2 | Enter another FBC a week later with Haemoglobin 105. | The trend chart shows Haemoglobin over time with its reference range shaded. | #42 |
| 3 | **Plan & notes** → **Record new plan**: paste the plan from the letter, written by Dr Rivera. | It's quoted exactly as typed, line breaks and all, with its author and date; a new plan keeps the earlier ones. | #45 |
| 4 | **Add Next Step**: MDT, "Discuss at breast MDT", due next week. Sign in as the secretary and **Mark done**. | A secretary manages Next Steps (booking the MDT is often their job), but can't write a note or a plan. | #45 |
| 5 | **Add note**: a letter to the referring GP. | Author and recipient come from the Provider directory. | #45 |
| 6 | **Performance Status**: ECOG 1 in June, ECOG 2 today. **CNS**: present, 2 lesions (left frontal, cerebellum), treated with SRS. | The latest ECOG shows as a badge on the Overview with its date, and the CNS line beside it. | #44 |

**If something goes wrong:** a sub-tab is missing → it isn't built yet (turn on Show upcoming screens to see what's coming). "Oncology isn't active at this Practice" → switch it on as the developer admin.
