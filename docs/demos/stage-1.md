# Stage 1 demo: Front door

**Audience:** Dr De Souza, practice staff, anyone we're presenting Vigil to. **Runs on:** your laptop, dev environment, synthetic data only (design doc §15).

**Before the demo**
1. `scripts/run-local.sh` (it migrates the database and loads the synthetic demo Practice). Or, with the stack already up: `make demo-data`.
2. Open http://localhost:3000. You should see the **Dev login** with four Users of *Harbourside Oncology (synthetic)*, and Dr Alex Rivera again under *Northside Oncology (synthetic)*.

**The story:** everyone signs in as themselves, and Vigil shows each person only what their Job Title allows.

| # | Do | Point out | Ticket |
|---|---|---|---|
| 1 | Choose **Dr Alex Rivera (synthetic), Clinician**. | The top bar shows who you are and your Job Title; the orange DEV badge means synthetic data only. Clinicians see every screen. | #13 |
| 2 | **Log out**, choose **Jordan Park (synthetic), Secretary**. | Users is there, Settings isn't. Same app, different Job Title. | #13 |
| 3 | Log out, choose **Casey Dev (synthetic), Developer admin**. | No Patients anywhere: developer admins configure and support Vigil but never see Patient data. | #13 |
| 4 | As Casey Dev, paste `/patients/jane/summary` into the address bar. | "Not available for your Job Title". (From #8 the Patient API refuses too, with a 403.) | #13 |

| 5 | As Casey Dev, look at the sidebar and the home page. | Only what's built appears: Users and System status (Settings joins with #14/#15). Home is **System status**: database OK, VLM worker not configured, DEV. | #16 |
| 6 | Tick **Show upcoming screens** (top bar, dev only). | Every later screen appears, badged with its stage (Patients "S2", PBS "S3"…). Open one: an orange note says "coming in Stage N". Untick it again. | #16 |
| 7 | As Casey Dev, open **Users** → **New User**: *Riley Hart (synthetic)*, `riley.hart`, Secretary → Add User. | Anyone who manages Users (clinician, secretary, developer admin) can add one. Trial coordinators don't even see this screen. | #6 |
| 8 | On Riley's row → **Change Job Title** → Trial coordinator, reason "Moving to trials" → Change. | The dialog says it's recorded as a sign-off by Casey Dev (Developer admin). | #6 |
| 9 | Click **Riley Hart** → the audit trail. | "Job Title changed from Secretary to Trial coordinator, signed off by Casey Dev (synthetic) (Developer admin)", with the reason and time; "Added as Secretary" below it. | #6 |
| 10 | Back in Users → **Deactivate** Riley. | A reason is required. Log out: Riley is no longer on the dev login. Nothing is deleted; the audit trail stays. | #6 |
| 11 | Try to change your own Job Title. | There's no button on your own row ("You"): nobody can lock themselves out. | #6 |

| 12 | As Dr Alex Rivera, open **Settings** → Practice details. Change the phone number → Save details. | Clinicians and developer admins keep the Practice's details up to date; the location is there for trial-site distances later. The save is in the audit trail under Dr Rivera's name. | #14 |
| 13 | Log out, choose Jordan Park (Secretary). | No Settings in the sidebar: only clinicians and developer admins change them. | #14 |
| 14 | As Casey Dev, open **Settings** → Specialty Modules. Oncology is **On**. | Vigil is a general Core with Specialty Modules; Oncology is the first. Only a developer admin switches them. | #15 |
| 15 | Tick **Show upcoming screens**, open a Patient (e.g. `/patients/demo/summary`, as Dr Rivera) and note the Diagnosis section and the Treatment Options tab. Then, as Casey Dev, **Switch Oncology off** (sign-off, reason "Showing the Core"). | Back as Dr Rivera: the Oncology sections and the Treatment Options tab are gone; the Core screens still work. Switch it back on and they return: nothing was deleted. | #15 |

| 16 | Log out. Point at Dr Alex Rivera listed twice on the dev login: Harbourside and Northside. Choose **Dr Alex Rivera, Northside Oncology**. | One person, one login, a Practice Membership at each Practice. The top bar's Practice is Northside; Users shows only Northside's people, and Oncology is off here because each Practice has its own modules. | #24 |
| 17 | Still as Dr Rivera at Northside: **Users** → **New User**, enter only the username `jordan.park`, Job Title Secretary → Add User. | Jordan already has a login (at Harbourside), so their own name comes with it and nothing about Harbourside shows here. Log out: Jordan is now listed under both Practices. | #24 |
| 18 | Choose Casey Dev (Harbourside) → Users → **Deactivate** Dr Rivera, reason "Moved to Northside". Log out. | Dr Rivera is gone from Harbourside on the dev login but still listed at Northside: deactivating affects only one Practice. Reactivate them afterwards. | #24 |

**If something goes wrong:** the dev login says "No Users yet" → run `make demo-data`. It says the dev login isn't available → set `VIGIL_DEV_LOGIN_ENABLED=true` in `.env` (dev only) and restart.
