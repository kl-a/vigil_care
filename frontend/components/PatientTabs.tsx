"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import { patientTabsFor } from "@/lib/modules/registry";
import { isVisible } from "@/lib/stages";
import { useViewer } from "./shell/ViewerProvider";

export function PatientTabs({ patientId }: { patientId: string }) {
  const pathname = usePathname();
  const { showUpcoming, activeModules } = useViewer();
  return (
    <nav aria-label="Patient" className="flex gap-4 overflow-x-auto text-[13px]">
      {patientTabsFor(activeModules).filter((tab) => isVisible(tab.screen, showUpcoming)).map((tab) => {
        const href = `/patients/${patientId}/${tab.segment}`;
        const current = pathname === href;
        return (
          <Link key={tab.segment} href={href} aria-current={current ? "page" : undefined}
            className={`whitespace-nowrap border-b-2 pb-2 font-medium ${current ? "border-primary text-foreground" : "border-transparent text-muted-foreground"}`}>
            {tab.label}
          </Link>
        );
      })}
    </nav>
  );
}
