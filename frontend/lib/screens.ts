import { ACTIVE_MODULES, patientTabsFor } from "./modules/registry";
import type { ModuleKey, ScreenInfo } from "./modules/types";

/** Screen inventory from design doc §5 (numbers) plus the developer admin's System status. */
export interface Screen extends ScreenInfo {
  path: string;
}

/** Core screens outside a Patient. Patient screens come from the Patient tabs (Core and modules). */
export const CORE_SCREENS: readonly Screen[] = [
  { number: 1, title: "Login", path: "/login", purpose: "Individual sign-in with 2FA." },
  { number: 2, title: "Dashboard", path: "/dashboard", purpose: "Practice-wide Open Items." },
  { number: 3, title: "Patient List", path: "/patients", purpose: "Browse, search and create Patients." },
  { number: 5, title: "Document Upload", path: "/documents", purpose: "Ingest Documents and follow their status." },
  { number: 6, title: "Extraction Review", path: "/review", purpose: "Review Extracted Facts one by one." },
  { number: 7, title: "Redaction QA", path: "/redaction", purpose: "Review and correct PII masking." },
  { number: 8, title: "Redaction Jobs", path: "/redaction-jobs", purpose: "Standalone de-identification for trial portals and referrals." },
  { number: 12, title: "Trial Browser", path: "/trials", purpose: "Explore the local trial database." },
  { number: 14, title: "PBS Drug Lookup", path: "/pbs", purpose: "Quick drug reference." },
  { number: 17, title: "Provider Management", path: "/providers", purpose: "The Practice's Provider directory." },
  { number: 18, title: "User Management", path: "/users", purpose: "Manage who can log in." },
  { number: 19, title: "Settings", path: "/settings", purpose: "System configuration." },
  { title: "System status", path: "/system", purpose: "Health, pipeline runs, job queue and refresh logs, with no Patient data." },
];

export function screensFor(activeModules: readonly ModuleKey[]): Screen[] {
  const patientScreens = patientTabsFor(activeModules).map((tab) => ({ ...tab.screen, path: `/patients/[id]/${tab.segment}` }));
  return [...CORE_SCREENS, ...patientScreens];
}

export function screenForPath(path: string, activeModules: readonly ModuleKey[] = ACTIVE_MODULES): Screen | undefined {
  return screensFor(activeModules).find((screen) => screen.path === path);
}
