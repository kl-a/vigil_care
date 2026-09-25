/** Screen inventory from design doc §5 (numbers) plus the developer admin's System status. */
export interface Screen {
  number?: number;
  title: string;
  path: string;
  purpose: string;
}

export const SCREENS: readonly Screen[] = [
  { number: 1, title: "Login", path: "/login", purpose: "Individual sign-in with 2FA." },
  { number: 2, title: "Dashboard", path: "/dashboard", purpose: "Practice-wide Open Items." },
  { number: 3, title: "Patient List", path: "/patients", purpose: "Browse, search and create Patients." },
  { number: 4, title: "Patient Overview", path: "/patients/[id]/overview", purpose: "Clinical profile for one Patient." },
  { number: 5, title: "Document Upload", path: "/documents", purpose: "Ingest Documents and follow their status." },
  { number: 6, title: "Extraction Review", path: "/review", purpose: "Review Extracted Facts one by one." },
  { number: 7, title: "Redaction QA", path: "/redaction", purpose: "Review and correct PII masking." },
  { number: 8, title: "Redaction Jobs", path: "/redaction-jobs", purpose: "Standalone de-identification for trial portals and referrals." },
  { number: 9, title: "Clinical Data Viewer", path: "/patients/[id]/clinical-data", purpose: "Longitudinal Clinical Record." },
  { number: 10, title: "Medication Manager", path: "/patients/[id]/medications", purpose: "Medication list with reconciliation." },
  { number: 11, title: "Treatment Options", path: "/patients/[id]/treatment-options", purpose: "Standard-of-care options for one Condition (Oncology module)." },
  { number: 12, title: "Trial Browser", path: "/trials", purpose: "Explore the local trial database." },
  { number: 13, title: "Match Board", path: "/patients/[id]/trials", purpose: "Patient vs trials for a target Condition." },
  { number: 14, title: "PBS Drug Lookup", path: "/pbs", purpose: "Quick drug reference." },
  { number: 15, title: "Patient Summary", path: "/patients/[id]/summary", purpose: "The consultation-ready “At a Glance” page." },
  { number: 16, title: "Exports", path: "/patients/[id]/exports", purpose: "Generate and sign off Identified or De-identified Exports." },
  { number: 17, title: "Provider Management", path: "/providers", purpose: "The Practice's Provider directory." },
  { number: 18, title: "User Management", path: "/users", purpose: "Manage who can log in." },
  { number: 19, title: "Settings", path: "/settings", purpose: "System configuration." },
  { title: "Patient Documents", path: "/patients/[id]/documents", purpose: "This Patient's Documents." },
  { title: "System status", path: "/system", purpose: "Health, pipeline runs, job queue and refresh logs, with no Patient data." },
];

export function screenForPath(path: string): Screen | undefined {
  return SCREENS.find((screen) => screen.path === path);
}

/** "/patients/[id]/summary" → "(app)/patients/[id]/[tab]/page.tsx"; module tabs share one dynamic route. */
export function routeFileFor(path: string): string {
  if (path === "/login") return "login/page.tsx";
  if (path.startsWith("/patients/[id]/")) return "(app)/patients/[id]/[tab]/page.tsx";
  return `(app)${path}/page.tsx`;
}
