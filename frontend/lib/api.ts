import type { components } from "@/generated/api";

export type Schemas = components["schemas"];

/** Backend calls go through the Next.js `/api` proxy, so the session cookie stays same-origin. */
export const API = "/api";

/** A refused request, with the backend's explanation (FastAPI's `detail`) when there is one. */
export class ApiError extends Error {
  constructor(readonly status: number, message: string) {
    super(message);
  }
}

export async function request<T>(path: string, init?: RequestInit): Promise<T> {
  const response = await fetch(`${API}${path}`, {
    credentials: "same-origin",
    ...init,
    headers: init?.body ? { "Content-Type": "application/json", ...init.headers } : init?.headers,
  });
  if (!response.ok) throw new ApiError(response.status, await explain(response));
  return (response.status === 204 ? undefined : await response.json()) as T;
}

async function explain(response: Response): Promise<string> {
  try {
    const body = (await response.json()) as { detail?: unknown };
    if (typeof body.detail === "string") return body.detail;
    if (Array.isArray(body.detail)) return body.detail.map((d: { msg?: string }) => d.msg ?? "").filter(Boolean).join(" ");
  } catch { /* not JSON */ }
  return `The request failed (${response.status}).`;
}

export function messageOf(reason: unknown): string {
  return reason instanceof Error ? reason.message : String(reason);
}
