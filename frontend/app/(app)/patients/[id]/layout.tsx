import type { ReactNode } from "react";
import { PatientTabs } from "@/components/PatientTabs";
import { PatientHeader, PatientProvider } from "@/components/patients/PatientContext";

export default function PatientLayout({ children, params }: { children: ReactNode; params: { id: string } }) {
  return (
    <PatientProvider patientId={params.id}>
      <div className="flex flex-col">
        <div className="border-b border-border px-5 pt-3">
          <PatientHeader />
          <PatientTabs patientId={params.id} />
        </div>
        {children}
      </div>
    </PatientProvider>
  );
}
