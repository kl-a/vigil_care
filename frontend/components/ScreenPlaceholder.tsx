import { notFound } from "next/navigation";
import type { ReactNode } from "react";
import { screenForPath } from "@/lib/screens";

/** Stand-in for a screen that later tickets will build (docs/frontend-design.md §8). */
export function ScreenPlaceholder({ path, children }: { path: string; children?: ReactNode }) {
  const screen = screenForPath(path);
  if (!screen) notFound();
  return (
    <div data-screen-label={screen.title} className="flex w-full max-w-[1600px] flex-col gap-3.5 px-5 pb-8 pt-3">
      <div className="flex items-baseline gap-2.5">
        <h1 className="m-0 text-xl font-semibold">{screen.title}</h1>
        {screen.number !== undefined && <span className="font-mono text-xs text-muted-foreground">Screen {screen.number}</span>}
      </div>
      <p className="m-0 text-[13px] text-muted-foreground">{screen.purpose}</p>
      <div className="rounded-md border border-dashed border-border bg-card p-6 text-[13px] text-muted-foreground">Coming soon.</div>
      {children}
    </div>
  );
}
