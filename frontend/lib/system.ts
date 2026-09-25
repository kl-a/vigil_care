import { API, type Schemas } from "./api";

export type Health = Schemas["Health"];

/** Not `request()`: /health answers 503 when the database is down, still with a Health body to show. */
export async function fetchHealth(): Promise<Health> {
  const response = await fetch(`${API}/health`, { credentials: "same-origin" });
  if (response.status !== 200 && response.status !== 503) throw new Error(`Health check failed (${response.status}).`);
  return (await response.json()) as Health;
}
