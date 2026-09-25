import { fireEvent, render, screen, waitFor, within } from "@testing-library/react";
import { beforeEach, describe, expect, it, vi } from "vitest";

vi.mock("next/navigation", () => ({ usePathname: () => "/users", useRouter: () => ({ replace: vi.fn() }) }));

const users = vi.hoisted(() => ({
  listUsers: vi.fn(),
  createUser: vi.fn(),
  changeUser: vi.fn(),
  fetchUser: vi.fn(),
}));
vi.mock("@/lib/users", async (importOriginal) => ({ ...(await importOriginal<object>()), ...users }));
const providers = vi.hoisted(() => ({ listProviders: vi.fn() }));
vi.mock("@/lib/providers", async (importOriginal) => ({ ...(await importOriginal<object>()), ...providers }));

import UserManagementPage from "@/app/(app)/users/page";
import UserPage from "@/app/(app)/users/[id]/page";
import { ViewerProvider } from "@/components/shell/ViewerProvider";
import type { UserRow } from "@/lib/users";
import { userWith } from "./fixtures";

const me = userWith("secretary");
const row = (overrides: Partial<UserRow>): UserRow => ({
  id: "u-1", username: "sam.lee", display_name: "Sam Lee (synthetic)", job_title: "trial_coordinator",
  is_active: true, last_login_at: null, provider_id: null, provider_name: null, ...overrides,
});

async function renderPage(ui = <UserManagementPage />) {
  render(<ViewerProvider initialUser={me}>{ui}</ViewerProvider>);
}

