import { fireEvent, render, screen, waitFor, within } from "@testing-library/react";
import { beforeEach, describe, expect, it, vi } from "vitest";

const push = vi.fn();
vi.mock("next/navigation", () => ({ usePathname: () => "/patients", useRouter: () => ({ replace: vi.fn(), push }), notFound: vi.fn() }));

const patients = vi.hoisted(() => ({ listPatients: vi.fn(), fetchPatient: vi.fn(), createPatient: vi.fn(), changeIdentity: vi.fn() }));
vi.mock("@/lib/patients", async (importOriginal) => ({ ...(await importOriginal<object>()), ...patients }));

import PatientsPage from "@/app/(app)/patients/page";
import { PatientHeader, PatientProvider } from "@/components/patients/PatientContext";
import { PatientOverview } from "@/components/patients/PatientOverview";
import { ViewerProvider } from "@/components/shell/ViewerProvider";
import { formatDob, type PatientDetail, type PatientIdentity } from "@/lib/patients";
import { userWith } from "./fixtures";

const JANE: PatientIdentity = {
  given_name: "Jane", family_name: "Citizen (synthetic)", dob: "1962-04-03", medicare_number: "0000 00042 1", medicare_irn: "1",
  ihi: "0000 0000 0000 0042", mrn: "1002003", address: "10 Example Ave, Sydney NSW 2000", phone: "02 5550 0142",
  mobile: "0491 570 156", email: "jane.citizen@example.com", next_of_kin_name: "John Citizen (synthetic), husband", next_of_kin_phone: "0491 570 157",
};
const DETAIL: PatientDetail = {
  id: "pt-1", pseudonym: "VG-0042", display_name: "Jane Citizen (synthetic)", identity: JANE,
  history: [
    { action: "edit", by_display_name: "Jordan Park (synthetic)", by_job_title: "secretary", before: { mobile: "0491 570 100" }, after: { mobile: "0491 570 156" }, reason: null, at: "2026-09-25T01:00:00Z" },
    { action: "edit", by_display_name: "Casey Dev (synthetic)", by_job_title: "clinician", before: null, after: { given_name: "Jane" }, reason: null, at: "2026-09-24T01:00:00Z" },
  ],
};

function renderAs(ui: React.ReactNode) {
  render(<ViewerProvider initialUser={userWith("secretary")}>{ui}</ViewerProvider>);
}

describe("Patient List", () => {
  beforeEach(() => {
    vi.clearAllMocks();
    patients.listPatients.mockResolvedValue([
      { id: "pt-1", pseudonym: "VG-0042", display_name: "Jane Citizen (synthetic)", dob: "1962-04-03", mrn: "1002003", updated_at: "2026-09-25T01:00:00Z" },
      { id: "pt-2", pseudonym: "VG-0043", display_name: "Sam Example (synthetic)", dob: null, mrn: "1002017", updated_at: "2026-09-25T01:00:00Z" },
    ]);
  });

  it("lists Patients with DOB and age, MRN and Pseudonym, each linking to their Overview", async () => {
    renderAs(<PatientsPage />);
    const jane = (await screen.findByText("Jane Citizen (synthetic)")).closest("tr")!;
    expect(jane).toHaveTextContent("03/04/1962");
    expect(jane).toHaveTextContent("1002003");
    expect(jane).toHaveTextContent("VG-0042");
    expect(within(jane).getByRole("link", { name: "Jane Citizen (synthetic)" })).toHaveAttribute("href", "/patients/pt-1/overview");
  });

  it("searches by name or MRN", async () => {
    renderAs(<PatientsPage />);
    await screen.findByText("Jane Citizen (synthetic)");
    fireEvent.change(screen.getByLabelText("Search by name or MRN"), { target: { value: "citi" } });
    await waitFor(() => expect(patients.listPatients).toHaveBeenLastCalledWith("citi"));
  });

  it("creates a Patient with their identity and opens their Overview", async () => {
    patients.createPatient.mockResolvedValue(DETAIL);
    renderAs(<PatientsPage />);
    fireEvent.click(await screen.findByRole("button", { name: "New Patient" }));
    const form = screen.getByRole("form", { name: "New Patient" });
    fireEvent.change(within(form).getByLabelText("Given name"), { target: { value: "Jane" } });
    fireEvent.change(within(form).getByLabelText("Family name"), { target: { value: "Citizen" } });
    fireEvent.change(within(form).getByLabelText("Date of birth"), { target: { value: "1962-04-03" } });
    fireEvent.change(within(form).getByLabelText(/Medicare number/), { target: { value: "0000 00042 1" } });
    fireEvent.submit(form);
    await waitFor(() => expect(patients.createPatient).toHaveBeenCalledWith({
      given_name: "Jane", family_name: "Citizen", dob: "1962-04-03", medicare_number: "0000 00042 1",
    }));
    await waitFor(() => expect(push).toHaveBeenCalledWith("/patients/pt-1/overview"));
  });

  it("shows why the backend refused", async () => {
    patients.createPatient.mockRejectedValue(new Error("A Medicare number has 10 digits."));
    renderAs(<PatientsPage />);
    fireEvent.click(await screen.findByRole("button", { name: "New Patient" }));
    const form = screen.getByRole("form", { name: "New Patient" });
    fireEvent.change(within(form).getByLabelText("Given name"), { target: { value: "Jane" } });
    fireEvent.change(within(form).getByLabelText("Family name"), { target: { value: "Citizen" } });
    fireEvent.submit(form);
    expect(await within(form).findByRole("alert")).toHaveTextContent("10 digits");
  });
});

