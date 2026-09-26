import { fireEvent, render, screen, within } from "@testing-library/react";
import { beforeEach, describe, expect, it, vi } from "vitest";

let pathname = "/system";
vi.mock("next/navigation", () => ({ usePathname: () => pathname, useRouter: () => ({ replace: vi.fn() }) }));

import { PatientTabs } from "@/components/PatientTabs";
import { AppShell } from "@/components/shell/AppShell";
import { ViewerProvider } from "@/components/shell/ViewerProvider";
import { patientTabsFor } from "@/lib/modules/registry";
import { SHIPPED_STAGE, isShipped } from "@/lib/stages";
import { screenForPathname } from "@/lib/screens";
import { ONCOLOGY_ON, userWith } from "./fixtures";

async function renderAt(at: string) {
  pathname = at;
  render(
    <ViewerProvider loadUser={async () => userWith("clinician")}>
      <AppShell><p>placeholder content</p></AppShell>
    </ViewerProvider>,
  );
  await screen.findByRole("navigation", { name: "Main" });
}
const mainNav = () => within(screen.getByRole("navigation", { name: "Main" }));
const showUpcoming = () => fireEvent.click(screen.getByLabelText("Show upcoming screens"));

describe("build stages (design doc §15)", () => {
  beforeEach(() => window.localStorage.clear());

  it("is at Stage 3: Stages 1 to 3 have shipped", () => {
    expect(SHIPPED_STAGE).toBe(3);
    expect(isShipped(3)).toBe(true);
    expect(isShipped(4)).toBe(false);
  });

  it("gives every screen and Patient tab a stage", () => {
    expect(screenForPathname("/users/123")?.stage).toBe(1);
    expect(screenForPathname("/patients")?.stage).toBe(2);
    expect(screenForPathname("/patients/42")?.stage).toBe(2);
    expect(screenForPathname("/patients/42/summary")?.stage).toBe(5);
    expect(screenForPathname("/patients/42/treatment-options", ONCOLOGY_ON)?.stage).toBe(11);
    for (const tab of patientTabsFor(ONCOLOGY_ON)) expect(tab.screen.stage).toBeGreaterThan(0);
  });

  it("shows only built screens of shipped stages in the navigation", async () => {
    await renderAt("/system");
    for (const released of ["Patients", "PBS lookup", "Providers", "Users", "Settings", "System status"]) {
      expect(mainNav().getByRole("link", { name: released })).toBeInTheDocument();
    }
    for (const upcoming of ["Dashboard", "Trials", "Review queue", "Documents"]) {
      expect(mainNav().queryByRole("link", { name: upcoming })).not.toBeInTheDocument();
    }
  });

  it.each(["/review", "/dashboard"])("shows a friendly page, not a placeholder, at %s", async (path) => {
    await renderAt(path);
    expect(screen.getByRole("heading", { name: "Not available yet" })).toBeInTheDocument();
    expect(screen.queryByText("placeholder content")).not.toBeInTheDocument();
  });

  it("reveals upcoming screens as labelled placeholders when the dev toggle is on", async () => {
    await renderAt("/review");
    showUpcoming();
    expect(screen.getByText("placeholder content")).toBeInTheDocument();
    expect(screen.getByRole("note")).toHaveTextContent("coming in Stage 9");
    expect(mainNav().getByRole("link", { name: /Review queue/ })).toHaveTextContent("S9");
    expect(window.localStorage.getItem("vigil.showUpcoming")).toBe("true");
  });

  it("still refuses a screen the Job Title can't use, whatever the stage", async () => {
    pathname = "/patients/42";
    render(
      <ViewerProvider loadUser={async () => userWith("developer_admin")}>
        <AppShell><p>placeholder content</p></AppShell>
      </ViewerProvider>,
    );
    await screen.findByRole("navigation", { name: "Main" });
    showUpcoming();
    expect(screen.getByRole("heading", { name: "Not available for your Job Title" })).toBeInTheDocument();
  });

  it("shows only the built tabs of shipped stages on a Patient (the Overview) until upcoming ones are revealed", async () => {
    pathname = "/patients/42/overview";
    render(
      <ViewerProvider initialUser={userWith("clinician")} loadModules={async () => ONCOLOGY_ON}>
        <PatientTabs patientId="42" />
      </ViewerProvider>,
    );
    const tabs = within(await screen.findByRole("navigation", { name: "Patient" }));
    expect(tabs.getAllByRole("link").map((link) => link.textContent)).toEqual(["Overview"]);
  });
});
