import { notFound } from "next/navigation";
import type { ReactNode } from "react";
import { screenForPath } from "@/lib/screens";
import { Placeholder } from "./Placeholder";

export function ScreenPlaceholder({ path, children }: { path: string; children?: ReactNode }) {
  const screen = screenForPath(path);
  if (!screen) notFound();
  return <Placeholder screen={screen}>{children}</Placeholder>;
}
