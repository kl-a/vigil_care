import { describe, expect, it } from "vitest";
import { canAccess, navigationFor, standInFor } from "@/lib/navigation";
import { homePath, seesPatientData } from "@/lib/jobTitles";

const labels = (items: { label: string }[]) => items.map((i) => i.label);

describe("navigation by Job Title", () => {
  it("gives clinicians every item", () => {
    const nav = navigationFor("clinician");
    expect(labels(nav.main)).toEqual(["Dashboard", "Patients", "Review queue", "Documents", "Redaction", "Jobs", "Trials", "PBS lookup"]);
    expect(labels(nav.admin)).toEqual(["Providers", "Users", "Settings", "System status"]);
  });

  it("never shows developer admins anything with Patient data", () => {
    const nav = navigationFor("developer_admin");
    expect(nav.main).toEqual([]);
    expect(labels(nav.admin)).toEqual(["Users", "Settings", "System status"]);
  });

  it("hides Users and Settings from trial coordinators", () => {
    expect(labels(navigationFor("trial_coordinator").admin)).toEqual(["Providers", "System status"]);
  });

  it("lets secretaries manage Users but not Settings", () => {
    expect(labels(navigationFor("secretary").admin)).toEqual(["Providers", "Users", "System status"]);
  });
});

describe("route access", () => {
  it("blocks developer admins from every Patient route and the Dashboard", () => {
    for (const path of ["/patients", "/patients/jane/summary", "/dashboard", "/review", "/redaction/doc_1", "/pbs"]) {
      expect(canAccess(path, "developer_admin"), path).toBe(false);
    }
    expect(canAccess("/system", "developer_admin")).toBe(true);
    expect(canAccess("/users", "developer_admin")).toBe(true);
  });

  it("gives developer admins System status in place of the Dashboard, and nothing else", () => {
    expect(standInFor("/dashboard", "developer_admin")).toBe("/system");
    expect(standInFor("/dashboard", "clinician")).toBeUndefined();
    expect(standInFor("/patients", "developer_admin")).toBeUndefined();
  });

  it("blocks trial coordinators from Users and Settings", () => {
    expect(canAccess("/users", "trial_coordinator")).toBe(false);
    expect(canAccess("/settings", "trial_coordinator")).toBe(false);
    expect(canAccess("/patients/jane/summary", "trial_coordinator")).toBe(true);
  });

  it("treats developer admins as the only Job Title that never sees Patient data", () => {
    expect(seesPatientData("developer_admin")).toBe(false);
    expect(["clinician", "trial_coordinator", "secretary"].every((t) => seesPatientData(t as never))).toBe(true);
  });

  it("sends everyone home to System status until the Dashboard ships in Stage 5", () => {
    expect(homePath("developer_admin")).toBe("/system");
    expect(homePath("secretary")).toBe("/system");
  });
});
