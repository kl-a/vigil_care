"use client";

import { useRouter } from "next/navigation";
import { useEffect, useState } from "react";
import { EnvironmentBadge } from "@/components/shell/EnvironmentBadge";
import { useViewer } from "@/components/shell/ViewerProvider";
import { messageOf } from "@/lib/api";
import { ENVIRONMENT } from "@/lib/environment";
import { JOB_TITLE_LABEL, homePath } from "@/lib/jobTitles";
import { devLogin, fetchDevLoginChoices, type DevLoginChoice } from "@/lib/session";

type Choices = { status: "loading" } | { status: "ready"; users: DevLoginChoice[] } | { status: "error"; message: string };

export default function LoginPage() {
  return (
    <div data-screen-label="Login" className="flex min-h-screen items-center justify-center bg-background p-6">
      <div className="flex w-full max-w-[420px] flex-col gap-4">
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-2">
            <span className="flex h-[26px] w-[26px] items-center justify-center rounded-md bg-primary font-semibold text-primary-foreground">V</span>
            <span className="text-base font-semibold">Vigil</span>
          </div>
          <EnvironmentBadge environment={ENVIRONMENT} />
        </div>
        {ENVIRONMENT === "dev" ? <DevLogin /> : <NotYet />}
      </div>
    </div>
  );
}

function NotYet() {
  return (
    <div className="flex flex-col gap-2 rounded-md border border-border bg-card p-6 shadow-card">
      <h1 className="m-0 text-lg font-semibold">Sign in</h1>
      <p className="m-0 text-[13px] text-muted-foreground">
        Sign-in with a password and 2FA arrives in Stage 13. Until then Vigil is used only in the dev environment.
      </p>
    </div>
  );
}

/** A User at two Practices is two choices. */
const membershipKey = (choice: DevLoginChoice) => `${choice.id}:${choice.practice_id}`;

function DevLogin() {
  const router = useRouter();
  const { session, signIn } = useViewer();
  const [choices, setChoices] = useState<Choices>({ status: "loading" });
  const [signingIn, setSigningIn] = useState<string | null>(null); // the chosen Membership's key
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    if (session.status === "signed_in") router.replace(homePath(session.user.job_title));
  }, [session, router]);

  useEffect(() => {
    fetchDevLoginChoices()
      .then((users) => setChoices({ status: "ready", users }))
      .catch((reason: unknown) => setChoices({ status: "error", message: messageOf(reason) }));
  }, []);

  async function choose(user: DevLoginChoice) {
    setSigningIn(membershipKey(user));
    setError(null);
    try {
      const signedInUser = await devLogin(user.id, user.practice_id);
      signIn(signedInUser);
      router.replace(homePath(signedInUser.job_title));
    } catch (reason) {
      setError(messageOf(reason));
      setSigningIn(null);
    }
  }

  return (
    <div className="flex flex-col gap-3 rounded-md border border-dashed border-dev/60 bg-card p-6 shadow-card">
      <div className="flex items-center justify-between gap-2">
        <h1 className="m-0 text-lg font-semibold">Dev login</h1>
        <span className="rounded bg-dev-bg px-1.5 py-0.5 text-[11px] font-semibold text-dev">DEV ONLY</span>
      </div>
      <p className="m-0 text-[13px] text-muted-foreground">
        Choose who you are. No password or 2FA: this exists only in the dev environment, with synthetic data.
      </p>
      {choices.status === "loading" && <p role="status" className="m-0 text-[13px] text-muted-foreground">Loading Users…</p>}
      {choices.status === "error" && <p role="alert" className="m-0 text-[13px] text-neg">{choices.message}</p>}
      {choices.status === "ready" && choices.users.length === 0 && (
        <p className="m-0 text-[13px] text-muted-foreground">
          No Users yet. Load the synthetic demo Practice with <code className="font-mono">make demo-data</code>.
        </p>
      )}
      {choices.status === "ready" && choices.users.length > 0 && (
        <ul aria-label="Users" className="m-0 flex list-none flex-col gap-1.5 p-0">
          {choices.users.map((user) => (
            <li key={membershipKey(user)}>
              <button
                onClick={() => choose(user)}
                disabled={signingIn !== null}
                className="flex w-full items-center justify-between gap-3 rounded-md border border-border px-3 py-2 text-left hover:bg-muted disabled:opacity-60"
              >
                <span className="flex flex-col">
                  <span className="text-[13px] font-medium">{user.display_name}</span>
                  <span className="text-[11px] text-muted-foreground">{user.practice_name}</span>
                </span>
                <span className="text-xs text-muted-foreground">
                  {signingIn === membershipKey(user) ? "Signing in…" : JOB_TITLE_LABEL[user.job_title]}
                </span>
              </button>
            </li>
          ))}
        </ul>
      )}
      {error && <p role="alert" className="m-0 text-[13px] text-neg">{error}</p>}
    </div>
  );
}
