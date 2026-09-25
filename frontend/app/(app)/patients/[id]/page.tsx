import { redirect } from "next/navigation";

export default function PatientIndex({ params }: { params: { id: string } }) {
  redirect(`/patients/${params.id}/overview`);
}
