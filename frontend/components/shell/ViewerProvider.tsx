"use client";

import { createContext, useCallback, useContext, useEffect, useState, type ReactNode } from "react";
import { ENVIRONMENT } from "@/lib/environment";
import { isJobTitle, type JobTitle } from "@/lib/jobTitles";

type Theme = "light" | "dark";

interface Viewer {
  jobTitle: JobTitle;
  /** Dev-only "Preview as" until real sessions arrive (ticket #4). */
  canPreviewJobTitles: boolean;
  setPreviewJobTitle: (jobTitle: JobTitle) => void;
  theme: Theme;
  toggleTheme: () => void;
}

const PREVIEW_KEY = "vigil.previewJobTitle";
const THEME_KEY = "vigil.theme";
const ViewerContext = createContext<Viewer | null>(null);

function read(key: string): string | null {
  try { return window.localStorage.getItem(key); } catch { return null; }
}
function write(key: string, value: string): void {
  try { window.localStorage.setItem(key, value); } catch { /* storage unavailable: keep in memory only */ }
}

export function ViewerProvider({ children }: { children: ReactNode }) {
  const canPreviewJobTitles = ENVIRONMENT === "dev";
  const [jobTitle, setJobTitle] = useState<JobTitle>("clinician");
  const [theme, setTheme] = useState<Theme>("light");

  useEffect(() => {
    const stored = read(PREVIEW_KEY);
    if (canPreviewJobTitles && isJobTitle(stored)) setJobTitle(stored);
    if (read(THEME_KEY) === "dark") setTheme("dark");
  }, [canPreviewJobTitles]);

  useEffect(() => {
    document.documentElement.dataset.theme = theme;
  }, [theme]);

  const setPreviewJobTitle = useCallback((next: JobTitle) => {
    if (!canPreviewJobTitles) return;
    setJobTitle(next);
    write(PREVIEW_KEY, next);
  }, [canPreviewJobTitles]);

  const toggleTheme = useCallback(() => {
    setTheme((current) => {
      const next = current === "dark" ? "light" : "dark";
      write(THEME_KEY, next);
      return next;
    });
  }, []);

  return (
    <ViewerContext.Provider value={{ jobTitle, canPreviewJobTitles, setPreviewJobTitle, theme, toggleTheme }}>
      {children}
    </ViewerContext.Provider>
  );
}

export function useViewer(): Viewer {
  const viewer = useContext(ViewerContext);
  if (!viewer) throw new Error("useViewer must be used inside ViewerProvider");
  return viewer;
}
