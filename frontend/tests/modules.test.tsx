import { render, screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";
import { patientTabsFor, sectionsFor } from "@/lib/modules/registry";
import { SectionSlot } from "@/components/SectionSlot";
import { ViewerProvider } from "@/components/shell/ViewerProvider";
import { userWith } from "./fixtures";

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

  it("renders the sections of the Practice's active modules into a slot, and nothing when a module is off", async () => {
    const { unmount } = render(
      <ViewerProvider initialUser={userWith("clinician")} loadModules={async () => ["oncology"]}>
        <SectionSlot slot="patient-summary" />
      </ViewerProvider>,
    );
    expect(await screen.findByRole("region", { name: "Diagnosis" })).toBeInTheDocument();
    unmount();

    render(
      <ViewerProvider initialUser={userWith("clinician")} loadModules={async () => []}>
        <SectionSlot slot="patient-summary" />
      </ViewerProvider>,
    );
    await new Promise((resolve) => setTimeout(resolve, 0));
    expect(screen.queryByRole("region", { name: "Diagnosis" })).not.toBeInTheDocument();
  });
});
