import { expect, it } from "vitest";
import { parseEnvironment } from "@/lib/environment";

it("reads test and prod, and defaults anything else to dev", () => {
  expect(parseEnvironment("test")).toBe("test");
  expect(parseEnvironment("prod")).toBe("prod");
  expect(parseEnvironment(undefined)).toBe("dev");
  expect(parseEnvironment("staging")).toBe("dev");
});
