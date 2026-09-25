import { fireEvent, render, screen, waitFor, within } from "@testing-library/react";
import { beforeEach, describe, expect, it, vi } from "vitest";

vi.mock("next/navigation", () => ({ usePathname: () => "/settings", useRouter: () => ({ replace: vi.fn() }) }));

const practice = vi.hoisted(() => ({ fetchPractice: vi.fn(), changePractice: vi.fn() }));
vi.mock("@/lib/practice", () => practice);
const sites = vi.hoisted(() => ({ listSites: vi.fn(), addSite: vi.fn(), changeSite: vi.fn(), deleteSite: vi.fn() }));
vi.mock("@/lib/sites", () => sites);
const modules = vi.hoisted(() => ({ listModules: vi.fn(), setModuleActive: vi.fn(), fetchModuleConfiguration: vi.fn() }));
vi.mock("@/lib/modules/api", () => modules);

import SettingsPage from "@/app/(app)/settings/page";
import { ViewerProvider } from "@/components/shell/ViewerProvider";
import type { JobTitle } from "@/lib/jobTitles";
import { ONCOLOGY_ON, userWith } from "./fixtures";

const DETAILS = {
  id: "p-1", name: "Harbourside Oncology (synthetic)", address: "1 Example St, Sydney NSW 2000", phone: "02 5550 0100",
  fax: null, email: null, abn: null,
};
const ROOMS = { id: "s-1", name: "Harbourside rooms", address: "1 Example St, Sydney NSW 2000", lat: -33.8688, lng: 151.2093, is_primary: true };
const CLINIC = { id: "s-2", name: "Example Hospital clinic", address: "2 Example Rd", lat: -33.8898, lng: 151.1873, is_primary: false };

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
    window.localStorage.clear();
    sites.listSites.mockResolvedValue([ROOMS, CLINIC]);
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
    fireEvent.click(screen.getByRole("button", { name: "Save details" }));
    await waitFor(() => expect(practice.changePractice).toHaveBeenCalledWith({ phone: "02 5550 0199" }));
    expect(await screen.findByText(/in the audit trail under your name/)).toBeInTheDocument();
  });

  describe("Sites", () => {
    it("lists the Practice's Sites with the primary marked", async () => {
      renderAs("clinician");
      const list = await screen.findByRole("list", { name: "Sites" });
      const rooms = within(list).getByText("Harbourside rooms").closest("li")!;
      expect(rooms).toHaveTextContent("Primary");
      expect(within(list).getByText("Example Hospital clinic").closest("li")).not.toHaveTextContent("Primary");
    });

    it("adds a Site, checking the location is a number first", async () => {
      sites.addSite.mockResolvedValue({ ...CLINIC, id: "s-3", name: "Northside clinic" });
      renderAs("developer_admin");
      fireEvent.click(await screen.findByRole("button", { name: "Add Site" }));
      const form = screen.getByRole("form", { name: "New Site" });
      fireEvent.change(within(form).getByLabelText("Name"), { target: { value: "Northside clinic" } });
      fireEvent.change(within(form).getByLabelText(/Latitude/), { target: { value: "north" } });
      fireEvent.submit(form);
      expect(await within(form).findByRole("alert")).toHaveTextContent("must be numbers");
      expect(sites.addSite).not.toHaveBeenCalled();

      fireEvent.change(within(form).getByLabelText(/Latitude/), { target: { value: "-33.79" } });
      fireEvent.change(within(form).getByLabelText(/Longitude/), { target: { value: "151.18" } });
      fireEvent.submit(form);
      await waitFor(() => expect(sites.addSite).toHaveBeenCalledWith({ name: "Northside clinic", address: null, lat: -33.79, lng: 151.18 }));
    });

    it("makes another Site primary", async () => {
      sites.changeSite.mockResolvedValue({ ...CLINIC, is_primary: true });
      renderAs("clinician");
      const clinic = (await screen.findByText("Example Hospital clinic")).closest("li")!;
      fireEvent.click(within(clinic).getByRole("button", { name: "Make primary" }));
      await waitFor(() => expect(sites.changeSite).toHaveBeenCalledWith("s-2", { is_primary: true }));
    });

    it("deletes a Site with a reason, but never the primary", async () => {
      sites.deleteSite.mockResolvedValue(undefined);
      renderAs("clinician");
      const rooms = (await screen.findByText("Harbourside rooms")).closest("li")!;
      expect(within(rooms).queryByRole("button", { name: "Delete" })).not.toBeInTheDocument();
      const clinic = screen.getByText("Example Hospital clinic").closest("li")!;
      fireEvent.click(within(clinic).getByRole("button", { name: "Delete" }));
      const dialog = screen.getByRole("dialog");
      fireEvent.change(within(dialog).getByLabelText("Reason (required)"), { target: { value: "Clinic closed" } });
      fireEvent.click(within(dialog).getByRole("button", { name: "Delete Site" }));
      await waitFor(() => expect(sites.deleteSite).toHaveBeenCalledWith("s-2", "Clinic closed"));
    });

    it("shows Sites read-only to Job Titles that don't change Settings", async () => {
      renderAs("secretary");
      await screen.findByRole("list", { name: "Sites" });
      expect(screen.queryByRole("button", { name: "Add Site" })).not.toBeInTheDocument();
      expect(screen.queryByRole("button", { name: "Make primary" })).not.toBeInTheDocument();
    });
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
