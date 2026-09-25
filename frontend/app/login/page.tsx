import { EnvironmentBadge } from "@/components/shell/EnvironmentBadge";
import { ENVIRONMENT } from "@/lib/environment";

export default function LoginPage() {
  return (
    <div data-screen-label="Login" className="flex min-h-screen items-center justify-center bg-background p-6">
      <div className="flex w-full max-w-[380px] flex-col gap-4">
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-2">
            <span className="flex h-[26px] w-[26px] items-center justify-center rounded-md bg-primary font-semibold text-primary-foreground">V</span>
            <span className="text-base font-semibold">Vigil</span>
          </div>
          <EnvironmentBadge environment={ENVIRONMENT} />
        </div>
        <div className="flex flex-col gap-2 rounded-md border border-border bg-card p-6 shadow-card">
          <h1 className="m-0 text-lg font-semibold">Sign in</h1>
          <p className="m-0 text-[13px] text-muted-foreground">Screen 1 · Password and 2FA sign-in arrive with ticket #4.</p>
        </div>
      </div>
    </div>
  );
}
