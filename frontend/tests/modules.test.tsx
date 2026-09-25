import { render, screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";
import { SectionSlot } from "@/components/SectionSlot";
import { ViewerProvider } from "@/components/shell/ViewerProvider";
import { patientTabsFor, sectionsFor } from "@/lib/modules/registry";
import { NO_MODULES } from "@/lib/modules/types";
import { INSTALLED_MODULES } from "@/modules";
import { ONCOLOGY_ON, userWith } from "./fixtures";

describe("Specialty Module sections and tabs (the API decides what; manifests render)", () => {
  it("adds the Oncology Treatment Options tab only when Oncology is active", () => {
    expect(patientTabsFor(ONCOLOGY_ON).map((t) => t.label)).toContain("Treatment Options");
    expect(patientTabsFor(NO_MODULES).map((t) => t.label)).not.toContain("Treatment Options");
  });

  it("keeps the Core Patient tabs whatever modules are active", () => {
    const core = ["Overview", "Summary", "Clinical Data", "Documents", "Medications", "Trials", "Exports"];
    expect(patientTabsFor(NO_MODULES).map((t) => t.label)).toEqual(core);
  });

  it("returns a slot's sections in the API's order, with the API's titles", () => {
    expect(sectionsFor("clinical-data-tabs", ONCOLOGY_ON).map((s) => s.title)).toEqual([
      "Response Assessments", "Biomarkers", "Performance Status", "CNS",
    ]);
    expect(sectionsFor("clinical-data-tabs", NO_MODULES)).toEqual([]);
  });

  it("skips a section the API lists but no manifest can render", () => {
    const unknown = { ...ONCOLOGY_ON, sections: [{ module: "oncology", id: "not-built", slot: "patient-summary", title: "?", order: 1 }] };
    expect(sectionsFor("patient-summary", unknown)).toEqual([]);
  });

  it("has a renderer for every section and tab the backend's Oncology module declares", () => {
    const oncology = INSTALLED_MODULES.find((module) => module.key === "oncology")!;
    expect(Object.keys(oncology.sections).sort()).toEqual(ONCOLOGY_ON.sections.map((s) => s.id).sort());
    expect(Object.keys(oncology.patientTabs)).toEqual(ONCOLOGY_ON.patient_tabs.map((t) => t.segment));
  });

  it("renders the Practice's active sections into a slot, and nothing when the module is off", async () => {
    const { unmount } = render(
      <ViewerProvider initialUser={userWith("clinician")} loadModules={async () => ONCOLOGY_ON}>
        <SectionSlot slot="patient-summary" />
      </ViewerProvider>,
    );
    expect(await screen.findByRole("region", { name: "Diagnosis" })).toBeInTheDocument();
    unmount();

    render(
      <ViewerProvider initialUser={userWith("clinician")} loadModules={async () => NO_MODULES}>
        <SectionSlot slot="patient-summary" />
      </ViewerProvider>,
    );
    await new Promise((resolve) => setTimeout(resolve, 0));
    expect(screen.queryByRole("region", { name: "Diagnosis" })).not.toBeInTheDocument();
  });
});
