import Link from "next/link";
import type { JobTitle } from "@/lib/jobTitles";
import { navItemForPath, navigationFor, screenOf, type NavItem } from "@/lib/navigation";
import { isReleased, isVisible } from "@/lib/stages";
import { NAV_ICONS } from "./icons";

function NavLink({ item, current, expanded }: { item: NavItem; current: boolean; expanded: boolean }) {
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
      {expanded && !isReleased(screenOf(item)) && (
        <span title={`Coming in Stage ${screenOf(item).stage}`} className="rounded bg-dev-bg px-1 font-mono text-[10px] text-dev">S{screenOf(item).stage}</span>
      )}
    </Link>
  );
}

export function Sidebar({ jobTitle, pathname, expanded, showUpcoming }: { jobTitle: JobTitle; pathname: string; expanded: boolean; showUpcoming: boolean }) {
  const { main, admin } = navigationFor(jobTitle, (screen) => isVisible(screen, showUpcoming));
  const currentId = navItemForPath(pathname)?.id;
  return (
    <nav
      aria-label="Main"
      data-noprint=""
      className={`sticky top-12 flex h-[calc(100vh-48px)] flex-none flex-col gap-px self-start overflow-y-auto border-r border-border bg-card p-2 transition-[width] ${
        expanded ? "w-[208px]" : "w-[52px]"
      }`}
    >
      {main.map((item) => <NavLink key={item.id} item={item} current={item.id === currentId} expanded={expanded} />)}
      {main.length > 0 && <div className="mx-1 my-2 h-px bg-border" />}
      {admin.map((item) => <NavLink key={item.id} item={item} current={item.id === currentId} expanded={expanded} />)}
    </nav>
  );
}
