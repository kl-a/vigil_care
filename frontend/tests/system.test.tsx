import { fireEvent, render, screen, waitFor, within } from "@testing-library/react";
import { beforeEach, describe, expect, it, vi } from "vitest";

const system = vi.hoisted(() => ({ fetchHealth: vi.fn(), listPipelineRuns: vi.fn() }));
const fetchHealth = system.fetchHealth;
vi.mock("@/lib/system", async (importOriginal) => ({ ...(await importOriginal<object>()), ...system }));
const jobs = vi.hoisted(() => ({
  listRefreshes: vi.fn(), startRefresh: vi.fn(), fetchJob: vi.fn(), listJobs: vi.fn(), fetchQueueDepth: vi.fn(), listRefreshHistory: vi.fn(),
}));
vi.mock("@/lib/jobs", async (importOriginal) => ({ ...(await importOriginal<object>()), ...jobs }));

import SystemStatusPage from "@/app/(app)/system/page";
import { ViewerProvider } from "@/components/shell/ViewerProvider";
import type { JobTitle } from "@/lib/jobTitles";
import type { JobView } from "@/lib/jobs";
import type { PipelineRunView } from "@/lib/system";
import { userWith } from "./fixtures";

const OK = { status: "ok", environment: "dev", database: "ok", vlm_worker: "not_configured" };
const job = (overrides: Partial<JobView>): JobView => ({
  id: "j-1", kind: "refresh_pbs", status: "succeeded", system_wide: true, attempts: 1, max_attempts: 3, created_at: "2026-09-01T00:00:05Z",
  finished_at: "2026-09-01T00:01:00Z", last_error: null, payload: {}, steps: [], ...overrides,
});
const step = (name: string, output: Record<string, unknown> = {}) => ({ name, status: "succeeded", started_at: null, finished_at: null, output });
const run = (overrides: Partial<PipelineRunView>): PipelineRunView => ({
  id: "r-1", kind: "ocr", status: "succeeded", system_wide: false, inputs: {}, versions: {}, created_at: "2026-09-01T10:00:00Z",
  started_at: "2026-09-01T10:00:00Z", finished_at: "2026-09-01T10:00:42Z", error_detail: null, ...overrides,
});

/** Every Support View answers, empty unless a test says otherwise. */
function quietSupportViews() {
  system.listPipelineRuns.mockResolvedValue([]);
  jobs.listJobs.mockResolvedValue([]);
  jobs.listRefreshHistory.mockResolvedValue([]);
  jobs.fetchQueueDepth.mockResolvedValue({ queued: 0, running: 0, failed_last_day: 0 });
}

function renderAs(jobTitle: JobTitle) {
  render(<ViewerProvider initialUser={userWith(jobTitle)}><SystemStatusPage /></ViewerProvider>);
}

describe("System status", () => {
  beforeEach(() => {
    vi.clearAllMocks();
    quietSupportViews();
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
    quietSupportViews();
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
      .mockResolvedValueOnce(job({ id: "j-2", status: "running", finished_at: null, steps: [step("fetch")] }))
      .mockResolvedValue(job({ id: "j-2", status: "succeeded", steps: [step("fetch"), step("store")] }));
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

describe("Support Views", () => {
  beforeEach(() => {
    vi.clearAllMocks();
    quietSupportViews();
    fetchHealth.mockResolvedValue(OK);
    jobs.listRefreshes.mockResolvedValue([{ kind: "refresh_pbs", description: "Refresh the PBS Schedule", last_job: null }]);
  });

  it("shows the job queue's depth beside the health checks", async () => {
    jobs.fetchQueueDepth.mockResolvedValue({ queued: 2, running: 1, failed_last_day: 1 });
    renderAs("developer_admin");
    const tile = (await screen.findByText("Job queue")).closest("div")!;
    await waitFor(() => expect(tile).toHaveTextContent("2 queued · 1 running"));
    expect(tile).toHaveTextContent("1 failed in the last day");
  });

  it("lists recent Jobs by Job Kind, state and scope, with their IDs-only details", async () => {
    jobs.listJobs.mockResolvedValue([
      job({ id: "5b2c9e1a-0000-4000-8000-000000000001", steps: [step("fetch", { item_count: 3 })] }),
      job({ id: "5b2c9e1a-0000-4000-8000-000000000002", kind: "ingest_document", status: "failed", system_wide: false, attempts: 3, last_error: "unexpected_error:valueerror", payload: { document_id: "d-9" } }),
    ]);
    renderAs("developer_admin");
    const table = await screen.findByRole("table", { name: "Jobs" });
    const [, pbs, ingest] = within(table).getAllByRole("row");
    expect(pbs).toHaveTextContent("refresh_pbs");
    expect(pbs).toHaveTextContent("Succeeded");
    expect(pbs).toHaveTextContent("System-wide");
    expect(pbs).toHaveTextContent("fetch ✓ item_count=3");
    expect(ingest).toHaveTextContent("This Practice");
    expect(ingest).toHaveTextContent("document_id=d-9");
    expect(ingest).toHaveTextContent("unexpected_error:valueerror");
  });

  it("lists pipeline runs with their timings and error codes", async () => {
    system.listPipelineRuns.mockResolvedValue([run({ status: "failed", error_detail: "vlm_timeout", inputs: { document_id: "d-9", pages: [1, 2] } })]);
    renderAs("clinician");
    const table = await screen.findByRole("table", { name: "Pipeline runs" });
    const row = within(table).getAllByRole("row")[1];
    expect(row).toHaveTextContent("ocr");
    expect(row).toHaveTextContent("Failed");
    expect(row).toHaveTextContent("42 s");
    expect(row).toHaveTextContent("document_id=d-9 · pages=1,2");
    expect(row).toHaveTextContent("vlm_timeout");
  });

  it("says when there are no pipeline runs yet", async () => {
    renderAs("developer_admin");
    expect(await screen.findByText(/No pipeline runs yet/)).toBeInTheDocument();
  });

  it("shows Refresh history with each run's counts", async () => {
    jobs.listRefreshHistory.mockResolvedValue([
      job({ id: "j-3", steps: [step("fetch", { item_count: 5123, schedule_date: "2026-09-01" }), step("store")] }),
      job({ id: "j-2", status: "failed", attempts: 3, last_error: "source_unreachable" }),
    ]);
    renderAs("secretary");
    const table = await screen.findByRole("table", { name: "Refresh history" });
    const [, latest, failed] = within(table).getAllByRole("row");
    expect(latest).toHaveTextContent("item_count=5123 · schedule_date=2026-09-01");
    expect(latest).toHaveTextContent("55 s");
    expect(failed).toHaveTextContent("source_unreachable");
  });

  it("reloads the Jobs, the queue and the history when a developer admin starts a Refresh", async () => {
    jobs.startRefresh.mockResolvedValue(job({ id: "j-9", status: "queued", attempts: 0, finished_at: null }));
    jobs.fetchJob.mockResolvedValue(job({ id: "j-9" }));
    renderAs("developer_admin");
    fireEvent.click(await screen.findByRole("button", { name: "Start Refresh" }));
    await waitFor(() => expect(jobs.listJobs).toHaveBeenCalledTimes(2));
    expect(jobs.fetchQueueDepth).toHaveBeenCalledTimes(2);
    expect(jobs.listRefreshHistory).toHaveBeenCalledTimes(2);
  });
});
