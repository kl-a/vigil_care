import { render, screen } from "@testing-library/react";
import { describe, expect, it, vi } from "vitest";

vi.mock("next/navigation", () => ({ usePathname: () => "/pbs", useRouter: () => ({ replace: vi.fn() }) }));
vi.mock("@/lib/environment", () => ({ ENVIRONMENT: "test" }));

import { AppShell } from "@/components/shell/AppShell";
import { ViewerProvider } from "@/components/shell/ViewerProvider";
import { userWith } from "./fixtures";

describe("upcoming screens outside dev", () => {
  it("has no Show upcoming screens toggle, and a stored preference is ignored", async () => {
    window.localStorage.setItem("vigil.showUpcoming", "true");
    render(
      <ViewerProvider loadUser={async () => userWith("clinician")}>
        <AppShell><p>placeholder content</p></AppShell>
      </ViewerProvider>,
    );
    await screen.findByRole("navigation", { name: "Main" });
    expect(screen.queryByLabelText("Show upcoming screens")).not.toBeInTheDocument();
    expect(screen.getByRole("heading", { name: "Not available yet" })).toBeInTheDocument();
  });
});
