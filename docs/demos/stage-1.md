# Stage 1 demo: Front door

**Audience:** Dr De Souza, practice staff, anyone we're presenting Vigil to. **Runs on:** your laptop, dev environment, synthetic data only (design doc §15).

**Before the demo**
1. `scripts/run-local.sh` (it migrates the database and loads the synthetic demo Practice). Or, with the stack already up: `make demo-data`.
2. Open http://localhost:3000. You should see the **Dev login** with four Users of *Harbourside Oncology (synthetic)*.

**The story:** everyone signs in as themselves, and Vigil shows each person only what their Job Title allows.

| # | Do | Point out | Ticket |
|---|---|---|---|
| 1 | Choose **Dr Alex Rivera (Clinician)**. | The top bar shows who you are and your Job Title; the orange DEV badge means synthetic data only. Clinicians see every screen. | #13 |
| 2 | **Log out**, choose **Jordan Park (Secretary)**. | Users is there, Settings isn't. Same app, different Job Title. | #13 |
| 3 | Log out, choose **Casey Dev (Developer admin)**. | No Patients anywhere: developer admins configure and support Vigil but never see Patient data. Their home is System status. | #13 |
| 4 | As Casey Dev, paste `/patients/jane/summary` into the address bar. | "Not available for your Job Title": the screen and the API both refuse. | #13 |

*Steps for #6 (User Management and the audit trail), #14 (Practice details), #15 (switching Oncology off and on) and #16 (only built screens, System status) are added as those tickets land.*

**If something goes wrong:** the dev login says "No Users yet" → run `make demo-data`. It says the dev login isn't available → set `VIGIL_DEV_LOGIN_ENABLED=true` in `.env` (dev only) and restart.
