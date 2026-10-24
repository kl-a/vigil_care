import { request, type Schemas } from "@/lib/api";
import type { PatientListColumns } from "@/lib/modules/types";

/** Oncology's Clinical Data sub-tab counts (#57), by section id. */
export const fetchOncologyCounts = (patientId: string) => request<Record<string, number>>(`/patients/${patientId}/oncology-counts`);

/** The Patient List's Cancer Type(s) and Disease Extent columns (#57), filterable by Cancer Type. */
export const oncologyPatientListColumns: PatientListColumns = {
  load: async () => {
    const rows = await request<Schemas["PatientListValues"][]>("/patient-list/oncology");
    return Object.fromEntries(rows.map((r) => [r.patient_id, r.values]));
  },
  columns: [{ key: "cancer_types", label: "Cancer Type(s)" }, { key: "disease_extent", label: "Disease Extent" }],
  filter: { key: "cancer_types", label: "Cancer Type" },
};