describe("User Management", () => {
  beforeEach(() => {
    vi.clearAllMocks();
    window.localStorage.clear();
    users.listUsers.mockResolvedValue([row({}), row({ id: me.id, username: "jordan.park", display_name: me.display_name, job_title: "secretary" })]);
    users.changeUser.mockResolvedValue(row({}));
  });

  it("lists Users with Job Title, Provider record, status and last login", async () => {
    await renderPage();
    const sam = (await screen.findByText("Sam Lee (synthetic)")).closest("tr")!;
    expect(within(sam).getByText("Trial coordinator")).toBeInTheDocument();
    expect(within(sam).getByText("Active")).toBeInTheDocument();
    expect(within(sam).getByText("Never")).toBeInTheDocument();
    expect(within(sam).getByText("—")).toBeInTheDocument();
  });

  it("offers no actions on your own row", async () => {
    await renderPage();
    const mine = (await screen.findByText(me.display_name)).closest("tr")!;
    expect(within(mine).getByText("You")).toBeInTheDocument();
    expect(within(mine).queryByRole("button")).not.toBeInTheDocument();
  });

  it("changes a Job Title as a sign-off in your name", async () => {
    await renderPage();
    const sam = (await screen.findByText("Sam Lee (synthetic)")).closest("tr")!;
    fireEvent.click(within(sam).getByRole("button", { name: "Change Job Title" }));
    const dialog = screen.getByRole("dialog");
    fireEvent.change(within(dialog).getByLabelText("Job Title"), { target: { value: "developer_admin" } });
    expect(dialog).toHaveTextContent("will no longer see any Patient data");
    const confirm = within(dialog).getByRole("button", { name: "Change Job Title" });
    expect(confirm).toBeDisabled(); // SignOffDialog: nothing is signed off until you tick the box
    fireEvent.click(within(dialog).getByRole("checkbox", { name: `I confirm this change. Sign it off as ${me.display_name} (Secretary).` }));
    fireEvent.click(confirm);
    await waitFor(() => expect(users.changeUser).toHaveBeenCalledWith("u-1", { job_title: "developer_admin", reason: undefined }));
  });

  it("needs a reason to deactivate", async () => {
    await renderPage();
    const sam = (await screen.findByText("Sam Lee (synthetic)")).closest("tr")!;
    fireEvent.click(within(sam).getByRole("button", { name: "Deactivate" }));
    const dialog = screen.getByRole("dialog");
    const confirm = within(dialog).getByRole("button", { name: "Deactivate" });
    expect(confirm).toBeDisabled();
    fireEvent.change(within(dialog).getByLabelText("Reason (required)"), { target: { value: "Left the Practice" } });
    fireEvent.click(confirm);
    await waitFor(() => expect(users.changeUser).toHaveBeenCalledWith("u-1", { is_active: false, reason: "Left the Practice" }));
  });

  it("adds a User", async () => {
    users.createUser.mockResolvedValue(row({ id: "u-2" }));
    await renderPage();
    fireEvent.click(await screen.findByRole("button", { name: "New User" }));
    const form = screen.getByRole("form", { name: "New User" });
    fireEvent.change(within(form).getByLabelText("Name"), { target: { value: "Riley Hart (synthetic)" } });
    fireEvent.change(within(form).getByLabelText("Username"), { target: { value: "Riley.Hart" } });
    fireEvent.change(within(form).getByLabelText("Job Title"), { target: { value: "clinician" } });
    fireEvent.submit(form);
    await waitFor(() => expect(users.createUser).toHaveBeenCalledWith({ display_name: "Riley Hart (synthetic)", username: "riley.hart", job_title: "clinician" }));
  });

  it("adds someone who already uses Vigil at another Practice by username alone", async () => {
    users.createUser.mockResolvedValue(row({ id: "u-2" }));
    await renderPage();
    fireEvent.click(await screen.findByRole("button", { name: "New User" }));
    const form = screen.getByRole("form", { name: "New User" });
    fireEvent.change(within(form).getByLabelText("Username"), { target: { value: "alex.rivera" } });
    fireEvent.change(within(form).getByLabelText("Job Title"), { target: { value: "clinician" } });
    fireEvent.submit(form);
    await waitFor(() => expect(users.createUser).toHaveBeenCalledWith({ username: "alex.rivera", job_title: "clinician" }));
  });

  it("shows each User's linked Provider record by name", async () => {
    users.listUsers.mockResolvedValue([row({ provider_id: "p-1", provider_name: "Dr Riley Hart" })]);
    await renderPage();
    expect((await screen.findByText("Sam Lee (synthetic)")).closest("tr")).toHaveTextContent("Dr Riley Hart");
  });

  it("links a User to their own Provider record (Stage 2, shown as upcoming)", async () => {
    window.localStorage.setItem("vigil.showUpcoming", "true");
    providers.listProviders.mockResolvedValue([
      { id: "p-1", display_name: "Dr Riley Hart", title: "Dr", first_name: "Riley", last_name: "Hart", provider_number: null, specialty: "medical_oncology", is_internal: true, organisation: null, phone: null, email: null, fax: null, notes: null },
    ]);
    await renderPage();
    const sam = (await screen.findByText("Sam Lee (synthetic)")).closest("tr")!;
    fireEvent.click(within(sam).getByRole("button", { name: "Link Provider" }));
    const dialog = screen.getByRole("dialog");
    fireEvent.change(await within(dialog).findByLabelText("Provider record"), { target: { value: "p-1" } });
    fireEvent.click(within(dialog).getByRole("checkbox"));
    fireEvent.click(within(dialog).getByRole("button", { name: "Link" }));
    await waitFor(() => expect(users.changeUser).toHaveBeenCalledWith("u-1", { provider_id: "p-1" }));
  });

  it("hides linking until Stage 2 ships", async () => {
    await renderPage();
    const sam = (await screen.findByText("Sam Lee (synthetic)")).closest("tr")!;
    expect(within(sam).queryByRole("button", { name: "Link Provider" })).not.toBeInTheDocument();
  });

  it("shows why the backend refused", async () => {
    users.listUsers.mockRejectedValue(new Error("Not available for your Job Title."));
    await renderPage();
    expect(await screen.findByRole("alert")).toHaveTextContent("Not available for your Job Title.");
  });
});

describe("a User's page", () => {
  it("shows the audit trail: what changed, who signed it off and why", async () => {
    users.fetchUser.mockResolvedValue({
      ...row({}),
      history: [
        { action: "edit", by_display_name: "Jordan Park (synthetic)", by_job_title: "secretary", before: { job_title: "secretary" }, after: { job_title: "trial_coordinator" }, reason: "New role", reauthenticated: false, at: "2026-09-25T01:00:00Z" },
        { action: "edit", by_display_name: "Casey Dev (synthetic)", by_job_title: "developer_admin", before: null, after: { job_title: "secretary", username: "sam.lee" }, reason: null, reauthenticated: false, at: "2026-09-24T01:00:00Z" },
      ],
    });
    await renderPage(<UserPage params={{ id: "u-1" }} />);
    expect(await screen.findByText("Job Title changed from Secretary to Trial coordinator")).toBeInTheDocument();
    expect(screen.getByText(/Signed off by Jordan Park \(synthetic\) \(Secretary\)/)).toBeInTheDocument();
    expect(screen.getByText("Reason: New role")).toBeInTheDocument();
    expect(screen.getByText("Added as Secretary")).toBeInTheDocument();
  });
});
