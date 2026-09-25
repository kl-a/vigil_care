import { render, screen } from "@testing-library/react";
import { describe, expect, it, vi } from "vitest";

const fetchHealth = vi.hoisted(() => vi.fn());
vi.mock("@/lib/system", () => ({ fetchHealth }));

import SystemStatusPage from "@/app/(app)/system/page";

describe("System status", () => {
  it("shows the database, the VLM worker and the environment from /health", async () => {
    fetchHealth.mockResolvedValue({ status: "ok", environment: "dev", database: "ok", vlm_worker: "not_configured" });
    render(<SystemStatusPage />);
    expect(await screen.findByText("Everything Vigil needs is running.")).toBeInTheDocument();
    expect(screen.getByText("OK")).toBeInTheDocument();
    expect(screen.getByText("Not configured")).toBeInTheDocument();
    expect(screen.getByText("DEV")).toBeInTheDocument();
  });

  it("says plainly when the database is down", async () => {
    fetchHealth.mockResolvedValue({ status: "degraded", environment: "dev", database: "unreachable", vlm_worker: "not_configured" });
    render(<SystemStatusPage />);
    expect(await screen.findByText("Unreachable")).toBeInTheDocument();
    expect(screen.getByText(/degraded/)).toBeInTheDocument();
  });

  it("says when the backend doesn't answer", async () => {
    fetchHealth.mockRejectedValue(new Error("Health check failed (502)."));
    render(<SystemStatusPage />);
    expect(await screen.findByRole("alert")).toHaveTextContent("The backend isn't answering.");
  });
});
