# Stage 3 demo: PBS & Support Views

**Audience:** Dr De Souza, practice staff, anyone we're presenting Vigil to. **Runs on:** your laptop, dev environment, synthetic Patients only; the PBS Schedule is public data (design doc §15).

**Before the demo**
1. `scripts/run-local.sh` (it migrates the database, loads the demo data and starts the backend, the **worker** and the frontend). Or, with the stack already up: `make demo-data`.
2. Make sure the PBS Schedule is loaded: on a fresh database the worker starts the monthly PBS Refresh by itself as soon as it runs (it's due on the 1st, and has never run). Check System status → Refreshes shows it Succeeded; it takes about 3 minutes with the public API key (one request every 20 seconds). Offline, on a fresh database, the bundled Sample Schedule loads instead, clearly marked.

**The story:** Vigil keeps its own copy of public reference data, refreshed by background Jobs, and the people who support it can see everything that runs, without ever seeing a Patient.

| # | Do | Point out | Ticket |
|---|---|---|---|
| 1 | Sign in as **Dr Alex Rivera (synthetic), Clinician**. Open **PBS lookup** and type `pembro`. | Results appear as you type, "as of" the schedule date. Search works on drug names, brands and ingredients. | #20 |
| 2 | Open **Pembrolizumab**. | Each PBS item with its Listing per indication (amber Authority Required), the prescribing conditions, general and concessional co-payments, maximum quantity and repeats, and the Safety Net thresholds. | #20 |
| 3 | Log out; sign in as **Casey Dev (synthetic), Developer admin**. Open **Dashboard**. | It lands on System status: health, VLM worker, the Job queue and the Refreshes. No Patients, and no PBS lookup, in this user's navigation. | #10 |
| 4 | On the PBS Refresh, press **Start Refresh**. | Queued → Running → Succeeded, its steps (fetch ✓ · store ✓) ticking off. Only a developer admin can start one. It also runs by itself on the 1st of each month. | #18, #19 |
| 5 | Scroll to **Jobs** and **Refresh history**. | Each run's counts (item_count), schedule date, timings and ids: never a name or identifier. A quality gate proves no Patient data reaches any Support View or the logs. | #10 |
| 6 | Log out; sign in as **Jordan Park (synthetic), Secretary**, and open System status. | The same Support Views for everyone; only the developer admin gets the Start button. | #10 |

**If something goes wrong:** the Refresh stays Queued → the worker isn't running (`docker compose ps worker`, or `.run/worker.log` with `--dev`). PBS lookup says "Sample data, not for clinical use" → the API was unreachable on a database that had never loaded the real schedule; start another Refresh when online.
