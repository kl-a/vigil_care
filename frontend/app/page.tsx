"use client";

import { useRouter } from "next/navigation";
import { useEffect } from "react";
import { useViewer } from "@/components/shell/ViewerProvider";
import { homePath } from "@/lib/jobTitles";

export default function Home() {
  const router = useRouter();
  const { jobTitle } = useViewer();
  useEffect(() => router.replace(homePath(jobTitle)), [router, jobTitle]);
  return null;
}