describe("Patient header and Overview", () => {
  beforeEach(() => {
    vi.clearAllMocks();
    patients.fetchPatient.mockResolvedValue(DETAIL);
  });

  function renderPatient() {
    renderAs(<PatientProvider patientId="pt-1"><PatientHeader /><PatientOverview /></PatientProvider>);
  }

  it("heads every Patient screen with name, DOB and age, MRN and Pseudonym", async () => {
    renderPatient();
    const header = await screen.findByRole("region", { name: "Patient" });
    expect(header).toHaveTextContent("Jane Citizen (synthetic)");
    expect(header).toHaveTextContent(formatDob("1962-04-03"));
    expect(header).toHaveTextContent("MRN 1002003");
    expect(header).toHaveTextContent("VG-0042");
  });

  it("shows the full Patient Identity", async () => {
    renderPatient();
    const card = await screen.findByRole("region", { name: "Patient Identity" });
    expect(card).toHaveTextContent("0000 00042 1");
    expect(card).toHaveTextContent("jane.citizen@example.com");
    expect(card).toHaveTextContent("John Citizen (synthetic), husband");
  });

  it("edits the identity, sending only what changed", async () => {
    patients.changeIdentity.mockResolvedValue({ ...DETAIL, identity: { ...JANE, mobile: "0491 570 158" } });
    renderPatient();
    fireEvent.click(await screen.findByRole("button", { name: "Edit details" }));
    const form = screen.getByRole("form", { name: "Edit Patient Identity" });
    fireEvent.change(within(form).getByLabelText("Mobile"), { target: { value: "0491 570 158" } });
    fireEvent.submit(form);
    await waitFor(() => expect(patients.changeIdentity).toHaveBeenCalledWith("pt-1", { mobile: "0491 570 158" }));
  });

  it("shows the identity's audit trail: what changed, from what, to what, and who signed it off", async () => {
    renderPatient();
    const trail = await screen.findByRole("list", { name: "Identity audit trail" });
    const [latest, created] = within(trail).getAllByRole("listitem");
    expect(latest).toHaveTextContent("Mobile: 0491 570 100 → 0491 570 156");
    expect(latest).toHaveTextContent("Jordan Park (synthetic) (Secretary)");
    expect(created).toHaveTextContent("Patient created");
  });

  it("says so when the Patient doesn't exist", async () => {
    patients.fetchPatient.mockRejectedValue(new Error("No such Patient."));
    renderPatient();
    expect(await screen.findByRole("alert")).toHaveTextContent("No such Patient.");
  });
});

describe("formatDob", () => {
  it("shows the date the Australian way, with age in whole years", () => {
    expect(formatDob("1962-04-03", new Date(2026, 8, 25))).toBe("03/04/1962 (64)");
    expect(formatDob("1962-10-03", new Date(2026, 8, 25))).toBe("03/10/1962 (63)");
    expect(formatDob(null)).toBe("—");
  });
});
