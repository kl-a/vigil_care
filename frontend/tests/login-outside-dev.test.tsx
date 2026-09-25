import { render, screen } from "@testing-library/react";
import { describe, expect, it, vi } from "vitest";

vi.mock("next/navigation", () => ({ usePathname: () => "/login", useRouter: () => ({ replace: vi.fn() }) }));
vi.mock("@/lib/environment", () => ({ ENVIRONMENT: "test" }));
const fetchDevLoginChoices = vi.hoisted(() => vi.fn());
vi.mock("@/lib/session", () => ({ fetchDevLoginChoices, devLogin: vi.fn(), fetchCurrentUser: vi.fn(), logout: vi.fn() }));

import LoginPage from "@/app/login/page";
import { ViewerProvider } from "@/components/shell/ViewerProvider";

describe("Login screen outside dev", () => {
  it("has no dev login option and never asks for the seeded Users", () => {
    render(
      <ViewerProvider loadUser={async () => null}>
        <LoginPage />
      </ViewerProvider>,
    );
    expect(screen.getByRole("heading", { name: "Sign in" })).toBeInTheDocument();
    expect(screen.queryByText(/dev login/i)).not.toBeInTheDocument();
    expect(screen.queryByRole("list", { name: "Users" })).not.toBeInTheDocument();
    expect(fetchDevLoginChoices).not.toHaveBeenCalled();
  });
});
