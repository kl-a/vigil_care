import type { JobTitle } from "./jobTitles";
import { screenForPath, type Screen } from "./screens";

export type NavIcon =
  | "layout-dashboard" | "users" | "inbox" | "file-text" | "eye-off" | "folder-kanban"
  | "flask-conical" | "pill" | "stethoscope" | "user-cog" | "settings" | "activity";

export interface NavItem {
  id: string;
  label: string;
  href: string;
  icon: NavIcon;
  jobTitles: readonly JobTitle[];
  /** Indented under the previous item (e.g. Redaction → Jobs). */
  sub?: boolean;
}

const STAFF: readonly JobTitle[] = ["clinician", "trial_coordinator", "secretary"];

/** Main navigation: every item shows Patient data, so developer admins never get it. */
export const MAIN_NAV: readonly NavItem[] = [
  { id: "dashboard", label: "Dashboard", href: "/dashboard", icon: "layout-dashboard", jobTitles: STAFF },
  { id: "patients", label: "Patients", href: "/patients", icon: "users", jobTitles: STAFF },
  { id: "review", label: "Review queue", href: "/review", icon: "inbox", jobTitles: STAFF },
  { id: "documents", label: "Documents", href: "/documents", icon: "file-text", jobTitles: STAFF },
  { id: "redaction", label: "Redaction", href: "/redaction", icon: "eye-off", jobTitles: STAFF },
  { id: "redaction-jobs", label: "Jobs", href: "/redaction-jobs", icon: "folder-kanban", jobTitles: STAFF, sub: true },
  { id: "trials", label: "Trials", href: "/trials", icon: "flask-conical", jobTitles: STAFF },
  { id: "pbs", label: "PBS lookup", href: "/pbs", icon: "pill", jobTitles: STAFF },
];

export const ADMIN_NAV: readonly NavItem[] = [
  { id: "providers", label: "Providers", href: "/providers", icon: "stethoscope", jobTitles: STAFF },
  { id: "users", label: "Users", href: "/users", icon: "user-cog", jobTitles: ["clinician", "secretary", "developer_admin"] },
  { id: "settings", label: "Settings", href: "/settings", icon: "settings", jobTitles: ["clinician", "developer_admin"] },
  { id: "system", label: "System status", href: "/system", icon: "activity", jobTitles: [...STAFF, "developer_admin"] },
];

function allows(item: NavItem, jobTitle: JobTitle): boolean {
  return item.jobTitles.includes(jobTitle);
}

/** The screen a nav item opens (it carries the stage and whether it's built). */
export function screenOf(item: NavItem): Screen {
  const screen = screenForPath(item.href);
  if (!screen) throw new Error(`No screen for nav item ${item.href}`);
  return screen;
}

/** The items a Job Title may use, limited to screens `visible` accepts (design doc §15). */
export function navigationFor(jobTitle: JobTitle, visible: (screen: Screen) => boolean = () => true): { main: NavItem[]; admin: NavItem[] } {
  const show = (item: NavItem) => allows(item, jobTitle) && visible(screenOf(item));
  return { main: MAIN_NAV.filter(show), admin: ADMIN_NAV.filter(show) };
}

/** The nav item a path belongs to: its first segment ("/patients/x/summary" → patients). */
export function navItemForPath(pathname: string): NavItem | undefined {
  const first = pathname.split("/").filter(Boolean)[0];
  return [...MAIN_NAV, ...ADMIN_NAV].find((item) => item.href === `/${first}`);
}

/** Whether a Job Title may open a path. Unknown paths are left to the router's 404. */
export function canAccess(pathname: string, jobTitle: JobTitle): boolean {
  const item = navItemForPath(pathname);
  return item ? allows(item, jobTitle) : true;
}
