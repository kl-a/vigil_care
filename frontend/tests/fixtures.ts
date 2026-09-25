import type { CurrentUser, DevLoginChoice } from "@/lib/session";
import type { JobTitle } from "@/lib/jobTitles";
import type { ModuleConfiguration } from "@/lib/modules/types";
import oncologyActive from "./contracts/oncology-active.json";

const NAMES: Record<JobTitle, string> = {
  clinician: "Dr Alex Rivera",
  trial_coordinator: "Sam Lee",
  secretary: "Jordan Park",
  developer_admin: "Casey Dev",
};

/** A synthetic signed-in User (names from the frontend brief §10). */
export function userWith(jobTitle: JobTitle): CurrentUser {
  return {
    id: `00000000-0000-0000-0000-00000000000${Object.keys(NAMES).indexOf(jobTitle) + 1}`,
    display_name: NAMES[jobTitle],
    job_title: jobTitle,
    practice_id: "00000000-0000-0000-0000-0000000000aa",
    practice_name: "Harbourside Oncology (synthetic)",
  };
}

/** A dev login choice: one of the User's Practice Memberships. */
export function choiceFor(jobTitle: JobTitle): DevLoginChoice {
  return userWith(jobTitle);
}

/** GET /modules/active with Oncology on, exactly as the backend Builder returns it (checked by backend/tests/test_frontend_contract.py). */
export const ONCOLOGY_ON: ModuleConfiguration = oncologyActive;
