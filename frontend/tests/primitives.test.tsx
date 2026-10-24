import { fireEvent, render, screen, waitFor, within } from "@testing-library/react";
import { beforeEach, describe, expect, it, vi } from "vitest";

const api = vi.hoisted(() => ({ request: vi.fn() }));
vi.mock("@/lib/api", async (importOriginal) => ({ ...(await importOriginal<object>()), ...api }));

import { RowMenu } from "@/components/ui/RowMenu";
import { SubTabs } from "@/components/ui/SubTabs";
import { TableCard } from "@/components/ui/TableCard";
import { FlagWord, NotRecorded, ValueLegend } from "@/components/ui/ValueStates";
import { VerifiedMark } from "@/components/ui/Verified";
import { formatDate, formatWhen } from "@/lib/format";

describe("Dates", () => {
  it("are written one way: clinical dates, and moments in 24-hour time", () => {
    expect(formatDate("2026-09-18")).toBe("18 Sep 2026");
    expect(formatDate("2026-09-18T01:00:00Z")).toBe("18 Sep 2026");
    expect(formatDate(null)).toBe("—");
    expect(formatWhen(new Date(2026, 8, 18, 13, 5).toISOString())).toBe("18 Sep 2026, 13:05");
    expect(formatWhen(null)).toBe("Never");
  });
});

describe("The ✓ Verified icon", () => {
  beforeEach(() => vi.clearAllMocks());
  const ENTERED = { by: "Dr Alex Rivera", job_title: "clinician" as const, at: "2026-09-14T03:00:00Z" };

  it("says who verified it, then the latest Verification once loaded, and opens the whole history", async () => {
    api.request.mockResolvedValue([
      { by: "Sam Lee", job_title: "trial_coordinator", at: "2026-09-16T03:00:00Z", action: "edit", reason: "From the GP letter", before: { notes: null }, after: { notes: "x" } },
      { by: "Dr Alex Rivera", job_title: "clinician", at: "2026-09-14T03:00:00Z", action: "edit", reason: null, before: null, after: { name: "x" } },
    ]);
    render(<VerifiedMark subjectTable="condition" subjectId="c-1" entered={ENTERED} />);
    const mark = screen.getByRole("button", { name: /^Verified by Dr Alex Rivera \(Clinician\)/ });
    fireEvent.mouseEnter(mark);
    expect(await screen.findByRole("tooltip")).toHaveTextContent(/^Corrected by Sam Lee \(Trial coordinator\), 16 Sep 2026, \d\d:\d\d: From the GP letter$/);
    expect(api.request).toHaveBeenCalledWith("/verifications/condition/c-1");
    fireEvent.click(mark);
    const history = within(await screen.findByRole("dialog", { name: "History of this value" })).getByRole("list", { name: "History" });
    expect(within(history).getAllByRole("listitem").map((li) => li.textContent?.split(",")[0])).toEqual(["Corrected by Sam Lee (Trial coordinator)", "Verified by Dr Alex Rivera (Clinician)"]);
  });
});

describe("Value states", () => {
  it("show missing, outside range and the legend with an icon as well as colour", () => {
    render(<><NotRecorded /><FlagWord flag="high" /><FlagWord flag="normal" /><ValueLegend /></>);
    expect(screen.getAllByText("Not recorded")[0]!.tagName).toBe("EM");
    const high = screen.getByText("High");
    expect(high.querySelector("svg")).not.toBeNull();
    expect(screen.getByLabelText("Legend")).toHaveTextContent("VerifiedOutside reference rangeNot recorded = missing");
  });
});

describe("Sub-tabs, table toolbar and row menu", () => {
  it("work as segmented buttons with counts, a toolbar with a row count, and a ⋯ menu", async () => {
    const onChange = vi.fn();
    const onRemove = vi.fn();
    render(
      <>
        <SubTabs label="Clinical Data" tabs={[{ key: "labs", label: "Labs", count: 6 }, { key: "imaging", label: "Imaging" }]} current="labs" onChange={onChange} />
        <TableCard label="Patients" count="3 patients" toolbar={<input aria-label="Search" />}><table /></TableCard>
        <RowMenu label="Asthma" items={[{ label: "Remove", danger: true, onSelect: onRemove }]} />
      </>,
    );
    expect(screen.getByRole("button", { name: "Labs 6" })).toHaveAttribute("aria-current", "page");
    fireEvent.click(screen.getByRole("button", { name: "Imaging" }));
    expect(onChange).toHaveBeenCalledWith("imaging");
    expect(screen.getByRole("toolbar", { name: "Patients filters" })).toHaveTextContent("3 patients");
    fireEvent.click(screen.getByRole("button", { name: "More actions: Asthma" }));
    fireEvent.click(screen.getByRole("menuitem", { name: "Remove" }));
    await waitFor(() => expect(onRemove).toHaveBeenCalled());
    expect(screen.queryByRole("menu")).not.toBeInTheDocument();
  });
});
