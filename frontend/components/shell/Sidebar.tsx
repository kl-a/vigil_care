"use client";

import Link from "next/link";
import { useEffect, useState } from "react";
import type { JobTitle } from "@/lib/jobTitles";
import { navItemForPath, navigationFor, screenOf, type NavItem } from "@/lib/navigation";
import { isReleased, isVisible } from "@/lib/stages";
import { fetchOpenItems, mayAct } from "@/lib/summary";
import { NAV_ICONS } from "./icons";

function NavLink({ item, current, expanded, badge }: { item: NavItem; current: boolean; expanded: boolean; badge?: number | null }) {
  const Icon = NAV_ICONS[item.icon];
  return (
    <Link
      href={item.href}
      title={item.label}
      aria-current={current ? "page" : undefined}
      className={`flex h-8 items-center gap-2.5 rounded-md pr-2 text-[13px] font-medium hover:bg-muted ${
        item.sub && expanded ? "pl-[26px]" : "pl-2"
      } ${current ? "bg-accent text-primary" : "text-foreground"}`}
    >
      <Icon aria-hidden className="h-[15px] w-[15px] flex-none" />
      {expanded && <span className="flex-1 whitespace-nowrap">{item.label}</span>}
      {expanded && badge ? (
        <span aria-label={`${badge} Open Items you can act on`} className="rounded-full border border-cau-bd bg-cau-bg px-1.5 text-[11px] font-semibold tabular-nums text-cau">{badge}</span>
      ) : null}
      {expanded && !isReleased(screenOf(item)) && (
        <span title={`Coming in Stage ${screenOf(item).stage}`} className="rounded bg-dev-bg px-1 font-mono text-[10px] text-dev">S{screenOf(item).stage}</span>
      )}
    </Link>
  );
}

export function Sidebar({ jobTitle, pathname, expanded, showUpcoming }: { jobTitle: JobTitle; pathname: string; expanded: boolean; showUpcoming: boolean }) {
  const { main, admin } = navigationFor(jobTitle, (screen) => isVisible(screen, showUpcoming));
  const currentId = navItemForPath(pathname)?.id;
  // The Dashboard's count: Open Items this User can act on, fresh on every navigation (never for the developer admin).
  const counts = jobTitle !== "developer_admin" && main.some((item) => item.id === "dashboard");
  const [actionable, setActionable] = useState<number | null>(null);
  useEffect(() => {
    if (!counts) return;
    fetchOpenItems().then((items) => setActionable(items.filter((i) => mayAct(i.who, jobTitle)).length)).catch(() => setActionable(null));
  }, [counts, jobTitle, pathname]);
  // The column carries the background and border the full height of the page; the links stay in view as it scrolls.
  return (
    <div data-noprint="" className={`flex-none border-r border-border bg-card transition-[width] ${expanded ? "w-[208px]" : "w-[52px]"}`}>
    <nav aria-label="Main" className="sticky top-12 flex h-[calc(100vh-48px)] flex-col gap-px overflow-y-auto p-2">
      {main.map((item) => <NavLink key={item.id} item={item} current={item.id === currentId} expanded={expanded} badge={item.id === "dashboard" ? actionable : null} />)}
      {main.length > 0 && <div className="mx-1 my-2 h-px bg-border" />}
      {admin.map((item) => <NavLink key={item.id} item={item} current={item.id === currentId} expanded={expanded} />)}
    </nav>
    </div>
  );
}
