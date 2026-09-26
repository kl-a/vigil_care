"use client";

import Link from "next/link";
import { usePathname, useRouter } from "next/navigation";
import { ChevronRight } from "lucide-react";
import { useEffect, useState, type ReactNode } from "react";
import { homePath } from "@/lib/jobTitles";
import { canAccess, standInFor } from "@/lib/navigation";
import { screenForPathname } from "@/lib/screens";
import { isReleased, isVisible } from "@/lib/stages";
import { Forbidden } from "./Forbidden";
import { NotYetAvailable } from "./NotYetAvailable";
import { Sidebar } from "./Sidebar";
import { TopBar } from "./TopBar";
import { useViewer } from "./ViewerProvider";

function crumbsFor(pathname: string): { label: string; href: string }[] {
  const segments = pathname.split("/").filter(Boolean);
  return segments.map((segment, index) => ({
    label: segment.replace(/-/g, " ").replace(/^\w/, (c) => c.toUpperCase()),
    href: "/" + segments.slice(0, index + 1).join("/"),
  }));
}

export function AppShell({ children }: { children: ReactNode }) {
  const pathname = usePathname();
  const router = useRouter();
  const { session, showUpcoming, modules, refreshModules } = useViewer();
  const [expanded, setExpanded] = useState(true);

  useEffect(() => {
    if (session.status === "signed_out") router.replace("/login");
  }, [session.status, router]);

  // E.g. a developer admin's Dashboard is System status.
  const standIn = session.status === "signed_in" ? standInFor(pathname, session.user.job_title) : undefined;
  useEffect(() => {
    if (standIn) router.replace(standIn);
  }, [standIn, router]);

  // Another User (a developer admin) may have switched a module: pick it up on every navigation.
  const signedIn = session.status === "signed_in";
  useEffect(() => {
    if (signedIn) void refreshModules();
  }, [pathname, signedIn, refreshModules]);

  if (session.status === "loading") return <p role="status" className="p-6 text-sm text-muted-foreground">Loading…</p>;
  if (session.status === "signed_out") return null;

  const { job_title: jobTitle } = session.user;
  const crumbs = crumbsFor(pathname);
  const screen = screenForPathname(pathname, modules);
  const crumbVisible = (href: string) => {
    const crumbScreen = screenForPathname(href, modules);
    return crumbScreen === undefined || isVisible(crumbScreen, showUpcoming);
  };

  const allowed = canAccess(pathname, jobTitle);
  const available = screen === undefined || isVisible(screen, showUpcoming);
  // An upcoming screen shown only because of the dev toggle gets a note saying so.
  const previewing = allowed && screen !== undefined && available && !isReleased(screen);
  let content: ReactNode = children;
  if (standIn) content = null;
  else if (!allowed) content = <Forbidden jobTitle={jobTitle} />;
  else if (!available) content = <NotYetAvailable title={screen?.title ?? "This screen"} home={homePath(jobTitle)} />;

  return (
    <div className="flex min-h-screen flex-col">
      <TopBar onToggleSidebar={() => setExpanded((value) => !value)} />
      <div className="flex min-h-0 flex-1">
        <Sidebar jobTitle={jobTitle} pathname={pathname} expanded={expanded} showUpcoming={showUpcoming} />
        <main className="flex min-w-0 flex-1 flex-col">
          <nav aria-label="Breadcrumb" data-noprint="" className="flex flex-wrap items-center gap-1.5 px-5 pt-2.5 text-xs text-muted-foreground">
            {crumbs.map((crumb, index) => (
              <span key={crumb.href} className="inline-flex items-center gap-1.5">
                {index > 0 && <ChevronRight aria-hidden className="h-[11px] w-[11px]" />}
                {crumbVisible(crumb.href)
                  ? <Link href={crumb.href} className={index === crumbs.length - 1 ? "text-foreground" : "text-muted-foreground"}>{crumb.label}</Link>
                  : <span>{crumb.label}</span>}
              </span>
            ))}
          </nav>
          {previewing && (
            <p role="note" className="mx-5 mt-2 rounded-md border border-dashed border-dev/60 bg-dev-bg px-3 py-1.5 text-xs text-dev">
              Upcoming screen: coming in Stage {screen.stage}. Shown because &ldquo;Show upcoming screens&rdquo; is on (dev only).
            </p>
          )}
          {content}
        </main>
      </div>
    </div>
  );
}
