import Link from "next/link";
import { EnvironmentBadge } from "@/components/shell/EnvironmentBadge";
import { ENVIRONMENT } from "@/lib/environment";

export default function NotFound() {
  return (
    <div className="flex min-h-screen flex-col items-center justify-center gap-3 p-10 text-center">
      <EnvironmentBadge environment={ENVIRONMENT} />
      <h1 className="m-0 text-lg font-semibold">Page not found</h1>
      <Link href="/" className="text-[13px] font-medium text-primary">Go to your home page</Link>
    </div>
  );
}
