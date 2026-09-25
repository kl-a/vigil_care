import type { components } from "@/generated/api";

export type CurrentUser = components["schemas"]["CurrentUser"];
export type DevLoginChoice = components["schemas"]["DevLoginChoice"];

/** Backend calls go through the Next.js `/api` proxy, so the session cookie stays same-origin. */
const API = "/api";

async function call(path: string, init?: RequestInit): Promise<Response> {
  return fetch(`${API}${path}`, { credentials: "same-origin", ...init });
}

/** The signed-in User, or null when there's no session. */
export async function fetchCurrentUser(): Promise<CurrentUser | null> {
  const response = await call("/auth/me");
  if (response.status === 401) return null;
  if (!response.ok) throw new Error(`Couldn't load the signed-in User (${response.status}).`);
  return (await response.json()) as CurrentUser;
}

/** Dev only: the seeded Users you can sign in as. */
export async function fetchDevLoginChoices(): Promise<DevLoginChoice[]> {
  const response = await call("/auth/dev-login/users");
  if (!response.ok) throw new Error(`The dev login isn't available (${response.status}). Is VIGIL_DEV_LOGIN_ENABLED=true?`);
  return (await response.json()) as DevLoginChoice[];
}

export async function devLogin(userId: string): Promise<CurrentUser> {
  const response = await call("/auth/dev-login", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ user_id: userId }),
  });
  if (!response.ok) throw new Error("That User can't sign in.");
  return (await response.json()) as CurrentUser;
}

export async function logout(): Promise<void> {
  await call("/auth/logout", { method: "POST" });
}
