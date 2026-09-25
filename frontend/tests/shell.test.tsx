import { fireEvent, render, screen, waitFor, within } from "@testing-library/react";
import { beforeEach, describe, expect, it, vi } from "vitest";

let pathname = "/dashboard";
const replace = vi.fn();
vi.mock("next/navigation", () => ({ usePathname: () => pathname, useRouter: () => ({ replace }) }));

import { AppShell } from "@/components/shell/AppShell";
import { EnvironmentBadge } from "@/components/shell/EnvironmentBadge";
import { ViewerProvider } from "@/components/shell/ViewerProvider";
import type { JobTitle } from "@/lib/jobTitles";
import type { CurrentUser } from "@/lib/session";
import { userWith } from "./fixtures";

async function renderShell(at: string, user: CurrentUser | null, endSession = vi.fn(async () => {})) {
  pathname = at;
  render(
    <ViewerProvider loadUser={async () => user} endSession={endSession}>
      <AppShell><p>screen content</p></AppShell>
    </ViewerProvider>,
  );
  if (user) await screen.findByRole("navigation", { name: "Main" });
}

const signedInAs = (jobTitle: JobTitle) => userWith(jobTitle);
const mainNav = () => within(screen.getByRole("navigation", { name: "Main" }));

describe("app shell", () => {
  beforeEach(() => { window.localStorage.clear(); replace.mockClear(); });

  it("shows the signed-in User, the environment badge and the screen content", async () => {
    await renderShell("/dashboard", signedInAs("clinician"));
    expect(screen.getByText("DEV")).toBeInTheDocument();
    expect(screen.getByText("Dr Alex Rivera")).toBeInTheDocument();
    expect(screen.getByText("Clinician")).toBeInTheDocument();
    expect(screen.getByText("screen content")).toBeInTheDocument();
    expect(mainNav().getByRole("link", { name: "Patients" })).toBeInTheDocument();
  });

  it("has no Preview as: the Job Title comes from the session", async () => {
    await renderShell("/dashboard", signedInAs("clinician"));
    expect(screen.queryByLabelText(/preview as/i)).not.toBeInTheDocument();
  });

  it("marks the current section in the navigation", async () => {
    await renderShell("/patients/jane/summary", signedInAs("secretary"));
    expect(mainNav().getByRole("link", { name: "Patients" })).toHaveAttribute("aria-current", "page");
  });

  it("gives a developer admin a 403 on Patient screens and no Patient navigation", async () => {
    await renderShell("/patients/jane/summary", signedInAs("developer_admin"));
    expect(screen.getByRole("heading", { name: "Not available for your Job Title" })).toBeInTheDocument();
    expect(screen.queryByText("screen content")).not.toBeInTheDocument();
    expect(mainNav().queryByRole("link", { name: "Patients" })).not.toBeInTheDocument();
    expect(screen.queryByPlaceholderText(/search patients/i)).not.toBeInTheDocument();
    expect(mainNav().getByRole("link", { name: "System status" })).toBeInTheDocument();
  });

  it("gives a trial coordinator a 403 on User Management", async () => {
    await renderShell("/users", signedInAs("trial_coordinator"));
    expect(screen.getByText("This page isn't available to a Trial coordinator.")).toBeInTheDocument();
  });

  it("sends you to the Login screen when nobody is signed in", async () => {
    await renderShell("/dashboard", null);
    await waitFor(() => expect(replace).toHaveBeenCalledWith("/login"));
    expect(screen.queryByText("screen content")).not.toBeInTheDocument();
  });

  it("logs out and returns to the Login screen", async () => {
    const endSession = vi.fn(async () => {});
    await renderShell("/dashboard", signedInAs("clinician"), endSession);
    fireEvent.click(screen.getByRole("button", { name: /log out/i }));
    await waitFor(() => expect(replace).toHaveBeenCalledWith("/login"));
    expect(endSession).toHaveBeenCalled();
  });
});

describe("environment badge", () => {
  it("labels the test environment", () => {
    render(<EnvironmentBadge environment="test" />);
    expect(screen.getByText("TEST")).toHaveAttribute("title", "Test environment");
  });
});
