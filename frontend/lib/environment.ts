export type VigilEnvironment = "dev" | "test" | "prod";

export function parseEnvironment(value: string | undefined): VigilEnvironment {
  return value === "test" || value === "prod" ? value : "dev";
}

export const ENVIRONMENT: VigilEnvironment = parseEnvironment(process.env.NEXT_PUBLIC_VIGIL_ENV);
