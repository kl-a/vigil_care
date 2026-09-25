import { render, screen, within } from "@testing-library/react";
import { describe, expect, it, vi } from "vitest";

vi.mock("next/navigation", () => ({ usePathname: () => "/patients/pt-1/overview", useRouter: () => ({ replace: vi.fn() }) }));
// As it will be once Stage 2 ships (SHIPPED_STAGE = 2).
vi.mock("@/lib/stages", async (importOriginal) => {
  const actual = await importOriginal<typeof import("@/lib/stages")>();
  const isReleased = (screen: { stage: number; built?: boolean }) => screen.stage <= 2 && screen.built === true;
  return { ...actual, SHIPPED_STAGE: 2, isShipped: (stage: number) => stage <= 2, isReleased, isVisible: (s: { stage: number; built?: boolean }, up: boolean) => isReleased(s) || up };
});

import { PatientTabs } from "@/components/PatientTabs";
import { ViewerProvider } from "@/components/shell/ViewerProvider";
import { ONCOLOGY_ON, userWith } from "./fixtures";

describe("Patient tabs once Stage 2 ships", () => {
  it("show only the built tabs of shipped stages: the Overview", async () => {
    render(
      <ViewerProvider initialUser={userWith("clinician")} loadModules={async () => ONCOLOGY_ON}>
        <PatientTabs patientId="pt-1" />
      </ViewerProvider>,
    );
    const tabs = await screen.findByRole("navigation", { name: "Patient" });
    expect(within(tabs).getAllByRole("link").map((link) => link.textContent)).toEqual(["Overview"]);
  });
});
