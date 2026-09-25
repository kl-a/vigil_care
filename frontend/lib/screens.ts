import { patientTabsFor } from "./modules/registry";
import { NO_MODULES, type ModuleConfiguration, type ScreenInfo } from "./modules/types";

/** Screen inventory from design doc §5 (numbers) plus the developer admin's System status. */
export interface Screen extends ScreenInfo {
  path: string;
}

/** Core screens outside a Patient. Patient screens come from the Patient tabs (Core and modules). */
export const CORE_SCREENS: readonly Screen[] = [
  { number: 1, title: "Login", path: "/login", purpose: "Individual sign-in with 2FA.", stage: 1, built: true },
  { number: 2, title: "Dashboard", path: "/dashboard", purpose: "Practice-wide Open Items.", stage: 5 },
  { number: 3, title: "Patient List", path: "/patients", purpose: "Browse, search and create Patients.", stage: 2 },
  { number: 5, title: "Document Upload", path: "/documents", purpose: "Ingest Documents and follow their status.", stage: 6 },
  { number: 6, title: "Extraction Review", path: "/review", purpose: "Review Extracted Facts one by one.", stage: 9 },
  { number: 7, title: "Redaction QA", path: "/redaction", purpose: "Review and correct PII masking.", stage: 7 },
  { number: 8, title: "Redaction Jobs", path: "/redaction-jobs", purpose: "Standalone de-identification for trial portals and referrals.", stage: 7 },
  { number: 12, title: "Trial Browser", path: "/trials", purpose: "Explore the local trial database.", stage: 10 },
  { number: 14, title: "PBS Drug Lookup", path: "/pbs", purpose: "Quick drug reference.", stage: 3 },
  { number: 17, title: "Provider Management", path: "/providers", purpose: "The Practice's Provider directory.", stage: 2 },
  { number: 18, title: "User Management", path: "/users", purpose: "Manage who can log in.", stage: 1, built: true },
  { number: 19, title: "Settings", path: "/settings", purpose: "System configuration.", stage: 1, built: true },
  { title: "System status", path: "/system", purpose: "Health, pipeline runs, job queue and refresh logs, with no Patient data.", stage: 1, built: true },
];

export function screensFor(modules: ModuleConfiguration): Screen[] {
  const patientScreens = patientTabsFor(modules).map((tab) => ({ ...tab.screen, path: `/patients/[id]/${tab.segment}` }));
  return [...CORE_SCREENS, ...patientScreens];
}

export function screenForPath(path: string, modules: ModuleConfiguration = NO_MODULES): Screen | undefined {
  return screensFor(modules).find((screen) => screen.path === path);
}

/**
 * The screen a URL shows: a Core screen by its first segment (so /users/123 is User Management),
 * or a Patient tab (/patients/42 is the Overview; /patients/42/summary the Summary).
 */
export function screenForPathname(pathname: string, modules: ModuleConfiguration = NO_MODULES): Screen | undefined {
  const [first, patientId, tab] = pathname.split("/").filter(Boolean);
  if (first === "patients" && patientId) return screenForPath(`/patients/[id]/${tab ?? "overview"}`, modules);
  return screenForPath(`/${first ?? ""}`, modules);
}
