export type VigilEnvironment = "dev" | "test" | "prod";

const ENVIRONMENTS: readonly VigilEnvironment[] = ["dev", "test", "prod"];

/**
 * Fails closed: a missing or unknown value is an error, never a silent "dev",
 * because dev switches on dev-only features (e.g. Preview as).
 */
export function parseEnvironment(value: string | undefined): VigilEnvironment {
  if ((ENVIRONMENTS as readonly string[]).includes(value ?? "")) return value as VigilEnvironment;
  throw new Error(`NEXT_PUBLIC_VIGIL_ENV must be one of ${ENVIRONMENTS.join(", ")}; got ${JSON.stringify(value)}.`);
}

export const ENVIRONMENT: VigilEnvironment = parseEnvironment(process.env.NEXT_PUBLIC_VIGIL_ENV);
