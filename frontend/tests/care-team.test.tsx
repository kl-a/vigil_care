import { fireEvent, render, screen, waitFor, within } from "@testing-library/react";
import { beforeEach, describe, expect, it, vi } from "vitest";

vi.mock("next/navigation", () => ({ usePathname: () => "/patients/pt-1/overview", useRouter: () => ({ replace: vi.fn(), push: vi.fn() }) }));

const patients = vi.hoisted(() => ({ fetchPatient: vi.fn() }));
vi.mock("@/lib/patients", async (importOriginal) => ({ ...(await importOriginal<object>()), ...patients }));
const careTeam = vi.hoisted(() => ({ fetchCareTeam: vi.fn(), addCareTeamMember: vi.fn(), changeCareTeamMember: vi.fn(), fetchProviderPatients: vi.fn() }));
vi.mock("@/lib/careTeam", async (importOriginal) => ({ ...(await importOriginal<object>()), ...careTeam }));
const providers = vi.hoisted(() => ({ listProviders: vi.fn(), fetchProvider: vi.fn() }));
vi.mock("@/lib/providers", async (importOriginal) => ({ ...(await importOriginal<object>()), ...providers }));

import ProviderPage from "@/app/(app)/providers/[id]/page";
import { CareTeam } from "@/components/patients/CareTeam";
import { PatientHeader, PatientProvider } from "@/components/patients/PatientContext";
import { ViewerProvider } from "@/components/shell/ViewerProvider";
import type { CareTeamRow } from "@/lib/careTeam";
import type { ProviderRow } from "@/lib/providers";
import { userWith } from "./fixtures";

const member = (overrides: Partial<CareTeamRow>): CareTeamRow => ({
  id: "m-1", provider_id: "p-1", provider_name: "Dr Alex Rivera", role: "treating_oncologist", is_primary: true,
  start_date: "2024-03-01", end_date: null, notes: null, is_current: true, ...overrides,
});
const TEAM = [
  member({}),
  member({ id: "m-2", provider_id: "p-2", provider_name: "Dr Morgan Grey", role: "referring_gp", is_primary: false, start_date: "2024-02-12" }),
  member({ id: "m-3", provider_id: "p-3", provider_name: "Dr Taylor Quinn", role: "surgeon", is_primary: false, end_date: "2024-06-30", is_current: false }),
];
const GREY: ProviderRow = {
  id: "p-2", display_name: "Dr Morgan Grey", title: "Dr", first_name: "Morgan", last_name: "Grey", provider_number: null,
  specialty: "general_practice", is_internal: false, organisation: "Example Family Practice", phone: null, email: null, fax: null, notes: null,
};

function renderPatient() {
  render(
    <ViewerProvider initialUser={userWith("secretary")}>
      <PatientProvider patientId="pt-1"><PatientHeader /><CareTeam /></PatientProvider>
    </ViewerProvider>,
  );
}

