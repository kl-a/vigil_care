import type { ReactNode } from "react";
import { PatientTabs } from "@/components/PatientTabs";
import { PatientProvider } from "@/components/patients/PatientContext";
import { PatientHeader } from "@/components/patients/PatientHeader";

export default function PatientLayout({ children, params }: { children: ReactNode; params: { id: string } }) {
  return (
    <PatientProvider patientId={params.id}>
      <div className="flex flex-col">
        {/* The header band: one neutral tint for every Patient. */}
        <div className="border-b border-neu-bd bg-neu-bg/60 px-5 pt-3">
          <PatientHeader />
          <PatientTabs patientId={params.id} />
        </div>
        {children}
      </div>
    </PatientProvider>
  );
}
