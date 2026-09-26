# Stage 3 demo: PBS & Support Views

**Audience:** Dr De Souza, practice staff, anyone we're presenting Vigil to. **Runs on:** your laptop, dev environment, synthetic Patients only; the PBS Schedule is public data (design doc §15).

**Before the demo**
1. `scripts/run-local.sh` (it migrates the database, loads the demo data and starts the backend, the **worker** and the frontend). Or, with the stack already up: `make demo-data`.
2. Make sure the PBS Schedule is loaded: on a fresh database the worker starts the monthly PBS Refresh by itself as soon as it runs (it's due on the 1st, and has never run). Check System status → Refreshes shows it Succeeded; it takes about 3 minutes (one request every 20 seconds), and needs `VIGIL_PBS_API_KEY` in `.env`. Offline or without a key, on a fresh database, the Sample Schedule (a copy of 1 Sep 2026) loads instead, clearly marked as out of date and for demos only.

**The story:** Vigil keeps its own copy of public reference data, refreshed by background Jobs, and the people who support it can see everything that runs, without ever seeing a Patient.

| # | Do | Point out | Ticket |
|---|---|---|---|
| 1 | Sign in as **Dr Alex Rivera (synthetic), Clinician**. Open **PBS lookup**. | Every drug in the PBS Schedule, A–Z, with the total, the schedule date, and each drug's forms, therapeutic group and listing types. | #20, #30 |
| 2 | Type `dexamfetamine`; then clear it and pick **Therapeutic group → Cancer drugs** and **Listing type → Authority Required (Streamlined)**. | Dexamfetamine is found (not a cancer drug). The filters narrow the list, and the page address changes with them. | #30 |
| 3 | Open **Pembrolizumab**, then **← Back to results**. | Labelled sections: its PBS Items (program, maximum per prescription with units, repeats), when it can be prescribed (Listing per indication, amber Authority Required, conditions; items with the same rules shown once), and what the patient pays, once. Back returns to the same filtered list. | #20, #30 |
| 4 | Log out; sign in as **Casey Dev (synthetic), Developer admin**. Open **Dashboard**. | It lands on System status: health, VLM worker, the Job queue and the Refreshes. No Patients, and no PBS lookup, in this user's navigation. | #10 |
| 5 | On the PBS Refresh, press **Start Refresh**. | Queued → Running → Succeeded, its steps (fetch ✓ · store ✓) ticking off. Only a developer admin can start one. It also runs by itself on the 1st of each month. | #18, #19 |
| 6 | Scroll to **Jobs** and **Refresh history**. | Each run's counts (item_count), schedule date, timings and ids: never a name or identifier. A quality gate proves no Patient data reaches any Support View or the logs. | #10 |
| 7 | Log out; sign in as **Jordan Park (synthetic), Secretary**, and open System status. | The same Support Views for everyone; only the developer admin gets the Start button. | #10 |

**If something goes wrong:** the Refresh stays Queued → the worker isn't running (`docker compose ps worker`, or `.run/worker.log` with `--dev`). PBS lookup says "Sample data from the PBS Schedule of 1 Sep 2026: out of date, for demos only" → the API was unreachable, or `VIGIL_PBS_API_KEY` isn't set, on a database that had never loaded the real schedule; set the key and start another Refresh when online.
