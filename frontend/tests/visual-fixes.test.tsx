import { render, screen, within } from "@testing-library/react";
import { beforeEach, describe, expect, it, vi } from "vitest";

vi.mock("next/navigation", () => ({ usePathname: () => "/patients/pt-1/clinical-data", useRouter: () => ({ replace: vi.fn(), push: vi.fn() }) }));

const api = vi.hoisted(() => ({ request: vi.fn() }));
vi.mock("@/lib/api", async (importOriginal) => ({ ...(await importOriginal<object>()), ...api }));

import { ClinicalData } from "@/components/clinical/ClinicalData";
import { PatientProvider } from "@/components/patients/PatientContext";
import { Breadcrumbs, BreadcrumbProvider, useBreadcrumbLabel } from "@/components/shell/Breadcrumbs";
import { ViewerProvider } from "@/components/shell/ViewerProvider";
import { formatRange, formatUnit } from "@/lib/format";
import { ONCOLOGY_ON, userWith } from "./fixtures";

describe("Reference ranges and units", () => {
  it("write a one-sided range the way the flag reads it, and powers as superscripts", () => {
    expect(formatRange("115", "165")).toBe("115–165");
    expect(formatRange(null, "20")).toBe("≤20");
    expect(formatRange("60", null)).toBe("≥60");
    expect(formatRange(null, null)).toBe("—");
    expect(formatUnit("x10^9/L")).toBe("×10⁹/L");
    expect(formatUnit("x10^12/L")).toBe("×10¹²/L");
    expect(formatUnit("g/L")).toBe("g/L");
    expect(formatUnit(null)).toBe("");
    expect(formatUnit("mg/m2")).toBe("mg/m²");
    expect(formatUnit("mL/min/1.73m2")).toBe("mL/min/1.73m²");
  });
});

function Named({ href, label }: { href: string; label: string }) {
  useBreadcrumbLabel(href, label);
  return null;
}

describe("Breadcrumbs", () => {
  it("name a Patient instead of showing their id, and never show a raw id", () => {
    const { rerender } = render(
      <BreadcrumbProvider><Breadcrumbs pathname="/patients/d52a83cf-9117-5240-9160-66d3e894e378/summary" isVisible={() => true} /></BreadcrumbProvider>,
    );
    const crumbs = screen.getByRole("navigation", { name: "Breadcrumb" });
    expect(crumbs).toHaveTextContent("PatientsPatientSummary");
    expect(crumbs.textContent).not.toMatch(/d52a83cf/i);
    rerender(
      <BreadcrumbProvider>
        <Named href="/patients/d52a83cf-9117-5240-9160-66d3e894e378" label="Robin Sample" />
        <Breadcrumbs pathname="/patients/d52a83cf-9117-5240-9160-66d3e894e378/summary" isVisible={() => true} />
      </BreadcrumbProvider>,
    );
    expect(within(screen.getByRole("navigation", { name: "Breadcrumb" })).getByRole("link", { name: "Robin Sample" })).toBeInTheDocument();
  });
});

describe("Clinical Data deep links", () => {
  beforeEach(() => {
    vi.clearAllMocks();
    api.request.mockImplementation(async (path: string) => {
      if (path === "/patients/pt-1") return { id: "pt-1", display_name: "Robin Sample", pseudonym: "VG-0044", identity: {}, history: [] };
      if (path === "/clinical/entry-rights") return {};
      return [];
    });
  });

  it("open a Specialty Module's sub-tab once its tabs have loaded", async () => {
    window.history.pushState({}, "", "/patients/pt-1/clinical-data?tab=cancer-diagnosis");
    render(
      <ViewerProvider initialUser={userWith("clinician")} loadModules={async () => ONCOLOGY_ON}>
        <PatientProvider patientId="pt-1"><ClinicalData /></PatientProvider>
      </ViewerProvider>,
    );
    const tab = await screen.findByRole("button", { name: "Cancer Diagnosis" });
    await vi.waitFor(() => expect(tab).toHaveAttribute("aria-current", "page"));
    window.history.pushState({}, "", "/");
  });
});
