"use client";

import { useRouter } from "next/navigation";
import { useEffect } from "react";
import { useViewer } from "@/components/shell/ViewerProvider";
import { homePath } from "@/lib/jobTitles";

export default function Home() {
  const router = useRouter();
  const { session } = useViewer();
  useEffect(() => {
    if (session.status === "signed_in") router.replace(homePath(session.user.job_title));
    if (session.status === "signed_out") router.replace("/login");
  }, [router, session]);
  return null;
}
