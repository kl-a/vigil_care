"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import { ChevronRight } from "lucide-react";
import { useState, type ReactNode } from "react";
import { canAccess } from "@/lib/navigation";
import { Forbidden } from "./Forbidden";
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
  const { jobTitle } = useViewer();
  const [expanded, setExpanded] = useState(true);
  const crumbs = crumbsFor(pathname);
  return (
    <div className="flex min-h-screen flex-col">
      <TopBar onToggleSidebar={() => setExpanded((value) => !value)} />
      <div className="flex min-h-0 flex-1">
        <Sidebar jobTitle={jobTitle} pathname={pathname} expanded={expanded} />
        <main className="flex min-w-0 flex-1 flex-col">
          <nav aria-label="Breadcrumb" data-noprint="" className="flex flex-wrap items-center gap-1.5 px-5 pt-2.5 text-xs text-muted-foreground">
            {crumbs.map((crumb, index) => (
              <span key={crumb.href} className="inline-flex items-center gap-1.5">
                {index > 0 && <ChevronRight aria-hidden className="h-[11px] w-[11px]" />}
                <Link href={crumb.href} className={index === crumbs.length - 1 ? "text-foreground" : "text-muted-foreground"}>{crumb.label}</Link>
              </span>
            ))}
          </nav>
          {canAccess(pathname, jobTitle) ? children : <Forbidden jobTitle={jobTitle} />}
        </main>
      </div>
    </div>
  );
}