describe("Care Team", () => {
  beforeEach(() => {
    vi.clearAllMocks();
    patients.fetchPatient.mockResolvedValue({ id: "pt-1", pseudonym: "VG-0042", display_name: "Jane Citizen (synthetic)", identity: { dob: null, mrn: "1002003" }, history: [] });
    careTeam.fetchCareTeam.mockResolvedValue(TEAM);
    providers.listProviders.mockResolvedValue([GREY]);
  });

  it("puts the primary member in the Patient header", async () => {
    renderPatient();
    const header = await screen.findByRole("region", { name: "Patient" });
    await waitFor(() => expect(header).toHaveTextContent("Treating oncologist: Dr Alex Rivera"));
  });

  it("shows current members with role and dates, and ended ones as past", async () => {
    renderPatient();
    const current = await screen.findByRole("list", { name: "Current Care Team" });
    expect(within(current).getAllByRole("listitem").map((li) => li.textContent)).toEqual([
      expect.stringContaining("Dr Alex Rivera"),
      expect.stringContaining("Dr Morgan Grey"),
    ]);
    expect(within(current).getByText("Dr Alex Rivera").closest("li")).toHaveTextContent("Primary");
    expect(within(current).getByText("Dr Alex Rivera").closest("li")).toHaveTextContent("since 01/03/2024");
    const past = screen.getByRole("list", { name: "Past Care Team" });
    expect(past).toHaveTextContent("Dr Taylor Quinn");
    expect(past).toHaveTextContent("until 30/06/2024");
  });

  it("adds a Provider in a role", async () => {
    careTeam.addCareTeamMember.mockResolvedValue(member({ id: "m-4" }));
    renderPatient();
    fireEvent.click(await screen.findByRole("button", { name: "Add to Care Team" }));
    const form = screen.getByRole("form", { name: "Add to Care Team" });
    fireEvent.change(await within(form).findByLabelText("Provider"), { target: { value: "p-2" } });
    fireEvent.change(within(form).getByLabelText("Role"), { target: { value: "referring_gp" } });
    fireEvent.change(within(form).getByLabelText("Start date"), { target: { value: "2024-02-12" } });
    fireEvent.click(within(form).getByLabelText("Primary member"));
    fireEvent.submit(form);
    await waitFor(() => expect(careTeam.addCareTeamMember).toHaveBeenCalledWith("pt-1", {
      provider_id: "p-2", role: "referring_gp", is_primary: true, start_date: "2024-02-12", end_date: null, notes: null,
    }));
  });

  it("ends a membership on a chosen date", async () => {
    careTeam.changeCareTeamMember.mockResolvedValue(member({ id: "m-2", end_date: "2026-09-01", is_current: false }));
    renderPatient();
    const grey = (await screen.findByText("Dr Morgan Grey")).closest("li")!;
    fireEvent.click(within(grey).getByRole("button", { name: "End" }));
    fireEvent.change(within(grey).getByLabelText("End date"), { target: { value: "2026-09-01" } });
    fireEvent.click(within(grey).getByRole("button", { name: "End membership" }));
    await waitFor(() => expect(careTeam.changeCareTeamMember).toHaveBeenCalledWith("pt-1", "m-2", { end_date: "2026-09-01" }));
  });

  it("makes another current member primary", async () => {
    careTeam.changeCareTeamMember.mockResolvedValue(member({ id: "m-2" }));
    renderPatient();
    const grey = (await screen.findByText("Dr Morgan Grey")).closest("li")!;
    fireEvent.click(within(grey).getByRole("button", { name: "Make primary" }));
    await waitFor(() => expect(careTeam.changeCareTeamMember).toHaveBeenCalledWith("pt-1", "m-2", { is_primary: true }));
  });
});

describe("Provider page", () => {
  beforeEach(() => {
    vi.clearAllMocks();
    providers.fetchProvider.mockResolvedValue(GREY);
    careTeam.fetchProviderPatients.mockResolvedValue([
      { care_team_member_id: "m-2", patient_id: "pt-1", patient_name: "Jane Citizen (synthetic)", role: "referring_gp", is_primary: false, start_date: "2024-02-12", end_date: null, is_current: true },
    ]);
  });

  it("shows the Provider and the Patients they're involved with, in what role", async () => {
    render(<ViewerProvider initialUser={userWith("clinician")}><ProviderPage params={{ id: "p-2" }} /></ViewerProvider>);
    expect(await screen.findByRole("heading", { name: "Dr Morgan Grey" })).toBeInTheDocument();
    const jane = (await screen.findByRole("link", { name: "Jane Citizen (synthetic)" })).closest("tr")!;
    expect(within(jane).getByRole("link")).toHaveAttribute("href", "/patients/pt-1/overview");
    expect(jane).toHaveTextContent("Referring GP");
    expect(jane).toHaveTextContent("Current");
  });
});

describe("Care Team that can't be read", () => {
  it("says why instead of loading forever", async () => {
    patients.fetchPatient.mockResolvedValue({ id: "pt-1", pseudonym: "VG-0042", display_name: "Jane Citizen (synthetic)", identity: { dob: null, mrn: null }, history: [] });
    careTeam.fetchCareTeam.mockRejectedValue(new Error("The request failed (500)."));
    renderPatient();
    expect(await screen.findByRole("alert")).toHaveTextContent("The request failed (500).");
    expect(screen.queryByText("Loading Care Team…")).not.toBeInTheDocument();
  });
});
