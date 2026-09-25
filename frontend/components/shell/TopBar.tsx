"use client";

import Link from "next/link";
import { useRouter } from "next/navigation";
import { LogOut, Moon, PanelLeft, Search, Sun } from "lucide-react";
import { ENVIRONMENT } from "@/lib/environment";
import { JOB_TITLE_LABEL, homePath, seesPatientData } from "@/lib/jobTitles";
import { EnvironmentBadge } from "./EnvironmentBadge";
import { useSignedInUser, useViewer } from "./ViewerProvider";

function initials(name: string): string {
  const words = name.replace(/^(Dr|Prof|A\/Prof)\.?\s+/i, "").split(/\s+/).filter(Boolean);
  return words.slice(0, 2).map((word) => word[0]?.toUpperCase() ?? "").join("");
}

export function TopBar({ onToggleSidebar }: { onToggleSidebar: () => void }) {
  const router = useRouter();
  const { signOut, theme, toggleTheme, showUpcoming, toggleShowUpcoming } = useViewer();
  const user = useSignedInUser();
  const jobTitle = user.job_title;

  async function handleLogOut() {
    await signOut();
    router.replace("/login");
  }

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
      {ENVIRONMENT === "dev" && (
        <label className="flex h-8 flex-none cursor-pointer items-center gap-1.5 whitespace-nowrap rounded-md border border-dashed border-dev/50 px-2 text-xs text-dev">
          <input type="checkbox" checked={showUpcoming} onChange={toggleShowUpcoming} className="accent-current" />
          Show upcoming screens
        </label>
      )}
      <button aria-label="Toggle dark theme" onClick={toggleTheme} className="flex h-8 w-8 items-center justify-center rounded-md border border-border">
        {theme === "dark" ? <Sun aria-hidden className="h-[15px] w-[15px]" /> : <Moon aria-hidden className="h-[15px] w-[15px]" />}
      </button>
      <div className="flex h-8 items-center gap-2 pl-1 text-xs" title={user.practice_name}>
        <span aria-hidden className="flex h-6 w-6 items-center justify-center rounded-full bg-accent text-[11px] font-semibold text-primary">
          {initials(user.display_name)}
        </span>
        <span className="flex flex-col leading-tight">
          <span className="font-medium">{user.display_name}</span>
          <span className="text-[11px] text-muted-foreground">{JOB_TITLE_LABEL[jobTitle]}</span>
        </span>
      </div>
      <button onClick={handleLogOut} className="flex h-8 items-center gap-1.5 rounded-md border border-border px-2 text-xs hover:bg-muted">
        <LogOut aria-hidden className="h-3.5 w-3.5" />
        Log out
      </button>
    </header>
  );
}
