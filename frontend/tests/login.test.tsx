import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import { beforeEach, describe, expect, it, vi } from "vitest";

const replace = vi.fn();
vi.mock("next/navigation", () => ({ usePathname: () => "/login", useRouter: () => ({ replace }) }));

const session = vi.hoisted(() => ({
  fetchDevLoginChoices: vi.fn(),
  devLogin: vi.fn(),
  fetchCurrentUser: vi.fn(),
  logout: vi.fn(),
}));
vi.mock("@/lib/session", () => session);

import LoginPage from "@/app/login/page";
import { ViewerProvider } from "@/components/shell/ViewerProvider";
import { choiceFor, userWith } from "./fixtures";

function renderLogin() {
  render(
    <ViewerProvider loadUser={async () => null}>
      <LoginPage />
    </ViewerProvider>,
  );
}

describe("dev login", () => {
  beforeEach(() => {
    replace.mockClear();
    session.fetchDevLoginChoices.mockResolvedValue([choiceFor("clinician"), choiceFor("developer_admin")]);
  });

  it("lists the seeded Users by name and Job Title", async () => {
    renderLogin();
    expect(await screen.findByRole("button", { name: /Dr Alex Rivera/ })).toHaveTextContent("Clinician");
    expect(screen.getByRole("button", { name: /Casey Dev/ })).toHaveTextContent("Developer admin");
    expect(screen.getByText("DEV ONLY")).toBeInTheDocument();
  });

  it("signs in as the chosen User and goes to their home page", async () => {
    session.devLogin.mockResolvedValue(userWith("developer_admin"));
    renderLogin();
    fireEvent.click(await screen.findByRole("button", { name: /Casey Dev/ }));
    await waitFor(() => expect(replace).toHaveBeenCalledWith("/system"));
    expect(session.devLogin).toHaveBeenCalledWith(choiceFor("developer_admin").id);
  });

  it("points to make demo-data when there are no Users", async () => {
    session.fetchDevLoginChoices.mockResolvedValue([]);
    renderLogin();
    expect(await screen.findByText(/make demo-data/)).toBeInTheDocument();
  });

  it("explains when the dev login isn't available", async () => {
    session.fetchDevLoginChoices.mockRejectedValue(new Error("The dev login isn't available (404)."));
    renderLogin();
    expect(await screen.findByRole("alert")).toHaveTextContent("isn't available");
  });
});
