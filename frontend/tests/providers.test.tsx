import { fireEvent, render, screen, waitFor, within } from "@testing-library/react";
import { beforeEach, describe, expect, it, vi } from "vitest";

vi.mock("next/navigation", () => ({ usePathname: () => "/providers", useRouter: () => ({ replace: vi.fn() }) }));

const providers = vi.hoisted(() => ({ listProviders: vi.fn(), addProvider: vi.fn(), changeProvider: vi.fn(), deleteProvider: vi.fn() }));
vi.mock("@/lib/providers", async (importOriginal) => ({ ...(await importOriginal<object>()), ...providers }));

import ProvidersPage from "@/app/(app)/providers/page";
import { ViewerProvider } from "@/components/shell/ViewerProvider";
import type { ProviderRow } from "@/lib/providers";
import { userWith } from "./fixtures";

const provider = (overrides: Partial<ProviderRow>): ProviderRow => ({
  id: "p-1", display_name: "Dr Morgan Grey", title: "Dr", first_name: "Morgan", last_name: "Grey", provider_number: "123456AB",
  specialty: "general_practice", is_internal: false, organisation: "Example Family Practice", phone: "02 5550 0300",
  email: null, fax: null, notes: null, ...overrides,
});

function renderPage() {
  render(<ViewerProvider initialUser={userWith("secretary")}><ProvidersPage /></ViewerProvider>);
}

describe("Provider Management", () => {
  beforeEach(() => {
    vi.clearAllMocks();
    providers.listProviders.mockResolvedValue([
      provider({}),
      provider({ id: "p-2", display_name: "Dr Alex Rivera", first_name: "Alex", last_name: "Rivera", specialty: "medical_oncology", is_internal: true, provider_number: null }),
    ]);
  });

  it("lists Providers with specialty, internal or external, organisation and number", async () => {
    renderPage();
    const grey = (await screen.findByText("Dr Morgan Grey")).closest("tr")!;
    expect(grey).toHaveTextContent("General practice");
    expect(grey).toHaveTextContent("External");
    expect(grey).toHaveTextContent("Example Family Practice");
    expect(grey).toHaveTextContent("123456AB");
    expect(screen.getByText("Dr Alex Rivera").closest("tr")).toHaveTextContent("Internal");
  });

  it("searches by name and filters by specialty and internal or external", async () => {
    renderPage();
    await screen.findByText("Dr Morgan Grey");
    fireEvent.change(screen.getByLabelText("Search by name"), { target: { value: "grey" } });
    fireEvent.change(screen.getByLabelText("Specialty"), { target: { value: "general_practice" } });
    fireEvent.change(screen.getByLabelText("Internal or external"), { target: { value: "external" } });
    await waitFor(() => expect(providers.listProviders).toHaveBeenLastCalledWith({ q: "grey", specialty: "general_practice", internal: false }));
  });

  it("adds a Provider", async () => {
    providers.addProvider.mockResolvedValue(provider({ id: "p-3" }));
    renderPage();
    fireEvent.click(await screen.findByRole("button", { name: "New Provider" }));
    const form = screen.getByRole("form", { name: "New Provider" });
    fireEvent.change(within(form).getByLabelText("Title"), { target: { value: "Dr" } });
    fireEvent.change(within(form).getByLabelText("First name"), { target: { value: "Taylor" } });
    fireEvent.change(within(form).getByLabelText("Last name"), { target: { value: "Quinn" } });
    fireEvent.change(within(form).getByLabelText("Specialty"), { target: { value: "surgery" } });
    fireEvent.change(within(form).getByLabelText("Organisation"), { target: { value: "Example Hospital" } });
    fireEvent.submit(form);
    await waitFor(() => expect(providers.addProvider).toHaveBeenCalledWith(expect.objectContaining({
      title: "Dr", first_name: "Taylor", last_name: "Quinn", specialty: "surgery", is_internal: false, organisation: "Example Hospital", provider_number: null,
    })));
  });

  it("shows why a duplicate provider number was refused", async () => {
    providers.addProvider.mockRejectedValue(new Error("Provider number 123456AB is already used by Dr Morgan Grey."));
    renderPage();
    fireEvent.click(await screen.findByRole("button", { name: "New Provider" }));
    const form = screen.getByRole("form", { name: "New Provider" });
    fireEvent.change(within(form).getByLabelText("First name"), { target: { value: "Sam" } });
    fireEvent.change(within(form).getByLabelText("Last name"), { target: { value: "Other" } });
    fireEvent.change(within(form).getByLabelText("Provider number"), { target: { value: "123456AB" } });
    fireEvent.submit(form);
    expect(await within(form).findByRole("alert")).toHaveTextContent("already used by Dr Morgan Grey");
  });

  it("edits only what changed", async () => {
    providers.changeProvider.mockResolvedValue(provider({ phone: "02 5550 0399" }));
    renderPage();
    const grey = (await screen.findByText("Dr Morgan Grey")).closest("tr")!;
    fireEvent.click(within(grey).getByRole("button", { name: "Edit" }));
    const form = screen.getByRole("form", { name: "Edit Dr Morgan Grey" });
    fireEvent.change(within(form).getByLabelText("Phone"), { target: { value: "02 5550 0399" } });
    fireEvent.submit(form);
    await waitFor(() => expect(providers.changeProvider).toHaveBeenCalledWith("p-1", { phone: "02 5550 0399" }));
  });

  it("soft-deletes a Provider with a reason", async () => {
    providers.deleteProvider.mockResolvedValue(undefined);
    renderPage();
    const grey = (await screen.findByText("Dr Morgan Grey")).closest("tr")!;
    fireEvent.click(within(grey).getByRole("button", { name: "Delete" }));
    const dialog = screen.getByRole("dialog");
    fireEvent.change(within(dialog).getByLabelText("Reason (required)"), { target: { value: "Retired" } });
    fireEvent.click(within(dialog).getByRole("button", { name: "Delete Provider" }));
    await waitFor(() => expect(providers.deleteProvider).toHaveBeenCalledWith("p-1", "Retired"));
  });
});
