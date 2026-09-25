"use client";

import { createContext, useCallback, useContext, useEffect, useState, type ReactNode } from "react";
import type { JobTitle } from "@/lib/jobTitles";
import { fetchCurrentUser, logout, type CurrentUser } from "@/lib/session";

type Theme = "light" | "dark";

/** Who is signed in. Comes from the backend session; in dev you choose a seeded User at the dev login (#13). */
export type SessionState =
  | { status: "loading" }
  | { status: "signed_out" }
  | { status: "signed_in"; user: CurrentUser };

interface Viewer {
  session: SessionState;
  /** The signed-in User's Job Title; null until someone is signed in. */
  jobTitle: JobTitle | null;
  signedIn: (user: CurrentUser) => void;
  signOut: () => Promise<void>;
  theme: Theme;
  toggleTheme: () => void;
}

const THEME_KEY = "vigil.theme";
const ViewerContext = createContext<Viewer | null>(null);

function read(key: string): string | null {
  try { return window.localStorage.getItem(key); } catch { return null; }
}
function write(key: string, value: string): void {
  try { window.localStorage.setItem(key, value); } catch { /* storage unavailable: keep in memory only */ }
}

interface ViewerProviderProps {
  children: ReactNode;
  /** Injectable for tests; defaults to asking the backend. */
  loadUser?: () => Promise<CurrentUser | null>;
  endSession?: () => Promise<void>;
}

export function ViewerProvider({ children, loadUser = fetchCurrentUser, endSession = logout }: ViewerProviderProps) {
  const [session, setSession] = useState<SessionState>({ status: "loading" });
  const [theme, setTheme] = useState<Theme>("light");

  useEffect(() => {
    let cancelled = false;
    loadUser()
      .then((user) => { if (!cancelled) setSession(user ? { status: "signed_in", user } : { status: "signed_out" }); })
      .catch(() => { if (!cancelled) setSession({ status: "signed_out" }); });
    return () => { cancelled = true; };
  }, [loadUser]);

  useEffect(() => {
    if (read(THEME_KEY) === "dark") setTheme("dark");
  }, []);

  useEffect(() => {
    document.documentElement.dataset.theme = theme;
  }, [theme]);

  const signedIn = useCallback((user: CurrentUser) => setSession({ status: "signed_in", user }), []);

  const signOut = useCallback(async () => {
    try { await endSession(); } finally { setSession({ status: "signed_out" }); }
  }, [endSession]);

  const toggleTheme = useCallback(() => {
    setTheme((current) => {
      const next = current === "dark" ? "light" : "dark";
      write(THEME_KEY, next);
      return next;
    });
  }, []);

  const jobTitle = session.status === "signed_in" ? session.user.job_title : null;
  return (
    <ViewerContext.Provider value={{ session, jobTitle, signedIn, signOut, theme, toggleTheme }}>
      {children}
    </ViewerContext.Provider>
  );
}

export function useViewer(): Viewer {
  const viewer = useContext(ViewerContext);
  if (!viewer) throw new Error("useViewer must be used inside ViewerProvider");
  return viewer;
}

/** For screens inside the app shell, which renders only once someone is signed in. */
export function useSignedInUser(): CurrentUser {
  const { session } = useViewer();
  if (session.status !== "signed_in") throw new Error("useSignedInUser must be used inside the signed-in app shell");
  return session.user;
}
