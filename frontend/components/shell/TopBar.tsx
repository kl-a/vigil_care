"use client";

import Link from "next/link";
import { Moon, PanelLeft, Search, Sun } from "lucide-react";
import { ENVIRONMENT } from "@/lib/environment";
import { JOB_TITLE_LABEL, JOB_TITLES, homePath, seesPatientData, type JobTitle } from "@/lib/jobTitles";
import { EnvironmentBadge } from "./EnvironmentBadge";
import { useViewer } from "./ViewerProvider";

export function TopBar({ onToggleSidebar }: { onToggleSidebar: () => void }) {
  const { jobTitle, canPreviewJobTitles, setPreviewJobTitle, theme, toggleTheme } = useViewer();
  return (
    <header data-noprint="" className="sticky top-0 z-30 flex h-12 items-center gap-3 border-b border-border bg-card px-3">
      <button aria-label="Toggle sidebar" onClick={onToggleSidebar} className="flex h-8 w-8 items-center justify-center rounded-md text-muted-foreground hover:bg-muted">
        <PanelLeft aria-hidden className="h-4 w-4" />
      </button>
      <Link href={homePath(jobTitle)} className="flex items-center gap-2 text-foreground no-underline">
        <span className="flex h-6 w-6 items-center justify-center rounded-[5px] bg-primary text-[13px] font-semibold text-primary-foreground">V</span>
        <span className="text-[15px] font-semibold">Vigil</span>
      </Link>
      {seesPatientData(jobTitle) && (
        <label className="relative ml-3 min-w-[120px] flex-[0_1_340px]">
          <span className="sr-only">Search patients</span>
          <Search aria-hidden className="absolute left-[9px] top-[9px] h-3.5 w-3.5 text-muted-foreground" />
          <input
            placeholder="Search patients by name, MRN or Pseudonym…"
            className="h-8 w-full rounded-md border border-border bg-background pl-[30px] pr-2.5 text-[13px]"
          />
        </label>
      )}
      <div className="flex-1" />
      <EnvironmentBadge environment={ENVIRONMENT} />
      {canPreviewJobTitles && (
        <label className="flex h-8 flex-none items-center gap-1.5 whitespace-nowrap rounded-md border border-dashed border-dev/50 pl-2 pr-1 text-xs text-dev">
          Preview as
          <select
            value={jobTitle}
            onChange={(event) => setPreviewJobTitle(event.target.value as JobTitle)}
            className="h-[26px] cursor-pointer border-0 bg-transparent text-xs font-medium text-foreground"
          >
            {JOB_TITLES.map((title) => <option key={title} value={title}>{JOB_TITLE_LABEL[title]}</option>)}
          </select>
        </label>
      )}
      <button aria-label="Toggle dark theme" onClick={toggleTheme} className="flex h-8 w-8 items-center justify-center rounded-md border border-border">
        {theme === "dark" ? <Sun aria-hidden className="h-[15px] w-[15px]" /> : <Moon aria-hidden className="h-[15px] w-[15px]" />}
      </button>
      <Link href="/login" className="flex h-8 items-center gap-2 rounded-md border border-border pl-1 pr-2 text-xs text-foreground no-underline hover:bg-muted">
        <span className="flex h-6 w-6 items-center justify-center rounded-full bg-accent text-[11px] font-semibold text-primary">?</span>
        <span className="flex flex-col leading-tight">
          <span className="font-medium">Sign in</span>
          <span className="text-[11px] text-muted-foreground">{JOB_TITLE_LABEL[jobTitle]}</span>
        </span>
      </Link>
    </header>
  );
}
