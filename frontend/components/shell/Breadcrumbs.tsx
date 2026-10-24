"use client";

import { ChevronRight } from "lucide-react";
import Link from "next/link";
import { createContext, useContext, useEffect, useState, type ReactNode } from "react";

type Labels = { labels: Record<string, string>; setLabel: (href: string, label: string | null) => void };

const BreadcrumbLabels = createContext<Labels | null>(null);

/** Lets a page name a segment of its path (e.g. a Patient's id becomes their name). */
export function BreadcrumbProvider({ children }: { children: ReactNode }) {
  const [labels, setLabels] = useState<Record<string, string>>({});
  const setLabel = (href: string, label: string | null) =>
    setLabels((all) => {
      if ((all[href] ?? null) === label) return all;
      const next = { ...all };
      if (label === null) delete next[href];
      else next[href] = label;
      return next;
    });
  return <BreadcrumbLabels.Provider value={{ labels, setLabel }}>{children}</BreadcrumbLabels.Provider>;
}

/** Names the crumb for `href` while the calling component is shown. Does nothing outside the app shell. */
export function useBreadcrumbLabel(href: string, label: string | null) {
  const setLabel = useContext(BreadcrumbLabels)?.setLabel;
  useEffect(() => {
    if (!setLabel) return;
    setLabel(href, label);
    return () => setLabel(href, null);
    // eslint-disable-next-line react-hooks/exhaustive-deps -- setLabel is stable in effect
  }, [href, label]);
}

// A path segment that is an id, not a word: shown as what it is ("Patient"), never raw.
const ID = /^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$/i;
const ID_LABEL: Record<string, string> = { patients: "Patient", providers: "Provider", users: "User", pbs: "Drug" };

function crumbsFor(pathname: string, labels: Record<string, string>): { label: string; href: string }[] {
  const segments = pathname.split("/").filter(Boolean);
  return segments.map((segment, index) => {
    const href = "/" + segments.slice(0, index + 1).join("/");
    const fallback = ID.test(segment) ? ID_LABEL[segments[index - 1] ?? ""] ?? "Record" : segment.replace(/-/g, " ").replace(/^\w/, (c) => c.toUpperCase());
    return { href, label: labels[href] ?? fallback };
  });
}

export function Breadcrumbs({ pathname, isVisible }: { pathname: string; isVisible: (href: string) => boolean }) {
  const labels = useContext(BreadcrumbLabels)?.labels ?? {};
  const crumbs = crumbsFor(pathname, labels);
  return (
    <nav aria-label="Breadcrumb" data-noprint="" className="flex flex-wrap items-center gap-1.5 px-5 pt-2.5 text-xs text-muted-foreground">
      {crumbs.map((crumb, index) => (
        <span key={crumb.href} className="inline-flex items-center gap-1.5">
          {index > 0 && <ChevronRight aria-hidden className="h-[11px] w-[11px]" />}
          {isVisible(crumb.href)
            ? <Link href={crumb.href} className={index === crumbs.length - 1 ? "text-foreground" : "text-muted-foreground"}>{crumb.label}</Link>
            : <span>{crumb.label}</span>}
        </span>
      ))}
    </nav>
  );
}
