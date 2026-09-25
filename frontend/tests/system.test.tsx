import { fireEvent, render, screen, waitFor, within } from "@testing-library/react";
import { beforeEach, describe, expect, it, vi } from "vitest";

const fetchHealth = vi.hoisted(() => vi.fn());
vi.mock("@/lib/system", () => ({ fetchHealth }));
const jobs = vi.hoisted(() => ({ listRefreshes: vi.fn(), startRefresh: vi.fn(), fetchJob: vi.fn() }));
vi.mock("@/lib/jobs", async (importOriginal) => ({ ...(await importOriginal<object>()), ...jobs }));

import SystemStatusPage from "@/app/(app)/system/page";
import { ViewerProvider } from "@/components/shell/ViewerProvider";
import type { JobTitle } from "@/lib/jobTitles";
import type { JobView } from "@/lib/jobs";
import { userWith } from "./fixtures";

const OK = { status: "ok", environment: "dev", database: "ok", vlm_worker: "not_configured" };
const job = (overrides: Partial<JobView>): JobView => ({
  id: "j-1", kind: "refresh_pbs", status: "succeeded", attempts: 1, max_attempts: 3, created_at: "2026-09-01T00:00:05Z",
  finished_at: "2026-09-01T00:01:00Z", last_error: null, steps: [], ...overrides,
});

function renderAs(jobTitle: JobTitle) {
  render(<ViewerProvider initialUser={userWith(jobTitle)}><SystemStatusPage /></ViewerProvider>);
}

describe("System status", () => {
  beforeEach(() => {
    vi.clearAllMocks();
    jobs.listRefreshes.mockResolvedValue([{ kind: "refresh_pbs", description: "Refresh the PBS Schedule (monthly on the 1st, or on demand)", last_job: job({}) }]);
  });

  it("shows the database, the VLM worker and the environment from /health", async () => {
    fetchHealth.mockResolvedValue(OK);
    renderAs("developer_admin");
    expect(await screen.findByText("Everything Vigil needs is running.")).toBeInTheDocument();
    expect(screen.getByText("OK")).toBeInTheDocument();
    expect(screen.getByText("Not configured")).toBeInTheDocument();
    expect(screen.getByText("DEV")).toBeInTheDocument();
  });

  it("says plainly when the database is down", async () => {
    fetchHealth.mockResolvedValue({ ...OK, status: "degraded", database: "unreachable" });
    renderAs("developer_admin");
    expect(await screen.findByText("Unreachable")).toBeInTheDocument();
    expect(screen.getByText(/degraded/)).toBeInTheDocument();
  });

  it("says when the backend doesn't answer", async () => {
    fetchHealth.mockRejectedValue(new Error("Health check failed (502)."));
    renderAs("developer_admin");
    expect((await screen.findAllByRole("alert"))[0]).toHaveTextContent("The backend isn't answering.");
  });
});

describe("Refreshes", () => {
  beforeEach(() => {
    vi.clearAllMocks();
    fetchHealth.mockResolvedValue(OK);
    jobs.listRefreshes.mockResolvedValue([{ kind: "refresh_pbs", description: "Refresh the PBS Schedule (monthly on the 1st, or on demand)", last_job: job({}) }]);
  });

  it("lists each Refresh with its last run", async () => {
    renderAs("clinician");
    const pbs = (await screen.findByText(/Refresh the PBS Schedule/)).closest("li")!;
    expect(pbs).toHaveTextContent("Succeeded");
    expect(within(pbs).queryByRole("button", { name: /Start/ })).not.toBeInTheDocument();
    expect(screen.getByText("Only a developer admin starts a Refresh.")).toBeInTheDocument();
  });

  it("lets a developer admin start one and follow the Job until it finishes", async () => {
    jobs.startRefresh.mockResolvedValue(job({ id: "j-2", status: "queued", attempts: 0, finished_at: null }));
    jobs.fetchJob
      .mockResolvedValueOnce(job({ id: "j-2", status: "running", finished_at: null, steps: [{ name: "fetch", status: "succeeded", started_at: null, finished_at: null }] }))
      .mockResolvedValue(job({ id: "j-2", status: "succeeded", steps: [{ name: "fetch", status: "succeeded", started_at: null, finished_at: null }, { name: "store", status: "succeeded", started_at: null, finished_at: null }] }));
    renderAs("developer_admin");
    const pbs = (await screen.findByText(/Refresh the PBS Schedule/)).closest("li")!;
    fireEvent.click(within(pbs).getByRole("button", { name: "Start Refresh" }));
    await waitFor(() => expect(jobs.startRefresh).toHaveBeenCalledWith("refresh_pbs"));
    expect(await within(pbs).findByText("Queued")).toBeInTheDocument();
    await waitFor(() => expect(within(pbs).getByText("Succeeded")).toBeInTheDocument(), { timeout: 5000 });
    expect(pbs).toHaveTextContent("fetch ✓ · store ✓");
  });

  it("shows a failed Refresh's error code", async () => {
    jobs.listRefreshes.mockResolvedValue([{ kind: "refresh_pbs", description: "Refresh the PBS Schedule", last_job: job({ status: "failed", attempts: 3, last_error: "source_unreachable" }) }]);
    renderAs("developer_admin");
    const pbs = (await screen.findByText(/Refresh the PBS Schedule/)).closest("li")!;
    expect(pbs).toHaveTextContent("Failed");
    expect(pbs).toHaveTextContent("source_unreachable");
    expect(pbs).toHaveTextContent("after 3 attempts");
  });
});
