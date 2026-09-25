import { readdirSync, readFileSync, statSync } from "node:fs";
import path from "node:path";
import { describe, expect, it } from "vitest";

const ROOT = path.resolve(__dirname, "..");
const SOURCE_DIRS = ["app", "components", "lib", "modules"];

function files(dir: string): string[] {
  return readdirSync(dir).flatMap((name) => {
    const full = path.join(dir, name);
    return statSync(full).isDirectory() ? files(full) : /\.(ts|tsx)$/.test(name) ? [full] : [];
  });
}

const sources = SOURCE_DIRS.flatMap((dir) => files(path.join(ROOT, dir)));
const importsOf = (file: string) => [...readFileSync(file, "utf8").matchAll(/from\s+["']([^"']+)["']/g)].map((m) => m[1]);

describe("module boundaries (design doc §4.1)", () => {
  it("names Specialty Modules only in modules/index.ts; Core code reads the registry", () => {
    const offenders = sources
      .filter((file) => !file.startsWith(path.join(ROOT, "modules")))
      .flatMap((file) => importsOf(file).filter((source) => source.startsWith("@/modules/")).map((source) => `${path.relative(ROOT, file)} → ${source}`));
    expect(offenders).toEqual([]);
  });

  it("keeps each Specialty Module from importing another", () => {
    const moduleDirs = readdirSync(path.join(ROOT, "modules")).filter((name) => statSync(path.join(ROOT, "modules", name)).isDirectory());
    const offenders = moduleDirs.flatMap((name) =>
      files(path.join(ROOT, "modules", name)).flatMap((file) =>
        importsOf(file).filter((source) => moduleDirs.some((other) => other !== name && source.startsWith(`@/modules/${other}`))),
      ),
    );
    expect(offenders).toEqual([]);
  });
});
