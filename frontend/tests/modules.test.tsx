import { render, screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";
import { patientTabsFor, sectionsFor } from "@/lib/modules/registry";
import { SectionSlot } from "@/components/SectionSlot";

describe("Specialty Module section registry", () => {
  it("adds the Oncology Treatment Options tab only when Oncology is active", () => {
    expect(patientTabsFor(["oncology"]).map((t) => t.label)).toContain("Treatment Options");
    expect(patientTabsFor([]).map((t) => t.label)).not.toContain("Treatment Options");
  });

  it("keeps the Core Patient tabs whatever modules are active", () => {
    const core = ["Overview", "Summary", "Clinical Data", "Documents", "Medications", "Trials", "Exports"];
    expect(patientTabsFor([]).map((t) => t.label)).toEqual(core);
  });

  it("returns a slot's sections from active modules only", () => {
    expect(sectionsFor("clinical-data-tabs", ["oncology"]).map((s) => s.title)).toEqual([
      "Response Assessments", "Biomarkers", "Performance Status", "CNS",
    ]);
    expect(sectionsFor("clinical-data-tabs", [])).toEqual([]);
  });

  it("renders module sections into a slot, and nothing when the module is off", () => {
    const { rerender } = render(<SectionSlot slot="patient-summary" activeModules={["oncology"]} />);
    expect(screen.getByRole("region", { name: "Diagnosis" })).toBeInTheDocument();

    rerender(<SectionSlot slot="patient-summary" activeModules={[]} />);
    expect(screen.queryByRole("region", { name: "Diagnosis" })).not.toBeInTheDocument();
  });
});
