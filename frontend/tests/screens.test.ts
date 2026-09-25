import { existsSync } from "node:fs";
import path from "node:path";
import { describe, expect, it } from "vitest";
import { CORE_SCREENS, screensFor } from "@/lib/screens";
import { patientTabsFor } from "@/lib/modules/registry";
import { NO_MODULES } from "@/lib/modules/types";
import { ONCOLOGY_ON } from "./fixtures";

const ALL = ONCOLOGY_ON;

/** "/patients/[id]/summary" → "(app)/patients/[id]/[tab]/page.tsx"; all Patient tabs share one dynamic route. */
function routeFileFor(path: string): string {
  if (path === "/login") return "login/page.tsx";
  if (path.startsWith("/patients/[id]/")) return "(app)/patients/[id]/[tab]/page.tsx";
  return `(app)${path}/page.tsx`;
}

describe("screen inventory", () => {
  it("registers all 19 screens from design doc §5, numbered 1 to 19, plus System status", () => {
    const numbered = screensFor(ALL).filter((s) => s.number !== undefined).map((s) => s.number);
    expect(numbered.sort((a, b) => a! - b!)).toEqual(Array.from({ length: 19 }, (_, i) => i + 1));
    expect(screensFor(ALL).some((s) => s.path === "/system")).toBe(true);
  });

  it("has an app route for every screen", () => {
    for (const screen of screensFor(ALL)) {
      const file = path.join(__dirname, "..", "app", routeFileFor(screen.path));
      expect(existsSync(file), `${screen.title} → ${file}`).toBe(true);
    }
  });

  it("gives every Patient tab (Core and module) a screen", () => {
    const tabs = patientTabsFor(ALL);
    for (const tab of tabs) {
      expect(screensFor(ALL).some((s) => s.path === `/patients/[id]/${tab.segment}`), tab.label).toBe(true);
    }
  });

  it("keeps module screens out of the Core screen list", () => {
    expect(CORE_SCREENS.some((s) => s.title === "Treatment Options")).toBe(false);
    expect(screensFor(NO_MODULES).some((s) => s.title === "Treatment Options")).toBe(false);
    expect(screensFor(ONCOLOGY_ON).some((s) => s.title === "Treatment Options")).toBe(true);
  });
});
