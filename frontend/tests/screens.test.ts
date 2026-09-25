import { existsSync } from "node:fs";
import path from "node:path";
import { describe, expect, it } from "vitest";
import { SCREENS, routeFileFor } from "@/lib/screens";
import { MODULES, patientTabsFor } from "@/lib/modules/registry";

describe("screen inventory", () => {
  it("registers all 19 screens from design doc §5, numbered 1 to 19, plus System status", () => {
    const numbered = SCREENS.filter((s) => s.number !== undefined).map((s) => s.number);
    expect(numbered.sort((a, b) => a! - b!)).toEqual(Array.from({ length: 19 }, (_, i) => i + 1));
    expect(SCREENS.some((s) => s.path === "/system")).toBe(true);
  });

  it("has an app route for every screen", () => {
    for (const screen of SCREENS) {
      const file = path.join(__dirname, "..", "app", routeFileFor(screen.path));
      expect(existsSync(file), `${screen.title} → ${file}`).toBe(true);
    }
  });

  it("gives every Patient tab (Core and module) a screen", () => {
    const tabs = patientTabsFor(MODULES.map((m) => m.key));
    for (const tab of tabs) {
      expect(SCREENS.some((s) => s.path === `/patients/[id]/${tab.segment}`), tab.label).toBe(true);
    }
  });
});
