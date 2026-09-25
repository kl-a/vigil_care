import type { ReactNode } from "react";
import { PatientTabs } from "@/components/PatientTabs";

export default function PatientLayout({ children, params }: { children: ReactNode; params: { id: string } }) {
  return (
    <div className="flex flex-col">
      <div className="border-b border-border px-5 pt-3">
        <div className="flex items-baseline gap-2.5 pb-2">
          <span className="text-base font-semibold">Patient</span>
          <span className="font-mono text-xs text-muted-foreground">{params.id}</span>
          <span className="text-xs text-muted-foreground">(Patient header arrives with ticket #8)</span>
        </div>
        <PatientTabs patientId={params.id} />
      </div>
      {children}
    </div>
  );
}
