import { fireEvent, render, screen, waitFor, within } from "@testing-library/react";
import { beforeEach, describe, expect, it, vi } from "vitest";

vi.mock("next/navigation", () => ({ usePathname: () => "/patients/pt-1/clinical-data", useRouter: () => ({ replace: vi.fn(), push: vi.fn() }) }));

const clinical = vi.hoisted(() => ({
  fetchConditions: vi.fn(), addCondition: vi.fn(), changeCondition: vi.fn(), removeCondition: vi.fn(),
  fetchEntryRights: vi.fn(), fetchInactiveModuleFacts: vi.fn(),
}));
vi.mock("@/lib/clinical", async (importOriginal) => ({ ...(await importOriginal<object>()), ...clinical }));

import { Conditions } from "@/components/clinical/Conditions";
import { InactiveModuleFacts } from "@/components/clinical/InactiveModuleFacts";
import { ViewerProvider } from "@/components/shell/ViewerProvider";
import { changesBetween, type ConditionRow } from "@/lib/clinical";
import { userWith } from "./fixtures";

const ENTERED = { by: "Dr Alex Rivera (synthetic)", job_title: "clinician" as const, at: "2026-09-27T01:00:00Z" };
const condition = (overrides: Partial<ConditionRow>): ConditionRow => ({
  id: "c-1", name: "Type 2 diabetes", status: "active", onset_date: "2015-06-01", notes: "Diet controlled",
  extended_by_module: null, entered: ENTERED, ...overrides,
});

function renderConditions(jobTitle: "clinician" | "secretary" = "clinician") {
  render(<ViewerProvider initialUser={userWith(jobTitle)}><Conditions patientId="pt-1" /></ViewerProvider>);
}

