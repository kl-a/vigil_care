# Stage 1 demo: Front door

**Audience:** Dr De Souza, practice staff, anyone we're presenting Vigil to. **Runs on:** your laptop, dev environment, synthetic data only (design doc §15).

**Before the demo**
1. `scripts/run-local.sh` (it migrates the database and loads the synthetic demo Practice). Or, with the stack already up: `make demo-data`.
2. Open http://localhost:3000. You should see the **Dev login** with four Users of *Harbourside Oncology (synthetic)*.

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

*Steps for #14 (Practice details) and #15 (switching Oncology off and on) are added as those tickets land.*

**If something goes wrong:** the dev login says "No Users yet" → run `make demo-data`. It says the dev login isn't available → set `VIGIL_DEV_LOGIN_ENABLED=true` in `.env` (dev only) and restart.
