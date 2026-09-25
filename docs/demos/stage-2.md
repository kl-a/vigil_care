# Stage 2 demo: Patients

**Audience:** Dr De Souza, practice staff, anyone we're presenting Vigil to. **Runs on:** your laptop, dev environment, synthetic data only (design doc §15).

**Before the demo**
1. `scripts/run-local.sh` (it migrates the database and loads the synthetic demo Practices). Or, with the stack already up: `make demo-data`.
2. Until Stage 2 ships (`SHIPPED_STAGE = 2` in `frontend/lib/stages.ts`), tick **Show upcoming screens** in the top bar after signing in. Patients, Providers and Settings → Sites then appear.

**The story:** the Practice keeps its Patients, its Provider directory and the places it sees Patients, and every change is signed off. Identity is shown in full inside Vigil and encrypted in the database.

| # | Do | Point out | Ticket |
|---|---|---|---|
| 1 | Sign in as **Jordan Park (synthetic), Secretary**. Open **Patients** and type `citi` in the search. | Jane Citizen appears with DOB and age, MRN and Pseudonym (VG-0042). Search works on names and MRN. | #8 |
| 2 | Open Jane Citizen. | The Patient header (name, DOB, MRN, Pseudonym) and the Overview's Patient Identity: Medicare + IRN, IHI, contact details, next of kin, in full. Only the tabs that are built show once Stage 2 ships. | #8 |
| 3 | **Edit details** → change her mobile to `0491 570 158` → Save. | The audit trail shows "Mobile: 0491 570 156 → 0491 570 158", signed off by Jordan Park (Secretary), with the time. | #8 |
| 4 | Show the database: `docker compose exec db psql -U vigil_owner -d vigil -c "SELECT mobile_encrypted, medicare_number_encrypted FROM identity.patient_identity LIMIT 1"` | The identifying fields are AES-256-GCM ciphertext; the key is never in the database. The audit entry is sealed too: `SELECT after FROM verification WHERE subject_table = 'patient'` shows which fields changed, not their values. | #8 |
| 5 | **New patient**: *Alex Test (synthetic)*, DOB 01/01/1980 → Create patient. | Vigil assigns the next Pseudonym (VG-0100 onwards) and opens the Overview. | #8 |
| 6 | Log out; sign in as **Casey Dev (synthetic), Developer admin**. Paste `/patients`. | "Not available for your Job Title": developer admins never see Patient data, and the API answers 403. | #8 |
| 7 | Log out; sign in as **Dr Alex Rivera (synthetic), Northside Oncology**. Open Patients. | Empty: Harbourside's Patients belong to Harbourside. The same person sees them only when acting at Harbourside. | #8, #24 |
| 8 | As Jordan Park (Harbourside), open **Providers**. Filter Specialty = General practice. | Dr Morgan Grey, the referring GP. Search by name; filter internal/external. | #7 |
| 9 | **New Provider**: Dr Casey Brook (synthetic), General practice, provider number `123456AB` → Add. Then add another with the same number. | The duplicate is refused: "Provider number 123456AB is already used by Dr Casey Brook (synthetic)." | #7 |
| 10 | **Delete** Dr Casey Brook with reason "Added in error". | Gone from the directory; the removal is in the audit trail. | #7 |
| 11 | Open **Users** → on Sam Lee's row **Link Provider** → choose a Provider → sign off. | A User's own entry in the directory, so letters and Care Teams can name them. (Dr Rivera is already linked.) | #7 |
| 12 | Sign in as Dr Alex Rivera (Harbourside). **Settings → Sites**. | Harbourside rooms (primary) and Example Hospital clinic. Trial-site distances in Stage 10 are measured from each Site. | #25 |
| 13 | **Add Site**: *Example Private clinic*, with an address and a location → Add Site. Then **Make primary**, and try to delete the old primary. | The primary moves; the primary Site can't be deleted. Every change is in the audit trail. | #25 |

*Care Team (#9) and soft-deleting a Patient (#17) complete Stage 2; their steps are added when they're built.*

**If something goes wrong:** Patients shows "No Patients yet" → run `make demo-data`. A Patient's details fail to load with "can't be decrypted" → the database was filled with a different `VIGIL_ENCRYPTION_KEY`; reset the dev database and reload the demo data.