describe("Conditions", () => {
  beforeEach(() => {
    vi.clearAllMocks();
    clinical.fetchConditions.mockResolvedValue([condition({}), condition({ id: "c-2", name: "COPD", status: "resolved", onset_date: null, notes: null })]);
    clinical.fetchEntryRights.mockResolvedValue({ condition: true });
    clinical.changeCondition.mockResolvedValue(condition({}));
    clinical.removeCondition.mockResolvedValue(undefined);
    clinical.addCondition.mockResolvedValue(condition({}));
  });

  it("lists each Condition with its status, onset and who entered it", async () => {
    renderConditions();
    const row = (await screen.findByText("Type 2 diabetes")).closest("tr")!;
    expect(row).toHaveTextContent("Active");
    expect(row).toHaveTextContent("01/06/2015");
    expect(row).toHaveTextContent("Diet controlled");
    expect(row).toHaveTextContent("Dr Alex Rivera (synthetic) (Clinician)");
    expect(screen.getByText("COPD").closest("tr")).toHaveTextContent("Resolved");
  });

  it("adds a Condition, sending empty fields as null", async () => {
    renderConditions();
    fireEvent.click(await screen.findByRole("button", { name: "Add Condition" }));
    const form = screen.getByRole("form", { name: "New Condition" });
    fireEvent.change(within(form).getByLabelText("Condition"), { target: { value: " Asthma " } });
    fireEvent.click(within(form).getByRole("button", { name: "Add Condition" }));
    await waitFor(() => expect(clinical.addCondition).toHaveBeenCalledWith("pt-1", { name: "Asthma", status: "active", onset_date: null, notes: null }));
  });

  it("asks for a reason once when saving a correction, and sends only what changed", async () => {
    renderConditions();
    fireEvent.click((await screen.findAllByRole("button", { name: "Edit" }))[0]!);
    const form = screen.getByRole("form", { name: "Edit Type 2 diabetes" });
    fireEvent.change(within(form).getByLabelText("Status"), { target: { value: "resolved" } });
    fireEvent.change(within(form).getByLabelText("Notes"), { target: { value: "" } });
    fireEvent.click(within(form).getByRole("button", { name: "Save" }));
    expect(clinical.changeCondition).not.toHaveBeenCalled();  // not until a reason is given
    const dialog = await screen.findByRole("dialog", { name: "Save changes to Type 2 diabetes" });
    expect(within(dialog).getByRole("button", { name: "Save" })).toBeDisabled();
    fireEvent.change(within(dialog).getByLabelText("Reason (required)"), { target: { value: "Resolved with diet" } });
    fireEvent.click(within(dialog).getByRole("button", { name: "Save" }));
    await waitFor(() => expect(clinical.changeCondition).toHaveBeenCalledWith("pt-1", "c-1", { status: "resolved", notes: null, reason: "Resolved with diet" }));
  });

  it("doesn't ask for a reason when a save changes nothing", async () => {
    renderConditions();
    fireEvent.click((await screen.findAllByRole("button", { name: "Edit" }))[0]!);
    fireEvent.click(within(screen.getByRole("form", { name: "Edit Type 2 diabetes" })).getByRole("button", { name: "Save" }));
    await waitFor(() => expect(screen.queryByRole("form", { name: "Edit Type 2 diabetes" })).not.toBeInTheDocument());
    expect(screen.queryByRole("dialog")).not.toBeInTheDocument();
    expect(clinical.changeCondition).not.toHaveBeenCalled();
  });

  it("removes a Condition only with a reason", async () => {
    renderConditions();
    fireEvent.click((await screen.findAllByRole("button", { name: "Remove" }))[1]!);
    const dialog = await screen.findByRole("dialog", { name: "Remove COPD" });
    fireEvent.change(within(dialog).getByLabelText("Reason (required)"), { target: { value: "Wrong Patient" } });
    fireEvent.click(within(dialog).getByRole("button", { name: "Remove Condition" }));
    await waitFor(() => expect(clinical.removeCondition).toHaveBeenCalledWith("pt-1", "c-2", "Wrong Patient"));
  });

  it("shows a secretary the Conditions read-only, with a lock", async () => {
    clinical.fetchEntryRights.mockResolvedValue({ condition: false });
    renderConditions("secretary");
    expect(await screen.findByText("Type 2 diabetes")).toBeInTheDocument();
    expect(await screen.findByText("Needs clinician/coordinator")).toBeInTheDocument();
    expect(screen.queryByRole("button", { name: "Add Condition" })).not.toBeInTheDocument();
    expect(screen.queryByRole("button", { name: "Edit" })).not.toBeInTheDocument();
  });

  it("says when none are recorded", async () => {
    clinical.fetchConditions.mockResolvedValue([]);
    renderConditions();
    expect(await screen.findByText("None recorded.")).toBeInTheDocument();
  });
});

describe("An inactive module's facts", () => {
  it("stay visible, read-only, in plain words", async () => {
    clinical.fetchInactiveModuleFacts.mockResolvedValue([
      { module: "oncology", display_name: "Oncology", facts: ["Breast cancer: Stage IIA (TNM) at diagnosis, 1 Mar 2024; metastatic"] },
    ]);
    render(<InactiveModuleFacts patientId="pt-1" />);
    const section = await screen.findByRole("region", { name: "Oncology (read-only)" });
    expect(section).toHaveTextContent("Breast cancer: Stage IIA (TNM) at diagnosis, 1 Mar 2024; metastatic");
    expect(within(section).queryByRole("button")).not.toBeInTheDocument();
  });

  it("show nothing when every module is active", async () => {
    clinical.fetchInactiveModuleFacts.mockResolvedValue([]);
    const { container } = render(<InactiveModuleFacts patientId="pt-1" />);
    await waitFor(() => expect(clinical.fetchInactiveModuleFacts).toHaveBeenCalled());
    expect(container).toBeEmptyDOMElement();
  });
});

describe("changesBetween", () => {
  it("keeps only the fields that differ, treating empty as null", () => {
    expect(changesBetween({ a: "x", b: null, c: "y" }, { a: "x", b: null, c: "z" })).toEqual({ c: "z" });
    expect(changesBetween({ a: null }, { a: undefined })).toEqual({});
  });
});
