import { fireEvent, render, screen, waitFor, within } from "@testing-library/react";
import { beforeEach, describe, expect, it, vi } from "vitest";

vi.mock("next/navigation", () => ({ usePathname: () => "/settings", useRouter: () => ({ replace: vi.fn() }) }));

const practice = vi.hoisted(() => ({ fetchPractice: vi.fn(), changePractice: vi.fn() }));
vi.mock("@/lib/practice", () => practice);
const modules = vi.hoisted(() => ({ listModules: vi.fn(), setModuleActive: vi.fn(), fetchModuleConfiguration: vi.fn() }));
vi.mock("@/lib/modules/api", () => modules);

import SettingsPage from "@/app/(app)/settings/page";
import { ViewerProvider } from "@/components/shell/ViewerProvider";
import type { JobTitle } from "@/lib/jobTitles";
import { ONCOLOGY_ON, userWith } from "./fixtures";

const DETAILS = {
  id: "p-1", name: "Harbourside Oncology (synthetic)", address: "1 Example St, Sydney NSW 2000", phone: "02 5550 0100",
  fax: null, email: null, abn: null, lat: -33.8688, lng: 151.2093,
};

function renderAs(jobTitle: JobTitle) {
  render(
    <ViewerProvider initialUser={userWith(jobTitle)} loadModules={modules.fetchModuleConfiguration}>
      <SettingsPage />
    </ViewerProvider>,
  );
}

describe("Settings", () => {
  beforeEach(() => {
    vi.clearAllMocks();
    practice.fetchPractice.mockResolvedValue(DETAILS);
    practice.changePractice.mockImplementation(async (change: object) => ({ ...DETAILS, ...change }));
    modules.listModules.mockResolvedValue([{ key: "oncology", display_name: "Oncology", version: "0.1.0", is_active: true }]);
    modules.fetchModuleConfiguration.mockResolvedValue(ONCOLOGY_ON);
    modules.setModuleActive.mockResolvedValue({ key: "oncology", display_name: "Oncology", version: "0.1.0", is_active: false });
  });

  it("saves only the Practice details that changed", async () => {
    renderAs("clinician");
    const phone = await screen.findByLabelText("Phone");
    fireEvent.change(phone, { target: { value: "02 5550 0199" } });
    fireEvent.change(screen.getByLabelText(/Latitude/), { target: { value: "-33.9" } });
    fireEvent.click(screen.getByRole("button", { name: "Save details" }));
    await waitFor(() => expect(practice.changePractice).toHaveBeenCalledWith({ phone: "02 5550 0199", lat: -33.9 }));
    expect(await screen.findByText(/in the audit trail under your name/)).toBeInTheDocument();
  });

  it("refuses a location that isn't a number before asking the backend", async () => {
    renderAs("clinician");
    fireEvent.change(await screen.findByLabelText(/Latitude/), { target: { value: "north" } });
    fireEvent.click(screen.getByRole("button", { name: "Save details" }));
    expect(await screen.findByRole("alert")).toHaveTextContent("must be numbers");
    expect(practice.changePractice).not.toHaveBeenCalled();
  });

  it("lets a developer admin switch Oncology off, as a sign-off, and reloads the active modules", async () => {
    renderAs("developer_admin");
    fireEvent.click(await screen.findByRole("button", { name: "Switch Oncology off" }));
    const dialog = screen.getByRole("dialog");
    expect(dialog).toHaveTextContent("Its data is kept.");
    fireEvent.change(within(dialog).getByLabelText("Reason (optional)"), { target: { value: "Pausing oncology" } });
    fireEvent.click(within(dialog).getByRole("checkbox"));
    fireEvent.click(within(dialog).getByRole("button", { name: "Switch off" }));
    await waitFor(() => expect(modules.setModuleActive).toHaveBeenCalledWith("oncology", { is_active: false, reason: "Pausing oncology" }));
    await waitFor(() => expect(modules.fetchModuleConfiguration).toHaveBeenCalledTimes(2));
  });

  it("shows clinicians the modules but no switch", async () => {
    renderAs("clinician");
    const list = await screen.findByRole("list", { name: "Specialty Modules" });
    expect(within(list).getByText("On")).toBeInTheDocument();
    expect(screen.queryByRole("button", { name: /Switch Oncology/ })).not.toBeInTheDocument();
    expect(screen.getByText("Only a developer admin switches modules on or off.")).toBeInTheDocument();
  });
});
