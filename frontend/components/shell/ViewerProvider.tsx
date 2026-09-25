"use client";

import { createContext, useCallback, useContext, useEffect, useState, type ReactNode } from "react";
import { ENVIRONMENT } from "@/lib/environment";
import { fetchModuleConfiguration } from "@/lib/modules/api";
import { NO_MODULES, type ModuleConfiguration } from "@/lib/modules/types";
import { fetchCurrentUser, logout, type CurrentUser } from "@/lib/session";

type Theme = "light" | "dark";

/** Who is signed in. Comes from the backend session; in dev you choose a seeded User at the dev login (#13). */
export type SessionState =
  | { status: "loading" }
  | { status: "signed_out" }
  | { status: "signed_in"; user: CurrentUser };

interface Viewer {
  session: SessionState;
  /** Record a session the backend has just started (e.g. after the dev login). */
  signIn: (user: CurrentUser) => void;
  /** End the session on the backend and here. */
  signOut: () => Promise<void>;
  theme: Theme;
  toggleTheme: () => void;
  /** Dev only: reveal screens whose stage hasn't shipped, as labelled placeholders. Always false elsewhere. */
  showUpcoming: boolean;
  toggleShowUpcoming: () => void;
  /** The Practice's active Specialty Modules, their sections and tabs; none until loaded or signed out. */
  modules: ModuleConfiguration;
  /** False until the active modules have loaded for the signed-in User. */
  modulesReady: boolean;
  /** Reload them, e.g. after a developer admin switches a module in Settings. */
  refreshModules: () => Promise<void>;
}

const THEME_KEY = "vigil.theme";
const UPCOMING_KEY = "vigil.showUpcoming";
const CAN_SHOW_UPCOMING = ENVIRONMENT === "dev";
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
  /** Start signed in as this User (tests of screens inside the shell). */
  initialUser?: CurrentUser;
  loadModules?: () => Promise<ModuleConfiguration>;
}

export function ViewerProvider({ children, loadUser = fetchCurrentUser, endSession = logout, initialUser, loadModules = fetchModuleConfiguration }: ViewerProviderProps) {
  const [session, setSession] = useState<SessionState>(initialUser ? { status: "signed_in", user: initialUser } : { status: "loading" });
  const [theme, setTheme] = useState<Theme>("light");
  const [showUpcoming, setShowUpcoming] = useState(false);
  const [modules, setModules] = useState<ModuleConfiguration>(NO_MODULES);
  const [modulesReady, setModulesReady] = useState(false);

  useEffect(() => {
    if (initialUser) return;
    let cancelled = false;
    loadUser()
      .then((user) => { if (!cancelled) setSession(user ? { status: "signed_in", user } : { status: "signed_out" }); })
      .catch(() => { if (!cancelled) setSession({ status: "signed_out" }); });
    return () => { cancelled = true; };
  }, [loadUser, initialUser]);

  useEffect(() => {
    if (read(THEME_KEY) === "dark") setTheme("dark");
    if (CAN_SHOW_UPCOMING && read(UPCOMING_KEY) === "true") setShowUpcoming(true);
  }, []);

  useEffect(() => {
    document.documentElement.dataset.theme = theme;
  }, [theme]);

  const refreshModules = useCallback(async () => {
    try { setModules(await loadModules()); } catch { setModules(NO_MODULES); } finally { setModulesReady(true); }
  }, [loadModules]);

  const signedInUserId = session.status === "signed_in" ? session.user.id : null;
  useEffect(() => {
    if (signedInUserId) void refreshModules();
    else { setModules(NO_MODULES); setModulesReady(false); }
  }, [signedInUserId, refreshModules]);

  const signIn = useCallback((user: CurrentUser) => setSession({ status: "signed_in", user }), []);

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

  const toggleShowUpcoming = useCallback(() => {
    if (!CAN_SHOW_UPCOMING) return;
    setShowUpcoming((current) => {
      write(UPCOMING_KEY, String(!current));
      return !current;
    });
  }, []);

  return (
    <ViewerContext.Provider value={{ session, signIn, signOut, theme, toggleTheme, showUpcoming, toggleShowUpcoming, modules, modulesReady, refreshModules }}>
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
