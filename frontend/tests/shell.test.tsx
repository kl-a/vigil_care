import { fireEvent, render, screen, within } from "@testing-library/react";
import { beforeEach, describe, expect, it, vi } from "vitest";

let pathname = "/dashboard";
vi.mock("next/navigation", () => ({ usePathname: () => pathname, useRouter: () => ({ replace: vi.fn() }) }));

import { AppShell } from "@/components/shell/AppShell";
import { EnvironmentBadge } from "@/components/shell/EnvironmentBadge";
import { ViewerProvider } from "@/components/shell/ViewerProvider";

function renderShell(at: string) {
  pathname = at;
  return render(
    <ViewerProvider>
      <AppShell><p>screen content</p></AppShell>
    </ViewerProvider>,
  );
}

const mainNav = () => within(screen.getByRole("navigation", { name: "Main" }));

function previewAs(label: string) {
  fireEvent.change(screen.getByLabelText(/preview as/i), { target: { value: label } });
}

describe("app shell", () => {
  beforeEach(() => window.localStorage.clear());

  it("shows the environment badge and the screen content for a clinician", () => {
    renderShell("/dashboard");
    expect(screen.getByText("DEV")).toBeInTheDocument();
    expect(screen.getByText("screen content")).toBeInTheDocument();
    expect(mainNav().getByRole("link", { name: "Patients" })).toBeInTheDocument();
  });

  it("marks the current section in the navigation", () => {
    renderShell("/patients/jane/summary");
    expect(mainNav().getByRole("link", { name: "Patients" })).toHaveAttribute("aria-current", "page");
  });

  it("gives a developer admin a 403 on Patient screens and no Patient navigation", () => {
    renderShell("/patients/jane/summary");
    previewAs("developer_admin");
    expect(screen.getByRole("heading", { name: "Not available for your Job Title" })).toBeInTheDocument();
    expect(screen.queryByText("screen content")).not.toBeInTheDocument();
    expect(mainNav().queryByRole("link", { name: "Patients" })).not.toBeInTheDocument();
    expect(screen.queryByPlaceholderText(/search patients/i)).not.toBeInTheDocument();
    expect(mainNav().getByRole("link", { name: "System status" })).toBeInTheDocument();
  });

  it("gives a trial coordinator a 403 on User Management", () => {
    renderShell("/users");
    previewAs("trial_coordinator");
    expect(screen.getByText("This page isn't available to a Trial coordinator.")).toBeInTheDocument();
  });

  it("remembers the previewed Job Title", () => {
    renderShell("/system");
    previewAs("secretary");
    expect(window.localStorage.getItem("vigil.previewJobTitle")).toBe("secretary");
  });
});

describe("environment badge", () => {
  it("labels the test environment", () => {
    render(<EnvironmentBadge environment="test" />);
    expect(screen.getByText("TEST")).toHaveAttribute("title", "Test environment");
  });
});
