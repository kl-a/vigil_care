import { fireEvent, render, screen, waitFor, within } from "@testing-library/react";
import { beforeEach, describe, expect, it, vi } from "vitest";

vi.mock("next/navigation", () => ({ usePathname: () => "/patients/pt-1/clinical-data", useRouter: () => ({ replace: vi.fn(), push: vi.fn() }) }));

const api = vi.hoisted(() => ({ request: vi.fn() }));
vi.mock("@/lib/api", async (importOriginal) => ({ ...(await importOriginal<object>()), ...api }));

import { TreatmentCourses } from "@/components/clinical/TreatmentCourses";
import { ViewerProvider } from "@/components/shell/ViewerProvider";
import type { TreatmentCourseRow } from "@/lib/clinical";
import { ordinal } from "@/modules/oncology/LinesOfTherapy";
import oncologyActive from "./contracts/oncology-active.json";
import { userWith } from "./fixtures";

const COURSE: TreatmentCourseRow = {
  id: "tc-1", condition_id: "c-1", condition_name: "Breast cancer", modality: "systemic", intent: "palliative", regimen_name: "Paclitaxel",
  regimen_drugs: [{ drug: "Paclitaxel", dose: "80 mg/m2" }], start_date: "2025-03-12", end_date: null, ongoing: true, reason_stopped: null,
  details: null, entered: null,
};

function respond(rights: Record<string, boolean>) {
  api.request.mockImplementation(async (path: string, init?: RequestInit) => {
    if (path === "/modules/active") return oncologyActive;
    if (path === "/clinical/entry-rights") return rights;
    if (path === "/patients/pt-1/treatment-courses" && !init) return [COURSE];
    if (path === "/patients/pt-1/lines-of-therapy") {
      return [{ treatment_course_id: "tc-1", cancer_diagnosis_id: "cd-1", line: 1, overridden: false, explanation: "1st line: 1st palliative systemic course of Breast cancer" }];
    }
    if (path === "/patients/pt-1/conditions") return [{ id: "c-1", name: "Breast cancer" }];
    return COURSE;
  });
}

function renderCourses(jobTitle: "clinician" | "trial_coordinator" = "clinician") {
  render(<ViewerProvider initialUser={userWith(jobTitle)}><TreatmentCourses patientId="pt-1" /></ViewerProvider>);
}

describe("Treatment Courses", () => {
  beforeEach(() => vi.clearAllMocks());

  it("lists a course with its Regimen and, from Oncology, its Line of Therapy and why", async () => {
    respond({ treatment_course: true, line_of_therapy_override: true });
    renderCourses();
    const course = (await screen.findByText("Paclitaxel", { selector: "span.font-medium" })).closest("li")!;
    expect(course).toHaveTextContent("Systemic · Palliative");
    expect(course).toHaveTextContent("For Breast cancer · 12/03/2025 – ongoing");
    expect(course).toHaveTextContent("Paclitaxel 80 mg/m2");
    expect(await within(course).findByText("1st line")).toBeInTheDocument();
    expect(course).toHaveTextContent("1st line: 1st palliative systemic course of Breast cancer");
    expect(within(course).getByRole("button", { name: "Change line" })).toBeInTheDocument();
  });

  it("offers a clinician's line override only to clinicians", async () => {
    respond({ treatment_course: true, line_of_therapy_override: false });
    renderCourses("trial_coordinator");
    const course = (await screen.findByText("Paclitaxel", { selector: "span.font-medium" })).closest("li")!;
    await within(course).findByText("1st line");
    expect(within(course).queryByRole("button", { name: "Change line" })).not.toBeInTheDocument();
    expect(within(course).getByRole("button", { name: "End course" })).toBeInTheDocument();
  });

  it("adds a systemic course with its planned drugs", async () => {
    respond({ treatment_course: true });
    renderCourses();
    fireEvent.click(await screen.findByRole("button", { name: "Add course" }));
    const form = await screen.findByRole("form", { name: "New Treatment Course" });
    fireEvent.change(within(form).getByLabelText("Intent"), { target: { value: "adjuvant" } });
    fireEvent.change(within(form).getByLabelText("Name"), { target: { value: "AC-T" } });
    fireEvent.change(within(form).getByLabelText("Drug 1"), { target: { value: "Doxorubicin" } });
    fireEvent.change(within(form).getByLabelText("Dose 1"), { target: { value: "60 mg/m2" } });
    fireEvent.click(within(form).getByRole("button", { name: "Add course" }));
    await waitFor(() => expect(api.request).toHaveBeenCalledWith("/patients/pt-1/treatment-courses", expect.objectContaining({ method: "POST" })));
    const [, init] = api.request.mock.calls.find(([path, i]) => path === "/patients/pt-1/treatment-courses" && i)!;
    expect(JSON.parse(init.body)).toMatchObject({
      condition_id: "c-1", modality: "systemic", intent: "adjuvant", regimen_name: "AC-T", regimen_drugs: [{ drug: "Doxorubicin", dose: "60 mg/m2" }], details: null,
    });
  });

  it("numbers lines in words", () => {
    expect([1, 2, 3, 4, 11, 21].map(ordinal)).toEqual(["1st", "2nd", "3rd", "4th", "11th", "21st"]);
  });
});
