import { fireEvent, render, screen, within } from "@testing-library/react";
import { beforeEach, describe, expect, it, vi } from "vitest";

vi.mock("next/navigation", () => ({ usePathname: () => "/patients", useRouter: () => ({ replace: vi.fn(), push: vi.fn() }) }));

const api = vi.hoisted(() => ({ request: vi.fn() }));
vi.mock("@/lib/api", async (importOriginal) => ({ ...(await importOriginal<object>()), ...api }));

import PatientsPage from "@/app/(app)/patients/page";
import { ClinicalData } from "@/components/clinical/ClinicalData";
import { PatientProvider } from "@/components/patients/PatientContext";
import { ViewerProvider } from "@/components/shell/ViewerProvider";
import { ONCOLOGY_ON, userWith } from "./fixtures";

const ROW = (id: string, name: string, pseudonym: string) => ({ id, display_name: name, pseudonym, dob: "1958-01-29", mrn: "1", updated_at: "2026-09-27T00:00:00Z" });

beforeEach(() => {
  vi.clearAllMocks();
  api.request.mockImplementation(async (path: string) => {
    if (path.startsWith("/patients?") || path === "/patients") return [ROW("pt-1", "Robin Sample", "VG-0044"), ROW("pt-2", "Sam Example", "VG-0043")];
    if (path === "/patient-list/oncology") return [
      { patient_id: "pt-1", values: { cancer_types: ["Colorectal cancer", "Melanoma"], disease_extent: ["Metastatic"] } },
      { patient_id: "pt-2", values: { cancer_types: ["Breast cancer"], disease_extent: ["Localised"] } },
    ];
    if (path === "/open-items") return [{ patient_id: "pt-1" }, { patient_id: "pt-1" }];
    if (path === "/patients/pt-1") return { id: "pt-1", display_name: "Robin Sample", pseudonym: "VG-0044", identity: {}, history: [] };
    if (path === "/patients/pt-1/clinical-counts") return { conditions: 5, labs: 6, imaging: 2, treatment: 3, plan: 3 };
    if (path === "/patients/pt-1/oncology-counts") return { "cancer-diagnosis": 2, "response-assessments": 2, biomarkers: 4, "performance-status": 2, cns: 0 };
    if (path === "/clinical/entry-rights") return {};
    return [];
  });
});

describe("The Patient List", () => {
  it("adds Oncology's Cancer Type(s) and Disease Extent, filters by Cancer Type, and counts Open Items", async () => {
    render(<ViewerProvider initialUser={userWith("clinician")} loadModules={async () => ONCOLOGY_ON}><PatientsPage /></ViewerProvider>);
    const robin = (await screen.findByRole("link", { name: "Robin Sample" })).closest("tr")!;
    expect(await within(robin).findByText("Colorectal cancer; Melanoma")).toBeInTheDocument();
    expect(robin).toHaveTextContent("Metastatic");
    expect(within(robin).getByText("VG-0044")).toBeInTheDocument();
    expect(robin).toHaveTextContent("2");
    expect(screen.getByRole("toolbar", { name: "Patients filters" })).toHaveTextContent("2 patients");
    fireEvent.change(await screen.findByLabelText("Cancer Type"), { target: { value: "Breast cancer" } });
    expect(screen.queryByRole("link", { name: "Robin Sample" })).not.toBeInTheDocument();
    expect(screen.getByRole("toolbar", { name: "Patients filters" })).toHaveTextContent("1 patient");
  });
});

describe("Clinical Data sub-tabs", () => {
  it("count what each holds, the Core's and Oncology's", async () => {
    render(
      <ViewerProvider initialUser={userWith("clinician")} loadModules={async () => ONCOLOGY_ON}>
        <PatientProvider patientId="pt-1"><ClinicalData /></PatientProvider>
      </ViewerProvider>,
    );
    expect(await screen.findByRole("button", { name: "Labs 6" })).toBeInTheDocument();
    expect(await screen.findByRole("button", { name: "Biomarkers 4" })).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "CNS 0" })).toBeInTheDocument();
  });
});
