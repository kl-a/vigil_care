# Stage 4 demo: the Clinical Record, entered by hand

**Audience:** Dr De Souza, practice staff, anyone we're presenting Vigil to. **Runs on:** your laptop, dev environment, synthetic Patients only (design doc §15).

**Before the demo**
1. `scripts/run-local.sh` (it migrates the database, loads the demo data and starts everything). Or, with the stack already up: `make demo-data`.
2. Stage 4 ships in three parts; until 4a ships (`SHIPPED_STAGE = 4`), turn on **Show upcoming screens** (dev) to see the Clinical Data tab.
3. As **Casey Dev (synthetic), Developer admin**, make sure **Oncology** is on in Settings → Specialty Modules.

**The story:** before any Document is read automatically, the clinician can build a Patient's record by hand. Every value says who entered it; every correction says why; and who may enter what follows their Job Title.

Built so far: Conditions and Cancer Diagnosis (4a, #35, #37), the drug reference (4b, #36), labs and plan & notes (4c, #42, #45). Still to come: Biomarkers (#38) and Recurrences (#39) in 4a; Treatment Courses (#40) and Medications (#41) in 4b; imaging and Response Assessments (#43) and ECOG/CNS (#44) in 4c.

## 4a · Conditions and cancer

| # | Do | Point out | Ticket |
|---|---|---|---|
| 1 | Sign in as **Dr Alex Rivera (synthetic), Clinician**. Open **Jane Citizen** → **Clinical Data** → Conditions → **Add Condition**: "Type 2 diabetes", active. | It's recorded as entered by Dr Rivera (Clinician), with the time. | #35 |
| 2 | **Add Condition** again, tick **This is a primary cancer**: Breast cancer, left, diagnosed 1 Mar 2024, Stage IIA (TNM), Disease Extent localised. | The Cancer Type shows its MeSH term (the trial registries' vocabulary). Stage is labelled "at diagnosis"; Disease Extent is "now". The Overview shows a block for it. | #37 |
| 3 | On the **Cancer Diagnosis** sub-tab, **Correct**: Disease Extent → metastatic, as of today. Save. | A reason is asked for once, for the whole save. | #35, #37 |
| 4 | Sign in as **Jordan Park (synthetic), Secretary** and open the same tab. | Everything is visible, read-only, with a "Needs clinician" lock. A secretary can't record a Stage. | #35, #37 |
| 5 | As the developer admin, switch **Oncology** off; as the clinician, reopen Jane. | The Oncology tabs are gone, but her cancer still shows, read-only: "Breast cancer: Stage IIA (TNM) at diagnosis, 1 Mar 2024; metastatic". Switch Oncology back on. | #35 |

## 4b · Treatment and Medications

To come with #40 and #41: adjuvant then palliative first-line courses (Line of Therapy derived), current Medications from the drug reference with their PBS links (#36 builds that reference after each PBS Refresh).

## 4c · Results and plan

| # | Do | Point out | Ticket |
|---|---|---|---|
| 1 | As the clinician, **Labs** → **Enter results**, panel **FBC**: Haemoglobin 98 (ref 115–165), Platelets 480 (ref 150–400); leave the rest empty. Save. | One save, one sign-off for the panel. Haemoglobin is flagged L and platelets H, from the report's own ranges; empty analytes are skipped. | #42 |
| 2 | Enter another FBC a week later with Haemoglobin 105. | The trend chart shows Haemoglobin over time with its reference range shaded. | #42 |
| 3 | **Plan & notes** → **Record new plan**: paste the plan from the letter, written by Dr Rivera. | It's quoted exactly as typed, line breaks and all, with its author and date; a new plan keeps the earlier ones. | #45 |
| 4 | **Add Next Step**: MDT, "Discuss at breast MDT", due next week. Sign in as the secretary and **Mark done**. | A secretary manages Next Steps (booking the MDT is often their job), but can't write a note or a plan. | #45 |
| 5 | **Add note**: a letter to the referring GP. | Author and recipient come from the Provider directory. | #45 |

**If something goes wrong:** the Clinical Data tab is missing → Stage 4 hasn't shipped; turn on Show upcoming screens. "Oncology isn't active at this Practice" → switch it on as the developer admin.
