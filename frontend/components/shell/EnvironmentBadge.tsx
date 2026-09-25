import { FlaskConical, ShieldCheck, Wrench } from "lucide-react";
import type { VigilEnvironment } from "@/lib/environment";

const BADGE: Record<VigilEnvironment, { label: string; title: string; className: string; Icon: typeof Wrench }> = {
  dev: { label: "DEV", title: "Development environment", className: "text-dev bg-dev-bg", Icon: Wrench },
  test: { label: "TEST", title: "Test environment", className: "text-test bg-test-bg", Icon: FlaskConical },
  prod: { label: "PROD", title: "Production environment", className: "text-neu bg-neu-bg", Icon: ShieldCheck },
};

export function EnvironmentBadge({ environment }: { environment: VigilEnvironment }) {
  const { label, title, className, Icon } = BADGE[environment];
  return (
    <span title={title} className={`inline-flex h-[22px] items-center gap-1 rounded px-[7px] font-mono text-[11px] font-medium ${className}`}>
      <Icon aria-hidden className="h-[11px] w-[11px]" />
      {label}
    </span>
  );
}
