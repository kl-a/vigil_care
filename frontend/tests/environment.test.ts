import { expect, it } from "vitest";
import { parseEnvironment } from "@/lib/environment";

it("reads dev, test and prod", () => {
  expect(parseEnvironment("dev")).toBe("dev");
  expect(parseEnvironment("test")).toBe("test");
  expect(parseEnvironment("prod")).toBe("prod");
});

it("refuses a missing or unknown environment instead of falling back to dev", () => {
  // Falling back to dev would switch on dev-only features (e.g. Preview as) in test or prod.
  expect(() => parseEnvironment(undefined)).toThrow(/NEXT_PUBLIC_VIGIL_ENV/);
  expect(() => parseEnvironment("staging")).toThrow(/staging/);
});
