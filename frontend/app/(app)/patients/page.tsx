import Link from "next/link";
import { ScreenPlaceholder } from "@/components/ScreenPlaceholder";

export default function PatientsPage() {
  return (
    <ScreenPlaceholder path="/patients">
      <p className="m-0 text-[13px]">
        Sample Patient for navigating the Patient screens: <Link href="/patients/jane/overview">Jane Citizen (synthetic)</Link>
      </p>
    </ScreenPlaceholder>
  );
}
