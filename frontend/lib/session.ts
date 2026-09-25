import { ApiError, request, type Schemas } from "./api";

export type CurrentUser = Schemas["CurrentUser"];
export type DevLoginChoice = Schemas["DevLoginChoice"];

/** The signed-in User, or null when there's no session. */
export async function fetchCurrentUser(): Promise<CurrentUser | null> {
  try {
    return await request<CurrentUser>("/auth/me");
  } catch (error) {
    if (error instanceof ApiError && error.status === 401) return null;
    throw error;
  }
}

/** Dev only: every active Practice Membership you can sign in as (a User at two Practices appears twice). */
export async function fetchDevLoginChoices(): Promise<DevLoginChoice[]> {
  try {
    return await request<DevLoginChoice[]>("/auth/dev-login/users");
  } catch (error) {
    const status = error instanceof ApiError ? error.status : "no answer";
    throw new Error(`The dev login isn't available (${status}). Is VIGIL_DEV_LOGIN_ENABLED=true?`);
  }
}

/** Signs in as the User, acting in one of their Practices. */
export const devLogin = (userId: string, practiceId: string) =>
  request<CurrentUser>("/auth/dev-login", { method: "POST", body: JSON.stringify({ user_id: userId, practice_id: practiceId }) });

/** Ends the session. Already signed out (401) counts as done. */
export async function logout(): Promise<void> {
  try {
    await request<void>("/auth/logout", { method: "POST" });
  } catch (error) {
    if (!(error instanceof ApiError && error.status === 401)) throw error;
  }
}
